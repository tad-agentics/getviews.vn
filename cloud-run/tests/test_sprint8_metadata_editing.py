"""Sprint 8 — §1 metadata + §5 editing signals."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import EDITING_SECTION_MIN_SALIENCE, select_sections_to_emit
from getviews_pipeline.signals.editing import extract_color_grading_signal, extract_editing_signals
from getviews_pipeline.signals.metadata import extract_metadata_signals, extract_safe_zone_signal
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest


def test_metadata_safe_zone_signal() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={"safe_zone_status": "bottom_overlay_risk"},
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    sigs = extract_safe_zone_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].section_id == "metadata"
    assert sigs[0].salience == 0.6


def test_metadata_business_vpop_signal() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "tiktok_account_type_heuristic": "business",
            "trending_vpop_sound": True,
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    sigs = [s for s in extract_metadata_signals(ctx) if s.id == "metadata_business_vpop_cml_friction"]
    assert len(sigs) == 1
    assert sigs[0].salience == 0.55


def test_editing_color_mismatch_beauty_desaturated() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "color_grading_style": "desaturated_serious",
            "niche_classification": {"creator_niche_slug": "beauty", "format_axis": "review_unboxing"},
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    sigs = extract_color_grading_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].section_id == "editing"
    assert sigs[0].salience == 0.45


def test_editing_overlay_small_emits() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={"text_overlay_font_size_tier": "small"},
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
    )
    sigs = extract_editing_signals(ctx)
    assert any(s.id == "editing_text_overlay_readability" for s in sigs)


def test_sections_emit_metadata_and_editing() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "safe_zone_status": "bottom_overlay_risk",
            "color_grading_style": "over_processed",
            "niche_classification": {"creator_niche_slug": "food", "format_axis": "vlog_daily"},
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx, depth="deep")
    assert "metadata" in out
    assert "editing" in out
    assert out.index("metadata") < out.index("editing")


def test_editing_section_gate_uses_floor_salience() -> None:
    """0.4 overlay signal must open ``editing`` (below SECTION_EMIT_THRESHOLD 0.5)."""
    ctx = build_diagnosis_ctx(
        user_analysis={
            "text_overlay_font_size_tier": "small",
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    manifest = build_signal_manifest(ctx)
    overlay = [s for s in manifest.get("editing", []) if s.id == "editing_text_overlay_readability"]
    assert len(overlay) == 1
    assert overlay[0].salience == EDITING_SECTION_MIN_SALIENCE
    out = select_sections_to_emit(manifest, ctx, depth="deep")
    assert "editing" in out
