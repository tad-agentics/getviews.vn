"""B.3.1 — channel formula helpers + thin gate assembly (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.channel_analyze import (
    CORPUS_GATE_MIN,
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
        patch("getviews_pipeline.channel_analyze._decrement_credit_or_raise") as dec,
    ):
        out = run_channel_analyze_sync(service_sb, user_sb, user_id="u1", raw_handle="@foo")
    dec.assert_not_called()
    assert out["formula_gate"] == "thin_corpus"
    assert out["formula"] is None
    assert out["total_videos"] == 5
    assert CORPUS_GATE_MIN == 10
