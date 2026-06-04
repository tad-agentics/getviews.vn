"""Sprint 5 §9 + §2 — engagement + context signals."""

from __future__ import annotations

from datetime import UTC, datetime

from getviews_pipeline.signals.context_signals import extract_context_signals
from getviews_pipeline.signals.engagement import extract_engagement_signals
from getviews_pipeline.signals.registry import build_diagnosis_ctx


def test_pinned_comment_not_in_vo_commerce() -> None:
    ua: dict = {
        "promotion_type": "organic",
        "commerce_intent": {
            "conversion_objective": "affiliate_shopee",
            "product_price_tier": "under_150k",
            "creator_type": "koc",
            "verbal_cta_present": True,
            "disclosure_present": True,
            "disclosure_form": "hashtag",
        },
        "audio_transcript": "Mình review son này cho mọi người.",
        "text_overlays": [],
    }
    st: dict = {
        "caption": "",
        "views": 5000,
        "pinned_comment_text": "Mã giảm 50K của chị nằm ở comment ghim nhé",
    }
    ctx = build_diagnosis_ctx(
        user_analysis=ua,
        user_stats=st,
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
        compliance_flags=[],
        niche_meta={},
    )
    ids = [s.id for s in extract_engagement_signals(ctx)]
    assert "engagement_pinned_comment_not_in_vo" in ids


def test_loop_architecture_positive() -> None:
    ua: dict = {
        "promotion_type": "organic",
        "audio_transcript": "x",
        "text_overlays": [],
        "loop_architecture_score": 0.85,
    }
    ctx = build_diagnosis_ctx(
        user_analysis=ua,
        user_stats={"caption": "", "views": 100},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
        compliance_flags=[],
    )
    ids = [s.id for s in extract_engagement_signals(ctx)]
    assert "engagement_loop_architecture_positive" in ids


def test_golden_hour_no_signal_date_only() -> None:
    st = {"caption": "", "views": 1000, "posted_at": "2026-05-14"}
    ctx = build_diagnosis_ctx(
        user_analysis={"promotion_type": "organic", "audio_transcript": "", "text_overlays": []},
        user_stats=st,
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
        compliance_flags=[],
    )
    assert extract_context_signals(ctx) == []


def test_tuong_tac_cheo_heuristic() -> None:
    ua = {"promotion_type": "organic", "audio_transcript": "", "text_overlays": []}
    st = {
        "caption": "",
        "views": 1000,
        "engagement_rate": 15.0,
        "retention_end_pct": 35.0,
        "views_vs_avg_ratio": 0.5,
    }
    ctx = build_diagnosis_ctx(
        user_analysis=ua,
        user_stats=st,
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
        compliance_flags=[],
        niche_meta={"median_er": 2.0},
    )
    ids = [s.id for s in extract_context_signals(ctx)]
    assert "context_tuong_tac_cheo_heuristic" in ids
