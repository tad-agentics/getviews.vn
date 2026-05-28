"""Marketing Corpus Pick — batch orchestrator (pick + analyze + record)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from getviews_pipeline.config import R2_PUBLIC_URL
from getviews_pipeline.supabase_client import get_service_client
from getviews_pipeline.video_analyze import (
    finalize_video_narrative_layer,
    run_video_analyze_pipeline,
)

logger = logging.getLogger(__name__)

MARKETING_ANALYSIS_DEPTH = "basic"
MARKETING_VIDEO_MODE = "win"
POOL_EXHAUSTED = "marketing_pool_exhausted"
ANALYSIS_FAILED = "analysis_failed"


def _r2_thumbnail_url(video_id: str) -> str | None:
    base = (R2_PUBLIC_URL or "").rstrip("/")
    vid = str(video_id or "").strip()
    if not base or not vid:
        return None
    return f"{base}/thumbnails/{vid}.webp"


def _resolve_thumbnail_url(corpus_thumb: str | None, video_id: str) -> str | None:
    thumb = str(corpus_thumb or "").strip()
    if thumb:
        return thumb
    return _r2_thumbnail_url(video_id)


def _narrative_ready(out: dict[str, Any]) -> bool:
    narrative = out.get("narrative_vi")
    if not isinstance(narrative, dict):
        return False
    return bool(str(narrative.get("van_de_chinh") or "").strip())


def _rpc_error_code(exc: Exception) -> str | None:
    msg = str(exc).lower()
    if POOL_EXHAUSTED in msg:
        return POOL_EXHAUSTED
    return None


def select_marketing_corpus_video_row(sb: Any) -> dict[str, Any]:
    """Call ``select_marketing_corpus_video`` RPC. Raises on pool exhausted."""
    res = sb.rpc("select_marketing_corpus_video").execute()
    data = res.data
    if not data:
        raise RuntimeError(POOL_EXHAUSTED)
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data:
        row = data[0]
        if isinstance(row, dict):
            return row
    raise RuntimeError(POOL_EXHAUSTED)


def record_marketing_pick(
    sb: Any,
    *,
    video_id: str,
    creator_niche_id: int,
    priority_weight: int,
    analysis_depth: str = MARKETING_ANALYSIS_DEPTH,
) -> str:
    """Persist pick history; returns ISO ``picked_at``."""
    res = sb.rpc(
        "record_marketing_video_pick",
        {
            "p_video_id": video_id,
            "p_creator_niche_id": creator_niche_id,
            "p_priority_weight": priority_weight,
            "p_analysis_depth": analysis_depth,
        },
    ).execute()
    picked_at = res.data
    if isinstance(picked_at, str) and picked_at.strip():
        return picked_at
    return datetime.now(UTC).isoformat()


def build_marketing_pick_response(
    corpus_row: dict[str, Any],
    analysis_out: dict[str, Any],
    *,
    picked_at: str,
) -> dict[str, Any]:
    """Shape API JSON for marketing team."""
    video_id = str(corpus_row.get("video_id") or analysis_out.get("video_id") or "")
    niche_id = int(corpus_row.get("creator_niche_id") or 0)
    return {
        "video_id": video_id,
        "tiktok_url": corpus_row.get("tiktok_url") or analysis_out.get("tiktok_url"),
        "thumbnail_url": _resolve_thumbnail_url(
            corpus_row.get("thumbnail_url"),
            video_id,
        ),
        "creator_handle": corpus_row.get("creator_handle")
        or (analysis_out.get("meta") or {}).get("creator"),
        "views": int(corpus_row.get("views") or (analysis_out.get("meta") or {}).get("views") or 0),
        "caption": corpus_row.get("caption"),
        "hook_phrase": corpus_row.get("hook_phrase"),
        "hook_type": corpus_row.get("hook_type"),
        "posted_at": corpus_row.get("posted_at"),
        "breakout_multiplier": corpus_row.get("breakout_multiplier"),
        "content_type": corpus_row.get("content_type"),
        "creator_niche": {
            "id": niche_id,
            "slug": corpus_row.get("creator_niche_slug"),
            "name_vn": corpus_row.get("creator_niche_name_vn"),
            "priority_weight": int(corpus_row.get("priority_weight") or 1),
        },
        "analysis": {
            "analysis_depth": MARKETING_ANALYSIS_DEPTH,
            "mode": analysis_out.get("mode") or MARKETING_VIDEO_MODE,
            "narrative_vi": analysis_out.get("narrative_vi"),
            "diagnosis": analysis_out.get("diagnosis"),
            "performance_tier": analysis_out.get("performance_tier"),
            "hook_phases": analysis_out.get("hook_phases") or [],
            "flop_issues": analysis_out.get("flop_issues"),
            "meta": analysis_out.get("meta"),
            "format_cards": analysis_out.get("format_cards"),
            "reference_videos": analysis_out.get("reference_videos"),
        },
        "picked_at": picked_at,
    }


def run_marketing_corpus_pick() -> dict[str, Any]:
    """Pick one corpus video, run basic/win diagnosis, record pick, return payload.

    Raises ``RuntimeError`` with code ``marketing_pool_exhausted`` or
    ``analysis_failed`` for HTTP mapping.
    """
    sb = get_service_client()
    try:
        corpus_row = select_marketing_corpus_video_row(sb)
    except Exception as exc:
        if _rpc_error_code(exc) == POOL_EXHAUSTED:
            raise RuntimeError(POOL_EXHAUSTED) from exc
        raise

    video_id = str(corpus_row.get("video_id") or "").strip()
    tiktok_url = str(corpus_row.get("tiktok_url") or "").strip() or None
    if not video_id:
        raise RuntimeError(POOL_EXHAUSTED)

    logger.info(
        "[marketing/pick] selected video_id=%s niche_id=%s views=%s",
        video_id,
        corpus_row.get("creator_niche_id"),
        corpus_row.get("views"),
    )

    try:
        analysis_out = run_video_analyze_pipeline(
            sb,
            sb,
            video_id=video_id,
            tiktok_url=tiktok_url,
            force_refresh=False,
            mode=MARKETING_VIDEO_MODE,
            step_queue=None,
            analysis_depth=MARKETING_ANALYSIS_DEPTH,
        )
    except Exception as exc:
        logger.exception("[marketing/pick] pipeline failed video_id=%s", video_id)
        raise RuntimeError(ANALYSIS_FAILED) from exc

    if not _narrative_ready(analysis_out):
        niche_id = int(corpus_row.get("creator_niche_id") or 0) or None
        try:
            finalize_video_narrative_layer(
                analysis_out,
                step_queue=None,
                fallback_niche_id=niche_id,
                user_sb=sb,
                service_sb=sb,
                user_id=None,
                analysis_depth=MARKETING_ANALYSIS_DEPTH,
            )
        except Exception as exc:
            logger.exception(
                "[marketing/pick] narrative finalize failed video_id=%s",
                video_id,
            )
            raise RuntimeError(ANALYSIS_FAILED) from exc

    if not _narrative_ready(analysis_out):
        logger.warning(
            "[marketing/pick] missing van_de_chinh after finalize video_id=%s",
            video_id,
        )
        raise RuntimeError(ANALYSIS_FAILED)

    niche_id = int(corpus_row.get("creator_niche_id") or 0)
    weight = int(corpus_row.get("priority_weight") or 1)
    picked_at = record_marketing_pick(
        sb,
        video_id=video_id,
        creator_niche_id=niche_id,
        priority_weight=weight,
    )

    return build_marketing_pick_response(corpus_row, analysis_out, picked_at=picked_at)
