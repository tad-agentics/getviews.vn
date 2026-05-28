"""Tests for deterministic fashion-commerce niche remap (A+B layer)."""

from __future__ import annotations

from getviews_pipeline.fashion_commerce_niche_remap import (
    apply_fashion_commerce_niche_remap,
    has_fashion_commerce_signals,
)
from getviews_pipeline.prompts import _HI9_VIDEO_FEW_SHOT_VI
from getviews_pipeline.two_axis_taxonomy import CREATOR_NICHE_VI


def test_glossary_business_rule_mentions_fashion_shopee() -> None:
    business = CREATOR_NICHE_VI["business"]
    fashion = CREATOR_NICHE_VI["fashion"]
    assert "fashion" in business
    assert "Shopee" in fashion or "shopee" in fashion.lower()


def test_few_shot_includes_shopee_fashion_example() -> None:
    assert "Ví dụ 4" in _HI9_VIDEO_FEW_SHOT_VI
    assert "review_unboxing" in _HI9_VIDEO_FEW_SHOT_VI
    assert '"fashion"' in _HI9_VIDEO_FEW_SHOT_VI
    assert "business" in _HI9_VIDEO_FEW_SHOT_VI


def test_detects_fashion_shopee_signals() -> None:
    aj = {
        "content_context": {
            "subject_matter": "Review set váy áo mua trên Shopee, CTA link giỏ hàng.",
            "content_purpose": "review",
        },
        "niche_classification": {
            "creator_niche_slug": "business",
            "format_axis": "review_unboxing",
            "confidence": 0.72,
        },
    }
    assert has_fashion_commerce_signals(aj) is True


def test_remaps_business_to_fashion_with_class_8() -> None:
    aj = {
        "content_context": {
            "subject_matter": "Review quần áo phụ kiện Shopee cuối video.",
            "content_purpose": "sell",
        },
        "commerce_intent": {"verbal_cta_quote": "Link Shopee trong bio nhé"},
        "niche_classification": {
            "creator_niche_slug": "business",
            "format_axis": "review_unboxing",
            "confidence": 0.7,
            "rationale": "Có CTA bán hàng.",
        },
    }
    result = apply_fashion_commerce_niche_remap(
        aj,
        video_id="7633003576469523733",
        current_content_class_id=49,
    )
    assert result.remapped is True
    assert result.previous_slug == "business"
    assert result.content_class_id == 7  # fashion × review_unboxing junction primary
    nc = aj["niche_classification"]
    assert nc["creator_niche_slug"] == "fashion"
    assert nc["alternative_creator_niche_slug"] == "business"
    assert float(nc["confidence"]) >= 0.85


def test_skips_pure_business_finance() -> None:
    aj = {
        "content_context": {
            "subject_matter": "Bài học đầu tư crypto và quản trị tài chính cá nhân.",
            "content_purpose": "educate",
        },
        "niche_classification": {
            "creator_niche_slug": "business",
            "format_axis": "talking_head_advice",
        },
    }
    result = apply_fashion_commerce_niche_remap(aj)
    assert result.remapped is False
    assert aj["niche_classification"]["creator_niche_slug"] == "business"


def test_skips_food_review_without_fashion() -> None:
    aj = {
        "content_context": {
            "subject_matter": "Review quán phở ngon ở quận 1.",
            "content_purpose": "review",
        },
        "niche_classification": {
            "creator_niche_slug": "business",
            "format_axis": "review_unboxing",
        },
    }
    assert has_fashion_commerce_signals(aj) is False
    result = apply_fashion_commerce_niche_remap(aj)
    assert result.remapped is False


def test_noop_when_already_fashion_and_class_aligned() -> None:
    aj = {
        "content_context": {
            "subject_matter": "OOTD phối đồ váy áo.",
            "content_purpose": "review",
        },
        "niche_classification": {
            "creator_niche_slug": "fashion",
            "format_axis": "review_unboxing",
            "confidence": 0.9,
        },
    }
    result = apply_fashion_commerce_niche_remap(aj, current_content_class_id=7)
    assert result.remapped is False
