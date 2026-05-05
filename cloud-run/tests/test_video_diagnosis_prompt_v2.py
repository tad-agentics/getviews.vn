"""Tests for D2 — video diagnosis prompt v2 helpers + contract.

Pins the prompt v2 contract (mechanism vocabulary, severity anchor,
fix vocabulary, forbidden cliché list, few-shot example, retention
summary) so future edits can't accidentally regress quality without
the test catching it.

Mirrors the D1 ``test_morning_ritual.py`` v2 assertions discipline.
"""

from __future__ import annotations

import pytest


def _imports():
    """Lazy import so pydantic isn't loaded at collection time."""
    try:
        from getviews_pipeline.video_analyze import (
            _summarise_retention_curve,
            _summarise_niche_row,
        )
        return _summarise_retention_curve, _summarise_niche_row
    except ModuleNotFoundError:
        pytest.skip("pydantic not installed in test env")


# ── _summarise_retention_curve ────────────────────────────────────────


def test_retention_summary_empty_when_curve_too_short() -> None:
    summarise, _ = _imports()
    assert summarise(None) == ""
    assert summarise([]) == ""
    assert summarise([{"t": 0, "pct": 100}]) == ""
    assert summarise([{"t": 0, "pct": 100}, {"t": 1, "pct": 80}]) == ""


def test_retention_summary_no_drop_when_curve_flat() -> None:
    summarise, _ = _imports()
    curve = [{"t": 0, "pct": 100}, {"t": 1, "pct": 99}, {"t": 2, "pct": 98}]
    out = summarise(curve)
    assert "Retention end 98%" in out
    assert "không có drop đột biến" in out


def test_retention_summary_flags_steepest_drop_with_timing() -> None:
    summarise, _ = _imports()
    # 100 → 95 (-5) → 60 (-35!) → 50 (-10) → 45 (-5) — biggest drop = -35
    # between t=1.0 (95%) and t=1.5 (60%). Helper reports drop_at = the
    # earlier point of the drop pair, drop_to = the later pct.
    curve = [
        {"t": 0.0, "pct": 100},
        {"t": 1.0, "pct": 95},
        {"t": 1.5, "pct": 60},
        {"t": 2.5, "pct": 50},
        {"t": 4.0, "pct": 45},
    ]
    out = summarise(curve)
    assert "Drop lớn nhất: 35% tại 1.0s → 60%" in out
    assert "Retention end 45%" in out


# ── _summarise_niche_row ──────────────────────────────────────────────


def test_niche_summary_handles_none_and_empty() -> None:
    _, summarise = _imports()
    # Both None and empty dict treated as "no data" — semantic
    # distinction isn't meaningful for the prompt.
    assert "chưa có dữ liệu ngách" in summarise(None)
    assert "chưa có dữ liệu ngách" in summarise({})


def test_niche_summary_includes_all_present_fields() -> None:
    _, summarise = _imports()
    row = {
        "sample_size": 200,
        "organic_avg_views": 100_000,
        "median_er": 0.054,
        "median_views": 80_000,
    }
    out = summarise(row)
    assert "sample=200" in out
    assert "avg_views≈100,000" in out
    assert "median_er=0.054" in out
    assert "median_views≈80,000" in out


def test_niche_summary_falls_back_to_avg_views_field() -> None:
    """When organic_avg_views is missing (e.g. from
    content_class_intelligence which exposes ``avg_views`` instead),
    the summary still produces a value."""
    _, summarise = _imports()
    row = {"sample_size": 50, "avg_views": 30_000, "median_er": 0.04}
    out = summarise(row)
    assert "avg_views≈30,000" in out


# ── Prompt v2 contract ────────────────────────────────────────────────


def test_win_prompt_v2_lists_seven_mechanisms() -> None:
    try:
        from getviews_pipeline.video_analyze import _MECHANISM_VOCAB_VI
    except ModuleNotFoundError:
        pytest.skip("pydantic not installed in test env")
    for mech in (
        "curiosity_gap", "social_proof", "identification",
        "contrarian_take", "before_after_promise",
        "status_anchor", "fomo_loss",
    ):
        assert mech in _MECHANISM_VOCAB_VI


def test_forbidden_phrases_list_includes_known_clichés() -> None:
    try:
        from getviews_pipeline.video_analyze import _FORBIDDEN_PHRASES_VI
    except ModuleNotFoundError:
        pytest.skip("pydantic not installed in test env")
    for phrase in (
        "tính năng ẩn", "bí mật không ai nói", "triệu view",
        "bùng nổ", "công thức vàng",
    ):
        assert phrase in _FORBIDDEN_PHRASES_VI
