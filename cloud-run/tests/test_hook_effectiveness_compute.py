"""Tests for the ``hook_effectiveness`` weekly aggregator.

Pure logic tests — no DB. The computational core is
``_compute_buckets`` + ``_trend_direction``; the full ``run_hook_
effectiveness`` is covered by a mocked-client integration case.

Each case pins a behaviour the state-of-corpus audit (Appendix B
Gap 1) identified as a hard requirement for unblocking Pattern +
Ideas reports.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

from getviews_pipeline.hook_effectiveness_compute import (
    SAMPLE_FLOOR,
    _compute_buckets,
    _trend_direction,
    run_hook_effectiveness,
)


def _video(
    *,
    niche_id: int = 1,
    hook_type: str = "question",
    views: int = 1000,
    engagement_rate: float | None = 0.05,
    save_rate: float | None = 0.03,
) -> dict[str, Any]:
    return {
        "niche_id": niche_id,
        "hook_type": hook_type,
        "views": views,
        "engagement_rate": engagement_rate,
        "save_rate": save_rate,
    }


# ── _compute_buckets ──────────────────────────────────────────────────────


def test_basic_bucket_averages_correctly() -> None:
    rows = [
        _video(views=1000, engagement_rate=0.04, save_rate=0.02),
        _video(views=2000, engagement_rate=0.06, save_rate=0.04),
        _video(views=1500, engagement_rate=0.05, save_rate=0.03),
    ]
    buckets = _compute_buckets(rows)
    assert (1, "question") in buckets
    b = buckets[(1, "question")]
    assert b["sample_size"] == 3
    assert b["avg_views"] == 1500
    # engagement_rate mean = (0.04 + 0.06 + 0.05) / 3 = 0.05
    assert b["avg_engagement_rate"] == 0.05
    # save_rate mean = (0.02 + 0.04 + 0.03) / 3 = 0.03
    assert b["avg_completion_rate"] == 0.03


def test_below_sample_floor_is_dropped() -> None:
    """Buckets under SAMPLE_FLOOR (3) should not appear in output."""
    rows = [_video(hook_type="rare") for _ in range(SAMPLE_FLOOR - 1)]
    buckets = _compute_buckets(rows)
    assert (1, "rare") not in buckets


def test_exactly_sample_floor_is_kept() -> None:
    """Boundary: n = SAMPLE_FLOOR exactly is accepted."""
    rows = [_video(hook_type="boundary") for _ in range(SAMPLE_FLOOR)]
    buckets = _compute_buckets(rows)
    assert (1, "boundary") in buckets


def test_null_engagement_and_save_rate_yield_none_averages() -> None:
    """When every row in a bucket has null rates, the avg is None
    (not 0 — avoids misleading downstream rankings)."""
    rows = [_video(engagement_rate=None, save_rate=None) for _ in range(3)]
    buckets = _compute_buckets(rows)
    b = buckets[(1, "question")]
    assert b["avg_engagement_rate"] is None
    assert b["avg_completion_rate"] is None
    # avg_views still computed (views is required, not nullable in schema)
    assert b["avg_views"] == 1000


def test_mixed_null_rates_average_the_populated_ones() -> None:
    """Rows with null rates are ignored in the average; populated rows
    still contribute. Protects against a single corrupt row dragging
    the whole bucket to None."""
    rows = [
        _video(engagement_rate=0.04, save_rate=None),
        _video(engagement_rate=0.06, save_rate=0.03),
        _video(engagement_rate=None, save_rate=0.05),
    ]
    buckets = _compute_buckets(rows)
    b = buckets[(1, "question")]
    # engagement: mean of 0.04 and 0.06 → 0.05
    assert b["avg_engagement_rate"] == 0.05
    # save_rate: mean of 0.03 and 0.05 → 0.04
    assert b["avg_completion_rate"] == 0.04


def test_zero_views_row_does_not_drag_avg() -> None:
    """Rows with views=0 are skipped from the avg_views computation
    so a single broken row doesn't pull a healthy bucket to zero."""
    rows = [
        _video(views=0),
        _video(views=1000),
        _video(views=2000),
        _video(views=3000),
    ]
    buckets = _compute_buckets(rows)
    b = buckets[(1, "question")]
    # avg_views = (1000 + 2000 + 3000) / 3 = 2000, not 1500
    assert b["avg_views"] == 2000
    # sample_size is still 4 (the row counts for bucket membership)
    assert b["sample_size"] == 4


def test_bucket_with_only_zero_views_is_dropped() -> None:
    """If every row in a bucket has views=0, we can't compute
    avg_views, so the bucket is skipped entirely."""
    rows = [_video(views=0) for _ in range(3)]
    buckets = _compute_buckets(rows)
    assert (1, "question") not in buckets


def test_multiple_niches_and_hooks_separately_bucketed() -> None:
    """(niche_id, hook_type) is the grouping key — don't bleed."""
    rows = (
        [_video(niche_id=1, hook_type="question", views=1000) for _ in range(3)]
        + [_video(niche_id=1, hook_type="shock_stat", views=5000) for _ in range(3)]
        + [_video(niche_id=2, hook_type="question", views=500) for _ in range(3)]
    )
    buckets = _compute_buckets(rows)
    assert buckets[(1, "question")]["avg_views"] == 1000
    assert buckets[(1, "shock_stat")]["avg_views"] == 5000
    assert buckets[(2, "question")]["avg_views"] == 500


# ── _trend_direction ──────────────────────────────────────────────────────


def test_trend_rising_above_10_pct() -> None:
    assert _trend_direction(current_avg=1200, prior_avg=1000) == "rising"


def test_trend_declining_below_negative_10_pct() -> None:
    assert _trend_direction(current_avg=800, prior_avg=1000) == "declining"


def test_trend_stable_inside_10_pct_band() -> None:
    assert _trend_direction(current_avg=1050, prior_avg=1000) == "stable"
    assert _trend_direction(current_avg=950, prior_avg=1000) == "stable"


def test_trend_stable_when_no_prior_data() -> None:
    """Brand-new buckets (no prior window) must return stable — not
    claim a direction they can't justify."""
    assert _trend_direction(current_avg=1000, prior_avg=0) == "stable"


def test_trend_boundary_exactly_10_pct_is_stable() -> None:
    """Strict inequality — exactly +10% is stable, not rising."""
    assert _trend_direction(current_avg=1100, prior_avg=1000) == "stable"
    assert _trend_direction(current_avg=900, prior_avg=1000) == "stable"


# ── run_hook_effectiveness — integration with mocked client ─────────────


def _mock_client_with_rows(
    current_rows: list[dict[str, Any]],
    prior_rows: list[dict[str, Any]],
) -> MagicMock:
    """Build a mock Supabase client that returns ``current_rows`` for
    the first ``.execute()`` call and ``prior_rows`` for the second."""
    client = MagicMock()

    select_chain = MagicMock()
    select_chain.not_.is_.return_value.gte.return_value.execute.side_effect = [
        MagicMock(data=current_rows),
    ]
    # Prior-window query has an additional ``.lt()`` call before execute.
    select_chain.not_.is_.return_value.gte.return_value.lt.return_value.execute.side_effect = [
        MagicMock(data=prior_rows),
    ]

    client.table.return_value.select.return_value = select_chain
    client.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
    return client


def test_run_end_to_end_upserts_buckets() -> None:
    """Happy path: enough rows in current window → upsert fires with
    the right shape + on_conflict key."""
    now = datetime.now(timezone.utc)
    current = [_video() for _ in range(3)]
    prior = [_video(views=800) for _ in range(3)]
    # Tag with indexed_at so the date filter doesn't blow up (the mock
    # doesn't actually filter, it just returns whatever we set).
    for r in current:
        r["indexed_at"] = now.isoformat()
    for r in prior:
        r["indexed_at"] = (now - timedelta(days=40)).isoformat()

    client = _mock_client_with_rows(current, prior)
    result = run_hook_effectiveness(client=client)

    assert result["upserted"] == 1  # one bucket: (1, "question")
    assert result["current_buckets"] == 1
    assert result["prior_buckets"] == 1
    # on_conflict key uses the composite
    upsert_call = client.table.return_value.upsert.call_args
    assert upsert_call.kwargs.get("on_conflict") == "niche_id,hook_type"
    # Rows carry the trend_direction + computed_at
    rows_arg = upsert_call.args[0]
    assert rows_arg[0]["trend_direction"] in ("rising", "stable", "declining")
    assert "computed_at" in rows_arg[0]


def test_run_with_zero_current_buckets_is_noop() -> None:
    """When no bucket clears the floor, don't upsert an empty chunk."""
    client = _mock_client_with_rows([], [])
    result = run_hook_effectiveness(client=client)
    assert result["upserted"] == 0
    client.table.return_value.upsert.assert_not_called()


def test_run_rising_trend_when_current_higher() -> None:
    """End-to-end: current avg_views 2000, prior 1000 → rising."""
    now = datetime.now(timezone.utc)
    current = [_video(views=2000) for _ in range(3)]
    prior = [_video(views=1000) for _ in range(3)]
    for r in current:
        r["indexed_at"] = now.isoformat()
    for r in prior:
        r["indexed_at"] = (now - timedelta(days=40)).isoformat()

    client = _mock_client_with_rows(current, prior)
    run_hook_effectiveness(client=client)

    rows_arg = client.table.return_value.upsert.call_args.args[0]
    assert rows_arg[0]["trend_direction"] == "rising"
