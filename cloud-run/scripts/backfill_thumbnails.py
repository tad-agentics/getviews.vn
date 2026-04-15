#!/usr/bin/env python3
"""Backfill R2 thumbnails for video_corpus rows that still have expired TikTok CDN URLs.

Usage (from cloud-run/ dir):
    python scripts/backfill_thumbnails.py [--dry-run] [--batch-size 20]

Requires env vars: ENSEMBLEDATA_TOKEN, R2_*, SUPABASE_SERVICE_KEY etc.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("backfill_thumbs")


async def main(dry_run: bool, batch_size: int) -> None:
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.r2 import download_and_upload_thumbnail, r2_configured
    from getviews_pipeline import ensemble

    if not r2_configured():
        logger.error("R2 not configured — set R2_BUCKET, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
        return

    sb = get_service_client()

    # Fetch all rows that still have TikTok CDN URLs (not yet uploaded to R2)
    resp = sb.table("video_corpus").select("video_id, thumbnail_url").execute()
    all_rows = resp.data or []
    stale = [r for r in all_rows if r.get("thumbnail_url") and "pub-" not in r["thumbnail_url"]]
    logger.info("Found %d rows with non-R2 thumbnail URLs", len(stale))

    if dry_run:
        logger.info("[dry-run] would process %d rows in batches of %d", len(stale), batch_size)
        return

    updated = 0
    failed = 0

    for i in range(0, len(stale), batch_size):
        chunk = stale[i:i + batch_size]
        video_ids = [r["video_id"] for r in chunk]
        logger.info("Batch %d/%d — fetching fresh metadata for %d videos",
                    i // batch_size + 1, -(-len(stale) // batch_size), len(chunk))

        # Fetch fresh post data from EnsembleData to get current CDN URLs
        try:
            fresh_posts = await ensemble.fetch_post_multi_info(video_ids)
        except Exception as exc:
            logger.warning("EnsembleData batch fetch failed: %s — skipping batch", exc)
            failed += len(chunk)
            continue

        fresh_by_id: dict[str, dict] = {}
        for post in fresh_posts:
            detail = post.get("aweme_detail") or post
            vid_id = str(detail.get("aweme_id") or "")
            if vid_id:
                fresh_by_id[vid_id] = detail

        # Upload each thumbnail to R2
        upload_tasks = []
        upload_ids = []
        for row in chunk:
            vid_id = row["video_id"]
            detail = fresh_by_id.get(vid_id)
            if not detail:
                logger.warning("%s — not found in EnsembleData response", vid_id)
                failed += 1
                continue

            # Extract fresh CDN thumbnail URL from aweme detail
            cover = detail.get("video", {}).get("cover") or {}
            cover_urls = cover.get("url_list") or []
            fresh_url = cover_urls[0] if cover_urls else row.get("thumbnail_url", "")

            if not fresh_url:
                logger.warning("%s — no cover URL in fresh response", vid_id)
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
                    sb.table("video_corpus").update({"thumbnail_url": result}).eq("video_id", vid_id).execute()
                    logger.info("✓ %s → %s", vid_id, result)
                    updated += 1
                except Exception as exc:
                    logger.warning("DB update failed for %s: %s", vid_id, exc)
                    failed += 1
            else:
                logger.warning("✗ %s — upload returned: %s", vid_id, result)
                failed += 1

        await asyncio.sleep(1)  # rate-limit EnsembleData

    logger.info("Done — updated=%d failed=%d", updated, failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run, batch_size=args.batch_size))
