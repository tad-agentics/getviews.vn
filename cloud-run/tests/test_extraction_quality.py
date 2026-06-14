"""Tests for extraction quality classification and peer pool ranking."""

from __future__ import annotations

from getviews_pipeline.extraction_quality import (
    classify_extraction_quality,
    is_clean_boost_attribution,
    is_suspect_low_attribution,
    peer_pool_quality_rank,
    peer_recency_tiebreak,
    peer_row_days_ago,
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


def test_peer_recency_tiebreak_buckets() -> None:
    assert peer_recency_tiebreak(3) == 3
    assert peer_recency_tiebreak(14) == 3
    assert peer_recency_tiebreak(15) == 2
    assert peer_recency_tiebreak(30) == 2
    assert peer_recency_tiebreak(45) == 1
    assert peer_recency_tiebreak(60) == 1
    assert peer_recency_tiebreak(61) == 0


def test_peer_pool_recency_tiebreak_among_similar_peers() -> None:
    base = {
        "boost_attribution": "organic_confident",
        "extraction_quality": "ok",
        "breakout_multiplier": 2.0,
        "engagement_rate": 5.0,
    }
    recent = {**base, "_corpus_days_ago": 5}
    older = {**base, "_corpus_days_ago": 45}
    assert peer_pool_quality_rank(recent) < peer_pool_quality_rank(older)


def test_peer_pool_strong_older_organic_beats_weak_recent() -> None:
    strong_old = {
        "boost_attribution": "organic_confident",
        "extraction_quality": "ok",
        "breakout_multiplier": 6.0,
        "engagement_rate": 8.0,
        "_corpus_days_ago": 50,
    }
    weak_recent = {
        "boost_attribution": "organic_confident",
        "extraction_quality": "ok",
        "breakout_multiplier": 1.2,
        "engagement_rate": 2.0,
        "_corpus_days_ago": 3,
    }
    assert peer_pool_quality_rank(strong_old) < peer_pool_quality_rank(weak_recent)


def test_peer_row_days_ago_prefers_posted_at() -> None:
    from datetime import UTC, datetime, timedelta

    posted = (datetime.now(UTC) - timedelta(days=4)).isoformat()
    indexed = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    row = {"posted_at": posted, "indexed_at": indexed}
    assert peer_row_days_ago(row) == 4
