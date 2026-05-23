"""§4.8.6 acceptance — 10-video sample: deep prompt signal density vs basic."""

from __future__ import annotations

import statistics

from getviews_pipeline.diagnose_sections import select_sections_to_emit
from getviews_pipeline.signals.registry import (
    build_diagnosis_ctx,
    build_signal_manifest,
    manifest_for_prompt,
)

_NICHE_META = {
    "sample_size": 120,
    "avg_transitions_per_second": 0.85,
    "p25_transitions_per_second": 0.55,
    "p75_transitions_per_second": 1.15,
    "median_er": 2.8,
    "p90_views": 80_000,
    "format_distribution": {"talking_head": 0.4, "vlog_daily": 0.35},
    "hook_distribution": {"question": 0.2, "bold_claim": 0.15},
}


def _rich_user_analysis(**overrides: object) -> dict:
    base = {
        "promotion_type": "affiliate",
        "commerce_intent": {
            "conversion_objective": "shop_direct",
            "product_price_tier": "mid",
            "creator_type": "kos_seller",
            "verbal_cta_present": False,
            "disclosure_present": False,
            "disclosure_form": "none",
        },
        "hook_analysis": {
            "first_frame_type": "product",
            "hook_phrase": "Giá này mà bỏ lỡ thì tiếc",
            "hook_type": "bold_claim",
            "hook_notes": "",
            "hook_timeline": [
                {"t": 0.3, "event": "text_overlay", "note": "hook"},
            ],
            "dialect_detected": "north",
            "hook_layering": "single",
            "hook_body_contract": "weak",
            "price_anchor_manipulation_suspected": True,
        },
        "transitions_per_second": 0.35,
        "safe_zone_status": "bottom_overlay_risk",
        "color_grading_style": "over_processed",
        "text_overlay_font_size_tier": "small",
        "text_overlay_color_emphasis": "high_contrast",
        "tiktok_account_type_heuristic": "business",
        "trending_vpop_sound": True,
        "audio_track_role": "trending_sound",
        "sound_layering": "thin",
        "sound_dialect_audio": "north",
        "creator_persona": "expert_friend",
        "tone": "urgent",
        "slang_terms_used": ["xịn xò", "auto"],
        "slang_freshness_score": 0.35,
        "persona_consistency_signals": {
            "tone_drift": True,
            "register_shift": True,
        },
        "niche_classification": {
            "creator_niche_slug": "beauty",
            "format_axis": "review_unboxing",
        },
        "affiliate_script_phases": {
            "hook": True,
            "problem": False,
            "solution": True,
            "proof": False,
            "cta": False,
        },
        "livestream_funnel_demo": True,
        "share_trigger_type": "su_that_reveal",
        "save_trigger_type": "checklist",
        "loop_architecture_score": 0.35,
        "douyin_origin": {"detected": True, "confidence": 0.7},
        "vietnam_adoption_stage": "early",
        "migration_fit_assessment": "poor",
    }
    base.update(overrides)
    return base


def _sample_contexts() -> list[dict]:
    """Ten varied flop/average profiles exercising F2 + F1 signal extractors."""
    profiles: list[dict] = []
    tiers = ("flop", "average", "hit", "flop", "average", "hit", "flop", "average", "hit", "flop")
    tps_values = (0.25, 0.4, 0.9, 1.4, 0.55, 0.75, 0.3, 1.2, 0.65, 0.45)
    for tier, tps in zip(tiers, tps_values, strict=True):
        ua = _rich_user_analysis(transitions_per_second=tps)
        stats = {
            "caption": "Review kem chống nắng #skincare #affiliate",
            "views": 12_000 if tier == "flop" else 95_000,
            "engagement_rate": 1.8 if tier == "flop" else 4.2,
            "breakout_multiplier": 0.8 if tier == "flop" else 2.4,
            "creator_median_views": 8000,
            "hashtags": ["skincare", "affiliate", "review"],
            "posting_hour": 20,
            "distribution_shape": "spike_then_flat",
            "stats_history": [
                {"day": 1, "views": 500},
                {"day": 2, "views": 8000},
                {"day": 3, "views": 8200},
            ],
            "commerce_conversion": {"order_count": 12},
        }
        profiles.append(
            build_diagnosis_ctx(
                user_analysis=ua,
                user_stats=stats,
                reference_videos=[
                    {
                        "video_id": "ref1",
                        "views": 40_000,
                        "hook_type": "question",
                        "content_format": "talking_head",
                        "reference_eligible": True,
                    },
                    {
                        "video_id": "ref2",
                        "views": 55_000,
                        "hook_type": "how_to",
                        "content_format": "vlog_daily",
                        "reference_eligible": True,
                    },
                ],
                channel_context={
                    "median_views": 8000,
                    "posting_cadence_per_week": 4.5,
                    "recent_breakout_count": 2 if tier == "hit" else 0,
                },
                performance_tier=tier,
                niche_meta=_NICHE_META,
                content_format="review_unboxing",
                niche_name="Beauty review",
                corpus_size=120,
                compliance_flags=[
                    {"flag": "restricted_phrase", "severity": "high"},
                ],
            )
        )
    return profiles


def _mean_signals_per_emitted_section(ctx: dict, *, depth: str) -> float:
    manifest = build_signal_manifest(ctx)
    sections = select_sections_to_emit(manifest, ctx, depth=depth)
    trimmed = manifest_for_prompt(manifest, depth=depth)
    if not sections:
        return 0.0
    counts = [len(trimmed.get(sid, [])) for sid in sections]
    return float(statistics.mean(counts))


def test_section_486_ten_video_deep_vs_basic_signal_density() -> None:
    """Feature-map §4.8.6 — deep prompt averages ≥2 signals/section vs basic."""
    contexts = _sample_contexts()
    assert len(contexts) == 10

    basic_means = [_mean_signals_per_emitted_section(ctx, depth="basic") for ctx in contexts]
    deep_means = [_mean_signals_per_emitted_section(ctx, depth="deep") for ctx in contexts]

    avg_basic = statistics.mean(basic_means)
    avg_deep = statistics.mean(deep_means)

    assert avg_deep >= 2.0, f"deep avg {avg_deep:.2f} < 2.0"
    assert avg_deep > avg_basic, (
        f"deep avg {avg_deep:.2f} not greater than basic avg {avg_basic:.2f}"
    )
