"""S4-2 — seeding_comment_pattern signal (§4.7 M5).

2026-06-12 coherence fix: the signal now requires boost suspicion (stored row
attribution or live classification) and is suppressed when the stored
attribution is ``organic_confident`` — a seeding claim next to an
"Organic — không thấy dấu hiệu boost" chip was a contradiction.
"""

from __future__ import annotations

from getviews_pipeline.signals.distribution import extract_seeding_comment_pattern_signal


def _radar(
    *,
    sampled: int = 10,
    neutral_pct: float = 90.0,
    spam_skipped_ratio: float = 0.6,
) -> dict:
    return {
        "sampled": sampled,
        "spam_skipped_ratio": spam_skipped_ratio,
        "sentiment": {"neutral_pct": neutral_pct, "positive_pct": 5.0, "negative_pct": 5.0},
    }


def _ctx(**overrides: object) -> dict:
    base = {
        "user_analysis": {"hook_analysis": {"hook_type": "demo"}},
        # views=100K ≥ p90 (30K×1.8=54K) + comment_rate 0.00012 < p10 0.002
        # → classify_boost_suspect = suspect_medium.
        "user_stats": {
            "views": 100_000,
            "comments": 12,
            "engagement_rate": 0.4,
        },
        "niche_meta": {
            "sample_size": 100,
            "p10_comment_rate": 0.002,
            "p25_er": 2.5,
            "p75_views": 10_000,
            "p90_views": 30_000,
            "median_er": 4.0,
        },
        "comment_radar": _radar(),
    }
    base.update(overrides)
    return base


def test_seeding_fires_on_spam_skew_and_boost_suspect_stats():
    sigs = extract_seeding_comment_pattern_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "seeding_comment_pattern"
    assert sigs[0].section_id == "boost_attribution"
    assert "dấu hiệu seeding" in sigs[0].claim


def test_seeding_claim_formats_comment_rate_per_1000_views():
    """Bug 2026-06-12: raw ratio leaked into prose as «tỉ lệ 0.000258»."""
    sigs = extract_seeding_comment_pattern_signal(_ctx())
    assert len(sigs) == 1
    # 12 comments / 100K views → 0.12 comment per 1.000 view
    assert "0.12 comment/1.000 view" in sigs[0].claim
    assert "0.000" not in sigs[0].claim


def test_seeding_suppressed_when_stored_attribution_is_organic_confident():
    """The boost chip says "Organic" — a seeding claim would contradict it."""
    ctx = _ctx(
        user_stats={
            "views": 100_000,
            "comments": 12,
            "engagement_rate": 0.4,
            "boost_attribution": "organic_confident",
        }
    )
    assert extract_seeding_comment_pattern_signal(ctx) == []


def test_seeding_no_fire_on_low_comment_rate_alone_when_classification_organic():
    """Live bug repro: low comment ratio + 93% neutral but views below the
    boost p90 → local classification organic_confident → no seeding claim."""
    ctx = _ctx(
        user_stats={
            # 50K < p90 54K → classify_boost_suspect = organic_confident,
            # but comment_rate 0.00024 < p10 0.002 (the old OR-trigger).
            "views": 50_000,
            "comments": 12,
            "engagement_rate": 0.4,
        },
        comment_radar=_radar(neutral_pct=93.0, spam_skipped_ratio=0.1),
    )
    assert extract_seeding_comment_pattern_signal(ctx) == []


def test_seeding_fires_when_stored_attribution_is_suspect_even_if_local_organic():
    ctx = _ctx(
        user_stats={
            "views": 50_000,  # below p90 → local organic_confident
            "comments": 12,
            "engagement_rate": 0.4,
            "boost_attribution": "suspect_medium",
        }
    )
    sigs = extract_seeding_comment_pattern_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "seeding_comment_pattern"


def test_seeding_no_fire_when_sample_too_small():
    ctx = _ctx(comment_radar=_radar(sampled=5))
    assert extract_seeding_comment_pattern_signal(ctx) == []


def test_seeding_no_fire_when_neutral_and_spam_low():
    ctx = _ctx(comment_radar=_radar(neutral_pct=50.0, spam_skipped_ratio=0.1))
    assert extract_seeding_comment_pattern_signal(ctx) == []


def test_seeding_no_fire_when_views_below_floor():
    ctx = _ctx(user_stats={"views": 5_000, "comments": 0, "engagement_rate": 0.2})
    assert extract_seeding_comment_pattern_signal(ctx) == []
