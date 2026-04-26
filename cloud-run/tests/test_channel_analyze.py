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
    _compute_cadence_struct,
    _compute_posting_heatmap,
    _compute_pulse,
    _compute_streak_days,
    _compute_views_mom_delta,
    _format_best_days,
    _format_best_hour_range,
    _median,
    _normalize_diagnostic_items,
    _normalize_formula_pcts,
    _optimal_length_band,
    _synthesize_lessons_from_diagnostic,
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
    # PR-2 — strengths + weaknesses always present (empty on thin-corpus).
    assert out["strengths"] == []
    assert out["weaknesses"] == []
    # Legacy ``lessons`` falls back to whatever the caller passed
    # (here: empty []), not synthesized from empty diagnostic arrays.
    assert out["lessons"] == []
    # PR-3 — cadence is None on thin-corpus (LiveSignals() default).
    assert out["cadence"] is None


# ── PR-2 — diagnostic restructure (strengths + weaknesses) ─────────────────


def test_normalize_diagnostic_items_drops_empties_and_clamps_lengths() -> None:
    raw = [
        {
            "title": "Hook bám trend đang lên",
            "metric": "Hook < 1s · 80% video",
            "why": "Audience của ngách này quyết định scroll trong 0.8s.",
            "action": "Tiếp tục mở bằng face cam, đẩy CTA xuống cuối.",
            "bridge_to": "01",
        },
        {"title": "", "metric": "Có metric nhưng thiếu title"},
        {
            "title": "Bridge unknown drops to None",
            "metric": "x",
            "why": "y",
            "action": "z",
            "bridge_to": "99",
        },
        # Pure-string item is dropped (defensive — LLM occasionally returns these).
        "not a dict",
    ]
    out = _normalize_diagnostic_items(raw, default_action_label="—")
    assert len(out) == 2
    assert out[0]["bridge_to"] == "01"
    assert out[1]["bridge_to"] is None
    assert out[1]["title"] == "Bridge unknown drops to None"


def test_normalize_diagnostic_items_keeps_action_default_when_blank() -> None:
    raw = [{"title": "Tit", "metric": "—", "why": "—", "action": ""}]
    out = _normalize_diagnostic_items(raw, default_action_label="TẬN DỤNG")
    assert out[0]["action"] == "TẬN DỤNG"


def test_synthesize_lessons_from_diagnostic_caps_to_legacy_shape() -> None:
    """Legacy bridge: 2 strengths + 2 weaknesses → 4 title/body lessons."""
    strengths = [
        {"title": "S1", "metric": "m1", "why": "w1", "action": "a1"},
        {"title": "S2", "metric": "m2", "why": "w2", "action": "a2"},
        {"title": "S3", "metric": "m3", "why": "w3", "action": "a3"},
    ]
    weaknesses = [
        {"title": "W1", "metric": "m1", "why": "w1", "action": "a1"},
        {"title": "W2", "metric": "m2", "why": "w2", "action": "a2"},
        {"title": "W3", "metric": "m3", "why": "w3", "action": "a3"},
    ]
    out = _synthesize_lessons_from_diagnostic(strengths, weaknesses)
    assert len(out) == 4  # 2 strengths + 2 weaknesses
    titles = [x["title"] for x in out]
    assert titles == ["S1", "S2", "W1", "W2"]
    assert all("body" in x and x["body"] for x in out)


def test_synthesize_lessons_drops_items_missing_body() -> None:
    """Item with title but no metric/why/action → dropped."""
    strengths = [
        {"title": "S1", "metric": "m", "why": "", "action": ""},
        {"title": "S2", "metric": "", "why": "", "action": ""},  # body=""
    ]
    out = _synthesize_lessons_from_diagnostic(strengths, [])
    assert len(out) == 1
    assert out[0]["title"] == "S1"


def test_synthesize_lessons_handles_none_inputs() -> None:
    assert _synthesize_lessons_from_diagnostic(None, None) == []


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


# ── PR-3 — cadence struct (calendar + best hour/day) ───────────────────────


def test_format_best_hour_range_window() -> None:
    assert _format_best_hour_range(20) == "20:00–22:00"
    assert _format_best_hour_range(0) == "00:00–02:00"
    # Wraps across midnight.
    assert _format_best_hour_range(23) == "23:00–01:00"
    assert _format_best_hour_range(None) == ""


def test_format_best_days_top_n_stable_ties() -> None:
    from collections import Counter

    # Mon=4, Tue=4, Wed=2 → ties between Mon/Tue; weekday order breaks tie.
    counts = Counter({0: 4, 1: 4, 2: 2})
    assert _format_best_days(counts, top_n=2) == "T2, T3"
    # Empty in → empty out.
    assert _format_best_days(Counter()) == ""


def test_compute_cadence_struct_returns_none_when_too_few_rows() -> None:
    from datetime import datetime, timezone

    now = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)
    assert _compute_cadence_struct([], now=now) is None
    rows = [{"posted_at": now.isoformat()}, {"posted_at": now.isoformat()}]
    assert _compute_cadence_struct(rows, now=now) is None


def test_compute_cadence_struct_posts_14d_grid_aligns_with_today() -> None:
    """Last cell = today; first cell = today − 13 days."""
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)
    today = now.date()
    rows = [
        # Today + 3 days ago + 13 days ago → cells at indices 13, 10, 0.
        {"posted_at": now.isoformat()},
        {"posted_at": (now - timedelta(days=3)).isoformat()},
        {"posted_at": (now - timedelta(days=13)).isoformat()},
    ]
    out = _compute_cadence_struct(rows, now=now)
    assert out is not None
    assert len(out["posts_14d"]) == 14
    assert out["posts_14d"][13] is True   # today
    assert out["posts_14d"][10] is True   # today − 3
    assert out["posts_14d"][0] is True    # today − 13
    assert out["posts_14d"][12] is False  # yesterday — gap
    # weekly_actual covers last 7 days (indices 7..13). Today and t-3 land
    # there; t-13 is outside the 7-day window.
    assert out["weekly_actual"] == 2
    # Spot-check today reference is what we expect.
    assert today is not None


def test_compute_cadence_struct_caps_target_at_actual() -> None:
    """A creator who's been on a tear shouldn't get an artificially low target."""
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)
    # 10 distinct days in the last 7-day window — but only 7 days exist
    # in 7 days, so weekly_actual will be 7. weekly_target must also
    # reach ≥ weekly_actual (then cap at 7 since the design's daily
    # ceiling is 7).
    rows = [
        {"posted_at": (now - timedelta(days=i)).isoformat()} for i in range(7)
    ]
    out = _compute_cadence_struct(rows, now=now)
    assert out is not None
    assert out["weekly_actual"] == 7
    assert out["weekly_target"] >= out["weekly_actual"]
    assert out["weekly_target"] <= 7


def test_compute_cadence_struct_emits_best_hour_and_days() -> None:
    """Peak weekday + peak hour propagate to formatted strings."""
    from datetime import datetime, timezone

    now = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)
    # Three Saturday 20:00 posts + one Sunday 9:00 → best_days = "T7, CN".
    rows = [
        {"posted_at": datetime(2026, 4, 25, 20, tzinfo=timezone.utc).isoformat()},
        {"posted_at": datetime(2026, 4, 18, 20, tzinfo=timezone.utc).isoformat()},
        {"posted_at": datetime(2026, 4, 11, 20, tzinfo=timezone.utc).isoformat()},
        {"posted_at": datetime(2026, 4, 19, 9, tzinfo=timezone.utc).isoformat()},
    ]
    out = _compute_cadence_struct(rows, now=now)
    assert out is not None
    assert out["best_hour"] == "20:00–22:00"
    assert out["best_days"].startswith("T7")
    assert "CN" in out["best_days"]
