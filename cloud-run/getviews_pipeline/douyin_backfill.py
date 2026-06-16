"""Douyin video banking backfill + content_class backfill (Phase 1 / 2a)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.config import DOUYIN_CDN_HEADERS, DOUYIN_VIDEO_DOWNLOAD_MAX_BYTES
from getviews_pipeline.douyin_content_class import resolve_content_class_from_analysis
from getviews_pipeline.r2 import download_and_upload_full_video
from getviews_pipeline.tikhub_douyin import (
    fetch_douyin_post_multi_info,
    fetch_douyin_post_info,
)

logger = logging.getLogger(__name__)


async def backfill_douyin_playback_urls(
    client: Any,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """Bank R2 playback_url for rows where it is null.

    Re-fetches fresh ``play_addr`` via TikHub batch when possible.
    """
    limit = max(1, min(int(limit), 500))
    res = (
        client.table("douyin_video_corpus")
        .select("video_id")
        .is_("playback_url", "null")
        .order("views", desc=True)
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return {"requested": 0, "banked": 0, "failed": 0, "skipped": 0}

    video_ids = [str(r["video_id"]) for r in rows if r.get("video_id")]
    aweme_by_id: dict[str, dict[str, Any]] = {}

    # Batch metadata refresh (fewer TikHub calls than per-video).
    chunk_size = 20
    for i in range(0, len(video_ids), chunk_size):
        chunk = video_ids[i : i + chunk_size]
        try:
            awemes = await fetch_douyin_post_multi_info(chunk)
            for a in awemes:
                aid = str(a.get("aweme_id") or "")
                if aid:
                    aweme_by_id[aid] = a
        except Exception as exc:
            logger.warning("[douyin-backfill] multi fetch failed: %s", exc)

    banked = 0
    failed = 0
    skipped = 0

    for vid in video_ids:
        aweme = aweme_by_id.get(vid)
        if not aweme:
            try:
                aweme = await fetch_douyin_post_info(vid)
            except Exception as exc:
                logger.warning("[douyin-backfill] post info failed %s: %s", vid, exc)
                failed += 1
                continue

        urls = ensemble.extract_video_urls(aweme)
        if not urls:
            skipped += 1
            continue

        playback_url = await download_and_upload_full_video(
            urls,
            vid,
            headers=DOUYIN_CDN_HEADERS,
            max_bytes=DOUYIN_VIDEO_DOWNLOAD_MAX_BYTES,
        )
        if not playback_url:
            failed += 1
            continue

        try:
            client.table("douyin_video_corpus").update(
                {"playback_url": playback_url},
            ).eq("video_id", vid).execute()
            banked += 1
        except Exception as exc:
            logger.warning("[douyin-backfill] db update failed %s: %s", vid, exc)
            failed += 1

    return {
        "requested": len(video_ids),
        "banked": banked,
        "failed": failed,
        "skipped": skipped,
    }


def backfill_douyin_content_class_ids(
    client: Any,
    *,
    limit: int = 500,
) -> dict[str, Any]:
    """Populate content_class_id from stored analysis_json (no re-extraction)."""
    limit = max(1, min(int(limit), 5000))
    res = (
        client.table("douyin_video_corpus")
        .select("video_id, niche_id, analysis_json, content_class_id")
        .is_("content_class_id", "null")
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    updated = 0
    for row in rows:
        vid = row.get("video_id")
        aj = row.get("analysis_json") or {}
        if not isinstance(aj, dict):
            continue
        cc_id, fmt = resolve_content_class_from_analysis(
            aj,
            douyin_niche_id=int(row.get("niche_id") or 0) or None,
        )
        if cc_id is None:
            continue
        try:
            client.table("douyin_video_corpus").update(
                {"content_class_id": cc_id, "content_format": fmt},
            ).eq("video_id", vid).execute()
            updated += 1
        except Exception as exc:
            logger.warning("[douyin-cc-backfill] update failed %s: %s", vid, exc)

    return {"scanned": len(rows), "updated": updated}


async def backfill_douyin_views(
    client: Any,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    """Re-fetch ``play_count`` via TikHub post-detail for rows stuck at views=0."""
    from getviews_pipeline.douyin_stats_hydrate import aweme_engagement_metrics

    limit = max(1, min(int(limit), 500))
    res = (
        client.table("douyin_video_corpus")
        .select("video_id")
        .eq("views", 0)
        .order("indexed_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return {"requested": 0, "updated": 0, "failed": 0, "skipped": 0}

    video_ids = [str(r["video_id"]) for r in rows if r.get("video_id")]
    aweme_by_id: dict[str, dict[str, Any]] = {}

    chunk_size = 20
    for i in range(0, len(video_ids), chunk_size):
        chunk = video_ids[i : i + chunk_size]
        try:
            awemes = await fetch_douyin_post_multi_info(chunk)
            for aweme in awemes:
                aid = str(aweme.get("aweme_id") or "")
                if aid:
                    aweme_by_id[aid] = aweme
        except Exception as exc:
            logger.warning("[douyin-views-backfill] multi fetch failed: %s", exc)

    updated = 0
    failed = 0
    skipped = 0

    for vid in video_ids:
        aweme = aweme_by_id.get(vid)
        if not aweme:
            try:
                aweme = await fetch_douyin_post_info(vid)
            except Exception as exc:
                logger.warning(
                    "[douyin-views-backfill] post info failed %s: %s", vid, exc,
                )
                failed += 1
                continue

        metrics = aweme_engagement_metrics(aweme)
        if int(metrics["views"]) <= 0:
            skipped += 1
            continue

        try:
            client.table("douyin_video_corpus").update(metrics).eq(
                "video_id", vid,
            ).execute()
            client.table("douyin_video_shots").update(
                {"views": metrics["views"]},
            ).eq("video_id", vid).execute()
            updated += 1
        except Exception as exc:
            logger.warning(
                "[douyin-views-backfill] db update failed %s: %s", vid, exc,
            )
            failed += 1

    return {
        "requested": len(video_ids),
        "updated": updated,
        "failed": failed,
        "skipped": skipped,
    }


async def run_backfill_douyin_playback_sync(
    client: Any,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    return await backfill_douyin_playback_urls(client, limit=limit)
