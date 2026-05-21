"""Hashtag → content_class_id map v2 (Phase 0b schema, Phase 3 learn loop)."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_cache: dict[str, list[tuple[int, float]]] = {}
_cache_ts: float = 0.0
_cache_lock = asyncio.Lock()
CACHE_TTL = 3600
PRUNE_MIN_YIELD = 0.0
PRUNE_STALE_DAYS = 14


async def _refresh_cache(client: Any) -> None:
    global _cache, _cache_ts
    async with _cache_lock:
        if time.time() - _cache_ts < CACHE_TTL and _cache:
            return
        try:
            loop = asyncio.get_event_loop()

            def _fetch() -> list[dict[str, Any]]:
                return (
                    client.table("hashtag_class_map")
                    .select("hashtag, content_class_id, confidence")
                    .gte("confidence", 0.5)
                    .order("confidence", desc=True)
                    .limit(10_000)
                    .execute()
                    .data
                    or []
                )

            rows = await loop.run_in_executor(None, _fetch)
            new_cache: dict[str, list[tuple[int, float]]] = {}
            for r in rows:
                h = str(r.get("hashtag") or "").lower().lstrip("#")
                if not h:
                    continue
                cc = int(r["content_class_id"])
                conf = float(r.get("confidence") or 0.5)
                new_cache.setdefault(h, []).append((cc, conf))
            _cache = new_cache
            _cache_ts = time.time()
            logger.info("[hashtag_class_map] cache refreshed: %d tags", len(_cache))
        except Exception as exc:
            logger.warning("[hashtag_class_map] cache refresh failed: %s", exc)


async def classify_from_hashtags(
    hashtags: list[str],
    client: Any,
) -> int | None:
    """Return best content_class_id from hashtag overlap, or None."""
    await _refresh_cache(client)
    filtered = [h.lower().lstrip("#") for h in (hashtags or []) if h]
    if not filtered:
        return None
    scores: dict[int, float] = {}
    for h in filtered:
        for cc_id, conf in _cache.get(h, []):
            scores[cc_id] = scores.get(cc_id, 0.0) + conf
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]


def fetch_map_hashtags_for_class_sync(
    client: Any,
    content_class_id: int,
    *,
    limit: int = 25,
) -> list[str]:
    """Top hashtags for a class from hashtag_class_map (yield/confidence order)."""
    try:
        rows = (
            client.table("hashtag_class_map")
            .select("hashtag, confidence, yield_14d")
            .eq("content_class_id", int(content_class_id))
            .gte("confidence", 0.5)
            .order("yield_14d", desc=True, nullsfirst=False)
            .order("confidence", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.debug("[hashtag_class_map] fetch for class=%s failed: %s", content_class_id, exc)
        return []
    out: list[str] = []
    seen: set[str] = set()
    for r in rows:
        h = str(r.get("hashtag") or "").lower().lstrip("#")
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out


def update_yields_from_global_rpc_sync(client: Any) -> int:
    """Refresh yield_14d on map rows from corpus_hashtag_yields_14d (global hashtag counts)."""
    try:
        result = client.rpc("corpus_hashtag_yields_14d", {}).execute()
        rows = result.data or []
    except Exception as exc:
        logger.warning("[hashtag_class_map] yield RPC failed: %s", exc)
        return 0
    yield_by_tag: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        tag = str(row.get("hashtag") or row.get("tag") or "").lower().lstrip("#")
        cnt = row.get("yield_14d") or row.get("count") or row.get("ingest_count")
        if tag and cnt is not None:
            try:
                yield_by_tag[tag] = float(cnt)
            except (TypeError, ValueError):
                pass
    if not yield_by_tag:
        return 0
    updated = 0
    now = datetime.now(UTC).isoformat()
    for tag, yld in list(yield_by_tag.items())[:500]:
        try:
            client.table("hashtag_class_map").update({
                "yield_14d": yld,
                "updated_at": now,
            }).eq("hashtag", tag).execute()
            updated += 1
        except Exception:
            pass
    return updated


def prune_stale_map_entries_sync(client: Any) -> int:
    """Drop map rows with low yield unseen for PRUNE_STALE_DAYS."""
    cutoff = (datetime.now(UTC) - timedelta(days=PRUNE_STALE_DAYS)).isoformat()
    try:
        stale = (
            client.table("hashtag_class_map")
            .select("hashtag, content_class_id")
            .lt("last_seen_at", cutoff)
            .lt("yield_14d", PRUNE_MIN_YIELD)
            .limit(500)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[hashtag_class_map] prune select failed: %s", exc)
        return 0
    pruned = 0
    for row in stale:
        try:
            client.table("hashtag_class_map").delete().eq(
                "hashtag", row["hashtag"],
            ).eq("content_class_id", row["content_class_id"]).execute()
            pruned += 1
        except Exception:
            pass
    if pruned:
        logger.info("[hashtag_class_map] pruned %d stale rows", pruned)
    return pruned


def expand_trending_seeds_sync(
    client: Any,
    *,
    content_class_id: int,
    signal_hashtags: list[str],
) -> int:
    """Seed class map from ingest target signal hashtags + top corpus hashtags for class."""
    written = 0
    now = datetime.now(UTC).isoformat()
    seeds: list[str] = []
    for raw in signal_hashtags or []:
        h = str(raw).lower().lstrip("#")
        if h and h not in seeds:
            seeds.append(h)
    try:
        corpus_rows = (
            client.table("video_corpus")
            .select("hashtags")
            .eq("content_class_id", int(content_class_id))
            .gte("indexed_at", (datetime.now(UTC) - timedelta(days=14)).isoformat())
            .limit(200)
            .execute()
            .data
            or []
        )
        tag_counts: dict[str, int] = {}
        for row in corpus_rows:
            for tag in row.get("hashtags") or []:
                h = str(tag).lower().lstrip("#")
                if h:
                    tag_counts[h] = tag_counts.get(h, 0) + 1
        for h, _ in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
            if h not in seeds:
                seeds.append(h)
    except Exception as exc:
        logger.debug("[hashtag_class_map] expand corpus scan failed: %s", exc)

    for h in seeds[:25]:
        try:
            client.table("hashtag_class_map").upsert({
                "hashtag": h,
                "content_class_id": int(content_class_id),
                "confidence": 0.55,
                "source": "ed_trending",
                "last_seen_at": now,
                "occurrences": 1,
            }, on_conflict="hashtag,content_class_id").execute()
            written += 1
        except Exception:
            pass
    return written


async def learn_from_corpus_row(
    client: Any,
    *,
    hashtags: list[str],
    content_class_id: int,
    source: str = "batch_learn",
    min_confidence: float = 0.6,
) -> int:
    """Upsert hashtag→class observations from an indexed row."""
    written = 0
    now = datetime.now(UTC).isoformat()
    for raw in hashtags or []:
        h = str(raw).lower().lstrip("#")
        if not h or len(h) < 2:
            continue
        try:
            client.table("hashtag_class_map").upsert({
                "hashtag": h,
                "content_class_id": content_class_id,
                "confidence": min_confidence,
                "source": source,
                "last_seen_at": now,
                "occurrences": 1,
            }, on_conflict="hashtag,content_class_id").execute()
            written += 1
        except Exception as exc:
            logger.debug("[hashtag_class_map] learn skip #%s: %s", h, exc)
    return written


def pick_hashtags_for_class(
    signal_hashtags: list[str],
    *,
    thin: bool = False,
    extra_from_map: list[str] | None = None,
) -> list[str]:
    """Build hashtag fetch list for a content-class ingest target."""
    limit = 25 if thin else 15
    merged: list[str] = []
    seen: set[str] = set()
    for src in (extra_from_map or [], signal_hashtags or []):
        for t in src:
            frag = str(t).strip().lstrip("#").lower()
            if frag and frag not in seen:
                seen.add(frag)
                merged.append(frag)
            if len(merged) >= limit:
                return merged
    return merged


def run_hashtag_map_maintenance_sync(client: Any) -> dict[str, int]:
    """Nightly learn/prune/yield refresh for all active ingest targets."""
    summary = {"yield_updated": 0, "pruned": 0, "expanded": 0}
    summary["yield_updated"] = update_yields_from_global_rpc_sync(client)
    summary["pruned"] = prune_stale_map_entries_sync(client)
    try:
        targets = (
            client.table("content_class_ingest_targets")
            .select("content_class_id, signal_hashtags, viability_tier")
            .eq("active", True)
            .limit(100)
            .execute()
            .data
            or []
        )
    except Exception:
        targets = []
    for t in targets:
        cc = int(t["content_class_id"])
        if t.get("viability_tier") in ("Thin", "Dormant"):
            summary["expanded"] += expand_trending_seeds_sync(
                client,
                content_class_id=cc,
                signal_hashtags=t.get("signal_hashtags") or [],
            )
    return summary
