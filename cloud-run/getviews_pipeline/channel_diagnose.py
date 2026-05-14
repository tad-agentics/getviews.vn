"""B.X — Channel diagnosis data-ingest layer.

Pure functions + one async fetch. No DB writes — the SSE endpoint owns persistence.
All I/O goes through ensemble.*; Supabase reads are passed in from the caller.

Also re-exports shared credit/handle utilities that were previously in
``channel_analyze.py`` (now deleted) so ``routers/video.py`` has a single
import point for all channel-diagnosis concerns.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, TypedDict

from getviews_pipeline import ensemble

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared utilities (migrated from channel_analyze.py)
# ---------------------------------------------------------------------------


def normalize_handle(raw: str | None) -> str:
    """Strip ``@`` and lowercase a TikTok handle."""
    if not raw:
        return ""
    return str(raw).strip().removeprefix("@").lower()


class InsufficientCreditsError(Exception):
    """``decrement_credit`` returned NULL (no credits to spend) or raised."""


def _decrement_credit_or_raise(user_sb: Any, *, user_id: str) -> None:
    """Decrement one credit; distinguish "out of credits" from "infra failed".

    On NULL response (the RPC's signal for "no credits remain") raise
    ``InsufficientCreditsError`` so the caller can surface
    ``insufficient_credits`` to the user. Transport / 5xx errors bubble
    up untouched so the caller's generic ``except Exception`` branch
    can map them to ``stream_failed`` — the previous behaviour
    rewrapped every error as ``InsufficientCreditsError`` and told the
    user "Hết credit" for what was actually a Supabase outage.
    """
    rpc_resp = user_sb.rpc("decrement_credit", {"p_user_id": user_id}).execute()
    if rpc_resp.data is None:
        raise InsufficientCreditsError()


def _fetch_niche_benchmarks(user_sb: Any, *, niche_id: int) -> dict[str, Any]:
    """Per-niche channel-level percentiles from ``niche_channel_benchmarks`` RPC."""
    fallback: dict[str, Any] = {
        "channel_count": 0,
        "avg_views_p50": 0,
        "avg_views_p75": 0,
        "engagement_p50": 0.0,
        "engagement_p75": 0.0,
        "posts_per_week_p50": 0.0,
        "posts_per_week_p75": 0.0,
    }
    try:
        res = user_sb.rpc("niche_channel_benchmarks", {"p_niche_id": niche_id}).execute()
        data = res.data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            data = data[0]
        if isinstance(data, dict):
            return {
                "channel_count":      int(data.get("channel_count") or 0),
                "avg_views_p50":      int(data.get("avg_views_p50") or 0),
                "avg_views_p75":      int(data.get("avg_views_p75") or 0),
                "engagement_p50":     float(data.get("engagement_p50") or 0),
                "engagement_p75":     float(data.get("engagement_p75") or 0),
                "posts_per_week_p50": float(data.get("posts_per_week_p50") or 0),
                "posts_per_week_p75": float(data.get("posts_per_week_p75") or 0),
            }
    except Exception as exc:
        logger.warning("[channel_diagnose] niche_channel_benchmarks RPC failed: %s", exc)
    return fallback

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

TrajectoryShape = Literal[
    "decline_from_peak",
    "stagnant",
    "steady_growth",
    "breakout",
    "bursty",
    "new_account",
]


class PerformerTile(TypedDict, total=False):
    video_id: str
    thumbnail_url: str | None
    views: int
    format_label: str
    caption_snippet: str
    video_url: str


class SampleVideo(TypedDict):
    thumbnail_url: str | None
    views: int
    video_url: str


class UGCCreator(TypedDict):
    handle: str
    followers: int
    avg_views: float
    engagement_rate: float
    format_label: str
    sample_videos: list[SampleVideo]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_timestamp(ts: Any) -> datetime | None:
    """Parse int (epoch), ISO string, or datetime to aware datetime. Returns None on failure."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(float(ts), tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(ts, str):
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(ts, fmt)
                return dt.replace(tzinfo=UTC)
            except ValueError:
                pass
        # epoch as string
        try:
            return datetime.fromtimestamp(float(ts), tz=UTC)
        except (OSError, OverflowError, ValueError):
            pass
    return None


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Format classification
# ---------------------------------------------------------------------------

_BUCKET_KEYWORDS: dict[str, list[str]] = {
    "livestream_clip": ["live", "trực tiếp", "stream", "livestream"],
    "unboxing_process": ["unbox", "mở hộp", "review", "đập hộp", "thử", "haul"],
    "list_ranking": ["top ", "#1", "#2", "best", "rank", "list", "bảng xếp"],
    "lifestyle_model": ["vlog", "outfit", "ootd", "daily", "cuộc sống", "ngày"],
    "photo_carousel": ["ảnh", "slide", "gallery", "carousel"],
}


def classify_format(video: dict[str, Any]) -> str:
    """Classify a video dict into one of 6 content format buckets.

    Inputs used: ``duration_sec``, ``caption`` (lowercased).
    Falls through to ``product_closeup`` if no keyword matches.
    """
    caption = str(video.get("caption") or "").lower()
    duration = float(video.get("duration_sec") or 0)

    # Photo carousels: very short duration (< 5 s) or carousel flag
    if duration < 5 and duration > 0:
        return "photo_carousel"

    for bucket, kws in _BUCKET_KEYWORDS.items():
        if any(kw in caption for kw in kws):
            return bucket

    # Lifestyle if no product cues and moderately long
    if duration > 60:
        return "lifestyle_model"

    return "product_closeup"


# ---------------------------------------------------------------------------
# Live channel video fetch
# ---------------------------------------------------------------------------


async def fetch_channel_videos_live(
    handle: str,
    target_count: int = 65,
) -> list[dict[str, Any]]:
    """Fetch recent videos for ``handle`` via EnsembleData.

    Returns a list of flat dicts with normalised fields. Returns ``[]`` on
    any failure — never raises.
    """
    try:
        awemes = await ensemble.fetch_user_posts(handle, depth=2)
    except Exception as exc:
        logger.warning("[channel_diagnose] fetch_user_posts failed handle=%r: %s", handle, exc)
        return []

    videos: list[dict[str, Any]] = []
    for aw in awemes[:target_count]:
        vid = _normalise_aweme(aw)
        if vid:
            videos.append(vid)
    return videos


def _normalise_aweme(aw: dict[str, Any]) -> dict[str, Any] | None:
    """Flatten a raw EnsembleData aweme into the ChannelVideo shape."""
    try:
        aweme_id = str(aw.get("aweme_id") or aw.get("id") or "").strip()
        if not aweme_id:
            return None

        stats = aw.get("statistics") or aw.get("stats") or {}
        author = aw.get("author") or {}

        views = int(stats.get("play_count") or stats.get("playCount") or 0)
        likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)
        comments = int(stats.get("comment_count") or stats.get("commentCount") or 0)
        caption = str(aw.get("desc") or aw.get("caption") or "")
        followers = int(author.get("follower_count") or author.get("followerCount") or 0)
        author_handle = str(author.get("unique_id") or author.get("uniqueId") or "")

        # Duration
        video_obj = aw.get("video") or {}
        duration_sec = float(
            video_obj.get("duration") or aw.get("duration") or 0
        )
        if duration_sec > 1000:
            duration_sec = duration_sec / 1000  # ms → s

        # posted_at
        create_time = aw.get("create_time") or aw.get("createTime")
        posted_at = _parse_timestamp(create_time)

        # thumbnail_url: prefer cover from video object; fallback to first slide
        thumbnail_url: str | None = None
        cover = video_obj.get("cover") or video_obj.get("origin_cover") or {}
        cover_urls: list[str] = cover.get("url_list") or []
        if cover_urls:
            thumbnail_url = cover_urls[0]
        if not thumbnail_url:
            image_lists = ensemble.extract_image_url_lists(aw)
            if image_lists and image_lists[0]:
                thumbnail_url = image_lists[0][0]

        # video_url
        video_urls = ensemble.extract_video_urls(aw)
        video_url = video_urls[0] if video_urls else ""

        content_format = classify_format({
            "caption": caption,
            "duration_sec": duration_sec,
        })

        return {
            "video_id": aweme_id,
            "views": views,
            "likes": likes,
            "comments": comments,
            "caption": caption,
            "duration_sec": duration_sec,
            "posted_at": posted_at,
            "thumbnail_url": thumbnail_url,
            "video_url": video_url,
            "author_handle": author_handle,
            "author_followers": followers,
            "content_format": content_format,
        }
    except Exception as exc:
        logger.debug("[channel_diagnose] aweme normalise failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Channel pattern
# ---------------------------------------------------------------------------


def build_channel_pattern(videos: list[dict[str, Any]]) -> dict[str, Any]:
    """Group videos by content_format and compute per-format stats.

    Returns a dict with a ``formats`` key (per-format breakdown) plus
    top-level ``global_avg_views`` and ``max_views`` fields used by
    ``classify_trajectory``.
    """
    now = _now()
    cutoff_recent = now - timedelta(days=30)

    by_fmt: dict[str, list[dict[str, Any]]] = {}
    for v in videos:
        fmt = v.get("content_format") or classify_format(v)
        by_fmt.setdefault(fmt, []).append(v)

    total_views = sum(v.get("views", 0) for v in videos)
    total_count = len(videos)
    global_avg = int(total_views / total_count) if total_count else 0
    max_views = max((v.get("views", 0) for v in videos), default=0)

    formats: dict[str, dict[str, Any]] = {}
    for fmt, vids in by_fmt.items():
        views_list = [v.get("views", 0) for v in vids]
        count = len(vids)
        avg_views = int(sum(views_list) / count) if count else 0
        fmt_max = max(views_list, default=0)

        recent = [
            v for v in vids
            if (v.get("posted_at") or datetime.min.replace(tzinfo=UTC)) >= cutoff_recent
        ]
        older = [v for v in vids if v not in recent]

        recent_avg = int(sum(v.get("views", 0) for v in recent) / len(recent)) if recent else 0
        prior_avg = int(sum(v.get("views", 0) for v in older) / len(older)) if older else 0

        formats[fmt] = {
            "count": count,
            "avg_views": avg_views,
            "max_views": fmt_max,
            "recent_avg": recent_avg,
            "prior_avg": prior_avg,
            "quality_flag": "thin" if count < 5 else "ok",
        }

    return {
        "formats": formats,
        "global_avg_views": global_avg,
        "max_views": max_views,
        "total_videos": total_count,
    }


# ---------------------------------------------------------------------------
# Recent window stats
# ---------------------------------------------------------------------------


def compute_recent_window_stats(
    videos: list[dict[str, Any]],
    days: int = 30,
) -> dict[str, Any]:
    """Channel-wide metrics for the most recent ``days`` days.

    Returns ``{"avg_views": int, "peak_views": int, "video_count": int}``.
    All values are zero when no videos fall in the window.
    """
    now = _now()
    cutoff = now - timedelta(days=days)
    recent = [
        v for v in videos
        if (v.get("posted_at") or datetime.min.replace(tzinfo=UTC)) >= cutoff
    ]
    if not recent:
        return {"avg_views": 0, "peak_views": 0, "video_count": 0}

    views_list = [v.get("views", 0) for v in recent]
    return {
        "avg_views": int(sum(views_list) / len(views_list)),
        "peak_views": max(views_list, default=0),
        "video_count": len(recent),
    }


# ---------------------------------------------------------------------------
# Inflection point
# ---------------------------------------------------------------------------


def _quarter_key(dt: datetime) -> str:
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}Q{q}"


def compute_inflection_point(videos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the biggest sequential quarter-over-quarter drop in average views.

    Requires ≥ 2 quarters with ≥ 2 videos each.
    Returns ``{peak_quarter, current_quarter, drop_pct, quarters}`` or ``None``.
    """
    by_quarter: dict[str, list[int]] = {}
    for v in videos:
        dt = v.get("posted_at")
        if not dt:
            continue
        q = _quarter_key(dt)
        by_quarter.setdefault(q, []).append(v.get("views", 0))

    # Keep quarters with ≥ 2 videos, sorted
    valid_quarters = sorted(
        [(q, vs) for q, vs in by_quarter.items() if len(vs) >= 2]
    )
    if len(valid_quarters) < 2:
        return None

    quarter_avgs = [(q, sum(vs) / len(vs)) for q, vs in valid_quarters]

    # Find the biggest sequential drop
    best: dict[str, Any] | None = None
    for i in range(1, len(quarter_avgs)):
        prev_q, prev_avg = quarter_avgs[i - 1]
        curr_q, curr_avg = quarter_avgs[i]
        if prev_avg > 0:
            drop_pct = (prev_avg - curr_avg) / prev_avg * 100
            if drop_pct > 0 and (best is None or drop_pct > best["drop_pct"]):
                best = {
                    "peak_quarter": prev_q,
                    "current_quarter": curr_q,
                    "peak_avg": int(prev_avg),
                    "current_avg": int(curr_avg),
                    "drop_pct": round(drop_pct, 1),
                }

    # Also compute monotonic growth info (used in steady_growth classification)
    if best is not None:
        # Check if the drop is sequential across ALL quarters (monotonic decline)
        all_avgs = [a for _, a in quarter_avgs]
        is_monotonic_growth = all(
            all_avgs[i] >= all_avgs[i - 1] * 1.2 for i in range(1, len(all_avgs))
        )
        best["is_monotonic_growth"] = is_monotonic_growth
        best["quarter_avgs"] = [(q, int(a)) for q, a in quarter_avgs]

    return best


# ---------------------------------------------------------------------------
# Trajectory classifier
# ---------------------------------------------------------------------------


def _compute_quarter_avgs(videos: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """Compute per-quarter average views, sorted ascending by quarter key."""
    by_quarter: dict[str, list[int]] = {}
    for v in videos:
        dt = v.get("posted_at")
        if not dt:
            continue
        q = _quarter_key(dt)
        by_quarter.setdefault(q, []).append(v.get("views", 0))
    valid = sorted(
        [(q, sum(vs) / len(vs)) for q, vs in by_quarter.items() if len(vs) >= 2]
    )
    return valid


def classify_trajectory(
    channel_pattern: dict[str, Any],
    recent_window_30d: dict[str, Any],
    inflection: dict[str, Any] | None,
    videos: list[dict[str, Any]],
) -> TrajectoryShape:
    """Classify the channel's trajectory. First-match-wins heuristic table.

    Order: new_account → breakout → decline_from_peak → steady_growth → bursty → stagnant
    """
    total_videos = len(videos)

    # Coverage check: if a non-trivial slice of the channel's videos
    # lack ``posted_at`` (EnsembleData payload missing ``create_time`` /
    # ``createTime``), every downstream heuristic that bins by date —
    # _compute_quarter_avgs, compute_inflection_point, the breakout
    # baseline (older_videos filter), oldest_age_days — silently skips
    # those rows. The classification can flip ``decline_from_peak`` →
    # ``stagnant`` (or vice versa) without any visible signal. Log so we
    # can spot the pattern in production logs instead of hunting a
    # mystery mis-classification.
    if total_videos > 0:
        missing_timestamp = sum(1 for v in videos if not v.get("posted_at"))
        if missing_timestamp / total_videos >= 0.20:
            logger.warning(
                "[channel_diagnose] trajectory classify: %d/%d videos (%.0f%%) "
                "missing posted_at — trajectory classification may be unreliable.",
                missing_timestamp,
                total_videos,
                100.0 * missing_timestamp / total_videos,
            )

    # Oldest video age
    oldest_dt = None
    for v in videos:
        dt = v.get("posted_at")
        if dt and (oldest_dt is None or dt < oldest_dt):
            oldest_dt = dt
    oldest_age_days = (_now() - oldest_dt).days if oldest_dt else 0

    # 1. new_account — tightened from (< 30 OR < 90d) to (< 15 OR < 60d).
    # Rationale: a channel with 20 videos and a 202K→15K drop is a declining
    # brand, not a new account; the old OR gate (< 30 videos) blocked
    # decline_from_peak from ever being evaluated for mid-size channels.
    if total_videos < 15 or oldest_age_days < 60:
        return "new_account"

    max_views = channel_pattern.get("max_views", 0)
    recent_avg = recent_window_30d.get("avg_views", 0)
    recent_count = recent_window_30d.get("video_count", 0)

    # Compute global_avg excluding the recent window so breakout detection isn't
    # self-inflating (recent high videos otherwise raise global_avg, defeating the 3x check).
    now = _now()
    older_videos = [
        v for v in videos
        if (v.get("posted_at") or datetime.min.replace(tzinfo=UTC)) < now - timedelta(days=30)
    ]
    if older_videos:
        baseline_avg = sum(v.get("views", 0) for v in older_videos) / len(older_videos)
    else:
        baseline_avg = channel_pattern.get("global_avg_views", 0)

    # 2. breakout: recent_avg > 3x baseline_avg (pre-30d) AND ≥3 recent videos
    if baseline_avg > 0 and recent_avg > 3 * baseline_avg and recent_count >= 3:
        return "breakout"

    # 3. decline_from_peak: max > 5x recent_avg AND inflection with drop_pct ≥ 60
    if (
        recent_avg > 0
        and max_views > 5 * recent_avg
        and inflection is not None
        and inflection.get("drop_pct", 0) >= 60
    ):
        return "decline_from_peak"

    # 4. steady_growth: ≥3 consecutive quarters each ≥1.2x prior
    quarter_avgs = _compute_quarter_avgs(videos)
    if len(quarter_avgs) >= 4:
        avgs = [a for _, a in quarter_avgs]
        # Count consecutive monotonic-growth windows of length ≥ 3
        consecutive = 1
        for i in range(1, len(avgs)):
            if avgs[i] >= avgs[i - 1] * 1.2:
                consecutive += 1
                if consecutive >= 4:
                    return "steady_growth"
            else:
                consecutive = 1

    # 5. bursty: stdev/mean > 1.5
    all_views = [v.get("views", 0) for v in videos]
    if all_views:
        mean_v = sum(all_views) / len(all_views)
        if mean_v > 0:
            variance = sum((x - mean_v) ** 2 for x in all_views) / len(all_views)
            stdev = math.sqrt(variance)
            if stdev / mean_v > 1.5:
                return "bursty"

    return "stagnant"


# ---------------------------------------------------------------------------
# Tile selectors
# ---------------------------------------------------------------------------


def _make_tile(v: dict[str, Any]) -> PerformerTile:
    caption = str(v.get("caption") or "")
    snippet = caption[:80] + ("…" if len(caption) > 80 else "")
    return PerformerTile(
        video_id=str(v.get("video_id") or ""),
        thumbnail_url=v.get("thumbnail_url"),
        views=int(v.get("views") or 0),
        format_label=str(v.get("content_format") or "product_closeup"),
        caption_snippet=snippet,
        video_url=str(v.get("video_url") or ""),
    )


def select_top_performers(
    videos: list[dict[str, Any]],
    channel_pattern: dict[str, Any],
    limit: int = 4,
) -> list[PerformerTile]:
    """Top-2 by views from each of the top-2 archetypes by avg_views, deduped, max ``limit``."""
    formats_data = channel_pattern.get("formats") or {}
    if not formats_data:
        # fallback: top N by views globally
        sorted_vids = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)
        return [_make_tile(v) for v in sorted_vids[:limit]]

    top_2_fmts = sorted(
        formats_data.items(),
        key=lambda kv: kv[1].get("avg_views", 0),
        reverse=True,
    )[:2]

    seen: set[str] = set()
    tiles: list[PerformerTile] = []
    for fmt, _ in top_2_fmts:
        fmt_vids = sorted(
            [v for v in videos if (v.get("content_format") or classify_format(v)) == fmt],
            key=lambda v: v.get("views", 0),
            reverse=True,
        )
        for v in fmt_vids[:2]:
            vid_id = str(v.get("video_id") or "")
            if vid_id not in seen:
                seen.add(vid_id)
                tiles.append(_make_tile(v))
            if len(tiles) >= limit:
                break
        if len(tiles) >= limit:
            break

    return tiles[:limit]


def select_worst_performers(
    videos: list[dict[str, Any]],
    limit: int = 4,
) -> list[PerformerTile]:
    """Bottom-quartile views among videos posted in the last 90 days."""
    now = _now()
    cutoff = now - timedelta(days=90)
    recent = [
        v for v in videos
        if (v.get("posted_at") or datetime.min.replace(tzinfo=UTC)) >= cutoff
    ]
    if not recent:
        recent = videos  # fallback to all

    views_list = sorted(v.get("views", 0) for v in recent)
    q1_idx = max(0, len(views_list) // 4)
    q1_threshold = views_list[q1_idx] if views_list else 0

    bottom = [v for v in recent if v.get("views", 0) <= q1_threshold]
    bottom_sorted = sorted(bottom, key=lambda v: v.get("views", 0))
    return [_make_tile(v) for v in bottom_sorted[:limit]]


def select_quarterly_breakout_videos(
    videos: list[dict[str, Any]],
    limit: int = 4,
) -> list[PerformerTile]:
    """Most-viewed videos from the most recent calendar quarter."""
    now = _now()
    current_q = _quarter_key(now)
    q_vids = [v for v in videos if v.get("posted_at") and _quarter_key(v["posted_at"]) == current_q]
    if not q_vids:
        # Fall back to the last 60 days
        cutoff = now - timedelta(days=60)
        q_vids = [
            v for v in videos
            if (v.get("posted_at") or datetime.min.replace(tzinfo=UTC)) >= cutoff
        ]
    sorted_vids = sorted(q_vids, key=lambda v: v.get("views", 0), reverse=True)
    return [_make_tile(v) for v in sorted_vids[:limit]]


async def select_niche_peer_videos(
    user_sb: Any,
    niche_id: int,
    exclude_handle: str,
    limit: int = 4,
) -> list[PerformerTile]:
    """Top corpus videos from niche peers (excluding the analysed handle).

    Falls back to [] if the corpus has < 4 niche peer rows.
    """
    try:
        res = (
            user_sb.table("video_corpus")
            .select("video_id,thumbnail_url,views,content_format,title,video_url,creator_handle")
            .eq("niche_id", niche_id)
            .neq("creator_handle", exclude_handle)
            .order("views", desc=True)
            .limit(limit * 3)
            .execute()
        )
        rows = res.data or []
        if len(rows) < 4:
            return []
        tiles: list[PerformerTile] = []
        seen_handles: set[str] = set()
        for row in rows:
            h = str(row.get("creator_handle") or "")
            if h in seen_handles:
                continue
            seen_handles.add(h)
            tiles.append(PerformerTile(
                video_id=str(row.get("video_id") or ""),
                thumbnail_url=row.get("thumbnail_url"),
                views=int(row.get("views") or 0),
                format_label=str(row.get("content_format") or "product_closeup"),
                caption_snippet=str(row.get("title") or "")[:80],
                video_url=str(row.get("video_url") or ""),
            ))
            if len(tiles) >= limit:
                break
        return tiles
    except Exception as exc:
        logger.warning("[channel_diagnose] niche peer query failed niche=%d: %s", niche_id, exc)
        return []


def extract_target_video_tile(
    target_video: dict[str, Any],
    similar_peer: dict[str, Any] | None = None,
) -> list[PerformerTile]:
    """Build 1-2 tiles for §4 (video vs channel)."""
    tiles = [_make_tile(target_video)]
    if similar_peer:
        tiles.append(_make_tile(similar_peer))
    return tiles


# ---------------------------------------------------------------------------
# Creator match for §4
# ---------------------------------------------------------------------------


def compute_creator_match(
    target_format: str,
    target_views: int,
    channel_pattern: dict[str, Any],
) -> dict[str, Any] | None:
    """§4 inputs: target_video vs same-format avg vs best-format avg.

    Returns None when the target format is not present in channel_pattern.
    """
    formats_data = channel_pattern.get("formats") or {}
    if target_format not in formats_data:
        return None
    fmt_data = formats_data[target_format]
    best_fmt = max(
        formats_data.items(), key=lambda kv: kv[1].get("avg_views", 0), default=(None, {})
    )
    return {
        "target_format": target_format,
        "target_views": target_views,
        "same_format_avg": fmt_data.get("avg_views", 0),
        "best_format": best_fmt[0],
        "best_format_avg": best_fmt[1].get("avg_views", 0) if best_fmt[0] else 0,
    }


# ---------------------------------------------------------------------------
# Dominant format
# ---------------------------------------------------------------------------


def extract_dominant_format(channel_pattern: dict[str, Any]) -> str:
    """Return the dominant content_format for top_hook derivation.

    Returns the bucket with ≥ 40% of all videos OR the highest-avg_views bucket.
    Returns '' when no clear winner exists.
    """
    formats_data = channel_pattern.get("formats") or {}
    total = channel_pattern.get("total_videos", 0)
    if not formats_data or total == 0:
        return ""

    for fmt, data in formats_data.items():
        if data.get("count", 0) >= 0.4 * total:
            return fmt

    # Highest avg_views
    best = max(formats_data.items(), key=lambda kv: kv[1].get("avg_views", 0), default=(None, {}))
    return best[0] if best[0] else ""


# ---------------------------------------------------------------------------
# Caption hashtag mining
# ---------------------------------------------------------------------------

_HASHTAG_RE = re.compile(r"#([^\s#]+)")


def mine_caption_hashtags(
    videos: list[dict[str, Any]],
    top: int = 2,
) -> list[str]:
    """Extract top-N hashtags by frequency across captions.

    Drops tags appearing in only one video (noise).
    Returns lowercased, hash-stripped strings.
    """
    tag_counter: Counter[str] = Counter()
    tag_video_count: Counter[str] = Counter()

    for v in videos:
        caption = str(v.get("caption") or "")
        tags_in_this = {m.group(1).lower() for m in _HASHTAG_RE.finditer(caption)}
        for t in tags_in_this:
            tag_counter[t] += 1
            tag_video_count[t] += 1

    # Drop single-occurrence tags
    multi = {t: c for t, c in tag_counter.items() if tag_video_count[t] > 1}
    if not multi:
        return []

    return [t for t, _ in Counter(multi).most_common(top)]


# ---------------------------------------------------------------------------
# UGC creator discovery
# ---------------------------------------------------------------------------


async def fetch_ugc_creators(
    handle: str,
    niche_slug: str,
    channel_videos: list[dict[str, Any]],
    channel_avg: float,
    limit: int = 3,
) -> list[UGCCreator]:
    """Hybrid 4-query UGC scout. Returns empty list on total failure."""
    if channel_avg <= 0:
        return []

    mined_tags = mine_caption_hashtags(channel_videos, top=2)
    query_tags = list({*mined_tags, niche_slug.lower().strip("#")})
    query_tags = [t for t in query_tags if t]

    async def _safe_hashtag(tag: str) -> list[dict[str, Any]]:
        try:
            awemes, _ = await ensemble.fetch_hashtag_posts(tag)
            return awemes
        except Exception as exc:
            logger.debug("[channel_diagnose] hashtag posts failed tag=%r: %s", tag, exc)
            return []

    async def _safe_user_search(kw: str) -> list[dict[str, Any]]:
        try:
            users, _ = await ensemble.fetch_user_search(kw)
            return users
        except Exception as exc:
            logger.debug("[channel_diagnose] user_search failed kw=%r: %s", kw, exc)
            return []

    results = await asyncio.gather(
        *[_safe_hashtag(tag) for tag in query_tags],
        _safe_user_search(handle),
        return_exceptions=True,
    )

    all_awemes: list[dict[str, Any]] = []
    for r in results:
        if isinstance(r, list):
            all_awemes.extend(r)

    # Dedup by author unique_id
    by_author: dict[str, list[dict[str, Any]]] = {}
    for aw in all_awemes:
        author = aw.get("author") or {}
        uid = str(author.get("unique_id") or author.get("uniqueId") or "").strip()
        if uid and uid != handle:
            by_author.setdefault(uid, []).append(aw)

    # Compute per-author avg_views and filter by > 5x channel_avg
    creators: list[dict[str, Any]] = []
    for uid, awemes in by_author.items():
        author = awemes[0].get("author") or {}
        author_views = []
        for aw in awemes:
            stats = aw.get("statistics") or aw.get("stats") or {}
            v = int(stats.get("play_count") or stats.get("playCount") or 0)
            if v > 0:
                author_views.append(v)
        if not author_views:
            continue
        avg_v = sum(author_views) / len(author_views)
        if avg_v <= 5 * channel_avg:
            continue

        likes_sum = sum(
            int((aw.get("statistics") or {}).get("digg_count") or 0)
            for aw in awemes
        )
        followers = int(author.get("follower_count") or author.get("followerCount") or 0)
        er = (likes_sum / (followers * len(awemes))) if followers > 0 and awemes else 0.0

        sample_videos: list[SampleVideo] = []
        top_awemes = sorted(
            awemes,
            key=lambda a: int((a.get("statistics") or {}).get("play_count") or 0),
            reverse=True,
        )[:2]
        for aw in top_awemes:
            stats = aw.get("statistics") or aw.get("stats") or {}
            thumb: str | None = None
            video_obj = aw.get("video") or {}
            cover = video_obj.get("cover") or {}
            cover_urls = cover.get("url_list") or []
            if cover_urls:
                thumb = cover_urls[0]
            vurls = ensemble.extract_video_urls(aw)
            sample_videos.append(SampleVideo(
                thumbnail_url=thumb,
                views=int(stats.get("play_count") or stats.get("playCount") or 0),
                video_url=vurls[0] if vurls else "",
            ))

        fmt = classify_format({"caption": str(awemes[0].get("desc") or ""), "duration_sec": 30})
        creators.append({
            "handle": str(author.get("unique_id") or author.get("uniqueId") or uid),
            "followers": followers,
            "avg_views": avg_v,
            "engagement_rate": round(er, 4),
            "format_label": fmt,
            "sample_videos": sample_videos,
        })

    creators.sort(key=lambda c: c["avg_views"], reverse=True)
    return [UGCCreator(**c) for c in creators[:limit]]  # type: ignore[misc]
