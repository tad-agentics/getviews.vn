#!/usr/bin/env python3
"""CLI runner for the morning ritual batch (writes ``daily_ritual``).

Usage (from ``cloud-run/``):

    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... GEMINI_API_KEY=... \\
    python3 scripts/run_morning_ritual_batch.py

    # Restrict to specific profiles (smoke test)
    python3 scripts/run_morning_ritual_batch.py --user-ids <uuid> <uuid2>

    # JSON summary only
    python3 scripts/run_morning_ritual_batch.py --json

Environment (same as deployed Cloud Run batch):
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY — required
    GEMINI_API_KEY — required for generation (see ``getviews_pipeline/config.py``)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("morning_ritual_batch")


def main() -> None:
    parser = argparse.ArgumentParser(description="GetViews morning ritual batch")
    parser.add_argument(
        "--user-ids",
        nargs="*",
        default=None,
        help="Profile UUIDs to process. Omit to process every profile with primary_niche set.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print RitualBatchSummary as JSON to stdout.",
    )
    args = parser.parse_args()

    from getviews_pipeline.morning_ritual import run_morning_ritual_batch
    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    user_ids: list[str] | None = args.user_ids if args.user_ids else None
    logger.info("Starting morning ritual batch user_ids=%s", user_ids or "ALL")
    summary = run_morning_ritual_batch(client, user_ids)

    if args.json:
        print(json.dumps(summary.__dict__, default=str, indent=2))
    else:
        print(f"\n{'='*60}")
        print("  Morning ritual batch complete")
        print(f"{'='*60}")
        print(f"  generated:              {summary.generated}")
        print(f"  skipped_thin:           {summary.skipped_thin}")
        print(f"  failed_schema:          {summary.failed_schema}")
        print(f"  failed_gemini:          {summary.failed_gemini}")
        print(f"  failed_duplicate_hooks: {summary.failed_duplicate_hooks}")
        print(f"  failed_upsert:          {summary.failed_upsert}")
        print(f"  users_no_niche:         {summary.users_no_niche}")
        print(f"{'='*60}\n")

    if summary.failed_gemini or summary.failed_schema or summary.failed_upsert:
        sys.exit(1)


if __name__ == "__main__":
    main()
