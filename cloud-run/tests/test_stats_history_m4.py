"""Phase 2b — §4.7 M4 stats_history + distribution_spike_then_flat signal."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from getviews_pipeline.signals.distribution import extract_distribution_spike_then_flat_signal
from getviews_pipeline.stats_history_m4 import (
    compute_distribution_shape,
    engagement_rate_pct,
    history_phases,
    make_stats_snapshot,
    select_stats_history_refetch_candidates,
)


def _full_history_spike_flat() -> list[dict]:
    return [
        make_stats_snapshot(views=1000, likes=50, comments=20, shares=10, phase="t0"),
        make_stats_snapshot(views=2500, likes=50, comments=25, shares=10, phase="t6h"),
        make_stats_snapshot(views=2600, likes=50, comments=2, shares=8, phase="t24h"),
    ]


def test_compute_distribution_shape_spike_then_flat_er_drop():
    assert compute_distribution_shape(_full_history_spike_flat()) == "spike_then_flat"


def test_compute_distribution_shape_no_spike():
    history = [
        make_stats_snapshot(views=1000, likes=50, comments=20, shares=10, phase="t0"),
        make_stats_snapshot(views=1200, likes=60, comments=22, shares=11, phase="t6h"),
        make_stats_snapshot(views=1300, likes=65, comments=24, shares=12, phase="t24h"),
    ]
    assert compute_distribution_shape(history) is None


def test_compute_distribution_shape_incomplete_history():
    assert compute_distribution_shape([make_stats_snapshot(views=1, likes=0, comments=0, shares=0, phase="t0")]) is None


def test_distribution_spike_then_flat_signal_fires():
    history = _full_history_spike_flat()
    ctx = {
        "user_stats": {
            "stats_history": history,
            "distribution_shape": "spike_then_flat",
        }
    }
    sigs = extract_distribution_spike_then_flat_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "distribution_spike_then_flat"
    assert sigs[0].section_id == "boost_attribution"
    assert "có dấu hiệu" in sigs[0].claim.lower()


def test_distribution_spike_then_flat_signal_from_computed_shape():
    history = _full_history_spike_flat()
    ctx = {"user_stats": {"stats_history": history}}
    sigs = extract_distribution_spike_then_flat_signal(ctx)
    assert any(s.id == "distribution_spike_then_flat" for s in sigs)


def test_select_refetch_candidates_t6h():
    now = datetime(2026, 5, 23, 12, 0, tzinfo=UTC)
    first_seen = (now - timedelta(hours=7)).isoformat()
    row = {
        "video_id": "v1",
        "tiktok_url": "https://tiktok.com/@x/video/v1",
        "first_seen_at": first_seen,
        "stats_history": [
            make_stats_snapshot(views=100, likes=1, comments=1, shares=0, phase="t0"),
        ],
    }

    class _Chain:
        def select(self, *_a, **_k):
            return self

        def gte(self, *_a, **_k):
            return self

        @property
        def not_(self):
            return self

        def is_(self, *_a, **_k):
            return self

        def neq(self, *_a, **_k):
            return self

        def order(self, *_a, **_k):
            return self

        def limit(self, *_a, **_k):
            return self

        def execute(self):
            class _Res:
                data = [row]

            return _Res()

    class _Client:
        def table(self, _name):
            return _Chain()

    work = select_stats_history_refetch_candidates(_Client(), limit=10, now=now)
    assert len(work) == 1
    assert work[0][1] == "t6h"


def test_history_phases():
    history = [
        make_stats_snapshot(views=1, likes=0, comments=0, shares=0, phase="t0"),
        make_stats_snapshot(views=2, likes=0, comments=0, shares=0, phase="t6h"),
    ]
    assert history_phases(history) == {"t0", "t6h"}


def test_engagement_rate_pct_matches_ingest_scale():
    """M4 refetch must write 0–100% ER like corpus_ingest._safe_engagement_rate."""
    assert engagement_rate_pct(1000, 50, 20, 10) == 8.0
    assert engagement_rate_pct(0, 50, 20, 10) == 0.0
    assert engagement_rate_pct(10, 1000, 1000, 1000) == 100.0
