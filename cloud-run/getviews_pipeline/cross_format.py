"""A.1 (2026-05-15) — cross-niche format insight.

When a user's video has a ``content_class_id``, that content_class
belongs to a ``format_axis`` (pov_storytelling, tutorial,
review_unboxing, etc.). This module computes how that format is
performing across niches — surfacing "your format is rising broadly,
here are top hooks others are using" insight that niche-only
diagnosis can't see.

Read-only — uses ``video_corpus`` + ``content_classifications`` joined
on ``content_class_id``. No new tables. Pre-launch corpus is small;
the helper requires ``niches_with_format >= 3`` and
``total_sample_size >= 20`` before returning a payload, so callers
can safely render unconditionally without showing noise during the
ingest catch-up window.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from getviews_pipeline.enum_labels_vi import HOOK_TYPE_VI

logger = logging.getLogger(__name__)


# Display labels for the 12 stable format_axis values seeded in
# ``20260510000004_two_axis_niche_pr1_schema.sql`` (+ PR6). Destination /
# travel-face vlogs use ``vlog_daily`` in DB — there is no separate
# ``vlog_destination`` axis (HI-9 alignment).
_FORMAT_AXIS_LABEL_VI: dict[str, str] = {
    "pov_storytelling":     "POV / Storytelling",
    "talking_head_advice":  "Talking head · Lời khuyên",
    "tutorial":             "Tutorial · Hướng dẫn",
    "vlog_daily":           "Vlog hằng ngày",
    "montage_highlights":   "Montage · Highlight",
    "skit_scripted":        "Hài skit",
    "react_commentary":     "React / Commentary",
    "dance_choreography":   "Dance choreography",
    "music_performance":    "Cover / Performance",
    "review_unboxing":      "Review · Unbox",
    "live_commerce":        "Livestream commerce",
    "comedy_observational": "Hài quan sát",
}


# Minimum thresholds before returning a signal — below these it's
# noise not trend. Tunable via env if pre-launch corpus is too small.
MIN_NICHES_WITH_FORMAT = 3
MIN_TOTAL_SAMPLE = 20

# Top-N hooks per format to surface in the response.
TOP_HOOKS_LIMIT = 5

# How many days back to look for the cross-format signal.
WINDOW_DAYS = 30


def _resolve_format_axis_for_content_class(
    sb: Any, content_class_id: int,
) -> str | None:
    """Look up format_axis on content_classifications for a content_class id.

    Single read; cheap. Caller falls back gracefully when None.
    """
    if not content_class_id:
        return None
    try:
        res = (
            sb.table("content_classifications")
            .select("format_axis")
            .eq("id", int(content_class_id))
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("[cross_format] content_classifications lookup failed: %s", exc)
        return None
    data = getattr(res, "data", None) if res else None
    if isinstance(data, dict):
        return data.get("format_axis")
    return None


def _fetch_format_corpus(
    sb: Any, format_axis: str, since_iso: str,
    *,
    content_format: str | None = None,
) -> list[dict[str, Any]]:
    """Pull corpus rows whose content_class shares the same format_axis.

    When ``content_format`` is set (slug matching ``video_corpus.content_format``),
    narrow to that structural format so cross-niche hooks match the user's
    video (audit CROSS-NICHE-FORMAT v4). Caller returns None if the filtered
    set fails gating — no fallback to unfiltered popularity.
    """
    try:
        # Step 1 — content_class ids in this format_axis (small set, ~5-10).
        cc_res = (
            sb.table("content_classifications")
            .select("id")
            .eq("format_axis", format_axis)
            .eq("active", True)
            .execute()
        )
        cc_ids = [int(r["id"]) for r in (cc_res.data or []) if r.get("id") is not None]
        if not cc_ids:
            return []
        # Step 2 — corpus rows in those content_classes within the window.
        q = (
            sb.table("video_corpus")
            .select("video_id, ingest_loop_niche_id, hook_type, views, content_format")
            .in_("content_class_id", cc_ids)
            .gt("views", 0)
            .gte("indexed_at", since_iso)
            .limit(2000)
        )
        cf = str(content_format or "").strip()
        if cf:
            q = q.eq("content_format", cf)
        res = q.execute()
        return list(res.data or [])
    except Exception as exc:
        logger.warning(
            "[cross_format] corpus fetch for format=%s failed: %s",
            format_axis, exc,
        )
        return []


def get_cross_format_signal(
    sb: Any,
    *,
    content_class_id: int | None,
    content_format: str | None = None,
    days: int = WINDOW_DAYS,
) -> dict[str, Any] | None:
    """Build the cross-niche format insight for one user video.

    Returns None when:
      - content_class_id is missing or unmapped to a format_axis.
      - The format has fewer than ``MIN_NICHES_WITH_FORMAT`` distinct
        niches (cross-niche signal not meaningful).
      - Total sample is below ``MIN_TOTAL_SAMPLE`` (noisy aggregate).

    Returned shape mirrors ``CrossFormatSignal`` in
    ``src/lib/api-types.ts``.
    """
    if not content_class_id:
        return None
    format_axis = _resolve_format_axis_for_content_class(sb, content_class_id)
    if not format_axis:
        return None

    since = (datetime.now(UTC) - timedelta(days=max(days, 1))).isoformat()
    rows = _fetch_format_corpus(sb, format_axis, since, content_format=content_format)
    if not rows:
        return None

    niches_seen: set[int] = set()
    by_hook: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total_sample = 0
    for r in rows:
        nid = r.get("ingest_loop_niche_id")
        ht = r.get("hook_type") or ""
        v = int(r.get("views") or 0)
        if v <= 0:
            continue
        total_sample += 1
        if nid is not None:
            niches_seen.add(int(nid))
        if ht:
            by_hook[ht].append({"views": v, "niche_id": nid})

    niches_with_format = len(niches_seen)
    if niches_with_format < MIN_NICHES_WITH_FORMAT:
        return None
    if total_sample < MIN_TOTAL_SAMPLE:
        return None

    # Rank hooks by avg_views, tiebreak by niche_spread (more diverse = more
    # transferable). Keep TOP_HOOKS_LIMIT.
    hook_summaries: list[dict[str, Any]] = []
    for hook_type, entries in by_hook.items():
        if len(entries) < 2:
            # Single-row hook isn't a "top hook"; skip to avoid noise.
            continue
        avg_v = sum(e["views"] for e in entries) / len(entries)
        spread = len({e["niche_id"] for e in entries if e["niche_id"] is not None})
        hook_summaries.append({
            "hook_type": hook_type,
            "hook_type_vi": HOOK_TYPE_VI.get(hook_type.lower(), hook_type),
            "avg_views": int(round(avg_v)),
            "niche_spread": spread,
        })
    hook_summaries.sort(key=lambda h: (h["avg_views"], h["niche_spread"]), reverse=True)

    return {
        "format_axis": format_axis,
        "format_label_vi": _FORMAT_AXIS_LABEL_VI.get(format_axis, format_axis),
        "niches_with_format": niches_with_format,
        "total_sample_size": total_sample,
        "top_hooks": hook_summaries[:TOP_HOOKS_LIMIT],
    }
