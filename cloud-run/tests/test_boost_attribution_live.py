"""W4-2 — live boost_attribution section (F1 deep only)."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import select_sections_to_emit
from getviews_pipeline.signals.distribution import extract_live_boost_attribution_signals
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest


def test_boost_views_er_mismatch_fires():
    ctx = build_diagnosis_ctx(
        user_analysis={"hook_analysis": {"hook_type": "question", "first_frame_type": "face"}},
        user_stats={
            "views": 120_000,
            "likes": 200,
            "comments": 0,
            "engagement_rate": 0.5,
        },
        reference_videos=[{"video_id": "1", "views": 1000}],
        channel_context=None,
        performance_tier="average",
        niche_meta={
            "sample_size": 100,
            "median_er": 4.0,
            "p25_er": 2.5,
            "p75_views": 10_000,
            "p90_views": 50_000,
        },
    )
    sigs = extract_live_boost_attribution_signals(ctx)
    assert any(s.id == "boost_views_er_mismatch" for s in sigs)


def test_boost_attribution_deep_only_not_in_basic():
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
    basic = select_sections_to_emit(manifest, ctx, depth="basic")
    deep = select_sections_to_emit(manifest, ctx, depth="deep")
    assert "boost_attribution" not in basic
    assert "boost_attribution" in deep
