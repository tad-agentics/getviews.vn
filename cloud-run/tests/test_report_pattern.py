"""WhatStalled acceptance — empty list requires what_stalled_reason (Phase C.2)."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.report_pattern import (
    build_fixture_pattern_report,
    build_pattern_report,
    build_thin_corpus_pattern_report,
    fetch_pattern_wow_diff_rows,
    wow_rows_to_wow_diff,
)
from getviews_pipeline.report_pattern_compute import compute_what_stalled
from getviews_pipeline.report_types import PatternPayload, validate_and_store_report


def test_fixture_what_stalled_invariant() -> None:
    inner = build_fixture_pattern_report()
    p = PatternPayload.model_validate(inner)
    assert p.what_stalled == []
    assert p.confidence.what_stalled_reason is not None


def test_validate_and_store_pattern_envelope() -> None:
    inner = build_fixture_pattern_report()
    env = validate_and_store_report("pattern", inner)
    assert env["kind"] == "pattern"
    assert "report" in env


def test_empty_stalled_without_reason_raises() -> None:
    """Regression — §C.2 invariant must reject empty list + null reason."""
    inner = copy.deepcopy(build_fixture_pattern_report())
    inner["confidence"]["what_stalled_reason"] = None
    assert inner["what_stalled"] == []
    with pytest.raises(ValueError, match="what_stalled invariant violated"):
        PatternPayload.model_validate(inner)


def test_what_stalled_cap_at_three() -> None:
    """Regression — §C.2 invariant caps what_stalled at 3 entries."""
    inner = copy.deepcopy(build_fixture_pattern_report())
    # Synthesise 4 stalled findings by duplicating the first finding shape.
    if not inner["findings"]:
        pytest.skip("fixture has no findings to clone")
    base = inner["findings"][0]
    inner["what_stalled"] = [base] * 4
    with pytest.raises(ValueError, match="at most 3 entries"):
        PatternPayload.model_validate(inner)


def test_validate_and_store_rejects_invariant_violation() -> None:
    """Envelope validator must propagate the invariant error, not swallow it."""
    inner = copy.deepcopy(build_fixture_pattern_report())
    inner["confidence"]["what_stalled_reason"] = None
    with pytest.raises(ValueError, match="what_stalled invariant violated"):
        validate_and_store_report("pattern", inner)


# —— C.2.1 — WoW RPC mapping + thin corpus + build_pattern_report merge ——


def test_wow_rows_to_wow_diff_empty() -> None:
    w = wow_rows_to_wow_diff([])
    assert w.new_entries == [] and w.dropped == [] and w.rank_changes == []


def test_wow_rows_to_wow_diff_buckets() -> None:
    rows = [
        {"hook_type": "a", "rank_now": 1, "rank_prior": 0, "rank_change": 1, "is_new": True, "is_dropped": False},
        {"hook_type": "b", "rank_now": 4, "rank_prior": 2, "rank_change": 2, "is_new": False, "is_dropped": True},
        {"hook_type": "c", "rank_now": 2, "rank_prior": 3, "rank_change": -1, "is_new": False, "is_dropped": False},
    ]
    w = wow_rows_to_wow_diff(rows)
    assert len(w.new_entries) == 1 and w.new_entries[0]["hook_type"] == "a"
    assert len(w.dropped) == 1 and w.dropped[0]["hook_type"] == "b"
    assert len(w.rank_changes) == 1 and w.rank_changes[0]["hook_type"] == "c"


def test_wow_rows_skips_null_hook_type() -> None:
    w = wow_rows_to_wow_diff([{"hook_type": None, "is_new": True}])
    assert w.new_entries == []


def test_thin_corpus_payload_validates() -> None:
    inner = build_thin_corpus_pattern_report()
    p = PatternPayload.model_validate(inner)
    assert p.confidence.sample_size < 30
    assert p.what_stalled == []
    assert p.confidence.what_stalled_reason


def test_full_fixture_is_full_corpus() -> None:
    inner = build_fixture_pattern_report()
    p = PatternPayload.model_validate(inner)
    assert p.confidence.sample_size >= 30


@patch("getviews_pipeline.report_pattern.fetch_pattern_wow_diff_rows")
def test_build_pattern_report_merges_wow(mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [
        {
            "hook_type": "hook_a",
            "rank_now": 2,
            "rank_prior": 5,
            "rank_change": 3,
            "is_new": True,
            "is_dropped": False,
        }
    ]
    out = build_pattern_report(42, "q", "trend_spike", window_days=14)
    assert out["wow_diff"]["new_entries"] and out["wow_diff"]["new_entries"][0]["hook_type"] == "hook_a"
    assert out["confidence"]["window_days"] == 14
    mock_fetch.assert_called_once_with(42)


@patch(
    "getviews_pipeline.supabase_client.get_service_client",
    side_effect=ValueError("no env"),
)
def test_fetch_pattern_wow_diff_rows_fail_open(_mock: MagicMock) -> None:
    assert fetch_pattern_wow_diff_rows(1) == []


def test_c22_what_stalled_acceptance_invariant() -> None:
    """Either 2–3 stalled rows or [] with non-null reason (C.2.2)."""
    he = [
        {"hook_type": "a", "avg_views": 1000, "avg_completion_rate": 0.8, "sample_size": 10, "trend_direction": "rising"},
        {"hook_type": "b", "avg_views": 900, "avg_completion_rate": 0.75, "sample_size": 10, "trend_direction": "stable"},
        {"hook_type": "c", "avg_views": 800, "avg_completion_rate": 0.7, "sample_size": 10, "trend_direction": "stable"},
        {"hook_type": "d", "avg_views": 100, "avg_completion_rate": 0.1, "sample_size": 10, "trend_direction": "declining"},
        {"hook_type": "e", "avg_views": 90, "avg_completion_rate": 0.09, "sample_size": 10, "trend_direction": "declining"},
    ]
    top3 = {"a", "b", "c"}
    stalled, reason = compute_what_stalled(he, top3, baseline_views=500.0)
    if not stalled:
        assert reason
    else:
        assert 2 <= len(stalled) <= 3
        assert reason is None
