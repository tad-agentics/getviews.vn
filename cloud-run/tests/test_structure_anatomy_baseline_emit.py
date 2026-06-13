"""Structure anatomy baseline — emit editing/sound/persona when data exists, not only gap signals."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import select_sections_to_emit
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest


def _fashion_affiliate_ctx(*, scenes: list | None = None, **ua_overrides: object) -> dict:
    ua: dict = {
        "scenes": scenes if scenes is not None else [{"type": "outfit_mirror", "start": 0.0, "end": 4.0}],
        "audio_transcript": "Phối đồ mùa hè cho chị em nha.",
        "has_human_speaking_to_camera": True,
        "commerce_intent": {"conversion_objective": "affiliate_shopee"},
    }
    ua.update(ua_overrides)
    return build_diagnosis_ctx(
        user_analysis=ua,
        user_stats={"sound_id": "trend-123", "music_title": "Summer vibe"},
        reference_videos=[{"aweme_id": "peer1"}],
        channel_context=None,
        performance_tier="average",
    )


def test_scene_timeline_emits_full_structure_anatomy_without_gap_signals() -> None:
    ctx = _fashion_affiliate_ctx()
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx)
    assert "script_structure" in out
    assert "editing" in out
    assert "sound" in out
    assert "persona" in out


def test_scene_timeline_skips_sound_when_truly_silent() -> None:
    ctx = _fashion_affiliate_ctx(
        audio_transcript="",
        has_human_speaking_to_camera=False,
    )
    ctx["user_stats"] = {}
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx)
    assert "script_structure" in out
    assert "editing" in out
    assert "sound" not in out


def test_scene_timeline_skips_persona_without_observables() -> None:
    ctx = _fashion_affiliate_ctx(
        scenes=[],
        audio_transcript="",
        has_human_speaking_to_camera=False,
    )
    ctx["user_analysis"].pop("scenes", None)
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx)
    assert "script_structure" not in out
    assert "persona" not in out
