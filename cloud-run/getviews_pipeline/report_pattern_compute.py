"""Phase C.2.2 — deterministic aggregators for pattern reports (hook_effectiveness + video_corpus)."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, cast

from getviews_pipeline.report_types import (
    ABPairVideo,
    ActionCardPayload,
    ContrastAgainst,
    EvidenceCardPayload,
    HookFinding,
    Lifecycle,
    Metric,
    OutlierStory,
    PatternABPair,
    PatternCellPayload,
    SumStat,
)
from getviews_pipeline.script_data import HOOK_TYPE_PATTERN_VI, latest_hook_effectiveness_rows

logger = logging.getLogger(__name__)

# Evidence tile colors — aligned with channel_analyze.TOP_VIDEO_TILE_COLORS + extras for 6 tiles.
_TILE_COLORS = ("#D9EB9A", "#E8E4DC", "#C5F0E8", "#F5E6C8", "#1F2A3B", "#2A2438")


def _evidence_card_extras(row: dict[str, Any]) -> tuple[float | None, int | None, str | None]:
    """Breakout for evidence strip (prefers ``breakout_ratio``), days since index, TikTok URL."""
    if "breakout_ratio" in row:
        _br_raw = row["breakout_ratio"]
        _br = _br_raw if _br_raw is not None and _br_raw != "" else row.get("breakout_multiplier")
    else:
        _br = row.get("breakout_multiplier")
    breakout_val: float | None = None
    if _br is not None and _br != "":
        try:
            breakout_val = round(float(_br), 1)
        except (TypeError, ValueError):
            breakout_val = None
    raw_ts = row.get("indexed_at") or row.get("created_at")
    days_ago: int | None = None
    if raw_ts:
        try:
            d = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - d.astimezone(timezone.utc)
            days_ago = max(0, delta.days)
        except Exception:
            days_ago = None
    tu = str(row.get("tiktok_url") or "").strip() or None
    return breakout_val, days_ago, tu


def _pattern_label(hook_type: str) -> str:
    key = (hook_type or "").strip().lower().replace("-", "_")
    return HOOK_TYPE_PATTERN_VI.get(key, hook_type.replace("_", " ").title() or "Hook")


def build_micro_context(
    corpus_rows: list[dict[str, Any]],
    hook_types: list[str],
    top_n: int = 5,
) -> str:
    """Aggregate scene-level micro-elements per hook_type for synthesis context.

    Extracts framing, overlay_style, pace, avg_duration, and first-scene
    descriptions from the top-N corpus videos per hook type. Returns a compact
    multi-line string injected into the Gemini prompt so the synthesis can name
    specific visual details rather than generic hook descriptions.
    """
    lines: list[str] = []

    for hook_type in hook_types:
        matching = [r for r in corpus_rows if (r.get("hook_type") or "") == hook_type]
        top = sorted(matching, key=lambda x: int(x.get("views") or 0), reverse=True)[:top_n]
        if not top:
            continue

        framings: Counter[str] = Counter()
        overlays: Counter[str] = Counter()
        paces: Counter[str] = Counter()
        subjects: Counter[str] = Counter()
        durations: list[float] = []
        scene_descriptions: list[str] = []

        for row in top:
            aj = row.get("analysis_json") or {}
            if isinstance(aj, str):
                try:
                    aj = json.loads(aj)
                except Exception:
                    aj = {}
            scenes = aj.get("scenes") or []

            for s in scenes[:3]:
                if s.get("framing"):
                    framings[str(s["framing"])] += 1
                if s.get("overlay_style"):
                    overlays[str(s["overlay_style"])] += 1
                if s.get("pace"):
                    paces[str(s["pace"])] += 1
                if s.get("subject"):
                    subjects[str(s["subject"])] += 1
                desc = (s.get("description") or "").strip()
                if desc and len(scene_descriptions) < 3:
                    scene_descriptions.append(desc[:70])

            dur = aj.get("video_duration") or row.get("video_duration")
            if dur:
                try:
                    durations.append(float(dur))
                except (TypeError, ValueError):
                    pass

        n = len(top)
        avg_dur = f"{sum(durations) / len(durations):.0f}s" if durations else "?"

        label = _pattern_label(hook_type)
        parts: list[str] = []

        top_framing = framings.most_common(1)
        top_overlay = overlays.most_common(1)
        top_pace = paces.most_common(1)
        top_subject = subjects.most_common(1)

        if top_framing:
            parts.append(f"góc quay={top_framing[0][0]}({top_framing[0][1]}/{n})")
        if top_overlay:
            parts.append(f"text_overlay={top_overlay[0][0]}({top_overlay[0][1]}/{n})")
        if top_pace:
            parts.append(f"nhịp={top_pace[0][0]}({top_pace[0][1]}/{n})")
        if top_subject:
            parts.append(f"chủ thể={top_subject[0][0]}({top_subject[0][1]}/{n})")
        parts.append(f"avg={avg_dur}")

        if scene_descriptions:
            sample = "; ".join(scene_descriptions[:2])
            parts.append(f"scene mẫu: [{sample}]")

        lines.append(f"Hook '{label}': {', '.join(parts)}")

    return "\n".join(lines)


def build_top_performers_context(
    corpus_rows: list[dict[str, Any]],
    hook_types: list[str],
    top_n: int = 3,
) -> str:
    """Format top-N corpus videos per hook_type as a citation-ready string."""
    now = datetime.now(timezone.utc)
    lines: list[str] = []
    for hook_type in hook_types:
        matching = sorted(
            [r for r in corpus_rows if (r.get("hook_type") or "") == hook_type],
            key=lambda x: int(x.get("views") or 0),
            reverse=True,
        )[:top_n]
        if not matching:
            continue
        label = _pattern_label(hook_type)
        lines.append(f"Hook '{label}':")
        for r in matching:
            handle = r.get("creator_handle") or "unknown"
            views = int(r.get("views") or 0)
            views_str = (
                f"{views / 1_000_000:.1f}M"
                if views >= 1_000_000
                else f"{views // 1_000}K"
                if views >= 1_000
                else str(views)
            )
            raw_ts = r.get("indexed_at") or r.get("created_at")
            recency = ""
            if raw_ts:
                try:
                    dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    days = (now - dt.astimezone(timezone.utc)).days
                    recency = (
                        ", đăng hôm nay"
                        if days == 0
                        else f", đăng {days} ngày trước"
                        if days <= 14
                        else f", đăng {days // 7} tuần trước"
                    )
                except Exception:
                    pass
            lines.append(f"  @{str(handle).lstrip('@')} — {views_str} view{recency}")
    return "\n".join(lines)


def find_ab_pair(
    corpus_rows: list[dict[str, Any]],
    top_hook_type: str,
    min_delta: int = 5,
) -> PatternABPair | None:
    """Same-creator hit (top_hook_type) vs flop (other hook), min hit/flop view ratio."""
    now = datetime.now(timezone.utc)

    by_creator: dict[str, list[dict[str, Any]]] = {}
    for r in corpus_rows:
        ch_raw = r.get("creator_handle") or ""
        if not ch_raw:
            continue
        ch = str(ch_raw).lstrip("@").strip()
        if not ch:
            continue
        by_creator.setdefault(ch, []).append(r)

    best_pair: PatternABPair | None = None
    best_delta = 0

    def _days(row: dict[str, Any]) -> int | None:
        raw = row.get("indexed_at") or row.get("created_at")
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0, (now - dt.astimezone(timezone.utc)).days)
        except Exception:
            return None

    def _url(row: dict[str, Any]) -> str | None:
        raw = str(row.get("tiktok_url") or "").strip()
        if raw.startswith("http"):
            return raw
        vid = row.get("video_id") or ""
        h = str(row.get("creator_handle") or "").lstrip("@")
        return f"https://www.tiktok.com/@{h}/video/{vid}" if vid and h else None

    for handle, rows in by_creator.items():
        if len(rows) < 2:
            continue

        hits = [r for r in rows if (r.get("hook_type") or "") == top_hook_type]
        flops = [
            r
            for r in rows
            if (r.get("hook_type") or "") != top_hook_type and r.get("hook_type")
        ]

        if not hits or not flops:
            continue

        best_hit = max(hits, key=lambda x: int(x.get("views") or 0))
        worst_flop = min(flops, key=lambda x: int(x.get("views") or 0))

        hit_views = int(best_hit.get("views") or 0)
        flop_views = int(worst_flop.get("views") or 0)
        # Audit fix #1 (Pass 2) — guard against zero/near-zero flops.
        # EnsembleData often returns ``play_count: 0`` for fresh or
        # private posts. Without this guard, ``max(flop_views, 1)``
        # floored division produced misleading mega-deltas
        # (e.g. "Video đỉnh 5K view vs Video thấp 0 view · 5,000×")
        # that the FE then rendered as evidence. Require a non-trivial
        # baseline before claiming an A/B pair exists.
        if flop_views < 100 or hit_views <= 0:
            continue
        delta = round(hit_views / flop_views)

        if delta < min_delta or delta <= best_delta:
            continue

        flop_hook_label = _pattern_label(str(worst_flop.get("hook_type") or ""))

        best_pair = PatternABPair(
            creator_handle=f"@{handle}",
            hit=ABPairVideo(
                video_id=str(best_hit.get("video_id") or ""),
                tiktok_url=_url(best_hit),
                views=hit_views,
                hook_type=_pattern_label(top_hook_type),
                days_ago=_days(best_hit),
            ),
            flop=ABPairVideo(
                video_id=str(worst_flop.get("video_id") or ""),
                tiktok_url=_url(worst_flop),
                views=flop_views,
                hook_type=flop_hook_label,
                days_ago=_days(worst_flop),
            ),
            delta=delta,
            hook_contrast=f"{_pattern_label(top_hook_type)} vs {flop_hook_label}",
        )
        best_delta = delta

    return best_pair


def fetch_outlier_story(
    client: Any,
    niche_id: int,
    window_days: int,
) -> OutlierStory | None:
    """Highest-breakout corpus row in the window (requires ``breakout_ratio`` populated)."""
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    since_iso = since.isoformat()
    try:
        resp = (
            client.table("video_corpus")
            .select("creator_handle, views, breakout_ratio, hook_type, indexed_at")
            .eq("niche_id", niche_id)
            .gte("indexed_at", since_iso)
            .not_.is_("breakout_ratio", "null")
            .gt("breakout_ratio", 5.0)
            .order("breakout_ratio", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("[pattern] outlier_story query failed: %s", exc)
        return None

    rows = resp.data or []
    if not rows:
        return None

    r = rows[0]
    ch = str(r.get("creator_handle") or "").strip().lstrip("@")
    if not ch:
        return None

    days_ago: int | None = None
    raw_idx = r.get("indexed_at")
    if raw_idx:
        try:
            dt = datetime.fromisoformat(str(raw_idx).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            days_ago = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).days
        except Exception:
            pass

    br = r.get("breakout_ratio")
    if br is None:
        return None

    return OutlierStory(
        creator_handle=f"@{ch}",
        views=int(r.get("views") or 0),
        breakout_ratio=float(round(float(br), 0)),
        hook_type=_pattern_label(str(r.get("hook_type") or "")),
        days_ago=days_ago,
    )


def _prereq_chips(hook_type: str) -> list[str]:
    """Static prerequisite hints per hook family (C.2 — mirrors TS hook-prereq-templates intent).

    BUG-16 (QA audit 2026-04-22): earlier versions mixed English loans
    ("Claim", "Cut", "UGC / testimonial", "pain", "stat", "Payoff",
    "Twist", "Trend audio") into copy that renders as Vietnamese chips.
    Fully translated so the UI stays monolingual.
    """
    key = (hook_type or "").strip().lower().replace("-", "_")
    defaults: dict[str, list[str]] = {
        "question": ["Đặt câu hỏi trong 0.5s đầu", "Nhìn thẳng camera"],
        "bold_claim": ["Tuyên bố mạnh trong 1s", "Chữ lớn trên màn hình"],
        "shock_stat": ["Dẫn nguồn số liệu rõ", "Cắt nhanh sau số liệu"],
        "story_open": ["Khơi cảm xúc 2–4s đầu", "Bối cảnh nhận diện được"],
        "curiosity_gap": ["Tạo khoảng trống ở 3s đầu", "Giải đáp trước giây 12"],
        "social_proof": ["Chứng cứ xã hội 1–3s", "Clip người thật / lời chứng rõ"],
        "how_to": ["Bước 1 ngay đầu", "Chữ overlay đồng bộ"],
        "pain_point": ["Chạm nỗi đau trong 1s đầu", "Hé lộ giải pháp ngắn"],
        "trend_hijack": ["Âm thanh trend khớp ngách", "Có cú rẽ lạ trong 2s"],
    }
    return defaults.get(key, ["Khung hình 9:16 ổn định", "Âm thanh rõ 2s đầu"])


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
    generated_prereqs: list[list[str]] | None = None,
    *,
    creator_sets: dict[str, set[str]] | None = None,
) -> list[HookFinding]:
    """Build up to 3 positive HookFinding rows from ranked hook_effectiveness rows."""
    if creator_sets is None:
        _cs: dict[str, set[str]] = defaultdict(set)
        for row in corpus_rows:
            ht = str(row.get("hook_type") or "")
            ch = str(row.get("creator_handle") or "")
            if ht and ch:
                _cs[ht].add(ch)
        creator_sets = _cs

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
        n_creators = len(creator_sets.get(ht, set())) if creator_sets else 0
        if (
            generated_prereqs
            and i < len(generated_prereqs)
            and generated_prereqs[i]
        ):
            prereqs = list(generated_prereqs[i])
        else:
            prereqs = _prereq_chips(ht)
        out.append(
            HookFinding(
                rank=i + 1,
                pattern=_pattern_label(ht),
                # BUG-16 (QA audit 2026-04-22): definitions render as
                # metric-row tooltips on /app/answer — previously in English.
                retention=_metric(_fmt_pct(ret), ret, "Xem trung bình (ước tính)"),
                delta=_metric(delta_s, delta_num, "So với view TB của ngách"),
                uses=uses,
                lifecycle=lf,
                contrast_against=ContrastAgainst(pattern=runner_label, why_this_won=wy[:200]),
                prerequisites=prereqs,
                insight=insight[:200],
                evidence_video_ids=ev_ids,
                creator_count=n_creators if n_creators > 0 else None,
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
        er_raw = float(row.get("engagement_rate") or 0)
        retention = min(0.99, er_raw / 100.0) if er_raw > 1.0 else min(0.99, max(0.0, er_raw))
        er_decimal = round((er_raw / 100.0) if er_raw > 1.0 else er_raw, 4)
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
        breakout_val, days_ago, tiktok_u = _evidence_card_extras(row)
        out.append(
            EvidenceCardPayload(
                video_id=vid,
                creator_handle=ch or "@unknown",
                title=str(row.get("caption") or row.get("transcript_snippet") or "Video")[:120],
                views=int(row.get("views") or 0),
                retention=retention,
                duration_sec=max(1, dur),
                bg_color=bg,
                hook_family=_pattern_label(str(row.get("hook_type") or "")),
                thumbnail_url=thumb_raw or None,
                breakout_ratio=breakout_val,
                engagement_rate=er_decimal,
                days_ago=days_ago,
                tiktok_url=tiktok_u,
            )
        )
        if len(out) >= limit:
            break
    return out


def compute_what_stalled(
    he_rows: list[dict[str, Any]],
    top3_types: set[str],
    baseline_views: float,
    *,
    creator_sets: dict[str, set[str]] | None = None,
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
        n_creators = len(creator_sets.get(ht, set())) if creator_sets else 0
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
                creator_count=n_creators if n_creators > 0 else None,
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


def _build_sound_trend_lookup(
    sound_trends: dict[str, Any] | None,
) -> dict[str, str]:
    """Flatten ``trend_velocity.sound_trends`` into a sound_id → label map.

    L2.2 Sprint 2 — Sound Radar. Returns {sound_id: "accelerating" |
    "peaking" | "cooling"} so ``_top_sounds_payload`` can stamp each
    sound with its current trend bucket. Empty dict when sound_trends
    is missing (FE renders no icons — graceful pre-Monday-cron state).
    """
    if not sound_trends:
        return {}
    out: dict[str, str] = {}
    for label in ("accelerating", "peaking", "cooling"):
        for entry in sound_trends.get(label) or []:
            sid = entry.get("sound_id")
            if sid:
                out[sid] = label
    return out


def _top_sounds_payload(
    rows: list[dict[str, Any]] | None,
    *,
    sound_trends_by_id: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Reduce trending_sounds rows to the FE-facing shape.

    Each entry: ``{name, usage_count, trend?}`` — the FE
    PatternMiniChart sound_mix branch consumes ``name`` for display
    and ``trend`` for the ↑/→/↓ icon. Filters out original-sound rows
    (we recommend trending music, not original audio).

    L2.2 Sprint 2 — when ``sound_trends_by_id`` is supplied, each
    sound that maps to a bucket gets a ``trend`` field
    ("accelerating" / "peaking" / "cooling"). Sounds with no bucket
    omit the field entirely so the FE renders no icon — same UX as
    pre-Sprint-2 for those entries.
    """
    if not rows:
        return []
    lookup = sound_trends_by_id or {}
    out: list[dict[str, Any]] = []
    for r in rows:
        if r.get("is_original_sound"):
            continue
        name = (r.get("sound_name") or "").strip()
        if not name:
            continue
        sid = r.get("sound_id")
        entry: dict[str, Any] = {"name": name, "usage_count": int(r.get("usage_count") or 0)}
        trend = lookup.get(sid) if sid else None
        if trend:
            entry["trend"] = trend
        out.append(entry)
        if len(out) >= 3:
            break
    return out


def _sound_cell_detail(
    rows: list[dict[str, Any]] | None,
    *,
    sound_trends_by_id: dict[str, str] | None = None,
) -> str:
    """Compose the small Vietnamese detail string under the sound % bar."""
    top = _top_sounds_payload(rows, sound_trends_by_id=sound_trends_by_id)
    if not top:
        return "ước lượng từ corpus"
    # When the #1 sound is accelerating, surface that explicitly in the
    # detail line — it's the highest-leverage signal a creator can
    # act on this week.
    leader = top[0]
    if leader.get("trend") == "accelerating":
        return f"đang nổi: {leader['name']}"
    return f"top ngách: {leader['name']}"


def build_pattern_cells(
    ni: dict[str, Any],
    trending_sounds: list[dict[str, Any]] | None = None,
    *,
    sound_trends: dict[str, Any] | None = None,
) -> list[PatternCellPayload]:
    """Four cells from niche_intelligence norms (best-effort)."""
    med_dur = float(ni.get("median_duration") or ni.get("avg_video_length_seconds") or ni.get("avg_duration") or 28)
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

    # L2.2 Sprint 2 — flatten trend_velocity.sound_trends into a quick
    # sound_id → bucket lookup, threaded through to the sound_mix cell
    # so each top_sound entry renders an ↑/→/↓ icon on the FE.
    sound_trends_by_id = _build_sound_trend_lookup(sound_trends)

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
            detail=_sound_cell_detail(trending_sounds, sound_trends_by_id=sound_trends_by_id),
            chart_kind="sound_mix",
            chart_data={
                "primary_pct": primary_pct,
                # L1.4 — top trending sounds from ``trending_sounds`` table
                # (latest week, ranked by usage_count). Empty list when the
                # niche has no sound aggregates yet (thin corpus or pre-cron).
                # L2.2 Sprint 2 — each entry now optionally carries
                # ``trend ∈ {"accelerating","peaking","cooling"}`` from
                # ``trend_velocity.sound_trends``; FE renders ↑/→/↓ when set.
                "top_sounds": _top_sounds_payload(
                    trending_sounds,
                    sound_trends_by_id=sound_trends_by_id,
                ),
            },
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
                "engagement_rate, video_duration, analysis_json, caption, transcript_snippet, "
                "thumbnail_url, tiktok_url, breakout_multiplier, breakout_ratio"
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

        # L1.4 — top trending sounds for the niche, latest week. Failure is
        # non-fatal: empty list flows through to ``build_pattern_cells``
        # which falls back to the original "ước lượng từ corpus" copy.
        trending_sounds: list[dict[str, Any]] = []
        try:
            ts_res = (
                sb.table("trending_sounds")
                .select("sound_name,sound_id,usage_count,is_original_sound,total_views,week_of")
                .eq("niche_id", niche_id)
                .order("week_of", desc=True)
                .order("usage_count", desc=True)
                .limit(10)
                .execute()
            )
            trending_sounds = ts_res.data or []
        except Exception as exc:
            logger.warning("[pattern] trending_sounds fetch failed niche=%s: %s", niche_id, exc)

        # L2.2 Sprint 2 — Sound Radar bucket lookup from trend_velocity.
        # Reads the most recent row's ``sound_trends`` JSONB and flattens
        # it into a sound_id → label map. Failure is non-fatal: empty
        # dict means the FE renders no ↑/→/↓ icons (pre-Sprint-2 UX).
        sound_trends: dict[str, Any] = {}
        try:
            tv_res = (
                sb.table("trend_velocity")
                .select("sound_trends, week_start")
                .eq("niche_id", niche_id)
                .order("week_start", desc=True)
                .limit(1)
                .execute()
            )
            tv_rows = tv_res.data or []
            if tv_rows:
                sound_trends = tv_rows[0].get("sound_trends") or {}
        except Exception as exc:
            logger.warning("[pattern] trend_velocity fetch failed niche=%s: %s", niche_id, exc)

        return {
            "niche_label": label,
            "ni": ni,
            "he_rows": he_latest,
            "corpus": corpus,
            "trending_sounds": trending_sounds,
            "sound_trends": sound_trends,
        }
    except Exception as exc:
        logger.warning("[pattern] load_pattern_inputs failed: %s", exc)
        return None


def rank_hooks_for_pattern(he_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order hooks by avg_views * avg_completion_rate (proxy for plan's rank)."""
    scored = [( _score_row(r), r) for r in he_rows]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]
