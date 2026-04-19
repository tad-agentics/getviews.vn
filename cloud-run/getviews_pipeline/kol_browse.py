"""B.2.1 — /kol/browse match scoring + row assembly (Phase B plan B.0.2 / B.2).

Rule-based match (weights sum to 1.0), computed per request (no persistence yet).
"""

from __future__ import annotations

import math
from typing import Any, Literal

Tab = Literal["pinned", "discover"]


def normalize_handle(raw: str | None) -> str:
    if not raw:
        return ""
    return str(raw).strip().removeprefix("@").lower()


def niche_match_component(creator_niche_id: int, user_niche_id: int) -> float:
    return 1.0 if int(creator_niche_id) == int(user_niche_id) else 0.0


def follower_range_overlap(creator_followers: int, user_followers: int) -> float:
    """B.0.2 — 1 − |log10(creator / user)| / 2, clamped 0–1; 0 if gap > 100×."""
    cf = max(int(creator_followers), 1)
    uf = max(int(user_followers), 1)
    ratio = max(cf, uf) / min(cf, uf)
    if ratio > 100:
        return 0.0
    raw = 1.0 - abs(math.log10(cf / uf)) / 2.0
    return max(0.0, min(1.0, raw))


def growth_percentile_from_avgs(creator_avg_views: float, niche_avg_views: list[float]) -> float:
    """Proxy for growth_percentile: rank by avg_views within niche (0–1)."""
    vals = [float(x) for x in niche_avg_views if x is not None and float(x) >= 0]
    if not vals:
        return 0.5
    n = len(vals)
    if n == 1:
        return 0.5
    rank = sum(1 for x in vals if float(x) <= float(creator_avg_views))
    return max(0.0, min(1.0, rank / float(n)))


def reference_channel_overlap(reference_handles: list[str], starter_handles_in_niche: set[str]) -> float:
    """Fraction of user's reference handles that appear in starter pool for the niche."""
    refs = [normalize_handle(h) for h in reference_handles if normalize_handle(h)]
    if not refs:
        return 1.0
    hits = sum(1 for h in refs if h in starter_handles_in_niche)
    return hits / float(len(refs))


def compute_match_score(
    *,
    creator_niche_id: int,
    user_niche_id: int,
    creator_followers: int,
    user_followers: int,
    creator_avg_views: float,
    niche_avg_views: list[float],
    reference_handles: list[str],
    starter_handles_in_niche: set[str],
) -> int:
    nm = niche_match_component(creator_niche_id, user_niche_id)
    fr = follower_range_overlap(creator_followers, user_followers)
    gp = growth_percentile_from_avgs(creator_avg_views, niche_avg_views)
    ro = reference_channel_overlap(reference_handles, starter_handles_in_niche)
    total = 0.40 * nm + 0.30 * fr + 0.20 * gp + 0.10 * ro
    return int(round(max(0.0, min(1.0, total)) * 100.0))


def _user_followers_proxy(sb: Any, *, niche_id: int, reference_handles: list[str]) -> int:
    """Mean followers across pinned references in starter_creators; else 50_000."""
    norms = [normalize_handle(h) for h in reference_handles if normalize_handle(h)]
    if not norms:
        return 50_000
    res = (
        sb.table("starter_creators")
        .select("followers")
        .eq("niche_id", niche_id)
        .in_("handle", norms)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return 50_000
    vals = [int(r.get("followers") or 0) for r in rows]
    return max(1, int(sum(vals) / len(vals)))


def _corpus_fallback_rows(sb: Any, *, niche_id: int, handles: list[str]) -> dict[str, dict[str, Any]]:
    """Per-handle aggregates from video_corpus when starter_creators row is missing."""
    if not handles:
        return {}
    res = (
        sb.table("video_corpus")
        .select("creator_handle, creator_followers, views")
        .eq("niche_id", niche_id)
        .in_("creator_handle", handles)
        .execute()
    )
    agg: dict[str, dict[str, int | float | list[int]]] = {}
    for row in res.data or []:
        h = str(row.get("creator_handle") or "")
        if not h:
            continue
        bucket = agg.setdefault(h, {"followers": 0, "views": [], "n": 0})
        cf = int(row.get("creator_followers") or 0)
        v = int(row.get("views") or 0)
        bucket["followers"] = max(int(bucket["followers"]), cf)
        vs = bucket["views"]
        assert isinstance(vs, list)
        vs.append(v)
        bucket["n"] = int(bucket["n"]) + 1
    out: dict[str, dict[str, Any]] = {}
    for h, b in agg.items():
        vs = b["views"]
        assert isinstance(vs, list)
        avg = sum(vs) / len(vs) if vs else 0.0
        out[h] = {
            "handle": h,
            "display_name": None,
            "followers": int(b["followers"]),
            "avg_views": float(avg),
            "video_count": int(b["n"]),
            "rank": 9999,
            "is_curated": False,
        }
    return out


def _niche_label(sb: Any, niche_id: int) -> str:
    res = (
        sb.table("niche_taxonomy")
        .select("name_vn, name_en")
        .eq("id", niche_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return ""
    data = rows[0]
    return str(data.get("name_vn") or data.get("name_en") or "")


def run_kol_browse_sync(
    user_sb: Any,
    *,
    niche_id: int,
    tab: Tab,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Build /kol/browse JSON for the authenticated user (JWT-scoped client)."""
    prof = (
        user_sb.table("profiles")
        .select("primary_niche, reference_channel_handles")
        .single()
        .execute()
    )
    pdata = prof.data or {}
    primary = pdata.get("primary_niche")
    if primary is None:
        raise ValueError("Chưa chọn ngách — chạy onboarding trước.")
    primary_int = int(primary)
    if int(niche_id) != primary_int:
        raise ValueError("niche_id không khớp ngách đã chọn của bạn.")

    ref_raw = pdata.get("reference_channel_handles") or []
    reference_handles = [normalize_handle(str(x)) for x in ref_raw if normalize_handle(str(x))]

    niche_label = _niche_label(user_sb, niche_id)
    user_followers = _user_followers_proxy(user_sb, niche_id=niche_id, reference_handles=reference_handles)

    starters_all = (
        user_sb.table("starter_creators")
        .select("handle, display_name, followers, avg_views, video_count, rank")
        .eq("niche_id", niche_id)
        .order("rank", desc=False)
        .execute()
    )
    starter_rows = list(starters_all.data or [])
    niche_avg_views = [float(r.get("avg_views") or 0) for r in starter_rows]
    starter_handle_set = {normalize_handle(str(r.get("handle") or "")) for r in starter_rows}

    pinned_set = set(reference_handles)

    def decorate(row: dict[str, Any]) -> dict[str, Any]:
        h = normalize_handle(str(row.get("handle") or ""))
        cid = niche_id
        cf = int(row.get("followers") or 0)
        av = float(row.get("avg_views") or 0)
        score = compute_match_score(
            creator_niche_id=cid,
            user_niche_id=primary_int,
            creator_followers=cf,
            user_followers=user_followers,
            creator_avg_views=av,
            niche_avg_views=niche_avg_views,
            reference_handles=reference_handles,
            starter_handles_in_niche=starter_handle_set,
        )
        name = row.get("display_name") or h
        return {
            "handle": h,
            "name": name,
            "niche_label": niche_label or None,
            "followers": cf,
            "avg_views": int(round(av)),
            "growth_30d_pct": 0.0,
            "match_score": score,
            "tone": "",
            "is_pinned": h in pinned_set,
        }

    if tab == "discover":
        total = len(starter_rows)
        start = (page - 1) * page_size
        slice_rows = starter_rows[start : start + page_size]
        rows = [decorate(dict(r)) for r in slice_rows]
        return {
            "tab": tab,
            "niche_id": niche_id,
            "page": page,
            "page_size": page_size,
            "total": total,
            "reference_handles": reference_handles,
            "rows": rows,
        }

    # pinned — preserve profile array order
    handles_ordered: list[str] = []
    seen: set[str] = set()
    for h in reference_handles:
        if h and h not in seen:
            seen.add(h)
            handles_ordered.append(h)

    by_handle: dict[str, dict[str, Any]] = {}
    for r in starter_rows:
        hn = normalize_handle(str(r.get("handle") or ""))
        if hn:
            by_handle[hn] = dict(r)

    missing = [h for h in handles_ordered if h not in by_handle]
    if missing:
        for h, fb in _corpus_fallback_rows(user_sb, niche_id=niche_id, handles=missing).items():
            by_handle.setdefault(h, fb)

    ordered_rows: list[dict[str, Any]] = []
    for h in handles_ordered:
        if h in by_handle:
            ordered_rows.append(by_handle[h])
        else:
            ordered_rows.append(
                {
                    "handle": h,
                    "display_name": None,
                    "followers": 0,
                    "avg_views": 0.0,
                    "video_count": 0,
                    "rank": 9999,
                    "is_curated": False,
                }
            )
    total = len(ordered_rows)
    start = (page - 1) * page_size
    slice_rows = ordered_rows[start : start + page_size]
    rows = [decorate(dict(r)) for r in slice_rows]
    return {
        "tab": tab,
        "niche_id": niche_id,
        "page": page,
        "page_size": page_size,
        "total": total,
        "reference_handles": reference_handles,
        "rows": rows,
    }
