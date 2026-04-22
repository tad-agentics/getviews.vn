"""Narrative layer tests for Lifecycle reports.

Covers the fallback path (no Gemini key / call failed) exhaustively —
the Gemini-happy path is exercised by a single mocked test since the
actual model output is non-deterministic.

These tests pin the "follow-ups aren't byte-identical" contract: two
different queries against the same cell list produce different
subject_lines.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from getviews_pipeline.report_lifecycle_gemini import (
    LifecycleNarrativeLLM,
    fill_lifecycle_narrative,
)


def _cells_format() -> list[dict[str, Any]]:
    return [
        {
            "name": "Tutorial",
            "stage": "rising",
            "reach_delta_pct": 28.0,
            "health_score": 82,
            "retention_pct": 73.0,
            "instance_count": None,
            "insight": "",
        },
        {
            "name": "Haul",
            "stage": "declining",
            "reach_delta_pct": -12.0,
            "health_score": 33,
            "retention_pct": 44.0,
            "instance_count": None,
            "insight": "",
        },
    ]


def _cells_hook_fatigue() -> list[dict[str, Any]]:
    return [
        {
            "name": "Hook 'Mình vừa test'",
            "stage": "declining",
            "reach_delta_pct": -18.0,
            "health_score": 38,
            "retention_pct": None,
            "instance_count": None,
            "insight": "",
        },
    ]


def _cells_subniche() -> list[dict[str, Any]]:
    return [
        {
            "name": "Skincare routine",
            "stage": "rising",
            "reach_delta_pct": 34.0,
            "health_score": 84,
            "retention_pct": None,
            "instance_count": 1240,
            "insight": "",
        },
        {
            "name": "Unboxing haul",
            "stage": "declining",
            "reach_delta_pct": -12.0,
            "health_score": 33,
            "retention_pct": None,
            "instance_count": 540,
            "insight": "",
        },
    ]


# ── Fallback path (Gemini unavailable) ──────────────────────────────────────


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_returns_all_required_keys() -> None:
    out = fill_lifecycle_narrative(
        query="format nào còn chạy tốt",
        niche_label="Skincare",
        mode="format",
        cells=_cells_format(),
        has_weak_cell=True,
    )
    assert set(out.keys()) == {
        "subject_line", "cell_insights", "refresh_moves", "related_questions",
    }
    # One insight per cell.
    assert len(out["cell_insights"]) == len(_cells_format())
    # Exactly 3 related questions (callers rely on this shape).
    assert len(out["related_questions"]) == 3


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_subject_line_quotes_lead_cell() -> None:
    out = fill_lifecycle_narrative(
        query="format nào còn chạy tốt",
        niche_label="Skincare",
        mode="format",
        cells=_cells_format(),
        has_weak_cell=True,
    )
    # Lead cell name appears in subject_line.
    assert "Tutorial" in out["subject_line"]
    # Subject line under 240 chars (Pydantic invariant).
    assert 0 < len(out["subject_line"]) <= 240


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_hook_fatigue_subject_quotes_pct_drop() -> None:
    out = fill_lifecycle_narrative(
        query="hook này còn dùng được không",
        niche_label="Skincare",
        mode="hook_fatigue",
        cells=_cells_hook_fatigue(),
        has_weak_cell=True,
    )
    # Fatigued hook is at -18% — the subject line must name that number.
    assert "18%" in out["subject_line"]


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_subniche_subject_counts_rising() -> None:
    out = fill_lifecycle_narrative(
        query="ngách con nào đang lên",
        niche_label="Skincare",
        mode="subniche",
        cells=_cells_subniche(),
        has_weak_cell=True,
    )
    # Lead cell (Skincare routine) in subject, +34% delta surfaced.
    assert "Skincare routine" in out["subject_line"]


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_different_queries_produce_different_subjects() -> None:
    """The 2026-04-22 bug guard: two different follow-up queries against
    the same niche + cells should NOT produce byte-identical subject
    lines (even in fallback mode)."""
    cells = _cells_format()
    a = fill_lifecycle_narrative(
        query="format nào còn chạy",
        niche_label="Skincare",
        mode="format",
        cells=cells,
        has_weak_cell=True,
    )
    b = fill_lifecycle_narrative(
        query="kênh nhỏ nên dùng format nào",
        niche_label="Skincare",
        mode="format",
        cells=cells,
        has_weak_cell=True,
    )
    assert a["subject_line"] != b["subject_line"]


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_refresh_moves_skipped_when_all_healthy() -> None:
    healthy_cells = [
        {
            "name": "Tutorial",
            "stage": "rising",
            "reach_delta_pct": 28.0,
            "health_score": 82,
            "retention_pct": 73.0,
            "instance_count": None,
            "insight": "",
        },
    ]
    out = fill_lifecycle_narrative(
        query="format nào chạy tốt",
        niche_label="Skincare",
        mode="format",
        cells=healthy_cells,
        has_weak_cell=False,
    )
    assert out["refresh_moves"] == []


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_cell_insights_each_under_240_chars() -> None:
    out = fill_lifecycle_narrative(
        query="format nào còn chạy tốt",
        niche_label="Skincare",
        mode="format",
        cells=_cells_format(),
        has_weak_cell=True,
    )
    for ins in out["cell_insights"]:
        assert 0 < len(ins) <= 240


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_related_questions_under_120_chars() -> None:
    out = fill_lifecycle_narrative(
        query="format nào còn chạy tốt",
        niche_label="Skincare",
        mode="format",
        cells=_cells_format(),
        has_weak_cell=True,
    )
    for q in out["related_questions"]:
        assert 0 < len(q) <= 120


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_empty_query_still_returns_valid_shape() -> None:
    out = fill_lifecycle_narrative(
        query="",
        niche_label="Skincare",
        mode="format",
        cells=_cells_format(),
        has_weak_cell=True,
    )
    assert out["subject_line"]
    assert len(out["cell_insights"]) == len(_cells_format())


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_empty_cells_returns_graceful_placeholder() -> None:
    out = fill_lifecycle_narrative(
        query="format nào còn chạy tốt",
        niche_label="Skincare",
        mode="format",
        cells=[],
        has_weak_cell=False,
    )
    # No cells → no insights, but shape is still valid.
    assert out["cell_insights"] == []
    assert out["subject_line"]  # non-empty placeholder


# ── Gemini-happy path (mocked) ──────────────────────────────────────────────


@patch("getviews_pipeline.gemini._generate_content_models")
@patch("getviews_pipeline.gemini._normalize_response")
@patch("getviews_pipeline.gemini._response_text")
@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_gemini_happy_path_returns_parsed_narrative(
    mock_response_text: MagicMock,
    mock_normalize: MagicMock,
    mock_gen: MagicMock,
) -> None:
    mock_gen.return_value = MagicMock()
    mock_response_text.return_value = """
{
  "subject_line": "Tutorial đang lên +28% trong khi Haul giảm — chuyển 60% content sang tutorial.",
  "cell_insights": [
    "Tutorial vẫn còn đà — đẩy thêm 2 video tuần này.",
    "Haul fatigue rõ — gộp haul vào routine hoặc story."
  ],
  "refresh_moves": [
    {"title": "Thử hook dạng câu hỏi", "detail": "Đổi mở đầu từ câu khẳng định sang câu hỏi retention tăng 8%.", "effort": "low"}
  ],
  "related_questions": [
    "Tutorial loại nào phù hợp kênh < 10K?",
    "Bao lâu thì tutorial sẽ chững?",
    "Nên giảm haul trước hay chuyển sang review?"
  ]
}
"""
    mock_normalize.side_effect = lambda x: x

    out = fill_lifecycle_narrative(
        query="format nào còn chạy tốt",
        niche_label="Skincare",
        mode="format",
        cells=_cells_format(),
        has_weak_cell=True,
    )
    assert "Tutorial đang lên" in out["subject_line"]
    assert len(out["cell_insights"]) == 2
    assert len(out["refresh_moves"]) == 1
    assert len(out["related_questions"]) == 3


@patch("getviews_pipeline.gemini._generate_content_models")
@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_gemini_exception_falls_through_to_fallback(mock_gen: MagicMock) -> None:
    mock_gen.side_effect = RuntimeError("gemini boom")

    out = fill_lifecycle_narrative(
        query="format nào còn chạy tốt",
        niche_label="Skincare",
        mode="format",
        cells=_cells_format(),
        has_weak_cell=True,
    )
    # Fallback still produced a valid shape.
    assert out["subject_line"]
    assert len(out["cell_insights"]) == 2
    assert len(out["related_questions"]) == 3


# ── Schema invariants (defence in depth) ────────────────────────────────────


def test_llm_schema_accepts_empty_refresh_moves() -> None:
    LifecycleNarrativeLLM.model_validate({
        "subject_line": "stub",
        "cell_insights": ["a"],
        "refresh_moves": [],
        "related_questions": ["q1", "q2", "q3"],
    })


def test_llm_schema_defaults_fill_missing_keys() -> None:
    # Gemini occasionally drops optional keys — parser must not reject.
    m = LifecycleNarrativeLLM.model_validate({"subject_line": "only subject"})
    assert m.cell_insights == []
    assert m.refresh_moves == []
    assert m.related_questions == []
