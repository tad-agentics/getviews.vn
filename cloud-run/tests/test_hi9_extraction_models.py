"""HI-9 — two-axis taxonomy + content_context on VideoAnalysis / CarouselAnalysis."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from getviews_pipeline.models import CarouselAnalysis, VideoAnalysis
from getviews_pipeline.prompts import CAROUSEL_EXTRACTION_PROMPT, VIDEO_EXTRACTION_PROMPT


def _minimal_video_analysis_dict() -> dict:
    return {
        "hook_analysis": {
            "first_frame_type": "face",
            "hook_phrase": "Xin chào",
            "hook_type": "question",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "has_human_speaking_to_camera": True,
        "has_expressed_opinion_or_question": False,
        "text_overlays": [],
        "scenes": [
            {
                "type": "face_to_camera",
                "start": 0.0,
                "end": 5.0,
            }
        ],
        "transitions_per_second": 0.2,
        "energy_level": "medium",
        "key_timestamps": [],
        "audio_transcript": "Xin chào mọi người",
        "tone": "conversational",
        "topics": [],
        "key_messages": [],
        "cta": None,
        "content_direction": {"what_works": "face mở đầu", "suggested_angles": []},
        "target_audience": "",
        "pain_points": [],
        "promotion_type": "organic",
        "style_tags": [],
    }


def test_video_analysis_legacy_row_without_hi9_fields_validates() -> None:
    m = VideoAnalysis.model_validate(_minimal_video_analysis_dict())
    assert m.content_context is None
    assert m.niche_classification is None


def test_video_analysis_hi9_fields_round_trip() -> None:
    d = _minimal_video_analysis_dict()
    d["content_context"] = {
        "subject_matter": "Review serum vitamin C cho da dầu.",
        "primary_subjects": ["serum", "da dầu"],
        "setting": "phòng ngủ ánh sáng tự nhiên",
        "products_mentioned": [{"name": "Serum X", "brand": "Brand Y", "category": "skincare"}],
        "creator_role": "user_reviewer",
        "dominant_actions": ["bôi serum", "trỏ camera"],
        "content_purpose": "review",
        "language_register": "casual",
        "topical_hashtags_implied": ["#skincare", "#review"],
    }
    d["niche_classification"] = {
        "creator_niche_slug": "beauty",
        "format_axis": "review_unboxing",
        "confidence": 0.85,
        "rationale": (
            "Da mặt cận + review sản phẩm — đúng ngách làm đẹp và định dạng review."
        ),
        "alternative_creator_niche_slug": None,
    }
    m = VideoAnalysis.model_validate(d)
    assert m.content_context is not None
    assert m.content_context.subject_matter is not None
    assert m.niche_classification is not None
    assert m.niche_classification.creator_niche_slug == "beauty"
    assert m.niche_classification.format_axis == "review_unboxing"


def test_video_analysis_rejects_invalid_creator_niche_slug() -> None:
    d = _minimal_video_analysis_dict()
    d["niche_classification"] = {
        "creator_niche_slug": "not_a_real_niche",
        "format_axis": "tutorial",
        "confidence": 0.9,
        "rationale": "test",
        "alternative_creator_niche_slug": None,
    }
    with pytest.raises(ValidationError):
        VideoAnalysis.model_validate(d)


def test_video_analysis_rejects_invalid_format_axis() -> None:
    d = _minimal_video_analysis_dict()
    d["niche_classification"] = {
        "creator_niche_slug": "food",
        "format_axis": "tutorial_step_by_step",
        "confidence": 0.9,
        "rationale": "test",
        "alternative_creator_niche_slug": None,
    }
    with pytest.raises(ValidationError):
        VideoAnalysis.model_validate(d)


def test_carousel_analysis_hi9_optional_like_video() -> None:
    d = {
        "hook_analysis": {
            "first_frame_type": "text_only",
            "hook_phrase": "5 lỗi sai",
            "hook_type": "how_to",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "slides": [
            {
                "index": 0,
                "visual_type": "text_card",
                "text_on_slide": ["5 lỗi"],
                "note": "",
                "text_density": "low",
                "has_face": False,
                "has_product": False,
                "word_count": 2,
            }
        ],
        "transitions_per_second": 0.0,
        "energy_level": "medium",
        "key_timestamps": [],
        "audio_transcript": "",
        "tone": "educational",
        "topics": [],
        "key_messages": [],
        "cta": None,
        "content_direction": {"what_works": "list có số", "suggested_angles": []},
        "content_arc": "list",
        "visual_consistency": "consistent",
        "estimated_read_time_seconds": 10,
        "content_context": {
            "subject_matter": "Carousel liệt kê 5 lỗi chăm da.",
            "primary_subjects": ["skincare"],
            "creator_role": "tutorial_host",
            "content_purpose": "educate",
            "language_register": "casual",
        },
        "niche_classification": {
            "creator_niche_slug": "beauty",
            "format_axis": "tutorial",
            "confidence": 0.78,
            "rationale": "Nhiều slide chữ + bước — carousel hướng dẫn trong ngách làm đẹp.",
            "alternative_creator_niche_slug": "wellness",
        },
    }
    m = CarouselAnalysis.model_validate(d)
    assert m.niche_classification is not None
    assert m.niche_classification.alternative_creator_niche_slug == "wellness"


def test_extraction_prompts_include_glossary_and_hi9() -> None:
    assert "content_context" in VIDEO_EXTRACTION_PROMPT
    assert "niche_classification" in VIDEO_EXTRACTION_PROMPT
    assert "Ví dụ 1" in VIDEO_EXTRACTION_PROMPT
    assert '"beauty"' in VIDEO_EXTRACTION_PROMPT or "beauty" in VIDEO_EXTRACTION_PROMPT
    assert "review_unboxing" in VIDEO_EXTRACTION_PROMPT
    assert "content_context" in CAROUSEL_EXTRACTION_PROMPT
    assert "real_estate" in VIDEO_EXTRACTION_PROMPT


def test_extract_subject_matter_helper() -> None:
    from getviews_pipeline.two_axis_taxonomy import extract_subject_matter_from_analysis_json

    assert extract_subject_matter_from_analysis_json(None) is None
    assert extract_subject_matter_from_analysis_json({}) is None
    assert extract_subject_matter_from_analysis_json({"content_context": {}}) is None
    assert (
        extract_subject_matter_from_analysis_json(
            {"content_context": {"subject_matter": "  a b  "}},
            max_len=3,
        )
        == "a b"
    )
