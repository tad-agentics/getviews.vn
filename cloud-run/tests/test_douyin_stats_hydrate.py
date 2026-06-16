"""Tests for ``douyin_stats_hydrate`` — TikHub statistics hydration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from getviews_pipeline.douyin_stats_hydrate import (
    aweme_engagement_metrics,
    aweme_play_count,
    hydrate_awemes_statistics,
    merge_aweme_statistics_fields,
)


def _search_aweme(play_count: int = 0, digg_count: int = 100_000) -> dict:
    return {
        "aweme_id": "7350123456789",
        "desc": "test",
        "statistics": {
            "play_count": play_count,
            "digg_count": digg_count,
            "comment_count": 100,
            "share_count": 50,
            "collect_count": 200,
        },
    }


def test_aweme_play_count_reads_statistics() -> None:
    assert aweme_play_count(_search_aweme(play_count=1_200_000)) == 1_200_000
    assert aweme_play_count(_search_aweme(play_count=0)) == 0


def test_merge_aweme_statistics_fields_overlays_play_count() -> None:
    base = _search_aweme(play_count=0)
    merged = merge_aweme_statistics_fields(
        base,
        {"play_count": 3_500_000, "digg_count": 400_000},
    )
    assert aweme_play_count(merged) == 3_500_000
    assert int(merged["statistics"]["digg_count"]) == 400_000


def test_aweme_engagement_metrics_computes_er_from_real_views() -> None:
    metrics = aweme_engagement_metrics(_search_aweme(play_count=1_000_000))
    assert metrics["views"] == 1_000_000
    assert metrics["likes"] == 100_000
    assert metrics["engagement_rate"] > 0


@pytest.mark.asyncio
async def test_hydrate_awemes_statistics_fetches_statistics_when_play_count_zero() -> None:
    search = _search_aweme(play_count=0)
    with patch(
        "getviews_pipeline.douyin_stats_hydrate.fetch_douyin_video_statistics",
        new_callable=AsyncMock,
        return_value={
            "7350123456789": {
                "play_count": 2_000_000,
                "digg_count": 180_000,
            },
        },
    ):
        out = await hydrate_awemes_statistics([search])
    assert len(out) == 1
    assert aweme_play_count(out[0]) == 2_000_000


@pytest.mark.asyncio
async def test_hydrate_skips_fetch_when_play_count_already_present() -> None:
    search = _search_aweme(play_count=900_000)
    with patch(
        "getviews_pipeline.douyin_stats_hydrate.fetch_douyin_video_statistics",
        new_callable=AsyncMock,
    ) as stats_fetch:
        out = await hydrate_awemes_statistics([search])
    stats_fetch.assert_not_called()
    assert aweme_play_count(out[0]) == 900_000
