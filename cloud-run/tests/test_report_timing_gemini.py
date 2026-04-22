"""Tests for the query-aware timing narrative.

Regression guard for 2026-04-22 user report — "follow-up questions
generate the same report every time." The no-Gemini fallback path must
still produce copy that mentions the user's question so two different
timing follow-ups on the same niche don't render identically.
"""

from __future__ import annotations

from getviews_pipeline.report_timing_gemini import fill_timing_narrative


def _top_window() -> dict[str, object]:
    return {"day": "Thứ 4", "hours": "20:00–22:00", "lift_multiplier": 1.8}


def _lowest_window() -> dict[str, str]:
    return {"day": "Thứ 7", "hours": "07:00–09:00"}


def test_fallback_insight_mentions_user_query() -> None:
    """Without a Gemini key, the fallback insight still quotes the user's
    question so two different queries produce two different insights."""
    narr_a = fill_timing_narrative(
        query="khi nào nên post cho mẹ bỉm?",
        niche_label="Mẹ bỉm sữa",
        top_window=_top_window(),
        top_3_windows=[],
        lowest_window=_lowest_window(),
        variance_note=None,
    )
    narr_b = fill_timing_narrative(
        query="giờ nào engagement cao nhất?",
        niche_label="Mẹ bỉm sữa",
        top_window=_top_window(),
        top_3_windows=[],
        lowest_window=_lowest_window(),
        variance_note=None,
    )
    assert "khi nào nên post" in narr_a["insight"]
    assert "engagement cao nhất" in narr_b["insight"]
    assert narr_a["insight"] != narr_b["insight"]


def test_fallback_when_query_empty_uses_generic_lead() -> None:
    narr = fill_timing_narrative(
        query="",
        niche_label="Tech",
        top_window=_top_window(),
        top_3_windows=[],
        lowest_window=_lowest_window(),
        variance_note=None,
    )
    assert "Khung Thứ 4" in narr["insight"]


def test_fallback_when_no_top_window_says_insufficient() -> None:
    narr = fill_timing_narrative(
        query="khi nào nên post?",
        niche_label="Tech",
        top_window=None,
        top_3_windows=[],
        lowest_window=None,
        variance_note=None,
    )
    assert "Chưa đủ tín hiệu" in narr["insight"]


def test_related_questions_always_three() -> None:
    narr = fill_timing_narrative(
        query="khi nào đăng cho creator mới?",
        niche_label="Beauty",
        top_window=_top_window(),
        top_3_windows=[],
        lowest_window=_lowest_window(),
        variance_note=None,
    )
    assert len(narr["related_questions"]) == 3
    for rq in narr["related_questions"]:
        assert 0 < len(rq) <= 120
