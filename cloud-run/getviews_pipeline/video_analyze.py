"""Phase B · B.1.3 — /video/analyze: cache, structural slots, Gemini LLM, diagnostics upsert.

Deterministic pieces reuse ``video_structural`` + ``video_niche_benchmark``.
Writes go through **service_role** (see migration: no authenticated INSERT).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from getviews_pipeline.video_niche_benchmark import (
    build_niche_benchmark_payload,
    fetch_niche_intelligence_sync,
    fetch_video_benchmark_with_axis,
)
from getviews_pipeline.video_structural import (
    decompose_segments,
    extract_hook_phases,
    model_retention_curve,
    video_duration_sec,
)

logger = logging.getLogger(__name__)

DIAGNOSTICS_STALE_AFTER = timedelta(hours=1)


def _fetch_sidecars_sync(
    video_id: str,
    comment_count_hint: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Run async thumbnail + comment-radar resolvers from the sync pipeline (thread pool)."""
    from getviews_pipeline.comment_radar_cache import resolve_comment_radar
    from getviews_pipeline.thumbnail_analysis_cache import resolve_thumbnail_analysis

    async def _both() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        return await asyncio.gather(
            resolve_thumbnail_analysis(video_id),
            resolve_comment_radar(video_id, comment_count_hint=comment_count_hint),
        )

    return asyncio.run(_both())


def _merge_sidecars_into_response(
    out: dict[str, Any],
    *,
    video_id: str,
    comment_count_hint: int,
) -> dict[str, Any]:
    """Attach corpus sidecars; failures are logged and omitted from the payload."""
    try:
        thumb, radar = _fetch_sidecars_sync(video_id, comment_count_hint)
    except Exception as exc:
        logger.warning(
            "[video_analyze] sidecar resolve failed video_id=%s: %s",
            video_id,
            exc,
        )
        return out
    if thumb is not None:
        out["thumbnail_analysis"] = thumb
    if radar is not None:
        out["comment_radar"] = radar
    return out


# ── Gemini output schemas (text-only, JSON) ───────────────────────────────


class LessonSlot(BaseModel):
    title: str = Field(max_length=120)
    body: str = Field(max_length=800)


class WinAnalysisLLM(BaseModel):
    analysis_headline: str = Field(max_length=200)
    analysis_subtext: str = Field(max_length=700)
    lessons: list[LessonSlot] = Field(min_length=3, max_length=3)
    hook_bodies: list[str] = Field(
        min_length=3,
        max_length=3,
        description="Vietnamese body copy for the 3 hook-phase cards, in time order.",
    )


class FlopIssueLLM(BaseModel):
    sev: Literal["high", "mid", "low"]
    t: float = Field(ge=0.0, le=600.0)
    end: float = Field(ge=0.0, le=600.0)
    title: str = Field(max_length=200)
    detail: str = Field(max_length=900)
    fix: str = Field(max_length=400)


class FlopHeadline(BaseModel):
    """Structured flop H1 segments; stored JSON-serialised in ``video_diagnostics.analysis_headline``."""

    prefix: str = Field(max_length=120, description='e.g. "Video dừng ở"')
    view_accent: str = Field(max_length=40, description='e.g. "8.4K view"')
    middle: str = Field(max_length=200, description="Diagnosis clause between view and prediction.")
    prediction_pos: str = Field(max_length=40, description='e.g. "~34K"')
    suffix: str = Field(max_length=120, description="Closing punctuation or short tail.")

    @model_validator(mode="after")
    def _total_chars_le_400(self) -> FlopHeadline:
        total = len(self.prefix) + len(self.view_accent) + len(self.middle) + len(self.prediction_pos) + len(
            self.suffix
        )
        if total > 400:
            raise ValueError(f"FlopHeadline total length {total} exceeds 400")
        return self


class FlopAnalysisLLM(BaseModel):
    analysis_headline: FlopHeadline
    flop_issues: list[FlopIssueLLM] = Field(min_length=1, max_length=8)


# ── Mode + KPI helpers ─────────────────────────────────────────────────────


def _median_views_proxy(niche_row: dict[str, Any] | None) -> float:
    if not niche_row:
        return 10_000.0
    o = float(niche_row.get("organic_avg_views") or 0)
    c = float(niche_row.get("commerce_avg_views") or 0)
    if o > 0 and c > 0:
        return (o + c) / 2.0
    return max(o, c, 5_000.0)


# Niche-less flop thresholds — used when ``niche_row`` is None (no
# hashtag classifier match, or niche_intelligence MV empty for that
# niche). Conservative: both tiers flag clear underperformance only.
#   • views < 5K — too few eyeballs to claim "win" by any metric
#   • views < 20K AND er < 1.5% — decent reach but weak engagement
# Otherwise default to win. Tunable via env vars for ops dial-back
# without a code push.
import os as _os  # local alias to avoid polluting module-level imports

NICHELESS_FLOP_VIEWS_FLOOR = int(_os.environ.get("NICHELESS_FLOP_VIEWS_FLOOR", "5000"))
NICHELESS_FLOP_VIEWS_LOOSE = int(_os.environ.get("NICHELESS_FLOP_VIEWS_LOOSE", "20000"))
NICHELESS_FLOP_ER_FLOOR = float(_os.environ.get("NICHELESS_FLOP_ER_FLOOR", "1.5"))


def is_flop_mode(video: dict[str, Any], niche_row: dict[str, Any] | None) -> bool:
    """Decide whether to render the flop UI for this video.

    Two-tier decision:

      1. **Niche cohort present** — compare against niche medians. Flop
         when views < 50% of niche median OR ER < 60% of niche median.
         This is the corpus-grounded signal — most accurate when we
         have a meaningful cohort.

      2. **No niche cohort** (``niche_row`` is None) — fall back to
         absolute thresholds. Pre-migration this branch silently
         defaulted to win, which mis-rendered every URL paste whose
         hashtags didn't classify (a high-frequency case for new niches
         + generic-tag videos). The absolute thresholds are
         conservative — they only flag clear underperformance, so a
         creator-relative comparison would be more accurate. Acceptable
         trade-off until we can derive a creator-cohort signal.
    """
    views = int(video.get("views") or 0)
    er = float(video.get("engagement_rate") or 0.0)

    if not niche_row:
        # Niche-less fallback. AND on the loose tier so a high-views
        # video with weak ER doesn't trigger flop unless ER is
        # genuinely poor — protects against false-positive flop on
        # passive-consumption niches (asmr, sleep content, etc.).
        if NICHELESS_FLOP_VIEWS_FLOOR > 0 and 0 < views < NICHELESS_FLOP_VIEWS_FLOOR:
            return True
        if (
            NICHELESS_FLOP_VIEWS_LOOSE > 0
            and 0 < views < NICHELESS_FLOP_VIEWS_LOOSE
            and 0 < er < NICHELESS_FLOP_ER_FLOOR
        ):
            return True
        return False

    niche_views = _median_views_proxy(niche_row)
    median_er = float(niche_row.get("median_er") or 0.04)
    if niche_views > 0 and views < niche_views * 0.5:
        return True
    if median_er > 0 and er < median_er * 0.6:
        return True
    return False


def projected_views_heuristic(
    views: int,
    niche_avg_views: int,
    flop_issues: list[dict[str, Any]],
) -> int:
    high = sum(1 for x in flop_issues if str(x.get("sev")) == "high")
    base = max(int(niche_avg_views * 0.35), int(views * 2.2))
    boost = int(high * niche_avg_views * 0.06)
    # No niche row / avg_views=0: skip niche-relative cap (otherwise cap=0 → min(0, …)=0).
    if niche_avg_views <= 0:
        return max(0, base + boost)
    cap = max(niche_avg_views, int(niche_avg_views * 1.15))
    return min(cap, base + boost)


def _fmt_int_short(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    return str(n)


def build_kpis(
    video: dict[str, Any],
    niche_meta: dict[str, Any],
    *,
    mode: Literal["win", "flop"],
    retention_end_pct: float,
) -> list[dict[str, str]]:
    views = int(video.get("views") or 0)
    shares = int(video.get("shares") or 0)
    saves = int(video.get("saves") or 0)
    # Niche-relative multiplier — historically labelled "× kênh" which
    # reads as "× channel" in Vietnamese but actually compares against
    # the niche cohort average. Two fixes (2026-05-08):
    #   1. Honest label: "× ngách" so it doesn't conflict with the
    #      true channel-relative ratio in ContextStrip.
    #   2. Hide the multiplier when the niche cohort is too thin
    #      (avg_views < 1_000) — otherwise the ``max(..., 1)`` floor
    #      produces nonsense like "126192.0× ngách" for sparse niches.
    niche_avg_raw = int(niche_meta.get("avg_views") or 0)
    if niche_avg_raw >= 1_000:
        mult = views / niche_avg_raw
        delta_views = f"{mult:.1f}× ngách" if mult >= 0.1 else "—"
    else:
        delta_views = "—"
    ret_pct = f"{retention_end_pct:.0f}%"
    ret_delta = "top 5%" if retention_end_pct >= 70 else "ngách TB"
    save_rate = (saves / views * 100.0) if views else 0.0
    sr_delta = "rất cao" if save_rate > 2.0 else "TB"
    return [
        {"label": "VIEW", "value": _fmt_int_short(views), "delta": delta_views},
        {"label": "GIỮ CHÂN", "value": ret_pct, "delta": ret_delta},
        {"label": "SAVE RATE", "value": f"{save_rate:.1f}%", "delta": sr_delta},
        {"label": "SHARE", "value": _fmt_int_short(shares), "delta": "lan toả"},
    ]


def _parse_ts(ts: Any) -> datetime | None:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    try:
        s = str(ts).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _diagnostics_fresh(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    ct = _parse_ts(row.get("computed_at"))
    if not ct:
        return False
    return datetime.now(UTC) - ct < DIAGNOSTICS_STALE_AFTER


def _cache_age_minutes(row: dict[str, Any]) -> int:
    ct = _parse_ts(row.get("computed_at"))
    if not ct:
        return 0
    delta = datetime.now(UTC) - ct
    return max(0, int(delta.total_seconds() // 60))


def _fetch_corpus_row(user_sb: Any, vid: str) -> dict[str, Any]:
    """Load one ``video_corpus`` row; never surfaces PostgREST 0-row as a 500."""
    from postgrest.exceptions import APIError

    cols = (
        "video_id,creator_handle,views,likes,comments,shares,saves,save_rate,"
        "engagement_rate,thumbnail_url,created_at,niche_id,content_class_id,"
        "content_format,analysis_json,breakout_multiplier,tiktok_url,"
        "creator_median_views"
    )
    try:
        vres = user_sb.table("video_corpus").select(cols).eq("video_id", vid).maybe_single().execute()
    except APIError as exc:
        code = getattr(exc, "code", None)
        details = str(getattr(exc, "details", "") or "")
        if code == "PGRST116" or "0 rows" in details:
            raise ValueError("video not in corpus") from exc
        raise
    if vres is None:
        raise ValueError("video not in corpus")
    data = getattr(vres, "data", None)
    if not isinstance(data, dict) or not data.get("video_id"):
        raise ValueError("video not in corpus")
    return data


def _coerce_analysis_headline_for_api(raw: Any, mode: Literal["win", "flop"]) -> Any:
    """Win: plain string. Flop: parse JSON ``FlopHeadline`` from TEXT column; legacy plain string passthrough."""
    if mode == "win":
        if raw is None:
            return None
        return raw if isinstance(raw, str) else str(raw)

    if raw is None:
        return None
    if isinstance(raw, dict):
        try:
            return FlopHeadline.model_validate(raw).model_dump()
        except Exception:
            logger.warning("[video_analyze] flop headline dict failed FlopHeadline validation")
            return str(raw)

    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("{"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return FlopHeadline.model_validate(parsed).model_dump()
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("[video_analyze] flop headline JSON invalid: %s", exc)
        return s

    return str(raw)


def _resolve_niche_label(user_sb: Any, niche_id: int) -> str:
    """``niche_taxonomy.name_vn`` preferred; empty string if missing or lookup fails."""
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


def _response_from_diagnostics_row(
    video: dict[str, Any],
    diag: dict[str, Any],
    *,
    mode: Literal["win", "flop"],
    niche_meta: dict[str, Any],
    niche_benchmark: list[dict[str, float]],
    retention_user: list[dict[str, float]],
    niche_label: str,
    retention_source: Literal["real", "modeled"] = "modeled",
    cross_format_signal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    analysis = video.get("analysis_json") or {}
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError:
            analysis = {}
    if not isinstance(analysis, dict):
        analysis = {}
    dur = video_duration_sec(analysis)
    hook = (analysis.get("hook_analysis") or {}) if isinstance(analysis.get("hook_analysis"), dict) else {}
    title_hint = str(hook.get("hook_phrase") or "")[:200]
    ret_curve = diag.get("retention_curve") or retention_user
    bench_curve = diag.get("niche_benchmark_curve") or niche_benchmark
    ret_end = float(ret_curve[-1]["pct"]) if ret_curve else 0.0

    # Channel-relative breakout: views vs the creator's own median.
    # Corpus path: read denormalized creator_median_views (from corpus_ingest).
    # On-demand path: column missing → skip; FE renders only when present.
    cm_views_raw = video.get("creator_median_views")
    creator_median_views = int(cm_views_raw) if cm_views_raw else None
    target_vs_creator_median = (
        round(int(video.get("views") or 0) / float(creator_median_views), 2)
        if creator_median_views and creator_median_views > 0
        else None
    )

    # Enrichment fields extracted by Gemini (VideoAnalysis schema, 2026-05-08).
    # Available on both corpus rows (analysis_json) and on-demand
    # (fresh extraction). Render only when populated to avoid empty chips.
    pain_points_raw = analysis.get("pain_points") or []
    style_tags_raw = analysis.get("style_tags") or []
    target_audience = str(analysis.get("target_audience") or "").strip()
    promotion_type = str(analysis.get("promotion_type") or "organic").strip().lower()
    pain_points = [str(p).strip() for p in pain_points_raw if isinstance(p, str) and p.strip()]
    style_tags = [str(s).strip() for s in style_tags_raw if isinstance(s, str) and s.strip()]
    enrichment: dict[str, Any] | None = None
    if target_audience or pain_points or style_tags or promotion_type != "organic":
        enrichment = {
            "target_audience": target_audience or None,
            "pain_points": pain_points,
            "promotion_type": promotion_type if promotion_type in (
                "organic", "brand_deal", "affiliate", "self_promotion",
            ) else "organic",
            "style_tags": style_tags,
        }

    return {
        "video_id": video["video_id"],
        "mode": mode,
        "meta": {
            "creator": video.get("creator_handle") or "",
            "views": int(video.get("views") or 0),
            "likes": int(video.get("likes") or 0),
            "comments": int(video.get("comments") or 0),
            "shares": int(video.get("shares") or 0),
            "save_rate": float(video.get("save_rate") or 0.0)
            if video.get("save_rate") is not None
            else (int(video.get("saves") or 0) / max(int(video.get("views") or 1), 1)),
            "duration_sec": dur,
            "thumbnail_url": video.get("thumbnail_url"),
            "date_posted": (video.get("created_at") or "")[:10]
            if video.get("created_at")
            else None,
            "title": title_hint or None,
            "niche_label": niche_label or None,
            "retention_source": retention_source,
            "creator_median_views": creator_median_views,
            "target_vs_creator_median": target_vs_creator_median,
        },
        "enrichment": enrichment,
        "kpis": build_kpis(video, niche_meta, mode=mode, retention_end_pct=ret_end),
        "segments": diag.get("segments") or [],
        "hook_phases": diag.get("hook_phases") or [],
        "lessons": diag.get("lessons") or [],
        "analysis_headline": _coerce_analysis_headline_for_api(diag.get("analysis_headline"), mode),
        "analysis_subtext": diag.get("analysis_subtext"),
        "flop_issues": diag.get("flop_issues"),
        "retention_curve": ret_curve,
        "niche_benchmark_curve": bench_curve,
        "niche_meta": niche_meta,
        # A.1 — cross-niche format insight (null when format is single-niche
        # or sample is too thin; FE renders only when present).
        "cross_format_signal": cross_format_signal,
        # Exposed so downstream callers (build_video_report narrative synthesis)
        # can pass the raw frame analysis to synthesize_diagnosis_v2 without a
        # second DB round-trip.  Not sent to the browser — stripped by
        # _add_narrative_synthesis before the final turn payload is built.
        "_analysis_json": analysis,
        "_content_format": str(video.get("content_format") or ""),
        "_niche_id": int(video.get("niche_id") or 0),
    }


# ── D2 (2026-05-15) — synthesis prompt v2 helpers ────────────────────────

# Forbidden cliché list — embedded in both Win + Flop prompts so Gemini
# doesn't hide behind sáo-rỗng vocabulary. Mirror of the morning-ritual
# v2 list (single source of truth would be nice; for now keep duplicated
# until a shared ``vn_copy_rules.py`` is justified).
_FORBIDDEN_PHRASES_VI = (
    '"tính năng ẩn", "bí mật không ai nói", "sự thật shock", "chỉ 1%", '
    '"hack não", "đừng bỏ qua", "xem ngay kẻo muộn", "triệu view", '
    '"bùng nổ", "công thức vàng", "chấn động"'
)

# Psychology mechanism vocabulary — same 7 from morning-ritual v2.
# Win prompt cites these so "lessons" name a mechanism instead of generic
# "tạo sự tò mò" boilerplate.
_MECHANISM_VOCAB_VI = (
    "- curiosity_gap: tạo khoảng trống thông tin viewer cần lấp\n"
    "- social_proof: ai đã làm + kết quả gì\n"
    "- identification: viewer thấy 'đó là mình' / 'đúng tình huống tôi'\n"
    "- contrarian_take: đi ngược common belief\n"
    "- before_after_promise: hứa transformation cụ thể đo được\n"
    "- status_anchor: gắn với identity / class viewer muốn thuộc về\n"
    "- fomo_loss: nguy cơ bỏ lỡ / thiệt hại nếu không hành động"
)


def _summarise_retention_curve(curve: list[dict[str, Any]] | None) -> str:
    """Compress a retention curve into a 1-line summary for prompt context.

    Identifies the steepest drop (timing + magnitude) so Gemini can anchor
    diagnosis to where viewers actually leave. Returns "" when the curve
    has fewer than 3 points (not enough signal).
    """
    if not curve or len(curve) < 3:
        return ""
    points = [
        (float(p.get("t") or 0.0), float(p.get("pct") or 0.0))
        for p in curve
        if isinstance(p, dict)
    ]
    if len(points) < 3:
        return ""
    points.sort(key=lambda p: p[0])
    # Find the largest single-step drop (next - current).
    biggest_drop = 0.0
    drop_at = 0.0
    drop_to = 0.0
    for i in range(len(points) - 1):
        delta = points[i + 1][1] - points[i][1]
        if delta < biggest_drop:  # delta is negative when retention drops
            biggest_drop = delta
            drop_at = points[i][0]
            drop_to = points[i + 1][1]
    end_pct = points[-1][1]
    if biggest_drop > -3:  # < 3% step drop → no notable drop
        return f"Retention end {end_pct:.0f}% — không có drop đột biến."
    return (
        f"Retention end {end_pct:.0f}%. Drop lớn nhất: "
        f"{abs(biggest_drop):.0f}% tại {drop_at:.1f}s → {drop_to:.0f}%."
    )


def _summarise_niche_row(row: dict[str, Any] | None) -> str:
    """Pre-format the niche/content_class row as bullets for prompt context.

    The legacy Flop prompt dumped raw JSON; Gemini parses fine but the
    signal-to-noise was bad. Bullet form reduces tokens AND makes
    the comparison anchor explicit.
    """
    if not row:
        return "(chưa có dữ liệu ngách)"
    bits: list[str] = []
    sample = row.get("sample_size")
    if sample is not None:
        bits.append(f"sample={sample}")
    avg_views = row.get("organic_avg_views") or row.get("avg_views")
    if avg_views is not None:
        bits.append(f"avg_views≈{int(avg_views):,}")
    median_er = row.get("median_er") or row.get("avg_engagement_rate")
    if median_er is not None:
        bits.append(f"median_er={float(median_er):.3f}")
    median_views = row.get("median_views")
    if median_views is not None:
        bits.append(f"median_views≈{int(median_views):,}")
    return "Ngách norms: " + ", ".join(bits) if bits else "(thưa data)"


def _call_win_gemini(
    *,
    video: dict[str, Any],
    analysis: dict[str, Any],
    niche_label: str,
    retention_curve: list[dict[str, Any]] | None = None,
) -> WinAnalysisLLM:
    from google.genai import types

    from getviews_pipeline.config import GEMINI_SYNTHESIS_FALLBACKS, GEMINI_SYNTHESIS_MODEL
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _normalize_response,
        _response_text,
    )

    hook = (analysis.get("hook_analysis") or {}) if isinstance(analysis.get("hook_analysis"), dict) else {}
    retention_summary = _summarise_retention_curve(retention_curve)
    prompt = f"""Bạn là biên tập TikTok tiếng Việt. Viết JSON theo schema cho màn "Vì sao video NỔ".

Ngách: {niche_label}
Video: creator @{video.get("creator_handle","")} | views ~{int(video.get("views") or 0)}
Hook phrase: {hook.get("hook_phrase") or ""}
Hook type: {hook.get("hook_type") or ""}
{retention_summary}

## Mechanism vocabulary (mỗi lesson PHẢI nêu tên 1 cơ chế từ list)

{_MECHANISM_VOCAB_VI}

## Quy tắc

- Headline + subtext súc tích, không sáo rỗng. Headline ≤ 90 ký tự.
- 3 lessons: title ngắn (≤ 50 ký tự) + body 1-2 câu. **Body PHẢI bắt đầu
  bằng tên mechanism từ list trên** + câu giải thích cụ thể (vd:
  "social_proof — số 47K view + creator @x đã chứng minh format này
  work cho ngách"). KHÔNG generic ("tạo sự thu hút", "engaging viewer").
- hook_bodies: đúng 3 đoạn cho 3 ô 0.0–0.8s / 0.8–1.8s / 1.8–3.0s.
  Mỗi đoạn 2-4 câu mô tả CƠ CHẾ hook tại window đó:
  - 0.0–0.8s = visual hook (frame mở đầu, body language, on-screen text)
  - 0.8–1.8s = narrative hook (câu mở miệng, promise)
  - 1.8–3.0s = retention hook (lý do viewer ở lại sau 3 giây)
  KHÔNG copy-paste hook phrase nguyên văn — diễn giải mechanism.
- TRÁNH TUYỆT ĐỐI cụm: {_FORBIDDEN_PHRASES_VI}.

## Few-shot (ví dụ ĐÚNG cho 1 lesson)

{{
  "title": "Số liệu cụ thể chốt curiosity",
  "body": "social_proof — '67% phụ nữ VN dùng SPF dưới 50' là social proof có data backing, viewer cần xem tiếp để biết mình thuộc nhóm nào."
}}
"""
    config = types.GenerateContentConfig(
        temperature=0.55,
        response_mime_type="application/json",
        response_json_schema=WinAnalysisLLM.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return WinAnalysisLLM.model_validate_json(_normalize_response(raw))


def _call_flop_gemini(
    *,
    video: dict[str, Any],
    analysis: dict[str, Any],
    niche_label: str,
    niche_row: dict[str, Any] | None,
    retention_curve: list[dict[str, Any]] | None = None,
) -> FlopAnalysisLLM:
    from google.genai import types

    from getviews_pipeline.config import GEMINI_SYNTHESIS_FALLBACKS, GEMINI_SYNTHESIS_MODEL
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _normalize_response,
        _response_text,
    )

    hook = (analysis.get("hook_analysis") or {}) if isinstance(analysis.get("hook_analysis"), dict) else {}
    niche_summary = _summarise_niche_row(niche_row)
    retention_summary = _summarise_retention_curve(retention_curve)
    prompt = f"""Bạn là chẩn đoán cấu trúc TikTok tiếng Việt. Video FLOP so với ngách.

Ngách: {niche_label}
{niche_summary}
Video: @{video.get("creator_handle","")} | views {int(video.get("views") or 0)} | ER {float(video.get("engagement_rate") or 0):.4f}
Hook phrase: {hook.get("hook_phrase") or ""}
{retention_summary}

## Severity anchor cho flop_issues (rule of thumb)

- high: retention drop >30% trong <2s, hoặc hook miss trong 0-3s, hoặc
  CTA conflict gây save_rate gần 0. Issue phải fix mới có hy vọng.
- mid: retention drop 15-30% trong cửa sổ 2-5s, hoặc structure issue
  (scene 6-8 thiếu payoff). Issue đáng fix nhưng không catastrophic.
- low: polish (text overlay legibility, sound mix, CTA wording).

## Fix vocabulary cho flop_issues.fix (mỗi fix PHẢI dùng 1 trong các action verb sau)

- "Đổi hook sang [type]" — khi hook_type không match niche norms
- "Cắt scene [N] / gộp [N] và [M]" — khi structure rời rạc
- "Đẩy CTA xuống giây [X]" / "Bỏ CTA mở đầu" — khi CTA conflict
- "Thay sound trending [genre]" — khi sound original không carry
- "Thêm text overlay tại giây [X]" — khi visual hook yếu
- "Compress hook về dưới [X]s" — khi hook stretch quá dài

## Schema

- analysis_headline: object 5 trường:
  - prefix: mở đầu ngắn (vd "Video dừng ở")
  - view_accent: cụm view ngắn (vd "8.4K view") — số khớp views video
  - middle: chẩn đoán flop (hook/scene…)
  - prediction_pos: dự đoán có dấu ~ (vd "~34K") NẾU có dự báo cụ thể;
    NẾU KHÔNG, TRẢ VỀ CHUỖI RỖNG "" — KHÔNG dùng "~0", "~—" placeholder.
  - suffix: kết (vd "." hoặc " nếu áp fix.")
  Tổng độ dài ≤ 400 ký tự.
- flop_issues: 3-6 mục, sắp xếp theo ảnh hưởng (high → low).
  - sev: 'high' | 'mid' | 'low' (theo rule trên).
  - t/end: giây timestamp trên timeline video.
  - detail: 1-2 câu chẩn đoán cụ thể.
  - fix: action-driven, dùng vocabulary trên với placeholder cụ thể.
- TRÁNH TUYỆT ĐỐI cụm: {_FORBIDDEN_PHRASES_VI}.

## Few-shot (ví dụ ĐÚNG cho 1 issue)

{{
  "sev": "high",
  "t": 0.2,
  "end": 1.8,
  "detail": "Hook 1.8s mới hiện face creator, viewer đã skip ở 0.6s vì frame mở đầu là logo + text English.",
  "fix": "Đổi hook sang pov face-first: scene 1 = 0.0–0.6s face creator + caption 'Tôi đã sai 3 năm khi…'."
}}
"""
    config = types.GenerateContentConfig(
        temperature=0.45,
        response_mime_type="application/json",
        response_json_schema=FlopAnalysisLLM.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return FlopAnalysisLLM.model_validate_json(_normalize_response(raw))


_CORPUS_ROW_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def resolve_video_id(sb: Any, *, video_id: str | None, tiktok_url: str | None) -> str:
    """Resolve whatever the caller passed into the canonical TikTok aweme_id.

    Accepts three shapes for `video_id`:
      - TikTok aweme_id (a numeric string like "7630766288574369045") —
        the canonical shape, returned as-is.
      - video_corpus.id (UUID) — some frontend callers (notably the
        Explore grid at src/routes/_app/trends/ExploreScreen.tsx) pass
        the corpus row PK instead of the aweme_id because the
        ExploreGridVideo type only exposes the row id. Tolerate it by
        looking the row up and returning its aweme_id.
      - empty → fall through to tiktok_url lookup.

    The UUID path exists because the shared URL vocab `?video_id=` is
    semantically ambiguous; fixing every call site would touch more
    code than fixing the resolver once. A surface-level frontend fix
    would also make sense for future cleanliness but doesn't change
    the server-side guarantee.
    """
    if video_id and str(video_id).strip():
        vid = str(video_id).strip()
        # UUID shape → treat as corpus row id, not aweme_id.
        if _CORPUS_ROW_UUID_RE.match(vid):
            res = (
                sb.table("video_corpus")
                .select("video_id")
                .eq("id", vid)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if not rows:
                raise ValueError("Không tìm thấy video trong corpus cho id này")
            return str(rows[0]["video_id"])
        return vid
    if not tiktok_url or not str(tiktok_url).strip():
        raise ValueError("Cần video_id hoặc tiktok_url")
    url = str(tiktok_url).strip()
    res = (
        sb.table("video_corpus")
        .select("video_id")
        .eq("tiktok_url", url)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise ValueError("Không tìm thấy video trong corpus cho URL này")
    return str(rows[0]["video_id"])


def run_video_analyze_pipeline(
    service_sb: Any,
    user_sb: Any,
    *,
    video_id: str | None,
    tiktok_url: str | None,
    force_refresh: bool = False,
    mode: Literal["win", "flop"] | None = None,
) -> dict[str, Any]:
    """Sync pipeline: read cache, else compute + Gemini + upsert. Returns API dict.

    When ``force_refresh`` is True, skip the 1h ``video_diagnostics`` TTL and
    always re-run Gemini + curve modeling (then upsert). Intended for debugging
    / prompt iteration only.

    When ``mode`` is ``"win"`` or ``"flop"``, that branch is used instead of
    the ``is_flop_mode`` heuristic. Because ``video_diagnostics`` is keyed only
    by ``video_id`` (one row holds either win- or flop-shaped analysis from the
    last run), a mode override always skips the fresh-diagnostics cache — same
    as an implicit ``force_refresh`` — so the response matches the requested path
    and the row is recomputed/upserted.
    """
    vid = resolve_video_id(user_sb, video_id=video_id, tiktok_url=tiktok_url)

    dres = (
        user_sb.table("video_diagnostics")
        .select("*")
        .eq("video_id", vid)
        .limit(1)
        .execute()
    )
    diag_row = (dres.data or [None])[0]

    video = _fetch_corpus_row(user_sb, vid)

    niche_id = int(video.get("niche_id") or 0)
    # A.2.3 — prefer content_class_intelligence when the corpus row carries
    # content_class_id (PR2-backfilled or freshly classified at ingest) AND
    # the bucket has enough samples. Falls back to niche_intelligence
    # transparently. ``benchmark_axis`` flows into VideoNicheMeta so the
    # FE can label "based on N similar-format videos" vs niche-wide.
    content_class_id = video.get("content_class_id")
    if content_class_id is None and video.get("content_format") and niche_id:
        # Defensive: corpus row may pre-date PR2 backfill but we know the
        # niche × format → derive on the fly so the new path can fire.
        from getviews_pipeline.corpus_ingest import _content_class_for
        content_class_id = _content_class_for(niche_id, video.get("content_format"))
    niche_intel, benchmark_axis = fetch_video_benchmark_with_axis(
        user_sb, niche_id=niche_id, content_class_id=content_class_id,
    )
    # A.1 — cross-niche format signal. Cheap read; returns None when
    # format is single-niche or sample is too thin so the FE renders
    # only when meaningful.
    from getviews_pipeline.cross_format import get_cross_format_signal
    cross_format_signal = get_cross_format_signal(
        user_sb, content_class_id=content_class_id,
    )
    default_niche_meta = {
        "avg_views": 0,
        "avg_retention": 0.5,
        "avg_ctr": 0.04,
        "sample_size": 0,
        "winners_sample_size": None,
    }
    if isinstance(video.get("analysis_json"), str):
        try:
            analysis = json.loads(video["analysis_json"])
        except json.JSONDecodeError:
            analysis = {}
    else:
        analysis = video.get("analysis_json") or {}
    if not isinstance(analysis, dict):
        analysis = {}
    dur = video_duration_sec(analysis)

    mode_override = mode is not None
    bypass_cache = force_refresh or mode_override
    if mode in ("win", "flop"):
        mode_resolved: Literal["win", "flop"] = mode
    else:
        mode_resolved = "flop" if is_flop_mode(video, niche_intel) else "win"

    if mode_override:
        logger.info(
            "[video_analyze] mode override: bypassing diagnostics cache video_id=%s mode=%s",
            vid,
            mode,
        )

    bench_payload = build_niche_benchmark_payload(
        niche_intel,
        niche_id=niche_id or 0,
        duration_sec=max(dur, 5.0),
        user_sb=user_sb,
    )
    niche_benchmark = bench_payload["niche_benchmark_curve"]
    niche_meta = bench_payload["niche_meta"] if bench_payload.get("niche_meta") is not None else default_niche_meta
    # A.2.3 — tag meta with which axis the benchmark came from so the FE
    # can render "vs N similar-format videos" vs "vs N videos in your niche".
    if niche_meta is not default_niche_meta:
        niche_meta["benchmark_axis"] = benchmark_axis
    rs = bench_payload.get("retention_source") or "modeled"
    retention_source: Literal["real", "modeled"] = "real" if rs == "real" else "modeled"

    niche_label_resolved = _resolve_niche_label(user_sb, niche_id) if niche_id else ""

    bm = float(video.get("breakout_multiplier") or 1.0)
    retention_user = model_retention_curve(
        max(dur, 5.0),
        niche_median_retention=float(niche_meta["avg_retention"]),
        breakout_multiplier=bm,
        n_points=20,
    )

    if diag_row and _diagnostics_fresh(diag_row) and not bypass_cache:
        age_min = _cache_age_minutes(diag_row)
        logger.info(
            "[video_analyze] cache hit: video_id=%s age_min=%d force_refresh=%s",
            vid,
            age_min,
            force_refresh,
        )
        base = _response_from_diagnostics_row(
            video,
            diag_row,
            mode=mode_resolved,
            niche_meta=niche_meta,
            niche_benchmark=niche_benchmark,
            retention_user=retention_user,
            niche_label=niche_label_resolved,
            retention_source=retention_source,
            cross_format_signal=cross_format_signal,
        )
        return _merge_sidecars_into_response(
            base,
            video_id=vid,
            comment_count_hint=int(video.get("comments") or 0),
        )

    # Gemini prompt label: last-resort literal when taxonomy row is missing.
    gemini_niche_label = niche_label_resolved or (f"niche_{niche_id}" if niche_id else "unknown")
    if not niche_label_resolved and niche_id:
        logger.warning(
            "[video_analyze] niche label fallback niche_%s for Gemini video_id=%s",
            niche_id,
            vid,
        )

    segments = decompose_segments(analysis)
    hook_cards = extract_hook_phases(analysis)

    if mode_resolved == "win":
        llm = _call_win_gemini(
            video=video, analysis=analysis, niche_label=gemini_niche_label,
            retention_curve=retention_user,
        )
        for i, body in enumerate(llm.hook_bodies[:3]):
            if i < len(hook_cards):
                hook_cards[i]["body"] = body
        lessons = [x.model_dump() for x in llm.lessons]
        headline = llm.analysis_headline
        subtext = llm.analysis_subtext
        flop_issues = None
        projected = None
    else:
        llm = _call_flop_gemini(
            video=video, analysis=analysis, niche_label=gemini_niche_label,
            niche_row=niche_intel, retention_curve=retention_user,
        )
        headline = llm.analysis_headline.model_dump_json()
        subtext = None
        lessons = []
        flop_issues = [x.model_dump() for x in llm.flop_issues]
        projected = projected_views_heuristic(
            int(video.get("views") or 0),
            int(niche_meta["avg_views"] or 0),
            flop_issues,
        )

    upsert_payload = {
        "video_id": vid,
        "analysis_headline": headline,
        "analysis_subtext": subtext,
        "lessons": lessons,
        "hook_phases": hook_cards,
        "segments": segments,
        "flop_issues": flop_issues,
        "retention_curve": retention_user,
        "niche_benchmark_curve": niche_benchmark,
        "computed_at": datetime.now(UTC).isoformat(),
    }
    try:
        service_sb.table("video_diagnostics").upsert(
            upsert_payload,
            on_conflict="video_id",
        ).execute()
    except Exception as exc:
        logger.exception("[video_analyze] upsert failed video_id=%s: %s", vid, exc)
        raise

    diag_read = upsert_payload
    out = _response_from_diagnostics_row(
        video,
        diag_read,
        mode=mode_resolved,
        niche_meta=niche_meta,
        niche_benchmark=niche_benchmark,
        retention_user=retention_user,
        niche_label=niche_label_resolved,
        retention_source=retention_source,
        cross_format_signal=cross_format_signal,
    )
    if projected is not None:
        out["projected_views"] = projected
    return _merge_sidecars_into_response(
        out,
        video_id=vid,
        comment_count_hint=int(video.get("comments") or 0),
    )


# ── On-demand analysis (URL not in corpus) ────────────────────────────────


def _build_video_dict_from_aweme(
    aweme: dict[str, Any],
    analyze_result: dict[str, Any],
    niche_id: int,
) -> dict[str, Any]:
    """Synthesise a corpus-row-shaped dict from a fresh aweme + Gemini
    analysis so the downstream synth + response builders work unchanged.

    The on-demand path never persists this row — it just needs the same
    keys ``_response_from_diagnostics_row`` + ``_call_win_gemini`` /
    ``_call_flop_gemini`` + ``build_kpis`` read from a corpus row.
    """
    from getviews_pipeline import ensemble

    metadata = ensemble.parse_metadata(aweme)
    metrics = metadata.metrics
    handle = metadata.author.username if metadata.author else ""
    video_id = str(aweme.get("aweme_id", "") or metadata.video_id or "")

    create_time = aweme.get("create_time") or aweme.get("createTime")
    created_iso: str | None = None
    if isinstance(create_time, (int, float)):
        try:
            created_iso = datetime.fromtimestamp(int(create_time), tz=UTC).isoformat()
        except (OSError, ValueError, OverflowError):
            created_iso = None

    views = int(metrics.views or 0)
    saves = int(metrics.bookmarks or 0)
    save_rate = saves / max(views, 1) if views > 0 else 0.0

    return {
        "video_id": video_id,
        "creator_handle": handle,
        "views": views,
        "likes": int(metrics.likes or 0),
        "comments": int(metrics.comments or 0),
        "shares": int(metrics.shares or 0),
        "saves": saves,
        "save_rate": save_rate,
        "engagement_rate": float(metadata.engagement_rate or 0.0),
        "thumbnail_url": metadata.thumbnail_url,
        "created_at": created_iso,
        "niche_id": niche_id,
        # The Gemini-driven analysis dict — same shape as a corpus row's
        # analysis_json. Drives KPI/segment/hook decomposition downstream.
        "analysis_json": analyze_result.get("analysis") or {},
        # No corpus baseline → assume 1.0 multiplier so retention modeling
        # falls back to the niche median curve without breakout skew.
        "breakout_multiplier": 1.0,
        "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{video_id}"
        if handle and video_id
        else "",
    }


async def _classify_niche_id_async(service_sb: Any, aweme: dict[str, Any]) -> int:
    """Best-effort niche_id from hashtags.

    Falls back to ``0`` when no hashtags match (the FE's ``winners_sample_size``
    null-fallback already renders "Đang xây dựng pool" copy in that case,
    so the user still gets a useful analysis without a niche cohort).
    """
    from getviews_pipeline import ensemble
    from getviews_pipeline.hashtag_niche_map import classify_from_hashtags

    try:
        meta = ensemble.parse_metadata(aweme)
        nid = await classify_from_hashtags(meta.hashtags, service_sb)
        return int(nid) if nid else 0
    except Exception as exc:  # noqa: BLE001 — niche is best-effort, never fatal
        logger.warning(
            "[video_analyze_on_demand] niche classify failed (continuing with 0): %s", exc,
        )
        return 0


async def _fetch_and_analyze_async(tiktok_url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch the aweme via EnsembleData + run Gemini analysis. Returns
    ``(aweme, analyze_result)``. Wrapped so the sync entry point can
    drive both steps under a single ``asyncio.run``.

    Creates a **fresh** httpx.AsyncClient instead of reusing the module-level
    singleton.  The singleton is bound to the main Cloud Run event loop; reusing
    it inside ``asyncio.run()`` (which creates a new event loop for the calling
    thread) raises ``RuntimeError: Event loop is closed`` in Python 3.12.
    """
    import httpx

    from getviews_pipeline import ensemble
    from getviews_pipeline.analysis_core import analyze_aweme

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=30.0, read=120.0)) as fresh_client:
        aweme = await ensemble.fetch_post_info(tiktok_url, _client=fresh_client)

    analyze_result = await analyze_aweme(aweme, include_diagnosis=False)
    return aweme, analyze_result


def run_video_analyze_on_demand(
    service_sb: Any,
    user_sb: Any,
    *,
    tiktok_url: str,
    mode: Literal["win", "flop"] | None = None,
) -> dict[str, Any]:
    """Sync pipeline for URLs not yet in ``video_corpus``.

    Mirrors the corpus-row branch of ``run_video_analyze_pipeline`` but:
      • Never reads or writes ``video_corpus`` / ``video_diagnostics``.
      • Skips sidecar fetches (``thumbnail_analysis`` + ``comment_radar``
        are corpus-only — no row to attach them to).
      • Best-effort niche resolution via hashtag classifier; when nothing
        matches, ``niche_id=0`` and ``niche_meta`` falls back to the same
        empty-pool copy the existing screen renders for sparse niches.

    Composer wiring (Studio → ``/app/video?url=…``) routes URL pastes
    through ``/video/analyze``; when ``_resolve_video_id`` raises
    ``"Không tìm thấy video trong corpus cho URL này"``, the router
    falls through to this function so the user gets a working analysis
    instead of a 404 dead-end. Result is flagged ``source: "on_demand"``
    so the FE can show a subtle "phân tích trực tiếp, không lưu corpus"
    hint without re-architecting the response shape.
    """
    aweme, analyze_result = asyncio.run(_fetch_and_analyze_async(tiktok_url))

    if "error" in analyze_result or "analysis" not in analyze_result:
        # Gemini choked on the video; surface as a 500-class error rather
        # than masking it as "not found". Caller maps to HTTP 500.
        err = str(analyze_result.get("error") or "Phân tích video thất bại")
        # Carousel-specific errors have their own codes — re-raise so callers
        # can distinguish and surface a Vietnamese message instead of a 500.
        raise RuntimeError(err)

    niche_id = asyncio.run(_classify_niche_id_async(service_sb, aweme))
    video = _build_video_dict_from_aweme(aweme, analyze_result, niche_id)
    vid = video["video_id"]
    if not vid:
        raise ValueError("Aweme thiếu video_id — không phân tích được")

    analysis = video["analysis_json"]
    dur = video_duration_sec(analysis)

    # A.2.3 — derive content_class_id from analysis so the on-demand path
    # (video not yet in corpus) can also benefit from sharper benchmarks.
    # classify_format does the format detection; _content_class_for maps
    # (niche × format) to a content_class.
    from getviews_pipeline.corpus_ingest import _content_class_for, classify_format
    _on_demand_format = classify_format(analysis, niche_id) if niche_id else None
    content_class_id = _content_class_for(niche_id, _on_demand_format) if niche_id else None
    # Propagate so _response_from_diagnostics_row can expose it as _content_format.
    video["content_format"] = _on_demand_format or ""
    niche_intel, benchmark_axis = fetch_video_benchmark_with_axis(
        user_sb, niche_id=niche_id, content_class_id=content_class_id,
    )
    # A.1 — cross-niche format signal. Cheap read; returns None when
    # format is single-niche or sample is too thin so the FE renders
    # only when meaningful.
    from getviews_pipeline.cross_format import get_cross_format_signal
    cross_format_signal = get_cross_format_signal(
        user_sb, content_class_id=content_class_id,
    )
    default_niche_meta = {
        "avg_views": 0,
        "avg_retention": 0.5,
        "avg_ctr": 0.04,
        "sample_size": 0,
        "winners_sample_size": None,
    }

    if mode in ("win", "flop"):
        mode_resolved: Literal["win", "flop"] = mode
    else:
        mode_resolved = "flop" if is_flop_mode(video, niche_intel) else "win"

    bench_payload = build_niche_benchmark_payload(
        niche_intel,
        niche_id=niche_id,
        duration_sec=max(dur, 5.0),
        user_sb=user_sb,
    )
    niche_benchmark = bench_payload["niche_benchmark_curve"]
    niche_meta = (
        bench_payload["niche_meta"]
        if bench_payload.get("niche_meta") is not None
        else default_niche_meta
    )
    # A.2.3 — tag axis (matches corpus path).
    if niche_meta is not default_niche_meta:
        niche_meta["benchmark_axis"] = benchmark_axis
    rs = bench_payload.get("retention_source") or "modeled"
    retention_source: Literal["real", "modeled"] = "real" if rs == "real" else "modeled"

    niche_label_resolved = _resolve_niche_label(user_sb, niche_id) if niche_id else ""
    gemini_niche_label = niche_label_resolved or "unknown"

    bm = float(video.get("breakout_multiplier") or 1.0)
    retention_user = model_retention_curve(
        max(dur, 5.0),
        niche_median_retention=float(niche_meta["avg_retention"]),
        breakout_multiplier=bm,
        n_points=20,
    )

    segments = decompose_segments(analysis)
    hook_cards = extract_hook_phases(analysis)

    if mode_resolved == "win":
        llm = _call_win_gemini(
            video=video, analysis=analysis, niche_label=gemini_niche_label,
            retention_curve=retention_user,
        )
        for i, body in enumerate(llm.hook_bodies[:3]):
            if i < len(hook_cards):
                hook_cards[i]["body"] = body
        lessons = [x.model_dump() for x in llm.lessons]
        headline: Any = llm.analysis_headline
        subtext = llm.analysis_subtext
        flop_issues: list[dict[str, Any]] | None = None
        projected: int | None = None
    else:
        llm_flop = _call_flop_gemini(
            video=video, analysis=analysis, niche_label=gemini_niche_label,
            niche_row=niche_intel, retention_curve=retention_user,
        )
        headline = llm_flop.analysis_headline.model_dump_json()
        subtext = None
        lessons = []
        flop_issues = [x.model_dump() for x in llm_flop.flop_issues]
        projected = projected_views_heuristic(
            int(video.get("views") or 0),
            int(niche_meta["avg_views"] or 0),
            flop_issues,
        )

    diag_synth = {
        "video_id": vid,
        "analysis_headline": headline,
        "analysis_subtext": subtext,
        "lessons": lessons,
        "hook_phases": hook_cards,
        "segments": segments,
        "flop_issues": flop_issues,
        "retention_curve": retention_user,
        "niche_benchmark_curve": niche_benchmark,
        "computed_at": datetime.now(UTC).isoformat(),
    }

    out = _response_from_diagnostics_row(
        video,
        diag_synth,
        mode=mode_resolved,
        niche_meta=niche_meta,
        niche_benchmark=niche_benchmark,
        retention_user=retention_user,
        niche_label=niche_label_resolved,
        retention_source=retention_source,
        cross_format_signal=cross_format_signal,
    )
    if projected is not None:
        out["projected_views"] = projected
    # Flag the response so the FE can render a subtle "phân tích trực tiếp"
    # badge — corpus rows don't set this, so the FE only highlights when
    # explicitly truthy.
    out["source"] = "on_demand"
    return out
