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
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
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


def _fmt_views(views: int) -> str:
    if views >= 1_000_000:
        n = f"{views / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{n}M"
    if views >= 1_000:
        return f"{views // 1_000}K"
    return str(views)


async def compute_ticker(client: Any, niche_id: int) -> list[TickerItem]:
    """Run all five bucket queries in parallel; interleave into one list."""
    loop = asyncio.get_running_loop()
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    tasks = [
        loop.run_in_executor(None, _breakout_items,   client, niche_id, since),
        loop.run_in_executor(None, _new_hook_items,   client, niche_id, since),
        loop.run_in_executor(None, _caution_items,    client, niche_id, since),
        loop.run_in_executor(None, _rising_kol_items, client, niche_id, since),
        loop.run_in_executor(None, _sound_items,      client, niche_id, since),
    ]
    bucket_results = await asyncio.gather(*tasks, return_exceptions=True)

    buckets: list[list[TickerItem]] = []
    for res in bucket_results:
        if isinstance(res, Exception):
            logger.warning("[ticker] bucket failed: %s", res)
            buckets.append([])
        else:
            buckets.append(list(res))

    # Round-robin interleave so the marquee reads mixed.
    out: list[TickerItem] = []
    i = 0
    while any(b[i:] for b in buckets if len(b) > i):
        for b in buckets:
            if len(b) > i:
                out.append(b[i])
        i += 1
    return out


# ── bucket queries ─────────────────────────────────────────────────────────

def _breakout_items(client: Any, niche_id: int, since: str) -> list[TickerItem]:
    """Top 2 videos by breakout_multiplier ingested in the last 7d."""
    rows = (
        client.table("video_corpus")
        .select("video_id, creator_handle, views, breakout_multiplier")
        .eq("niche_id", niche_id)
        .gte("created_at", since)
        .not_.is_("breakout_multiplier", None)
        .order("breakout_multiplier", desc=True)
        .limit(2)
        .execute()
        .data or []
    )
    out: list[TickerItem] = []
    for r in rows:
        bm = float(r.get("breakout_multiplier") or 0)
        if bm < 2.0:
            continue
        out.append(TickerItem(
            bucket="breakout",
            label_vi=_BUCKET_LABELS["breakout"],
            headline_vi=(
                f"@{r.get('creator_handle', '')} · "
                f"{_fmt_views(int(r.get('views') or 0))} views · "
                f"{bm:.1f}× trung bình kênh"
            ),
            target_kind="video",
            target_id=r.get("video_id"),
        ))
    return out


def _new_hook_items(client: Any, niche_id: int, since: str) -> list[TickerItem]:
    """Top 2 patterns that entered the niche's spread this week."""
    rows = (
        client.table("video_patterns")
        .select("id, display_name, niche_spread, weekly_instance_count, first_seen_at, is_active")
        .eq("is_active", True)
        .gte("first_seen_at", since)
        .order("weekly_instance_count", desc=True)
        .limit(10)
        .execute()
        .data or []
    )
    out: list[TickerItem] = []
    for p in rows:
        if niche_id not in (p.get("niche_spread") or []):
            continue
        count = int(p.get("weekly_instance_count") or 0)
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
    rows = (
        client.table("video_corpus")
        .select("creator_handle, views, creator_followers, breakout_multiplier")
        .eq("niche_id", niche_id)
        .gte("created_at", since)
        .execute()
        .data or []
    )
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
    """Top 2 sounds trending in this niche this week.

    trending_sounds is computed weekly; pick the most recent week_of entry
    covering this niche.
    """
    # Pull the most recent week_of entries. trending_sounds stores usage_count
    # + total_views per (niche, sound, week_of). Order by usage.
    rows = (
        client.table("trending_sounds")
        .select("sound_id, sound_name, usage_count, total_views, week_of")
        .eq("niche_id", niche_id)
        .order("week_of", desc=True)
        .order("usage_count", desc=True)
        .limit(4)
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
