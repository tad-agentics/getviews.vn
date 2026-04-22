"""Daily metadata-only refresh of ``video_corpus`` stats.

Closes the Axis 3 freshness gap (state-of-corpus.md): every row's
``views``/``likes``/``comments``/``shares``/``saves`` are stamped at
ingest and never updated. A video that went viral post-ingest is
invisible to breakout detection + lifecycle scoring.

This module re-pulls **just the engagement metrics** from EnsembleData
— no Gemini re-analyze, no scene reprocessing, no thumbnail re-fetch.
Cost is ~$0.001 per video (one ED post-multi call shared across 20
videos), so a daily 200-row refresh is well under $0.10/run.

Selection priority:
  1. ``last_refetched_at IS NULL`` first (newly-ingested rows that
     never had a re-pull yet).
  2. Among NULLs, highest ``views`` first — those are the rows whose
     trajectory matters most for breakout detection.
  3. Then rows whose ``last_refetched_at`` is older than
     ``REFRESH_STALE_DAYS`` (default 3 days), again ordered by ``views
     DESC``.
  4. Hard cap at ``REFRESH_BATCH_LIMIT`` (default 200) per run.

Stats below ``REFRESH_VIEWS_FLOOR`` (default 1000) are skipped — the
whole point is to catch breakouts, and a sub-1k video with no movement
isn't worth the EnsembleData call.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# How often a row should be refreshed. 3 days strikes the balance:
# breakouts that happen post-ingest get caught within ~72h of going
# viral, while we don't burn quota re-pulling stable rows.
REFRESH_STALE_DAYS = 3

# Cap per cron run. 200 × ~10 ED calls/sec ≈ 20s of EnsembleData time;
# well under the cron timeout. Increase as ED budget allows.
REFRESH_BATCH_LIMIT = 200

# Below this views threshold, refresh isn't worth the API call. Most
# videos under 1000 views have plateaued. Adjust if breakout detection
# starts missing genuine slow-burns.
REFRESH_VIEWS_FLOOR = 1000

# EnsembleData post-multi accepts up to 20 IDs per call.
REFRESH_CHUNK = 20


def _select_refresh_candidates(
    client: Any,
    *,
    stale_days: int = REFRESH_STALE_DAYS,
    views_floor: int = REFRESH_VIEWS_FLOOR,
    limit: int = REFRESH_BATCH_LIMIT,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Select ``video_id``/``niche_id``/``views`` for the next refresh batch.

    NULL ``last_refetched_at`` rows come first (priority bucket); among
    NULLs and within the stale-by-age bucket, ordered by ``views DESC``.
    """
    now = now or datetime.now(UTC)
    stale_cutoff = (now - timedelta(days=stale_days)).isoformat()

    # PostgREST doesn't support OR + complex ordering inline, so fetch
    # NULL bucket first, then stale-bucket, both filtered by views.
    null_bucket = (
        client.table("video_corpus")
        .select("video_id, niche_id, views, likes, comments, shares, saves")
        .is_("last_refetched_at", None)
        .gte("views", views_floor)
        .order("views", desc=True)
        .limit(limit)
        .execute()
    )
    rows: list[dict[str, Any]] = list(null_bucket.data or [])

    if len(rows) >= limit:
        return rows[:limit]

    remaining = limit - len(rows)
    stale_bucket = (
        client.table("video_corpus")
        .select("video_id, niche_id, views, likes, comments, shares, saves")
        .lt("last_refetched_at", stale_cutoff)
        .gte("views", views_floor)
        .order("views", desc=True)
        .limit(remaining)
        .execute()
    )
    rows.extend(stale_bucket.data or [])
    return rows[:limit]


def _extract_fresh_metrics(post: dict[str, Any]) -> dict[str, int] | None:
    """Pull stats out of an EnsembleData post-multi response item.

    Returns None when the post is missing/private/deleted (no usable
    stats) — caller skips the UPDATE for that ID.
    """
    detail = post.get("aweme_detail") or post
    stats = detail.get("statistics") or {}

    play_count = _to_int(stats.get("play_count") or stats.get("playCount"))
    if play_count is None or play_count <= 0:
        # No views = ED returned an empty / deleted shell. Skip.
        return None

    return {
        "views":    play_count,
        "likes":    _to_int(stats.get("digg_count") or stats.get("diggCount")) or 0,
        "comments": _to_int(stats.get("comment_count") or stats.get("commentCount")) or 0,
        "shares":   _to_int(stats.get("share_count") or stats.get("shareCount")) or 0,
        "saves":    _to_int(stats.get("collect_count") or stats.get("collectCount")) or 0,
    }


def _to_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _engagement_rate(views: int, likes: int, comments: int, shares: int) -> float:
    """Mirror the same formula corpus_ingest uses so refreshed rows
    stay comparable to ingest-time rows. (likes + comments + shares) / views."""
    if views <= 0:
        return 0.0
    return round((likes + comments + shares) / views, 6)


def _save_rate(views: int, saves: int) -> float:
    if views <= 0:
        return 0.0
    return round(saves / views, 6)


async def run_corpus_refresh(
    *,
    client: Any | None = None,
    limit: int = REFRESH_BATCH_LIMIT,
    stale_days: int = REFRESH_STALE_DAYS,
    views_floor: int = REFRESH_VIEWS_FLOOR,
) -> dict[str, Any]:
    """Refresh metadata stats for the highest-priority video_corpus rows.

    Returns ``{candidates, refreshed, skipped, missing, errors,
    delta_views_total}`` — ``delta_views_total`` is the cumulative
    view-count growth across refreshed rows, useful for tracking
    "did this run actually catch any movement?"
    """
    from getviews_pipeline import ensemble
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    now = datetime.now(UTC)
    candidates = _select_refresh_candidates(
        client,
        stale_days=stale_days,
        views_floor=views_floor,
        limit=limit,
        now=now,
    )

    if not candidates:
        logger.info("[corpus_refresh] no candidates")
        return {
            "candidates": 0,
            "refreshed": 0,
            "skipped": 0,
            "missing": 0,
            "errors": 0,
            "delta_views_total": 0,
        }

    # Snapshot prior views per ID so we can report delta after.
    prior_views: dict[str, int] = {
        str(r["video_id"]): int(r.get("views") or 0) for r in candidates
    }

    refreshed = skipped = missing = errors = 0
    delta_views_total = 0

    ids: list[str] = [str(r["video_id"]) for r in candidates]
    for chunk in _chunked(ids, REFRESH_CHUNK):
        try:
            posts = await ensemble.fetch_post_multi_info(chunk)
        except Exception as exc:
            logger.warning(
                "[corpus_refresh] fetch_post_multi_info failed for %d IDs: %s",
                len(chunk), exc,
            )
            errors += len(chunk)
            continue

        fresh_by_id: dict[str, dict[str, int]] = {}
        for post in posts:
            detail = post.get("aweme_detail") or post
            vid = str(detail.get("aweme_id") or "")
            if not vid:
                continue
            metrics = _extract_fresh_metrics(post)
            if metrics is not None:
                fresh_by_id[vid] = metrics

        for vid in chunk:
            metrics = fresh_by_id.get(vid)
            if metrics is None:
                # ED either didn't return the post or it came back as a
                # deleted/private shell with zero stats. Either way, no
                # update — count once, move on.
                missing += 1
                continue

            views = metrics["views"]
            likes = metrics["likes"]
            comments = metrics["comments"]
            shares = metrics["shares"]
            saves = metrics["saves"]

            payload = {
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "saves": saves,
                "engagement_rate": _engagement_rate(views, likes, comments, shares),
                "save_rate": _save_rate(views, saves),
                "last_refetched_at": now.isoformat(),
            }
            try:
                client.table("video_corpus").update(payload).eq("video_id", vid).execute()
                refreshed += 1
                delta_views_total += max(0, views - prior_views.get(vid, 0))
            except Exception as exc:
                logger.warning(
                    "[corpus_refresh] update failed for %s: %s", vid, exc,
                )
                errors += 1

    skipped = len(candidates) - refreshed - missing - errors
    logger.info(
        "[corpus_refresh] candidates=%d refreshed=%d missing=%d "
        "errors=%d skipped=%d delta_views_total=%d",
        len(candidates), refreshed, missing, errors, skipped, delta_views_total,
    )
    return {
        "candidates": len(candidates),
        "refreshed": refreshed,
        "skipped": skipped,
        "missing": missing,
        "errors": errors,
        "delta_views_total": delta_views_total,
    }


def _chunked(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]
