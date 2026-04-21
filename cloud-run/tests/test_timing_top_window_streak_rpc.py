"""D.2.2 — timing_top_window_streak RPC fetch contract.

Scenarios the real body produces (migration
``20260501000007_timing_top_window_streak_body.sql``):
  ZERO_WEEK: input (day, hour_bucket) is not the top cell of week 0 → 0.
  MULTI_WEEK: input held #1 for N consecutive most-recent weeks → N.
  WEEK_BOUNDARY: non-contiguous streak (matches week 0, 1 but breaks
    at week 2) stops at 2 — the count is contiguous from week 0, not
    total matches.

`fetch_top_window_streak` handles the RPC return-shape variability
(Supabase sometimes returns int, list-of-dict, or list-of-int); these
tests lock each path.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from getviews_pipeline.report_timing_compute import fetch_top_window_streak


def _sb(data: object) -> MagicMock:
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(data=data)
    return sb


# ── Scenario: ZERO_WEEK ───────────────────────────────────────────────────


def test_streak_zero_when_rpc_returns_zero() -> None:
    sb = _sb(0)
    assert fetch_top_window_streak(sb, niche_id=4, day=3, hour_bucket=4) == 0


def test_streak_zero_when_rpc_returns_none() -> None:
    """A NULL result (RPC could not resolve the niche) fails open to 0."""
    sb = _sb(None)
    assert fetch_top_window_streak(sb, niche_id=4, day=3, hour_bucket=4) == 0


# ── Scenario: MULTI_WEEK ──────────────────────────────────────────────────


def test_streak_multi_week_int_payload() -> None:
    """Most common shape — RPC returns a plain int."""
    sb = _sb(5)
    assert fetch_top_window_streak(sb, niche_id=4, day=3, hour_bucket=4) == 5


def test_streak_multi_week_list_of_dict_payload() -> None:
    """supabase-py wraps scalar returns as [{function_name: value}]."""
    sb = _sb([{"timing_top_window_streak": 6}])
    assert fetch_top_window_streak(sb, niche_id=4, day=3, hour_bucket=4) == 6


def test_streak_multi_week_list_of_int_payload() -> None:
    """Some drivers strip the dict wrapper — accept bare list of int too."""
    sb = _sb([4])
    assert fetch_top_window_streak(sb, niche_id=4, day=3, hour_bucket=4) == 4


# ── Scenario: WEEK_BOUNDARY ──────────────────────────────────────────────


def test_streak_week_boundary_stops_at_first_mismatch() -> None:
    """Contract documented in the RPC body: as soon as a week's top cell
    doesn't match (p_day, p_hour_bucket), counting stops — non-contiguous
    matches deeper in history never contribute to the streak.

    We can't re-execute the SQL here; we lock the Python consumer's
    contract by passing exactly the integer the SQL is specified to
    return in the boundary case.
    """
    # Simulate: week 0 matches, week 1 matches, week 2 mismatches,
    # week 3 matches again → streak = 2.
    sb = _sb(2)
    assert fetch_top_window_streak(sb, niche_id=4, day=3, hour_bucket=4) == 2


def test_streak_clamps_negative_to_zero() -> None:
    """Defensive: if the RPC returns a negative int (shouldn't happen —
    plpgsql floors at 0), the fetcher clamps to 0 instead of emitting a
    negative streak that would confuse the fatigue-band threshold."""
    sb = _sb(-3)
    assert fetch_top_window_streak(sb, niche_id=4, day=3, hour_bucket=4) == 0


# ── Fetch wrapper resilience ─────────────────────────────────────────────


def test_streak_passes_all_three_params_to_rpc() -> None:
    sb = _sb(0)
    fetch_top_window_streak(sb, niche_id=9, day=2, hour_bucket=5)
    sb.rpc.assert_called_once_with(
        "timing_top_window_streak",
        {"p_niche_id": 9, "p_day": 2, "p_hour_bucket": 5},
    )


def test_streak_fails_open_on_rpc_exception() -> None:
    """A raise inside `.execute()` (network / schema error) must not
    bubble up — the fatigue band stays dark instead of crashing the
    Timing report."""
    sb = MagicMock()
    sb.rpc.return_value.execute.side_effect = RuntimeError("boom")
    assert fetch_top_window_streak(sb, niche_id=4, day=3, hour_bucket=4) == 0
