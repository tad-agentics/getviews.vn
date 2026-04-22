"""Cache layer for comment_radar.

Keeps Supabase + EnsembleData imports out of the pure scorer (comment_radar.py
stays unit-testable). Callers request `resolve_comment_radar(video_id)` and
get back the already-scored dict ready to forward to the client.

Flow:
    1. SELECT comment_radar, comment_radar_fetched_at FROM video_corpus
    2. If cached + fresh (< CACHE_TTL_DAYS) → return cached dict.
    3. Else → fetch_comments_for_video → score_comments → UPDATE + return.
    4. Any failure → None. Never raises to the caller.

Concurrency (BUG-09, QA audit 2026-04-22): VideoScreen fires two
``POST /video/analyze`` calls in parallel (mode=win + mode=flop — different
React Query cache keys). On a cold comment_radar cache both calls raced
past the read, fetched comments from EnsembleData independently, scored
slightly different 50-comment samples (TikTok orders newest-first, so a
new comment arriving between the two fetches shifts membership), and each
wrote its own radar — users saw 24/76/0 on one tab and 28/72/0 on the
other for the same video. A per-video asyncio lock collapses the races:
whichever call arrives first does the fetch + writeback, the second waits
on the lock, reads the freshly-written cache, and returns identical data.
"""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = 7

# Per-video async locks. Lazily created on first use, indexed by
# ``video_id``. We never prune — the dict grows with the working set of
# concurrently-analysed videos, which is bounded by Cloud Run's request
# concurrency (currently 4–8) × a short window. A long-lived instance
# might accumulate a few hundred Lock objects at worst.
_FETCH_LOCKS: dict[str, asyncio.Lock] = {}

# In-flight result cache. Populated inside the lock once a fetch
# completes; the second caller re-reads this map after acquiring the
# lock. Falls through when the DB cache also has the row (which is the
# normal case on Cloud Run); matters in tests + edge cases where
# ``_anon_client`` is unavailable and the DB cache read is skipped.
# Bounded LRU so a long-lived instance can't leak memory — each entry is
# a small dict; 1024 entries × ~1KB ≈ 1MB at the cap.
_INFLIGHT_MAX = 1024
_INFLIGHT_RESULTS: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _remember_inflight(video_id: str, radar: dict[str, Any]) -> None:
    _INFLIGHT_RESULTS[video_id] = radar
    _INFLIGHT_RESULTS.move_to_end(video_id)
    while len(_INFLIGHT_RESULTS) > _INFLIGHT_MAX:
        _INFLIGHT_RESULTS.popitem(last=False)


def _fetch_lock(video_id: str) -> asyncio.Lock:
    lock = _FETCH_LOCKS.get(video_id)
    if lock is None:
        lock = asyncio.Lock()
        _FETCH_LOCKS[video_id] = lock
    return lock


def _is_fresh(fetched_at: str | None) -> bool:
    if not fetched_at:
        return False
    try:
        dt = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc) - dt <= timedelta(days=CACHE_TTL_DAYS)


def _read_cached_sync(client: Any, video_id: str) -> tuple[dict[str, Any] | None, bool]:
    """Return (cached_radar_or_None, is_fresh). cached_radar is None on miss."""
    try:
        res = (
            client.table("video_corpus")
            .select("comment_radar, comment_radar_fetched_at")
            .eq("video_id", video_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None, False
        row = rows[0]
        cached = row.get("comment_radar")
        fetched_at = row.get("comment_radar_fetched_at")
        if not isinstance(cached, dict) or not cached:
            return None, False
        return cached, _is_fresh(fetched_at)
    except Exception as exc:
        logger.warning("[comment_radar_cache] read failed for %s: %s", video_id, exc)
        return None, False


def _write_cached_sync(video_id: str, radar: dict[str, Any]) -> None:
    """Persist comment radar using service_role — anon cannot UPDATE video_corpus."""
    try:
        from getviews_pipeline.supabase_client import get_service_client

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        get_service_client().table("video_corpus").update(
            {
                "comment_radar": radar,
                "comment_radar_fetched_at": now_iso,
            }
        ).eq("video_id", video_id).execute()
    except Exception as exc:
        logger.warning("[comment_radar_cache] write failed for %s: %s", video_id, exc)


async def resolve_comment_radar(
    video_id: str,
    *,
    comment_count_hint: int = 0,
) -> dict[str, Any] | None:
    """Return a comment_radar dict for `video_id`, using cache when possible.

    `comment_count_hint` lets us short-circuit a fetch when the video has very
    few comments (< 5) — the radar would be statistically noisy and the
    EnsembleData unit would be wasted.

    Fails open — returns None if anything upstream errors. The caller is
    expected to treat None as "no radar available today."
    """
    vid = str(video_id or "").strip()
    if not vid:
        return None

    if comment_count_hint > 0 and comment_count_hint < 5:
        logger.info(
            "[comment_radar_cache] skip fetch for %s — only %d comments available",
            vid, comment_count_hint,
        )
        return None

    from getviews_pipeline.comment_radar import (
        fetch_comments_for_video,
        score_comments,
    )
    from getviews_pipeline.corpus_context import _anon_client
    from getviews_pipeline.runtime import run_sync

    try:
        client = _anon_client()
    except Exception as exc:
        logger.warning("[comment_radar_cache] Supabase client unavailable: %s", exc)
        client = None

    # Cache read first — cheap, doesn't need the lock.
    if client is not None:
        cached, fresh = await run_sync(_read_cached_sync, client, vid)
        if cached and fresh:
            logger.info("[comment_radar_cache] cache hit (fresh) for %s", vid)
            return cached

    # Serialise refetches per video_id so two concurrent callers (typical
    # VideoScreen pattern: mode=win + mode=flop fired together) share one
    # fetch + writeback. Whichever arrives second re-reads the cache after
    # the lock releases and returns the freshly-written radar.
    async with _fetch_lock(vid):
        # The in-flight map is the dedupe signal that works even when the
        # DB cache read was skipped (e.g. anon client unavailable).
        inflight = _INFLIGHT_RESULTS.get(vid)
        if inflight is not None:
            logger.info("[comment_radar_cache] in-flight hit for %s", vid)
            return inflight
        if client is not None:
            cached, fresh = await run_sync(_read_cached_sync, client, vid)
            if cached and fresh:
                logger.info(
                    "[comment_radar_cache] cache hit (post-lock) for %s", vid,
                )
                return cached
            if cached:
                logger.info(
                    "[comment_radar_cache] cache hit (stale) for %s — refetching",
                    vid,
                )

        # Fetch + score.
        comments = await fetch_comments_for_video(vid)
        if not comments:
            return None
        radar = score_comments(
            comments,
            total_available=max(comment_count_hint, len(comments)),
        )
        radar_dict = radar.asdict()

        # Memoise for any concurrent caller still waiting on the lock
        # (they'll return at the in-flight check above once we release).
        _remember_inflight(vid, radar_dict)

        # Write-back — service_role; best effort, never blocks.
        try:
            await run_sync(_write_cached_sync, vid, radar_dict)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("[comment_radar_cache] post-fetch write failed: %s", exc)

        return radar_dict


__all__ = ["CACHE_TTL_DAYS", "resolve_comment_radar"]
