"""Sprint 3 §11 — creator persona, slang, persona section signals."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import PERSONA_SECTION_MIN_SALIENCE, select_sections_to_emit
from getviews_pipeline.models import VideoAnalysis
from getviews_pipeline.signals.persona import extract_persona_signals
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest
from getviews_pipeline.vietnamese_slang import merge_lexicon_slang_into_video_analysis_dict


def _minimal_video_dict(**overrides: object) -> dict:
    base = {
        "hook_analysis": {
            "first_frame_type": "face",
            "hook_phrase": "x",
            "hook_type": "how_to",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "has_human_speaking_to_camera": True,
        "has_expressed_opinion_or_question": False,
        "text_overlays": [],
        "scenes": [{"type": "face_to_camera", "start": 0.0, "end": 5.0}],
        "transitions_per_second": 0.2,
        "energy_level": "medium",
        "key_timestamps": [],
        "audio_transcript": "Mình test producrt này ok nha.",
        "tone": "conversational",
        "topics": [],
        "key_messages": [],
        "cta": None,
        "content_direction": {"what_works": "x", "suggested_angles": []},
        "target_audience": "",
        "pain_points": [],
        "promotion_type": "organic",
        "style_tags": [],
    }
    base.update(overrides)
    return base


def test_creator_persona_slugs_validate() -> None:
    for slug in (
        "chuyen_gia",
        "ban_than",
        "nguoi_trai_nghiem_that",
        "hai_huoc_vung_mien",
        "chu_shop_kos",
        "anh_chi_mentor",
    ):
        d = _minimal_video_dict(creator_persona=slug)
        m = VideoAnalysis.model_validate(d)
        assert m.creator_persona == slug


def test_merge_lexicon_finds_plus_one_may() -> None:
    d = _minimal_video_dict(
        audio_transcript="Ae ơi +1 máy cho tụi mình đi",
        slang_terms_used=[],
    )
    merge_lexicon_slang_into_video_analysis_dict(d)
    assert any("+1 máy" in str(t) for t in (d.get("slang_terms_used") or []))


def test_persona_mismatch_signal() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "creator_persona": "hai_huoc_vung_mien",
        },
        user_stats={"caption": "", "views": 1},
        reference_videos=[],
        channel_context={
            "available": True,
            "sample_size": 5,
            "dominant_creator_persona": "chuyen_gia",
        },
        performance_tier="average",
    )
    ids = [s.id for s in extract_persona_signals(ctx)]
    assert "persona_channel_baseline_mismatch" in ids


def test_persona_authenticity_signal_when_no_negative_markers() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "creator_persona": "nguoi_trai_nghiem_that",
            "audio_transcript": "Sản phẩm này rất tuyệt vời mọi người nên mua.",
        },
        user_stats={"caption": "", "views": 1},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    ids = [s.id for s in extract_persona_signals(ctx)]
    assert "persona_authenticity_weak_negative_markers" in ids


def test_slang_dated_signal() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "slang_freshness_score": "dated",
            "slang_terms_used": ["xì pam"],
        },
        user_stats={"caption": "", "views": 1},
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
    )
    ids = [s.id for s in extract_persona_signals(ctx)]
    assert "persona_slang_dated" in ids


def test_dialect_expert_tension_signal() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "creator_persona": "chuyen_gia",
            "hook_analysis": {
                "first_frame_type": "face",
                "hook_phrase": "x",
                "hook_type": "how_to",
                "hook_notes": "",
                "hook_timeline": [],
                "dialect_detected": "southern",
            },
        },
        user_stats={"caption": "", "views": 1},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    ids = [s.id for s in extract_persona_signals(ctx)]
    assert "persona_dialect_expert_tension" in ids


def test_persona_section_emits_when_salient() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "creator_persona": "ban_than",
            "audio_transcript": "ok",
        },
        user_stats={"caption": "", "views": 1},
        reference_videos=[],
        channel_context={
            "available": True,
            "sample_size": 5,
            "dominant_creator_persona": "chuyen_gia",
        },
        performance_tier="hit",
    )
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx)
    sig = next(s for s in manifest["persona"] if s.id == "persona_channel_baseline_mismatch")
    assert sig.salience >= PERSONA_SECTION_MIN_SALIENCE
    assert "persona" in out
