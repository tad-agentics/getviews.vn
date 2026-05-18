"""Sprint 7 — §7 triggers + §4 script structure signals."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import select_sections_to_emit
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest
from getviews_pipeline.signals.script import extract_script_signals
from getviews_pipeline.signals.triggers import extract_trigger_signals


def test_su_that_tran_trui_heuristic() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "audio_transcript": "Mình đã thử serum này một tuần nhưng thất vọng toàn tập.",
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    sigs = [s for s in extract_trigger_signals(ctx) if s.id == "trigger_su_that_tran_trui"]
    assert len(sigs) == 1
    assert sigs[0].section_id == "diagnosis"


def test_share_save_triggers() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "share_trigger_type": "utility_reference",
            "save_trigger_type": "how_to_checklist",
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="hit",
    )
    ids = {s.id for s in extract_trigger_signals(ctx)}
    assert "trigger_share_archetype" in ids
    assert "trigger_save_archetype" in ids


def test_five_phase_affiliate_gap() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "commerce_intent": {"conversion_objective": "affiliate_shopee"},
            "affiliate_script_phases": {
                "hook_attention": True,
                "product_showcase": False,
                "usage_demo": False,
                "social_proof": True,
                "closing_cta": True,
            },
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
    )
    sigs = extract_script_signals(ctx)
    assert any(s.id == "script_affiliate_five_phase_gap" for s in sigs)
    gap = next(s for s in sigs if s.id == "script_affiliate_five_phase_gap")
    assert gap.salience == 0.75
    assert gap.section_id == "script_structure"


def test_five_phase_sparse_skips() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "commerce_intent": {"conversion_objective": "shop_direct"},
            "affiliate_script_phases": {
                "hook_attention": None,
                "product_showcase": None,
                "usage_demo": False,
                "social_proof": None,
                "closing_cta": None,
            },
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    assert extract_script_signals(ctx) == []


def test_livestream_over_complete() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "commerce_intent": {"conversion_objective": "livestream_funnel"},
            "livestream_funnel_demo": "over_complete",
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    sigs = extract_script_signals(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "script_livestream_demo_too_complete"
    assert sigs[0].salience == 0.6


def test_script_structure_section_gate() -> None:
    manifest = build_signal_manifest(
        build_diagnosis_ctx(
            user_analysis={
                "commerce_intent": {"conversion_objective": "affiliate_shopee"},
                "affiliate_script_phases": {
                    "hook_attention": False,
                    "product_showcase": False,
                    "usage_demo": True,
                    "social_proof": True,
                    "closing_cta": True,
                },
            },
            user_stats={},
            reference_videos=[],
            channel_context=None,
            performance_tier="average",
        ),
    )
    ctx = build_diagnosis_ctx(
        user_analysis={},
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    out = select_sections_to_emit(manifest, ctx)
    assert "script_structure" in out


def test_manifest_includes_trigger_and_script() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "audio_transcript": "Không giống quảng cáo chút nào, mình thất vọng.",
            "commerce_intent": {"conversion_objective": "affiliate_shopee"},
            "affiliate_script_phases": {
                "hook_attention": True,
                "product_showcase": False,
                "usage_demo": False,
                "social_proof": True,
                "closing_cta": True,
            },
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
    )
    m = build_signal_manifest(ctx)
    assert m.get("diagnosis")
    assert m.get("script_structure")
