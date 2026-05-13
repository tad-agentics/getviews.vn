"""Performance-tier classification and KPI enrichment service.

Phase 1.1: thin re-export from pipelines.py so callers can migrate to
services.performance without a code change on their end.

Phase 3 (two-core split): this module will own the actual performance-tier
and KPI-enrichment logic as part of run_video_diagnosis_core.
"""

from __future__ import annotations

from getviews_pipeline.pipelines import (  # noqa: F401
    _estimate_er_percentile_rank,
    _truncate_transcripts,
    classify_performance_tier_corpus,
    compute_bright_spot_signal,
    compute_view_scenarios,
    enrich_format_cards_from_corpus,
    refine_performance_tier,
)

# Phase 5.4 — quality tier helpers re-exported here for convenience.
from getviews_pipeline.services.corpus_quality import (  # noqa: F401
    is_cohort_eligible,
    quality_tier,
)

__all__ = [
    "classify_performance_tier_corpus",
    "compute_bright_spot_signal",
    "compute_view_scenarios",
    "_estimate_er_percentile_rank",
    "_truncate_transcripts",
    "enrich_format_cards_from_corpus",
    "refine_performance_tier",
    "is_cohort_eligible",
    "quality_tier",
]
