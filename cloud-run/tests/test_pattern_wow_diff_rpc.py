"""D.2.1 — pattern_wow_diff_7d RPC fetch contract.

Four scenarios the real SQL body produces (migration
``20260501000006_pattern_wow_diff_7d_body.sql``):
  NEW: hook present in current-week top-10, absent in prior-week top-10.
  DROPPED: present in prior top-10, absent in current top-10.
  RANK CHANGE: present in both, rank_change = rank_prior - rank_now.
  EMPTY: no hooks in either window → zero rows.

The RPC output flows through ``fetch_pattern_wow_diff_rows`` →
``wow_rows_to_wow_diff`` → `WoWDiff` in the /answer pattern payload. We
mock the Supabase client so these tests lock in the SQL→Python contract
without a live Postgres connection.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from getviews_pipeline.report_pattern import (
    fetch_pattern_wow_diff_rows,
    wow_rows_to_wow_diff,
)


def _rpc_mock(rows: list[dict[str, object]]) -> MagicMock:
    """Supabase client whose `.rpc(...).execute()` returns the given rows."""
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(data=rows)
    return sb


def _fetch_with(rows: list[dict[str, object]], monkeypatch) -> list[dict[str, object]]:
    """Plumb a mocked service client through fetch_pattern_wow_diff_rows."""
    sb = _rpc_mock(rows)
    monkeypatch.setattr(
        "getviews_pipeline.supabase_client.get_service_client",
        lambda: sb,
    )
    return fetch_pattern_wow_diff_rows(p_niche_id := 4) if False else fetch_pattern_wow_diff_rows(4)


# ── Scenario: NEW ─────────────────────────────────────────────────────────


def test_pattern_wow_diff_new_entry_bucket(monkeypatch) -> None:
    """A hook absent from prior-week top-10 but present in current → is_new."""
    rows = [
        {
            "hook_type": "breakout_hook",
            "rank_now": 3,
            "rank_prior": None,
            "rank_change": None,
            "is_new": True,
            "is_dropped": False,
        },
    ]
    out = _fetch_with(rows, monkeypatch)
    assert out == rows  # pass-through shape
    diff = wow_rows_to_wow_diff(out)
    assert len(diff.new_entries) == 1
    assert diff.new_entries[0]["hook_type"] == "breakout_hook"
    assert not diff.dropped
    assert not diff.rank_changes


# ── Scenario: DROPPED ─────────────────────────────────────────────────────


def test_pattern_wow_diff_dropped_bucket(monkeypatch) -> None:
    """A hook in prior-week top-10 absent from current top-10 → is_dropped.

    Covers the "slide out of top 10" case documented in the migration
    header — a rank-8 → rank-15 transition is surfaced as DROPPED because
    the ranker only keeps the top 10 per window.
    """
    rows = [
        {
            "hook_type": "fading_hook",
            "rank_now": None,
            "rank_prior": 7,
            "rank_change": None,
            "is_new": False,
            "is_dropped": True,
        },
    ]
    out = _fetch_with(rows, monkeypatch)
    diff = wow_rows_to_wow_diff(out)
    assert len(diff.dropped) == 1
    assert diff.dropped[0]["hook_type"] == "fading_hook"
    assert not diff.new_entries
    assert not diff.rank_changes


# ── Scenario: RANK CHANGE (both signs) ────────────────────────────────────


def test_pattern_wow_diff_rank_change_positive_and_negative(monkeypatch) -> None:
    """A hook in both windows reports rank_change = rank_prior - rank_now.

    Positive rank_change = moved up (e.g. was rank 5, now rank 2 →
    rank_change = 3). Negative rank_change = moved down.
    """
    rows = [
        {
            "hook_type": "rising_hook",
            "rank_now": 2,
            "rank_prior": 5,
            "rank_change": 3,
            "is_new": False,
            "is_dropped": False,
        },
        {
            "hook_type": "sinking_hook",
            "rank_now": 8,
            "rank_prior": 4,
            "rank_change": -4,
            "is_new": False,
            "is_dropped": False,
        },
    ]
    out = _fetch_with(rows, monkeypatch)
    diff = wow_rows_to_wow_diff(out)
    assert not diff.new_entries and not diff.dropped
    assert len(diff.rank_changes) == 2
    by_handle = {r["hook_type"]: r for r in diff.rank_changes}
    assert by_handle["rising_hook"]["rank_change"] == 3
    assert by_handle["sinking_hook"]["rank_change"] == -4


# ── Scenario: EMPTY ───────────────────────────────────────────────────────


def test_pattern_wow_diff_empty_when_no_rows_in_either_window(monkeypatch) -> None:
    """Fresh niche / no corpus yet → RPC returns zero rows → empty WoWDiff."""
    out = _fetch_with([], monkeypatch)
    diff = wow_rows_to_wow_diff(out)
    assert diff.new_entries == []
    assert diff.dropped == []
    assert diff.rank_changes == []


# ── Fetch wrapper resilience ──────────────────────────────────────────────


def test_fetch_passes_niche_id_to_rpc(monkeypatch) -> None:
    """Make sure the wrapper forwards p_niche_id as the named arg the RPC expects."""
    sb = _rpc_mock([])
    monkeypatch.setattr(
        "getviews_pipeline.supabase_client.get_service_client",
        lambda: sb,
    )
    fetch_pattern_wow_diff_rows(42)
    # supabase-py .rpc(name, params) shape.
    sb.rpc.assert_called_once_with("pattern_wow_diff_7d", {"p_niche_id": 42})


def test_fetch_handles_dict_response_as_single_row(monkeypatch) -> None:
    """Some Supabase responses come back as a single dict rather than a list."""
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(
        data={"hook_type": "solo", "rank_now": 1, "is_new": True},
    )
    monkeypatch.setattr(
        "getviews_pipeline.supabase_client.get_service_client",
        lambda: sb,
    )
    out = fetch_pattern_wow_diff_rows(1)
    assert out == [{"hook_type": "solo", "rank_now": 1, "is_new": True}]
