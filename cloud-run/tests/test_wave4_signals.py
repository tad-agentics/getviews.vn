"""W4-3 — Win remainder + P0 flop signals."""

from __future__ import annotations

from getviews_pipeline.signals.hook import extract_niche_hook_percentile_gap_signal
from getviews_pipeline.signals.reference import extract_niche_format_underrepresented_signal
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest
from getviews_pipeline.signals.win import (
    extract_win_breakout_vs_channel_signal,
    extract_win_format_in_growth_signal,
    extract_win_replicable_cta_signal,
)


def _hit_ctx(**overrides) -> dict:
    content_format = str(overrides.pop("content_format", "product_closeup"))
    performance_tier = str(overrides.pop("performance_tier", "hit"))
    base = build_diagnosis_ctx(
        user_analysis={
            "hook_analysis": {"hook_type": "question", "first_frame_type": "face"},
            "cta": "Inbox mình để nhận mẫu",
            "commerce_intent": {"verbal_cta_present": True},
        },
        user_stats={
            "views": 50_000,
            "engagement_rate": 6.0,
            "breakout_multiplier": 3.2,
            "creator_median_views": 15_000,
        },
        reference_videos=[{"video_id": "1", "views": 1000}],
        channel_context={"available": True, "sample_size": 5, "median_views": 15000},
        performance_tier=performance_tier,
        niche_meta={
            "sample_size": 80,
            "format_distribution": {"product_closeup": 45, "unboxing_process": 30},
            "hook_distribution": {"question": 40, "bold_claim": 35},
        },
        content_format=content_format,
    )
    base.update(overrides)
    return base


def test_win_breakout_vs_channel():
    sigs = extract_win_breakout_vs_channel_signal(_hit_ctx())
    assert any(s.id == "win_breakout_vs_channel" for s in sigs)


def test_win_format_in_growth():
    sigs = extract_win_format_in_growth_signal(_hit_ctx())
    assert any(s.id == "win_format_in_growth" for s in sigs)


def test_win_replicable_cta():
    sigs = extract_win_replicable_cta_signal(_hit_ctx())
    assert any(s.id == "win_replicable_cta" for s in sigs)


def test_niche_format_underrepresented():
    ctx = _hit_ctx(content_format="lifestyle_model")
    sigs = extract_niche_format_underrepresented_signal(ctx)
    assert any(s.id == "niche_format_underrepresented" for s in sigs)


def test_niche_hook_percentile_gap():
    ctx = build_diagnosis_ctx(
        user_analysis={"hook_analysis": {"hook_type": "dialect_identity", "first_frame_type": "face"}},
        user_stats={"views": 1000, "engagement_rate": 3.0},
        reference_videos=[{"video_id": "1"}],
        channel_context=None,
        performance_tier="flop",
        niche_meta={
            "sample_size": 80,
            "hook_distribution": {"question": 50, "bold_claim": 40, "dialect_identity": 2},
        },
    )
    sigs = extract_niche_hook_percentile_gap_signal(ctx)
    assert any(s.id == "niche_hook_percentile_gap" for s in sigs)


def test_manifest_includes_new_signal_ids():
    manifest = build_signal_manifest(_hit_ctx(content_format="lifestyle_model"))
    all_ids = {s.id for lst in manifest.values() for s in lst}
    assert "win_breakout_vs_channel" in all_ids
    assert "niche_format_underrepresented" in all_ids
