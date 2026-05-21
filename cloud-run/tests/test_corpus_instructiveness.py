"""Unit tests for corpus instructiveness scoring (selection-only)."""

from __future__ import annotations

from getviews_pipeline.corpus_boost_suspect import BoostPercentiles, classify_boost_suspect
from getviews_pipeline.corpus_instructiveness import (
    IngestBatchContext,
    NicheViewStats,
    _classify_creator_tier,
    apply_diversity_caps,
    compute_instructiveness_score,
    looks_like_non_vietnamese_caption,
    predict_hook_from_caption,
    pre_pool_min_views,
)


def test_pre_pool_min_views_shadow_uses_tier_floor():
    assert pre_pool_min_views("shadow") == 3_000
    assert pre_pool_min_views("purity") == 3_000
    assert pre_pool_min_views("legacy") == 20_000


def test_predict_hook_from_caption_question():
    assert predict_hook_from_caption("Tại sao video này flop?") == "question"


def test_non_vietnamese_caption_cjk():
    assert looks_like_non_vietnamese_caption("沉浸式早八 淡颜韩系日常妆") is True
    assert looks_like_non_vietnamese_caption("Hướng dẫn make up cho gái Việt") is False


def test_boost_suspect_zero_comments_high_views():
    pct = BoostPercentiles(p75_views=20_000, p90_views=100_000, p25_er=2.0)
    res = classify_boost_suspect(
        views=150_000,
        er=4.0,
        comments=0,
        percentiles=pct,
        hard_reject_enabled=False,
    )
    assert res.attribution == "suspect_medium"
    assert res.reference_eligible is False


def test_instructiveness_prefers_breakout_over_flat_views():
    ctx = IngestBatchContext(
        niche_stats={
            3: NicheViewStats(niche_id=3, p50_views=10_000, p75_views=20_000, corpus_count=200),
        },
        global_boost=BoostPercentiles(thin=False, p90_views=500_000),
        niche_boost={3: BoostPercentiles(thin=False, p90_views=500_000)},
    )
    breakout_aweme = {
        "aweme_id": "1",
        "desc": "#makeup tutorial",
        "create_time": 1_700_000_000,
        "author": {"unique_id": "creator_a", "follower_count": 50_000},
        "authorStats": {"medianPlayCount": 5_000},
        "statistics": {
            "play_count": 50_000,
            "digg_count": 3000,
            "comment_count": 200,
            "share_count": 50,
        },
        "music": {"id": "s1"},
    }
    flat_aweme = {
        "aweme_id": "2",
        "desc": "#makeup",
        "create_time": 1_700_000_000,
        "author": {"unique_id": "creator_b", "follower_count": 5_000_000},
        "authorStats": {"medianPlayCount": 2_000_000},
        "statistics": {
            "play_count": 2_100_000,
            "digg_count": 40_000,
            "comment_count": 500,
            "share_count": 100,
        },
        "music": {"id": "s2"},
    }

    def _er(**kwargs):
        v = kwargs["views"]
        if v <= 0:
            return 0.0
        return (kwargs["likes"] + kwargs["comments"] + kwargs["shares"]) / v * 100

    s_breakout = compute_instructiveness_score(
        breakout_aweme,
        niche_id=3,
        signal_hashtags=["makeup"],
        er=_er(
            views=50_000,
            likes=3000,
            comments=200,
            shares=50,
        ),
        views=50_000,
        comments=200,
        save_rate=None,
        ctx=ctx,
    )
    s_flat = compute_instructiveness_score(
        flat_aweme,
        niche_id=3,
        signal_hashtags=["makeup"],
        er=_er(
            views=2_100_000,
            likes=40_000,
            comments=500,
            shares=100,
        ),
        views=2_100_000,
        comments=500,
        save_rate=None,
        ctx=ctx,
    )
    assert s_breakout.instructiveness_score > s_flat.instructiveness_score
    assert s_breakout.breakout_value >= 2.0


def test_diversity_cap_per_creator():
    from getviews_pipeline.corpus_instructiveness import CandidateScore
    from getviews_pipeline.corpus_boost_suspect import BoostSuspectResult

    boost = BoostSuspectResult(
        attribution="organic_confident",
        would_reject=False,
        reference_eligible=True,
    )
    items = []
    for i in range(5):
        items.append(
            CandidateScore(
                aweme={"aweme_id": str(i), "author": {"unique_id": "same"}},
                instructiveness_score=100 - i,
                breakout_value=3.0,
                breakout_source="author_median",
                velocity=1.0,
                boost=boost,
                predicted_hook=None,
                hook_penalty_applied=False,
                would_skip_pre_gemini=False,
                tier1_pass=True,
                convergence_pass=True,
            )
        )
    selected = apply_diversity_caps(items, 5, max_per_creator=2, max_per_sound=5)
    assert len(selected) == 2


def test_classify_creator_tier_zero_followers_is_nano():
    assert _classify_creator_tier(0) == "nano"
    assert _classify_creator_tier(None) is None
    assert _classify_creator_tier(-1) is None


def test_corpus_ingest_uses_shared_classify_creator_tier():
    from getviews_pipeline.corpus_ingest import _classify_creator_tier as ingest_fn

    assert ingest_fn is _classify_creator_tier
    assert ingest_fn(0) == "nano"

