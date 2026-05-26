"""Hashtag → content_class_id map v2 (Phase 0b schema, Phase 3 learn loop)."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_SEED_SIGNAL_HASHTAG_LIMIT = 15
_SEED_MAP_HASHTAG_LIMIT = 25


def _norm_hashtag(ht: str) -> str:
    return str(ht or "").strip().lstrip("#").lower()


def _dominant_legacy_niche_for_class_sync(client: Any, content_class_id: int) -> int | None:
    """Representative ``ingest_loop_niche_id`` from corpus rows for this class."""
    try:
        res = (
            client.table("video_corpus")
            .select("ingest_loop_niche_id")
            .eq("content_class_id", int(content_class_id))
            .not_.is_("ingest_loop_niche_id", "null")
            .limit(200)
            .execute()
        )
        counts: dict[int, int] = {}
        for row in res.data or []:
            nid = row.get("ingest_loop_niche_id")
            if nid is not None:
                counts[int(nid)] = counts.get(int(nid), 0) + 1
        if counts:
            return max(counts.items(), key=lambda x: x[1])[0]
    except Exception as exc:
        logger.debug("[hashtag_class_map] dominant legacy niche cc=%s: %s", content_class_id, exc)
    return None


def _legacy_niche_ids_for_class_sync(client: Any, content_class_id: int) -> set[int]:
    """Legacy ``niche_taxonomy.id`` set linked to a content class via junction + corpus."""
    from getviews_pipeline.profile_niches import legacy_niche_id_for_creator_niche

    out: set[int] = set()
    dom = _dominant_legacy_niche_for_class_sync(client, content_class_id)
    if dom is not None:
        out.add(dom)
    try:
        rows = (
            client.table("creator_niche_content_classes")
            .select("creator_niche_id")
            .eq("content_class_id", int(content_class_id))
            .execute()
            .data
            or []
        )
        for row in rows:
            leg = legacy_niche_id_for_creator_niche(int(row["creator_niche_id"]))
            if leg is not None:
                out.add(int(leg))
    except Exception as exc:
        logger.debug("[hashtag_class_map] junction legacy niches cc=%s: %s", content_class_id, exc)
    return out


def _hashtags_from_niche_taxonomy_sync(client: Any, legacy_niche_ids: set[int]) -> list[str]:
    if not legacy_niche_ids:
        return []
    out: list[str] = []
    seen: set[str] = set()
    try:
        rows = (
            client.table("niche_taxonomy")
            .select("signal_hashtags")
            .in_("id", sorted(legacy_niche_ids))
            .execute()
            .data
            or []
        )
        for row in rows:
            for raw in row.get("signal_hashtags") or []:
                h = _norm_hashtag(raw)
                if h and h not in seen:
                    seen.add(h)
                    out.append(h)
    except Exception as exc:
        logger.debug("[hashtag_class_map] niche_taxonomy hashtags: %s", exc)
    return out


def _hashtags_from_niche_map_sync(client: Any, legacy_niche_ids: set[int], *, limit: int) -> list[str]:
    if not legacy_niche_ids:
        return []
    out: list[str] = []
    seen: set[str] = set()
    try:
        rows = (
            client.table("hashtag_niche_map")
            .select("hashtag, occurrences")
            .in_("niche_id", sorted(legacy_niche_ids))
            .eq("is_generic", False)
            .order("occurrences", desc=True)
            .limit(limit * 2)
            .execute()
            .data
            or []
        )
        for row in rows:
            h = _norm_hashtag(row.get("hashtag") or "")
            if h and h not in seen:
                seen.add(h)
                out.append(h)
            if len(out) >= limit:
                break
    except Exception as exc:
        logger.debug("[hashtag_class_map] hashtag_niche_map fetch: %s", exc)
    return out


def _corpus_hashtags_for_class_sync(
    client: Any,
    content_class_id: int,
    *,
    limit: int = 15,
) -> list[str]:
    """Top hashtags observed on indexed corpus rows for this class (all-time)."""
    tag_counts: dict[str, int] = {}
    offset = 0
    page_size = 500
    try:
        while offset < 2000:
            rows = (
                client.table("video_corpus")
                .select("hashtags")
            .eq("content_class_id", int(content_class_id))
            .range(offset, offset + page_size - 1)
                .execute()
                .data
                or []
            )
            if not rows:
                break
            for row in rows:
                for tag in row.get("hashtags") or []:
                    h = _norm_hashtag(tag)
                    if h:
                        tag_counts[h] = tag_counts.get(h, 0) + 1
            if len(rows) < page_size:
                break
            offset += page_size
    except Exception as exc:
        logger.debug("[hashtag_class_map] corpus hashtag scan cc=%s: %s", content_class_id, exc)
    return [h for h, _ in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]]


def _upsert_map_seeds_sync(
    client: Any,
    *,
    content_class_id: int,
    seeds: list[tuple[str, float, str]],
) -> int:
    """Upsert ``(hashtag, confidence, source)`` tuples into ``hashtag_class_map``."""
    written = 0
    now = datetime.now(UTC).isoformat()
    for h, conf, source in seeds[:_SEED_MAP_HASHTAG_LIMIT]:
        if not h:
            continue
        try:
            client.table("hashtag_class_map").upsert({
                "hashtag": h,
                "content_class_id": int(content_class_id),
                "confidence": conf,
                "source": source,
                "last_seen_at": now,
                "occurrences": 1,
            }, on_conflict="hashtag,content_class_id").execute()
            written += 1
        except Exception as exc:
            logger.debug("[hashtag_class_map] seed upsert #%s cc=%s: %s", h, content_class_id, exc)
    return written


def collect_seeds_for_class_sync(
    client: Any,
    *,
    content_class_id: int,
    signal_hashtags: list[str] | None = None,
) -> list[str]:
    """Ordered unique hashtag seeds for one content class (no DB writes)."""
    merged: list[str] = []
    seen: set[str] = set()

    def _add(tags: list[str]) -> None:
        for raw in tags:
            h = _norm_hashtag(raw)
            if h and h not in seen:
                seen.add(h)
                merged.append(h)

    legacy_ids = _legacy_niche_ids_for_class_sync(client, content_class_id)
    _add(_hashtags_from_niche_taxonomy_sync(client, legacy_ids))
    _add(_hashtags_from_niche_map_sync(client, legacy_ids, limit=_SEED_MAP_HASHTAG_LIMIT))
    _add(list(signal_hashtags or []))
    _add(_corpus_hashtags_for_class_sync(client, content_class_id, limit=15))
    _add(fetch_map_hashtags_for_class_sync(client, content_class_id, limit=_SEED_MAP_HASHTAG_LIMIT))
    return merged[:_SEED_MAP_HASHTAG_LIMIT]


def seed_class_discovery_sync(
    client: Any,
    *,
    active_only: bool = True,
    backfill_signal_hashtags: bool = True,
    content_class_ids: list[int] | None = None,
) -> dict[str, int]:
    """Seed ``hashtag_class_map`` (+ optional ``signal_hashtags``) for ingest targets.

    Sources (priority order): ``niche_taxonomy.signal_hashtags`` via junction,
    ``hashtag_niche_map``, existing target ``signal_hashtags``, corpus hashtags,
    existing class-map rows.
    """
    summary = {
        "classes_processed": 0,
        "map_rows_written": 0,
        "signal_hashtags_updated": 0,
    }
    try:
        q = client.table("content_class_ingest_targets").select(
            "content_class_id, signal_hashtags, active",
        )
        if active_only:
            q = q.eq("active", True)
        if content_class_ids:
            q = q.in_("content_class_id", content_class_ids)
        targets = q.limit(200).execute().data or []
    except Exception as exc:
        logger.error("[hashtag_class_map] seed targets fetch failed: %s", exc)
        return summary

    for t in targets:
        cc_id = int(t["content_class_id"])
        signal = list(t.get("signal_hashtags") or [])
        seeds = collect_seeds_for_class_sync(client, content_class_id=cc_id, signal_hashtags=signal)
        if not seeds:
            continue
        summary["classes_processed"] += 1
        seed_tuples: list[tuple[str, float, str]] = []
        legacy_ids = _legacy_niche_ids_for_class_sync(client, cc_id)
        tax_set = set(_hashtags_from_niche_taxonomy_sync(client, legacy_ids))
        map_set = set(_hashtags_from_niche_map_sync(client, legacy_ids, limit=_SEED_MAP_HASHTAG_LIMIT))
        for h in seeds:
            if h in tax_set:
                seed_tuples.append((h, 0.65, "niche_taxonomy_seed"))
            elif h in map_set:
                seed_tuples.append((h, 0.60, "hashtag_niche_map"))
            else:
                seed_tuples.append((h, 0.55, "class_discovery_seed"))
        summary["map_rows_written"] += _upsert_map_seeds_sync(
            client, content_class_id=cc_id, seeds=seed_tuples,
        )
        if backfill_signal_hashtags and not signal:
            try:
                client.table("content_class_ingest_targets").update({
                    "signal_hashtags": seeds[:_SEED_SIGNAL_HASHTAG_LIMIT],
                    "updated_at": datetime.now(UTC).isoformat(),
                }).eq("content_class_id", cc_id).execute()
                summary["signal_hashtags_updated"] += 1
            except Exception as exc:
                logger.warning("[hashtag_class_map] signal_hashtags backfill cc=%s: %s", cc_id, exc)

    logger.info(
        "[hashtag_class_map] seed_class_discovery — classes=%d map_rows=%d signal_backfill=%d",
        summary["classes_processed"],
        summary["map_rows_written"],
        summary["signal_hashtags_updated"],
    )
    return summary


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
    summary: dict[str, int] = {
        "yield_updated": 0,
        "pruned": 0,
        "expanded": 0,
        "seed_classes": 0,
        "seed_map_rows": 0,
        "seed_signal_backfill": 0,
    }
    seed_out = seed_class_discovery_sync(client, active_only=True, backfill_signal_hashtags=True)
    summary["seed_classes"] = seed_out["classes_processed"]
    summary["seed_map_rows"] = seed_out["map_rows_written"]
    summary["seed_signal_backfill"] = seed_out["signal_hashtags_updated"]
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
        existing = fetch_map_hashtags_for_class_sync(client, cc, limit=3)
        if existing:
            continue
        summary["expanded"] += expand_trending_seeds_sync(
            client,
            content_class_id=cc,
            signal_hashtags=t.get("signal_hashtags") or [],
        )
    return summary
