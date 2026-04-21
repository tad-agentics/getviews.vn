"""B.3.1 — channel formula helpers + thin gate assembly (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.channel_analyze import (
    CORPUS_GATE_MIN,
    LiveSignals,
    _compute_posting_heatmap,
    _compute_views_mom_delta,
    _median,
    _normalize_formula_pcts,
    _optimal_length_band,
    _top_hook_from_types,
    run_channel_analyze_sync,
)


def test_normalize_formula_pcts_targets_hundred() -> None:
    raw = [
        {"step": "Hook", "detail": "a", "pct": 22},
        {"step": "Setup", "detail": "b", "pct": 18},
        {"step": "Body", "detail": "c", "pct": 45},
        {"step": "Payoff", "detail": "d", "pct": 15},
    ]
    out = _normalize_formula_pcts(raw)
    assert len(out) == 4
    assert sum(x["pct"] for x in out) == 100
    assert all(x["pct"] >= 4 for x in out)


def test_top_hook_from_types_mode() -> None:
    top, pct = _top_hook_from_types(["pov", "pov", "story", "pov"])
    assert top == "pov"
    assert pct == pytest.approx(75.0)


def test_optimal_length_band_from_duration_seconds() -> None:
    rows = [
        {"analysis_json": {"duration_seconds": 30}},
        {"analysis_json": {"duration_seconds": 40}},
        {"analysis_json": {"duration_seconds": 50}},
        {"analysis_json": {"duration_seconds": 60}},
    ]
    assert _optimal_length_band(rows) == "30–50s"


def test_median_middle_value() -> None:
    assert _median([1.0, 3.0, 9.0]) == 3.0
    assert _median([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_views_mom_delta_with_synthetic_windows() -> None:
    """Last 30d avg vs prior 30d — enough samples → MoM string."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    rows = []
    for i in range(15):
        rows.append(
            {
                "created_at": (now - timedelta(days=10 + i)).isoformat(),
                "views": 1000 + i * 10,
                "engagement_rate": 0.05,
            }
        )
    for i in range(15):
        rows.append(
            {
                "created_at": (now - timedelta(days=40 + i)).isoformat(),
                "views": 500 + i * 5,
                "engagement_rate": 0.04,
            }
        )
    out = _compute_views_mom_delta(rows)
    assert "MoM" in out
    assert out.startswith("↑")


# ── D.1.4 — posting_heatmap aggregation ────────────────────────────────────


def test_posting_heatmap_empty_when_fewer_than_three_rows() -> None:
    """Guard: < 3 parseable timestamps → [] so the frontend hides the panel."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    rows = [{"created_at": now.isoformat()}, {"created_at": now.isoformat()}]
    assert _compute_posting_heatmap(rows) == []
    # Also covers malformed timestamps — parser returns None, filter drops them.
    assert _compute_posting_heatmap([{"created_at": "not-a-date"}] * 10) == []


def test_posting_heatmap_returns_7_by_8_shape() -> None:
    """Valid sample returns a dense 7×8 grid regardless of empty cells."""
    from datetime import datetime, timezone

    # Three Monday-18h posts land in (weekday=0, hour_bucket=4).
    rows = [
        {"created_at": datetime(2026, 4, 6, 18, tzinfo=timezone.utc).isoformat()},
        {"created_at": datetime(2026, 4, 6, 19, tzinfo=timezone.utc).isoformat()},
        {"created_at": datetime(2026, 4, 6, 19, 30, tzinfo=timezone.utc).isoformat()},
    ]
    grid = _compute_posting_heatmap(rows)
    assert len(grid) == 7
    assert all(len(row) == 8 for row in grid)
    assert grid[0][4] == 3
    # Other cells stay zero.
    total_cells = sum(sum(row) for row in grid)
    assert total_cells == 3


def test_posting_heatmap_buckets_hours_correctly() -> None:
    """Hours 3–5 are dropped; 0–2 land in bucket 7; 22–23 in bucket 6."""
    from datetime import datetime, timezone

    rows = [
        # Dead zone — all dropped.
        {"created_at": datetime(2026, 4, 6, 3, tzinfo=timezone.utc).isoformat()},
        {"created_at": datetime(2026, 4, 6, 4, tzinfo=timezone.utc).isoformat()},
        {"created_at": datetime(2026, 4, 6, 5, tzinfo=timezone.utc).isoformat()},
        # 22–24 → bucket 6.
        {"created_at": datetime(2026, 4, 7, 22, tzinfo=timezone.utc).isoformat()},
        {"created_at": datetime(2026, 4, 7, 23, tzinfo=timezone.utc).isoformat()},
        # 0–3 → bucket 7.
        {"created_at": datetime(2026, 4, 8, 0, tzinfo=timezone.utc).isoformat()},
        {"created_at": datetime(2026, 4, 8, 1, tzinfo=timezone.utc).isoformat()},
        {"created_at": datetime(2026, 4, 8, 2, tzinfo=timezone.utc).isoformat()},
    ]
    grid = _compute_posting_heatmap(rows)
    assert grid[1][6] == 2  # Tue 22–24
    assert grid[2][7] == 3  # Wed 0–3
    # Dead-zone hours produce zero across the whole grid when they're the only samples.
    assert sum(sum(row) for row in grid) == 5


def test_run_channel_analyze_thin_corpus_no_credit() -> None:
    """Below gate video count → thin_corpus; must not call decrement_credit."""
    user_sb = MagicMock()
    user_sb.table.return_value.select.return_value.single.return_value.execute.return_value = MagicMock(
        data={"primary_niche": 1},
    )
    service_sb = MagicMock()
    with (
        patch("getviews_pipeline.channel_analyze._resolve_niche_label", return_value="Tech"),
        patch(
            "getviews_pipeline.channel_analyze._fetch_corpus_stats_rpc",
            return_value={"total": 5, "avg_views": 900, "avg_er": 0.04},
        ),
        patch("getviews_pipeline.channel_analyze._fetch_starter_row", return_value=None),
        patch("getviews_pipeline.channel_analyze._fetch_top_corpus_rows", return_value=[]),
        patch("getviews_pipeline.channel_analyze._fetch_hook_types", return_value=[]),
        patch(
            "getviews_pipeline.channel_analyze.compute_live_signals",
            return_value=LiveSignals(),
        ),
        patch("getviews_pipeline.channel_analyze._decrement_credit_or_raise") as dec,
    ):
        out = run_channel_analyze_sync(service_sb, user_sb, user_id="u1", raw_handle="@foo")
    dec.assert_not_called()
    assert out["formula_gate"] == "thin_corpus"
    assert out["formula"] is None
    assert out["total_videos"] == 5
    assert CORPUS_GATE_MIN == 10
