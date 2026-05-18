"""§8 Douyin — heuristic match TikTok analysis to ``douyin_video_corpus`` (Sprint 9).

Uses mapped creator niche → Douyin ``niche_id`` plus matching ``hook_type``.
Pipeline thaw / cron TikHub cost gate is separate — this module only reads Supabase.

Env: ``GETVIEWS_DOUYIN_ORIGIN_MATCH`` = ``0`` disables enrichment (default on).
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Map CreatorNicheSlug (HI-9) → ``douyin_niche_taxonomy.id`` (approximate cultural peers).
_CREATOR_SLUG_TO_DOUYIN_NICHE_ID: dict[str, int] = {
    "wellness": 1,
    "beauty": 2,
    "lifestyle": 3,
    "travel": 4,
    "food": 5,
    "tech_gaming": 6,
    "fashion": 7,
    "pets_home": 8,
    "business": 9,
    "family": 10,
    "gym_fitness": 1,
    "education": 6,
    "comedy": 3,
    "music_dance": 3,
    "real_estate": 8,
    "auto": 6,
}


def _douyin_match_enabled() -> bool:
    raw = (os.environ.get("GETVIEWS_DOUYIN_ORIGIN_MATCH") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def map_creator_niche_to_douyin_niche_id(slug: str | None) -> int | None:
    if not slug:
        return None
    key = str(slug).strip().lower()
    return _CREATOR_SLUG_TO_DOUYIN_NICHE_ID.get(key)


def _parse_ts(val: str | None) -> datetime | None:
    if not val:
        return None
    s = str(val).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None


def _iso_dateish(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).date().isoformat()


def lag_days_vn_after_douyin(douyin_ts: datetime | None, vn_ts: datetime | None) -> int | None:
    if douyin_ts is None or vn_ts is None:
        return None
    delta = vn_ts - douyin_ts
    return int(delta.total_seconds() // 86400)


def adoption_stage_from_lag(lag_days: int | None) -> str | None:
    if lag_days is None:
        return None
    if lag_days < 0:
        return "leading_edge"
    if lag_days <= 7:
        return "leading_edge"
    if lag_days <= 21:
        return "mid_curve"
    return "trailing"


def migration_fit_from_adapt_level(level: str | None) -> str:
    s = str(level or "").strip().lower()
    if s == "green":
        return "clean_adapt"
    if s == "yellow":
        return "needs_localization"
    if s == "red":
        return "poor_fit"
    return "unknown"


def fetch_douyin_peer_row(sb: Any, *, niche_id: int, hook_type: str) -> dict[str, Any] | None:
    """Return one corpus row: same Douyin niche + hook_type, highest views."""

    ht = str(hook_type).strip().lower().replace("-", "_")
    try:
        res = (
            sb.table("douyin_video_corpus")
            .select("video_id, posted_at, indexed_at, adapt_level, views")
            .eq("niche_id", niche_id)
            .eq("hook_type", ht)
            .order("views", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("[douyin_match] supabase query failed")
        return None
    rows = res.data or []
    return rows[0] if rows else None


def enrich_analysis_with_douyin_match(
    analysis: dict[str, Any],
    user_stats: dict[str, Any],
    sb: Any,
) -> None:
    """Mutate *analysis* when a peer exists and matcher is enabled."""

    if not _douyin_match_enabled():
        return
    if not isinstance(analysis, dict):
        return
    if analysis.get("douyin_origin"):
        return

    hook = analysis.get("hook_analysis")
    if not isinstance(hook, dict):
        return
    hook_type = str(hook.get("hook_type") or "").strip().lower()
    if not hook_type or hook_type in ("none", "other"):
        return

    nc = analysis.get("niche_classification")
    slug = ""
    if isinstance(nc, dict):
        slug = str(nc.get("creator_niche_slug") or "").strip().lower()
    niche_id = map_creator_niche_to_douyin_niche_id(slug or None)
    if niche_id is None:
        return

    row = fetch_douyin_peer_row(sb, niche_id=niche_id, hook_type=hook_type)
    if not row or not row.get("video_id"):
        return

    dy_raw = row.get("posted_at") or row.get("indexed_at")
    vn_raw = user_stats.get("posted_at") if isinstance(user_stats, dict) else None
    dy_dt = _parse_ts(str(dy_raw) if dy_raw is not None else None)
    vn_dt = _parse_ts(str(vn_raw) if vn_raw is not None else None)
    lag = lag_days_vn_after_douyin(dy_dt, vn_dt)
    stage = adoption_stage_from_lag(lag)

    analysis["douyin_origin"] = {
        "douyin_aweme_id": str(row["video_id"]),
        "first_seen_douyin": _iso_dateish(dy_dt),
        "first_seen_vietnam": _iso_dateish(vn_dt),
        "lag_days": lag,
    }
    if stage:
        analysis["vietnam_adoption_stage"] = stage
    analysis["migration_fit_assessment"] = migration_fit_from_adapt_level(
        str(row.get("adapt_level") or "") or None
    )
