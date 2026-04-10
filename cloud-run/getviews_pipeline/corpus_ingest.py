"""Batch corpus ingest: fetch trending posts per niche → analyze → upsert to video_corpus.

Flow per niche:
  1. Fetch top posts via keyword + hashtag search (EnsembleData).
  2. Filter to posts not already in video_corpus (skip known video_ids).
  3. Analyze each post with Gemini (video or carousel path).
  4. Upsert rows to video_corpus via service-role Supabase client.
  5. After all niches complete, refresh niche_intelligence materialized view.

Designed to run as a Cloud Scheduler cron or via POST /batch/ingest.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import analyze_aweme
from getviews_pipeline.helpers import filter_recency, merge_aweme_lists
from getviews_pipeline.runtime import get_analysis_semaphore

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

BATCH_VIDEOS_PER_NICHE = int(os.environ.get("BATCH_VIDEOS_PER_NICHE", "10"))
BATCH_RECENCY_DAYS = int(os.environ.get("BATCH_RECENCY_DAYS", "30"))
BATCH_MAX_FAILURES = int(os.environ.get("BATCH_MAX_FAILURES", "3"))
BATCH_CONCURRENCY = int(os.environ.get("BATCH_CONCURRENCY", "4"))


# ── Result containers ───────────────────────────────────────────────────────────

@dataclass
class IngestResult:
    niche_id: int
    niche_name: str
    inserted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class BatchSummary:
    total_inserted: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    niches_processed: int = 0
    niche_results: list[dict[str, Any]] = field(default_factory=list)
    materialized_view_refreshed: bool = False


# ── Supabase service-role client ────────────────────────────────────────────────

def _service_client() -> Any:
    """Create a Supabase client with service_role key (bypasses RLS for batch writes)."""
    from supabase import Client, create_client  # type: ignore[import-untyped]

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set for batch ingest"
        )
    return create_client(url, key)


# ── Niche fetching ──────────────────────────────────────────────────────────────

async def _fetch_niches(client: Any) -> list[dict[str, Any]]:
    """Return all rows from niche_taxonomy."""
    result = client.table("niche_taxonomy").select("id, name_en, name_vn, signal_hashtags").execute()
    return result.data or []


async def _existing_video_ids(client: Any, niche_id: int) -> set[str]:
    """Return set of video_ids already in video_corpus for this niche."""
    result = (
        client.table("video_corpus")
        .select("video_id")
        .eq("niche_id", niche_id)
        .execute()
    )
    return {row["video_id"] for row in (result.data or [])}


# ── Post pool fetch ─────────────────────────────────────────────────────────────

async def _fetch_niche_pool(niche: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch posts for a niche via keyword search + hashtag posts, merged + deduped."""
    term = (niche.get("name_en") or "").strip()
    hashtags: list[str] = niche.get("signal_hashtags") or []

    tasks: list[Any] = [ensemble.fetch_keyword_search(term, period=BATCH_RECENCY_DAYS)]
    for ht in hashtags[:3]:
        tasks.append(ensemble.fetch_hashtag_posts(ht.lstrip("#"), cursor=0))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_awemes: list[dict[str, Any]] = []
    for res in results:
        if isinstance(res, Exception):
            logger.warning("Pool fetch error: %s", res)
            continue
        if isinstance(res, tuple):
            awemes, _ = res
        elif isinstance(res, list):
            awemes = res
        else:
            continue
        all_awemes.extend(awemes)

    merged = merge_aweme_lists(all_awemes, [])
    return filter_recency(merged, BATCH_RECENCY_DAYS)


# ── Single post ingest ──────────────────────────────────────────────────────────

def _build_corpus_row(
    aweme: dict[str, Any],
    analysis: dict[str, Any],
    niche_id: int,
) -> dict[str, Any] | None:
    """Map aweme + analysis result to a video_corpus row dict. Returns None on error."""
    if "error" in analysis or "analysis" not in analysis:
        return None

    metadata = analysis.get("metadata") or {}
    stats = metadata.get("stats") or {}
    author = metadata.get("author") or {}
    content_type = analysis.get("content_type", "video")

    video_id = str(aweme.get("aweme_id", "") or "")
    if not video_id:
        return None

    handle = (
        author.get("username")
        or str(aweme.get("author", {}).get("unique_id", "") or "")
        or "unknown"
    )

    tiktok_url = (
        metadata.get("tiktok_url")
        or f"https://www.tiktok.com/@{handle}/video/{video_id}"
    )

    # Thumbnail: first CDN URL from display cover if available
    video_obj = aweme.get("video") or {}
    cover = video_obj.get("origin_cover") or video_obj.get("cover") or {}
    cover_urls: list[str] = cover.get("url_list") or []
    thumbnail_url = cover_urls[0] if cover_urls else None

    # Video play URL (first H264 URL)
    video_urls = ensemble.extract_video_urls(aweme)
    video_url = video_urls[0] if video_urls else None

    return {
        "video_id": video_id,
        "content_type": content_type,
        "niche_id": niche_id,
        "creator_handle": handle,
        "tiktok_url": tiktok_url,
        "thumbnail_url": thumbnail_url,
        "video_url": video_url,
        "frame_urls": [],
        "analysis_json": analysis.get("analysis", {}),
        "views": int(stats.get("views") or 0),
        "likes": int(stats.get("likes") or 0),
        "comments": int(stats.get("comments") or 0),
        "shares": int(stats.get("shares") or 0),
        "engagement_rate": float(analysis.get("engagement_rate") or metadata.get("engagement_rate") or 0),
    }


# ── Per-niche ingest ─────────────────────────────────────────────────────────────

async def ingest_niche(
    niche: dict[str, Any],
    client: Any,
) -> IngestResult:
    niche_id: int = niche["id"]
    niche_name: str = niche.get("name_en") or niche.get("name_vn") or str(niche_id)
    result = IngestResult(niche_id=niche_id, niche_name=niche_name)

    logger.info("[corpus] niche=%s id=%d — fetching pool", niche_name, niche_id)

    try:
        pool = await _fetch_niche_pool(niche)
    except Exception as exc:
        logger.error("[corpus] niche=%s pool fetch failed: %s", niche_name, exc)
        result.errors.append(f"pool_fetch: {exc}")
        result.failed += 1
        return result

    existing_ids = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _existing_video_ids_sync(client, niche_id)
    )

    # Select top N by engagement rate, exclude already-indexed
    candidates = [
        a for a in pool
        if str(a.get("aweme_id", "") or "") not in existing_ids
    ]
    # Sort by engagement rate desc
    candidates.sort(
        key=lambda a: float(a.get("statistics", {}).get("digg_count", 0) or 0),
        reverse=True,
    )
    candidates = candidates[:BATCH_VIDEOS_PER_NICHE]

    if not candidates:
        logger.info("[corpus] niche=%s — all posts already indexed, skipping", niche_name)
        return result

    logger.info("[corpus] niche=%s — analyzing %d candidates", niche_name, len(candidates))

    sem = get_analysis_semaphore()
    fa: dict[str, Any] = {}

    async def _analyze_one(aweme: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(aweme, include_diagnosis=False, full_analyses=fa)

    analyses = await asyncio.gather(*[_analyze_one(a) for a in candidates], return_exceptions=True)

    rows: list[dict[str, Any]] = []
    for aweme, analysis in zip(candidates, analyses):
        if isinstance(analysis, Exception):
            logger.warning("[corpus] analyze error: %s", analysis)
            result.failed += 1
            result.errors.append(str(analysis))
            continue
        row = _build_corpus_row(aweme, analysis, niche_id)
        if row is None:
            result.skipped += 1
        else:
            rows.append(row)

    if rows:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: _upsert_rows_sync(client, rows)
            )
            result.inserted += len(rows)
            logger.info("[corpus] niche=%s — upserted %d rows", niche_name, len(rows))
        except Exception as exc:
            logger.error("[corpus] niche=%s upsert failed: %s", niche_name, exc)
            result.failed += len(rows)
            result.errors.append(f"upsert: {exc}")

    return result


def _existing_video_ids_sync(client: Any, niche_id: int) -> set[str]:
    result = (
        client.table("video_corpus")
        .select("video_id")
        .eq("niche_id", niche_id)
        .execute()
    )
    return {row["video_id"] for row in (result.data or [])}


def _upsert_rows_sync(client: Any, rows: list[dict[str, Any]]) -> None:
    client.table("video_corpus").upsert(rows, on_conflict="video_id").execute()


# ── Materialized view refresh ────────────────────────────────────────────────────

def _refresh_niche_intelligence_sync(client: Any) -> None:
    """Refresh niche_intelligence materialized view via RPC."""
    client.rpc("refresh_niche_intelligence", {}).execute()


async def _refresh_niche_intelligence(client: Any) -> bool:
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: _refresh_niche_intelligence_sync(client)
        )
        logger.info("[corpus] niche_intelligence materialized view refreshed")
        return True
    except Exception as exc:
        logger.error("[corpus] materialized view refresh failed: %s", exc)
        return False


# ── Main batch entry point ───────────────────────────────────────────────────────

async def run_batch_ingest(
    niche_ids: list[int] | None = None,
) -> BatchSummary:
    """Run full batch ingest. Optionally restrict to specific niche_ids.

    Args:
        niche_ids: If provided, only ingest these niche IDs. Otherwise all niches.

    Returns:
        BatchSummary with per-niche counts and materialized view status.
    """
    summary = BatchSummary()
    client = _service_client()

    niches: list[dict[str, Any]] = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _fetch_niches_sync(client)
    )

    if niche_ids:
        niches = [n for n in niches if n["id"] in niche_ids]

    if not niches:
        logger.warning("[corpus] No niches to process")
        return summary

    logger.info("[corpus] Starting batch ingest for %d niches", len(niches))

    # Process niches in batches of BATCH_CONCURRENCY to avoid overwhelming APIs
    for i in range(0, len(niches), BATCH_CONCURRENCY):
        batch = niches[i : i + BATCH_CONCURRENCY]
        results = await asyncio.gather(
            *[ingest_niche(n, client) for n in batch],
            return_exceptions=True,
        )
        for res in results:
            if isinstance(res, Exception):
                logger.error("[corpus] niche ingest raised: %s", res)
                summary.total_failed += 1
                continue
            summary.total_inserted += res.inserted
            summary.total_skipped += res.skipped
            summary.total_failed += res.failed
            summary.niches_processed += 1
            summary.niche_results.append({
                "niche_id": res.niche_id,
                "niche_name": res.niche_name,
                "inserted": res.inserted,
                "skipped": res.skipped,
                "failed": res.failed,
                "errors": res.errors,
            })

    # Refresh materialized view once all niches are done
    summary.materialized_view_refreshed = await _refresh_niche_intelligence(client)

    logger.info(
        "[corpus] Batch complete — inserted=%d skipped=%d failed=%d niches=%d mv_refreshed=%s",
        summary.total_inserted,
        summary.total_skipped,
        summary.total_failed,
        summary.niches_processed,
        summary.materialized_view_refreshed,
    )
    return summary


def _fetch_niches_sync(client: Any) -> list[dict[str, Any]]:
    result = (
        client.table("niche_taxonomy")
        .select("id, name_en, name_vn, signal_hashtags")
        .execute()
    )
    return result.data or []
