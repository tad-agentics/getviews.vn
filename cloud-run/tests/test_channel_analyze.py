"""B.3.1 — channel formula helpers + thin gate assembly (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.channel_analyze import (
    CORPUS_GATE_MIN,
    LiveSignals,
    _age_label_vi,
    _build_recent_7d,
    _classify_verdict,
    _compute_posting_heatmap,
    _compute_pulse,
    _compute_streak_days,
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
    # PR-1 — pulse + recent_7d ride along even on the thin-corpus path so
    # the FE's PulseBlock still has something to render.
    assert "pulse" in out
    assert isinstance(out["pulse"], dict)
    assert out["pulse"]["headline_kind"] in {"win", "concern", "neutral"}
    assert "recent_7d" in out
    assert isinstance(out["recent_7d"], list)


# ── PR-1 — pulse hero + recent_7d ranked verdict list ──────────────────────


def test_compute_streak_days_consecutive_recent_days() -> None:
    """3 distinct days each with a post → streak = 3."""
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc)
    rows = [
        {"posted_at": today.isoformat()},
        {"posted_at": (today - timedelta(days=1)).isoformat()},
        {"posted_at": (today - timedelta(days=2)).isoformat()},
    ]
    assert _compute_streak_days(rows) == 3


def test_compute_streak_days_breaks_on_gap() -> None:
    """A 2-day gap stops the streak at the gap edge."""
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc)
    rows = [
        {"posted_at": today.isoformat()},
        {"posted_at": (today - timedelta(days=1)).isoformat()},
        # gap on day-2
        {"posted_at": (today - timedelta(days=3)).isoformat()},
    ]
    assert _compute_streak_days(rows) == 2


def test_compute_streak_days_today_empty_does_not_break() -> None:
    """Designer's nuance: no post today is OK if yesterday counted.

    Creators may not have posted yet — the chip would feel
    unnecessarily punishing if it zeroed the streak before the day was
    over. The helper allows offset=0 to be empty without breaking.
    """
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc)
    rows = [
        {"posted_at": (today - timedelta(days=1)).isoformat()},
        {"posted_at": (today - timedelta(days=2)).isoformat()},
        {"posted_at": (today - timedelta(days=3)).isoformat()},
    ]
    assert _compute_streak_days(rows) == 3


def test_compute_streak_days_caps_at_window() -> None:
    """Long perfect cadence caps at the configured window (14)."""
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc)
    rows = [
        {"posted_at": (today - timedelta(days=i)).isoformat()} for i in range(20)
    ]
    assert _compute_streak_days(rows, window_days=14) == 14


def test_compute_streak_days_no_rows() -> None:
    assert _compute_streak_days([]) == 0
    # Unparseable timestamps → no contribution.
    assert _compute_streak_days([{"posted_at": "not-a-date"}]) == 0


def test_compute_pulse_win_kind_for_up_delta() -> None:
    live = LiveSignals(views_mom_delta="↑ 18% MoM", streak_days=5)
    p = _compute_pulse(live=live, avg_views=10_000, total_videos=20)
    assert p["headline_kind"] == "win"
    assert "lên" in p["headline"]
    assert p["streak_days"] == 5
    assert p["streak_window"] == 14


def test_compute_pulse_concern_kind_for_down_delta() -> None:
    live = LiveSignals(views_mom_delta="↓ 22% MoM", streak_days=2)
    p = _compute_pulse(live=live, avg_views=8_000, total_videos=15)
    assert p["headline_kind"] == "concern"
    assert "chùng" in p["headline"]


def test_compute_pulse_neutral_for_low_total_videos() -> None:
    live = LiveSignals(views_mom_delta="↑ 30% MoM", streak_days=1)
    p = _compute_pulse(live=live, avg_views=1_000, total_videos=2)
    # Sample too thin → neutral, regardless of delta direction.
    assert p["headline_kind"] == "neutral"
    assert "thêm dữ liệu" in p["headline"]


def test_classify_verdict_thresholds() -> None:
    assert _classify_verdict(2.5) == "WIN"
    assert _classify_verdict(1.5) == "WIN"
    assert _classify_verdict(1.0) == "AVG"
    assert _classify_verdict(0.7) == "AVG"  # boundary inclusive on UNDER side
    assert _classify_verdict(0.69) == "UNDER"
    assert _classify_verdict(0.0) == "UNDER"


def test_age_label_vi_short_forms() -> None:
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)
    assert _age_label_vi(now.isoformat(), now=now) == "vừa xong"
    assert _age_label_vi((now - timedelta(minutes=15)).isoformat(), now=now) == "15 phút trước"
    assert _age_label_vi((now - timedelta(hours=3)).isoformat(), now=now) == "3 giờ trước"
    assert _age_label_vi((now - timedelta(days=2)).isoformat(), now=now) == "2 ngày trước"
    assert _age_label_vi((now - timedelta(days=14)).isoformat(), now=now) == "2 tuần trước"
    assert _age_label_vi(None, now=now) == "—"
    assert _age_label_vi("not-a-date", now=now) == "—"


def test_build_recent_7d_sorts_win_first_then_avg_then_under() -> None:
    """vs_median classifies + sorts: WIN → AVG → UNDER, ties by vs_median."""
    from datetime import datetime, timezone

    now = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)
    rows = [
        {"video_id": "u", "hook_phrase": "Under", "views": 500, "posted_at": now.isoformat()},
        {"video_id": "w", "hook_phrase": "Winner", "views": 5_000, "posted_at": now.isoformat()},
        {"video_id": "a", "hook_phrase": "Average", "views": 1_000, "posted_at": now.isoformat()},
    ]
    out = _build_recent_7d(rows, avg_views=1_000, now=now)
    assert [v["video_id"] for v in out] == ["w", "a", "u"]
    assert out[0]["verdict"] == "WIN"
    assert out[0]["vs_median"] == 5.0
    assert out[1]["verdict"] == "AVG"
    assert out[2]["verdict"] == "UNDER"
    # Heuristic note is non-empty Vietnamese for every row.
    assert all(v["verdict_note"] for v in out)


def test_build_recent_7d_empty_in_empty_out() -> None:
    assert _build_recent_7d([], avg_views=1_000) == []


def test_build_recent_7d_zero_avg_does_not_div_zero() -> None:
    """Defensive: avg_views=0 must not crash the divisor."""
    from datetime import datetime, timezone

    now = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)
    rows = [
        {"video_id": "x", "hook_phrase": "Tit", "views": 100, "posted_at": now.isoformat()},
    ]
    out = _build_recent_7d(rows, avg_views=0, now=now)
    assert len(out) == 1
    assert out[0]["vs_median"] == 100.0  # views / max(1)
