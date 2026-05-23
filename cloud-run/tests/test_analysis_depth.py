"""Wave 3 — analysis_depth whitelist, manifest cap, cache key helper."""

from __future__ import annotations

import pytest

from getviews_pipeline.diagnose_sections import (
    BASIC_SECTION_ALLOWLIST,
    select_sections_to_emit,
    upsell_locked_sections,
)
from getviews_pipeline.signals.base import Signal
from getviews_pipeline.signals.registry import (
    build_diagnosis_ctx,
    build_signal_manifest,
    manifest_for_prompt,
)
from getviews_pipeline.video_analyze import _normalize_analysis_depth


def test_normalize_analysis_depth() -> None:
    assert _normalize_analysis_depth("basic") == "basic"
    assert _normalize_analysis_depth("deep") == "deep"
    assert _normalize_analysis_depth(None) == "basic"
    assert _normalize_analysis_depth("invalid") == "basic"


def test_basic_depth_omits_commerce_whitelist() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "commerce_intent": {
                "conversion_objective": "shop_direct",
                "product_price_tier": "not_commerce",
                "creator_type": "kos_seller",
                "verbal_cta_present": True,
                "disclosure_present": True,
                "disclosure_form": "voice",
            },
            "hook_analysis": {
                "first_frame_type": "face",
                "hook_phrase": "x",
                "hook_type": "question",
                "hook_notes": "",
                "hook_timeline": [],
            },
        },
        user_stats={"caption": "hi", "views": 50_000, "commerce_conversion": {"order_count": 80}},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    manifest = build_signal_manifest(ctx)
    deep = select_sections_to_emit(manifest, ctx, depth="deep")
    basic = select_sections_to_emit(manifest, ctx, depth="basic")
    assert "commerce" in deep
    assert "commerce" not in basic
    assert set(basic).issubset(BASIC_SECTION_ALLOWLIST)


def test_manifest_for_prompt_cap_by_depth() -> None:
    manifest = {
        "diagnosis": [
            Signal(
                id=f"s{i}",
                section_id="diagnosis",
                taxonomy_ref="§d",
                salience=1.0 - i * 0.01,
                claim=f"c{i}",
                evidence=[],
            )
            for i in range(6)
        ]
    }
    basic_trim = manifest_for_prompt(manifest, depth="basic")
    deep_trim = manifest_for_prompt(manifest, depth="deep")
    assert len(basic_trim["diagnosis"]) == 3
    assert len(deep_trim["diagnosis"]) == 5


def test_select_sections_default_is_basic() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "commerce_intent": {
                "conversion_objective": "shop_direct",
                "product_price_tier": "not_commerce",
                "creator_type": "kos_seller",
                "verbal_cta_present": True,
                "disclosure_present": True,
                "disclosure_form": "voice",
            },
            "hook_analysis": {
                "first_frame_type": "face",
                "hook_phrase": "x",
                "hook_type": "question",
                "hook_notes": "",
                "hook_timeline": [],
            },
        },
        user_stats={"caption": "hi", "views": 50_000, "commerce_conversion": {"order_count": 80}},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    manifest = build_signal_manifest(ctx)
    default_sections = select_sections_to_emit(manifest, ctx)
    basic_sections = select_sections_to_emit(manifest, ctx, depth="basic")
    assert default_sections == basic_sections
    assert "commerce" not in default_sections


def test_upsell_locked_sections_basic_only() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "commerce_intent": {
                "conversion_objective": "shop_direct",
                "product_price_tier": "not_commerce",
                "creator_type": "kos_seller",
                "verbal_cta_present": True,
                "disclosure_present": True,
                "disclosure_form": "voice",
            },
            "hook_analysis": {
                "first_frame_type": "face",
                "hook_phrase": "x",
                "hook_type": "question",
                "hook_notes": "",
                "hook_timeline": [],
            },
        },
        user_stats={"caption": "hi", "views": 50_000, "commerce_conversion": {"order_count": 80}},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    manifest = build_signal_manifest(ctx)
    locked = upsell_locked_sections(manifest, ctx, depth="basic", performance_tier="average")
    assert locked
    assert all(row["section_id"] not in BASIC_SECTION_ALLOWLIST for row in locked)
    commerce = next(row for row in locked if row["section_id"] == "commerce")
    assert int(commerce.get("signal_count") or 0) >= 1
    assert upsell_locked_sections(manifest, ctx, depth="deep", performance_tier="average") == []


def test_upsell_locked_sections_boost_teaser_vi() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={"hook_analysis": {"hook_type": "question", "first_frame_type": "face"}},
        user_stats={
            "views": 120_000,
            "likes": 200,
            "comments": 0,
            "engagement_rate": 0.5,
            "breakout_multiplier": 2.0,
        },
        reference_videos=[{"video_id": "1", "views": 1000}],
        channel_context={"available": True, "sample_size": 5, "median_views": 1000},
        performance_tier="average",
        niche_meta={
            "sample_size": 100,
            "median_er": 4.0,
            "p25_er": 2.5,
            "p75_views": 10_000,
            "p90_views": 50_000,
        },
    )
    manifest = build_signal_manifest(ctx)
    locked = upsell_locked_sections(manifest, ctx, depth="basic", performance_tier="average")
    boost = next((row for row in locked if row["section_id"] == "boost_attribution"), None)
    assert boost is not None
    assert boost.get("teaser_vi")
    assert int(boost.get("signal_count") or 0) >= 1


def test_builder_for_intent_cta_maps_intents() -> None:
    from getviews_pipeline.answer_session import builder_for_intent_cta

    assert builder_for_intent_cta("shot_list") == "script"
    assert builder_for_intent_cta("content_calendar") == "timing"
    assert builder_for_intent_cta("hook_variants") == "ideas"
    assert builder_for_intent_cta("not_a_cta") is None


def test_append_turn_deduct_credits_atomic(monkeypatch) -> None:
    """Deep primary must use single RPC with p_amount=2 — no partial deduct."""
    from unittest.mock import MagicMock

    import getviews_pipeline.answer_session as mod

    rpc_calls: list[dict] = []

    def fake_rpc(name: str, params: dict):
        rpc_calls.append(params)
        resp = MagicMock()
        resp.data = None if params.get("p_amount") == 2 else 0
        chain = MagicMock()
        chain.execute.return_value = resp
        return chain

    user_sb = MagicMock()
    user_sb.rpc.side_effect = fake_rpc

    srv = MagicMock()
    srv.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={
            "id": "sess-1",
            "user_id": "u-1",
            "format": "video",
            "niche_id": 1,
            "title": "t",
            "initial_q": "q",
        }
    )
    srv.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    monkeypatch.setattr(mod, "get_service_client", lambda: srv)
    monkeypatch.setattr(
        "getviews_pipeline.supabase_client.user_supabase",
        lambda _token: user_sb,
    )

    with pytest.raises(RuntimeError, match="insufficient_credits"):
        mod.append_turn(
            "u-1",
            "token",
            "sess-1",
            query="q",
            kind="primary",
            analysis_depth="deep",
        )

    assert rpc_calls == [{"p_user_id": "u-1", "p_amount": 2}]
