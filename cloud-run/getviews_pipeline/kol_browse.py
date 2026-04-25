"""B.2.1 — /kol/browse match scoring + row assembly (Phase B plan B.0.2 / B.2).

Rule-based match (weights sum to 1.0), computed per request (no persistence yet).
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

Tab = Literal["pinned", "discover"]
SortKey = Literal["pinned", "rank", "match", "followers", "avg_views", "growth", "name"]
KOL_SORT_QUERY_KEYS = frozenset({"pinned", "rank", "match", "followers", "avg_views", "growth", "name"})

# Discovery gate. The channel-formula screen separately gates pattern
# rendering at CLAIM_TIERS["pattern_spread"]=10, but with the current
# corpus density (~46K rows / 18 niches → most starter_creators carry
# 1-2 indexed videos) using the same 10 here filters every row out and
# /kol shows a blank state. Decoupled from the formula gate: surface
# any starter_creator with at least one indexed video; the channel
# screen still shows ``thin_corpus`` for under-10 handles, which is
# better than an empty discovery list.
MIN_INDEXED_VIDEOS_FOR_DISCOVERY = 1

# D.1.3 — cache TTL for creator_velocity.match_score. Beyond this window
# we recompute + writeback; the profile-change trigger invalidates earlier.
MATCH_SCORE_TTL = timedelta(days=7)

_log = logging.getLogger(__name__)


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


def _apply_follower_bounds(
    rows: list[dict[str, Any]],
    followers_min: int | None,
    followers_max: int | None,
) -> list[dict[str, Any]]:
    if followers_min is None and followers_max is None:
        return rows
    out: list[dict[str, Any]] = []
    for r in rows:
        f = int(r.get("followers") or 0)
        if followers_min is not None and f < int(followers_min):
            continue
        if followers_max is not None and f > int(followers_max):
            continue
        out.append(r)
    return out


def _apply_growth_fast_proxy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """No growth_30d in starter_creators yet — keep top ~third by avg_views in pool."""
    if len(rows) <= 2:
        return rows
    avs = sorted(float(r.get("avg_views") or 0) for r in rows)
    n = len(avs)
    cut_i = min(n - 1, max(0, int(math.floor(0.66 * (n - 1)))))
    cutoff = avs[cut_i]
    return [r for r in rows if float(r.get("avg_views") or 0) >= cutoff]


def _growth_display_pct_proxy(avg_views: float, niche_avg_views: list[float]) -> float:
    """Proxy momentum for TĂNG 30D when no real view-velocity row exists.

    Re-shapes the niche-wide avg_views percentile into a ±22% band. This
    is the D.1.5 fallback — used when ``view_velocity_30d_pct`` is NULL
    (e.g. new creators with < 2 corpus videos per window) or stale
    (> ``VIEW_VELOCITY_TTL`` old).
    """
    gp = growth_percentile_from_avgs(avg_views, niche_avg_views)
    return round((gp - 0.5) * 0.44, 4)


# D.1.5 — real 30d view velocity freshness. Past this window we prefer the
# avg-views proxy over a stale column read; `[kol-growth]` log attributes
# the decision so D.5.1 can surface the mix of real vs proxy reads.
VIEW_VELOCITY_TTL = timedelta(days=7)


def _resolve_growth_display_pct(
    *,
    handle: str,
    avg_views: float,
    niche_avg_views: list[float],
    cached_view_velocity: tuple[float, datetime | None] | None,
    now: datetime,
) -> float:
    """D.1.5 — Real view-velocity first, proxy fallback. Logs the choice."""
    if cached_view_velocity is not None:
        value, ts = cached_view_velocity
        if ts is not None and (now - ts) < VIEW_VELOCITY_TTL:
            _log.info("[kol-growth] handle=%s source=real value=%.4f", handle, value)
            return round(float(value), 4)
        _log.info(
            "[kol-growth] handle=%s source=proxy reason=stale_view_velocity age_days=%s",
            handle,
            int((now - ts).total_seconds() / 86400) if ts else "n/a",
        )
    else:
        _log.info("[kol-growth] handle=%s source=proxy reason=missing_view_velocity", handle)
    return _growth_display_pct_proxy(avg_views, niche_avg_views)




def _sort_decorated_rows(
    rows: list[dict[str, Any]],
    *,
    sort: SortKey,
    desc: bool,
    pinned_handles_order: list[str] | None,
) -> None:
    """In-place sort of API-shaped rows (already decorated)."""
    if sort == "rank":
        return
    if sort == "pinned" and pinned_handles_order:
        rank = {h: i for i, h in enumerate(pinned_handles_order)}
        rows.sort(key=lambda r: rank.get(str(r.get("handle") or ""), 9999), reverse=desc)
        return
    key_fn: dict[str, Any] = {
        "match": lambda r: int(r.get("match_score") or 0),
        "followers": lambda r: int(r.get("followers") or 0),
        "avg_views": lambda r: int(r.get("avg_views") or 0),
        "growth": lambda r: float(r.get("growth_30d_pct") or 0.0),
        "name": lambda r: str(r.get("name") or "").lower(),
    }
    fn = key_fn.get(sort, key_fn["match"])
    rows.sort(key=fn, reverse=desc)


def _filter_decorated_by_search(rows: list[dict[str, Any]], search: str | None) -> list[dict[str, Any]]:
    """Substring match on handle or display name (post-decorate, pre-sort / pre-page)."""
    if not search:
        return rows
    q = search.strip().lower().lstrip("@")
    if not q:
        return rows
    out: list[dict[str, Any]] = []
    for r in rows:
        h = str(r.get("handle") or "").lower()
        n = str(r.get("name") or "").lower()
        if q in h or q in n:
            out.append(r)
    return out


def _match_description_sentence(score: int, niche_label: str) -> str:
    label = (niche_label or "").strip() or "ngách của bạn"
    if score >= 78:
        return (
            f"Cùng audience overlap, khác giọng — bổ sung tốt cho catalog của bạn "
            f"trong {label} (điểm khớp {score}/100)."
        )
    if score >= 55:
        return (
            f"Khớp tốt với {label} — có thể mở rộng tầng viewer hoặc format quen thuộc "
            f"({score}/100)."
        )
    return f"Mức khớp vừa phải với {label} — tham khảo tone hoặc hook khác biệt ({score}/100)."


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


def _parse_computed_at(raw: Any) -> datetime | None:
    """Accept the TIMESTAMPTZ shapes Supabase returns (ISO strings or datetime)."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    try:
        txt = str(raw).strip()
        if not txt:
            return None
        if txt.endswith("Z"):
            txt = txt[:-1] + "+00:00"
        dt = datetime.fromisoformat(txt)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:  # pragma: no cover — defensive
        return None


def _is_fresh(computed_at: datetime | None, *, now: datetime | None = None) -> bool:
    """True when `computed_at` is within MATCH_SCORE_TTL of `now`."""
    if computed_at is None:
        return False
    current = now or datetime.now(tz=timezone.utc)
    return (current - computed_at) < MATCH_SCORE_TTL


def _fetch_creator_velocity_cache(
    sb: Any, *, niche_id: int
) -> tuple[
    dict[str, tuple[int, datetime | None]],
    dict[str, tuple[float, datetime | None]],
]:
    """Single-round-trip read of both cache columns on ``creator_velocity``.

    D.1 patch: folds the former ``_fetch_cached_match_scores`` (D.1.3) and
    ``_fetch_view_velocity_map`` (D.1.5) into one SELECT so /kol/browse
    issues one DB round-trip for the niche instead of two.

    Returns ``(match_score_map, view_velocity_map)``. Rows with a NULL
    column are absent from the respective map but may still appear in the
    other — a creator with ``match_score`` populated but ``view_velocity``
    still NULL (or vice versa) is a common transient state after either
    cache is invalidated.
    """
    try:
        res = (
            sb.table("creator_velocity")
            .select(
                "creator_handle, match_score, match_score_computed_at, "
                "view_velocity_30d_pct, view_velocity_computed_at"
            )
            .eq("niche_id", niche_id)
            .execute()
        )
    except Exception as exc:  # pragma: no cover — defensive
        _log.warning("[kol-browse] creator_velocity cache read failed: %s", exc)
        return {}, {}

    score_map: dict[str, tuple[int, datetime | None]] = {}
    velocity_map: dict[str, tuple[float, datetime | None]] = {}
    for row in res.data or []:
        handle = normalize_handle(str(row.get("creator_handle") or ""))
        if not handle:
            continue
        raw_score = row.get("match_score")
        if raw_score is not None:
            ts = _parse_computed_at(row.get("match_score_computed_at"))
            score_map[handle] = (int(raw_score), ts)
        raw_velocity = row.get("view_velocity_30d_pct")
        if raw_velocity is not None:
            ts = _parse_computed_at(row.get("view_velocity_computed_at"))
            velocity_map[handle] = (float(raw_velocity), ts)
    return score_map, velocity_map


def _writeback_match_scores(
    sb: Any,
    *,
    niche_id: int,
    scores: dict[str, int],
    now: datetime | None = None,
) -> None:
    """UPDATE creator_velocity rows with freshly computed match scores. Misses are skipped."""
    if not scores:
        return
    ts = (now or datetime.now(tz=timezone.utc)).isoformat()
    for handle, score in scores.items():
        if not handle:
            continue
        try:
            (
                sb.table("creator_velocity")
                .update({"match_score": int(score), "match_score_computed_at": ts})
                .eq("creator_handle", handle)
                .eq("niche_id", niche_id)
                .execute()
            )
        except Exception as exc:  # pragma: no cover — defensive
            _log.warning("[kol-match-persist] cache write failed handle=%s: %s", handle, exc)


def run_kol_browse_sync(
    user_sb: Any,
    *,
    niche_id: int,
    tab: Tab,
    page: int,
    page_size: int,
    followers_min: int | None = None,
    followers_max: int | None = None,
    growth_fast: bool = False,
    sort: str | None = None,
    sort_desc: bool | None = None,
    search: str | None = None,
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

    # D.1.3 — cache read. `recomputed` tracks rows that need a writeback
    # UPDATE on creator_velocity after decoration (TTL miss / null cache).
    cached_scores, cached_velocities = _fetch_creator_velocity_cache(user_sb, niche_id=niche_id)
    recomputed: dict[str, int] = {}
    _now = datetime.now(tz=timezone.utc)

    def decorate(row: dict[str, Any]) -> dict[str, Any]:
        h = normalize_handle(str(row.get("handle") or ""))
        cid = niche_id
        cf = int(row.get("followers") or 0)
        av = float(row.get("avg_views") or 0)
        cache_hit = cached_scores.get(h)
        if cache_hit is not None and _is_fresh(cache_hit[1], now=_now):
            score = int(cache_hit[0])
        else:
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
            if h:
                recomputed[h] = score
        name = row.get("display_name") or h
        md = _match_description_sentence(score, niche_label)
        g_pct = _resolve_growth_display_pct(
            handle=h,
            avg_views=av,
            niche_avg_views=niche_avg_views,
            cached_view_velocity=cached_velocities.get(h),
            now=_now,
        )
        return {
            "handle": h,
            "name": name,
            "niche_label": niche_label or None,
            "followers": cf,
            "avg_views": int(round(av)),
            "growth_30d_pct": g_pct,
            "match_score": score,
            "is_pinned": h in pinned_set,
            "match_description": md,
        }

    if tab == "discover":
        pool: list[dict[str, Any]] = [dict(r) for r in starter_rows]
        # Surface any starter_creator with at least one indexed video.
        # The channel screen still shows ``thin_corpus`` if the user
        # clicks into a creator under the formula threshold — a degraded
        # but informative landing beats a fully empty discovery list.
        # Pinned channels skip this gate because the user explicitly
        # added them.
        pool = [r for r in pool if int(r.get("video_count") or 0) >= MIN_INDEXED_VIDEOS_FOR_DISCOVERY]
        pool = _apply_follower_bounds(pool, followers_min, followers_max)
        if growth_fast:
            pool = _apply_growth_fast_proxy(pool)
        decorated = [decorate(dict(r)) for r in pool]
        decorated = _filter_decorated_by_search(decorated, search)
        sk_disc: SortKey = sort if sort in (
            "rank",
            "match",
            "followers",
            "avg_views",
            "growth",
            "name",
        ) else "match"
        sd_disc = bool(sort_desc) if sort_desc is not None else True
        if sk_disc != "rank":
            _sort_decorated_rows(decorated, sort=sk_disc, desc=sd_disc, pinned_handles_order=None)
        total = len(decorated)
        start = (page - 1) * page_size
        rows = decorated[start : start + page_size]
        _writeback_match_scores(user_sb, niche_id=niche_id, scores=recomputed, now=_now)
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
    pool_pin: list[dict[str, Any]] = [dict(r) for r in ordered_rows]
    pool_pin = _apply_follower_bounds(pool_pin, followers_min, followers_max)
    if growth_fast:
        pool_pin = _apply_growth_fast_proxy(pool_pin)
    decorated_pin = [decorate(dict(r)) for r in pool_pin]
    decorated_pin = _filter_decorated_by_search(decorated_pin, search)
    sk_pin: SortKey = sort if sort in (
        "pinned",
        "rank",
        "match",
        "followers",
        "avg_views",
        "growth",
        "name",
    ) else "pinned"
    sd_pin = bool(sort_desc) if sort_desc is not None else False
    if sk_pin == "rank":
        pass
    elif sk_pin == "pinned":
        _sort_decorated_rows(
            decorated_pin,
            sort="pinned",
            desc=sd_pin,
            pinned_handles_order=handles_ordered,
        )
    else:
        _sort_decorated_rows(decorated_pin, sort=sk_pin, desc=sd_pin, pinned_handles_order=None)
    total = len(decorated_pin)
    start = (page - 1) * page_size
    rows = decorated_pin[start : start + page_size]
    _writeback_match_scores(user_sb, niche_id=niche_id, scores=recomputed, now=_now)
    return {
        "tab": tab,
        "niche_id": niche_id,
        "page": page,
        "page_size": page_size,
        "total": total,
        "reference_handles": reference_handles,
        "rows": rows,
    }
