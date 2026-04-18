"""Cache layer for comment_radar.

Keeps Supabase + EnsembleData imports out of the pure scorer (comment_radar.py
stays unit-testable). Callers request `resolve_comment_radar(video_id)` and
get back the already-scored dict ready to forward to the client.

Flow:
    1. SELECT comment_radar, comment_radar_fetched_at FROM video_corpus
    2. If cached + fresh (< CACHE_TTL_DAYS) → return cached dict.
    3. Else → fetch_comments_for_video → score_comments → UPDATE + return.
    4. Any failure → None. Never raises to the caller.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = 7


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


def _write_cached_sync(client: Any, video_id: str, radar: dict[str, Any]) -> None:
    try:
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        client.table("video_corpus").update(
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

    # Cache read first.
    if client is not None:
        cached, fresh = await run_sync(_read_cached_sync, client, vid)
        if cached and fresh:
            logger.info("[comment_radar_cache] cache hit (fresh) for %s", vid)
            return cached
        if cached:
            logger.info(
                "[comment_radar_cache] cache hit (stale) for %s — refetching", vid,
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

    # Write-back — best effort, never blocks.
    if client is not None:
        try:
            await run_sync(_write_cached_sync, client, vid, radar_dict)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("[comment_radar_cache] post-fetch write failed: %s", exc)

    return radar_dict


__all__ = ["CACHE_TTL_DAYS", "resolve_comment_radar"]
