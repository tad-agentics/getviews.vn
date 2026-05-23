"""F5 — channel peek for Trends cards + ChannelScreen Nhanh (W5-4, Launch Phase 1)."""

from __future__ import annotations

import logging
import statistics
from collections import Counter
from datetime import datetime
from typing import Any

from getviews_pipeline.channel_diagnose import (
    build_channel_pattern,
    compute_recent_window_stats,
    extract_dominant_format,
    fetch_niche_benchmarks,
    normalize_handle,
)
from getviews_pipeline.channel_findings import (
    ChannelFinding,
    build_channel_findings,
    format_distribution_from_corpus_rows,
    pick_channel_quick_peek,
)
from getviews_pipeline.supabase_client import get_service_client

logger = logging.getLogger(__name__)

_QUICK_PEEK_FINDING_IDS = frozenset({
    "channel_view_ceiling_300",
    "channel_format_entropy_high",
})


def _parse_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _dominant_hook(videos: list[dict[str, Any]]) -> str | None:
    counts: dict[str, int] = {}
    for row in videos:
        ht = str(row.get("hook_type") or "").strip()
        if ht:
            counts[ht] = counts.get(ht, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _breakout_video(videos: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_mult = 0.0
    for row in videos:
        mult = row.get("breakout_multiplier")
        try:
            m = float(mult) if mult is not None else 0.0
        except (TypeError, ValueError):
            m = 0.0
        if m > best_mult:
            best_mult = m
            best = row
    if best is None or best_mult < 1.2:
        # Fallback: highest views in window
        sorted_rows = sorted(videos, key=lambda r: int(r.get("views") or 0), reverse=True)
        best = sorted_rows[0] if sorted_rows else None
    if not best:
        return None
    vid = best.get("video_id")
    if not vid:
        return None
    return {
        "video_id": str(vid),
        "views": int(best.get("views") or 0),
        "hook_type": best.get("hook_type"),
        "breakout_multiplier": best.get("breakout_multiplier"),
    }


def _mode_int(rows: list[dict[str, Any]], key: str) -> int | None:
    counts: Counter[int] = Counter()
    for row in rows:
        raw = row.get(key)
        if raw is not None:
            counts[int(raw)] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _mode_str(rows: list[dict[str, Any]], key: str) -> str | None:
    counts: Counter[str] = Counter()
    for row in rows:
        raw = str(row.get(key) or "").strip()
        if raw:
            counts[raw] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _fetch_peer_corpus_rows(
    sb: Any,
    handle: str,
    *,
    content_class_id: int | None,
    legacy_niche_id: int | None,
) -> list[dict[str, Any]]:
    """Peer rows for format distribution — corpus-only, no EnsembleData."""
    h = normalize_handle(handle)
    if content_class_id is None and legacy_niche_id is None:
        return []
    try:
        q = (
            sb.table("video_corpus")
            .select("content_format,views,creator_handle")
            .neq("creator_handle", h)
        )
        if content_class_id is not None:
            q = q.eq("content_class_id", content_class_id)
        elif legacy_niche_id is not None:
            q = q.eq("ingest_loop_niche_id", legacy_niche_id)
        res = q.order("views", desc=True).limit(80).execute()
        return list(res.data or [])
    except Exception as exc:
        logger.warning(
            "[channel_quick_peek] peer corpus fetch failed handle=%s class=%s niche=%s: %s",
            h,
            content_class_id,
            legacy_niche_id,
            exc,
        )
        return []


def _findings_teasers(findings: list[ChannelFinding], limit: int = 2) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for finding in findings:
        if finding.id not in _QUICK_PEEK_FINDING_IDS:
            continue
        out.append({
            "finding_id": finding.id,
            "teaser": finding.claim,
            "strength": finding.strength,
        })
        if len(out) >= limit:
            break
    return out


def channel_quick_peek_for_handle(handle: str) -> dict[str, Any]:
    """Corpus-only F5 payload — no credits, no SSE."""
    h = normalize_handle(handle)
    empty: dict[str, Any] = {
        "finding_id": None,
        "teaser": None,
        "median_views": None,
        "dominant_hook": None,
        "breakout_video": None,
        "findings": [],
        "corpus_video_count": 0,
    }
    if not h:
        return empty

    sb = get_service_client()
    res = (
        sb.table("video_corpus")
        .select(
            "video_id,views,likes,comments,content_format,posted_at,"
            "hook_type,breakout_multiplier,analysis_json,boost_attribution,"
            "content_class_id,caption,indexed_at,ingest_loop_niche_id,creator_tier"
        )
        .eq("creator_handle", h)
        .order("posted_at", desc=True)
        .limit(40)
        .execute()
    )
    raw_rows = res.data or []
    videos: list[dict[str, Any]] = []
    for row in raw_rows:
        videos.append(
            {
                "video_id": row.get("video_id"),
                "views": row.get("views"),
                "likes": row.get("likes"),
                "comments": row.get("comments"),
                "content_format": row.get("content_format"),
                "posted_at": _parse_ts(row.get("posted_at")),
                "hook_type": row.get("hook_type"),
                "breakout_multiplier": row.get("breakout_multiplier"),
            }
        )

    if len(videos) < 3:
        return empty

    view_list = [int(v.get("views") or 0) for v in videos if int(v.get("views") or 0) > 0]
    median_views = int(statistics.median(view_list)) if view_list else None

    channel_pattern = build_channel_pattern(videos)
    recent_window_30d = compute_recent_window_stats(videos)
    dominant_format = extract_dominant_format(channel_pattern) or None
    content_class_id = _mode_int(raw_rows, "content_class_id")
    legacy_niche_id = _mode_int(raw_rows, "ingest_loop_niche_id")
    creator_tier = _mode_str(raw_rows, "creator_tier")
    peer_corpus_rows = _fetch_peer_corpus_rows(
        sb,
        h,
        content_class_id=content_class_id,
        legacy_niche_id=legacy_niche_id,
    )
    niche_format_distribution = format_distribution_from_corpus_rows(peer_corpus_rows)
    niche_benchmarks = fetch_niche_benchmarks(
        sb,
        niche_id=legacy_niche_id or 0,
        content_class_id=content_class_id,
        creator_tier=creator_tier,
    )

    findings = build_channel_findings(
        videos=videos,
        channel_pattern=channel_pattern,
        recent_window_30d=recent_window_30d,
        inflection=None,
        niche_benchmarks=niche_benchmarks,
        peer_corpus_rows=peer_corpus_rows,
        handle_corpus_rows=raw_rows,
        dominant_format=dominant_format,
        niche_format_distribution=niche_format_distribution or None,
    )
    peek = pick_channel_quick_peek(findings)
    finding_id = peek["finding_id"] if peek else None
    teaser = peek["teaser"] if peek else None

    return {
        "finding_id": finding_id,
        "teaser": teaser,
        "median_views": median_views,
        "dominant_hook": _dominant_hook(videos),
        "breakout_video": _breakout_video(videos),
        "findings": _findings_teasers(findings),
        "corpus_video_count": len(videos),
    }
