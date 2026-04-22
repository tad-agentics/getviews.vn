"""One-shot batch: re-run ``classify_format`` on rows stuck in ``other``.

Axis 2 gap (state-of-corpus.md): 37.4% of populated ``content_format``
values bucket to ``other`` — the regex classifier's fallback. Most of
the "other" tail is Vietnamese-specific narrative / explainer / review
patterns the original regex missed, not genuinely uncategorisable
content.

This module pulls every row where ``content_format = 'other' OR
content_format IS NULL`` and re-runs ``classify_format`` on the stored
``analysis_json``. When the updated classifier produces a non-'other'
bucket, the row is updated in place. Zero Gemini calls, zero cost —
pure regex pass on cached extraction output.

Intended usage: one-shot catch-up after a regex expansion. Safe to
re-run — idempotent, only writes rows whose classification actually
changes.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# Scanning batch size for the SELECT pager. Larger = fewer round-trips
# but bigger response payloads (analysis_json can be ~5KB per row).
# 500 keeps each page under ~2.5MB which is fine for PostgREST.
SCAN_PAGE_SIZE = 500


def _select_other_rows(
    client: Any,
    *,
    page_size: int = SCAN_PAGE_SIZE,
    last_created_at: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch one page of 'other' / NULL rows, oldest first."""
    q = (
        client.table("video_corpus")
        .select("video_id, niche_id, content_format, analysis_json, created_at")
        .or_("content_format.eq.other,content_format.is.null")
        .order("created_at", desc=False)
        .limit(page_size)
    )
    if last_created_at is not None:
        q = q.gt("created_at", last_created_at)
    return (q.execute()).data or []


def run_content_format_reclassify(
    *,
    client: Any | None = None,
    page_size: int = SCAN_PAGE_SIZE,
) -> dict[str, Any]:
    """Scan ``video_corpus`` for ``other``/NULL rows and re-classify.

    Returns a summary dict:
      - scanned: total rows inspected
      - reclassified: rows updated (now in a non-'other' bucket)
      - still_other: rows where the updated classifier still returns 'other'
      - errors: per-row update failures
      - by_bucket: Counter of destination buckets for the reclassified rows
    """
    from getviews_pipeline.corpus_ingest import classify_format
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    scanned = reclassified = still_other = errors = 0
    by_bucket: Counter[str] = Counter()

    last_created_at: str | None = None
    while True:
        rows = _select_other_rows(
            client,
            page_size=page_size,
            last_created_at=last_created_at,
        )
        if not rows:
            break

        for row in rows:
            scanned += 1
            analysis_json = row.get("analysis_json") or {}
            niche_id = int(row.get("niche_id") or 0)
            new_format = classify_format(analysis_json, niche_id)

            if new_format == "other" or new_format == row.get("content_format"):
                still_other += 1
                continue

            try:
                (
                    client.table("video_corpus")
                    .update({"content_format": new_format})
                    .eq("video_id", row["video_id"])
                    .execute()
                )
                reclassified += 1
                by_bucket[new_format] += 1
            except Exception as exc:
                logger.warning(
                    "[content_format_reclassify] update failed for %s: %s",
                    row.get("video_id"), exc,
                )
                errors += 1

        last_created_at = rows[-1].get("created_at") or last_created_at
        if len(rows) < page_size:
            break

    logger.info(
        "[content_format_reclassify] scanned=%d reclassified=%d still_other=%d errors=%d",
        scanned, reclassified, still_other, errors,
    )
    return {
        "scanned": scanned,
        "reclassified": reclassified,
        "still_other": still_other,
        "errors": errors,
        "by_bucket": dict(by_bucket),
    }
