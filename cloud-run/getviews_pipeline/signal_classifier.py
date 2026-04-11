"""P1-8: Signal strength classifier — grades trend signal per (niche, hook_type).

Signal grades (mirrors SignalBadge.tsx frontend values):
  confirmed / rising: 3+ creators, 100K+ total views, <7 days → "rising"
  rising (weaker):    2+ creators, positive velocity, <14 days  → "rising"
  early:              1-2 creators, <7 days, velocity unclear   → "early"
  stable:             seen before, no strong directional change → "stable"
  declining:          negative velocity in last 7 days           → "declining"

Data sources:
  video_corpus    — ground truth counts per (niche, hook_type, recency)
  hook_effectiveness — pre-aggregated avg ER + trend_direction per (niche, hook_type)
  trend_velocity  — hook_type_shifts JSONB, week-over-week changes

Output: upserted rows in signal_grades table.

Usage (from batch pipeline):
    from getviews_pipeline.signal_classifier import run_signal_grading
    result = await run_signal_grading(client)
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

SIGNAL_CONFIRMED_CREATORS = 3
SIGNAL_CONFIRMED_VIEWS = 100_000
SIGNAL_CONFIRMED_DAYS = 7

SIGNAL_RISING_CREATORS = 2
SIGNAL_RISING_DAYS = 14


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SignalGradingResult:
    grades_written: int = 0
    niches_processed: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Grade computation
# ---------------------------------------------------------------------------

def _compute_signal(
    creator_count: int,
    total_views: int,
    max_recency_days: int,
    trend_direction: str | None,
) -> str:
    """Return signal grade string from raw corpus stats.

    Applies the four-tier classification:
      confirmed rising  → "rising"
      weaker rising     → "rising"
      early signal      → "early"
      declining         → "declining"
      otherwise         → "stable"
    """
    if trend_direction == "declining":
        return "declining"

    # Confirmed rising: 3+ creators, 100K+ views, within 7 days
    if (
        creator_count >= SIGNAL_CONFIRMED_CREATORS
        and total_views >= SIGNAL_CONFIRMED_VIEWS
        and max_recency_days <= SIGNAL_CONFIRMED_DAYS
    ):
        return "rising"

    # Weaker rising: 2+ creators, within 14 days, non-declining trend
    if (
        creator_count >= SIGNAL_RISING_CREATORS
        and max_recency_days <= SIGNAL_RISING_DAYS
        and trend_direction in ("rising", None)
    ):
        return "rising"

    # Early signal: 1-2 creators, very recent
    if creator_count >= 1 and max_recency_days <= SIGNAL_CONFIRMED_DAYS:
        return "early"

    return "stable"


def _grade_niche_sync(
    client: Any,
    niche_id: int,
    week_start: date,
    today: date,
) -> list[dict[str, Any]]:
    """Compute signal grades for all hook types in a niche.

    Returns list of signal_grades rows ready for upsert.
    """
    # 1. Corpus counts per hook_type in last 14 days
    since = (today - timedelta(days=14)).isoformat()
    corpus_result = (
        client.table("video_corpus")
        .select("analysis_json, creator_handle, views, indexed_at")
        .eq("niche_id", niche_id)
        .gte("indexed_at", since)
        .execute()
    )
    corpus_rows = corpus_result.data or []

    # Aggregate per hook_type
    hook_stats: dict[str, dict[str, Any]] = {}
    for row in corpus_rows:
        analysis = row.get("analysis_json") or {}
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except Exception:
                continue

        # Extract hook_type from analysis_json (may be nested)
        hook_type = (
            analysis.get("hook_analysis", {}).get("hook_type")
            or analysis.get("hook_type")
        )
        if not hook_type:
            continue

        indexed_at_str = row.get("indexed_at", "")
        try:
            indexed_at = datetime.fromisoformat(indexed_at_str.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - indexed_at).days
        except Exception:
            days_ago = 14

        if hook_type not in hook_stats:
            hook_stats[hook_type] = {
                "creators": set(),
                "total_views": 0,
                "min_days_ago": days_ago,
                "sample_size": 0,
            }
        s = hook_stats[hook_type]
        s["creators"].add(row.get("creator_handle", ""))
        s["total_views"] += row.get("views", 0)
        s["min_days_ago"] = min(s["min_days_ago"], days_ago)
        s["sample_size"] += 1

    # 2. hook_effectiveness trend_direction as signal hint
    he_result = (
        client.table("hook_effectiveness")
        .select("hook_type, trend_direction")
        .eq("niche_id", niche_id)
        .order("computed_at", desc=True)
        .limit(50)
        .execute()
    )
    trend_dir_map: dict[str, str] = {}
    for row in (he_result.data or []):
        ht = row.get("hook_type", "")
        td = row.get("trend_direction")
        if ht and ht not in trend_dir_map:
            trend_dir_map[ht] = td or "stable"

    # 3. Build grade rows
    grade_rows = []
    week_str = week_start.isoformat()
    now_str = datetime.now(timezone.utc).isoformat()

    for hook_type, stats in hook_stats.items():
        creator_count = len(stats["creators"])
        total_views = stats["total_views"]
        min_days_ago = stats["min_days_ago"]
        sample_size = stats["sample_size"]
        trend_direction = trend_dir_map.get(hook_type)

        signal = _compute_signal(creator_count, total_views, min_days_ago, trend_direction)

        grade_rows.append({
            "niche_id": niche_id,
            "hook_type": hook_type,
            "week_start": week_str,
            "signal": signal,
            "creator_count": creator_count,
            "total_views": total_views,
            "sample_size": sample_size,
            "computed_at": now_str,
        })

    return grade_rows


def _upsert_signal_grades_sync(client: Any, grades: list[dict[str, Any]]) -> int:
    """Upsert signal_grades rows. Returns count upserted."""
    if not grades:
        return 0

    batch_size = 100
    total = 0
    for i in range(0, len(grades), batch_size):
        batch = grades[i : i + batch_size]
        client.table("signal_grades").upsert(
            batch,
            on_conflict="niche_id,hook_type,week_start",
        ).execute()
        total += len(batch)
    return total


def _fetch_niche_ids_sync(client: Any) -> list[int]:
    result = client.table("niche_taxonomy").select("id").execute()
    return [row["id"] for row in (result.data or [])]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_signal_grading(client: Any | None = None) -> SignalGradingResult:
    """Compute and store signal grades for all niches.

    Called weekly (Sunday night) after run_analytics().
    Pass an existing service_role client or None to create one.
    """
    result = SignalGradingResult()
    loop = asyncio.get_event_loop()

    if client is None:
        from getviews_pipeline.supabase_client import get_service_client
        try:
            client = get_service_client()
        except RuntimeError as exc:
            result.errors.append(str(exc))
            return result

    today = date.today()
    # week_start = most recent Sunday
    days_since_sunday = (today.weekday() + 1) % 7
    week_start = today - timedelta(days=days_since_sunday)

    try:
        niche_ids = await loop.run_in_executor(None, _fetch_niche_ids_sync, client)
    except Exception as exc:
        result.errors.append(f"fetch niches: {exc}")
        return result

    logger.info("[signal] Grading %d niches for week %s", len(niche_ids), week_start)

    all_grades: list[dict[str, Any]] = []
    for niche_id in niche_ids:
        try:
            grades = await loop.run_in_executor(
                None, _grade_niche_sync, client, niche_id, week_start, today
            )
            all_grades.extend(grades)
            result.niches_processed += 1
        except Exception as exc:
            logger.error("[signal] Failed to grade niche %d: %s", niche_id, exc)
            result.errors.append(f"niche {niche_id}: {exc}")

    try:
        result.grades_written = await loop.run_in_executor(
            None, _upsert_signal_grades_sync, client, all_grades
        )
        logger.info("[signal] %d signal_grades rows upserted", result.grades_written)
    except Exception as exc:
        logger.error("[signal] Upsert failed: %s", exc)
        result.errors.append(f"upsert: {exc}")

    return result
