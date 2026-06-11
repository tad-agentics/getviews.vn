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


# Must match ``ChannelScreen.tsx`` ``CREDIT_COST`` and vision §10 (F4 Channel Sâu).
CHANNEL_DIAGNOSE_CREDIT_COST = 3


def _decrement_credit_or_raise(user_sb: Any, *, user_id: str) -> None:
    """Atomically deduct ``CHANNEL_DIAGNOSE_CREDIT_COST`` credits in one RPC.

    Uses ``decrement_credit(p_user_id, p_amount)`` so all credits are spent in
    a single guarded UPDATE — a transport error mid-deduction can no longer
    leave the user partially charged (TD-1). NULL response = "no credits
    remain" → ``InsufficientCreditsError``; transport / 5xx errors bubble up
    untouched so the caller maps them to ``stream_failed`` rather than telling
    the user "Hết credit" for what was actually a Supabase outage.

    Parity: ``answer_session.append_turn`` uses the same atomic ``p_amount``
    call; FE ``ChannelScreen`` gates ``credits_remaining >= 3``.
    """
    rpc_resp = user_sb.rpc(
        "decrement_credit",
        {"p_user_id": user_id, "p_amount": CHANNEL_DIAGNOSE_CREDIT_COST},
    ).execute()
    if rpc_resp.data is None:
        raise InsufficientCreditsError()


def fetch_niche_benchmarks(
    user_sb: Any,
    *,
    niche_id: int,
    content_class_id: int | None = None,
    creator_tier: str | None = None,
) -> dict[str, Any]:
    """Channel percentiles — class+tier RPC when class known, else legacy niche RPC."""
    fallback: dict[str, Any] = {
        "channel_count": 0,
        "avg_views_p25": 0,
        "avg_views_p50": 0,
        "avg_views_p75": 0,
        "engagement_p50": 0.0,
        "engagement_p75": 0.0,
        "posts_per_week_p50": 0.0,
        "posts_per_week_p75": 0.0,
    }
    if content_class_id is not None:
        try:
            res = user_sb.rpc(
                "content_class_channel_benchmarks",
                {
                    "p_content_class_id": content_class_id,
                    "p_creator_tier": creator_tier,
                },
            ).execute()
            data = res.data
            if isinstance(data, list) and data and isinstance(data[0], dict):
                data = data[0]
            if isinstance(data, dict) and int(data.get("channel_count") or 0) > 0:
                p50 = int(data.get("avg_views_p50") or 0)
                return {
                    "channel_count": int(data.get("channel_count") or 0),
                    "avg_views_p25": p50,
                    "avg_views_p50": p50,
                    "avg_views_p75": int(data.get("avg_views_p75") or 0),
                    "engagement_p50": float(data.get("engagement_p50") or 0),
                    "engagement_p75": float(data.get("engagement_p75") or 0),
                    "posts_per_week_p50": float(data.get("posts_per_week_p50") or 0),
                    "posts_per_week_p75": float(data.get("posts_per_week_p75") or 0),
                    "benchmark_axis": "content_class",
                }
        except Exception as exc:
            logger.warning(
                "[channel_diagnose] content_class_channel_benchmarks failed class=%s: %s",
                content_class_id,
                exc,
            )
    try:
        res = user_sb.rpc("niche_channel_benchmarks", {"p_niche_id": niche_id}).execute()
        data = res.data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            data = data[0]
        if isinstance(data, dict):
            return {
                "channel_count":      int(data.get("channel_count") or 0),
                "avg_views_p25":      int(data.get("avg_views_p25") or 0),
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


# Back-compat alias for internal callers and tests that patch the legacy name.
_fetch_niche_benchmarks = fetch_niche_benchmarks

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
    posted_at: str


class SampleVideo(TypedDict):
    thumbnail_url: str | None
    views: int
    video_url: str


class UGCCreator(TypedDict, total=False):
    handle: str
    followers: int | None
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


def _quarter_start_dt(qkey: str) -> datetime | None:
    """First day of calendar quarter from ``2026Q1``-style key."""
    try:
        year = int(qkey[:4])
        qnum = int(qkey[-1])
        month = {1: 1, 2: 4, 3: 7, 4: 10}[qnum]
        return datetime(year, month, 1, tzinfo=UTC)
    except (KeyError, ValueError, IndexError):
        return None


def _format_share_mix(videos: list[dict[str, Any]]) -> dict[str, int]:
    """Top content_format shares as integer percents (sum ≈ 100 for top-3)."""
    if not videos:
        return {}
    counts = Counter(
        str(v.get("content_format") or classify_format(v)) for v in videos
    )
    total = len(videos)
    top3 = counts.most_common(3)
    return {fmt: round(100 * c / total) for fmt, c in top3}


def compute_inflection_point(videos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the biggest sequential quarter-over-quarter drop in average views.

    Requires ≥ 2 quarters with ≥ 2 videos each.
    Returns peak/current quarter stats plus format mixes split at the boundary
    between quarters (for verdict narrative).
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
                boundary = _quarter_start_dt(curr_q)
                before_vids = [
                    v for v in videos
                    if v.get("posted_at") and isinstance(v["posted_at"], datetime)
                    and boundary is not None and v["posted_at"] < boundary
                ]
                after_vids = [
                    v for v in videos
                    if v.get("posted_at") and isinstance(v["posted_at"], datetime)
                    and boundary is not None and v["posted_at"] >= boundary
                ]
                before_avg_v = (
                    sum(v.get("views", 0) for v in before_vids) / len(before_vids)
                    if before_vids else 0.0
                )
                after_avg_v = (
                    sum(v.get("views", 0) for v in after_vids) / len(after_vids)
                    if after_vids else 0.0
                )
                best = {
                    "peak_quarter": prev_q,
                    "current_quarter": curr_q,
                    "peak_avg": int(prev_avg),
                    "current_avg": int(curr_avg),
                    "drop_pct": round(drop_pct, 1),
                    "date_iso":              boundary.isoformat() if boundary else "",
                    "before_format_mix":    _format_share_mix(before_vids),
                    "after_format_mix":     _format_share_mix(after_vids),
                    "before_avg_views":     round(before_avg_v),
                    "after_avg_views":      round(after_avg_v),
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
    pa = v.get("posted_at")
    posted_iso = pa.isoformat() if isinstance(pa, datetime) else ""
    return PerformerTile(
        video_id=str(v.get("video_id") or ""),
        thumbnail_url=v.get("thumbnail_url"),
        views=int(v.get("views") or 0),
        format_label=str(v.get("content_format") or "product_closeup"),
        caption_snippet=snippet,
        video_url=str(v.get("video_url") or ""),
        posted_at=posted_iso,
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
            .eq("ingest_loop_niche_id", niche_id)
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
                caption_snippet=str(row.get("caption") or "")[:80],
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
# Channel persona (two-axis) + score card + cadence + hashtags + peers (v2)
# ---------------------------------------------------------------------------

PeerSource = Literal["content_class", "niche_only", "thin"]


FORMAT_LABEL_VI: dict[str, str] = {
    "livestream_clip": "Live / cắt sóng",
    "unboxing_process": "Unbox / quy trình",
    "list_ranking": "Top / ranking",
    "lifestyle_model": "Lifestyle / Model",
    "photo_carousel": "Ảnh / slideshow",
    "product_closeup": "Cận sản phẩm",
}


def format_label_vi(fmt: str) -> str:
    return FORMAT_LABEL_VI.get(fmt, fmt.replace("_", " "))


async def derive_channel_persona(
    user_sb: Any,
    handle: str,
    legacy_niche_id: int,
    channel_pattern: dict[str, Any],
) -> dict[str, Any]:
    """Dominant format + corpus-backed (or mapped) content class for the handle."""
    dominant_format = extract_dominant_format(channel_pattern)
    dom_cc: int | None = None
    label_vn = "—"

    try:
        res = (
            user_sb.table("video_corpus")
            .select("content_class_id")
            .eq("ingest_loop_niche_id", legacy_niche_id)
            .eq("creator_handle", handle.lower())
            .not_.is_("content_class_id", "null")
            .limit(200)
            .execute()
        )
        rows = res.data or []
        if rows:
            cc_counts: Counter[int] = Counter()
            for r in rows:
                cid = r.get("content_class_id")
                if cid is not None:
                    cc_counts[int(cid)] += 1
            if cc_counts:
                dom_cc = cc_counts.most_common(1)[0][0]
    except Exception as exc:
        logger.debug("[channel_diagnose] persona corpus query failed: %s", exc)

    if dom_cc is None and dominant_format:
        try:
            rpc = user_sb.rpc(
                "map_legacy_corpus_to_content_class",
                {
                    "p_niche_id": legacy_niche_id,
                    "p_content_format": dominant_format,
                },
            ).execute()
            raw = rpc.data
            if raw is not None:
                if isinstance(raw, list) and raw:
                    first = raw[0]
                    dom_cc = int(first) if not isinstance(first, dict) else int(first.get("map_legacy_corpus_to_content_class") or 0)  # noqa: E501
                else:
                    dom_cc = int(raw)
                if dom_cc == 0:
                    dom_cc = None
        except Exception as exc:
            logger.debug("[channel_diagnose] map_legacy RPC failed: %s", exc)

    if dom_cc is not None:
        try:
            cr = (
                user_sb.table("content_classifications")
                .select("name_vn")
                .eq("id", dom_cc)
                .maybe_single()
                .execute()
            )
            rowd = cr.data
            if isinstance(rowd, dict) and rowd.get("name_vn"):
                label_vn = str(rowd["name_vn"])
        except Exception as exc:
            logger.debug("[channel_diagnose] content_class label failed: %s", exc)

    return {
        "dominant_format": dominant_format,
        "dominant_content_class_id": dom_cc,
        "content_class_label": label_vn,
    }


async def fetch_handle_corpus_for_findings(
    user_sb: Any,
    handle: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Recent handle rows for Phase 2a channel findings (compliance, boost, persona, slang)."""
    h = handle.lower().strip()
    if not h:
        return []
    try:
        res = (
            user_sb.table("video_corpus")
            .select(
                "video_id,analysis_json,boost_attribution,content_class_id,"
                "posted_at,caption,indexed_at,views"
            )
            .eq("creator_handle", h)
            .order("posted_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(res.data or [])
    except Exception as exc:
        logger.debug("[channel_diagnose] handle corpus for findings failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# P3 (Lightreel audit 2026-06-11) — recent-content feature audit + brand UGC
# ---------------------------------------------------------------------------

_AUDIT_MIN_ROWS = 3
_AUDIT_MAX_ROWS = 12
_FACE_SCENE_TYPES = frozenset({"face_to_camera"})


def _audit_features_from_analysis(analysis: Any) -> dict[str, Any] | None:
    """Per-video feature flags from a corpus ``analysis_json`` blob.

    Tolerates both raw Scene keys (``type``/``start``) and normalised
    payloads (``scene_type``/``start_s``). None when there is no analysis.
    """
    if not isinstance(analysis, dict) or not analysis:
        return None
    scenes = analysis.get("scenes")
    scenes = scenes if isinstance(scenes, list) else []
    has_face = False
    has_overlay = False
    for sc in scenes:
        if not isinstance(sc, dict):
            continue
        if (
            str(sc.get("subject") or "") == "face"
            or str(sc.get("type") or sc.get("scene_type") or "") in _FACE_SCENE_TYPES
        ):
            has_face = True
        if str(sc.get("overlay_style") or "").lower() not in ("", "none", "null"):
            has_overlay = True
    ha = analysis.get("hook_analysis")
    ha = ha if isinstance(ha, dict) else {}
    hook_phrase = str(ha.get("hook_phrase") or "").strip()
    hook_type = str(ha.get("hook_type") or "").strip().lower()
    has_hook = len(hook_phrase) >= 4 or hook_type not in ("", "none", "null")
    role = str(analysis.get("audio_track_role") or "").strip().lower() or None
    return {
        "has_face": has_face,
        "has_overlay": has_overlay,
        "has_hook": has_hook,
        "audio_track_role": role,
    }


def compute_recent_content_audit(
    handle_corpus_rows: list[dict[str, Any]],
    *,
    recent_total: int | None = None,
) -> dict[str, Any] | None:
    """Aggregate frame-level features across the handle's recent corpus rows.

    Lightreel G4 (P3): the "no human faces / no hooks / music is background"
    absence audit across recent content. Zero new Gemini calls — rows come
    from ``fetch_handle_corpus_for_findings`` (extraction already paid for at
    ingest). Returns None below ``_AUDIT_MIN_ROWS`` analysed rows: a thin
    audit would be noise dressed as a count.
    """
    feats: list[dict[str, Any]] = []
    for row in handle_corpus_rows[:_AUDIT_MAX_ROWS]:
        f = _audit_features_from_analysis(row.get("analysis_json"))
        if f is None:
            continue
        try:
            f["views"] = int(row.get("views") or 0)
        except (TypeError, ValueError):
            f["views"] = 0
        feats.append(f)
    if len(feats) < _AUDIT_MIN_ROWS:
        return None
    n = len(feats)
    roles = Counter(f["audio_track_role"] for f in feats if f["audio_track_role"])
    out: dict[str, Any] = {
        "videos_scanned": n,
        "recent_total": recent_total,
        "face_videos": sum(1 for f in feats if f["has_face"]),
        "hook_videos": sum(1 for f in feats if f["has_hook"]),
        "overlay_videos": sum(1 for f in feats if f["has_overlay"]),
        "audio_roles": dict(roles),
    }
    face_views = [f["views"] for f in feats if f["has_face"] and f["views"] > 0]
    noface_views = [f["views"] for f in feats if not f["has_face"] and f["views"] > 0]
    if face_views and noface_views:
        out["avg_views_with_face"] = int(sum(face_views) / len(face_views))
        out["avg_views_without_face"] = int(sum(noface_views) / len(noface_views))
    return out


_PATTERN_LOCK_RE = re.compile(
    r"[^.!?\n]*\btr[êe]n\s+([\d][\d.,]*)\s*([KkMm]|ngh[ìi]n|tri[ệe]u)?\s*view[^.!?\n]*[.!?]?",
    re.IGNORECASE,
)


def _parse_views_token(raw: str, unit: str) -> float:
    u = (unit or "").lower()
    if u in ("k", "nghìn", "nghin"):
        return float(raw.replace(",", ".")) * 1_000
    if u in ("m", "triệu", "trieu"):
        return float(raw.replace(",", ".")) * 1_000_000
    return float(raw.replace(".", "").replace(",", ""))


def enforce_pattern_lock_guard(
    sections: list[dict[str, Any]],
    top_performers: list[dict[str, Any]],
) -> None:
    """Deterministic check on the what_worked pattern-lock sentence.

    The prompt demands the induced threshold sit BELOW the lowest cited
    top-performer's views; this guard makes that a guarantee — a violating
    sentence is stripped (the rest of the section stands) and logged.
    """
    floors = [int(t.get("views") or 0) for t in top_performers if int(t.get("views") or 0) > 0]
    if not floors:
        return
    floor = min(floors)
    for sec in sections:
        if sec.get("section_id") != "what_worked":
            continue
        text = str(sec.get("text") or "")
        m = _PATTERN_LOCK_RE.search(text)
        if not m:
            return
        try:
            threshold = _parse_views_token(m.group(1), m.group(2) or "")
        except (TypeError, ValueError):
            return
        if threshold >= floor:
            sec["text"] = (text[: m.start()] + text[m.end():]).strip()
            logger.warning(
                "[channel_diagnose] pattern-lock threshold %s >= min cited views %s — sentence stripped",
                threshold, floor,
            )
        return

_BRAND_HANDLE_NOISE = frozenset(
    {"official", "vn", "store", "shop", "real", "studio", "team", "brand"}
)


def _brand_term_from_handle(handle: str) -> str:
    """Search term for brand-mention UGC: longest non-noise token of the handle.

    ``curnon.official`` → ``curnon``; falls back to the raw handle when
    stripping would leave nothing usable.
    """
    tokens = [t for t in re.split(r"[._\d]+", (handle or "").lower()) if t]
    core = [t for t in tokens if t not in _BRAND_HANDLE_NOISE]
    if core:
        best = max(core, key=len)
        if len(best) >= 3:
            return best
    return (handle or "").lower()


async def fetch_brand_ugc_videos(
    handle: str,
    recent_avg_views: float,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """External creators' videos ABOUT this brand/channel (Lightreel G5, P3).

    One ED keyword-search call per uncached diagnosis (daily budget gate lives
    in ``ensemble._ensemble_get``); the route additionally gates on
    ``config.BRAND_UGC_SEARCH_ENABLED``. A creator qualifies only when the
    caption (or their handle) actually mentions the brand term AND the video
    clears 1.5× the channel's recent average — the section's claim is "UGC
    outperforms the brand channel", so weaker rows would dilute it.
    Empty list on any failure — never raises.
    """
    term = _brand_term_from_handle(handle)
    if len(term) < 3:
        return []
    try:
        awemes, _ = await ensemble.fetch_keyword_search(term, period=180, sorting=1)
    except Exception as exc:
        logger.warning(
            "[channel_diagnose] brand UGC keyword search failed handle=%s: %s", handle, exc
        )
        return []
    floor = max(1.5 * float(recent_avg_views or 0), 1.0)
    h_lower = (handle or "").lower()
    best_by_author: dict[str, dict[str, Any]] = {}
    for aw in awemes or []:
        norm = _normalise_aweme(aw)
        if not norm:
            continue
        uid = str(norm.get("author_handle") or "").lower()
        if not uid or uid == h_lower:
            continue
        caption_l = str(norm.get("caption") or "").lower()
        if term not in caption_l and term not in uid:
            continue
        views = int(norm.get("views") or 0)
        if views < floor:
            continue
        prev = best_by_author.get(uid)
        if prev is None or views > int(prev.get("views") or 0):
            best_by_author[uid] = norm
    ranked = sorted(
        best_by_author.values(), key=lambda r: int(r.get("views") or 0), reverse=True
    )[:limit]
    out: list[dict[str, Any]] = []
    for r in ranked:
        views = int(r.get("views") or 0)
        out.append({
            "handle": str(r.get("author_handle") or ""),
            "followers": r.get("author_followers"),
            "views": views,
            "caption_snippet": str(r.get("caption") or "")[:80],
            "video_id": str(r.get("video_id") or ""),
            "video_url": str(r.get("video_url") or ""),
            "thumbnail_url": r.get("thumbnail_url"),
            "multiplier": round(views / max(float(recent_avg_views or 0), 1.0), 1),
        })
    return out


def compute_posting_cadence(videos: list[dict[str, Any]]) -> dict[str, Any]:
    """Posts/week over the last 30 days (no clock-time / golden-hour metrics)."""
    now = _now()
    cutoff = now - timedelta(days=30)
    recent = [
        v for v in videos
        if (v.get("posted_at") or datetime.min.replace(tzinfo=UTC)) >= cutoff
    ]
    weeks = 30 / 7.0
    posts_per_week = len(recent) / weeks if weeks > 0 else 0.0
    return {"posts_per_week": round(posts_per_week, 2)}


def compute_score_card(
    videos: list[dict[str, Any]],
    channel_pattern: dict[str, Any],
    recent_window_30d: dict[str, Any],
    _inflection: dict[str, Any] | None,
    niche_benchmarks: dict[str, Any],
    persona: dict[str, Any],
    trajectory: TrajectoryShape,
) -> dict[str, Any]:
    """Structured TLDR metrics for the score card (no Gemini)."""
    max_v = int(channel_pattern.get("max_views") or 0)
    recent_avg = int(recent_window_30d.get("avg_views") or 0)
    trajectory_delta_pct = 0
    if max_v > 0:
        trajectory_delta_pct = int(round(-100.0 * (max_v - recent_avg) / max_v))

    peak_video = max(videos, key=lambda v: int(v.get("views") or 0), default=None)
    peak_date_iso: str | None = None
    peak_age_months: int | None = None
    if peak_video and peak_video.get("posted_at"):
        pd = peak_video["posted_at"]
        if isinstance(pd, datetime):
            peak_date_iso = pd.date().isoformat()
            peak_age_months = max((_now() - pd).days // 30, 0)

    p25 = int(niche_benchmarks.get("avg_views_p25") or 0)
    p50 = int(niche_benchmarks.get("avg_views_p50") or 0)
    p75 = int(niche_benchmarks.get("avg_views_p75") or 0)
    recent_f = float(recent_avg)
    if p50 <= 0 and p25 <= 0:
        pct = 50
    elif recent_f < p25 and p25 > 0:
        pct = 15
    elif recent_f < p50 and p50 > 0:
        pct = 38
    elif recent_f < p75 and p75 > 0:
        pct = 62
    else:
        pct = 88

    cadence = compute_posting_cadence(videos)
    peer_median_posts = float(niche_benchmarks.get("posts_per_week_p50") or 0)

    return {
        "trajectory_shape": trajectory,
        "trajectory_delta_pct": trajectory_delta_pct,
        "percentile_in_niche": pct,
        "niche_p25": p25,
        "niche_p50": p50,
        "niche_p75": p75,
        "category_label": str(persona.get("content_class_label") or "—"),
        "peak_views": max_v,
        "peak_date_iso": peak_date_iso,
        "peak_age_months": peak_age_months,
        "recent_avg_views": recent_avg,
        "posts_per_week": cadence["posts_per_week"],
        "peer_median_posts_per_week": peer_median_posts,
        "sample_size_videos": len(videos),
    }


def _fmt_views_short(n: int | float) -> str:
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1_000}K"
    return str(n)


def render_score_card_captions(card: dict[str, Any]) -> dict[str, str]:
    """Vietnamese interpretations for score-card rows (template, deterministic)."""
    captions: dict[str, str] = {}

    traj = str(card.get("trajectory_shape") or "stagnant")
    pam = card.get("peak_age_months")
    peak_age = int(pam) if pam is not None else 0

    if traj == "decline_from_peak":
        captions["trajectory"] = (
            f"Đỉnh từ khoảng {peak_age} tháng trước, hiện chững lại. "
            "Cần khôi phục pattern cũ hoặc thử format mới — thuật toán đã giảm "
            "đề xuất nếu retention theo batch video liên tiếp không ổn định."
        )
    elif traj == "stagnant":
        captions["trajectory"] = (
            "Trì trệ — không có tăng/giảm rõ. Nguy cơ reach bị giữ ở baseline; "
            "cần thử góc mới hoặc hook mạnh hơn để thoát plateau."
        )
    elif traj == "steady_growth":
        captions["trajectory"] = (
            "Tăng trưởng đều — momentum tốt. Giữ cadence, tiếp tục scale format "
            "thắng và test 1 biến thể/tuần để tránh bão hoà audience."
        )
    elif traj == "breakout":
        captions["trajectory"] = (
            "Breakout gần đây — cửa sổ cold-start rộng. Đăng dày 5–7 video/tuần "
            "để tối đa momentum trước khi baseline hạ."
        )
    elif traj == "bursty":
        captions["trajectory"] = (
            "Biến động mạnh — vài video nổ, phần lớn flat. Reverse-engineer video "
            "nổ để tìm pattern chung rồi lặp lại có kiểm soát."
        )
    else:  # new_account
        captions["trajectory"] = (
            "Kênh mới — chưa đủ dữ liệu cho pattern ổn định. Test 3–5 format khác "
            "nhau trong 30 ngày, đo view/format, rồi chốt 1–2 trụ cột."
        )

    pct = int(card.get("percentile_in_niche") or 50)
    p50 = int(card.get("niche_p50") or 0)
    p75 = int(card.get("niche_p75") or 0)
    recent = float(card.get("recent_avg_views") or 1)

    if pct <= 25 and p50 > 0:
        captions["percentile"] = (
            f"Dưới trung vị ngách (P50 ~ {_fmt_views_short(p50)} view/video). "
            f"Top 25% ngách cần ~{_fmt_views_short(p75)} — gap ~{p75 / recent:.1f}x so với bạn. "
            "Ưu tiên 1–2 format mạnh nhất thay vì rải đều."
        )
    elif pct <= 50 and p50 > 0:
        captions["percentile"] = (
            f"Sát dưới trung vị (P50 ~ {_fmt_views_short(p50)}). "
            f"Khoảng cách lên top 25% ~{max(p75 - recent, 0) / recent * 100:.0f}% nếu giữ hook tốt. "
            "Tập trung double-down format đang cho recent_avg cao nhất."
        )
    elif pct <= 75 and p50 > 0:
        captions["percentile"] = (
            f"Trên trung vị ngách (P50 ~ {_fmt_views_short(p50)}). "
            f"Top 25% ~{_fmt_views_short(p75)} — còn room ~{max(p75 - recent, 0) / max(recent, 1) * 100:.0f}%. "
            "Scale format thắng; chỉ test mới với rủi ro có giới hạn."
        )
    else:
        captions["percentile"] = (
            "Bạn đang ở nhóm trên cao của ngách benchmark. "
            "Duy trì pattern cốt lõi; mở rộng biến thể nhẹ để không làm loãng retention."
        )

    median = float(card.get("peer_median_posts_per_week") or 0)
    ppw = float(card.get("posts_per_week") or 0)
    if median > 0:
        delta_pct = (ppw - median) / median
        if delta_pct < -0.20:
            captions["cadence"] = (
                f"Ít hơn median ngách ({median:.1f} video/tuần) khoảng {abs(delta_pct) * 100:.0f}%. "
                "TikTok thưởng velocity ổn định — khoảng trống đăng dài có thể làm giảm cold-start. "
                "Thử nhịp 4–5 video/tuần nếu team kịp sản xuất."
            )
        elif delta_pct > 0.20:
            captions["cadence"] = (
                f"Đăng nhiều hơn median ngách ({median:.1f}) ~{delta_pct * 100:.0f}%. "
                "Volume cao chỉ hiệu quả nếu mỗi video vẫn giữ hook; nếu avg đang giảm, cân nhắc giảm sang median."
            )
        else:
            captions["cadence"] = (
                f"Sát median đăng tải ({median:.1f} video/tuần). Cadence ổn — ưu tiên chất lượng hook và retention."
            )
    else:
        captions["cadence"] = (
            f"{ppw:.1f} video/tuần (30 ngày gần nhất). "
            "Chưa có benchmark đăng tải ngách — soi tay đối thủ cùng category trong bảng dưới."
        )

    max_v = int(card.get("peak_views") or 0)
    ravg = int(card.get("recent_avg_views") or 0)
    if max_v > 0:
        drop = int(round(100 * (max_v - ravg) / max_v)) if ravg <= max_v else 0
        captions["peak_recent"] = (
            f"Đỉnh {_fmt_views_short(max_v)} vs gần đây ~{_fmt_views_short(ravg)} "
            f"(chênh ~{drop}% so với đỉnh). "
            "Nếu gap lớn, thường do đổi format hoặc hook yếu ở batch gần đây."
        )
    else:
        captions["peak_recent"] = "Chưa đủ view để so đỉnh vs hiện tại."

    return captions


_HASHTAG_RE = re.compile(r"#([^\s#]+)")


def compute_hashtag_insights(videos: list[dict[str, Any]], top: int = 5) -> list[dict[str, Any]]:
    """Top hashtags by usage with avg views and multiplier vs channel mean."""
    tag_views: dict[str, list[int]] = {}
    tag_counts: dict[str, int] = {}
    for v in videos:
        caption = str(v.get("caption") or "")
        views = int(v.get("views") or 0)
        seen_tag: set[str] = set()
        for m in _HASHTAG_RE.finditer(caption):
            t = m.group(1).lower()
            if t in seen_tag:
                continue
            seen_tag.add(t)
            tag_counts[t] = tag_counts.get(t, 0) + 1
            tag_views.setdefault(t, []).append(views)
    if not tag_counts:
        return []
    top_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], -sum(tag_views[x[0]]) / len(tag_views[x[0]])))[:top]
    channel_avg = sum(v.get("views", 0) for v in videos) / max(len(videos), 1)
    out: list[dict[str, Any]] = []
    for tag, count in top_tags:
        avgs = tag_views[tag]
        avg_v = sum(avgs) / len(avgs)
        mult = (avg_v / channel_avg) if channel_avg > 0 else 1.0
        out.append({
            "tag": f"#{tag}",
            "count": count,
            "avg_views": int(avg_v),
            "multiplier": round(mult, 2),
        })
    return out


def hashtag_caption_for_insight(insight: dict[str, Any], channel_avg: float) -> str:
    """Two-line Vietnamese hint per hashtag row."""
    m = float(insight.get("multiplier") or 1.0)
    count = int(insight.get("count") or 0)
    if m >= 2.0 and count <= 5:
        return (
            f"Outperform {m:.1f}x trung bình kênh nhưng chỉ dùng {count} lần. "
            "Ưu tiên ghim vào caption các video cùng chủ đề."
        )
    if m >= 1.5:
        return f"Trên trung bình ({m:.1f}x). Giữ hashtag này ở các video liên quan."
    if m <= 0.5:
        return (
            f"Hút view thấp ({m:.1f}x). Có thể quá hẹp hoặc không khớp nội dung — "
            "thử mix thêm hashtag ngách rộng hơn."
        )
    if m < 1.0:
        return f"Hơi dưới trung bình ({m:.1f}x). Cân nhắc thay bằng hashtag có avg cao hơn trong list."
    return f"Trung tính ({m:.1f}x). Không kéo view mạnh nhưng không gây hại."


def select_verdict_tiles(videos: list[dict[str, Any]]) -> list[PerformerTile]:
    """Peak video + 2 most recent (deduped) for forensic context in §1."""
    if not videos:
        return []
    peak = max(videos, key=lambda v: int(v.get("views") or 0))
    tiles: list[PerformerTile] = [_make_tile(peak)]
    recent_2 = sorted(
        [v for v in videos if v.get("posted_at")],
        key=lambda v: v["posted_at"],  # type: ignore[index]
        reverse=True,
    )[:2]
    seen = {str(peak.get("video_id") or "")}
    for v in recent_2:
        vid = str(v.get("video_id") or "")
        if vid and vid not in seen:
            seen.add(vid)
            tiles.append(_make_tile(v))
    return tiles[:3]


def normalize_peer_creator_for_fe(
    creator: dict[str, Any],
    *,
    niche_slug: str = "",
) -> dict[str, Any]:
    """Shape UGC/peer rows for the SPA (thumbnail + followers guard)."""
    samples = creator.get("sample_videos") or []
    thumb = None
    svurl = ""
    if samples and isinstance(samples[0], dict):
        thumb = samples[0].get("thumbnail_url")
        svurl = str(samples[0].get("video_url") or "")
    raw_followers = creator.get("followers")
    if raw_followers is None:
        followers: int | None = None
    else:
        fc = int(raw_followers)
        followers = fc if fc > 0 else None
    return {
        "handle": str(creator.get("handle") or ""),
        "followers": followers,
        "avg_views": float(creator.get("avg_views") or 0),
        "thumbnail_url": thumb or "",
        "niche_slug": niche_slug,
        "sample_video_url": svurl,
        "format_label": str(creator.get("format_label") or ""),
    }


def _peer_unique_handle_count(rows: list[dict[str, Any]]) -> int:
    return len({
        str(r.get("creator_handle") or "").lower()
        for r in rows
        if r.get("creator_handle")
    })


def _run_peer_corpus_query(
    user_sb: Any,
    legacy_niche_id: int,
    exclude_handle: str,
    content_class_id: int | None,
    creator_tier: str | None = None,
    *,
    reference_eligible_only: bool = False,
) -> list[dict[str, Any]]:
    ex = exclude_handle.lower().strip()
    q = (
        user_sb.table("video_corpus")
        .select(
            "creator_handle,views,content_format,thumbnail_url,video_url,video_id,"
            "caption,creator_tier,reference_eligible,indexed_at"
        )
        .eq("ingest_loop_niche_id", legacy_niche_id)
        .neq("creator_handle", ex)
    )
    if content_class_id is not None:
        q = q.eq("content_class_id", content_class_id)
    if creator_tier:
        q = q.eq("creator_tier", creator_tier)
    if reference_eligible_only:
        q = q.eq("reference_eligible", True)
    res = q.order("views", desc=True).limit(160).execute()
    return res.data or []


def _peer_corpus_with_eligible_fallback(
    user_sb: Any,
    legacy_niche_id: int,
    exclude_handle: str,
    content_class_id: int | None,
    creator_tier: str | None,
) -> list[dict[str, Any]]:
    """Try ``reference_eligible=true`` first; retry unfiltered when &lt;4 unique handles."""
    eligible = _run_peer_corpus_query(
        user_sb,
        legacy_niche_id,
        exclude_handle,
        content_class_id,
        creator_tier,
        reference_eligible_only=True,
    )
    if _peer_unique_handle_count(eligible) >= 4:
        return eligible
    all_rows = _run_peer_corpus_query(
        user_sb,
        legacy_niche_id,
        exclude_handle,
        content_class_id,
        creator_tier,
        reference_eligible_only=False,
    )
    if _peer_unique_handle_count(eligible) < 4:
        logger.info(
            "[channel_diagnose] peer reference_eligible fallback "
            "eligible_handles=%d all_handles=%d",
            _peer_unique_handle_count(eligible),
            _peer_unique_handle_count(all_rows),
        )
    return all_rows


def _peer_tier_fallback_chain(
    user_sb: Any,
    legacy_niche_id: int,
    exclude_handle: str,
    content_class_id: int | None,
    creator_tier: str | None,
) -> tuple[list[dict[str, Any]], PeerSource]:
    """(class, tier) → (class, all tiers) → niche-only fallback."""
    if content_class_id is None:
        rows = _peer_corpus_with_eligible_fallback(
            user_sb, legacy_niche_id, exclude_handle, None, creator_tier=None,
        )
        n = _peer_unique_handle_count(rows)
        if n >= 4:
            return rows, "niche_only"
        return rows, "thin" if rows else "thin"

    if creator_tier:
        tier_rows = _peer_corpus_with_eligible_fallback(
            user_sb,
            legacy_niche_id,
            exclude_handle,
            content_class_id,
            creator_tier=creator_tier,
        )
        if _peer_unique_handle_count(tier_rows) >= 4:
            return tier_rows, "content_class"

    class_rows = _peer_corpus_with_eligible_fallback(
        user_sb, legacy_niche_id, exclude_handle, content_class_id, creator_tier=None,
    )
    if _peer_unique_handle_count(class_rows) >= 4:
        return class_rows, "content_class"

    niche_rows = _peer_corpus_with_eligible_fallback(
        user_sb, legacy_niche_id, exclude_handle, None, creator_tier=None,
    )
    if _peer_unique_handle_count(niche_rows) >= 4:
        return niche_rows, "niche_only"
    if niche_rows:
        return niche_rows, "thin"
    return [], "thin"


async def select_niche_peer_creators(
    user_sb: Any,
    legacy_niche_id: int,
    content_class_id: int | None,
    exclude_handle: str,
    channel_avg: float,
    limit: int = 3,
    creator_tier: str | None = None,
) -> tuple[list[dict[str, Any]], PeerSource, list[dict[str, Any]]]:
    """Corpus-first peers (content_class + optional tier → fallback) + follower enrichment."""
    if channel_avg <= 0:
        return [], "thin", []

    tier_rows, source = _peer_tier_fallback_chain(
        user_sb,
        legacy_niche_id,
        exclude_handle,
        content_class_id,
        creator_tier,
    )
    if not tier_rows:
        return [], "thin", []

    by_h: dict[str, list[dict[str, Any]]] = {}
    for r in tier_rows:
        h = str(r.get("creator_handle") or "").strip().lower()
        if not h:
            continue
        by_h.setdefault(h, []).append(r)

    scored: list[tuple[str, float, list[dict[str, Any]]]] = []
    for h, rs in by_h.items():
        views = [int(x.get("views") or 0) for x in rs]
        avg_v = sum(views) / len(views) if views else 0.0
        scored.append((h, avg_v, rs))
    scored.sort(key=lambda t: t[1], reverse=True)

    handles_for_enrich: list[tuple[str, float, list[dict[str, Any]]]] = []
    for item in scored:
        if len(handles_for_enrich) >= limit * 3:
            break
        handles_for_enrich.append(item)

    async def _followers(h: str) -> int | None:
        try:
            users, _ = await ensemble.fetch_user_search(h)
            for u in users:
                uid = str(u.get("unique_id") or u.get("uniqueId") or "").strip().lower()
                if uid == h.lower():
                    fc = int(u.get("follower_count") or u.get("followerCount") or 0)
                    return fc if fc > 0 else None
        except Exception:
            pass
        return None

    f_followers = await asyncio.gather(*[_followers(h) for h, _, _ in handles_for_enrich])

    creators: list[dict[str, Any]] = []
    for idx, (h, avg_v, rs) in enumerate(handles_for_enrich):
        if not rs:
            continue
        fol = f_followers[idx] if idx < len(f_followers) else None
        rs_sorted = sorted(rs, key=lambda x: int(x.get("views") or 0), reverse=True)
        top2 = rs_sorted[:2]
        fmt_counter = Counter(str(x.get("content_format") or "product_closeup") for x in rs)
        dom_fmt = fmt_counter.most_common(1)[0][0]
        sample_videos: list[SampleVideo] = []
        for x in top2:
            sample_videos.append(SampleVideo(
                thumbnail_url=x.get("thumbnail_url"),
                views=int(x.get("views") or 0),
                video_url=str(x.get("video_url") or ""),
            ))
        creators.append({
            "handle": h,
            "followers": fol,
            "avg_views": avg_v,
            "engagement_rate": 0.0,
            "format_label": dom_fmt,
            "sample_videos": sample_videos,
        })

    creators.sort(key=lambda c: c["avg_views"], reverse=True)
    return creators[:limit], source, tier_rows


def derive_next_video_concept(
    peer_creators: list[dict[str, Any]],
    channel_pattern: dict[str, Any],
    videos: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Deterministic next-video skeleton from top peer format gap."""
    if not peer_creators or not videos:
        return None
    top = max(peer_creators, key=lambda c: float(c.get("avg_views") or 0))
    peer_fmt = str(top.get("format_label") or "product_closeup")
    total = len(videos)
    if total == 0:
        return None
    chan_count = sum(
        1 for v in videos
        if str(v.get("content_format") or classify_format(v)) == peer_fmt
    )
    share = chan_count / total
    if share >= 0.45:
        return None
    samples = top.get("sample_videos") or []
    sample0: dict[str, Any] = samples[0] if samples and isinstance(samples[0], dict) else {}
    sample_url = str(sample0.get("video_url") or "")
    thumb = sample0.get("thumbnail_url")
    dur = 18.0
    for v in videos:
        if str(v.get("content_format") or "") == peer_fmt:
            dur = float(v.get("duration_sec") or 18)
            break
    peer_avg = float(top.get("avg_views") or 0)
    rationale = (
        f"@{top.get('handle')} trung bình ~{_fmt_views_short(int(peer_avg))} với format "
        f"{format_label_vi(peer_fmt)}; bạn chỉ có {chan_count}/{total} video cùng format (~{share*100:.0f}%)."
    )
    return {
        "format": peer_fmt,
        "format_label": format_label_vi(peer_fmt),
        "duration_sec": int(dur),
        "rationale_struct": rationale,
        "sample_peer_handle": str(top.get("handle") or ""),
        "sample_video_url": sample_url,
        "sample_thumbnail_url": thumb,
        "peer_avg_views": int(peer_avg),
        "channel_share_pct": round(share * 100, 1),
    }


# ---------------------------------------------------------------------------
# Caption hashtag mining (continued)
# ---------------------------------------------------------------------------


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
        raw_fc = int(author.get("follower_count") or author.get("followerCount") or 0)
        followers = raw_fc if raw_fc > 0 else None
        er = (likes_sum / (raw_fc * len(awemes))) if raw_fc > 0 and awemes else 0.0

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
