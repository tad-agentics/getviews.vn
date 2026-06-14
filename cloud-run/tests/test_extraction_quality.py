"""Tests for extraction quality classification and peer pool ranking."""

from __future__ import annotations

from getviews_pipeline.extraction_quality import (
    classify_extraction_quality,
    is_clean_boost_attribution,
    is_suspect_low_attribution,
    peer_pool_quality_rank,
)


def test_classify_ok_for_normal_extraction() -> None:
    q = classify_extraction_quality(
        {
            "scenes": [{"start": 0, "end": 3}, {"start": 3, "end": 8}],
            "transitions_per_second": 0.4,
        }
    )
    assert q == "ok"


def test_classify_degraded_scenes_coarse() -> None:
    q = classify_extraction_quality(
        {
            "scenes": [{"start": 0, "end": 30}],
            "transitions_per_second": 0.1,
        }
    )
    assert q == "degraded_scenes"


def test_classify_degraded_transitions_zero() -> None:
    q = classify_extraction_quality(
        {
            "scenes": [{"start": 0, "end": 3}, {"start": 3, "end": 8}],
            "transitions_per_second": 0,
        }
    )
    assert q == "degraded"


def test_peer_pool_prefers_clean_boost_and_ok_extraction() -> None:
    clean_ok = {
        "boost_attribution": "organic_confident",
        "extraction_quality": "ok",
        "breakout_multiplier": 2.0,
        "engagement_rate": 5.0,
    }
    suspect = {
        "boost_attribution": "suspect_low",
        "extraction_quality": "ok",
        "breakout_multiplier": 9.0,
        "engagement_rate": 8.0,
    }
    assert peer_pool_quality_rank(clean_ok) < peer_pool_quality_rank(suspect)
    assert is_clean_boost_attribution("organic_confident")
    assert is_suspect_low_attribution("suspect_low")
    assert not is_clean_boost_attribution("suspect_low")
