#!/usr/bin/env python3
"""Backfill pattern_id on existing video_corpus rows.

When the viral-pattern-fingerprint feature landed, the ingest hook started
stamping `pattern_id` on every newly-upserted row. Everything analysed before
that merge has pattern_id=NULL — roughly the entire existing corpus. Until
those rows are fingerprinted, trend_spike's "top pattern this week" line
stays empty and content_directions can't group references by family.

This one-shot script iterates NULL-pattern_id rows, computes + upserts a
pattern, and stamps the corpus row. Rate-limited so it doesn't flood
video_patterns with duplicate inserts during peak traffic. Safe to re-run —
already-stamped rows are skipped.

Usage (from cloud-run/ dir):
    python scripts/backfill_pattern_ids.py [--dry-run] [--batch-size 200]
                                           [--max-rows 5000]

Requires env vars: SUPABASE_URL, SUPABASE_ANON_KEY (reads) + SUPABASE_SERVICE_KEY
(writes). Falls open on any single-row error — logs + continues.

After the backfill:
    - /batch/analytics will recompute weekly_instance_count + delta for the
      patterns this script wrote, so trend_spike starts citing them.
    - content_directions pattern-grouped responses light up immediately.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(asctime)s %(message)s")
logger = logging.getLogger("backfill_patterns")


@dataclass
class BackfillStats:
    seen: int = 0
    stamped: int = 0
    skipped: int = 0
    failed: int = 0

    def log(self) -> None:
        logger.info(
            "[backfill_patterns] seen=%d stamped=%d skipped=%d failed=%d",
            self.seen, self.stamped, self.skipped, self.failed,
        )


async def backfill(dry_run: bool, batch_size: int, max_rows: int) -> BackfillStats:
    from getviews_pipeline.pattern_fingerprint import compute_and_upsert_pattern
    from getviews_pipeline.supabase_client import get_service_client

    sb = get_service_client()
    stats = BackfillStats()

    # Pagination: Supabase responses are capped (~1000 rows/page) so we page
    # by ascending id to avoid the same rows being returned twice if the
    # in-flight UPDATE shifts ORDER BY indexed_at.
    last_id: str | None = None

    while stats.seen < max_rows:
        remaining = max_rows - stats.seen
        limit = min(batch_size, remaining)
        try:
            query = (
                sb.table("video_corpus")
                .select("video_id, niche_id, analysis_json")
                .is_("pattern_id", "null")
                .order("video_id")
                .limit(limit)
            )
            if last_id is not None:
                query = query.gt("video_id", last_id)
            result = query.execute()
        except Exception as exc:
            logger.exception("Supabase fetch failed: %s", exc)
            break

        rows = result.data or []
        if not rows:
            logger.info("[backfill_patterns] no more NULL rows — done")
            break

        for row in rows:
            stats.seen += 1
            video_id = str(row.get("video_id") or "")
            niche_id = row.get("niche_id")
            analysis_json = row.get("analysis_json") or {}
            if not video_id or not isinstance(niche_id, int) or not analysis_json:
                stats.skipped += 1
                continue
            if dry_run:
                stats.stamped += 1
                continue
            try:
                pattern_id = await compute_and_upsert_pattern(sb, analysis_json, niche_id)
                if not pattern_id:
                    stats.skipped += 1
                    continue
                sb.table("video_corpus").update(
                    {"pattern_id": pattern_id}
                ).eq("video_id", video_id).execute()
                stats.stamped += 1
            except Exception as exc:
                stats.failed += 1
                logger.warning(
                    "backfill failed for video_id=%s niche_id=%s: %s",
                    video_id, niche_id, exc,
                )

        last_id = str(rows[-1].get("video_id") or "") or None

        # Gentle pacing — don't flood Supabase / the patterns table.
        if not dry_run:
            time.sleep(0.25)

        if stats.seen % 500 == 0:
            stats.log()

    stats.log()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="walk rows without writing")
    parser.add_argument(
        "--batch-size", type=int, default=200,
        help="rows fetched per Supabase page (default 200)",
    )
    parser.add_argument(
        "--max-rows", type=int, default=10_000,
        help="maximum rows to process in this invocation (default 10k)",
    )
    args = parser.parse_args()

    try:
        stats = asyncio.run(
            backfill(
                dry_run=args.dry_run,
                batch_size=args.batch_size,
                max_rows=args.max_rows,
            )
        )
    except KeyboardInterrupt:
        logger.warning("Interrupted — partial results above")
        return 130
    return 0 if stats.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
