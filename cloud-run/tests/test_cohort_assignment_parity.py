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
    monkeypatch.setattr(
        "getviews_pipeline.video_niche_benchmark.settings.live_cohort_class_first",
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


def test_fetch_video_benchmark_legacy_prefers_niche_when_class_first_off(monkeypatch):
    monkeypatch.setattr(
        "getviews_pipeline.video_niche_benchmark.settings.live_cohort_class_first",
        False,
    )

    class FakeSb:
        def __init__(self) -> None:
            self.last_table: str | None = None

        def table(self, name: str):
            self.last_table = name
            return self

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def execute(self):
            if self.last_table == "niche_intelligence":
                return type("R", (), {"data": [{
                    "niche_id": 3,
                    "sample_size": 100,
                    "median_views": 8000,
                    "median_er": 3.0,
                    "avg_engagement_rate": 3.0,
                    "computed_at": "2026-01-01",
                }]})()
            return type("R", (), {"data": [{
                "content_class_id": 7,
                "sample_size": 40,
                "median_views": 12000,
                "median_er": 4.0,
                "avg_engagement_rate": 4.0,
                "computed_at": "2026-01-01",
            }]})()

    row, axis = fetch_video_benchmark_with_axis(
        FakeSb(),
        niche_id=3,
        content_class_id=7,
    )
    assert axis == "niche"
    assert row is not None
    assert int(row.get("niche_id") or 0) == 3


def test_fetch_video_benchmark_legacy_queries_niche_once_on_miss(monkeypatch):
    monkeypatch.setattr(
        "getviews_pipeline.video_niche_benchmark.settings.live_cohort_class_first",
        False,
    )

    niche_calls = 0
    class_calls = 0

    class FakeSb:
        def __init__(self) -> None:
            self.last_table: str | None = None

        def table(self, name: str):
            self.last_table = name
            return self

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def execute(self):
            nonlocal niche_calls, class_calls
            if self.last_table == "niche_intelligence":
                niche_calls += 1
                return type("R", (), {"data": []})()
            if self.last_table == "content_class_intelligence":
                class_calls += 1
                return type("R", (), {"data": []})()
            return type("R", (), {"data": []})()

    row, axis = fetch_video_benchmark_with_axis(
        FakeSb(),
        niche_id=3,
        content_class_id=7,
    )
    assert row is None
    assert axis == "none"
    assert niche_calls == 1
    assert class_calls == 1
