"""Wave 2 B — manifest telemetry + section emit coverage on rich fixtures."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import select_sections_to_emit
from getviews_pipeline.signals.registry import (
    build_diagnosis_ctx,
    build_signal_manifest,
    manifest_telemetry,
)


def _rich_commerce_ctx() -> dict:
    return build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "affiliate",
            "commerce_intent": {
                "conversion_objective": "shop_direct",
                "product_price_tier": "mid",
                "creator_type": "kos_seller",
                "verbal_cta_present": True,
                "disclosure_present": False,
                "disclosure_form": "none",
            },
            "hook_analysis": {
                "first_frame_type": "product",
                "hook_phrase": "Sản phẩm này đáng thử",
                "hook_type": "question",
                "hook_notes": "",
                "hook_timeline": [{"phase": "hook", "start": 0, "end": 3}],
                "face_appears_at": 1.2,
                "dialect_detected": "southern",
            },
            "creator_persona": "chu_shop_kos",
            "tone": "casual",
            "audio_transcript": "Hôm nay mình review serum này cho các bạn",
            "text_overlays": [{"text": "Giá sốc", "start": 0, "end": 2}],
            "transitions_per_second": 0.8,
            "safe_zone_status": "violated",
            "color_grading_style": "warm",
            "audio_track_role": "spoken_overlay",
            "share_trigger_type": "relatable",
            "save_trigger_type": "tutorial",
        },
        user_stats={
            "video_id": "fixture-rich-001",
            "caption": "#skincare #review",
            "views": 120_000,
            "likes": 8_000,
            "comments": 400,
            "engagement_rate": 0.07,
            "breakout_multiplier": 2.1,
        },
        reference_videos=[
            {
                "video_id": "ref-1",
                "views": 500_000,
                "hook_type": "question",
                "content_format": "review",
            }
        ],
        channel_context={"median_views": 40_000},
        performance_tier="above_average",
        niche_meta={
            "median_er": 0.05,
            "p90_views": 200_000,
            "hook_distribution": {"question": 0.3},
            "format_distribution": {"review": 0.4},
        },
        content_format="review",
        niche_name="Làm đẹp",
        corpus_size=1200,
    )


def test_manifest_telemetry_counts_signals_and_empty_sections() -> None:
    ctx = _rich_commerce_ctx()
    manifest = build_signal_manifest(ctx)
    deep_sections = select_sections_to_emit(manifest, ctx)
    telemetry = manifest_telemetry(manifest, sections_to_emit=deep_sections)

    assert telemetry["signal_count"] >= 5
    assert len(telemetry["signal_ids"]) == telemetry["signal_count"]
    assert telemetry["sections_with_signals"]["diagnosis"] >= 1
    assert "sections_to_emit" in telemetry
    assert isinstance(telemetry["sections_empty"], list)
    # Rich fixture should populate core sections — empty list is a regression signal.
    assert "diagnosis" not in telemetry["sections_empty"]
    assert "hook_analysis" not in telemetry["sections_empty"]


def test_rich_fixture_deep_emits_commerce_and_hook_sections() -> None:
    ctx = _rich_commerce_ctx()
    manifest = build_signal_manifest(ctx)
    deep = select_sections_to_emit(manifest, ctx)

    assert "hook_analysis" in deep
    assert "diagnosis" in deep
    assert "commerce" in deep
    assert len(manifest.get("hook_analysis") or []) >= 1
