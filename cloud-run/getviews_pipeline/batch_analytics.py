"""P1-7: Breakout multiplier computation — weekly batch analytics.

Three-pass computation:
  Pass 1 — Creator velocity:
    For each (creator_handle, niche_id) pair in video_corpus:
      avg_views = AVG(views) over all corpus videos for that creator
      video_count = COUNT(*)
    Upsert into creator_velocity (avg_views, video_count, computed_at).

  Pass 2 — Breakout multiplier:
    For each video in video_corpus:
      breakout_multiplier = video.views / creator_velocity.avg_views
    Update video_corpus.breakout_multiplier WHERE creator_velocity row exists.

  Pass 3 — View velocity (D.1.5):
    For each (creator_handle, niche_id), compare recent-30d mean views vs
    prior-30d mean views (both windowed on video_corpus.created_at — the
    TikTok post timestamp, not indexed_at). Needs ≥ 2 videos in each
    window; else leave the column NULL so kol_browse falls back to the
    avg-views proxy.

Designed to run weekly (Sunday night) after nightly corpus ingest completes.
Safe to run multiple times — all operations are idempotent (upsert / update).
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service-role Supabase client
# ---------------------------------------------------------------------------

def _service_client() -> Any:
    from getviews_pipeline.supabase_client import get_service_client

    return get_service_client()


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class AnalyticsResult:
    creators_updated: int = 0
    videos_updated: int = 0
    view_velocity_updated: int = 0
    errors: list[str] = field(default_factory=list)


# D.1.5 — view-velocity window bounds. The UI renders the fraction as a
# signed percentage; the clip prevents a 1-view prior window from producing
# a 1000× "growth" spike that would mislead the TĂNG 30D column.
_VIEW_VELOCITY_WINDOW_DAYS = 30
_VIEW_VELOCITY_MIN_VIDEOS_PER_WINDOW = 2
_VIEW_VELOCITY_CLIP_MAX = 2.0
_VIEW_VELOCITY_CLIP_MIN = -0.99


# ---------------------------------------------------------------------------
# Pass 1 — Creator velocity
# ---------------------------------------------------------------------------

_VELOCITY_WINDOW_DAYS = 180
"""Rolling window for creator velocity — uses the most recent 180 days of corpus data.

180 days covers seasonal patterns without being distorted by viral outliers from
18+ months ago that no longer reflect a creator's current baseline.
"""


def _compute_creator_velocity_sync(client: Any) -> list[dict[str, Any]]:
    """Aggregate avg_views + video_count per (creator_handle, niche_id) from corpus.

    Performs Python-side aggregation via SELECT on video_corpus within a rolling
    180-day window. This prevents unbounded full-table scans as the corpus grows
    and produces more accurate baselines by excluding stale historical outliers.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=_VELOCITY_WINDOW_DAYS)).isoformat()
    rows = (
        client.table("video_corpus")
        .select("creator_handle, niche_id, views")
        .gt("views", 0)
        .gte("indexed_at", since)
        .execute()
    )
    data = rows.data or []

    # Group by (creator_handle, niche_id)
    groups: dict[tuple[str, int], list[int]] = {}
    for row in data:
        key = (row["creator_handle"], row["niche_id"])
        groups.setdefault(key, []).append(row["views"])

    # Compute aggregates
    velocities = []
    for (handle, niche_id), view_list in groups.items():
        if len(view_list) < 2:
            # Need at least 2 videos to compute a meaningful average
            continue
        avg = sum(view_list) / len(view_list)
        velocities.append({
            "creator_handle": handle,
            "niche_id": niche_id,
            "avg_views": avg,
            "video_count": len(view_list),
        })
    return velocities


def _upsert_creator_velocity_sync(client: Any, velocities: list[dict[str, Any]]) -> int:
    """Upsert creator_velocity rows. Returns count of upserted rows."""
    if not velocities:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "creator_handle": v["creator_handle"],
            "niche_id": v["niche_id"],
            "avg_views": v["avg_views"],
            "video_count": v["video_count"],
            "computed_at": now,
        }
        for v in velocities
    ]

    # Upsert in batches of 200 to avoid request size limits
    batch_size = 200
    updated = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.table("creator_velocity").upsert(
            batch,
            on_conflict="creator_handle,niche_id",
        ).execute()
        updated += len(batch)

    return updated


# ---------------------------------------------------------------------------
# Pass 2 — Breakout multiplier
# ---------------------------------------------------------------------------

def _compute_breakout_multipliers_sync(client: Any) -> int:
    """Update video_corpus.breakout_multiplier for all videos with a known creator avg.

    Strategy:
      1. Fetch all creator_velocity rows (avg_views).
      2. For each creator, fetch their corpus videos within the same rolling window.
      3. Compute breakout = views / avg_views; update video_corpus.

    Uses batched updates to avoid hitting Supabase row limits.
    Returns total count of videos updated.
    """
    # Fetch creator velocities (only those with meaningful avg)
    # Include niche_id so the map is keyed per (creator, niche) — a creator active
    # in multiple niches has a different avg_views per niche.
    vel_result = (
        client.table("creator_velocity")
        .select("creator_handle, niche_id, avg_views")
        .gt("avg_views", 0)
        .gt("video_count", 1)
        .execute()
    )
    velocity_map: dict[tuple[str, int], float] = {
        (row["creator_handle"], row["niche_id"]): row["avg_views"]
        for row in (vel_result.data or [])
    }

    if not velocity_map:
        logger.info("[analytics] No creator velocity data — skipping breakout computation")
        return 0

    since = (datetime.now(timezone.utc) - timedelta(days=_VELOCITY_WINDOW_DAYS)).isoformat()

    # Fetch corpus videos for creators we have velocity for (with niche_id for correct lookup)
    handles = list({handle for handle, _ in velocity_map})
    total_updated = 0

    # Process in chunks to avoid URL length limits
    chunk_size = 50
    for i in range(0, len(handles), chunk_size):
        chunk = handles[i : i + chunk_size]
        vid_result = (
            client.table("video_corpus")
            .select("id, creator_handle, niche_id, views")
            .in_("creator_handle", chunk)
            .gt("views", 0)
            .gte("indexed_at", since)
            .execute()
        )
        videos = vid_result.data or []

        # Update breakout_multiplier for each video using the per-niche creator average
        for video in videos:
            avg = velocity_map.get((video["creator_handle"], video["niche_id"]))
            if not avg or avg <= 0:
                continue
            breakout = round(video["views"] / avg, 2)
            try:
                client.table("video_corpus").update(
                    {"breakout_multiplier": breakout}
                ).eq("id", video["id"]).execute()
                total_updated += 1
            except Exception as exc:
                logger.warning(
                    "[analytics] Failed to update breakout for video %s: %s",
                    video["id"], exc,
                )

    return total_updated


# ---------------------------------------------------------------------------
# Pass 3 — View velocity (30d recent vs prior 30d, D.1.5)
# ---------------------------------------------------------------------------


def _parse_ts(raw: Any) -> datetime | None:
    """Accept ISO strings / datetimes — returns UTC-aware datetime or None."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    try:
        s = str(raw).strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _compute_view_velocity_sync(client: Any) -> list[dict[str, Any]]:
    """Per-creator recent-30d mean views vs prior-30d mean views.

    Uses ``video_corpus.created_at`` (the TikTok post timestamp) — NOT
    ``indexed_at`` — so late-ingested older videos don't pollute the
    recent window. Requires ``>= _VIEW_VELOCITY_MIN_VIDEOS_PER_WINDOW``
    videos in each window; others are skipped (column stays NULL).
    """
    now = datetime.now(timezone.utc)
    t_recent_start = now - timedelta(days=_VIEW_VELOCITY_WINDOW_DAYS)
    t_prior_start = now - timedelta(days=2 * _VIEW_VELOCITY_WINDOW_DAYS)

    # Pull 60 days of corpus rows in a single select — cheaper than two.
    rows = (
        client.table("video_corpus")
        .select("creator_handle, niche_id, views, created_at")
        .gt("views", 0)
        .gte("created_at", t_prior_start.isoformat())
        .execute()
    )
    data = rows.data or []

    # group by (handle, niche) → (recent_views[], prior_views[])
    buckets: dict[tuple[str, int], tuple[list[int], list[int]]] = {}
    for row in data:
        handle = row.get("creator_handle")
        niche_id = row.get("niche_id")
        views = row.get("views")
        dt = _parse_ts(row.get("created_at"))
        if handle is None or niche_id is None or views is None or dt is None:
            continue
        key = (str(handle), int(niche_id))
        slot = buckets.setdefault(key, ([], []))
        v = int(views)
        if dt >= t_recent_start:
            slot[0].append(v)
        elif dt >= t_prior_start:
            slot[1].append(v)

    out: list[dict[str, Any]] = []
    for (handle, niche_id), (recent, prior) in buckets.items():
        if len(recent) < _VIEW_VELOCITY_MIN_VIDEOS_PER_WINDOW:
            continue
        if len(prior) < _VIEW_VELOCITY_MIN_VIDEOS_PER_WINDOW:
            continue
        recent_mean = sum(recent) / len(recent)
        prior_mean = sum(prior) / len(prior)
        if prior_mean <= 0:
            continue
        pct = (recent_mean - prior_mean) / prior_mean
        pct = _clip(pct, _VIEW_VELOCITY_CLIP_MIN, _VIEW_VELOCITY_CLIP_MAX)
        out.append(
            {
                "creator_handle": handle,
                "niche_id": niche_id,
                "view_velocity_30d_pct": round(pct, 4),
            }
        )
    return out


def _update_view_velocity_sync(client: Any, rows: list[dict[str, Any]]) -> int:
    """UPDATE creator_velocity rows with the freshly computed view velocity.

    Uses UPDATE + per-row eq filters so we only touch existing rows (a
    creator with < 2 videos in the 180d velocity window won't have a
    creator_velocity row to match — skipping those silently is correct).
    """
    if not rows:
        return 0
    now_iso = datetime.now(timezone.utc).isoformat()
    updated = 0
    for r in rows:
        try:
            (
                client.table("creator_velocity")
                .update(
                    {
                        "view_velocity_30d_pct": r["view_velocity_30d_pct"],
                        "view_velocity_computed_at": now_iso,
                    }
                )
                .eq("creator_handle", r["creator_handle"])
                .eq("niche_id", r["niche_id"])
                .execute()
            )
            updated += 1
        except Exception as exc:
            logger.warning(
                "[analytics] view_velocity update failed handle=%s niche=%s: %s",
                r["creator_handle"],
                r["niche_id"],
                exc,
            )
    return updated


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_analytics(client: Any | None = None) -> AnalyticsResult:
    """Compute creator velocity + breakout multipliers.

    Designed to run weekly after corpus ingest completes.
    Pass an existing service_role client or None to create one.

    Returns AnalyticsResult with counts and any non-fatal errors.
    """
    result = AnalyticsResult()
    loop = asyncio.get_event_loop()

    if client is None:
        try:
            client = _service_client()
        except RuntimeError as exc:
            result.errors.append(str(exc))
            return result

    try:
        logger.info("[analytics] Pass 1 — computing creator velocity...")
        velocities = await loop.run_in_executor(
            None, _compute_creator_velocity_sync, client
        )
        logger.info("[analytics] %d creator velocity rows computed", len(velocities))

        result.creators_updated = await loop.run_in_executor(
            None, _upsert_creator_velocity_sync, client, velocities
        )
        logger.info("[analytics] %d creator_velocity rows upserted", result.creators_updated)

    except Exception as exc:
        logger.error("[analytics] Pass 1 failed: %s", exc)
        result.errors.append(f"creator_velocity: {exc}")

    try:
        logger.info("[analytics] Pass 2 — computing breakout multipliers...")
        result.videos_updated = await loop.run_in_executor(
            None, _compute_breakout_multipliers_sync, client
        )
        logger.info("[analytics] %d breakout_multiplier values updated", result.videos_updated)

    except Exception as exc:
        logger.error("[analytics] Pass 2 failed: %s", exc)
        result.errors.append(f"breakout_multiplier: {exc}")

    try:
        logger.info("[analytics] Pass 3 — computing view velocity (30d)...")
        velocity_rows = await loop.run_in_executor(
            None, _compute_view_velocity_sync, client
        )
        logger.info("[analytics] %d view-velocity rows computed", len(velocity_rows))
        result.view_velocity_updated = await loop.run_in_executor(
            None, _update_view_velocity_sync, client, velocity_rows
        )
        logger.info(
            "[analytics] %d creator_velocity rows updated with view_velocity_30d_pct",
            result.view_velocity_updated,
        )
    except Exception as exc:
        logger.error("[analytics] Pass 3 failed: %s", exc)
        result.errors.append(f"view_velocity: {exc}")

    return result
