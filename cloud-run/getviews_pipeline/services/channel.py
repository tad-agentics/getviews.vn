"""Channel-context and creator-comparison service.

Phase 1.1: thin re-export from pipelines.py so callers can migrate to
services.channel without a code change on their end.

Phase 4.1 (v5 feature): this module owns per_format_views aggregation
and channel snapshot caching (Phase 5.5 — 24h TTL).

Phase 5.5 — channel snapshot caching:
  Same creator handle requested twice within 24h reuses the cached
  ``per_format_views`` + recent posts context rather than re-querying
  EnsembleData (which costs ~4s per handle lookup) or video_corpus.
  Cache is in-process (dict + TTL timestamp) — appropriate for the
  min-instances=1 user pod.  Channel data is stable within a day.

  Cache key: normalized handle (lowercase, no @).
  TTL: 24 hours (CHANNEL_SNAPSHOT_TTL_SECONDS).
  Eviction: LRU via size cap — CHANNEL_SNAPSHOT_MAX_ENTRIES entries max.
  Thread-safety: write under _lock; read without lock (dict access is
  atomic in CPython due to the GIL; worst case a stale read triggers a
  redundant fetch, not a crash).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from getviews_pipeline.pipelines import (  # noqa: F401
    fetch_channel_context_sync as _fetch_channel_context_sync,
)
from getviews_pipeline.pipelines import (
    refine_performance_tier,
)

logger = logging.getLogger(__name__)

CHANNEL_SNAPSHOT_TTL_SECONDS = 86_400  # 24h
CHANNEL_SNAPSHOT_MAX_ENTRIES = 500     # evict oldest when cap exceeded

_channel_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_lock = threading.Lock()


def _normalize_handle(handle: str) -> str:
    return handle.strip().lstrip("@").strip().lower()


def _evict_if_needed() -> None:
    """Drop the oldest half of the cache when the size cap is hit."""
    if len(_channel_cache) <= CHANNEL_SNAPSHOT_MAX_ENTRIES:
        return
    sorted_keys = sorted(_channel_cache, key=lambda k: _channel_cache[k][0])
    for k in sorted_keys[: len(sorted_keys) // 2]:
        _channel_cache.pop(k, None)


def fetch_channel_context_sync(
    creator_handle: str,
    current_video_id: str,
    *,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Cached wrapper around ``pipelines.fetch_channel_context_sync``.

    Returns the channel context dict (same shape as the pipelines version).
    On cache hit (within 24h) the Supabase query is skipped entirely.

    Phase 5.5 guarantee: the first call for a handle fetches from Supabase
    and populates the cache.  Subsequent calls within 24h return the cached
    snapshot immediately (~0ms vs ~200ms for the Supabase round-trip).
    """
    key = _normalize_handle(creator_handle)
    if not key:
        return {"available": False, "reason": "Thiếu handle hoặc video id để tra kênh"}

    now = time.monotonic()

    if not force_refresh:
        cached = _channel_cache.get(key)
        if cached is not None:
            ts, payload = cached
            if now - ts < CHANNEL_SNAPSHOT_TTL_SECONDS:
                logger.debug("[channel_cache] hit handle=%s", key)
                try:
                    from getviews_pipeline.observability import log_channel_cache_event
                    log_channel_cache_event(
                        event="channel_cache_hit",
                        handle=key,
                        cache_age_sec=round(now - ts, 1),
                    )
                except Exception:
                    pass
                return payload
            # Expired — fall through to refresh.

    try:
        from getviews_pipeline.observability import log_channel_cache_event
        log_channel_cache_event(event="channel_cache_miss", handle=key, cache_age_sec=None)
    except Exception:
        pass
    result = _fetch_channel_context_sync(creator_handle, current_video_id)

    # Only cache successful, available responses so a Supabase error doesn't
    # poison the cache slot for 24h.
    if result.get("available"):
        with _lock:
            _evict_if_needed()
            _channel_cache[key] = (now, result)
            logger.debug("[channel_cache] stored handle=%s", key)

    return result


def channel_cache_stats() -> dict[str, Any]:
    """Return diagnostic info about the in-process cache (for Phase 5.8 observability)."""
    now = time.monotonic()
    valid = sum(
        1 for ts, _ in _channel_cache.values() if now - ts < CHANNEL_SNAPSHOT_TTL_SECONDS
    )
    return {
        "total_entries": len(_channel_cache),
        "valid_entries": valid,
        "stale_entries": len(_channel_cache) - valid,
        "ttl_seconds": CHANNEL_SNAPSHOT_TTL_SECONDS,
        "max_entries": CHANNEL_SNAPSHOT_MAX_ENTRIES,
    }


def clear_channel_cache(handle: str | None = None) -> None:
    """Invalidate the channel snapshot cache (test helper + force_refresh path)."""
    with _lock:
        if handle is None:
            _channel_cache.clear()
        else:
            _channel_cache.pop(_normalize_handle(handle), None)


__all__ = [
    "fetch_channel_context_sync",
    "refine_performance_tier",
    "channel_cache_stats",
    "clear_channel_cache",
    "CHANNEL_SNAPSHOT_TTL_SECONDS",
    "CHANNEL_SNAPSHOT_MAX_ENTRIES",
]
