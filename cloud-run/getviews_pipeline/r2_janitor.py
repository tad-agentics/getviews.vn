"""R2 storage janitor — delete orphaned R2 objects.

When a ``video_corpus`` row is deleted, FK cascades remove dependent
``video_shots`` and ``video_diagnostics`` rows in Postgres, but the
R2-stored objects (video files, thumbnails, scene frames, extracted
frames) are NOT cleaned up — those live in Cloudflare R2 outside the
DB transaction.

This module reconciles R2 storage against the live ``video_corpus``
table. Any object whose key references a video_id no longer in
``video_corpus`` is treated as orphaned and deleted.

R2 key prefixes covered (must match the upload paths in ``r2.py``):
  - ``videos/{video_id}.mp4``                — full clips
  - ``thumbnails/{video_id}.{ext}``          — thumbnails
  - ``frames/{video_id}/{i}.png``            — Wave-1 ``FRAME_TIMESTAMPS_SEC`` frames
  - ``video_shots/{video_id}/{n}.jpg``       — Wave-2.5 per-scene frames

Safety design:
  - Pulls the live video_id set into memory once per run, then streams
    R2 objects in pages and reconciles each. Keeps memory bounded.
  - ``dry_run=True`` (default) lists orphans without deleting. Set
    ``dry_run=False`` only when running the destructive pass.
  - Deletes in batches of 1000 (S3 ``DeleteObjects`` cap).
  - Per-prefix counters surfaced in the summary so an operator can
    spot a misconfigured prefix (e.g. all `videos/` flagged orphan
    would mean a key-pattern drift, not a real cleanup).

Cost: zero Gemini, zero ED. R2 LIST + DELETE class A operations are
~$4.50 per million; a corpus of 2k videos × 4 prefixes × ~5 keys
each = ~40k LIST ops = $0.18 per full sweep. Cheap to run weekly.

Usage:
    from getviews_pipeline.r2_janitor import run_r2_janitor
    summary = run_r2_janitor(dry_run=True)   # preview
    summary = run_r2_janitor(dry_run=False)  # destructive
"""

from __future__ import annotations

import logging
import re
from typing import Any

from getviews_pipeline.r2 import _get_r2_client, r2_configured

logger = logging.getLogger(__name__)

from getviews_pipeline.config import R2_BUCKET_NAME

# Key patterns — extract video_id from the R2 object key. Must match
# the upload paths in r2.py. If a new prefix is added in r2.py, mirror
# it here AND in PREFIXES below.
_VIDEO_ID_PATTERN_BY_PREFIX: dict[str, re.Pattern[str]] = {
    "videos/":      re.compile(r"^videos/([^/.]+)\.mp4$"),
    "thumbnails/":  re.compile(r"^thumbnails/([^/.]+)\.[A-Za-z0-9]+$"),
    "frames/":      re.compile(r"^frames/([^/]+)/\d+\.png$"),
    "video_shots/": re.compile(r"^video_shots/([^/]+)/\d+\.jpg$"),
}

PREFIXES = tuple(_VIDEO_ID_PATTERN_BY_PREFIX.keys())

# S3 DeleteObjects request hard cap (AWS spec; R2 honors it).
_DELETE_BATCH_SIZE = 1000

# LIST page size — R2 default is 1000, can be raised via MaxKeys.
# Keeping at 1000 to stay simple and not hit any R2 quota oddities.
_LIST_PAGE_SIZE = 1000


def _live_video_ids(client: Any) -> set[str]:
    """Pull the live video_id set from video_corpus into memory.

    Uses small page reads to avoid building one giant SELECT result
    that PostgREST would refuse. Each row is just a TEXT id so memory
    pressure is low (~50 bytes × N rows).
    """
    ids: set[str] = set()
    page_size = 5000
    last_seen: str | None = None

    while True:
        q = (
            client.table("video_corpus")
            .select("video_id")
            .order("video_id")
            .limit(page_size)
        )
        if last_seen is not None:
            q = q.gt("video_id", last_seen)
        rows = (q.execute()).data or []
        if not rows:
            break
        for row in rows:
            vid = row.get("video_id")
            if vid:
                ids.add(vid)
        last_seen = rows[-1].get("video_id")
        if len(rows) < page_size:
            break

    logger.info("[r2-janitor] live video_corpus ids: %d", len(ids))
    return ids


def _extract_video_id(prefix: str, key: str) -> str | None:
    """Pull the video_id out of an R2 object key. Returns None if the
    key doesn't match the expected pattern for its prefix (which would
    indicate a key-pattern drift in r2.py — caller should log + skip)."""
    pat = _VIDEO_ID_PATTERN_BY_PREFIX.get(prefix)
    if pat is None:
        return None
    m = pat.match(key)
    return m.group(1) if m else None


def _list_keys_under_prefix(s3_client: Any, prefix: str) -> Any:
    """Yield R2 object keys under prefix, paginated. Caller iterates."""
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(
        Bucket=R2_BUCKET_NAME, Prefix=prefix, MaxKeys=_LIST_PAGE_SIZE,
    ):
        for obj in page.get("Contents", []) or []:
            yield obj.get("Key", "")


def _delete_keys_batch(s3_client: Any, keys: list[str]) -> int:
    """Delete up to _DELETE_BATCH_SIZE keys via S3 DeleteObjects.

    Returns the number of keys successfully deleted (R2 returns Errors
    for any that failed; we just log + skip). Empty input → 0."""
    if not keys:
        return 0
    resp = s3_client.delete_objects(
        Bucket=R2_BUCKET_NAME,
        Delete={"Objects": [{"Key": k} for k in keys], "Quiet": False},
    )
    deleted_count = len(resp.get("Deleted", []) or [])
    errors = resp.get("Errors", []) or []
    if errors:
        for err in errors:
            logger.warning(
                "[r2-janitor] delete failed key=%s code=%s msg=%s",
                err.get("Key"), err.get("Code"), err.get("Message"),
            )
    return deleted_count


def run_r2_janitor(
    *,
    dry_run: bool = True,
    client: Any | None = None,
) -> dict[str, Any]:
    """Reconcile R2 storage against ``video_corpus`` and delete orphans.

    Returns a summary dict:
      - mode: "dry_run" or "destructive"
      - live_video_ids: count from video_corpus
      - per_prefix: {prefix: {scanned, kept, orphaned, deleted, malformed}}
      - total_deleted: sum across prefixes (0 in dry_run)
      - r2_configured: bool — janitor exits early when R2 is not set up

    Safe to run when R2 is unconfigured — returns a summary with
    `r2_configured=False` and does no S3 work.
    """
    summary: dict[str, Any] = {
        "mode": "dry_run" if dry_run else "destructive",
        "r2_configured": r2_configured(),
        "live_video_ids": 0,
        "per_prefix": {},
        "total_deleted": 0,
    }

    if not r2_configured():
        logger.warning("[r2-janitor] R2 not configured — exit early")
        return summary

    if client is None:
        from getviews_pipeline.supabase_client import get_service_client
        client = get_service_client()

    live_ids = _live_video_ids(client)
    summary["live_video_ids"] = len(live_ids)

    s3 = _get_r2_client()

    for prefix in PREFIXES:
        scanned = kept = malformed = 0
        orphan_keys: list[str] = []
        per_prefix_deleted = 0

        for key in _list_keys_under_prefix(s3, prefix):
            scanned += 1
            vid = _extract_video_id(prefix, key)
            if vid is None:
                # Key didn't match the expected pattern — log + skip.
                # Don't delete malformed keys; an unrecognized pattern
                # is more likely a code drift than a true orphan.
                malformed += 1
                logger.warning(
                    "[r2-janitor] malformed key under %s: %s", prefix, key,
                )
                continue
            if vid in live_ids:
                kept += 1
                continue
            orphan_keys.append(key)

            # Flush a destructive batch as soon as we hit the cap, so
            # memory footprint stays bounded for very large prefixes.
            if not dry_run and len(orphan_keys) >= _DELETE_BATCH_SIZE:
                per_prefix_deleted += _delete_keys_batch(s3, orphan_keys)
                orphan_keys = []

        # Flush any tail batch.
        if not dry_run and orphan_keys:
            per_prefix_deleted += _delete_keys_batch(s3, orphan_keys)
            orphan_keys = []

        # In dry_run, orphan_keys still contains the (un-flushed) tail
        # which inflates the orphaned counter. Recompute orphaned from
        # scanned-kept-malformed to be exact.
        orphaned = scanned - kept - malformed

        summary["per_prefix"][prefix] = {
            "scanned": scanned,
            "kept": kept,
            "malformed": malformed,
            "orphaned": orphaned,
            "deleted": per_prefix_deleted,
        }
        summary["total_deleted"] += per_prefix_deleted

        logger.info(
            "[r2-janitor] %s — scanned=%d kept=%d orphaned=%d deleted=%d malformed=%d",
            prefix, scanned, kept, orphaned, per_prefix_deleted, malformed,
        )

    logger.info(
        "[r2-janitor] done — mode=%s live_ids=%d total_deleted=%d",
        summary["mode"], summary["live_video_ids"], summary["total_deleted"],
    )
    return summary
