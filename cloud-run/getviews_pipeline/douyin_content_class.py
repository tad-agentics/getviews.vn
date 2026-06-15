"""Resolve ``content_class_id`` for Douyin corpus rows (Phase 2a).

Reuses the same junction lookup as TikTok corpus ingest
(``content_class_id_for_creator_niche_format``) on HI-9
``niche_classification`` fields already present in ``analysis_json``.
"""

from __future__ import annotations

from typing import Any

from getviews_pipeline.junction_content_class import (
    content_class_id_for_creator_niche_format,
)
from getviews_pipeline.profile_niches import CREATOR_NICHE_SLUG_TO_ID

# douyin_niche_taxonomy.id → default creator_niche_id for fallback when
# format_axis is missing (maps through douyin_match cultural peers).
_DOUYIN_NICHE_TO_CREATOR_NICHE: dict[int, int] = {
    1: 10,   # wellness / gym
    2: 1,    # beauty
    3: 4,    # lifestyle
    4: 11,   # travel
    5: 3,    # food
    6: 8,    # tech_gaming
    7: 2,    # fashion
    8: 16,   # real_estate
    9: 9,    # business
    10: 6,   # family
}


def _format_axis_from_analysis(analysis_json: dict[str, Any]) -> str | None:
    nc = analysis_json.get("niche_classification")
    if not isinstance(nc, dict):
        return None
    fmt = nc.get("format_axis") or nc.get("carousel_format_axis")
    if isinstance(fmt, str) and fmt.strip():
        return fmt.strip()
    return None


def _creator_niche_id_from_analysis(analysis_json: dict[str, Any]) -> int | None:
    nc = analysis_json.get("niche_classification")
    if not isinstance(nc, dict):
        return None
    slug = str(nc.get("creator_niche_slug") or "").strip().lower()
    if not slug:
        return None
    return CREATOR_NICHE_SLUG_TO_ID.get(slug)


def resolve_content_class_from_analysis(
    analysis_json: dict[str, Any],
    *,
    douyin_niche_id: int | None = None,
) -> tuple[int | None, str | None]:
    """Return ``(content_class_id, content_format)`` from extraction JSON.

    Falls back to douyin flat ``niche_id`` → creator niche + ``vlog_daily``
    when ``format_axis`` is absent (pre-HI-9 rows).
    """
    if not isinstance(analysis_json, dict):
        analysis_json = {}

    fmt = _format_axis_from_analysis(analysis_json)
    cn_id = _creator_niche_id_from_analysis(analysis_json)

    if cn_id is None and douyin_niche_id is not None:
        cn_id = _DOUYIN_NICHE_TO_CREATOR_NICHE.get(int(douyin_niche_id))

    if cn_id is None:
        return None, fmt

    if not fmt:
        fmt = "vlog_daily"

    cc_id = content_class_id_for_creator_niche_format(cn_id, fmt)
    return cc_id, fmt
