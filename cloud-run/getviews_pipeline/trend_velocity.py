"""Trend velocity computation — Layer 3 of the §12 intelligence layer.

Computes week-over-week hook shifts for each niche from video_corpus and
upserts one row per (niche_id, week_start) into trend_velocity.

Flow:
  1. For each niche, query video_corpus for videos from the last 14 days.
  2. Bucket videos into this_week (last 7 days) and prev_week (7–14 days ago).
  3. Per hook_type: compute count delta % and engagement rate delta %.
  4. Aggregate new_hashtags from video_corpus.hashtags (top-level column) across all videos.
  5. Upsert trend_velocity (niche_id, week_start, hook_type_shifts, new_hashtags).

Called from corpus_ingest._run_weekly_analytics() every Sunday alongside
batch_analytics and signal_classifier.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class TrendVelocityResult:
    niches_processed: int = 0
    rows_upserted: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _compute_trend_velocity_for_niche_sync(
    client: Any,
    niche_id: int,
    niche_name: str,
    today: date,
) -> dict[str, Any] | None:
    """Compute hook_type_shifts and new_hashtags for one niche.

    Returns a trend_velocity row dict ready for upsert, or None on failure.
    """
    # Align to Sunday: weekday() 0=Mon … 6=Sun
    # Sunday → subtract 0; Mon → subtract 1; … Sat → subtract 6
    days_since_sunday = (today.weekday() + 1) % 7
    week_start = today - timedelta(days=days_since_sunday)

    cutoff_14d = today - timedelta(days=14)

    try:
        result = (
            client.table("video_corpus")
            .select("engagement_rate, indexed_at, analysis_json, hashtags")
            .eq("niche_id", niche_id)
            .gte("indexed_at", cutoff_14d.isoformat())
            .execute()
        )
    except Exception as exc:
        logger.error("[tv] niche=%s fetch failed: %s", niche_name, exc)
        return None

    rows = result.data or []
    if not rows:
        logger.info("[tv] niche=%s — no rows in last 14 days, skipping", niche_name)
        return None

    # Bucket by week
    cutoff_7d = today - timedelta(days=7)

    # hook_type → {this_week_count, prev_week_count, this_week_er_sum, prev_week_er_sum}
    hook_stats: dict[str, dict[str, float]] = defaultdict(lambda: {
        "tw_count": 0.0,
        "pw_count": 0.0,
        "tw_er_sum": 0.0,
        "pw_er_sum": 0.0,
    })

    hashtag_set: set[str] = set()

    for row in rows:
        aj = row.get("analysis_json") or {}
        # hook_type is nested under hook_analysis in analysis_json (written by corpus_ingest).
        # Fall back to top-level key for older rows written before the nested schema.
        hook = str(
            (aj.get("hook_analysis") or {}).get("hook_type")
            or aj.get("hook_type")
            or "unknown"
        ).strip()
        er = float(row.get("engagement_rate") or 0.0)
        indexed = str(row.get("indexed_at") or "")
        is_this_week = indexed >= cutoff_7d.isoformat()

        s = hook_stats[hook]
        if is_this_week:
            s["tw_count"] += 1
            s["tw_er_sum"] += er
        else:
            s["pw_count"] += 1
            s["pw_er_sum"] += er

        # Hashtags are stored as a top-level column in video_corpus, not inside analysis_json.
        for tag in (row.get("hashtags") or []):
            if isinstance(tag, str) and tag:
                hashtag_set.add(tag.lstrip("#").lower())

    # Build hook_type_shifts
    hook_type_shifts: dict[str, Any] = {}
    for hook, s in hook_stats.items():
        tw = s["tw_count"]
        pw = s["pw_count"]
        tw_er = s["tw_er_sum"] / tw if tw > 0 else 0.0
        pw_er = s["pw_er_sum"] / pw if pw > 0 else 0.0

        if pw > 0:
            count_delta_pct = round((tw - pw) / pw * 100, 1)
        elif tw > 0:
            count_delta_pct = 100.0  # new this week
        else:
            count_delta_pct = 0.0

        if pw_er > 0:
            er_delta_pct = round((tw_er - pw_er) / pw_er * 100, 1)
        else:
            er_delta_pct = 0.0

        # Derive signal label consistent with signal_classifier
        if count_delta_pct >= 50 and tw >= 3:
            signal = "rising"
        elif count_delta_pct >= 10 and tw >= 2:
            signal = "early"
        elif count_delta_pct <= -30:
            signal = "declining"
        else:
            signal = "stable"

        hook_type_shifts[hook] = {
            "count_delta_pct": count_delta_pct,
            "er_delta_pct": er_delta_pct,
            "this_week_count": int(tw),
            "prev_week_count": int(pw),
            "signal": signal,
        }

    return {
        "niche_id": niche_id,
        "week_start": week_start.isoformat(),
        "hook_type_shifts": hook_type_shifts,
        "format_changes": {},      # populated by format_lifecycle once that's built
        "new_hashtags": sorted(hashtag_set)[:50],  # cap at 50 tags
        "sound_trends": {},        # Layer 7 (Sound Radar) — deferred
    }


def _upsert_trend_velocity_sync(client: Any, rows: list[dict[str, Any]]) -> int:
    """Upsert trend_velocity rows. Returns count of rows upserted."""
    if not rows:
        return 0
    client.table("trend_velocity").upsert(
        rows,
        on_conflict="niche_id,week_start",
    ).execute()
    return len(rows)


# ---------------------------------------------------------------------------
# Async entry point
# ---------------------------------------------------------------------------

async def run_trend_velocity(client: Any | None = None) -> TrendVelocityResult:
    """Compute and upsert trend_velocity for all niches.

    Designed to be called from corpus_ingest._run_weekly_analytics() every Sunday.
    Never raises — all errors are captured in result.errors.

    Args:
        client: Optional pre-built Supabase service client. If None, one is created.
    """
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    result = TrendVelocityResult()
    today = date.today()
    loop = asyncio.get_event_loop()

    # Fetch all niches
    try:
        niches_resp = await loop.run_in_executor(
            None,
            lambda: client.table("niche_taxonomy").select("id, name_en").execute(),
        )
        niches: list[dict[str, Any]] = niches_resp.data or []
    except Exception as exc:
        result.errors.append(f"fetch niches: {exc}")
        return result

    if not niches:
        logger.warning("[tv] No niches found — skipping trend_velocity computation")
        return result

    logger.info("[tv] Computing trend_velocity for %d niches (week_start based on %s)", len(niches), today)

    # Compute one row per niche (sync, in executor)
    rows_to_upsert: list[dict[str, Any]] = []
    for niche in niches:
        niche_id = niche["id"]
        niche_name = niche.get("name_en", str(niche_id))
        try:
            row = await loop.run_in_executor(
                None,
                lambda nid=niche_id, nn=niche_name: _compute_trend_velocity_for_niche_sync(
                    client, nid, nn, today
                ),
            )
            if row is not None:
                rows_to_upsert.append(row)
                result.niches_processed += 1
                logger.debug("[tv] niche=%s — %d hook shifts computed", niche_name, len(row["hook_type_shifts"]))
        except Exception as exc:
            msg = f"niche={niche_name}: {exc}"
            logger.error("[tv] %s", msg)
            result.errors.append(msg)

    # Upsert all rows in one call
    if rows_to_upsert:
        try:
            result.rows_upserted = await loop.run_in_executor(
                None,
                lambda: _upsert_trend_velocity_sync(client, rows_to_upsert),
            )
            logger.info(
                "[tv] Upserted %d trend_velocity rows for %d niches",
                result.rows_upserted,
                result.niches_processed,
            )
        except Exception as exc:
            result.errors.append(f"upsert: {exc}")
            logger.error("[tv] Upsert failed: %s", exc)

    return result
