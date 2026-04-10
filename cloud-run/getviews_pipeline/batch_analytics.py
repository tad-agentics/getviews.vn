"""P1-7: Breakout multiplier computation — weekly batch analytics.

Two-pass computation:
  Pass 1 — Creator velocity:
    For each (creator_handle, niche_id) pair in video_corpus:
      avg_views = AVG(views) over all corpus videos for that creator
      video_count = COUNT(*)
    Upsert into creator_velocity (avg_views, video_count, computed_at).

  Pass 2 — Breakout multiplier:
    For each video in video_corpus:
      breakout_multiplier = video.views / creator_velocity.avg_views
    Update video_corpus.breakout_multiplier WHERE creator_velocity row exists.

Designed to run weekly (Sunday night) after nightly corpus ingest completes.
Safe to run multiple times — both operations are idempotent (upsert / update).
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service-role Supabase client
# ---------------------------------------------------------------------------

def _service_client() -> Any:
    from supabase import create_client  # type: ignore[import-untyped]

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class AnalyticsResult:
    creators_updated: int = 0
    videos_updated: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pass 1 — Creator velocity
# ---------------------------------------------------------------------------

def _compute_creator_velocity_sync(client: Any) -> list[dict[str, Any]]:
    """Aggregate avg_views + video_count per (creator_handle, niche_id) from corpus.

    Uses a direct SQL query via Supabase's postgrest RPC endpoint.
    Falls back to Python-side aggregation if RPC is unavailable.
    """
    try:
        # Try SQL aggregation via RPC (most efficient)
        result = client.rpc("compute_creator_velocity", {}).execute()
        if result.data:
            return result.data or []
    except Exception:
        pass  # RPC not available — fall through to Python aggregation

    # Python-side fallback: fetch all corpus rows and aggregate
    rows = (
        client.table("video_corpus")
        .select("creator_handle, niche_id, views")
        .gt("views", 0)
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
      2. For each creator, fetch their corpus videos.
      3. Compute breakout = views / avg_views; update video_corpus.

    Uses batched updates to avoid hitting Supabase row limits.
    Returns total count of videos updated.
    """
    # Fetch creator velocities (only those with meaningful avg)
    vel_result = (
        client.table("creator_velocity")
        .select("creator_handle, avg_views")
        .gt("avg_views", 0)
        .gt("video_count", 1)
        .execute()
    )
    velocity_map: dict[str, float] = {
        row["creator_handle"]: row["avg_views"]
        for row in (vel_result.data or [])
    }

    if not velocity_map:
        logger.info("[analytics] No creator velocity data — skipping breakout computation")
        return 0

    # Fetch corpus videos for creators we have velocity for
    handles = list(velocity_map.keys())
    total_updated = 0

    # Process in chunks to avoid URL length limits
    chunk_size = 50
    for i in range(0, len(handles), chunk_size):
        chunk = handles[i : i + chunk_size]
        vid_result = (
            client.table("video_corpus")
            .select("id, creator_handle, views")
            .in_("creator_handle", chunk)
            .gt("views", 0)
            .execute()
        )
        videos = vid_result.data or []

        # Update breakout_multiplier for each video
        for video in videos:
            avg = velocity_map.get(video["creator_handle"])
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

    return result
