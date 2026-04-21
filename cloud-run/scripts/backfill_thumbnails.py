#!/usr/bin/env python3
"""Backfill R2 thumbnails for video_corpus rows that still have expired TikTok CDN URLs.

Two entrypoints:

  - CLI::   python scripts/backfill_thumbnails.py [--dry-run] [--batch-size 20] [--limit 500]
  - Admin::  await run_thumbnail_backfill(batch_size=20, limit=None)

The admin path is wired at ``/admin/trigger/thumbnail_backfill`` — reuses the
same code so the fix stays in one place.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)


async def run_thumbnail_backfill(
    *,
    batch_size: int = 20,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Rehost stale TikTok-CDN thumbnails to R2. Returns stats dict.

    The stored URLs have expired signed tokens *and* TikTok's CDN enforces
    hotlink protection (``x-deny-reason: host_not_allowed``) against
    datacenter IPs. So for each stale row we:

      1. Refetch the post from EnsembleData to get a fresh signed URL
      2. Call ``download_and_upload_thumbnail`` which now routes through
         ``get_cdn_client()`` (residential proxy + TikTok ``Referer``)
      3. Update ``video_corpus.thumbnail_url`` on success

    Steps 1-3 run in batches of ``batch_size`` with a short sleep between
    batches to spare the EnsembleData rate limit.
    """
    from getviews_pipeline import ensemble
    from getviews_pipeline.r2 import download_and_upload_thumbnail, r2_configured
    from getviews_pipeline.supabase_client import get_service_client

    if not r2_configured():
        return {
            "ok": False,
            "error": "r2_not_configured",
            "detail": "Set R2_BUCKET, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY",
        }

    sb = get_service_client()
    resp = sb.table("video_corpus").select("video_id, thumbnail_url").execute()
    all_rows = resp.data or []
    stale = [
        r for r in all_rows
        if r.get("thumbnail_url") and "pub-" not in r["thumbnail_url"]
    ]
    if limit is not None:
        stale = stale[:limit]

    logger.info("[backfill_thumbs] %d rows to rehost (batch_size=%d dry_run=%s)",
                len(stale), batch_size, dry_run)

    if dry_run:
        return {"ok": True, "candidates": len(stale), "updated": 0, "failed": 0, "dry_run": True}

    updated = 0
    failed = 0
    batches = -(-len(stale) // batch_size) if stale else 0

    for i in range(0, len(stale), batch_size):
        chunk = stale[i:i + batch_size]
        video_ids = [r["video_id"] for r in chunk]
        logger.info("[backfill_thumbs] batch %d/%d — %d videos",
                    i // batch_size + 1, batches, len(chunk))

        try:
            fresh_posts = await ensemble.fetch_post_multi_info(video_ids)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[backfill_thumbs] ED batch fetch failed: %s — skipping batch", exc)
            failed += len(chunk)
            continue

        fresh_by_id: dict[str, dict] = {}
        for post in fresh_posts:
            detail = post.get("aweme_detail") or post
            vid_id = str(detail.get("aweme_id") or "")
            if vid_id:
                fresh_by_id[vid_id] = detail

        upload_tasks = []
        upload_ids: list[str] = []
        for row in chunk:
            vid_id = row["video_id"]
            detail = fresh_by_id.get(vid_id)
            if not detail:
                logger.warning("[backfill_thumbs] %s — not in ED response", vid_id)
                failed += 1
                continue
            cover = detail.get("video", {}).get("cover") or {}
            cover_urls = cover.get("url_list") or []
            fresh_url = cover_urls[0] if cover_urls else row.get("thumbnail_url", "")
            if not fresh_url:
                logger.warning("[backfill_thumbs] %s — no cover URL in ED response", vid_id)
                failed += 1
                continue
            upload_tasks.append(download_and_upload_thumbnail(fresh_url, vid_id))
            upload_ids.append(vid_id)

        if not upload_tasks:
            continue

        results = await asyncio.gather(*upload_tasks, return_exceptions=True)
        for vid_id, result in zip(upload_ids, results):
            if isinstance(result, str) and result:
                try:
                    sb.table("video_corpus").update(
                        {"thumbnail_url": result}
                    ).eq("video_id", vid_id).execute()
                    updated += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[backfill_thumbs] DB update failed for %s: %s", vid_id, exc)
                    failed += 1
            else:
                logger.warning("[backfill_thumbs] ✗ %s — upload result: %s", vid_id, result)
                failed += 1

        await asyncio.sleep(1)  # ED rate limit

    return {
        "ok": True,
        "candidates": len(stale),
        "updated": updated,
        "failed": failed,
    }


async def _cli_main(dry_run: bool, batch_size: int, limit: int | None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    stats = await run_thumbnail_backfill(
        batch_size=batch_size, limit=limit, dry_run=dry_run,
    )
    print(stats)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(_cli_main(dry_run=args.dry_run, batch_size=args.batch_size, limit=args.limit))
