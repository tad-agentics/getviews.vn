"""Phase 2b — live/batch cohort assignment parity (env-gated contract)."""

from __future__ import annotations

from getviews_pipeline.corpus_ingest import _should_skip_existing_for_dedup
from getviews_pipeline.corpus_instructiveness import (
    ContentClassViewStats,
    IngestBatchContext,
    NicheViewStats,
    corpus_score_cohort,
    use_class_score_cohort,
)
from getviews_pipeline.corpus_instructiveness import _breakout_for_aweme as breakout_fn
from getviews_pipeline.video_niche_benchmark import fetch_video_benchmark_with_axis


def test_corpus_score_cohort_default_class():
    assert corpus_score_cohort() == "class"
    assert use_class_score_cohort() is True


def test_breakout_uses_class_p50_when_class_cohort(monkeypatch):
    monkeypatch.setattr(
        "getviews_pipeline.corpus_instructiveness.use_class_score_cohort",
        lambda: True,
    )
    ctx = IngestBatchContext(
        class_stats={
            42: ContentClassViewStats(content_class_id=42, p50_views=10_000, corpus_count=50),
        },
        niche_stats={3: NicheViewStats(niche_id=3, p50_views=100_000, corpus_count=200)},
    )
    aweme = {
        "aweme_id": "1",
        "author": {"follower_count": 5_000_000},
        "authorStats": {},
        "statistics": {"play_count": 50_000},
    }
    br, src = breakout_fn(
        aweme, 50_000, niche_id=3, ctx=ctx, content_class_id=42,
    )
    assert br == 5.0
    assert src == "class_p50"


def test_class_dedup_allows_reupsert_when_class_changes(monkeypatch):
    monkeypatch.setattr(
        "getviews_pipeline.corpus_ingest._corpus_ingest_loop_mode",
        lambda: "class",
    )
    existing = {"vid1"}
    assert _should_skip_existing_for_dedup(
        "vid1",
        existing,
        loop_content_class_id=10,
        existing_class_by_video={"vid1": 5},
    ) is False
    assert _should_skip_existing_for_dedup(
        "vid1",
        existing,
        loop_content_class_id=5,
        existing_class_by_video={"vid1": 5},
    ) is True


def test_fetch_video_benchmark_class_first_prefers_class(monkeypatch):
    # Round B (commit 76f07b6) made class-first unconditional in
    # ``fetch_video_benchmark_with_axis`` — the function no longer reads
    # ``settings.live_cohort_class_first``. The flag still exists in
    # ``getviews_pipeline.settings`` (used by trend_velocity/morning_ritual),
    # so patch it there rather than the removed
    # ``video_niche_benchmark.settings`` attribute.
    monkeypatch.setattr(
        "getviews_pipeline.settings.settings.live_cohort_class_first",
        True,
    )

    class FakeSb:
        def table(self, name: str):
            return self

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def execute(self):
            class R:
                data = [{
                    "content_class_id": 7,
                    "sample_size": 40,
                    "median_views": 12000,
                    "median_er": 4.0,
                    "avg_engagement_rate": 4.0,
                    "computed_at": "2026-01-01",
                }]

            return R()

    row, axis = fetch_video_benchmark_with_axis(
        FakeSb(),
        niche_id=3,
        content_class_id=7,
    )
    assert axis == "content_class"
    assert row is not None


# NOTE: the former ``..._legacy_prefers_niche_when_class_first_off`` test was
# removed — Round B (commit 76f07b6) made class-first unconditional, so the
# "flag off → niche-first" path no longer exists. The class-first-wins contract
# is covered by ``test_fetch_video_benchmark_class_first_prefers_class`` above.


def test_fetch_video_benchmark_returns_none_when_all_cohorts_miss():
    # Round B: ``fetch_video_benchmark_with_axis`` tries content_class (tier →
    # class) then the niche shim. When every cohort misses it must return
    # ``(None, "none")`` — graceful miss, no exception. The legacy
    # ``niche_intelligence`` MV was dropped, so the niche shim no longer queries
    # that table directly.
    class FakeSb:
        def table(self, name: str):
            return self

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def execute(self):
            return type("R", (), {"data": []})()

    row, axis = fetch_video_benchmark_with_axis(
        FakeSb(),
        niche_id=3,
        content_class_id=7,
    )
    assert row is None
    assert axis == "none"
