"""Home-screen ticker aggregator — rolling items across five categories.

Feeds the design's marquee ticker ("BREAKOUT · HOOK MỚI · CẢNH BÁO · KOL NỔI
· ÂM THANH") at the top of the Home screen.

Five buckets, ≤ 2 items per bucket, all from the last 7 days. Order in the
final list is round-robin so the marquee feels mixed, not clumped. Every
item carries its bucket label + a short Vietnamese headline + a deep-link
payload the frontend can route on click.

Fails open: if any single bucket query errors, that bucket is omitted — the
ticker just shows fewer items rather than failing the whole request.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

logger = logging.getLogger(__name__)

TickerBucket = Literal["breakout", "hook_mới", "cảnh_báo", "kol_nổi", "âm_thanh"]


@dataclass(frozen=True)
class TickerItem:
    bucket: TickerBucket
    label_vi: str              # "BREAKOUT" etc — frontend renders with color per bucket
    headline_vi: str           # "3.2M views · @handle đẩy hook mới"
    target_kind: str           # "video" | "creator" | "pattern" | "sound" | "none"
    target_id: str | None      # video_id, handle, pattern_id, sound_id, or None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


_BUCKET_LABELS: dict[TickerBucket, str] = {
    "breakout":   "BREAKOUT",
    "hook_mới":   "HOOK MỚI",
    "cảnh_báo":   "CẢNH BÁO",
    "kol_nổi":    "KOL NỔI",
    "âm_thanh":   "ÂM THANH",
}

MIN_PATTERN_VIDEOS_7D = 1
_BREAKOUT_MULTIPLIER_FLOOR = 2.0


def _apply_corpus_niche_scope(q: Any, client: Any, niche_id: int) -> Any:
    """Class-first corpus filter when junction exists; else legacy ingest niche."""
    from getviews_pipeline.profile_niches import content_class_ids_for_legacy_niche

    class_ids = content_class_ids_for_legacy_niche(client, niche_id)
    if class_ids:
        return q.in_("content_class_id", class_ids)
    return q.eq("ingest_loop_niche_id", niche_id)


def _pattern_niche_counts_7d(
    client: Any,
    niche_id: int,
    pattern_ids: list[str],
    since: str,
) -> dict[str, int]:
    """Live 7d counts — ``weekly_instance_count`` is cron-maintained and often 0."""
    if not pattern_ids:
        return {}
    try:
        q = (
            client.table("video_corpus")
            .select("pattern_id")
            .gte("indexed_at", since)
            .in_("pattern_id", pattern_ids)
        )
        q = _apply_corpus_niche_scope(q, client, niche_id)
        rows = q.execute().data or []
    except Exception as exc:
        logger.warning("[ticker] pattern counts failed niche=%s: %s", niche_id, exc)
        return {}
    counts: Counter[str] = Counter()
    for r in rows:
        pid = r.get("pattern_id")
        if pid:
            counts[str(pid)] += 1
    return dict(counts)


def _fmt_views(views: int) -> str:
    if views >= 1_000_000:
        n = f"{views / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{n}M"
    if views >= 1_000:
        return f"{views // 1_000}K"
    return str(views)


def _dedupe_ticker_items(items: list[TickerItem]) -> list[TickerItem]:
    seen: set[tuple[str, str | None]] = set()
    out: list[TickerItem] = []
    for it in items:
        key = (it.bucket, it.target_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _interleave_buckets(buckets: list[list[TickerItem]]) -> list[TickerItem]:
    out: list[TickerItem] = []
    i = 0
    while any(len(b) > i for b in buckets):
        for b in buckets:
            if len(b) > i:
                out.append(b[i])
        i += 1
    return out


def _append_unique(out: list[TickerItem], seen: set[tuple[str, str | None]], items: list[TickerItem]) -> None:
    for item in items:
        key = (item.bucket, item.target_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)


def _niche_pulse_summary_items(client: Any, niche_id: int) -> list[TickerItem]:
    """Real niche-week stats when hook/breakout buckets are thin (same source as PulseCard)."""
    from getviews_pipeline.pulse import _compute_pulse_sync

    try:
        stats = _compute_pulse_sync(client, niche_id)
    except Exception as exc:
        logger.warning("[ticker] pulse summary failed niche=%s: %s", niche_id, exc)
        return []

    out: list[TickerItem] = []
    if stats.videos_this_week >= 1:
        out.append(TickerItem(
            bucket="breakout",
            label_vi="TUẦN NÀY",
            headline_vi=(
                f"{stats.videos_this_week} video mới · "
                f"{_fmt_views(stats.views_this_week)} views trong ngách"
            ),
            target_kind="none",
            target_id="pulse:videos",
        ))
    if stats.viral_count_this_week >= 1:
        out.append(TickerItem(
            bucket="breakout",
            label_vi=_BUCKET_LABELS["breakout"],
            headline_vi=f"{stats.viral_count_this_week} video ≥3× trung bình kênh tuần này",
            target_kind="none",
            target_id="pulse:viral",
        ))
    if stats.top_hook_name:
        out.append(TickerItem(
            bucket="hook_mới",
            label_vi=_BUCKET_LABELS["hook_mới"],
            headline_vi=f'"{stats.top_hook_name}" · hook dẫn view tuần này',
            target_kind="none",
            target_id="pulse:top_hook",
        ))
    if stats.views_last_week > 0 and stats.views_delta_pct != 0:
        sign = "+" if stats.views_delta_pct > 0 else ""
        label = _BUCKET_LABELS["breakout"] if stats.views_delta_pct >= 0 else _BUCKET_LABELS["cảnh_báo"]
        out.append(TickerItem(
            bucket="breakout" if stats.views_delta_pct >= 0 else "cảnh_báo",
            label_vi=label,
            headline_vi=f"View ngách {sign}{stats.views_delta_pct:.0f}% so với tuần trước",
            target_kind="none",
            target_id="pulse:views_delta",
        ))
    return out


async def compute_ticker(client: Any, niche_id: int) -> list[TickerItem]:
    """Run bucket queries in parallel; interleave; pad with pulse/hot views when thin."""
    loop = asyncio.get_running_loop()
    since = (datetime.now(UTC) - timedelta(days=7)).isoformat()

    tasks = [
        loop.run_in_executor(None, _breakout_items, client, niche_id, since),
        loop.run_in_executor(None, _new_hook_items, client, niche_id, since),
        loop.run_in_executor(None, _active_pattern_items, client, niche_id, since),
        loop.run_in_executor(None, _caution_items, client, niche_id, since),
        loop.run_in_executor(None, _sound_items, client, niche_id, since),
    ]
    bucket_results = await asyncio.gather(*tasks, return_exceptions=True)

    buckets: list[list[TickerItem]] = []
    for res in bucket_results:
        if isinstance(res, Exception):
            logger.warning("[ticker] bucket failed: %s", res)
            buckets.append([])
        else:
            buckets.append(list(res))

    out = _dedupe_ticker_items(_interleave_buckets(buckets))
    seen = {(it.bucket, it.target_id) for it in out}
    _append_unique(out, seen, _hot_views_items(client, niche_id, since))
    _append_unique(out, seen, _niche_pulse_summary_items(client, niche_id))
    return out


# ── bucket queries ─────────────────────────────────────────────────────────

def _corpus_7d_query(client: Any, niche_id: int, since: str, select: str) -> Any:
    q = client.table("video_corpus").select(select).gte("indexed_at", since)
    return _apply_corpus_niche_scope(q, client, niche_id)


def _breakout_rows(
    client: Any,
    niche_id: int,
    since: str,
    *,
    eligible_only: bool,
) -> list[dict[str, Any]]:
    q = _corpus_7d_query(
        client,
        niche_id,
        since,
        "video_id, creator_handle, views, breakout_multiplier, reference_eligible",
    ).not_.is_("breakout_multiplier", None)
    if eligible_only:
        q = q.eq("reference_eligible", True)
    return q.order("breakout_multiplier", desc=True).limit(2).execute().data or []


def _breakout_items(client: Any, niche_id: int, since: str) -> list[TickerItem]:
    """Top 2 videos by breakout_multiplier ingested in the last 7d."""
    rows = _breakout_rows(client, niche_id, since, eligible_only=True)
    if len(rows) < 2:
        seen = {r.get("video_id") for r in rows}
        for r in _breakout_rows(client, niche_id, since, eligible_only=False):
            vid = r.get("video_id")
            if vid in seen:
                continue
            seen.add(vid)
            rows.append(r)
            if len(rows) >= 2:
                break
    out: list[TickerItem] = []
    for r in rows:
        bm = float(r.get("breakout_multiplier") or 0)
        if bm < _BREAKOUT_MULTIPLIER_FLOOR:
            continue
        handle = (r.get("creator_handle") or "").strip() or "creator"
        out.append(TickerItem(
            bucket="breakout",
            label_vi=_BUCKET_LABELS["breakout"],
            headline_vi=(
                f"@{handle} · "
                f"{_fmt_views(int(r.get('views') or 0))} views · "
                f"{bm:.1f}× trung bình kênh"
            ),
            target_kind="video",
            target_id=r.get("video_id"),
        ))
    return out


def _hot_views_items(client: Any, niche_id: int, since: str) -> list[TickerItem]:
    """Backfill when breakout/hook buckets are thin — top viewed in-scope videos (7d)."""
    try:
        rows = (
            _corpus_7d_query(
                client,
                niche_id,
                since,
                "video_id, creator_handle, views, breakout_multiplier",
            )
            .order("views", desc=True)
            .limit(4)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[ticker] hot_views failed niche=%s: %s", niche_id, exc)
        return []
    out: list[TickerItem] = []
    for r in rows:
        views = int(r.get("views") or 0)
        if views < 1:
            continue
        handle = (r.get("creator_handle") or "").strip() or "creator"
        bm = float(r.get("breakout_multiplier") or 0)
        if bm >= _BREAKOUT_MULTIPLIER_FLOOR:
            headline = (
                f"@{handle} · {_fmt_views(views)} views · "
                f"{bm:.1f}× trung bình kênh"
            )
        else:
            headline = f"@{handle} · {_fmt_views(views)} views · tuần này"
        out.append(TickerItem(
            bucket="breakout",
            label_vi=_BUCKET_LABELS["breakout"],
            headline_vi=headline,
            target_kind="video",
            target_id=r.get("video_id"),
        ))
        if len(out) >= 2:
            break
    return out


def _new_hook_items(client: Any, niche_id: int, since: str) -> list[TickerItem]:
    """Top 2 patterns that entered the niche's spread this week."""
    rows = (
        client.table("video_patterns")
        .select("id, display_name, niche_spread, weekly_instance_count, first_seen_at, is_active")
        .eq("is_active", True)
        .gte("first_seen_at", since)
        .order("weekly_instance_count", desc=True)
        .limit(24)
        .execute()
        .data or []
    )
    candidates: list[dict[str, Any]] = []
    for p in rows:
        if niche_id not in (p.get("niche_spread") or []):
            continue
        candidates.append(p)
    if not candidates:
        return []

    live_counts = _pattern_niche_counts_7d(
        client,
        niche_id,
        [str(p.get("id")) for p in candidates if p.get("id")],
        since,
    )

    def _week_count(p: dict[str, Any]) -> int:
        pid = str(p.get("id") or "")
        stored = int(p.get("weekly_instance_count") or 0)
        live = int(live_counts.get(pid, 0))
        return max(stored, live)

    ranked = sorted(candidates, key=_week_count, reverse=True)
    out: list[TickerItem] = []
    for p in ranked:
        count = _week_count(p)
        if count < MIN_PATTERN_VIDEOS_7D:
            continue
        name = (p.get("display_name") or "Pattern").strip()
        out.append(TickerItem(
            bucket="hook_mới",
            label_vi=_BUCKET_LABELS["hook_mới"],
            headline_vi=f'"{name}" · {count} video tuần này',
            target_kind="pattern",
            target_id=p.get("id"),
        ))
        if len(out) >= 2:
            break
    return out


def _active_pattern_items(client: Any, niche_id: int, since: str) -> list[TickerItem]:
    """Patterns with real 7d volume in the niche (not only ``first_seen_at`` this week)."""
    rows = (
        client.table("video_patterns")
        .select("id, display_name, niche_spread, weekly_instance_count, is_active")
        .eq("is_active", True)
        .order("weekly_instance_count", desc=True)
        .limit(40)
        .execute()
        .data or []
    )
    candidates: list[dict[str, Any]] = []
    for p in rows:
        if niche_id not in (p.get("niche_spread") or []):
            continue
        candidates.append(p)
    if not candidates:
        return []

    live_counts = _pattern_niche_counts_7d(
        client,
        niche_id,
        [str(p.get("id")) for p in candidates if p.get("id")],
        since,
    )
    ranked = sorted(
        candidates,
        key=lambda p: int(live_counts.get(str(p.get("id") or ""), 0)),
        reverse=True,
    )
    out: list[TickerItem] = []
    for p in ranked:
        count = int(live_counts.get(str(p.get("id") or ""), 0))
        if count < MIN_PATTERN_VIDEOS_7D:
            continue
        name = (p.get("display_name") or "Pattern").strip()
        out.append(TickerItem(
            bucket="hook_mới",
            label_vi=_BUCKET_LABELS["hook_mới"],
            headline_vi=f'"{name}" · {count} video đang chạy trong ngách',
            target_kind="pattern",
            target_id=p.get("id"),
        ))
        if len(out) >= 2:
            break
    return out


def _caution_items(client: Any, niche_id: int, since: str) -> list[TickerItem]:
    """Patterns cooling off fast — weekly count dropped ≥ 40% week-on-week."""
    rows = (
        client.table("video_patterns")
        .select("id, display_name, niche_spread, weekly_instance_count, weekly_instance_count_prev, is_active")
        .eq("is_active", True)
        .execute()
        .data or []
    )
    out: list[TickerItem] = []
    for p in rows:
        if niche_id not in (p.get("niche_spread") or []):
            continue
        prev = int(p.get("weekly_instance_count_prev") or 0)
        now_ = int(p.get("weekly_instance_count") or 0)
        if prev < 10:  # below pattern_spread tier — not a cooling signal, just noise
            continue
        if now_ >= prev * 0.6:
            continue
        drop_pct = int((1 - now_ / prev) * 100)
        name = (p.get("display_name") or "Pattern").strip()
        out.append(TickerItem(
            bucket="cảnh_báo",
            label_vi=_BUCKET_LABELS["cảnh_báo"],
            headline_vi=f'"{name}" · giảm {drop_pct}% tuần này',
            target_kind="pattern",
            target_id=p.get("id"),
        ))
        if len(out) >= 2:
            break
    return out


def _rising_kol_items(client: Any, niche_id: int, since: str) -> list[TickerItem]:
    """Creators whose new-video view totals this week look outsized."""
    try:
        rows = (
            _corpus_7d_query(
                client,
                niche_id,
                since,
                "creator_handle, views, creator_followers, breakout_multiplier",
            )
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[ticker] rising_kol failed niche=%s: %s", niche_id, exc)
        return []
    by_handle: dict[str, dict[str, float]] = {}
    for r in rows:
        h = (r.get("creator_handle") or "").strip()
        if not h:
            continue
        agg = by_handle.setdefault(h, {
            "total_views": 0.0, "videos": 0.0,
            "followers": float(r.get("creator_followers") or 0),
            "max_bm": 0.0,
        })
        agg["total_views"] += float(r.get("views") or 0)
        agg["videos"] += 1
        bm = float(r.get("breakout_multiplier") or 0)
        if bm > agg["max_bm"]:
            agg["max_bm"] = bm
    # Rank by max breakout_multiplier; break ties by total_views.
    ranked = sorted(
        by_handle.items(),
        key=lambda kv: (kv[1]["max_bm"], kv[1]["total_views"]),
        reverse=True,
    )
    out: list[TickerItem] = []
    for handle, agg in ranked:
        if agg["max_bm"] < 2.0 or agg["videos"] < 1:
            continue
        out.append(TickerItem(
            bucket="kol_nổi",
            label_vi=_BUCKET_LABELS["kol_nổi"],
            headline_vi=(
                f"@{handle} · {int(agg['videos'])} video mới · "
                f"đỉnh {agg['max_bm']:.1f}×"
            ),
            target_kind="creator",
            target_id=handle,
        ))
        if len(out) >= 2:
            break
    return out


def _sound_items(client: Any, niche_id: int, since: str) -> list[TickerItem]:
    """Top 2 sounds trending in this niche this week (class-scoped ``trending_sounds``)."""
    from getviews_pipeline.profile_niches import content_class_ids_for_legacy_niche

    class_ids = content_class_ids_for_legacy_niche(client, niche_id)
    if not class_ids:
        return []

    rows = (
        client.table("trending_sounds")
        .select("sound_id, sound_name, usage_count, total_views, week_of")
        .in_("content_class_id", class_ids)
        .order("week_of", desc=True)
        .order("usage_count", desc=True)
        .limit(12)
        .execute()
        .data or []
    )
    out: list[TickerItem] = []
    seen_week: str | None = None
    for r in rows:
        wk = r.get("week_of")
        if seen_week and wk != seen_week:
            break  # only take items from the latest week_of
        seen_week = wk
        name = (r.get("sound_name") or "").strip() or "sound"
        views = int(r.get("total_views") or 0)
        out.append(TickerItem(
            bucket="âm_thanh",
            label_vi=_BUCKET_LABELS["âm_thanh"],
            headline_vi=f'"{name}" · {_fmt_views(views)} views tuần này',
            target_kind="sound",
            target_id=r.get("sound_id"),
        ))
        if len(out) >= 2:
            break
    return out


__all__ = ["TickerItem", "TickerBucket", "compute_ticker"]
