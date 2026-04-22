"""Tests for the query-aware ideas narrative.

Regression guard for 2026-04-22 user report — Ideas follow-ups used to
produce the same ``lead`` + ``related_questions`` regardless of what the
user asked.
"""

from __future__ import annotations

from getviews_pipeline.report_ideas_gemini import fill_ideas_narrative


def test_fallback_lead_mentions_user_query() -> None:
    narr_a = fill_ideas_narrative(
        query="ý tưởng nào cho mẹ bỉm mới bắt đầu?",
        niche_label="Mẹ bỉm sữa",
        sample_n=85,
        top_idea_hooks=["POV: ngày đầu đi làm lại", "5 món đồ phải có"],
    )
    narr_b = fill_ideas_narrative(
        query="video dưới 30s nên tập trung vào gì?",
        niche_label="Mẹ bỉm sữa",
        sample_n=85,
        top_idea_hooks=["POV: ngày đầu đi làm lại", "5 món đồ phải có"],
    )
    assert "mẹ bỉm mới bắt đầu" in narr_a["lead"]
    assert "video dưới 30s" in narr_b["lead"]
    assert narr_a["lead"] != narr_b["lead"]


def test_fallback_related_questions_reference_top_idea() -> None:
    narr = fill_ideas_narrative(
        query="idea top #1?",
        niche_label="Làm đẹp",
        sample_n=120,
        top_idea_hooks=["Trước & sau 7 ngày"],
    )
    assert any("Trước & sau 7 ngày" in rq for rq in narr["related_questions"])


def test_empty_query_falls_back_to_generic_lead() -> None:
    narr = fill_ideas_narrative(
        query="",
        niche_label="Tech",
        sample_n=95,
        top_idea_hooks=["Demo sản phẩm mới"],
    )
    assert "95" in narr["lead"]
    assert "Tech" in narr["lead"]


def test_empty_hooks_still_produces_lead_and_three_questions() -> None:
    narr = fill_ideas_narrative(
        query="cần ý tưởng mới",
        niche_label="Food",
        sample_n=50,
        top_idea_hooks=[],
    )
    assert narr["lead"]
    assert len(narr["related_questions"]) == 3
