"""Phase C.2.2 — deterministic aggregators for pattern reports (hook_effectiveness + video_corpus)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, cast

from getviews_pipeline.report_types import (
    ActionCardPayload,
    ContrastAgainst,
    EvidenceCardPayload,
    HookFinding,
    Lifecycle,
    Metric,
    PatternCellPayload,
    SourceRow,
    SumStat,
)
from getviews_pipeline.script_data import HOOK_TYPE_PATTERN_VI, latest_hook_effectiveness_rows

logger = logging.getLogger(__name__)

# Evidence tile colors — aligned with channel_analyze.TOP_VIDEO_TILE_COLORS + extras for 6 tiles.
_TILE_COLORS = ("#D9EB9A", "#E8E4DC", "#C5F0E8", "#F5E6C8", "#1F2A3B", "#2A2438")


def _pattern_label(hook_type: str) -> str:
    key = (hook_type or "").strip().lower().replace("-", "_")
    return HOOK_TYPE_PATTERN_VI.get(key, hook_type.replace("_", " ").title() or "Hook")


def _prereq_chips(hook_type: str) -> list[str]:
    """Static prerequisite hints per hook family (C.2 — mirrors TS hook-prereq-templates intent)."""
    key = (hook_type or "").strip().lower().replace("-", "_")
    defaults: dict[str, list[str]] = {
        "question": ["Câu hỏi trong 0.5s đầu", "Nhìn thẳng camera"],
        "bold_claim": ["Claim trong 1s", "Chữ lớn trên màn hình"],
        "shock_stat": ["Số liệu nguồn rõ", "Cut nhanh sau stat"],
        "story_open": ["Hook cảm xúc 2–4s", "Bối cảnh nhận diện được"],
        "curiosity_gap": ["Khoảng trống ở 3s đầu", "Payoff trước giây 12"],
        "social_proof": ["Bằng chứng xã hội 1–3s", "UGC / testimonial rõ"],
        "how_to": ["Bước 1 ngay đầu", "Chữ overlay đồng bộ"],
        "pain_point": ["Gọi đúng pain 1s đầu", "Giải pháp preview nhỏ"],
        "trend_hijack": ["Trend audio khớp niche", "Twist trong 2s"],
    }
    return defaults.get(key, ["Ổn định khung 9:16", "Audio rõ trong 2s đầu"])


def _metric(val: str, num: float, definition: str) -> Metric:
    return Metric(value=val, numeric=num, definition=definition)


def _fmt_pct(x: float) -> str:
    return f"{int(round(x * 100))}%"


def _fmt_delta_pct(avg_views: float, baseline: float) -> tuple[str, float]:
    if baseline <= 0:
        return "+0%", 0.0
    pct = (avg_views / baseline - 1.0) * 100.0
    sign = "+" if pct >= 0 else ""
    return f"{sign}{int(round(pct))}%", avg_views / baseline - 1.0


def _score_row(r: dict[str, Any]) -> float:
    av = float(r.get("avg_views") or 0)
    ret = float(r.get("avg_completion_rate") or 0)
    return av * max(ret, 0.05)


def compute_lifecycle(
    corpus_rows: list[dict[str, Any]],
    hook_type: str,
    trend_direction: str | None,
) -> Lifecycle:
    """Derive lifecycle from corpus timestamps + hook_effectiveness trend hint."""
    matched = [x for x in corpus_rows if (x.get("hook_type") or "") == hook_type]
    dates: list[datetime] = []
    for x in matched:
        raw = x.get("indexed_at") or x.get("created_at")
        if not raw:
            continue
        try:
            dates.append(datetime.fromisoformat(str(raw).replace("Z", "+00:00")))
        except Exception:
            continue
    if dates:
        first = min(dates)
        peak = max(dates, key=lambda d: d.timestamp())
        first_seen = first.strftime("%Y-%m-%d")
        peak_s = peak.strftime("%Y-%m")
    else:
        first_seen = "—"
        peak_s = "—"

    td = (trend_direction or "stable").lower()
    if td == "rising":
        mom = cast(Literal["rising", "plateau", "declining"], "rising")
    elif td == "declining":
        mom = cast(Literal["rising", "plateau", "declining"], "declining")
    else:
        mom = cast(Literal["rising", "plateau", "declining"], "plateau")
    return Lifecycle(first_seen=first_seen, peak=peak_s, momentum=mom)


def compute_findings(
    ranked_hooks: list[dict[str, Any]],
    corpus_rows: list[dict[str, Any]],
    baseline_views: float,
    runner_ups: dict[str, str],
    insights: list[str],
    why_won: list[str],
) -> list[HookFinding]:
    """Build up to 3 positive HookFinding rows from ranked hook_effectiveness rows."""
    out: list[HookFinding] = []
    for i, r in enumerate(ranked_hooks[:3]):
        ht = str(r.get("hook_type") or "")
        av = float(r.get("avg_views") or 0)
        ret = float(r.get("avg_completion_rate") or 0)
        uses = int(r.get("sample_size") or 0)
        delta_s, delta_num = _fmt_delta_pct(av, baseline_views)
        trend = str(r.get("trend_direction") or "stable")
        lf = compute_lifecycle(corpus_rows, ht, trend)
        if len(ranked_hooks) > 3:
            default_runner = str(ranked_hooks[3].get("hook_type") or "other")
        else:
            default_runner = "other"
        runner = runner_ups.get(ht, default_runner)
        runner_label = _pattern_label(str(runner))
        insight = insights[i] if i < len(insights) else f"{_pattern_label(ht)} đang vượt baseline ngách."
        wy = why_won[i] if i < len(why_won) else f"Phù hợp xu hướng xem hiện tại so với {runner_label}."
        ev_ids = _evidence_ids_for_hook(corpus_rows, ht, limit=2)
        out.append(
            HookFinding(
                rank=i + 1,
                pattern=_pattern_label(ht),
                retention=_metric(_fmt_pct(ret), ret, "avg completion (proxy)"),
                delta=_metric(delta_s, delta_num, "vs niche avg views"),
                uses=uses,
                lifecycle=lf,
                contrast_against=ContrastAgainst(pattern=runner_label, why_this_won=wy[:200]),
                prerequisites=_prereq_chips(ht),
                insight=insight[:200],
                evidence_video_ids=ev_ids,
            )
        )
    return out


def _evidence_ids_for_hook(corpus_rows: list[dict[str, Any]], hook_type: str, *, limit: int) -> list[str]:
    matched = [x for x in corpus_rows if (x.get("hook_type") or "") == hook_type]
    matched.sort(key=lambda x: int(x.get("views") or 0), reverse=True)
    return [str(x.get("video_id")) for x in matched[:limit] if x.get("video_id")]


def pick_evidence_videos(
    corpus_rows: list[dict[str, Any]],
    hook_types: set[str],
    *,
    limit: int = 6,
) -> list[EvidenceCardPayload]:
    """Top ``limit`` videos whose hook is in ``hook_types``, views desc, dedupe creators."""
    pool = [x for x in corpus_rows if (x.get("hook_type") or "") in hook_types]
    pool.sort(key=lambda x: int(x.get("views") or 0), reverse=True)
    seen: set[str] = set()
    out: list[EvidenceCardPayload] = []
    i = 0
    for row in pool:
        ch = str(row.get("creator_handle") or "")
        if ch in seen:
            continue
        seen.add(ch)
        vid = str(row.get("video_id") or "")
        if not vid:
            continue
        er = float(row.get("engagement_rate") or 0)
        retention = min(0.99, er / 100.0) if er > 1.0 else min(0.99, max(0.0, er))
        dur = int(float(row.get("video_duration") or 0) or 0)
        if dur <= 0:
            aj = row.get("analysis_json") or {}
            if isinstance(aj, str):
                import json

                try:
                    aj = json.loads(aj)
                except Exception:
                    aj = {}
            if isinstance(aj, dict):
                dur = int(float(aj.get("duration_seconds") or 0) or 0)
        bg = _TILE_COLORS[i % len(_TILE_COLORS)]
        i += 1
        thumb_raw = str(row.get("thumbnail_url") or "").strip()
        out.append(
            EvidenceCardPayload(
                video_id=vid,
                creator_handle=ch or "@unknown",
                title=str(row.get("caption") or row.get("transcript_snippet") or "Video")[:120],
                views=int(row.get("views") or 0),
                retention=retention,
                duration_sec=max(1, dur),
                bg_color=bg,
                hook_family=str(row.get("hook_type") or "other"),
                thumbnail_url=thumb_raw or None,
            )
        )
        if len(out) >= limit:
            break
    return out


def compute_what_stalled(
    he_rows: list[dict[str, Any]],
    top3_types: set[str],
    baseline_views: float,
) -> tuple[list[HookFinding], str | None]:
    """Return 2–3 stalled hooks or [] + human-readable reason (C.2 §5)."""
    eligible = [r for r in he_rows if int(r.get("sample_size") or 0) >= 5]
    if len(eligible) < 4:
        return [], "ngách quá thưa — không đủ hook để xếp hạng âm có ý nghĩa"

    retentions = [float(x.get("avg_completion_rate") or 0) for x in eligible]
    if not retentions:
        return [], "ngách quá thưa — không đủ hook để xếp hạng âm có ý nghĩa"
    sorted_r = sorted(retentions)
    q1 = sorted_r[max(0, len(sorted_r) // 4 - 1)]

    candidates: list[dict[str, Any]] = []
    for r in eligible:
        ht = str(r.get("hook_type") or "")
        if ht in top3_types:
            continue
        ret = float(r.get("avg_completion_rate") or 0)
        td = str(r.get("trend_direction") or "stable").lower()
        if td == "declining" or ret <= q1:
            candidates.append(r)

    candidates.sort(key=lambda x: float(x.get("avg_completion_rate") or 0))
    if len(candidates) < 2:
        return [], "không đủ hook suy trong tầm quan sát 7 ngày để hiển thị 2–3 dòng"

    picked = candidates[:3]
    stalled: list[HookFinding] = []
    for i, r in enumerate(picked):
        ht = str(r.get("hook_type") or "")
        av = float(r.get("avg_views") or 0)
        ret = float(r.get("avg_completion_rate") or 0)
        uses = int(r.get("sample_size") or 0)
        delta_s, delta_num = _fmt_delta_pct(av, baseline_views)
        lf = Lifecycle(
            first_seen="—",
            peak="—",
            momentum="declining",
        )
        insight = (
            f"Retention trung bình thấp hơn các hook đang thắng; "
            f"xem xét giảm dùng {_pattern_label(ht)} trong 7 ngày tới."
        )[:200]
        stalled.append(
            HookFinding(
                rank=i + 1,
                pattern=_pattern_label(ht),
                retention=_metric(_fmt_pct(ret), ret, "avg completion (proxy)"),
                delta=_metric(delta_s, delta_num, "vs niche leaders"),
                uses=uses,
                lifecycle=lf,
                contrast_against=ContrastAgainst(
                    pattern="Winning hooks",
                    why_this_won="Ưu tiên hook đang giữ retention cao hơn.",
                ),
                prerequisites=_prereq_chips(ht)[:1],
                insight=insight,
                evidence_video_ids=[],
            )
        )
    return stalled, None


def build_tldr_callouts(ni: dict[str, Any], window_days: int) -> list[SumStat]:
    """Three SumStat chips from niche_intelligence + window label."""
    n = int(ni.get("sample_size") or 0)
    med_er = float(ni.get("median_er") or ni.get("avg_engagement_rate") or 0)
    er_display = f"{med_er * 100:.1f}%" if med_er <= 1 else f"{med_er:.1f}%"
    return [
        SumStat(label="Video trong cửa sổ", value=str(n), trend=f"{window_days} ngày", tone="neutral"),
        SumStat(label="Median ER ngách", value=er_display, trend="baseline", tone="neutral"),
        SumStat(label="Độ phủ hook", value="corpus", trend="live", tone="up"),
    ]


def build_pattern_cells(ni: dict[str, Any]) -> list[PatternCellPayload]:
    """Four cells from niche_intelligence norms (best-effort)."""
    med_dur = float(ni.get("median_duration") or ni.get("avg_video_length_seconds") or ni.get("avg_duration") or 28)
    pct_sound = float(ni.get("pct_original_sound") or 0)
    md = int(med_dur)
    dur_bars = [
        max(8, md - 14),
        max(8, md - 7),
        md,
        min(95, md + 5),
        min(95, md + 10),
    ]
    hook_marker = float(ni.get("median_hook_offset_norm") or 0.42)
    hook_marker = min(1.0, max(0.0, hook_marker))
    ps_raw = float(ni.get("pct_original_sound") or 60)
    primary_pct = ps_raw * 100.0 if ps_raw <= 1.0 else min(100.0, ps_raw)
    return [
        PatternCellPayload(
            title="Thời lượng vàng",
            finding=f"{md}s",
            detail="median ngách (30d)",
            chart_kind="duration",
            chart_data={"bars": dur_bars},
        ),
        PatternCellPayload(
            title="Thời điểm hook",
            finding="0.3–0.8s",
            detail="face + text overlay",
            chart_kind="hook_timing",
            chart_data={"marker": hook_marker},
        ),
        PatternCellPayload(
            title="Nhạc nền",
            finding=f"{int(primary_pct)}% gốc",
            detail="ước lượng từ corpus",
            chart_kind="sound_mix",
            chart_data={"primary_pct": primary_pct},
        ),
        PatternCellPayload(
            title="CTA",
            finding="Follow / link",
            detail="phổ biến trong ngách",
            chart_kind="cta_bars",
            chart_data={"bars": [20, 35, 50, 30, 42]},
        ),
    ]


def static_action_cards(baseline_views: float) -> list[ActionCardPayload]:
    """Three CTAs + simple forecast from baseline views (B.4-lite)."""
    low = max(1000, int(baseline_views * 0.9))
    high = max(low + 500, int(baseline_views * 1.35))
    mid = int(baseline_views) if baseline_views > 0 else 5000
    return [
        ActionCardPayload(
            icon="sparkles",
            title="Mở Xưởng Viết",
            sub="Draft từ hook #1",
            cta="Mở",
            primary=True,
            route="/app/script",
            forecast={"expected_range": f"{low//1000}K–{high//1000}K", "baseline": f"{mid//1000}K"},
        ),
        ActionCardPayload(
            icon="search",
            title="Soi kênh đối thủ",
            sub="Benchmark retention",
            cta="Mở",
            route="/app/channel",
            forecast={"expected_range": "—", "baseline": f"{mid//1000}K"},
        ),
        ActionCardPayload(
            icon="calendar",
            title="Theo dõi trend",
            sub="Tuần này",
            cta="Xem",
            route="/app/trends",
            forecast={"expected_range": "—", "baseline": "—"},
        ),
    ]


def fetch_corpus_window(sb: Any, niche_id: int, days: int, *, limit: int = 2500) -> list[dict[str, Any]]:
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        res = (
            sb.table("video_corpus")
            .select(
                "video_id, creator_handle, views, hook_type, indexed_at, created_at, "
                "engagement_rate, video_duration, analysis_json, caption, transcript_snippet, thumbnail_url"
            )
            .eq("niche_id", niche_id)
            .gte("indexed_at", cutoff)
            .order("views", desc=True)
            .limit(limit)
            .execute()
        )
        return list(res.data or [])
    except Exception as exc:
        logger.warning("[pattern] corpus fetch failed: %s", exc)
        return []


def load_pattern_inputs(sb: Any, niche_id: int, window_days: int) -> dict[str, Any] | None:
    """Load niche label, intelligence row, hook_effectiveness, corpus slice."""
    try:
        nt = sb.table("niche_taxonomy").select("name_vn, name_en").eq("id", niche_id).maybe_single().execute()
        row = nt.data or {}
        label = str(row.get("name_vn") or row.get("name_en") or f"Niche {niche_id}")

        ni_res = sb.table("niche_intelligence").select("*").eq("niche_id", niche_id).maybe_single().execute()
        ni = ni_res.data or {}

        he_res = (
            sb.table("hook_effectiveness")
            .select(
                "hook_type, avg_views, avg_completion_rate, sample_size, trend_direction, computed_at"
            )
            .eq("niche_id", niche_id)
            .order("computed_at", desc=True)
            .limit(300)
            .execute()
        )
        he_raw = he_res.data or []
        he_latest = latest_hook_effectiveness_rows(he_raw if isinstance(he_raw, list) else [])

        corpus = fetch_corpus_window(sb, niche_id, max(window_days, 14))

        return {
            "niche_label": label,
            "ni": ni,
            "he_rows": he_latest,
            "corpus": corpus,
        }
    except Exception as exc:
        logger.warning("[pattern] load_pattern_inputs failed: %s", exc)
        return None


def rank_hooks_for_pattern(he_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order hooks by avg_views * avg_completion_rate (proxy for plan's rank)."""
    scored = [( _score_row(r), r) for r in he_rows]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]
