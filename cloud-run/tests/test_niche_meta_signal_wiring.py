"""§4.8.4 — live niche_meta must carry MV signal fields into build_diagnosis_ctx."""

from __future__ import annotations

from unittest.mock import MagicMock

from getviews_pipeline.signals.hook import extract_niche_hook_percentile_gap_signal
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest
from getviews_pipeline.video_niche_benchmark import (
    build_niche_benchmark_payload,
    enrich_niche_meta_for_signals,
)


def test_enrich_niche_meta_copies_distributions_from_cci_row() -> None:
    slim = {"avg_views": 50_000, "sample_size": 60, "median_er": 4.5}
    row = {
        "content_class_id": 3,
        "sample_size": 60,
        "median_er": 4.5,
        "hook_distribution": {"question": 40, "bold_claim": 35},
        "tone_distribution": {"casual": 55, "professional": 20},
        "avg_transitions_per_second": 0.42,
        "avg_hashtag_count": 4.2,
        "pct_has_caption_text": 72.0,
        "claim_tier": "strong",
        "median_views": 40_000,
    }
    out = enrich_niche_meta_for_signals(
        slim,
        row,
        sb=None,
        niche_id=2,
        benchmark_axis="content_class",
        content_class_id=3,
    )
    assert out["hook_distribution"] == row["hook_distribution"]
    assert out["tone_distribution"] == row["tone_distribution"]
    assert out["avg_transitions_per_second"] == 0.42
    assert out["claim_tier"] == "strong"
    assert out["p25_er"] == 4.5
    assert out["p90_views"] == 40_000 * 1.8


def test_build_payload_merges_signal_fields_for_live_path() -> None:
    row = {
        "content_class_id": 11,
        "avg_views": 82_000,
        "median_views": 60_000,
        "median_er": 5.0,
        "sample_size": 45,
        "hook_distribution": {"question": 30, "visual_hook": 25},
        "tone_distribution": {"casual": 50},
        "avg_transitions_per_second": 0.35,
        "claim_tier": "moderate",
        "computed_at": "2026-05-01T00:00:00Z",
    }
    payload = build_niche_benchmark_payload(
        row,
        niche_id=4,
        duration_sec=58.0,
        benchmark_axis="content_class",
        content_class_id=11,
    )
    meta = payload["niche_meta"]
    assert meta is not None
    assert meta["hook_distribution"] == row["hook_distribution"]
    assert meta["avg_transitions_per_second"] == 0.35


def test_tier_axis_merges_class_distributions() -> None:
    tier_row = {
        "content_class_id": 11,
        "creator_tier": "micro",
        "sample_size": 40,
        "median_views": 25_000,
        "p75_views": 38_000,
        "median_er": 4.0,
        "avg_views": 30_000,
    }
    class_row = {
        "content_class_id": 11,
        "sample_size": 120,
        "hook_distribution": {"question": 42},
        "tone_distribution": {"casual": 60},
        "avg_transitions_per_second": 0.5,
        "median_er": 4.2,
        "median_views": 22_000,
    }
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[class_row]
    )
    slim = {"avg_views": 30_000, "sample_size": 40, "median_er": 4.0}
    out = enrich_niche_meta_for_signals(
        slim,
        tier_row,
        sb=sb,
        niche_id=4,
        benchmark_axis="content_class_tier",
        content_class_id=11,
    )
    assert out["hook_distribution"] == {"question": 42}
    assert out["p75_views"] == 38_000


def test_live_shaped_niche_meta_fires_hook_percentile_gap() -> None:
    row = {
        "content_class_id": 3,
        "avg_views": 50_000,
        "median_views": 40_000,
        "median_er": 5.0,
        "sample_size": 80,
        "hook_distribution": {"question": 40, "bold_claim": 35},
    }
    meta = build_niche_benchmark_payload(
        row,
        niche_id=2,
        benchmark_axis="content_class",
        content_class_id=3,
    )["niche_meta"]
    assert meta is not None

    ctx = build_diagnosis_ctx(
        user_analysis={
            "hook_analysis": {"hook_type": "story", "first_frame_type": "face"},
        },
        user_stats={"views": 10_000, "engagement_rate": 3.0},
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
        niche_meta=meta,
        content_format="review",
    )
    sigs = extract_niche_hook_percentile_gap_signal(ctx)
    assert sigs, "hook_distribution from prod-shaped niche_meta should fire gap signal"
    manifest = build_signal_manifest(ctx)
    assert any(
        s.id == "niche_hook_percentile_gap"
        for section in manifest.values()
        for s in section
    )
