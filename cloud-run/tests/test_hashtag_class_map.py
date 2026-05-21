"""Tests for hashtag_class_map v2 helpers."""

from __future__ import annotations

from getviews_pipeline.hashtag_class_map import pick_hashtags_for_class


def test_pick_hashtags_for_class_map_first():
    merged = pick_hashtags_for_class(
        ["signal1", "signal2"],
        thin=True,
        extra_from_map=["map_a", "map_b", "map_c"],
    )
    assert merged[0] == "map_a"
    assert len(merged) <= 25


def test_pick_hashtags_thin_limit():
    tags = [f"tag{i}" for i in range(30)]
    merged = pick_hashtags_for_class(tags, thin=True)
    assert len(merged) == 25
