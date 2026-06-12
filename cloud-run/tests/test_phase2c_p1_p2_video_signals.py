"""Phase 2c.2 — video P1 + P2 signal backlog."""

from __future__ import annotations

from datetime import UTC, datetime

from getviews_pipeline.signals.channel import extract_channel_video_vs_eligible_peers_signal
from getviews_pipeline.signals.commerce import (
    extract_commerce_price_tier_structure_signal,
    extract_commerce_silent_cta_signal,
)
from getviews_pipeline.signals.distribution import extract_boost_tradeoff_education_signal
from getviews_pipeline.signals.editing import extract_editing_broll_ratio_low_signal
from getviews_pipeline.signals.engagement import (
    extract_comment_hook_missing_signal,
    extract_save_trigger_weak_signal,
)
from getviews_pipeline.signals.hook import extract_hook_vague_specificity_signal
from getviews_pipeline.signals.metadata import (
    extract_caption_density_signal,
    extract_hashtag_volume_gap_signal,
)
from getviews_pipeline.signals.persona import extract_tone_distribution_gap_signal
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest
from getviews_pipeline.signals.script import extract_zero_value_stretch_signal
from getviews_pipeline.signals.sound import (
    extract_sound_no_audio_hook_window_signal,
    extract_sound_trending_mismatch_signal,
)

PHASE2C_IDS = frozenset(
    {
        "hook_vague_specificity",
        "boost_tradeoff_education",
        "commerce_silent_cta",
        "commerce_price_tier_structure",
        "metadata_hashtag_volume_gap",
        "metadata_caption_density",
        "editing_broll_ratio_low",
        "sound_trending_mismatch",
        "sound_no_audio_hook_window",
        "persona_tone_distribution_gap",
        "script_zero_value_stretch",
        "engagement_comment_hook_missing",
        "engagement_save_trigger_weak",
        "channel_video_vs_eligible_peers",
        "seeding_comment_pattern",
    }
)


def _niche_meta(**overrides: object) -> dict:
    base = {
        "sample_size": 80,
        "avg_hashtag_count": 6.0,
        "pct_has_caption_text": 72.0,
        "tone_distribution": {"entertaining": 50, "informative": 30, "emotional": 20},
        "sound_radar": {
            "accelerating": [{"sound_id": "s1"}, {"sound_id": "s2"}],
            "peaking": [],
            "cooling": [],
        },
        "p75_views": 10_000,
        "p90_views": 50_000,
        "p25_er": 2.5,
        "median_er": 4.0,
    }
    base.update(overrides)
    return base


def _ctx(**overrides: object) -> dict:
    ua = {
        "hook_analysis": {
            "hook_phrase": "xem clip nay nhe",
            "hook_type": "question",
            "hook_timeline": [],
        },
        "tone": "dramatic",
        "audio_transcript": "Hom nay minh se review chi tiet san pham nay cho moi nguoi.",
        "scenes": [
            {"type": "face_to_camera", "subject": "face", "pace": "medium", "start": 0, "end": 10},
            {"type": "face_to_camera", "subject": "face", "pace": "static", "start": 10, "end": 20},
            {"type": "face_to_camera", "subject": "face", "pace": "static", "start": 20, "end": 35},
        ],
        "video_duration": 35,
        "commerce_intent": {
            "conversion_objective": "affiliate_shopee",
            "product_price_tier": "under_150k",
            "verbal_cta_present": False,
        },
        "text_overlays": [{"text": "Mua trong gio live nhe"}],
    }
    base = build_diagnosis_ctx(
        user_analysis=ua,
        user_stats={
            "views": 5000,
            "engagement_rate": 3.0,
            "caption": "short",
            "hashtag_count": 2,
            "posted_at": datetime(2026, 5, 13, 8, 0, 0, tzinfo=UTC).isoformat(),
            "sound_id": "other_sound",
        },
        reference_videos=[
            {"views": 20_000, "reference_eligible": True, "posted_at": "2026-05-10T19:00:00+07:00"},
            {"views": 18_000, "reference_eligible": True, "posted_at": "2026-05-11T20:00:00+07:00"},
        ],
        channel_context={
            "available": True,
            "sample_size": 5,
            "median_views": 8000,
            "posting_hour_views": {"8": 1200, "19": 9000, "20": 8500},
        },
        performance_tier="flop",
        niche_meta=_niche_meta(),
    )
    base.update(overrides)
    return base


def test_hook_vague_specificity_fires() -> None:
    sigs = extract_hook_vague_specificity_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "hook_vague_specificity"


def test_boost_tradeoff_education_medium_plus() -> None:
    ctx = _ctx(
        user_stats={
            "views": 120_000,
            "comments": 0,
            "engagement_rate": 0.4,
            "caption": "x",
            "hashtag_count": 2,
        }
    )
    sigs = extract_boost_tradeoff_education_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "boost_tradeoff_education"


def test_commerce_silent_cta() -> None:
    sigs = extract_commerce_silent_cta_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "commerce_silent_cta"


def test_commerce_price_tier_structure() -> None:
    sigs = extract_commerce_price_tier_structure_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "commerce_price_tier_structure"


def test_metadata_hashtag_volume_gap() -> None:
    sigs = extract_hashtag_volume_gap_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "metadata_hashtag_volume_gap"


def test_metadata_caption_density() -> None:
    sigs = extract_caption_density_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "metadata_caption_density"


def test_editing_broll_ratio_low() -> None:
    sigs = extract_editing_broll_ratio_low_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "editing_broll_ratio_low"


def test_sound_trending_mismatch() -> None:
    sigs = extract_sound_trending_mismatch_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "sound_trending_mismatch"


def test_sound_no_audio_hook_window() -> None:
    sigs = extract_sound_no_audio_hook_window_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "sound_no_audio_hook_window"


def test_persona_tone_distribution_gap() -> None:
    sigs = extract_tone_distribution_gap_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "persona_tone_distribution_gap"


def test_script_zero_value_stretch() -> None:
    sigs = extract_zero_value_stretch_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "script_zero_value_stretch"


def test_engagement_comment_hook_missing() -> None:
    sigs = extract_comment_hook_missing_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "engagement_comment_hook_missing"


def test_engagement_save_trigger_weak_hit_tier() -> None:
    ctx = _ctx(performance_tier="hit", content_format="how_to")
    ctx["user_analysis"]["save_trigger_type"] = "none"
    sigs = extract_save_trigger_weak_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "engagement_save_trigger_weak"


def test_channel_video_vs_eligible_peers() -> None:
    ctx = _ctx(user_stats={"views": 3000, "engagement_rate": 2.0, "caption": "x", "hashtag_count": 2})
    sigs = extract_channel_video_vs_eligible_peers_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "channel_video_vs_eligible_peers"


def test_manifest_includes_all_phase2c_ids() -> None:
    ctx_main = _ctx(
        user_stats={
            "views": 5000,
            "engagement_rate": 3.0,
            "caption": "x",
            "hashtag_count": 2,
            "posted_at": datetime(2026, 5, 13, 8, 0, 0, tzinfo=UTC).isoformat(),
            "sound_id": "other_sound",
        },
        performance_tier="hit",
        content_format="how_to",
    )
    ctx_main["user_analysis"]["save_trigger_type"] = "none"

    ctx_boost = _ctx(
        user_stats={
            "views": 120_000,
            "comments": 0,
            "engagement_rate": 0.4,
            "caption": "x",
            "hashtag_count": 2,
            "posted_at": datetime(2026, 5, 13, 8, 0, 0, tzinfo=UTC).isoformat(),
            "sound_id": "other_sound",
        }
    )

    ctx_channel = _ctx(
        user_stats={"views": 3000, "engagement_rate": 2.0, "caption": "x", "hashtag_count": 2}
    )

    # 2026-06-12: seeding_comment_pattern now requires boost suspicion —
    # views must clear the boost p90 (50K×1.8=90K) so the live classification
    # is suspect, not organic_confident (which suppresses the claim).
    ctx_seeding = _ctx(
        user_stats={
            "views": 120_000,
            "comments": 8,
            "engagement_rate": 0.3,
            "caption": "x",
            "hashtag_count": 2,
        },
        comment_radar={
            "sampled": 10,
            "spam_skipped_ratio": 0.6,
            "sentiment": {"neutral_pct": 90.0, "positive_pct": 5.0, "negative_pct": 5.0},
        },
    )

    found: set[str] = set()
    for ctx in (ctx_main, ctx_boost, ctx_channel, ctx_seeding):
        manifest = build_signal_manifest(ctx)
        found |= {s.id for lst in manifest.values() for s in lst}

    missing = PHASE2C_IDS - found
    assert not missing, f"missing manifest ids: {missing}"
