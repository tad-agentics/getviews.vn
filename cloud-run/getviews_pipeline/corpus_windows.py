"""Centralized corpus recency windows (benchmark MV vs peer pool vs reports).

Split by design:
  - ``corpus_benchmark_window_days`` — content_class_intelligence MV base CTE
  - ``corpus_reference_fetch_days`` — PostgREST pool query (indexed_at)
  - ``corpus_reference_pick_days`` — proximity pick filter (posted_at → indexed_at)
  - ``corpus_citation_window_days`` — get_corpus_count + synthesis citation copy
  - ``corpus_adaptive_max_days`` — adaptive report window ladder cap

``batch_recency_days`` (ingest discovery) stays separate — it controls which
TikTok posts enter the nightly pool, not which indexed rows are readable.
"""

from __future__ import annotations

from getviews_pipeline.settings import settings


def corpus_benchmark_window_days() -> int:
    return settings.corpus_benchmark_window_days


def corpus_reference_fetch_days() -> int:
    return settings.corpus_reference_fetch_days


def corpus_reference_pick_days() -> int:
    return settings.corpus_reference_pick_days


def corpus_citation_window_days() -> int:
    return settings.corpus_citation_window_days


def corpus_adaptive_max_days() -> int:
    return settings.corpus_adaptive_max_days
