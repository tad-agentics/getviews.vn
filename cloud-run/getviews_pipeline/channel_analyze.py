"""B.3.1 — GET /channel/analyze: claim-tier gate, channel_formulas cache, Gemini, credits.

Thin corpus (< ``CLAIM_TIERS['pattern_spread']`` videos in ``video_corpus`` for the
handle × niche) returns ``formula_gate: thin_corpus`` — no Gemini, no credit.

Fresh cache (< 7 days) returns cached row — no Gemini, no credit.

Otherwise: ``decrement_credit`` then Gemini (formula + lessons + bio) then service upsert.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from getviews_pipeline.claim_tiers import CLAIM_TIERS
from getviews_pipeline.kol_browse import normalize_handle
from getviews_pipeline.video_structural import video_duration_sec

logger = logging.getLogger(__name__)

CHANNEL_FORMULA_STALE_AFTER = timedelta(days=7)
CORPUS_GATE_MIN = CLAIM_TIERS["pattern_spread"]
TOP_VIDEO_TILE_COLORS = (
    "#D9EB9A",
    "#E8E4DC",
    "#C5F0E8",
    "#F5E6C8",
)


@dataclass
class LiveSignals:
    """B.3.2 — deterministic KPI + posting signals from ``video_corpus`` (created_at + ER)."""

    posting_cadence: str = ""
    posting_time: str = ""
    views_mom_delta: str = "—"
    reach_lift_delta: str = "—"
    optimal_band: str = "—"
    duration_sample_n: int = 0
    # D.1.4 — 7×8 video-count matrix keyed by (weekday=Mon..Sun, hour-bucket).
    # Empty list means "insufficient temporal data" — frontend hides the panel.
    posting_heatmap: list[list[int]] = field(default_factory=list)
    # Studio Home pulse (PR-1) — consecutive recent days with ≥1 post,
    # backed by the same 14-day rolling window as the design's pulse hero.
    streak_days: int = 0
    streak_window_days: int = 14
    # Studio Home cadence (PR-3) — typed shape backing the design's
    # CadenceCalendar block:
    #   { posts_14d: bool[14], weekly_actual, weekly_target,
    #     best_hour: "20:00–22:00", best_days: "T7, CN" }
    # ``None`` when there's insufficient temporal data to render the
    # block; FE hides the cadence section in that case.
    cadence: dict[str, Any] | None = None


class InsufficientCreditsError(Exception):
    """``decrement_credit`` returned false or raised."""


class ChannelFormulaStepLLM(BaseModel):
    step: str = Field(max_length=40)
    detail: str = Field(max_length=220)
    pct: int = Field(ge=4, le=92)


class ChannelLessonLLM(BaseModel):
    """Legacy lesson shape — kept for the cache-bridge path that synthesizes
    a ``lessons[]`` array from strengths so pre-PR-2 FE surfaces (channel
    screen InsightsFooter) keep rendering. Not emitted by Gemini anymore."""

    title: str = Field(max_length=120)
    body: str = Field(max_length=800)


# ── PR-2 Studio Home — diagnostic restructure ──────────────────────────────
#
# Replaces the freeform ``lessons`` array with typed strengths +
# weaknesses per the design pack's MyChannelCard §C/§D. Each item carries
# enough structure to render the design's diagnostic block:
#   • title    — the headline (e.g. "Hook bám trend đang lên")
#   • metric   — quantified evidence (e.g. "Retention 0.8s · ngách TB 1.2s")
#   • why      — why this is a strength / weakness (1-2 sentences)
#   • action   — TẬN DỤNG (strength) / CÁCH SỬA (weakness)
#   • bridge_to — optional anchor: "01" (Quay ngay) or "02" (Pattern)


_BRIDGE_VALUES = ("01", "02")


class ChannelStrengthLLM(BaseModel):
    title: str = Field(max_length=120)
    metric: str = Field(max_length=120)
    why: str = Field(max_length=320)
    action: str = Field(max_length=320, description="TẬN DỤNG — cách phát huy điểm mạnh.")
    bridge_to: str | None = Field(
        default=None,
        description="Optional 2-char tier id ('01' or '02') — design's bridge button.",
    )


class ChannelWeaknessLLM(BaseModel):
    title: str = Field(max_length=120)
    metric: str = Field(max_length=120)
    why: str = Field(max_length=320)
    action: str = Field(max_length=320, description="CÁCH SỬA — cách khắc phục điểm yếu.")
    bridge_to: str | None = Field(
        default=None,
        description="Optional 2-char tier id ('01' or '02') — design's bridge button.",
    )


class ChannelAnalyzeLLM(BaseModel):
    bio: str = Field(max_length=320, description="Một câu tiếng Việt mô tả tone kênh.")
    formula: list[ChannelFormulaStepLLM] = Field(min_length=4, max_length=4)
    strengths: list[ChannelStrengthLLM] = Field(min_length=2, max_length=4)
    weaknesses: list[ChannelWeaknessLLM] = Field(min_length=1, max_length=3)


def _parse_ts(ts: Any) -> datetime | None:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        s = str(ts).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _cache_fresh(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    ct = _parse_ts(row.get("computed_at"))
    if not ct:
        return False
    return datetime.now(timezone.utc) - ct < CHANNEL_FORMULA_STALE_AFTER


def _fmt_int_short(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    return str(int(n))


def _normalize_formula_pcts(formula: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw = [max(4, min(92, int(x.get("pct") or 0))) for x in formula]
    s = sum(raw) or 1
    scaled = [max(4, round(p * 100 / s)) for p in raw]
    drift = 100 - sum(scaled)
    if drift != 0 and scaled:
        scaled[-1] = max(4, scaled[-1] + drift)
    out: list[dict[str, Any]] = []
    for i, x in enumerate(formula):
        d = dict(x)
        d["pct"] = scaled[i] if i < len(scaled) else 25
        out.append(d)
    return out


def _decrement_credit_or_raise(user_sb: Any, *, user_id: str) -> None:
    try:
        rpc_resp = user_sb.rpc("decrement_credit", {"p_user_id": user_id}).execute()
        if rpc_resp.data is False:
            raise InsufficientCreditsError()
    except InsufficientCreditsError:
        raise
    except Exception as exc:
        logger.warning("[channel_analyze] decrement_credit failed: %s", exc)
        raise InsufficientCreditsError() from exc


def _resolve_niche_label(user_sb: Any, niche_id: int) -> str:
    if not niche_id:
        return ""
    try:
        tres = (
            user_sb.table("niche_taxonomy")
            .select("name_vn,name_en")
            .eq("id", niche_id)
            .limit(1)
            .execute()
        )
        tr = (tres.data or [{}])[0]
        return str(tr.get("name_vn") or tr.get("name_en") or "")
    except Exception:
        return ""


def _fetch_starter_row(user_sb: Any, *, handle: str, niche_id: int) -> dict[str, Any] | None:
    try:
        res = (
            user_sb.table("starter_creators")
            .select("handle,display_name,followers,avg_views,video_count")
            .eq("niche_id", niche_id)
            .eq("handle", handle)
            .maybe_single()
            .execute()
        )
        return res.data
    except Exception:
        return None


def _fetch_corpus_stats_rpc(user_sb: Any, *, handle: str, niche_id: int) -> dict[str, Any]:
    try:
        res = user_sb.rpc("channel_corpus_stats", {"p_handle": handle, "p_niche": niche_id}).execute()
        data = res.data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            data = data[0]
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            return json.loads(data)
    except Exception as exc:
        logger.warning("[channel_analyze] channel_corpus_stats RPC failed: %s", exc)
    return {"total": 0, "avg_views": 0, "avg_er": 0.0}


def _fetch_niche_benchmarks(user_sb: Any, *, niche_id: int) -> dict[str, Any]:
    """Per-niche channel-level percentiles for the HomeMyChannelSection bars.

    Returns a flat dict matching the SQL row from
    ``niche_channel_benchmarks(p_niche_id)`` (see migration
    ``20260528000000_niche_channel_benchmarks_rpc.sql``). Falls back to
    a zeroed shape on failure so the FE can render the panel without
    the benchmark layer rather than crashing.
    """
    fallback = {
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
                "channel_count":       int(data.get("channel_count") or 0),
                "avg_views_p50":       int(data.get("avg_views_p50") or 0),
                "avg_views_p75":       int(data.get("avg_views_p75") or 0),
                "engagement_p50":      float(data.get("engagement_p50") or 0),
                "engagement_p75":      float(data.get("engagement_p75") or 0),
                "posts_per_week_p50":  float(data.get("posts_per_week_p50") or 0),
                "posts_per_week_p75":  float(data.get("posts_per_week_p75") or 0),
            }
    except Exception as exc:
        logger.warning("[channel_analyze] niche_channel_benchmarks RPC failed: %s", exc)
    return fallback


def _fetch_hook_types(user_sb: Any, *, handle: str, niche_id: int) -> list[str]:
    try:
        res = (
            user_sb.table("video_corpus")
            .select("hook_type")
            .ilike("creator_handle", handle)
            .eq("niche_id", niche_id)
            .limit(5000)
            .execute()
        )
        out: list[str] = []
        for row in res.data or []:
            ht = str(row.get("hook_type") or "").strip()
            if ht:
                out.append(ht)
        return out
    except Exception as exc:
        logger.warning("[channel_analyze] hook_type fetch failed: %s", exc)
        return []


def _fetch_top_corpus_rows(user_sb: Any, *, handle: str, niche_id: int, limit: int) -> list[dict[str, Any]]:
    try:
        res = (
            user_sb.table("video_corpus")
            .select(
                "video_id,views,engagement_rate,hook_type,hook_phrase,thumbnail_url,analysis_json,creator_followers"
            )
            .ilike("creator_handle", handle)
            .eq("niche_id", niche_id)
            .order("views", desc=True)
            .limit(limit)
            .execute()
        )
        return list(res.data or [])
    except Exception as exc:
        logger.warning("[channel_analyze] top corpus rows failed: %s", exc)
        return []


def _top_hook_from_types(types_list: list[str]) -> tuple[str, float]:
    if not types_list:
        return "—", 0.0
    c = Counter(types_list)
    top, n = c.most_common(1)[0]
    return top, round(100.0 * n / len(types_list), 1)


def _optimal_length_band_with_count(rows: list[dict[str, Any]]) -> tuple[str, int]:
    durs: list[float] = []
    for row in rows:
        aj = row.get("analysis_json")
        if isinstance(aj, str):
            try:
                aj = json.loads(aj)
            except json.JSONDecodeError:
                aj = {}
        if not isinstance(aj, dict):
            aj = {}
        d = video_duration_sec(aj)
        if d and d > 3:
            durs.append(float(d))
    if len(durs) < 3:
        return "—", 0
    durs.sort()
    n = len(durs)
    lo = durs[int(0.25 * (n - 1))]
    hi = durs[int(0.75 * (n - 1))]
    return f"{int(round(lo))}–{int(round(hi))}s", n


def _optimal_length_band(rows: list[dict[str, Any]]) -> str:
    s, _ = _optimal_length_band_with_count(rows)
    return s


def _median(nums: list[float]) -> float:
    if not nums:
        return 0.0
    s = sorted(nums)
    m = len(s) // 2
    if len(s) % 2:
        return float(s[m])
    return (float(s[m - 1]) + float(s[m])) / 2.0


def _parse_row_created_at(row: dict[str, Any]) -> datetime | None:
    return _parse_ts(row.get("created_at"))


def _fetch_temporal_corpus_rows(user_sb: Any, *, handle: str, niche_id: int, limit: int) -> list[dict[str, Any]]:
    try:
        res = (
            user_sb.table("video_corpus")
            # ``posted_at`` is the creator's actual publish date (PR-1 streak
            # uses it preferentially; existing cadence/MoM/heatmap helpers
            # keep reading ``created_at`` = our ingest time).
            .select("created_at,posted_at,views,engagement_rate")
            .ilike("creator_handle", handle)
            .eq("niche_id", niche_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(res.data or [])
    except Exception as exc:
        logger.warning("[channel_analyze] temporal corpus rows failed: %s", exc)
        return []


def _compute_posting_cadence_time_peak(rows: list[dict[str, Any]]) -> tuple[str, str, int | None]:
    """Peak (weekday, hour) by video count; cadence from posts/week heuristic."""
    parsed: list[tuple[datetime, dict[str, Any]]] = []
    for r in rows:
        dt = _parse_row_created_at(r)
        if dt:
            parsed.append((dt, r))
    if len(parsed) < 3:
        return "", "", None

    buckets: Counter[tuple[int, int]] = Counter()
    for dt, _ in parsed:
        buckets[(dt.weekday(), dt.hour)] += 1
    peak_wd, peak_hr = max(buckets, key=lambda k: buckets[k])

    days_span = max((parsed[0][0].date() - parsed[-1][0].date()).days, 1)
    weeks = max(days_span / 7.0, 0.25)
    per_week = len(parsed) / weeks
    if per_week >= 5.5:
        cad = "Hàng ngày"
    elif per_week >= 3.0:
        cad = "~4–5 lần/tuần"
    elif per_week >= 1.5:
        cad = f"~{max(2, int(round(per_week)))} lần/tuần"
    else:
        cad = f"~{max(1, int(round(per_week)))} lần/tuần"

    wd_short = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"][peak_wd]
    if 5 <= peak_hr < 12:
        slot = "sáng"
    elif peak_hr == 12:
        slot = "trưa"
    elif 12 < peak_hr < 18:
        slot = "chiều"
    elif 18 <= peak_hr < 22:
        slot = "tối"
    else:
        slot = "đêm"
    time_lbl = f"{peak_hr:02d}:00 {slot} · {wd_short}"
    return cad, time_lbl, peak_hr


# Studio Home cadence (PR-3) — design's NHỊP ĐĂNG block ────────────────────
#
# Renders a 14-day calendar of boolean post-or-skip cells + a Giờ vàng /
# Ngày vàng pair. Computed deterministically from temporal corpus rows;
# returns None when there isn't enough data to seed the calendar.

# Min temporal rows for the cadence struct to be useful.
_CADENCE_MIN_ROWS = 3
_CADENCE_WEEKDAY_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]  # Mon..Sun


def _format_best_hour_range(peak_hour: int | None) -> str:
    """Peak hour → "20:00–22:00" (2-hour window centred on the peak)."""
    if peak_hour is None:
        return ""
    start = peak_hour
    end = (peak_hour + 2) % 24
    return f"{start:02d}:00–{end:02d}:00"


def _format_best_days(weekday_counts: Counter[int], *, top_n: int = 2) -> str:
    """Top-N weekdays as Vietnamese short labels, comma-separated."""
    if not weekday_counts:
        return ""
    # Sort by count desc, breaking ties by weekday order so output is stable.
    ordered = sorted(
        weekday_counts.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )
    picks = [_CADENCE_WEEKDAY_VI[wd] for wd, _ in ordered[:top_n] if 0 <= wd < 7]
    return ", ".join(picks)


def _compute_cadence_struct(
    rows: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Build the typed cadence shape backing the design's CadenceCalendar.

    Output:
      ``{
          "posts_14d": list[bool],       # exactly 14 entries; index 0 = 13 days ago, index 13 = today
          "weekly_actual": int,           # posts in the last 7 days
          "weekly_target": int,           # rolling 30-60d posts/week (≥ weekly_actual)
          "best_hour": "20:00–22:00",
          "best_days": "T7, CN",
      }``

    Returns None when fewer than ``_CADENCE_MIN_ROWS`` parseable timestamps —
    same guard as ``_compute_posting_heatmap``.
    """
    parsed: list[datetime] = []
    for r in rows:
        dt = _parse_ts(r.get("posted_at")) or _parse_row_created_at(r)
        if dt is None:
            continue
        parsed.append(dt.astimezone(timezone.utc))
    if len(parsed) < _CADENCE_MIN_ROWS:
        return None

    today = (now or datetime.now(timezone.utc)).date()

    # 14-day boolean grid (today − 13 ... today).
    days_with_post: set[date] = {dt.date() for dt in parsed}
    posts_14d = [(today - timedelta(days=13 - i)) in days_with_post for i in range(14)]
    weekly_actual = sum(1 for b in posts_14d[-7:] if b)

    # weekly_target: derive from the wider window's posts/week (capped at
    # design's daily cap of 7). Always ≥ weekly_actual so the FE pill
    # never reads "8/5 tuần này".
    cutoff_30 = today - timedelta(days=30)
    in_window = [dt for dt in parsed if dt.date() >= cutoff_30]
    if in_window:
        unique_days = len({dt.date() for dt in in_window})
        # Posts/week heuristic from unique-days-with-post over the 30-day
        # window — matches the design's "weekly target" framing better
        # than raw post count (a creator who posts twice on Saturdays
        # shouldn't get inflated targets).
        per_week = unique_days / max(min(30, (today - cutoff_30).days), 1) * 7
        weekly_target = max(weekly_actual, int(round(per_week)))
    else:
        weekly_target = weekly_actual
    weekly_target = max(1, min(weekly_target, 7))

    # Peak hour and best days come from the same row pool.
    weekday_counter: Counter[int] = Counter()
    hour_counter: Counter[int] = Counter()
    for dt in parsed:
        weekday_counter[dt.weekday()] += 1
        hour_counter[dt.hour] += 1

    peak_hour = hour_counter.most_common(1)[0][0] if hour_counter else None

    return {
        "posts_14d": posts_14d,
        "weekly_actual": weekly_actual,
        "weekly_target": weekly_target,
        "best_hour": _format_best_hour_range(peak_hour),
        "best_days": _format_best_days(weekday_counter),
    }


# D.1.4 — hour-bucket map matches `HOURS_VN` in TimingHeatmap.tsx:
# [6–9, 9–12, 12–15, 15–18, 18–20, 20–22, 22–24, 0–3]. Hours 3–5 are
# intentionally dropped (posting-empty dead zone on TikTok VN).
_POSTING_HEATMAP_HOUR_BUCKETS: dict[int, int] = {
    6: 0, 7: 0, 8: 0,
    9: 1, 10: 1, 11: 1,
    12: 2, 13: 2, 14: 2,
    15: 3, 16: 3, 17: 3,
    18: 4, 19: 4,
    20: 5, 21: 5,
    22: 6, 23: 6,
    0: 7, 1: 7, 2: 7,
}
_POSTING_HEATMAP_MIN_ROWS = 3


def _compute_posting_heatmap(rows: list[dict[str, Any]]) -> list[list[int]]:
    """7×8 video-count matrix keyed by (weekday=Mon..Sun, hour-bucket).

    Returns ``[]`` when fewer than 3 rows parse to a valid timestamp — the
    frontend treats an empty grid as "insufficient temporal data" and hides
    the panel so we don't over-read a tiny sample.
    """
    parsed: list[datetime] = []
    for r in rows:
        dt = _parse_row_created_at(r)
        if dt is not None:
            parsed.append(dt)
    if len(parsed) < _POSTING_HEATMAP_MIN_ROWS:
        return []
    grid: list[list[int]] = [[0] * 8 for _ in range(7)]
    for dt in parsed:
        local = dt.astimezone(timezone.utc)
        hour_bucket = _POSTING_HEATMAP_HOUR_BUCKETS.get(local.hour)
        if hour_bucket is None:
            continue
        grid[local.weekday()][hour_bucket] += 1
    return grid


def _compute_streak_days(rows: list[dict[str, Any]], *, window_days: int = 14) -> int:
    """Studio Home pulse (PR-1) — consecutive recent days with ≥1 post.

    Counts back from today (UTC) until we hit a day with no parsed
    timestamps. Capped at ``window_days`` so a perfectly-cadent kênh
    doesn't overflow the design's 14-day pulse strip.

    Pure function over the temporal-corpus row list already fetched by
    ``compute_live_signals`` — adds zero DB cost.
    """
    if not rows:
        return 0
    days_with_post: set[date] = set()
    for r in rows:
        dt = _parse_ts(r.get("posted_at")) or _parse_row_created_at(r)
        if dt is None:
            continue
        days_with_post.add(dt.astimezone(timezone.utc).date())
    if not days_with_post:
        return 0
    today = datetime.now(timezone.utc).date()
    streak = 0
    for offset in range(window_days):
        check = today - timedelta(days=offset)
        if check in days_with_post:
            streak += 1
        else:
            # Allow today to be empty (creator may not have posted yet)
            # without zeroing the streak; everything else breaks it.
            if offset == 0:
                continue
            break
    return min(streak, window_days)


def _compute_views_mom_delta(rows: list[dict[str, Any]]) -> str:
    now = datetime.now(timezone.utc)
    t30 = now - timedelta(days=30)
    t60 = now - timedelta(days=60)
    last_views: list[int] = []
    prev_views: list[int] = []
    for r in rows:
        dt = _parse_row_created_at(r)
        if not dt:
            continue
        v = int(r.get("views") or 0)
        if v <= 0:
            continue
        if dt >= t30:
            last_views.append(v)
        elif t60 <= dt < t30:
            prev_views.append(v)
    if len(last_views) < 3 or len(prev_views) < 3:
        return "—"
    a1 = sum(last_views) / len(last_views)
    a0 = sum(prev_views) / len(prev_views)
    if a0 < 100:
        return "—"
    pct = (a1 - a0) / a0 * 100.0
    if abs(pct) < 1.0:
        return "ổn định MoM"
    arrow = "↑" if pct >= 0 else "↓"
    return f"{arrow} {abs(pct):.0f}% MoM"


def _compute_reach_lift_delta(rows: list[dict[str, Any]], peak_hour: int | None) -> str:
    if peak_hour is None:
        return "—"
    peak_ers: list[float] = []
    off_ers: list[float] = []
    for r in rows:
        dt = _parse_row_created_at(r)
        if not dt:
            continue
        er = float(r.get("engagement_rate") or 0.0)
        if er <= 0:
            continue
        h = dt.hour
        circ = min(abs(h - peak_hour), 24 - abs(h - peak_hour))
        in_peak = circ <= 1
        (peak_ers if in_peak else off_ers).append(er)
    if len(peak_ers) < 3 or len(off_ers) < 3:
        return "—"
    mp = _median(peak_ers)
    mo = _median(off_ers)
    if mo <= 1e-9:
        return "—"
    lift = (mp - mo) / mo * 100.0
    if lift < 3.0:
        return "—"
    return f"+{lift:.0f}% reach vs khác giờ"


def compute_live_signals(
    user_sb: Any,
    *,
    handle: str,
    niche_id: int,
    top_rows: list[dict[str, Any]],
) -> LiveSignals:
    temporal = _fetch_temporal_corpus_rows(user_sb, handle=handle, niche_id=niche_id, limit=3000)
    cad, pt, peak_h = _compute_posting_cadence_time_peak(temporal)
    band, n_dur = _optimal_length_band_with_count(top_rows)
    return LiveSignals(
        posting_cadence=cad,
        posting_time=pt,
        views_mom_delta=_compute_views_mom_delta(temporal),
        reach_lift_delta=_compute_reach_lift_delta(temporal, peak_h),
        optimal_band=band,
        duration_sample_n=n_dur,
        posting_heatmap=_compute_posting_heatmap(temporal),
        streak_days=_compute_streak_days(temporal, window_days=14),
        streak_window_days=14,
        cadence=_compute_cadence_struct(temporal),
    )


def _call_channel_gemini(
    *,
    niche_label: str,
    handle: str,
    name: str,
    sample_rows: list[dict[str, Any]],
) -> ChannelAnalyzeLLM:
    from google.genai import types

    from getviews_pipeline.config import GEMINI_SYNTHESIS_FALLBACKS, GEMINI_SYNTHESIS_MODEL
    from getviews_pipeline.gemini import _generate_content_models, _normalize_response, _response_text

    lines = []
    for i, r in enumerate(sample_rows[:20], start=1):
        hp = str(r.get("hook_phrase") or "")[:120]
        ht = str(r.get("hook_type") or "")
        v = int(r.get("views") or 0)
        lines.append(f"{i}. views≈{v} | hook_type={ht} | hook_phrase={hp}")
    pack = "\n".join(lines)

    prompt = f"""Bạn là biên tập TikTok tiếng Việt. Phân tích CÔNG THỨC nội dung và CHẨN ĐOÁN sức khoẻ của một kênh trong một ngách.

Ngách: {niche_label}
Kênh: @{handle} ({name})

Dữ liệu 20 video view cao nhất (gợi ý cấu trúc lặp lại):
{pack}

Trả về JSON theo schema:
- bio: đúng MỘT câu tiếng Việt mô tả tone / positioning kênh (không kể tên riêng dài dòng).
- formula: đúng 4 bước Hook / Setup / Body / Payoff (step ngắn tiếng Việt hoặc tiếng Anh: Hook, Setup, Body, Payoff).
  Mỗi detail mô tả khung giây + ý chính (tiếng Việt). pct là số nguyên 4–92, tổng các pct nên gần 100.
- strengths: 2–4 điểm mạnh cụ thể của kênh (đo trực tiếp từ data trên, KHÔNG so với ngách khác).
  Mỗi điểm:
    • title  : tiêu đề ≤ 80 ký tự, danh từ + động từ rõ ràng (vd: "Hook 0.8s bám trend đang lên").
    • metric : 1 con số + đơn vị + benchmark (vd: "Hook xuất hiện < 1s · 80% video", "Retention 3s 65%, ngách 48%").
    • why    : 1–2 câu giải thích VÌ SAO đây là điểm mạnh — gắn với hành vi audience hoặc thuật toán.
    • action : TẬN DỤNG cụ thể — 1–2 câu, có hành động (vd: "Tiếp tục mở video bằng face cam, đẩy CTA xuống cuối").
    • bridge_to (optional): "01" nếu tận dụng được qua kịch bản/quay ngay, "02" nếu qua remix pattern.
- weaknesses: 1–3 điểm yếu cần sửa (cũng đo từ chính kênh).
  Mỗi điểm có cùng schema (title / metric / why / action / bridge_to). action là CÁCH SỬA cụ thể.

NGUYÊN TẮC:
- Số liệu cụ thể, không nói chung chung. Nếu không có metric đáng tin → không viết về nó.
- Tiếng Việt tự nhiên, ngắn gọn. KHÔNG mở đầu bằng "Chào", "Tuyệt vời", "Wow". KHÔNG dùng "bí mật", "công thức vàng", "triệu view".
- Action phải có động từ và đối tượng rõ ràng — không "nên cải thiện hook" mà "rút hook xuống còn 0.8s, mở bằng câu hỏi".
"""
    config = types.GenerateContentConfig(
        temperature=0.5,
        response_mime_type="application/json",
        response_json_schema=ChannelAnalyzeLLM.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return ChannelAnalyzeLLM.model_validate_json(_normalize_response(raw))


def _build_kpis(
    *,
    avg_views: int,
    top_hook: str,
    hook_pct: float,
    optimal_length: str,
    total_videos: int,
    views_mom_delta: str,
    posting_time: str,
    reach_lift_delta: str,
    duration_sample_n: int,
) -> list[dict[str, str]]:
    dur_n = duration_sample_n if duration_sample_n > 0 else min(total_videos, 500) if total_videos else 0
    dur_delta = f"từ {dur_n} video gần" if total_videos and dur_n > 0 else "—"
    return [
        {"label": "VIEW TRUNG BÌNH", "value": _fmt_int_short(int(avg_views)), "delta": views_mom_delta},
        {
            "label": "HOOK CHỦ ĐẠO",
            "value": f"\"{top_hook}\"",
            "delta": f"{hook_pct:.0f}% video dùng" if hook_pct > 0 else "—",
        },
        {
            "label": "ĐỘ DÀI TỐI ƯU",
            "value": optimal_length,
            "delta": dur_delta,
        },
        {"label": "THỜI GIAN POST", "value": posting_time or "—", "delta": reach_lift_delta},
    ]


def _build_top_videos(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows[:4]):
        title = str(r.get("hook_phrase") or "").strip() or "Video"
        out.append(
            {
                "video_id": str(r.get("video_id") or ""),
                "title": title[:200],
                "views": int(r.get("views") or 0),
                "thumbnail_url": r.get("thumbnail_url"),
                "bg_color": TOP_VIDEO_TILE_COLORS[i % len(TOP_VIDEO_TILE_COLORS)],
            }
        )
    return out


# ── Studio Home pulse (PR-1) ────────────────────────────────────────────
#
# The design's PulseBlock reads as a streak chip + a one-sentence headline
# in a serif voice. We compose the headline deterministically from signals
# already on hand (views_mom_delta + posting_cadence + best/worst) so this
# new field doesn't add a Gemini call to /channel/analyze. Subsequent PRs
# may swap the templates for an LLM-generated paragraph.

PulseHeadlineKind = str  # "win" | "concern" | "neutral"


def _compute_pulse(
    *,
    live: LiveSignals,
    avg_views: int,
    total_videos: int,
) -> dict[str, Any]:
    """Compose pulse hero {streak, headline, headline_kind}.

    Uses ``live.views_mom_delta`` as the lead signal — it's already a
    Vietnamese-formatted "↑ 18% MoM" / "↓ 9% MoM" string. We classify
    direction from that and assemble a sentence that names the streak
    when it's noteworthy (≥ 3 days) and otherwise falls back to a
    cadence-only framing.
    """
    streak = int(getattr(live, "streak_days", 0) or 0)
    window = int(getattr(live, "streak_window_days", 14) or 14)
    delta = (live.views_mom_delta or "").strip()
    cadence = (live.posting_cadence or "").strip()

    kind: PulseHeadlineKind = "neutral"
    if delta.startswith("↑"):
        kind = "win"
    elif delta.startswith("↓"):
        kind = "concern"

    # Compose headline. Pieces:
    #   • "Streak X/14 ngày" — only when streak ≥ 3 (otherwise hide the
    #     streak chip entirely on the FE, but keep a fallback).
    #   • Direction sentence keyed off MoM delta + sample sufficiency.
    if total_videos < 3:
        headline = "Đang chờ thêm dữ liệu để dựng nhịp kênh — quay lại sau khi có thêm 2-3 video mới."
        kind = "neutral"
    elif kind == "win":
        headline = (
            f"Tuần qua kênh đang lên — view trung bình {delta} so với tháng trước."
            if delta != "ổn định MoM"
            else "Kênh đang giữ phong độ — view ổn định so với tháng trước."
        )
    elif kind == "concern":
        headline = (
            f"Tuần qua kênh đang chùng — view trung bình {delta} so với tháng trước."
            " Soi sâu để tìm chỗ cần sửa."
        )
    else:
        # Neutral: lean on cadence narrative if available.
        if cadence:
            headline = f"Nhịp đăng hiện tại: {cadence}. View vẫn ổn định so với tháng trước."
        else:
            headline = "Kênh đang ổn định — tiếp tục pattern bạn đang có."

    return {
        "streak_days": streak,
        "streak_window": window,
        "headline": headline,
        "headline_kind": kind,
        # Pass-through so the FE can render the chip's secondary line
        # without re-parsing the kpis array on its own.
        "mom_delta": delta or "—",
        "avg_views": int(avg_views),
    }


# ── Recent 7d ranked verdict list (PR-1) ────────────────────────────────

# vsMedian thresholds (mirror the design's tier-1 classification):
#   ≥ 1.5×  → WIN
#   < 0.7×  → UNDER
#   else    → AVG
_VS_MEDIAN_WIN = 1.5
_VS_MEDIAN_UNDER = 0.7

# Cap the list at the design's "≤ 5 rows fits without scroll" rule.
_RECENT_7D_LIMIT = 8


def _fetch_recent_7d_rows(user_sb: Any, *, handle: str, niche_id: int) -> list[dict[str, Any]]:
    """Fetch up to 8 of the kênh's videos posted in the last 7 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        res = (
            user_sb.table("video_corpus")
            .select(
                # ``hook_phrase`` doubles as the title (matches
                # ``_build_top_videos``); ``thumbnail_url`` is rendered
                # only when present.
                "video_id,hook_phrase,hook_type,views,engagement_rate,"
                "posted_at,created_at,thumbnail_url"
            )
            .ilike("creator_handle", handle)
            .eq("niche_id", niche_id)
            .gte("posted_at", cutoff)
            .order("posted_at", desc=True)
            .limit(_RECENT_7D_LIMIT)
            .execute()
        )
        return list(res.data or [])
    except Exception as exc:
        # ``posted_at`` may be NULL on legacy rows; fall back to
        # ``created_at`` so we still surface something rather than a
        # dead block on the design's hero strip.
        logger.warning("[channel_analyze] recent_7d posted_at query failed: %s", exc)
        try:
            res = (
                user_sb.table("video_corpus")
                .select(
                    "video_id,hook_phrase,hook_type,views,engagement_rate,"
                    "posted_at,created_at,thumbnail_url"
                )
                .ilike("creator_handle", handle)
                .eq("niche_id", niche_id)
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(_RECENT_7D_LIMIT)
                .execute()
            )
            return list(res.data or [])
        except Exception as inner:
            logger.warning("[channel_analyze] recent_7d created_at fallback failed: %s", inner)
            return []


def _classify_verdict(vs_median: float) -> str:
    if vs_median >= _VS_MEDIAN_WIN:
        return "WIN"
    if vs_median < _VS_MEDIAN_UNDER:
        return "UNDER"
    return "AVG"


def _verdict_note_vi(*, verdict: str, hook_type: str | None) -> str:
    """Heuristic Vietnamese note matching the design's verdict copy.

    Templated rather than LLM-generated — keeps PR-1 zero-Gemini-cost
    and gives the FE concrete strings out of the box. Future PRs may
    swap in a Gemini call when /channel/analyze is already paying for
    one.
    """
    ht = (hook_type or "").strip()
    if verdict == "WIN":
        if ht:
            return f"Vượt mức trung bình kênh — hook \"{ht}\" đang chạm đúng audience."
        return "Vượt mức trung bình kênh — hook đang chạm đúng audience."
    if verdict == "UNDER":
        return "Dưới mức trung bình — hook chưa đủ mạnh để giữ scroll."
    return "Sát trung bình kênh — pattern quen thuộc, chưa có yếu tố đặc biệt."


def _age_label_vi(posted_at_iso: str | None, *, now: datetime | None = None) -> str:
    """"3 giờ trước" / "2 ngày trước" / "5 tuần trước" — short Vi style."""
    if not posted_at_iso:
        return "—"
    dt = _parse_ts(posted_at_iso)
    if dt is None:
        return "—"
    ref = now or datetime.now(timezone.utc)
    delta = ref - dt
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 60:
        return "vừa xong"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} phút trước"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} giờ trước"
    days = hours // 24
    if days < 7:
        return f"{days} ngày trước"
    weeks = days // 7
    return f"{weeks} tuần trước"


def _build_recent_7d(
    rows: list[dict[str, Any]],
    *,
    avg_views: int,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Map raw recent rows → ranked verdict cards (sorted by vs_median)."""
    if not rows:
        return []
    safe_avg = max(int(avg_views or 0), 1)
    out: list[dict[str, Any]] = []
    for r in rows:
        views = int(r.get("views") or 0)
        vs_median = round(views / safe_avg, 2)
        verdict = _classify_verdict(vs_median)
        title = str(r.get("hook_phrase") or "").strip() or "Video"
        posted_at_iso = r.get("posted_at") or r.get("created_at")
        out.append(
            {
                "video_id": str(r.get("video_id") or ""),
                "title": title[:200],
                "thumbnail_url": r.get("thumbnail_url"),
                "hook_category": (str(r.get("hook_type") or "") or None),
                "posted_at": posted_at_iso,
                "age_label": _age_label_vi(posted_at_iso, now=now),
                "views": views,
                "vs_median": vs_median,
                "verdict": verdict,
                "verdict_note": _verdict_note_vi(
                    verdict=verdict,
                    hook_type=str(r.get("hook_type") or "") or None,
                ),
            }
        )
    # Design ranks WIN at top → AVG → UNDER, breaking ties by vs_median desc.
    rank = {"WIN": 0, "AVG": 1, "UNDER": 2}
    out.sort(key=lambda v: (rank.get(v["verdict"], 9), -float(v["vs_median"])))
    return out


def _synthesize_lessons_from_diagnostic(
    strengths: list[dict[str, Any]] | None,
    weaknesses: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """Legacy bridge — produce a ``lessons[]`` array from diagnostic items.

    Keeps the channel screen's InsightsFooter + ChannelScreen rendering on
    cache-hit responses where the new diagnostic columns are populated but
    the existing ``lessons`` consumers haven't been migrated yet. Strengths
    come first (max 2) then weaknesses (max 2) so the footer stays at
    ~4 items.
    """
    out: list[dict[str, str]] = []
    for item in (strengths or [])[:2]:
        title = str(item.get("title") or "").strip()[:120]
        metric = str(item.get("metric") or "").strip()
        why = str(item.get("why") or "").strip()
        action = str(item.get("action") or "").strip()
        body = " ".join(s for s in [metric, why, action] if s).strip()
        if title and body:
            out.append({"title": title, "body": body[:800]})
    for item in (weaknesses or [])[:2]:
        title = str(item.get("title") or "").strip()[:120]
        metric = str(item.get("metric") or "").strip()
        why = str(item.get("why") or "").strip()
        action = str(item.get("action") or "").strip()
        body = " ".join(s for s in [metric, why, action] if s).strip()
        if title and body:
            out.append({"title": title, "body": body[:800]})
    return out


def _normalize_diagnostic_items(
    raw: list[dict[str, Any]] | None,
    *,
    default_action_label: str,
) -> list[dict[str, Any]]:
    """Defensive coerce — clamp lengths, drop empties, normalize bridge_to.

    Used when reading cached rows back out of channel_formulas (no Pydantic
    validation on the cache path) and when the LLM occasionally includes
    a stray null / wrong-type field.
    """
    out: list[dict[str, Any]] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:120]
        metric = str(item.get("metric") or "").strip()[:120]
        why = str(item.get("why") or "").strip()[:320]
        action = str(item.get("action") or "").strip()[:320]
        if not (title and (metric or why or action)):
            continue
        bridge = item.get("bridge_to")
        bridge_str: str | None = None
        if isinstance(bridge, str) and bridge in _BRIDGE_VALUES:
            bridge_str = bridge
        out.append(
            {
                "title": title,
                "metric": metric,
                "why": why,
                "action": action or default_action_label,
                "bridge_to": bridge_str,
            }
        )
    return out


def _assemble_response(
    *,
    handle: str,
    niche_id: int,
    niche_label: str,
    starter: dict[str, Any] | None,
    stats: dict[str, Any],
    top_rows: list[dict[str, Any]],
    hook_types: list[str],
    formula: list[dict[str, Any]] | None,
    strengths: list[dict[str, Any]] | None,
    weaknesses: list[dict[str, Any]] | None,
    bio: str,
    top_hook: str | None,
    cached_optimal: str | None,
    live: LiveSignals,
    formula_gate: str | None,
    user_sb: Any,
    computed_at: str | None = None,
    cache_hit: bool | None = None,
    legacy_lessons: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    total = int(stats.get("total") or 0)
    avg_views = int(stats.get("avg_views") or 0)
    avg_er = float(stats.get("avg_er") or 0.0)

    th, hpct = _top_hook_from_types(
        hook_types if hook_types else [str(r.get("hook_type") or "").strip() for r in top_rows if r.get("hook_type")]
    )
    resolved_top_hook = (top_hook or "").strip() or th
    resolved_optimal = (cached_optimal or "").strip() or live.optimal_band or _optimal_length_band(top_rows)
    dur_n = live.duration_sample_n
    if dur_n <= 0 and resolved_optimal and resolved_optimal != "—":
        _, dur_n = _optimal_length_band_with_count(top_rows)

    if resolved_top_hook and resolved_top_hook != "—" and hook_types:
        hook_pct = 100.0 * sum(1 for h in hook_types if h == resolved_top_hook) / len(hook_types)
    else:
        hook_pct = hpct

    name = str((starter or {}).get("display_name") or "").strip() or handle
    followers = int((starter or {}).get("followers") or 0)
    if followers <= 0 and top_rows:
        followers = max(int(r.get("creator_followers") or 0) for r in top_rows)

    norm_strengths = _normalize_diagnostic_items(strengths, default_action_label="—")
    norm_weaknesses = _normalize_diagnostic_items(weaknesses, default_action_label="—")
    # Legacy ``lessons`` is a synthesized derivative of strengths/weaknesses
    # when the diagnostic shape is populated. Falls back to the
    # caller-provided ``legacy_lessons`` (cache-hit path with empty
    # diagnostic columns) so the channel screen stays rendered.
    out_lessons: list[dict[str, Any]]
    if norm_strengths or norm_weaknesses:
        out_lessons = _synthesize_lessons_from_diagnostic(norm_strengths, norm_weaknesses)
    else:
        out_lessons = list(legacy_lessons or [])

    out: dict[str, Any] = {
        "handle": handle,
        "niche_id": niche_id,
        "niche_label": niche_label,
        "name": name,
        "bio": (bio or "").strip(),
        "followers": followers,
        "total_videos": total,
        "avg_views": avg_views,
        "engagement_pct": round(avg_er, 6),
        "posting_cadence": live.posting_cadence,
        "posting_time": live.posting_time,
        "top_hook": resolved_top_hook,
        "formula": formula,
        "lessons": out_lessons,
        "strengths": norm_strengths,
        "weaknesses": norm_weaknesses,
        "formula_gate": formula_gate,
        "kpis": _build_kpis(
            avg_views=avg_views,
            top_hook=resolved_top_hook,
            hook_pct=hook_pct,
            optimal_length=resolved_optimal or "—",
            total_videos=total,
            views_mom_delta=live.views_mom_delta,
            posting_time=live.posting_time,
            reach_lift_delta=live.reach_lift_delta,
            duration_sample_n=dur_n,
        ),
        "top_videos": _build_top_videos(top_rows),
        "posting_heatmap": list(live.posting_heatmap),
        # Per-niche channel-level percentiles (HomeMyChannelSection bars +
        # "Ngách: …" / "Top 25%: …" labels). Falls back to a zeroed shape
        # if the RPC is unavailable; FE checks ``channel_count`` to decide
        # whether to render the benchmark layer at all.
        "niche_benchmarks": _fetch_niche_benchmarks(user_sb, niche_id=niche_id),
        # Studio Home pulse hero (PR-1) — streak chip + serif headline.
        # Always recomputed even on cache-hit responses since it reflects
        # today's signals, not what Gemini saw 7 days ago.
        "pulse": _compute_pulse(live=live, avg_views=avg_views, total_videos=total),
        # Studio Home recent-7d ranked verdict list (PR-1) — fresh DB
        # query each request; small (≤8 rows) so the cost is negligible.
        "recent_7d": _build_recent_7d(
            _fetch_recent_7d_rows(user_sb, handle=handle, niche_id=niche_id),
            avg_views=avg_views,
        ),
        # Studio Home NHỊP ĐĂNG block (PR-3) — typed cadence shape
        # (calendar grid + best-hour / best-days). ``None`` when there
        # isn't enough temporal data; FE hides the section in that case.
        "cadence": live.cadence,
    }
    if computed_at is not None:
        out["computed_at"] = computed_at
    if cache_hit is not None:
        out["cache_hit"] = cache_hit
    return out


def run_channel_analyze_sync(
    service_sb: Any,
    user_sb: Any,
    *,
    user_id: str,
    raw_handle: str,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Sync pipeline for GET /channel/analyze."""
    handle = normalize_handle(raw_handle)
    if not handle:
        raise ValueError("Thiếu handle")

    try:
        pres = user_sb.table("profiles").select("primary_niche").single().execute()
    except Exception as exc:
        raise ValueError(f"Hồ sơ: {exc}") from exc
    niche_id = (pres.data or {}).get("primary_niche")
    if niche_id is None:
        raise ValueError("Chưa chọn ngách")

    niche_id = int(niche_id)
    niche_label = _resolve_niche_label(user_sb, niche_id)
    starter = _fetch_starter_row(user_sb, handle=handle, niche_id=niche_id)
    stats = _fetch_corpus_stats_rpc(user_sb, handle=handle, niche_id=niche_id)
    total = int(stats.get("total") or 0)

    if total == 0 and not starter:
        raise ValueError("Không thấy kênh trong ngách này")

    top_rows = _fetch_top_corpus_rows(user_sb, handle=handle, niche_id=niche_id, limit=80)
    hook_types = _fetch_hook_types(user_sb, handle=handle, niche_id=niche_id)
    live = compute_live_signals(user_sb, handle=handle, niche_id=niche_id, top_rows=top_rows)

    if total < CORPUS_GATE_MIN:
        return _assemble_response(
            handle=handle,
            niche_id=niche_id,
            niche_label=niche_label,
            starter=starter,
            stats=stats,
            top_rows=top_rows,
            hook_types=hook_types,
            formula=None,
            strengths=[],
            weaknesses=[],
            bio="",
            top_hook=None,
            cached_optimal=None,
            live=live,
            formula_gate="thin_corpus",
            user_sb=user_sb,
        )

    try:
        cres = (
            user_sb.table("channel_formulas")
            .select("*")
            .eq("handle", handle)
            .eq("niche_id", niche_id)
            .maybe_single()
            .execute()
        )
        cached = cres.data
    except Exception as exc:
        logger.warning("[channel_analyze] cache read failed: %s", exc)
        cached = None

    if cached and _cache_fresh(cached) and not force_refresh:
        raw_ct = cached.get("computed_at")
        ct = _parse_ts(raw_ct)
        computed_at_iso = ct.isoformat() if ct else (str(raw_ct) if raw_ct else None)
        # PR-2 — diagnostic columns may be empty on rows cached pre-PR-2;
        # ``_assemble_response`` falls back to the legacy ``lessons`` array
        # in that case so the channel screen InsightsFooter keeps rendering.
        cached_strengths = list(cached.get("strengths") or [])
        cached_weaknesses = list(cached.get("weaknesses") or [])
        cached_lessons = list(cached.get("lessons") or [])
        return _assemble_response(
            handle=handle,
            niche_id=niche_id,
            niche_label=niche_label,
            starter=starter,
            stats=stats,
            top_rows=top_rows,
            hook_types=hook_types,
            formula=list(cached.get("formula") or []),
            strengths=cached_strengths,
            weaknesses=cached_weaknesses,
            bio=str(cached.get("bio") or ""),
            top_hook=str(cached.get("top_hook") or "") or None,
            cached_optimal=(str(cached.get("optimal_length") or "").strip() or None),
            live=live,
            formula_gate=None,
            user_sb=user_sb,
            computed_at=computed_at_iso,
            cache_hit=True,
            legacy_lessons=cached_lessons,
        )

    _decrement_credit_or_raise(user_sb, user_id=user_id)

    sample = _fetch_top_corpus_rows(user_sb, handle=handle, niche_id=niche_id, limit=20)
    name = str((starter or {}).get("display_name") or "").strip() or handle
    llm = _call_channel_gemini(niche_label=niche_label or f"niche_{niche_id}", handle=handle, name=name, sample_rows=sample)
    formula_dicts = _normalize_formula_pcts([x.model_dump() for x in llm.formula])
    strengths_dicts = [x.model_dump() for x in llm.strengths]
    weaknesses_dicts = [x.model_dump() for x in llm.weaknesses]
    # Persist a synthesized ``lessons`` alongside so legacy /channel/analyze
    # consumers (the channel screen + InsightsFooter on Home) remain
    # rendered without a coordinated FE migration.
    legacy_lessons_dicts = _synthesize_lessons_from_diagnostic(strengths_dicts, weaknesses_dicts)
    th2, _ = _top_hook_from_types(hook_types)
    opt, _opt_n = _optimal_length_band_with_count(top_rows)

    upsert = {
        "handle": handle,
        "niche_id": niche_id,
        "formula": formula_dicts,
        "lessons": legacy_lessons_dicts,
        "strengths": strengths_dicts,
        "weaknesses": weaknesses_dicts,
        "top_hook": th2,
        "optimal_length": opt,
        "posting_time": live.posting_time,
        "posting_cadence": live.posting_cadence,
        "avg_views": int(stats.get("avg_views") or 0),
        "engagement_pct": float(stats.get("avg_er") or 0),
        "total_videos": int(stats.get("total") or 0),
        "bio": llm.bio.strip()[:320],
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        service_sb.table("channel_formulas").upsert(upsert, on_conflict="handle,niche_id").execute()
    except Exception as exc:
        logger.exception("[channel_analyze] upsert failed handle=%s niche=%s: %s", handle, niche_id, exc)
        raise

    now_iso = str(upsert["computed_at"])
    return _assemble_response(
        handle=handle,
        niche_id=niche_id,
        niche_label=niche_label,
        starter=starter,
        stats=stats,
        top_rows=top_rows,
        hook_types=hook_types,
        formula=formula_dicts,
        strengths=strengths_dicts,
        weaknesses=weaknesses_dicts,
        bio=upsert["bio"],
        top_hook=th2,
        cached_optimal=None,
        live=live,
        formula_gate=None,
        user_sb=user_sb,
        computed_at=now_iso,
        cache_hit=False,
    )
