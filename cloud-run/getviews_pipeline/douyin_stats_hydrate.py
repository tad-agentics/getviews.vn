"""Hydrate Douyin aweme ``statistics`` from TikHub post-detail endpoints.

Keyword/hashtag **search** often returns ``play_count: 0`` while
``fetch_one_video_v2`` / ``fetch_multi_video`` return the real view
count. Ingest and backfill call these helpers before persisting metrics.
"""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.tikhub_douyin import (
    fetch_douyin_post_info,
    fetch_douyin_post_multi_info,
)

logger = logging.getLogger(__name__)

_MULTI_CHUNK = 20


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


def merge_aweme_detail_statistics(
    base: dict[str, Any],
    detail: dict[str, Any],
) -> dict[str, Any]:
    """Overlay detail ``statistics`` onto a search aweme (shallow copy)."""
    merged = dict(base)
    detail_stats = detail.get("statistics")
    if isinstance(detail_stats, dict) and detail_stats:
        merged["statistics"] = {
            **(base.get("statistics") or {}),
            **detail_stats,
        }
    return merged


async def hydrate_awemes_statistics(
    awemes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return awemes with post-detail statistics merged where needed."""
    if not awemes:
        return []

    by_id: dict[str, dict[str, Any]] = {}
    need_ids: list[str] = []
    for aweme in awemes:
        vid = str(aweme.get("aweme_id") or "").strip()
        if not vid:
            continue
        by_id[vid] = aweme
        if aweme_statistics_need_hydration(aweme):
            need_ids.append(vid)

    if not need_ids:
        return list(awemes)

    detail_by_id: dict[str, dict[str, Any]] = {}
    for i in range(0, len(need_ids), _MULTI_CHUNK):
        chunk = need_ids[i : i + _MULTI_CHUNK]
        try:
            details = await fetch_douyin_post_multi_info(chunk)
            for detail in details:
                did = str(detail.get("aweme_id") or "").strip()
                if did:
                    detail_by_id[did] = detail
        except Exception as exc:
            logger.warning(
                "[douyin-stats] multi fetch failed for chunk %s: %s",
                chunk[:3],
                exc,
            )

    out: list[dict[str, Any]] = []
    for aweme in awemes:
        vid = str(aweme.get("aweme_id") or "").strip()
        if not vid or not aweme_statistics_need_hydration(aweme):
            out.append(aweme)
            continue

        detail = detail_by_id.get(vid)
        if detail is None:
            try:
                detail = await fetch_douyin_post_info(vid)
            except Exception as exc:
                logger.warning(
                    "[douyin-stats] post info failed for %s: %s", vid, exc,
                )
                out.append(aweme)
                continue

        hydrated = merge_aweme_detail_statistics(aweme, detail)
        if aweme_play_count(hydrated) <= 0:
            logger.debug(
                "[douyin-stats] %s still play_count=0 after detail fetch", vid,
            )
        out.append(hydrated)

    return out
