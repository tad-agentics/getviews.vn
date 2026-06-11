"""§0 commerce signals — commerce_intent + legacy promotion_type fallback."""

from __future__ import annotations

from getviews_pipeline.signals.commerce import extract_commerce_signals


def _base_ua() -> dict:
    return {
        "promotion_type": "organic",
        "cta": None,
        "hook_analysis": {
            "first_frame_type": "face",
            "hook_phrase": "",
            "hook_type": "question",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "content_context": {
            "subject_matter": "x",
            "primary_subjects": [],
            "setting": "",
            "products_mentioned": [],
            "creator_role": "user_reviewer",
            "dominant_actions": [],
            "content_purpose": "review",
            "language_register": "casual",
            "topical_hashtags_implied": [],
        },
    }


def test_organic_no_commerce_intent_emits_no_signals() -> None:
    ctx = {"user_analysis": _base_ua()}
    assert extract_commerce_signals(ctx) == []


def test_commerce_intent_commercial_emits_conversion_and_verbal_cta() -> None:
    ua = _base_ua()
    ua["commerce_intent"] = {
        "conversion_objective": "affiliate_shopee",
        "product_price_tier": "not_commerce",
        "creator_type": "koc",
        "verbal_cta_present": False,
        "disclosure_present": False,
        "disclosure_form": "none",
    }
    ids = [s.id for s in extract_commerce_signals({"user_analysis": ua})]
    assert "commerce_conversion_objective" in ids
    assert "commerce_verbal_cta_missing" in ids
    assert "commerce_disclosure_missing" not in ids
    assert "commerce_creator_type_inconsistent" not in ids


def test_price_tier_under_150k_authority_hook_mismatch() -> None:
    ua = _base_ua()
    ua["commerce_intent"] = {
        "conversion_objective": "affiliate_shopee",
        "product_price_tier": "under_150k",
        "creator_type": "koc",
        "verbal_cta_present": True,
        "disclosure_present": True,
        "disclosure_form": "voice",
    }
    ua["hook_analysis"]["hook_type"] = "bold_claim"
    ids = [s.id for s in extract_commerce_signals({"user_analysis": ua})]
    assert "commerce_price_tier_hook_mismatch" in ids


def test_creator_type_entertainment_vs_sell_mismatch() -> None:
    ua = _base_ua()
    ua["content_context"]["content_purpose"] = "sell"
    ua["commerce_intent"] = {
        "conversion_objective": "shop_direct",
        "product_price_tier": "not_commerce",
        "creator_type": "entertainment",
        "verbal_cta_present": True,
        "disclosure_present": True,
        "disclosure_form": "hashtag",
    }
    ids = [s.id for s in extract_commerce_signals({"user_analysis": ua})]
    assert "commerce_creator_type_inconsistent" in ids


def test_legacy_affiliate_no_commerce_intent_promotion_and_cta_missing() -> None:
    ua = _base_ua()
    ua["promotion_type"] = "affiliate"
    ua["cta"] = None
    ids = [s.id for s in extract_commerce_signals({"user_analysis": ua})]
    assert "commerce_promotion_detected" in ids
    assert "commerce_cta_missing" in ids
    assert "commerce_conversion_objective" not in ids


def test_legacy_brand_deal_no_disclosure_signal() -> None:
    ua = _base_ua()
    ua["promotion_type"] = "brand_deal"
    ua["cta"] = "Mua ngay"
    ids = [s.id for s in extract_commerce_signals({"user_analysis": ua})]
    assert "commerce_promotion_detected" in ids
    assert "commerce_disclosure_missing" not in ids
    assert "commerce_cta_missing" not in ids
