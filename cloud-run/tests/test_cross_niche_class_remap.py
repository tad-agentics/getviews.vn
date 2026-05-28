"""Tests for cross-niche content_class realignment after HI-11 loop route."""

from __future__ import annotations

from getviews_pipeline.cross_niche_class_remap import (
    apply_cross_niche_class_remap,
    resolve_post_route_content_class_id,
)
from getviews_pipeline.prompts import _HI9_VIDEO_FEW_SHOT_VI
from getviews_pipeline.two_axis_taxonomy import CREATOR_NICHE_VI


def test_glossary_real_estate_excludes_baby_talk() -> None:
    assert "em bé" in CREATOR_NICHE_VI["real_estate"].lower()
    assert "miếng" in CREATOR_NICHE_VI["real_estate"]


def test_few_shot_includes_baby_family_example() -> None:
    assert "Ví dụ 5" in _HI9_VIDEO_FEW_SHOT_VI
    assert "gội đầu" in _HI9_VIDEO_FEW_SHOT_VI
    assert '"family"' in _HI9_VIDEO_FEW_SHOT_VI


def test_remaps_baby_vlog_out_of_real_estate_listing() -> None:
    aj = {
        "content_context": {
            "subject_matter": "Em bé gội đầu nói Chắc chắn miếng đi — clip nuôi con hài.",
            "content_purpose": "entertain",
        },
        "hook": {"spoken_hook_quote": "Chắc chắn miếng đi"},
        "niche_classification": {
            "creator_niche_slug": "lifestyle",
            "format_axis": "vlog_daily",
            "confidence": 0.85,
            "rationale": "Vlog đời sống em bé.",
        },
    }
    result = apply_cross_niche_class_remap(
        aj,
        video_id="7644232974795427080",
        current_content_class_id=51,
        loop_creator_niche_id=16,
    )
    assert result.remapped is True
    assert result.target_slug == "family"
    assert result.content_class_id == 30
    nc = aj["niche_classification"]
    assert nc["creator_niche_slug"] == "family"
    assert nc["alternative_creator_niche_slug"] == "lifestyle"


def test_skips_when_loop_and_gemini_agree() -> None:
    aj = {
        "content_context": {
            "subject_matter": "Tour căn hộ 2PN view sông, giá 45 triệu/m².",
        },
        "niche_classification": {
            "creator_niche_slug": "real_estate",
            "format_axis": "vlog_daily",
            "confidence": 0.9,
        },
    }
    result = apply_cross_niche_class_remap(
        aj,
        current_content_class_id=51,
        loop_creator_niche_id=16,
    )
    assert result.remapped is False


def test_skips_low_confidence() -> None:
    aj = {
        "content_context": {"subject_matter": "Em bé gội đầu."},
        "niche_classification": {
            "creator_niche_slug": "family",
            "format_axis": "vlog_daily",
            "confidence": 0.4,
        },
    }
    result = apply_cross_niche_class_remap(
        aj,
        current_content_class_id=51,
        loop_creator_niche_id=16,
    )
    assert result.remapped is False


def test_resolve_applies_fashion_then_cross() -> None:
    aj = {
        "content_context": {
            "subject_matter": "Review váy Shopee — em bé trong khung hình phụ.",
            "content_purpose": "sell",
        },
        "commerce_intent": {"verbal_cta_quote": "Link Shopee nhé"},
        "niche_classification": {
            "creator_niche_slug": "business",
            "format_axis": "review_unboxing",
            "confidence": 0.88,
        },
    }
    cc = resolve_post_route_content_class_id(
        aj,
        route_content_class_id=49,
        loop_creator_niche_id=9,
    )
    assert cc == 7
    assert aj["niche_classification"]["creator_niche_slug"] == "fashion"
