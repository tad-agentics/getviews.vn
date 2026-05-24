"""S4-2 — seeding_comment_pattern signal (§4.7 M5)."""

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
        "user_stats": {
            "views": 50_000,
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


def test_seeding_fires_on_spam_skew_and_thin_comments():
    sigs = extract_seeding_comment_pattern_signal(_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "seeding_comment_pattern"
    assert sigs[0].section_id == "boost_attribution"
    assert "dấu hiệu seeding" in sigs[0].claim


def test_seeding_no_fire_when_sample_too_small():
    ctx = _ctx(comment_radar=_radar(sampled=5))
    assert extract_seeding_comment_pattern_signal(ctx) == []


def test_seeding_no_fire_when_neutral_and_spam_low():
    ctx = _ctx(comment_radar=_radar(neutral_pct=50.0, spam_skipped_ratio=0.1))
    assert extract_seeding_comment_pattern_signal(ctx) == []


def test_seeding_no_fire_when_views_below_floor():
    ctx = _ctx(user_stats={"views": 5_000, "comments": 0, "engagement_rate": 0.2})
    assert extract_seeding_comment_pattern_signal(ctx) == []
