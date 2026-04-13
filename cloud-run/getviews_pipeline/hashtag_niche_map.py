"""hashtag_niche_map — DB-backed hashtag→niche classification with auto-learning.

Two public entry points:

    classify_from_hashtags(hashtags, client) -> int | None
        Looks up each hashtag in hashtag_niche_map (cached, refreshed hourly).
        Returns the niche_id with the most overlapping hashtags, or None.

    learn_hashtag_mappings(video_hashtags, niche_id, niche_source, client)
        Upserts new hashtag→niche observations learned during batch ingest.
        Only called when niche_source is "onboarding" or "topics" to avoid
        circular dependency (never learn from hashtag-classified videos).

Cache:
    In-process module-level dicts, refreshed every CACHE_TTL seconds.
    Each Cloud Run instance caches independently — no Redis needed.
    A fresh batch run always gets a fresh cache within one hour.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from getviews_pipeline.helpers import GENERIC_HASHTAGS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache state (module-level, per-instance)
# ---------------------------------------------------------------------------

_hashtag_to_niche: dict[str, int] = {}   # hashtag → niche_id (active only)
_generic_set: frozenset[str] = GENERIC_HASHTAGS  # merged with DB generics
_cache_ts: float = 0.0
_cache_lock = asyncio.Lock()
CACHE_TTL = 3600  # seconds


async def _refresh_cache(client: Any) -> None:
    """Reload active mappings and generic set from hashtag_niche_map.

    Runs at most once per CACHE_TTL window. Thread-safe via asyncio.Lock.
    Falls back to existing cache on any Supabase error.
    """
    global _hashtag_to_niche, _generic_set, _cache_ts

    async with _cache_lock:
        # Double-checked locking: another coroutine may have refreshed while we waited.
        if time.time() - _cache_ts < CACHE_TTL and _hashtag_to_niche:
            return

        try:
            loop = asyncio.get_event_loop()

            def _fetch_active() -> list[dict[str, Any]]:
                return (
                    client.table("hashtag_niche_map")
                    .select("hashtag, niche_id")
                    .eq("is_generic", False)
                    .gte("occurrences", 10)
                    .execute()
                    .data or []
                )

            def _fetch_generics() -> list[dict[str, Any]]:
                return (
                    client.table("hashtag_niche_map")
                    .select("hashtag")
                    .eq("is_generic", True)
                    .execute()
                    .data or []
                )

            active_rows, generic_rows = await asyncio.gather(
                loop.run_in_executor(None, _fetch_active),
                loop.run_in_executor(None, _fetch_generics),
            )

            _hashtag_to_niche = {r["hashtag"]: r["niche_id"] for r in active_rows}
            _generic_set = GENERIC_HASHTAGS | frozenset(r["hashtag"] for r in generic_rows)
            _cache_ts = time.time()

            logger.info(
                "[hashtag_map] cache refreshed: %d active mappings, %d generic tags",
                len(_hashtag_to_niche),
                len(_generic_set),
            )
        except Exception as exc:
            logger.warning("[hashtag_map] cache refresh failed — using stale cache: %s", exc)


# ---------------------------------------------------------------------------
# classify_from_hashtags
# ---------------------------------------------------------------------------

async def classify_from_hashtags(
    hashtags: list[str],
    client: Any,
) -> int | None:
    """Classify a video into a niche_id based on its hashtags.

    Filters out generic tags, then scores remaining tags against the cached
    hashtag→niche mapping. Returns the niche_id with the highest overlap count.
    Returns None if no non-generic hashtags match any niche.

    Args:
        hashtags: Raw hashtag strings from the video (with or without leading #).
        client:   Supabase service-role client (sync supabase-py client).
    """
    await _refresh_cache(client)

    filtered = [
        h.lower().lstrip("#")
        for h in (hashtags or [])
        if h.lower().lstrip("#") not in _generic_set
    ]
    if not filtered:
        return None

    scores: dict[int, int] = {}
    for ht in filtered:
        niche_id = _hashtag_to_niche.get(ht)
        if niche_id is not None:
            scores[niche_id] = scores.get(niche_id, 0) + 1

    if not scores:
        return None

    return max(scores, key=lambda k: scores[k])


# ---------------------------------------------------------------------------
# learn_hashtag_mappings
# ---------------------------------------------------------------------------

async def learn_hashtag_mappings(
    video_hashtags: list[str],
    niche_id: int,
    niche_source: str,
    client: Any,
) -> None:
    """Learn new hashtag→niche mappings from a batch-indexed video.

    CRITICAL: Only learn when niche_source is "onboarding" or "topics".
    Never learn from hashtag-classified videos (niche_source="hashtags") —
    that would create a circular dependency where low-confidence assignments
    reinforce themselves over time.

    Learning rules:
      - New hashtag → insert with occurrences=1, niche_id=niche_id
      - Same hashtag, same niche → increment occurrences
      - Same hashtag, different niche → increment niche_count; if niche_count≥3
        mark is_generic=true (cross-niche tag → exclude from classification)
      - Already generic → skip

    Args:
        video_hashtags: Raw hashtag strings from the video.
        niche_id:       The niche the video was classified into.
        niche_source:   How the niche was determined ("onboarding"|"topics"|
                        "hashtags"|"fallback").
        client:         Supabase service-role client (sync).
    """
    # "corpus_batch" = video was fetched for a specific niche during batch ingest.
    # Niche is determined by which niche_taxonomy row was queried — reliable ground truth.
    if niche_source not in ("onboarding", "topics", "corpus_batch"):
        return

    if not niche_id or not video_hashtags:
        return

    loop = asyncio.get_event_loop()

    for ht in video_hashtags:
        ht_clean = ht.lower().lstrip("#")
        # Skip known generics and too-short tags (e.g. "vn", "vl")
        if ht_clean in _generic_set or len(ht_clean) < 3:
            continue

        try:
            await loop.run_in_executor(
                None,
                lambda h=ht_clean: _upsert_one(client, h, niche_id),
            )
        except Exception as exc:
            logger.warning("[hashtag_map] learn failed for '%s': %s", ht_clean, exc)


def _upsert_one(client: Any, hashtag: str, niche_id: int) -> None:
    """Sync helper: fetch existing row and upsert with updated counts."""
    result = (
        client.table("hashtag_niche_map")
        .select("niche_id, occurrences, niche_count, is_generic")
        .eq("hashtag", hashtag)
        .limit(1)
        .execute()
    )
    rows = result.data or []

    if not rows:
        # First time we've seen this hashtag — insert
        client.table("hashtag_niche_map").insert({
            "hashtag": hashtag,
            "niche_id": niche_id,
            "occurrences": 1,
            "niche_count": 1,
            "source": "corpus",
            "is_generic": False,
        }).execute()
        return

    row = rows[0]

    # Already generic — nothing to learn
    if row.get("is_generic"):
        return

    if row.get("niche_id") == niche_id:
        # Same niche: strengthen the mapping
        client.table("hashtag_niche_map").update({
            "occurrences": (row.get("occurrences") or 0) + 1,
            "updated_at": "now()",
        }).eq("hashtag", hashtag).execute()
    else:
        # Different niche: this tag crosses niches → track ambiguity
        new_niche_count = (row.get("niche_count") or 1) + 1
        update: dict[str, Any] = {
            "niche_count": new_niche_count,
            "updated_at": "now()",
        }
        if new_niche_count >= 3:
            # Seen in 3+ niches → too ambiguous, mark generic
            update["is_generic"] = True
            logger.info(
                "[hashtag_map] '%s' marked generic (niche_count=%d)", hashtag, new_niche_count
            )
        client.table("hashtag_niche_map").update(update).eq("hashtag", hashtag).execute()


# ---------------------------------------------------------------------------
# Force cache invalidation (for testing / manual trigger)
# ---------------------------------------------------------------------------

def invalidate_cache() -> None:
    """Reset cache timestamp so next classify_from_hashtags call re-fetches."""
    global _cache_ts
    _cache_ts = 0.0
