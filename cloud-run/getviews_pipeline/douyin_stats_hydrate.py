"""Hydrate Douyin aweme ``statistics`` from TikHub's statistics API.

Keyword/hashtag **search** and even post-detail endpoints often omit
``play_count``. TikHub documents
``GET /api/v1/douyin/app/v3/fetch_multi_video_statistics`` as the
supported source for play counts on Douyin.
"""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.tikhub_douyin import fetch_douyin_video_statistics

logger = logging.getLogger(__name__)

_STATISTICS_CHUNK = 50


def aweme_play_count(aweme: dict[str, Any]) -> int:
    stats = aweme.get("statistics") or {}
    try:
        return int(
            stats.get("play_count")
            or stats.get("playCount")
            or stats.get("view_count")
            or 0
        )
    except (TypeError, ValueError):
        return 0


def aweme_statistics_need_hydration(aweme: dict[str, Any]) -> bool:
    """True when search payload is missing a trustworthy play_count."""
    return aweme_play_count(aweme) <= 0


def aweme_engagement_metrics(aweme: dict[str, Any]) -> dict[str, int | float]:
    """Extract corpus-grade engagement fields from a hydrated aweme."""
    from getviews_pipeline.douyin_metadata import _safe_engagement_rate

    stats = aweme.get("statistics") or {}
    views = aweme_play_count(aweme)
    likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)
    comments = int(stats.get("comment_count") or 0)
    shares = int(stats.get("share_count") or 0)
    saves = int(stats.get("collect_count") or 0)
    engagement_rate = _safe_engagement_rate(
        er_from_analysis=None,
        views=views,
        likes=likes,
        comments=comments,
        shares=shares,
        saves=saves,
    )
    return {
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "engagement_rate": engagement_rate,
    }


def merge_aweme_statistics_fields(
    base: dict[str, Any],
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Overlay statistics fields onto a search aweme (shallow copy)."""
    merged = dict(base)
    if stats:
        merged["statistics"] = {
            **(base.get("statistics") or {}),
            **stats,
        }
    return merged


async def _fetch_statistics_map(aweme_ids: list[str]) -> dict[str, dict[str, Any]]:
    stats_by_id: dict[str, dict[str, Any]] = {}
    for i in range(0, len(aweme_ids), _STATISTICS_CHUNK):
        chunk = aweme_ids[i : i + _STATISTICS_CHUNK]
        try:
            stats_by_id.update(await fetch_douyin_video_statistics(chunk))
        except Exception as exc:
            logger.warning(
                "[douyin-stats] statistics fetch failed for chunk %s: %s",
                chunk[:3],
                exc,
            )
    return stats_by_id


async def hydrate_awemes_statistics(
    awemes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return awemes with TikHub statistics merged where play_count was missing."""
    if not awemes:
        return []

    need_ids: list[str] = []
    for aweme in awemes:
        vid = str(aweme.get("aweme_id") or "").strip()
        if vid and aweme_statistics_need_hydration(aweme):
            need_ids.append(vid)

    if not need_ids:
        return list(awemes)

    stats_by_id = await _fetch_statistics_map(need_ids)

    out: list[dict[str, Any]] = []
    for aweme in awemes:
        vid = str(aweme.get("aweme_id") or "").strip()
        if not vid or not aweme_statistics_need_hydration(aweme):
            out.append(aweme)
            continue

        stats = stats_by_id.get(vid)
        if not stats:
            logger.debug("[douyin-stats] no statistics payload for %s", vid)
            out.append(aweme)
            continue

        hydrated = merge_aweme_statistics_fields(aweme, stats)
        if aweme_play_count(hydrated) <= 0:
            logger.debug(
                "[douyin-stats] %s still play_count=0 after statistics fetch", vid,
            )
        out.append(hydrated)

    return out
