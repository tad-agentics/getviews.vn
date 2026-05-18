"""Sprint 10 — §12 commerce conversion metrics override signal."""

from __future__ import annotations

from getviews_pipeline.signals.performance import extract_commerce_performance_override_signal
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest


def _commercial_ua() -> dict:
    return {
        "promotion_type": "organic",
        "commerce_intent": {
            "conversion_objective": "shop_direct",
            "product_price_tier": "not_commerce",
            "creator_type": "kos_seller",
            "verbal_cta_present": True,
            "disclosure_present": True,
            "disclosure_form": "voice",
        },
        "hook_analysis": {"hook_type": "question"},
    }


def test_override_flop_tier_high_orders_per_1k() -> None:
    ctx = {
        "performance_tier": "flop",
        "user_analysis": _commercial_ua(),
        "user_stats": {
            "views": 80_000,
            "commerce_conversion": {"order_count": 300},
        },
    }
    sigs = extract_commerce_performance_override_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "commerce_performance_conversion_override"
    assert sigs[0].salience == 1.0
    assert sigs[0].section_id == "commerce"
    assert sigs[0].taxonomy_ref == "§12"


def test_no_override_when_hit_tier() -> None:
    ctx = {
        "performance_tier": "hit",
        "user_analysis": _commercial_ua(),
        "user_stats": {
            "views": 80_000,
            "commerce_conversion": {"order_count": 300},
        },
    }
    assert extract_commerce_performance_override_signal(ctx) == []


def test_no_override_when_orders_sparse_for_views() -> None:
    ctx = {
        "performance_tier": "average",
        "user_analysis": _commercial_ua(),
        "user_stats": {
            "views": 80_000,
            "commerce_conversion": {"order_count": 12},
        },
    }
    assert extract_commerce_performance_override_signal(ctx) == []


def test_no_override_when_entertainment_only() -> None:
    ua = _commercial_ua()
    ua["commerce_intent"]["conversion_objective"] = "entertainment_first"
    ctx = {
        "performance_tier": "flop",
        "user_analysis": ua,
        "user_stats": {
            "views": 80_000,
            "commerce_conversion": {"order_count": 300},
        },
    }
    assert extract_commerce_performance_override_signal(ctx) == []


def test_flat_shop_order_count_escape_hatch() -> None:
    ctx = {
        "performance_tier": "average",
        "user_analysis": _commercial_ua(),
        "user_stats": {"views": 50_000, "shop_order_count": 75},
    }
    sigs = extract_commerce_performance_override_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].salience == 1.0


def test_manifest_lists_override_in_commerce_section() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis=_commercial_ua(),
        user_stats={
            "views": 60_000,
            "commerce_conversion": {"order_count": 120},
        },
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
    )
    manifest = build_signal_manifest(ctx)
    ids = [s.id for s in manifest.get("commerce", [])]
    assert "commerce_performance_conversion_override" in ids

