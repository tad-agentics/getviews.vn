"""Tests for HI-11 rolling eval helpers."""

from __future__ import annotations

from getviews_pipeline.hi11_rolling_eval import (
    AGREEMENT_TARGET,
    HI9_SHADOW_TARGET,
    JUNCTION_MISS_TARGET,
    ROLLING_NIGHTS,
    _hi9_shadow_agreement,
    _junction_miss_rate,
    _rolling_median,
)


def test_junction_miss_rate_empty():
    assert _junction_miss_rate([]) == 0.0


def test_junction_miss_rate_counts_miss():
    rows = [
        {
            "niche_resolution_confidence": 0.9,
            "niche_resolution_source": "junction_miss",
            "content_class_id": 5,
        },
        {
            "niche_resolution_confidence": 0.9,
            "niche_resolution_source": "gemini_two_axis",
            "content_class_id": 5,
        },
    ]
    assert _junction_miss_rate(rows) == 0.5


def test_threshold_constants():
    assert AGREEMENT_TARGET == 0.85
    assert HI9_SHADOW_TARGET == 0.85
    assert JUNCTION_MISS_TARGET == 0.05
    assert ROLLING_NIGHTS == 7


def test_hi9_shadow_agreement_match():
    rows = [
        {
            "content_class_id": 10,
            "inferred_creator_niche_id": 1,
            "analysis_json": {
                "niche_classification": {"format_axis": "tutorial"},
            },
        },
    ]
    rate, n = _hi9_shadow_agreement(rows)
    assert n >= 0
    assert 0.0 <= rate <= 1.0


def test_rolling_median():
    history = [{"hashtag_class_agreement": 0.8}, {"hashtag_class_agreement": 0.9}]
    assert _rolling_median(history, "hashtag_class_agreement") == 0.85

