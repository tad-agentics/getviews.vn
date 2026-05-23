"""§4.7 M4 — stats_history time-series + distribution_shape detection.

Ingest writes a ``t0`` snapshot; this module appends ``t6h`` / ``t24h``
via EnsembleData and derives ``spike_then_flat`` when criteria match.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

REFETCH_PHASES = ("t6h", "t24h")
REFETCH_OFFSETS_H = {"t6h": 6, "t24h": 24}
REFETCH_BATCH_LIMIT = 80
REFETCH_CHUNK = 20
REFETCH_CHUNK_COOLDOWN_S = 0.3
REFETCH_RETRY_BACKOFF_S = 1.0
REFETCH_LOOKBACK_DAYS = 3


@dataclass
class StatsHistoryRefetchResult:
    candidates: int = 0
    refreshed: int = 0
    missing: int = 0
    errors: int = 0
    shapes_set: int = 0


def make_stats_snapshot(
    *,
    views: int,
    likes: int,
    comments: int,
    shares: int,
    phase: str,
    at: datetime | None = None,
) -> dict[str, Any]:
    ts = at or datetime.now(UTC)
    return {
        "at": ts.isoformat(),
        "phase": phase,
        "views": int(views),
        "likes": int(likes),
        "comments": int(comments),
        "shares": int(shares),
    }


def history_phases(history: Any) -> set[str]:
    if not isinstance(history, list):
        return set()
    out: set[str] = set()
    for item in history:
        if isinstance(item, dict):
            phase = str(item.get("phase") or "").strip()
            if phase:
                out.add(phase)
    return out


def engagement_rate_pct(views: int, likes: int, comments: int, shares: int) -> float:
    if views <= 0:
        return 0.0
    return (likes + comments + shares) / views * 100.0


def comments_per_view(comments: int, views: int) -> float:
    if views <= 0:
        return 0.0
    return comments / views


def engagement_rate_pct(views: int, likes: int, comments: int, shares: int) -> float:
    """Match ``corpus_ingest._safe_engagement_rate`` — percentage 0–100, never >100."""
    if views <= 0:
        return 0.0
    return min((likes + comments + shares) / views * 100.0, 100.0)


def compute_distribution_shape(history: Any) -> str | None:
    """Return ``spike_then_flat`` when M4 criteria match, else None."""
    if not isinstance(history, list):
        return None

    by_phase: dict[str, dict[str, Any]] = {}
    for item in history:
        if not isinstance(item, dict):
            continue
        phase = str(item.get("phase") or "").strip()
        if phase in ("t0", "t6h", "t24h"):
            by_phase[phase] = item

    t0 = by_phase.get("t0")
    t6 = by_phase.get("t6h")
    t24 = by_phase.get("t24h")
    if not t0 or not t6 or not t24:
        return None

    try:
        v0 = int(t0.get("views") or 0)
        v6 = int(t6.get("views") or 0)
        likes6 = int(t6.get("likes") or 0)
        comments6 = int(t6.get("comments") or 0)
        shares6 = int(t6.get("shares") or 0)
        likes24 = int(t24.get("likes") or 0)
        comments24 = int(t24.get("comments") or 0)
        shares24 = int(t24.get("shares") or 0)
        v24 = int(t24.get("views") or 0)
    except (TypeError, ValueError):
        return None

    if v0 <= 0 or v6 < 2 * v0:
        return None

    er6 = engagement_rate_pct(v6, likes6, comments6, shares6)
    er24 = engagement_rate_pct(v24, likes24, comments24, shares24)
    cpv6 = comments_per_view(comments6, v6)
    cpv24 = comments_per_view(comments24, v24)

    er_drop = er6 > 0 and (er6 - er24) / er6 >= 0.30
    cpv_drop = cpv6 > 0 and (cpv6 - cpv24) / cpv6 >= 0.30

    if er_drop or cpv_drop:
        return "spike_then_flat"
    return None


def _parse_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    try:
        text = str(raw).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def _due_phase(first_seen_at: Any, *, now: datetime, phase: str) -> bool:
    fs = _parse_ts(first_seen_at)
    if fs is None:
        return False
    hours = REFETCH_OFFSETS_H[phase]
    return now >= fs + timedelta(hours=hours)


def select_stats_history_refetch_candidates(
    client: Any,
    *,
    limit: int = REFETCH_BATCH_LIMIT,
    now: datetime | None = None,
) -> list[tuple[dict[str, Any], str]]:
    """Return ``(row, phase)`` pairs due for ``t6h`` or ``t24h`` refetch."""
    now = now or datetime.now(UTC)
    lookback = (now - timedelta(days=REFETCH_LOOKBACK_DAYS)).isoformat()

    res = (
        client.table("video_corpus")
        .select(
            "video_id,tiktok_url,stats_history,first_seen_at,"
            "views,likes,comments,shares,distribution_shape"
        )
        .gte("first_seen_at", lookback)
        .not_.is_("tiktok_url", "null")
        .neq("tiktok_url", "")
        .order("first_seen_at")
        .limit(max(limit * 4, 200))
        .execute()
    )
    rows: list[dict[str, Any]] = list(res.data or [])

    out: list[tuple[dict[str, Any], str]] = []
    for row in rows:
        if len(out) >= limit:
            break
        phases = history_phases(row.get("stats_history"))
        if "t0" not in phases:
            continue
        for phase in REFETCH_PHASES:
            if phase in phases:
                continue
            if _due_phase(row.get("first_seen_at"), now=now, phase=phase):
                out.append((row, phase))
                break
    return out


def _extract_metrics_from_post(post: dict[str, Any]) -> dict[str, int] | None:
    detail = post.get("aweme_detail") or post
    stats = detail.get("statistics") or {}
    views = int(stats.get("play_count") or stats.get("playCount") or 0)
    if views <= 0:
        return None
    return {
        "views": views,
        "likes": int(stats.get("digg_count") or stats.get("diggCount") or 0),
        "comments": int(stats.get("comment_count") or stats.get("commentCount") or 0),
        "shares": int(stats.get("share_count") or stats.get("shareCount") or 0),
    }


def append_snapshot(history: Any, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    base: list[dict[str, Any]] = []
    if isinstance(history, list):
        base = [h for h in history if isinstance(h, dict)]
    return [*base, snapshot]


async def run_stats_history_refetch(
    *,
    client: Any | None = None,
    limit: int = REFETCH_BATCH_LIMIT,
) -> StatsHistoryRefetchResult:
    from getviews_pipeline import ensemble
    from getviews_pipeline.corpus_refresh import _BudgetExceeded, _fetch_chunk_with_retry
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    now = datetime.now(UTC)
    work = select_stats_history_refetch_candidates(client, limit=limit, now=now)
    result = StatsHistoryRefetchResult(candidates=len(work))
    if not work:
        logger.info("[stats_history_m4] no candidates")
        return result

    by_id: dict[str, tuple[dict[str, Any], str]] = {}
    for row, phase in work:
        vid = str(row.get("video_id") or "")
        if vid:
            by_id[vid] = (row, phase)

    ids = list(by_id.keys())
    for chunk_idx, chunk in enumerate(_chunked(ids, REFETCH_CHUNK)):
        posts = await _fetch_chunk_with_retry(ensemble, chunk)
        if posts is _BudgetExceeded:
            result.errors += len(chunk)
            break
        if isinstance(posts, Exception):
            result.errors += len(chunk)
            continue

        fresh_by_id: dict[str, dict[str, int]] = {}
        for post in posts:
            detail = post.get("aweme_detail") or post
            vid = str(detail.get("aweme_id") or "")
            if not vid:
                continue
            metrics = _extract_metrics_from_post(post)
            if metrics is not None:
                fresh_by_id[vid] = metrics

        for vid in chunk:
            row, phase = by_id[vid]
            metrics = fresh_by_id.get(vid)
            if metrics is None:
                result.missing += 1
                continue

            snapshot = make_stats_snapshot(
                views=metrics["views"],
                likes=metrics["likes"],
                comments=metrics["comments"],
                shares=metrics["shares"],
                phase=phase,
                at=now,
            )
            new_history = append_snapshot(row.get("stats_history"), snapshot)
            payload: dict[str, Any] = {
                "stats_history": new_history,
                "views": metrics["views"],
                "likes": metrics["likes"],
                "comments": metrics["comments"],
                "shares": metrics["shares"],
                "engagement_rate": round(
                    engagement_rate_pct(
                        metrics["views"],
                        metrics["likes"],
                        metrics["comments"],
                        metrics["shares"],
                    ),
                    6,
                ),
                "last_refetched_at": now.isoformat(),
            }
            if phase == "t24h":
                shape = compute_distribution_shape(new_history)
                if shape:
                    payload["distribution_shape"] = shape
                    result.shapes_set += 1

            try:
                client.table("video_corpus").update(payload).eq("video_id", vid).execute()
                result.refreshed += 1
            except Exception as exc:
                logger.warning("[stats_history_m4] update failed video_id=%s: %s", vid, exc)
                result.errors += 1

        if chunk_idx * REFETCH_CHUNK + len(chunk) < len(ids):
            await asyncio.sleep(REFETCH_CHUNK_COOLDOWN_S)

    logger.info(
        "[stats_history_m4] candidates=%d refreshed=%d missing=%d errors=%d shapes_set=%d",
        result.candidates,
        result.refreshed,
        result.missing,
        result.errors,
        result.shapes_set,
    )
    return result


def _chunked(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]
