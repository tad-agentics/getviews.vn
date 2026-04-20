"""Phase C.0.3 — adaptive corpus window from ``video_corpus`` (service role).

Floors match ``phase-c-plan.md`` §C.0.3: Pattern 30, Ideas 60, Timing 80.
Prefer 7d → widen to 14d → 30d until the floor is met.
"""

from __future__ import annotations

import logging
from typing import Literal

from getviews_pipeline.supabase_client import get_service_client

logger = logging.getLogger(__name__)

# §C.0.3 sample_size floors (minimum posts in window for “full” report behaviour)
PATTERN_SAMPLE_FLOOR = 30
IDEAS_SAMPLE_FLOOR = 60
TIMING_SAMPLE_FLOOR = 80

ReportKind = Literal["pattern", "ideas", "timing"]


def count_video_corpus_for_niche(niche_id: int, days: int) -> int:
    """Count rows in ``video_corpus`` for ``niche_id`` in the last ``days`` days."""
    if niche_id <= 0:
        return 0
    try:
        sb = get_service_client()
        res = (
            sb.table("video_corpus")
            .select("video_id", count="exact")
            .eq("niche_id", niche_id)
            .gte("indexed_at", f"now() - interval '{days} days'")
            .execute()
        )
        return int(res.count or 0)
    except Exception as exc:  # pragma: no cover - network / schema
        logger.warning("[adaptive_window] count failed niche_id=%s days=%s: %s", niche_id, days, exc)
        return 0


def choose_adaptive_window_days(niche_id: int, report_kind: ReportKind) -> int:
    """Return 7, 14, or 30 — smallest window where corpus count ≥ format floor.

    Unknown/no niche → **7** (caller uses stubs; strip still reflects policy).
    If all windows are below floor, returns **30** (widest honest window).
    """
    floors: dict[ReportKind, int] = {
        "pattern": PATTERN_SAMPLE_FLOOR,
        "ideas": IDEAS_SAMPLE_FLOOR,
        "timing": TIMING_SAMPLE_FLOOR,
    }
    floor = floors.get(report_kind, PATTERN_SAMPLE_FLOOR)
    if niche_id <= 0:
        return 7

    for days in (7, 14, 30):
        n = count_video_corpus_for_niche(niche_id, days)
        if n >= floor:
            return days
    return 30
