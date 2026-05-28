"""ME-17 — Backfill ``content_context`` + ``niche_classification`` for legacy corpus rows.

Text-only Gemini over existing ``analysis_json`` (no media re-fetch). Sets
``niche_resolution_source='gemini_two_axis'`` for provenance on backfilled rows.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from pydantic import BaseModel, ConfigDict

from getviews_pipeline.corpus_ingest import _niche_resolution_shadow_fields  # noqa: PLC2701
from getviews_pipeline.cross_niche_class_remap import (
    apply_cross_niche_class_remap,
    resolve_post_route_content_class_id,
)
from getviews_pipeline.fashion_commerce_niche_remap import apply_fashion_commerce_niche_remap
from getviews_pipeline.models import (
    CarouselNicheClassification,
    ContentContext,
    NicheClassification,
)
from getviews_pipeline.profile_niches import CREATOR_NICHE_SLUG_TO_ID, creator_niche_id_for_legacy_niche
from getviews_pipeline.two_axis_taxonomy import (
    build_carousel_extraction_niche_glossary_block,
    build_extraction_niche_glossary_block,
)

logger = logging.getLogger(__name__)

_COMPACT_JSON_MAX_CHARS = 28_000
_DEFAULT_MAX_RUNTIME_S = 3300.0


class VideoClassificationBackfillLLM(BaseModel):
    """Structured response for video rows — mirrors HI-9 extraction shape."""

    model_config = ConfigDict(extra="ignore")

    content_context: ContentContext
    niche_classification: NicheClassification


class CarouselClassificationBackfillLLM(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content_context: ContentContext
    niche_classification: CarouselNicheClassification


_BACKFILL_SYSTEM_VI = """Bạn là trợ lý phân loại nội dung TikTok Việt Nam.
Trả về đúng một JSON khớp schema — không markdown, không lời dẫn.
Chỉ suy luận từ JSON phân tích người dùng cung cấp; không bịa chi tiết không có trong dữ liệu.
Điền đầy đủ content_context và niche_classification theo glossary trong user message."""


def _compact_analysis_json(analysis_json: dict[str, Any]) -> str:
    raw = json.dumps(analysis_json, ensure_ascii=False, default=str)
    if len(raw) <= _COMPACT_JSON_MAX_CHARS:
        return raw
    return raw[: _COMPACT_JSON_MAX_CHARS - 24] + '\n…(đã cắt bớt JSON)'


def _build_user_prompt(content_type: str, compact_json: str) -> str:
    if content_type == "carousel":
        glossary = build_carousel_extraction_niche_glossary_block()
        type_line = (
            "Loại nội dung: carousel — niche_classification dùng carousel_format_axis "
            "(không dùng format_axis của video)."
        )
    else:
        glossary = build_extraction_niche_glossary_block()
        type_line = "Loại nội dung: video — niche_classification dùng format_axis."
    return f"""=== Glossary (bắt buộc — slug đúng chuỗi snake_case) ===
{glossary}

{type_line}

=== JSON phân tích đã lưu (căn cứ duy nhất) ===
{compact_json}
"""


def backfill_row_with_gemini(
    analysis_json: dict[str, Any],
    content_type: str,
) -> dict[str, Any] | None:
    """Return merged ``analysis_json`` dict, or ``None`` on Gemini/parse failure."""
    try:
        from google.genai import types  # type: ignore
    except Exception as exc:
        logger.warning("[classification_backfill] google.genai unavailable: %s", exc)
        return None

    from getviews_pipeline.config import (
        GEMINI_EXTRACTION_FALLBACKS,
        GEMINI_EXTRACTION_MODEL,
        GEMINI_EXTRACTION_TEMPERATURE,
    )
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _parse_json_object,
        _response_text,
    )

    ct = (content_type or "video").strip().lower()
    if ct not in ("video", "carousel"):
        ct = "video"

    compact = _compact_analysis_json(analysis_json)
    user_prompt = _build_user_prompt(ct, compact)

    if ct == "carousel":
        schema = CarouselClassificationBackfillLLM.model_json_schema()
        ResponseModel = CarouselClassificationBackfillLLM
    else:
        schema = VideoClassificationBackfillLLM.model_json_schema()
        ResponseModel = VideoClassificationBackfillLLM

    cfg = types.GenerateContentConfig(
        temperature=GEMINI_EXTRACTION_TEMPERATURE,
        max_output_tokens=2048,
        response_mime_type="application/json",
        response_json_schema=schema,
        system_instruction=_BACKFILL_SYSTEM_VI,
    )
    try:
        response = _generate_content_models(
            [user_prompt],
            primary_model=GEMINI_EXTRACTION_MODEL,
            fallbacks=GEMINI_EXTRACTION_FALLBACKS,
            config=cfg,
            call_site="classification_backfill",
        )
        text = _response_text(response)
        if not text.strip():
            logger.warning("[classification_backfill] empty Gemini response")
            return None
        parsed = _parse_json_object(text)
        validated = ResponseModel.model_validate(parsed)
    except Exception as exc:
        logger.warning("[classification_backfill] Gemini/validate failed: %s", exc)
        return None

    patch = validated.model_dump(mode="json", exclude_none=False)
    merged: dict[str, Any] = {**analysis_json, **patch}
    apply_fashion_commerce_niche_remap(merged)
    return merged


def _backfill_shadow_columns(
    merged_analysis: dict[str, Any],
    *,
    resolver_niche_id: int,
    video_id: str,
    content_type: str,
) -> dict[str, Any]:
    """Telemetry columns for ``video_corpus`` update.

    Prefer explicit ME-17 provenance (always ``gemini_two_axis``) while still
    emitting the same disagree/junction log signals as live ingest via
    ``_niche_resolution_shadow_fields``.
    """
    _ = _niche_resolution_shadow_fields(
        merged_analysis,
        resolver_niche_id,
        video_id=video_id,
        content_type=content_type,
    )
    nc = merged_analysis.get("niche_classification")
    if not isinstance(nc, dict):
        nc = {}
    try:
        conf = float(nc.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    slug_raw = nc.get("creator_niche_slug")
    slug = str(slug_raw).strip() if slug_raw is not None else ""
    inferred: int | None = CREATOR_NICHE_SLUG_TO_ID.get(slug)
    return {
        "niche_resolution_source": "gemini_two_axis",
        "niche_resolution_confidence": conf if conf > 0 else None,
        "inferred_creator_niche_id": inferred,
    }


def run_classification_backfill(
    *,
    client: Any | None = None,
    batch_size: int = 500,
    max_runtime_s: float = _DEFAULT_MAX_RUNTIME_S,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Process up to ``batch_size`` rows with ``niche_resolution_source IS NULL``.

    Newest first (``indexed_at DESC``) per plan. Stops early when
    ``max_runtime_s`` elapsed (Cloud Run safety).
    """
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    q = (
        client.table("video_corpus")
        .select(
            "video_id, ingest_loop_niche_id, content_type, analysis_json, "
            "indexed_at, content_class_id"
        )
        .is_("niche_resolution_source", "null")
        .not_.is_("analysis_json", "null")
        .order("indexed_at", desc=True)
        .limit(batch_size)
    )
    rows: list[dict[str, Any]] = (q.execute()).data or []

    stats: dict[str, Any] = {
        "ok": True,
        "candidates": len(rows),
        "processed": 0,
        "skipped_empty_analysis": 0,
        "failed_gemini": 0,
        "failed_update": 0,
        "dry_run": dry_run,
        "max_runtime_s": max_runtime_s,
        "stopped_reason": "complete",
    }

    if dry_run or not rows:
        if not rows:
            stats["stopped_reason"] = "no_rows"
        return stats

    started = time.monotonic()
    for row in rows:
        if time.monotonic() - started > max_runtime_s:
            stats["stopped_reason"] = "time_budget"
            break

        vid = str(row.get("video_id") or "")
        aj = row.get("analysis_json")
        if not isinstance(aj, dict) or not aj:
            stats["skipped_empty_analysis"] += 1
            continue

        ct = str(row.get("content_type") or "video")
        merged = backfill_row_with_gemini(aj, ct)
        if merged is None:
            stats["failed_gemini"] += 1
            continue

        resolver_nid = int(row.get("ingest_loop_niche_id") or 0)
        current_cc = row.get("content_class_id")
        if isinstance(current_cc, str) and current_cc.isdigit():
            current_cc = int(current_cc)
        elif not isinstance(current_cc, int):
            current_cc = None
        loop_creator_cn = creator_niche_id_for_legacy_niche(resolver_nid)
        resolved_cc = resolve_post_route_content_class_id(
            merged,
            route_content_class_id=current_cc,
            video_id=vid,
            loop_creator_niche_id=loop_creator_cn,
        )
        shadow = _backfill_shadow_columns(
            merged,
            resolver_niche_id=resolver_nid,
            video_id=vid,
            content_type=ct,
        )
        update_payload: dict[str, Any] = {"analysis_json": merged, **shadow}
        if resolved_cc is not None and resolved_cc != current_cc:
            update_payload["content_class_id"] = resolved_cc
        try:
            (
                client.table("video_corpus")
                .update(update_payload)
                .eq("video_id", vid)
                .execute()
            )
            stats["processed"] += 1
        except Exception as exc:
            logger.warning("[classification_backfill] update failed video_id=%s: %s", vid, exc)
            stats["failed_update"] += 1

    logger.info(
        "[classification_backfill] candidates=%d processed=%d "
        "failed_gemini=%d failed_update=%d reason=%s",
        stats["candidates"],
        stats["processed"],
        stats["failed_gemini"],
        stats["failed_update"],
        stats["stopped_reason"],
    )
    return stats


def run_fashion_commerce_remap_backfill(
    *,
    client: Any | None = None,
    batch_size: int = 500,
    max_runtime_s: float = _DEFAULT_MAX_RUNTIME_S,
    dry_run: bool = False,
    video_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Re-map misclassified business fashion-commerce rows already in ``video_corpus``."""
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    select_cols = (
        "video_id, ingest_loop_niche_id, content_type, analysis_json, "
        "content_class_id, inferred_creator_niche_id"
    )
    if video_ids:
        q = (
            client.table("video_corpus")
            .select(select_cols)
            .in_("video_id", video_ids)
            .not_.is_("analysis_json", "null")
        )
    else:
        q = (
            client.table("video_corpus")
            .select(select_cols)
            .not_.is_("analysis_json", "null")
            .or_("inferred_creator_niche_id.eq.9,content_class_id.in.(47,48,49)")
            .order("indexed_at", desc=True)
            .limit(batch_size)
        )
    rows: list[dict[str, Any]] = (q.execute()).data or []

    stats: dict[str, Any] = {
        "ok": True,
        "candidates": len(rows),
        "processed": 0,
        "skipped_no_remap": 0,
        "failed_update": 0,
        "dry_run": dry_run,
        "max_runtime_s": max_runtime_s,
        "stopped_reason": "complete",
        "video_ids_filter": video_ids,
    }

    if dry_run or not rows:
        if not rows:
            stats["stopped_reason"] = "no_rows"
        return stats

    started = time.monotonic()
    for row in rows:
        if time.monotonic() - started > max_runtime_s:
            stats["stopped_reason"] = "time_budget"
            break

        vid = str(row.get("video_id") or "")
        aj = row.get("analysis_json")
        if not isinstance(aj, dict) or not aj:
            stats["skipped_no_remap"] += 1
            continue

        merged = dict(aj)
        current_cc = row.get("content_class_id")
        if isinstance(current_cc, str) and current_cc.isdigit():
            current_cc = int(current_cc)
        elif not isinstance(current_cc, int):
            current_cc = None

        fashion_remap = apply_fashion_commerce_niche_remap(
            merged,
            video_id=vid,
            current_content_class_id=current_cc,
        )
        if not fashion_remap.remapped:
            stats["skipped_no_remap"] += 1
            continue

        resolver_nid = int(row.get("ingest_loop_niche_id") or 0)
        ct = str(row.get("content_type") or "video")
        shadow = _backfill_shadow_columns(
            merged,
            resolver_niche_id=resolver_nid,
            video_id=vid,
            content_type=ct,
        )
        update_payload: dict[str, Any] = {"analysis_json": merged, **shadow}
        if fashion_remap.content_class_id is not None:
            update_payload["content_class_id"] = fashion_remap.content_class_id

        if dry_run:
            stats["processed"] += 1
            continue

        try:
            (
                client.table("video_corpus")
                .update(update_payload)
                .eq("video_id", vid)
                .execute()
            )
            stats["processed"] += 1
        except Exception as exc:
            logger.warning(
                "[fashion_commerce_remap_backfill] update failed video_id=%s: %s",
                vid,
                exc,
            )
            stats["failed_update"] += 1

    logger.info(
        "[fashion_commerce_remap_backfill] candidates=%d processed=%d "
        "skipped_no_remap=%d failed_update=%d reason=%s",
        stats["candidates"],
        stats["processed"],
        stats["skipped_no_remap"],
        stats["failed_update"],
        stats["stopped_reason"],
    )
    return stats


def run_cross_niche_class_remap_backfill(
    *,
    client: Any | None = None,
    batch_size: int = 500,
    max_runtime_s: float = _DEFAULT_MAX_RUNTIME_S,
    dry_run: bool = False,
    video_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Re-align ``content_class_id`` when Gemini topic disagrees with HI-11 loop class."""
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    select_cols = (
        "video_id, ingest_loop_niche_id, content_type, analysis_json, "
        "content_class_id, inferred_creator_niche_id, niche_resolution_confidence"
    )
    if video_ids:
        q = (
            client.table("video_corpus")
            .select(select_cols)
            .in_("video_id", video_ids)
            .not_.is_("analysis_json", "null")
        )
    else:
        q = (
            client.table("video_corpus")
            .select(select_cols)
            .not_.is_("analysis_json", "null")
            .gte("niche_resolution_confidence", 0.6)
            .order("indexed_at", desc=True)
            .limit(batch_size * 4)
        )
    rows: list[dict[str, Any]] = (q.execute()).data or []

    stats: dict[str, Any] = {
        "ok": True,
        "candidates": len(rows),
        "processed": 0,
        "skipped_no_remap": 0,
        "failed_update": 0,
        "dry_run": dry_run,
        "max_runtime_s": max_runtime_s,
        "stopped_reason": "complete",
        "video_ids_filter": video_ids,
    }

    if dry_run or not rows:
        if not rows:
            stats["stopped_reason"] = "no_rows"
        return stats

    started = time.monotonic()
    for row in rows:
        if stats["processed"] >= batch_size:
            stats["stopped_reason"] = "batch_cap"
            break
        if time.monotonic() - started > max_runtime_s:
            stats["stopped_reason"] = "time_budget"
            break

        vid = str(row.get("video_id") or "")
        aj = row.get("analysis_json")
        if not isinstance(aj, dict) or not aj:
            stats["skipped_no_remap"] += 1
            continue

        merged = dict(aj)
        current_cc = row.get("content_class_id")
        if isinstance(current_cc, str) and current_cc.isdigit():
            current_cc = int(current_cc)
        elif not isinstance(current_cc, int):
            current_cc = None

        loop_nid = int(row.get("ingest_loop_niche_id") or 0)
        loop_creator_cn = creator_niche_id_for_legacy_niche(loop_nid)
        cross_remap = apply_cross_niche_class_remap(
            merged,
            video_id=vid,
            current_content_class_id=current_cc,
            loop_creator_niche_id=loop_creator_cn,
        )
        if not cross_remap.remapped:
            stats["skipped_no_remap"] += 1
            continue

        shadow = _backfill_shadow_columns(
            merged,
            resolver_niche_id=loop_nid,
            video_id=vid,
            content_type=str(row.get("content_type") or "video"),
        )
        update_payload: dict[str, Any] = {"analysis_json": merged, **shadow}
        if cross_remap.content_class_id is not None:
            update_payload["content_class_id"] = cross_remap.content_class_id

        if dry_run:
            stats["processed"] += 1
            continue

        try:
            (
                client.table("video_corpus")
                .update(update_payload)
                .eq("video_id", vid)
                .execute()
            )
            stats["processed"] += 1
        except Exception as exc:
            logger.warning(
                "[cross_niche_remap_backfill] update failed video_id=%s: %s",
                vid,
                exc,
            )
            stats["failed_update"] += 1

    logger.info(
        "[cross_niche_remap_backfill] candidates=%d processed=%d "
        "skipped_no_remap=%d failed_update=%d reason=%s",
        stats["candidates"],
        stats["processed"],
        stats["skipped_no_remap"],
        stats["failed_update"],
        stats["stopped_reason"],
    )
    return stats
