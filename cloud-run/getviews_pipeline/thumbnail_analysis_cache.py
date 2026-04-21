"""Cache layer for thumbnail_analysis.

Keeps Supabase imports out of the pure Gemini wrapper. Callers ask for
`resolve_thumbnail_analysis(video_id)` and get back a scored dict ready to
forward in structured_output.

Flow:
    1. SELECT thumbnail_analysis + fetched_at + frame_urls FROM video_corpus.
    2. Return cached dict if fresh (< CACHE_TTL_DAYS).
    3. Else, pick frame_urls[0] (t=0 extracted in ingest), run analyze_thumbnail,
       UPDATE + return.
    4. Any failure → None. Never raises to the caller.

For videos NOT in the corpus (user-submitted + unindexed), we have no
pre-extracted frame URL — return None so the frontend hides the tile.
A later PR can wire on-demand ffmpeg extraction; for now Phase 1 serves
only corpus-hit videos, which is the common path (creators analyse their
own published videos, which are indexed on ingest).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = 30


def _is_fresh(fetched_at: str | None, ttl_days: int = CACHE_TTL_DAYS) -> bool:
    if not fetched_at:
        return False
    try:
        dt = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc) - dt <= timedelta(days=ttl_days)


def _read_cached_sync(
    client: Any, video_id: str,
) -> tuple[dict[str, Any] | None, bool, str | None]:
    """Return (cached_radar_or_None, is_fresh, frame_url_or_None)."""
    try:
        res = (
            client.table("video_corpus")
            .select(
                "thumbnail_analysis, thumbnail_analysis_fetched_at, frame_urls",
            )
            .eq("video_id", video_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None, False, None
        row = rows[0]
        cached = row.get("thumbnail_analysis")
        fetched_at = row.get("thumbnail_analysis_fetched_at")
        frame_urls = row.get("frame_urls") or []
        frame_url = str(frame_urls[0]) if frame_urls else None
        if not isinstance(cached, dict) or not cached:
            return None, False, frame_url
        return cached, _is_fresh(fetched_at), frame_url
    except Exception as exc:
        logger.warning("[thumbnail_cache] read failed for %s: %s", video_id, exc)
        return None, False, None


def _write_cached_sync(video_id: str, payload: dict[str, Any]) -> None:
    """Persist thumbnail cache using service_role — anon cannot UPDATE video_corpus."""
    try:
        from getviews_pipeline.supabase_client import get_service_client

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        get_service_client().table("video_corpus").update(
            {
                "thumbnail_analysis": payload,
                "thumbnail_analysis_fetched_at": now_iso,
            }
        ).eq("video_id", video_id).execute()
    except Exception as exc:
        logger.warning("[thumbnail_cache] write failed for %s: %s", video_id, exc)


async def resolve_thumbnail_analysis(video_id: str) -> dict[str, Any] | None:
    """Return a thumbnail_analysis dict for `video_id`, using cache when possible.

    Returns None when the video isn't in the corpus, has no extracted frames,
    or the Gemini call fails. The caller treats None as "no thumbnail tile
    available" — rendering hides gracefully.
    """
    vid = str(video_id or "").strip()
    if not vid:
        return None

    from getviews_pipeline.corpus_context import _anon_client
    from getviews_pipeline.runtime import run_sync
    from getviews_pipeline.thumbnail_analysis import analyze_thumbnail

    try:
        client = _anon_client()
    except Exception as exc:
        logger.warning("[thumbnail_cache] Supabase client unavailable: %s", exc)
        return None

    cached, fresh, frame_url = await run_sync(_read_cached_sync, client, vid)
    if cached and fresh:
        logger.info("[thumbnail_cache] cache hit (fresh) for %s", vid)
        return cached
    if not frame_url:
        logger.info(
            "[thumbnail_cache] no frame_url for %s — skipping thumbnail pass", vid,
        )
        return None
    if cached:
        logger.info(
            "[thumbnail_cache] cache hit (stale) for %s — refetching", vid,
        )

    payload = await run_sync(analyze_thumbnail, frame_url)
    if not payload:
        return None

    try:
        await run_sync(_write_cached_sync, vid, payload)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("[thumbnail_cache] post-fetch write failed: %s", exc)

    return payload


__all__ = ["CACHE_TTL_DAYS", "resolve_thumbnail_analysis"]
