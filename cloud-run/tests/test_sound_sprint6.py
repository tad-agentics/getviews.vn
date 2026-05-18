"""Sprint 6 — §6 sound signals + lifecycle helper."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import select_sections_to_emit
from getviews_pipeline.layer0_sound import infer_sound_lifecycle_phase, normalize_lifecycle_phase
from getviews_pipeline.signals.base import Signal
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest
from getviews_pipeline.signals.sound import extract_sound_signals


def test_infer_sound_lifecycle_emerging() -> None:
    assert infer_sound_lifecycle_phase(0, 5) == "emerging"
    assert infer_sound_lifecycle_phase(1, 4) == "emerging"


def test_infer_sound_lifecycle_growth() -> None:
    assert infer_sound_lifecycle_phase(4, 10) == "growth"


def test_infer_sound_lifecycle_peak() -> None:
    assert infer_sound_lifecycle_phase(6, 6) == "peak"


def test_infer_sound_lifecycle_decline() -> None:
    assert infer_sound_lifecycle_phase(10, 3) == "decline"


def test_normalize_lifecycle_phase() -> None:
    assert normalize_lifecycle_phase("EMERGING") == "emerging"
    assert normalize_lifecycle_phase("nope") is None


def test_sound_lifecycle_from_trending_profile() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={},
        user_stats={
            "sound_id": "abc",
            "trending_sound_profile": {"lifecycle_phase": "emerging"},
        },
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
        niche_meta={},
    )
    sigs = [s for s in extract_sound_signals(ctx) if s.id == "sound_lifecycle_phase"]
    assert len(sigs) == 1
    assert sigs[0].salience == 0.65
    assert sigs[0].section_id == "sound"


def test_sound_lifecycle_from_radar_accelerating_hot() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={},
        user_stats={"sound_id": "s1"},
        reference_videos=[],
        channel_context=None,
        performance_tier="hit",
        niche_meta={
            "sound_radar": {
                "accelerating": [
                    {"sound_id": "s1", "delta_pct": 999.0},
                ],
            },
        },
    )
    sigs = [s for s in extract_sound_signals(ctx) if s.id == "sound_lifecycle_phase"]
    assert len(sigs) == 1
    assert "emerging" in sigs[0].claim


def test_cml_strip_risk_only_when_explicit_false() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={"promotion_type": "affiliate"},
        user_stats={
            "sound_id": "x",
            "account_commercial_heuristic": True,
            "trending_sound_profile": {"commercial_music_library_eligible": False},
        },
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    sigs = [s for s in extract_sound_signals(ctx) if s.id == "sound_cml_strip_risk"]
    assert len(sigs) == 1
    assert sigs[0].salience == 0.85


def test_dialect_audio_mismatch() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "hook_analysis": {"dialect_detected": "hue"},
            "sound_dialect_audio": "southern",
        },
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    sigs = [s for s in extract_sound_signals(ctx) if s.id == "sound_dialect_audio_mismatch"]
    assert len(sigs) == 1


def test_sound_layering_mukbang_thin() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={"sound_layering": "thin", "topics": ["mukbang"]},
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
        content_format="mukbang",
    )
    sigs = [s for s in extract_sound_signals(ctx) if s.id == "sound_layering_thin_mukbang"]
    assert len(sigs) == 1


def test_sound_section_emits_via_manifest() -> None:
    manifest = {
        "sound": [
            Signal(
                id="sound_lifecycle_phase",
                section_id="sound",
                taxonomy_ref="§6",
                salience=0.65,
                claim="test",
                evidence=[],
            ),
        ],
    }
    ctx = build_diagnosis_ctx(
        user_analysis={"audio_track_role": "trending_sound"},
        user_stats={"sound_id": "z"},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    sections = select_sections_to_emit(manifest, ctx)
    assert "sound" in sections
