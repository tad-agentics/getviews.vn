#!/usr/bin/env python3
"""CLI runner for the video corpus batch ingest.

Usage (from cloud-run/ directory):

    # Ingest all niches
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
    ENSEMBLE_DATA_API_KEY=... GEMINI_API_KEY=... \\
    python scripts/run_batch_ingest.py

    # Ingest specific niche IDs only
    python scripts/run_batch_ingest.py --niche-ids 1 3 5

    # Dry-run: fetch pool and print counts without writing to DB
    python scripts/run_batch_ingest.py --dry-run

Environment variables:
    SUPABASE_URL                  — Supabase project URL
    SUPABASE_SERVICE_ROLE_KEY     — Service role key (bypasses RLS for writes)
    ENSEMBLE_DATA_API_KEY         — EnsembleData token
    GEMINI_API_KEY                — Google Gemini API key
    BATCH_VIDEOS_PER_NICHE        — Max videos to analyze per niche (default: 10)
    BATCH_RECENCY_DAYS            — Only include posts from last N days (default: 30)
    BATCH_CONCURRENCY             — Parallel niches processed at once (default: 4)
    GEMINI_CONCURRENCY            — Max parallel Gemini calls (default: 4)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ensure cloud-run/ root is on sys.path so getviews_pipeline imports work
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("batch_ingest")


async def _dry_run(niche_ids: list[int] | None) -> None:
    from getviews_pipeline import ensemble
    from getviews_pipeline.corpus_ingest import _fetch_niche_pool, _fetch_niches_sync, _service_client

    client = _service_client()
    niches = _fetch_niches_sync(client)
    if niche_ids:
        niches = [n for n in niches if n["id"] in niche_ids]

    logger.info("[dry-run] %d niches to process", len(niches))
    for niche in niches:
        pool = await _fetch_niche_pool(niche)
        logger.info(
            "[dry-run] niche=%s id=%d — pool size=%d",
            niche.get("name_en"),
            niche["id"],
            len(pool),
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description="GetViews.vn corpus batch ingest")
    parser.add_argument(
        "--niche-ids",
        nargs="*",
        type=int,
        default=None,
        help="Restrict to specific niche IDs (space-separated). Omit for all niches.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch pool sizes only — no Gemini calls, no DB writes.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print final summary as JSON to stdout.",
    )
    args = parser.parse_args()

    if args.dry_run:
        await _dry_run(args.niche_ids)
        return

    from getviews_pipeline.corpus_ingest import run_batch_ingest

    summary = await run_batch_ingest(niche_ids=args.niche_ids)

    if args.json:
        print(json.dumps(summary.__dict__, default=str, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  Batch Ingest Complete")
        print(f"{'='*60}")
        print(f"  Niches processed:       {summary.niches_processed}")
        print(f"  Videos inserted:        {summary.total_inserted}")
        print(f"  Videos skipped:         {summary.total_skipped}")
        print(f"  Failures:               {summary.total_failed}")
        print(f"  MV refreshed:           {summary.materialized_view_refreshed}")
        print(f"{'='*60}")

        if summary.niche_results:
            print("\nPer-niche breakdown:")
            for r in summary.niche_results:
                status = "✓" if r["failed"] == 0 else "⚠"
                print(
                    f"  {status} [{r['niche_id']:>3}] {r['niche_name']:<25} "
                    f"inserted={r['inserted']} skipped={r['skipped']} failed={r['failed']}"
                )
                for err in r["errors"]:
                    print(f"        error: {err}")

    if summary.total_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
