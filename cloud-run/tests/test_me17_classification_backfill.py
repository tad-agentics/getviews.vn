"""ME-17 — classification backfill merge + stats (Gemini mocked)."""

from __future__ import annotations

import json

import pytest

from getviews_pipeline.classification_backfill import (
    VideoClassificationBackfillLLM,
    _compact_analysis_json,
    backfill_row_with_gemini,
)


def test_compact_analysis_json_truncates() -> None:
    big = {"x": "y" * 50_000}
    s = _compact_analysis_json(big)
    assert len(s) <= 28_000
    assert "cắt bớt" in s or "…" in s


def test_video_backfill_llm_minimal_round_trip() -> None:
    raw = {
        "content_context": {"subject_matter": "Review sản phẩm"},
        "niche_classification": {
            "creator_niche_slug": "beauty",
            "format_axis": "review_unboxing",
            "confidence": 0.88,
            "rationale": "Có sản phẩm lên hình và đánh giá.",
        },
    }
    m = VideoClassificationBackfillLLM.model_validate(raw)
    d = m.model_dump(mode="json")
    assert d["niche_classification"]["format_axis"] == "review_unboxing"


def test_backfill_row_with_gemini_merges(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_gen(contents, **kwargs):  # noqa: ANN001, ARG001
        return object()

    def fake_text(_response):  # noqa: ANN001
        return json.dumps(
            {
                "content_context": {"subject_matter": "Làm đẹp tại nhà"},
                "niche_classification": {
                    "creator_niche_slug": "beauty",
                    "format_axis": "tutorial",
                    "confidence": 0.9,
                    "rationale": "Hướng dẫn các bước skincare.",
                },
            }
        )

    monkeypatch.setattr(
        "getviews_pipeline.gemini._generate_content_models",
        fake_gen,
    )
    monkeypatch.setattr("getviews_pipeline.gemini._response_text", fake_text)

    base = {
        "hook_analysis": {
            "first_frame_type": "text_only",
            "hook_phrase": "Xin chào",
            "hook_type": "how_to",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "topics": ["skincare"],
    }
    merged = backfill_row_with_gemini(base, "video")
    assert merged is not None
    assert merged["topics"] == ["skincare"]
    assert merged["content_context"]["subject_matter"] == "Làm đẹp tại nhà"
    assert merged["niche_classification"]["format_axis"] == "tutorial"

