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
from getviews_pipeline.signals.salience import section_emit_threshold
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


def test_section_emit_threshold_default() -> None:
    assert section_emit_threshold(depth="basic") == 0.5
    assert section_emit_threshold(depth="deep") == 0.45


def test_deep_relax_salience_can_be_disabled(monkeypatch) -> None:
    from getviews_pipeline import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "getviews_deep_relax_salience", False)
    assert section_emit_threshold(depth="basic") == 0.5
    assert section_emit_threshold(depth="deep") == 0.5


def test_deep_relax_salience_lowers_threshold_only_for_deep() -> None:
    assert section_emit_threshold(depth="basic") == 0.5
    assert section_emit_threshold(depth="deep") == 0.45


def test_deep_relax_salience_emits_borderline_metadata_section(monkeypatch) -> None:
    from getviews_pipeline import settings as settings_mod

    ctx = build_diagnosis_ctx(
        user_analysis={"hook_analysis": {"hook_type": "question", "first_frame_type": "face"}},
        user_stats={"caption": "hi", "views": 50_000},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    manifest = {
        "metadata": [
            Signal(
                id="metadata_caption_density",
                section_id="metadata",
                taxonomy_ref="§1.6",
                salience=0.47,
                claim="Caption mỏng hơn median ngách.",
                evidence=[],
            )
        ]
    }
    assert "metadata" in select_sections_to_emit(manifest, ctx, depth="deep")
    assert "metadata" not in select_sections_to_emit(manifest, ctx, depth="basic")
    monkeypatch.setattr(settings_mod.settings, "getviews_deep_relax_salience", False)
    assert "metadata" not in select_sections_to_emit(manifest, ctx, depth="deep")


def test_normalize_source_entry_allowlist() -> None:
    from getviews_pipeline.report_types import normalize_source_entry

    assert normalize_source_entry("trends") == "trends"
    assert normalize_source_entry("composer") == "composer"
    assert normalize_source_entry("intent_cta") == "intent_cta"
    assert normalize_source_entry("ideas") is None
    assert normalize_source_entry(None) is None
    assert normalize_source_entry("") is None


def test_append_turn_persists_source_entry_on_primary_video(monkeypatch) -> None:
    """§4.6 — turn-1 video payload echoes allowlisted source_entry."""
    from unittest.mock import MagicMock

    import getviews_pipeline.answer_session as mod
    from getviews_pipeline.report_types import VideoPayload

    video_inner = {
        "video_id": "7630766288574369045",
        "mode": "win",
        "meta": {
            "creator": "creatorx",
            "views": 250_000,
            "likes": 18_000,
            "comments": 800,
            "shares": 1_200,
            "save_rate": 0.04,
            "duration_sec": 28.5,
            "thumbnail_url": "https://r2.test/thumbnails/x.png",
            "date_posted": "2026-04-15",
            "title": "Đây là cách",
            "niche_label": "Làm đẹp",
            "retention_source": "modeled",
        },
        "kpis": [],
        "segments": [],
        "hook_phases": [],
        "errors": [],
        "retention_curve": [],
        "niche_benchmark_curve": [],
        "niche_meta": {
            "avg_views": 100_000,
            "avg_retention": 0.55,
            "avg_ctr": 0.04,
            "sample_size": 200,
            "winners_sample_size": 30,
        },
    }

    def fake_build_video_report(**_kwargs: object) -> dict:
        return dict(video_inner)

    monkeypatch.setattr(
        "getviews_pipeline.report_video.build_video_report",
        fake_build_video_report,
    )

    user_sb = MagicMock()
    user_sb.rpc.return_value.execute.return_value = MagicMock(data=0)

    srv = MagicMock()

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "answer_sessions":
            chain = m.select.return_value.eq.return_value.single.return_value
            chain.execute.return_value = MagicMock(
                data={
                    "id": "sess-1",
                    "user_id": "u-1",
                    "format": "video",
                    "niche_id": 1,
                    "title": "t",
                    "initial_q": "q",
                    "intent_type": "trend_spike",
                }
            )
            m.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        elif name == "answer_turns":
            m.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            m.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "turn-1", "turn_index": 0, "kind": "primary"}]
            )
        elif name == "usage_events":
            m.insert.return_value.execute.return_value = MagicMock(data=[])
        else:
            raise AssertionError(f"unexpected table {name!r}")
        return m

    srv.table.side_effect = table
    monkeypatch.setattr(mod, "get_service_client", lambda: srv)
    monkeypatch.setattr(
        "getviews_pipeline.supabase_client.user_supabase",
        lambda _token: user_sb,
    )

    out = mod.append_turn(
        "u-1",
        "token",
        "sess-1",
        query="https://www.tiktok.com/@x/video/1",
        kind="primary",
        source_entry="trends",
    )

    assert out["payload"]["kind"] == "video"
    assert out["payload"]["report"]["source_entry"] == "trends"
    VideoPayload.model_validate(out["payload"]["report"])


def test_append_turn_skips_source_entry_on_follow_up(monkeypatch) -> None:
    from unittest.mock import MagicMock

    import getviews_pipeline.answer_session as mod

    def fake_build_timing_report(*_args: object, **_kwargs: object) -> dict:
        from getviews_pipeline.report_timing import build_fixture_timing_report

        return build_fixture_timing_report()

    monkeypatch.setattr(mod, "build_timing_report", fake_build_timing_report)

    user_sb = MagicMock()
    srv = MagicMock()

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "answer_sessions":
            chain = m.select.return_value.eq.return_value.single.return_value
            chain.execute.return_value = MagicMock(
                data={
                    "id": "sess-1",
                    "user_id": "u-1",
                    "format": "pattern",
                    "niche_id": 1,
                    "intent_type": "trend_spike",
                }
            )
            m.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        elif name == "answer_turns":
            m.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"turn_index": 0}]
            )
            m.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "turn-2", "turn_index": 1, "kind": "timing"}]
            )
        elif name == "usage_events":
            m.insert.return_value.execute.return_value = MagicMock(data=[])
        else:
            raise AssertionError(f"unexpected table {name!r}")
        return m

    srv.table.side_effect = table
    monkeypatch.setattr(mod, "get_service_client", lambda: srv)
    monkeypatch.setattr(
        "getviews_pipeline.supabase_client.user_supabase",
        lambda _token: user_sb,
    )

    out = mod.append_turn(
        "u-1",
        "token",
        "sess-1",
        query="khi nào nên post?",
        kind="timing",
        source_entry="intent_cta",
    )

    assert out["payload"]["kind"] == "timing"
    assert "source_entry" not in out["payload"]["report"]
