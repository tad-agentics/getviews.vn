"""Shared extraction quality classification (TD-7 batch + live parity)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Literal

logger = logging.getLogger(__name__)

ExtractionQuality = Literal["ok", "degraded_scenes", "degraded"]

_SUSPECT_BOOST = frozenset({"suspect_low", "suspect_medium"})


def classify_extraction_quality(
    analysis_json: dict[str, Any],
    *,
    content_type: str = "video",
) -> ExtractionQuality:
    """Return extraction_quality for video_corpus from analysis_json heuristics."""
    if content_type != "video":
        return "ok"

    scenes: list[dict[str, Any]] = analysis_json.get("scenes") or []
    if not isinstance(scenes, list):
        scenes = []

    video_duration_approx = scenes[-1].get("end") if scenes else None
    try:
        duration_f = float(video_duration_approx) if video_duration_approx is not None else 0.0
    except (TypeError, ValueError):
        duration_f = 0.0

    if duration_f > 10 and len(scenes) <= 1:
        return "degraded_scenes"

    tps = analysis_json.get("transitions_per_second") or 0
    try:
        tps_f = float(tps)
    except (TypeError, ValueError):
        tps_f = 0.0

    if len(scenes) > 1 and tps_f == 0:
        return "degraded"

    return "ok"


def is_clean_boost_attribution(attribution: str | None) -> bool:
    return (attribution or "unknown").strip() not in _SUSPECT_BOOST


def is_suspect_low_attribution(attribution: str | None) -> bool:
    return (attribution or "").strip() == "suspect_low"


def peer_row_days_ago(row: dict[str, Any]) -> int:
    """Days since publish/index; prefers ``_corpus_days_ago`` when annotated."""
    raw = row.get("_corpus_days_ago")
    if raw is not None:
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            pass
    now = datetime.now(UTC)
    for field in ("posted_at", "indexed_at"):
        ts = row.get(field)
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return max(0, int((now - dt).total_seconds() // 86400))
        except (TypeError, ValueError, OSError):
            continue
    return 60


def peer_recency_tiebreak(days_ago: int) -> int:
    """Gentle recency bucket (higher = newer). Last sort key only."""
    days = max(0, int(days_ago))
    if days <= 14:
        return 3
    if days <= 30:
        return 2
    if days <= 60:
        return 1
    return 0


def peer_pool_quality_rank(row: dict[str, Any]) -> tuple[int, int, float, float, int]:
    """Sort key: prefer clean boost, ok extraction, higher breakout/ER, then recency."""
    boost = str(row.get("boost_attribution") or "unknown")
    if boost in _SUSPECT_BOOST:
        boost_rank = 2 if boost == "suspect_low" else 3
    else:
        boost_rank = 0

    eq = str(row.get("extraction_quality") or "ok")
    if eq == "degraded":
        eq_rank = 2
    elif eq == "degraded_scenes":
        eq_rank = 1
    else:
        eq_rank = 0

    breakout = float(row.get("breakout_multiplier") or row.get("breakout_ratio") or 0)
    er = float(row.get("engagement_rate") or 0)
    recency = peer_recency_tiebreak(peer_row_days_ago(row))
    return (boost_rank, eq_rank, -breakout, -er, -recency)
