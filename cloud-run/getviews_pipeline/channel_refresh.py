"""Per-handle on-demand corpus refresh — closes the daily-batch staleness
gap for the connected creator's own channel.

The nightly ``cron-batch-ingest`` (20:00 UTC) populates ``video_corpus`` per
niche via signal_hashtags. That means a creator's brand-new video posted in
the morning won't appear in their Studio dashboard until the next batch
cycle — up to ~24h of lag, and longer if the creator posts without the
niche's signal hashtags.

This module implements an on-demand per-handle scrape that fires when a
creator opens Studio and their last_ingest_at is older than
``STALE_AFTER_HOURS``. EnsembleData is hit for that single handle only;
Gemini analyzes any new awemes; rows land in ``video_corpus`` like the
batch path, so all downstream surfaces (HomeMyChannelSection percentiles,
ChannelScreen formula, /trends) immediately see the fresh data.

Cost: ~1 ED unit per refresh per active creator per day. Capped at
``MAX_PER_REFRESH`` new videos to bound Gemini spend on a per-call basis.

Anti-spam: 18-hour staleness gate is enforced server-side, so a misbehaving
client tab-spamming /channel/refresh-mine still only triggers one ED scrape
per 18-hour window per handle.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.corpus_ingest import (
    IngestResult,
    _ingest_candidate_awemes,
    _normalize_handle,
)

logger = logging.getLogger(__name__)

STALE_AFTER_HOURS = 18
MAX_PER_REFRESH = 8


def _last_ingest_at_sync(client: Any, *, handle: str, niche_id: int) -> datetime | None:
    """Return MAX(indexed_at) for this handle in this niche, or None."""
    norm = _normalize_handle(handle)
    if not norm:
        return None
    try:
        res = (
            client.table("video_corpus")
            .select("indexed_at")
            .ilike("creator_handle", norm)
            .eq("niche_id", niche_id)
            .order("indexed_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("[refresh-mine] last_ingest_at lookup failed: %s", exc)
        return None
    rows = res.data or []
    if not rows:
        return None
    raw = rows[0].get("indexed_at")
    if not raw:
        return None
    try:
        s = str(raw).replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _existing_aweme_ids_sync(client: Any, *, handle: str, niche_id: int) -> set[str]:
    """All aweme_ids already in video_corpus for this handle+niche."""
    norm = _normalize_handle(handle)
    try:
        res = (
            client.table("video_corpus")
            .select("video_id")
            .eq("niche_id", niche_id)
            .ilike("creator_handle", norm)
            .execute()
        )
    except Exception as exc:
        logger.warning("[refresh-mine] existing-ids lookup failed: %s", exc)
        return set()
    return {row["video_id"] for row in (res.data or []) if row.get("video_id")}


async def refresh_channel_corpus(
    client: Any,
    *,
    handle: str,
    niche_id: int,
    niche_name: str,
    force: bool = False,
) -> dict[str, Any]:
    """Refresh corpus rows for one TikTok handle.

    Skips work if last_ingest_at is within ``STALE_AFTER_HOURS`` (unless
    ``force=True``). Returns a dict the API layer wraps into a JSONResponse:

      ``cached``     — within freshness window, no work done
      ``refreshed``  — ED scrape ran; ``count`` new rows ingested
      ``error``      — ED fetch failed; ``reason`` explains
    """
    norm = _normalize_handle(handle)
    if not norm:
        return {"status": "error", "reason": "empty_handle"}

    last = _last_ingest_at_sync(client, handle=norm, niche_id=niche_id)
    now = datetime.now(timezone.utc)

    if not force and last is not None and (now - last) < timedelta(hours=STALE_AFTER_HOURS):
        return {
            "status": "cached",
            "last_ingest_at": last.isoformat(),
            "stale_after_hours": STALE_AFTER_HOURS,
        }

    try:
        awemes = await ensemble.fetch_user_posts(norm, depth=1)
    except Exception as exc:
        logger.warning("[refresh-mine] fetch_user_posts failed for @%s: %s", norm, exc)
        return {"status": "error", "reason": "ed_fetch_failed", "detail": str(exc)[:200]}

    if not awemes:
        return {
            "status": "refreshed",
            "count": 0,
            "last_ingest_at": last.isoformat() if last else None,
            "reason": "no_videos",
        }

    existing_ids = _existing_aweme_ids_sync(client, handle=norm, niche_id=niche_id)
    new_awemes = [a for a in awemes if str(a.get("aweme_id", "") or "") not in existing_ids]
    if not new_awemes:
        return {
            "status": "refreshed",
            "count": 0,
            "last_ingest_at": now.isoformat(),
            "reason": "all_seen",
        }

    # Cap per-call ingest so a creator who's been offline for a month doesn't
    # trigger a 30-video Gemini run on a single Studio open.
    capped = new_awemes[:MAX_PER_REFRESH]

    try:
        result: IngestResult = await _ingest_candidate_awemes(
            client, niche_id, niche_name, capped,
        )
    except Exception as exc:
        logger.exception("[refresh-mine] ingest failed for @%s: %s", norm, exc)
        return {"status": "error", "reason": "ingest_failed", "detail": str(exc)[:200]}

    return {
        "status": "refreshed",
        "count": result.inserted,
        "skipped": result.skipped,
        "failed": result.failed,
        "last_ingest_at": now.isoformat(),
    }
