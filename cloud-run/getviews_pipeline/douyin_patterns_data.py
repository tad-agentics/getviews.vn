"""D5d (2026-06-05) — Kho Douyin · read model for ``GET /douyin/patterns``.

Returns the most recent week's 3-pattern batch per active niche,
ordered by (niche_id ASC, rank ASC). The FE §I "Pattern signals"
surface (D5e) renders these as 3-up cards above the §II video grid.

Why "most recent week" instead of "this week":

  • The cron fires Mondays 21:00 UTC. On a Monday morning before the
    cron runs, the most recent ``week_of`` row is from the prior week
    — still the freshest data we have. Returning empty in that
    half-day window would render the §I surface as empty for no
    user-facing reason.
  • For each niche we pick MAX(week_of), then return the 3 rows for
    that week. Different niches may end up on slightly different
    weeks during the cron rollout window — that's fine; the FE shows
    them side by side regardless.

No pagination — exactly 3 patterns × 10 niches = 30 rows max. Trivial
to ship over the wire.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def fetch_douyin_patterns(sb: Any) -> dict[str, Any]:
    """Build the ``/douyin/patterns`` response payload.

    Returns:
        ``{"patterns": [...]}`` — flat array of pattern rows, ordered
        by ``(niche_id, rank)``. Empty list when no rows exist (cron
        hasn't run yet) — FE renders an empty state for §I in that
        case.
    """
    # Pull the 200 most-recent rows ordered by week_of DESC, then
    # collapse client-side to "max week_of per niche". 200 is well
    # over 3×10×any-reasonable-history; keeps the query bounded.
    try:
        res = (
            sb.table("douyin_patterns")
            .select(
                "id, niche_id, week_of, rank, name_vn, name_zh, "
                "hook_template_vi, format_signal_vi, sample_video_ids, "
                "cn_rise_pct_avg, computed_at"
            )
            .order("week_of", desc=True)
            .order("niche_id", desc=False)
            .order("rank", desc=False)
            .limit(200)
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        logger.exception("[douyin/patterns] fetch failed: %s", exc)
        return {"patterns": []}

    # Collapse to the most-recent week_of per niche.
    latest_week_per_niche: dict[int, str] = {}
    for r in rows:
        nid = r.get("niche_id")
        wk = r.get("week_of")
        if nid is None or not wk:
            continue
        nid_int = int(nid)
        wk_str = str(wk)
        existing = latest_week_per_niche.get(nid_int)
        if existing is None or wk_str > existing:
            latest_week_per_niche[nid_int] = wk_str

    out: list[dict[str, Any]] = []
    for r in rows:
        nid = r.get("niche_id")
        wk = r.get("week_of")
        if nid is None or not wk:
            continue
        if str(wk) != latest_week_per_niche.get(int(nid)):
            continue
        out.append(_serialize_pattern(r))

    # Re-order deterministically — the source query was DESC on
    # week_of, but after collapsing we want stable (niche_id, rank)
    # for the FE.
    out.sort(key=lambda p: (p["niche_id"], p["rank"]))
    return {"patterns": out}


def _serialize_pattern(row: dict[str, Any]) -> dict[str, Any]:
    """Project a Supabase row into the FE-facing shape. Keeps NULL-safe
    defaults so the FE can branch on a `null` adapt-rise without
    optional-chaining everything."""

    def _float_or_none(v: Any) -> float | None:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    raw_samples = row.get("sample_video_ids")
    samples: list[str] = []
    if isinstance(raw_samples, list):
        for s in raw_samples:
            if isinstance(s, str) and s.strip():
                samples.append(s.strip())

    return {
        "id": str(row.get("id") or ""),
        "niche_id": int(row.get("niche_id") or 0),
        "week_of": str(row.get("week_of") or ""),
        "rank": int(row.get("rank") or 0),
        "name_vn": str(row.get("name_vn") or ""),
        "name_zh": row.get("name_zh"),
        "hook_template_vi": str(row.get("hook_template_vi") or ""),
        "format_signal_vi": str(row.get("format_signal_vi") or ""),
        "sample_video_ids": samples,
        "cn_rise_pct_avg": _float_or_none(row.get("cn_rise_pct_avg")),
        "computed_at": row.get("computed_at"),
    }
