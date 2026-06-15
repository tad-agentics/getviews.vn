"""Douyin corpus rows as live-diagnosis reference videos (Phase 2b).

Reads ``douyin_video_corpus`` from Supabase only — no live TikHub in the
hot SSE path. Gated by ``GETVIEWS_DOUYIN_REFERENCE_POOL``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from getviews_pipeline.config import GETVIEWS_DOUYIN_REFERENCE_POOL
from getviews_pipeline.douyin_match import (
    fetch_douyin_peer_rows,
    map_creator_niche_to_douyin_niche_id,
)
from getviews_pipeline.hook_type_normalize import normalize_hook_type

logger = logging.getLogger(__name__)

_DOUYIN_REF_LIMIT = int(os.environ.get("GETVIEWS_DOUYIN_REFERENCE_LIMIT", "3"))


def douyin_reference_pool_enabled() -> bool:
    return GETVIEWS_DOUYIN_REFERENCE_POOL


def _build_douyin_reference_aweme(row: dict[str, Any]) -> dict[str, Any]:
    """Map a douyin_video_corpus row → aweme-shaped ref dict."""
    vid = str(row.get("video_id") or "")
    handle = str(row.get("creator_handle") or "")
    views = int(row.get("views") or 0)
    likes = int(row.get("likes") or 0)
    desc = str(row.get("title_vi") or row.get("title_zh") or "")[:200]
    playback = str(row.get("playback_url") or "")
    douyin_url = str(row.get("douyin_url") or f"https://www.douyin.com/video/{vid}")
    analysis_json = row.get("analysis_json") or {}
    if not isinstance(analysis_json, dict):
        analysis_json = {}

    return {
        "aweme_id": vid,
        "desc": desc,
        "author": {"unique_id": handle, "nickname": row.get("creator_name")},
        "douyin_url": douyin_url,
        "thumbnail_url": row.get("thumbnail_url"),
        "statistics": {
            "play_count": views,
            "digg_count": likes,
            "comment_count": int(row.get("comments") or 0),
            "share_count": int(row.get("shares") or 0),
        },
        "_from_douyin_corpus": True,
        "_corpus_analysis": analysis_json,
        "_corpus_er": float(row.get("engagement_rate") or 0.0),
        "_corpus_video_url": playback or None,
        "_corpus_hook_analysis": analysis_json.get("hook_analysis") or {},
        "_corpus_content_format": row.get("content_format") or "",
        "_corpus_content_class_id": row.get("content_class_id"),
        "_douyin_adapt_level": row.get("adapt_level"),
        "_douyin_sub_vi": row.get("sub_vi"),
    }


async def fetch_douyin_reference_awemes(
    client: Any,
    *,
    creator_niche_slug: str | None,
    hook_type: str | None,
    content_class_id: int | None = None,
    limit: int | None = None,
    exclude_video_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return Douyin peer awemes for reference carousel merge."""
    if not douyin_reference_pool_enabled():
        return []

    niche_id = map_creator_niche_to_douyin_niche_id(creator_niche_slug)
    if niche_id is None:
        return []

    ht = normalize_hook_type(hook_type or "")
    if ht in ("none", "other", ""):
        ht = ""

    lim = limit if limit is not None else _DOUYIN_REF_LIMIT
    rows = fetch_douyin_peer_rows(
        client,
        niche_id=niche_id,
        hook_type=ht or "other",
        content_class_id=content_class_id,
        limit=lim,
        require_playback=True,
    )

    out: list[dict[str, Any]] = []
    for row in rows:
        vid = str(row.get("video_id") or "")
        if not vid or vid == exclude_video_id:
            continue
        if not row.get("playback_url"):
            continue
        # Hot-path safety: a row with no stored analysis would fall through
        # to live ``analyze_aweme`` in ``_ref`` (download + Gemini in the SSE
        # path). Skip it — Douyin refs must be Supabase-only.
        aj = row.get("analysis_json")
        if not isinstance(aj, dict) or not aj:
            continue
        out.append(_build_douyin_reference_aweme(row))
    return out
