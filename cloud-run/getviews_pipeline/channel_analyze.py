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
from datetime import datetime, timedelta, timezone
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


class InsufficientCreditsError(Exception):
    """``decrement_credit`` returned false or raised."""


class ChannelFormulaStepLLM(BaseModel):
    step: str = Field(max_length=40)
    detail: str = Field(max_length=220)
    pct: int = Field(ge=4, le=92)


class ChannelLessonLLM(BaseModel):
    title: str = Field(max_length=120)
    body: str = Field(max_length=800)


class ChannelAnalyzeLLM(BaseModel):
    bio: str = Field(max_length=320, description="Một câu tiếng Việt mô tả tone kênh.")
    formula: list[ChannelFormulaStepLLM] = Field(min_length=4, max_length=4)
    lessons: list[ChannelLessonLLM] = Field(min_length=4, max_length=4)


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
            .select("created_at,views,engagement_rate")
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

    prompt = f"""Bạn là biên tập TikTok tiếng Việt. Phân tích CÔNG THỨC nội dung của một kênh trong một ngách.

Ngách: {niche_label}
Kênh: @{handle} ({name})

Dữ liệu 20 video view cao nhất (gợi ý cấu trúc lặp lại):
{pack}

Trả về JSON theo schema:
- bio: đúng MỘT câu tiếng Việt mô tả tone / positioning kênh (không kể tên riêng dài dòng).
- formula: đúng 4 bước Hook / Setup / Body / Payoff (step ngắn tiếng Việt hoặc tiếng Anh như design: Hook, Setup, Body, Payoff).
  Mỗi detail mô tả khung giây + ý chính (tiếng Việt). pct là số nguyên 4–92, tổng các pct nên gần 100.
- lessons: đúng 4 bài học title+body (tiếng Việt, body 1–3 câu, thực tế, không sáo rỗng).
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
    lessons: list[dict[str, Any]] | None,
    bio: str,
    top_hook: str | None,
    cached_optimal: str | None,
    live: LiveSignals,
    formula_gate: str | None,
    computed_at: str | None = None,
    cache_hit: bool | None = None,
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
        "lessons": lessons or [],
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
            lessons=[],
            bio="",
            top_hook=None,
            cached_optimal=None,
            live=live,
            formula_gate="thin_corpus",
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
        return _assemble_response(
            handle=handle,
            niche_id=niche_id,
            niche_label=niche_label,
            starter=starter,
            stats=stats,
            top_rows=top_rows,
            hook_types=hook_types,
            formula=list(cached.get("formula") or []),
            lessons=list(cached.get("lessons") or []),
            bio=str(cached.get("bio") or ""),
            top_hook=str(cached.get("top_hook") or "") or None,
            cached_optimal=(str(cached.get("optimal_length") or "").strip() or None),
            live=live,
            formula_gate=None,
            computed_at=computed_at_iso,
            cache_hit=True,
        )

    _decrement_credit_or_raise(user_sb, user_id=user_id)

    sample = _fetch_top_corpus_rows(user_sb, handle=handle, niche_id=niche_id, limit=20)
    name = str((starter or {}).get("display_name") or "").strip() or handle
    llm = _call_channel_gemini(niche_label=niche_label or f"niche_{niche_id}", handle=handle, name=name, sample_rows=sample)
    formula_dicts = _normalize_formula_pcts([x.model_dump() for x in llm.formula])
    lessons_dicts = [x.model_dump() for x in llm.lessons]
    th2, _ = _top_hook_from_types(hook_types)
    opt, _opt_n = _optimal_length_band_with_count(top_rows)

    upsert = {
        "handle": handle,
        "niche_id": niche_id,
        "formula": formula_dicts,
        "lessons": lessons_dicts,
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
        lessons=lessons_dicts,
        bio=upsert["bio"],
        top_hook=th2,
        cached_optimal=None,
        live=live,
        formula_gate=None,
        computed_at=now_iso,
        cache_hit=False,
    )
