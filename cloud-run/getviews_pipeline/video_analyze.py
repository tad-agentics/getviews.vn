"""Phase B · B.1.3 — /video/analyze: cache, structural slots, Gemini LLM, diagnostics upsert.

Deterministic pieces reuse ``video_structural`` + ``video_niche_benchmark``.
Writes go through **service_role** (see migration: no authenticated INSERT).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from getviews_pipeline.video_niche_benchmark import (
    build_niche_benchmark_payload,
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


# ── Gemini output schemas (Call 1 — structured errors only) ─────────────

_SILENT_FORMAT_EXCEPTIONS_VIDEO = frozenset(
    {
        "product_display_silent",
        "ambient_lifestyle",
        "macro_closeup_product",
        "aesthetic_broll",
        "text_overlay_only",
        "faceless",
        "highlight",
        "product_showcase",
        "jewelry",
        "watch_flex",
        "luxury_broll",
    }
)

# Formats where a talking head is not expected — skip no_human_presence (v4 FORMAT-CONTRADICT).
PRESENTER_NOT_REQUIRED_FORMATS = frozenset({
    "product_showcase",
    "flat_lay",
    "unboxing_silent",
})


class VideoErrorItemLLM(BaseModel):
    """Matches frontend ``VideoFlopIssue`` (+ error_id)."""

    error_id: str = Field(max_length=64, description="Stable slug e.g. ERR_hook_weak")
    sev: Literal["high", "mid", "low"]
    t: float = Field(ge=0.0, le=600.0)
    end: float = Field(ge=0.0, le=600.0)
    title: str = Field(max_length=200)
    detail: str = Field(max_length=900)
    fix: str = Field(max_length=400)


class VideoErrorsExtractionLLM(BaseModel):
    errors: list[VideoErrorItemLLM] = Field(default_factory=list, max_length=8)


# ── Mode + KPI helpers ─────────────────────────────────────────────────────


def _median_views_proxy(niche_row: dict[str, Any] | None) -> float:
    """Best view proxy from a benchmark row (niche or content_class MV).

    The niche MV has organic/commerce split; the content_class MV
    exposes ``avg_views``/``median_views`` directly. Reading only the
    niche columns made content_class rows fall through to the 5000
    floor and is_flop_mode silently classified every video against the
    wrong baseline.
    """
    if not niche_row:
        return 10_000.0
    o = float(niche_row.get("organic_avg_views") or 0)
    c = float(niche_row.get("commerce_avg_views") or 0)
    if o > 0 and c > 0:
        return (o + c) / 2.0
    blended = max(o, c, 0.0)
    if blended > 0:
        return blended
    direct = float(niche_row.get("avg_views") or 0)
    if direct > 0:
        return direct
    median = float(niche_row.get("median_views") or 0)
    if median > 0:
        return median
    return 5_000.0


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


def _fmt_int_short(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    return str(n)


_KPI_QUANT_CACHE_TTL_S = 300.0
_KPI_QUANT_CACHE: dict[
    int,
    tuple[float, tuple[tuple[float | None, float | None], tuple[float | None, float | None]]],
] = {}


def fetch_niche_save_share_pct_quantiles_sync(
    sb: Any,
    niche_id: int,
    *,
    min_samples: int = 5,
    limit: int = 200,
) -> tuple[tuple[float | None, float | None], tuple[float | None, float | None]]:
    """``((save_p25, save_p75), (share_p25, share_p75))`` on 0–100% scale for KPI labels.

    Save cohort uses ``100*saves/views`` per row (same definition as the KPI value), not
    ``save_rate``, so tertiles stay comparable when ``save_rate`` is sparsely populated.
    Results are cached per process (~5 min) to avoid hammering PostgREST on repeat reads.
    """
    if not niche_id or sb is None:
        return (None, None), (None, None)

    now = time.monotonic()
    cached = _KPI_QUANT_CACHE.get(niche_id)
    if cached is not None and now - cached[0] < _KPI_QUANT_CACHE_TTL_S:
        return cached[1]

    try:
        since = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        res = (
            sb.table("video_corpus")
            .select("views, shares, saves")
            .eq("niche_id", niche_id)
            .gt("views", 0)
            .gte("indexed_at", since)
            .limit(limit)
            .execute()
        )
        rows = list(res.data or [])
    except Exception as exc:
        logger.debug("[video_analyze] kpi cohort quantiles failed niche=%s: %s", niche_id, exc)
        return (None, None), (None, None)

    save_pcts: list[float] = []
    share_pcts: list[float] = []
    for r in rows:
        v = int(r.get("views") or 0)
        if v <= 0:
            continue
        sv = int(r.get("saves") or 0)
        save_pcts.append(100.0 * sv / float(v))
        sh = int(r.get("shares") or 0)
        share_pcts.append(100.0 * sh / float(v))

    def _qpct(vals: list[float]) -> tuple[float | None, float | None]:
        if len(vals) < min_samples:
            return None, None
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        p25 = vals_sorted[max(0, (n * 25) // 100)]
        p75 = vals_sorted[min(n - 1, (n * 75) // 100)]
        if p75 <= p25:
            return None, None
        return float(p25), float(p75)

    out = _qpct(save_pcts), _qpct(share_pcts)
    _KPI_QUANT_CACHE[niche_id] = (now, out)
    return out


def classify_kpi_tertile_label(
    value: float,
    p25: float | None,
    p75: float | None,
    *,
    metric: str = "",
) -> str:
    """``thấp`` / ``TB`` / ``cao`` / ``''`` when cohort band missing (audit SAVE-LABEL v4)."""
    if p25 is None or p75 is None or p75 <= p25:
        return ""
    if value < p25:
        label = "thấp"
    elif value > p75:
        label = "cao"
    else:
        label = "TB"
    if metric:
        logger.debug(
            "[metric_label] metric=%s value=%s p25=%s p75=%s → label=%s",
            metric,
            value,
            p25,
            p75,
            label,
        )
    return label


def build_kpis(
    video: dict[str, Any],
    niche_meta: dict[str, Any],
    *,
    mode: Literal["win", "flop"],
    retention_end_pct: float,
    cohort_save_p25_pct: float | None = None,
    cohort_save_p75_pct: float | None = None,
    cohort_share_p25_pct: float | None = None,
    cohort_share_p75_pct: float | None = None,
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
    sr_l = classify_kpi_tertile_label(
        save_rate,
        cohort_save_p25_pct,
        cohort_save_p75_pct,
        metric="save_rate",
    )
    band_ok = (
        cohort_save_p25_pct is not None
        and cohort_save_p75_pct is not None
        and cohort_save_p75_pct > cohort_save_p25_pct
    )
    if save_rate > 2.0 and (not band_ok or save_rate > cohort_save_p75_pct):
        sr_delta = "rất cao"
    elif sr_l:
        sr_delta = sr_l
    else:
        sr_delta = ""

    share_rate = (shares / views * 100.0) if views else 0.0
    sh_l = classify_kpi_tertile_label(
        share_rate,
        cohort_share_p25_pct,
        cohort_share_p75_pct,
        metric="share_rate",
    )
    if sh_l:
        share_delta = sh_l
    else:
        share_delta = "lan toả" if shares > 0 else "—"

    return [
        {"label": "VIEW", "value": _fmt_int_short(views), "delta": delta_views},
        {"label": "GIỮ CHÂN", "value": ret_pct, "delta": ret_delta},
        {"label": "SAVE RATE", "value": f"{save_rate:.1f}%", "delta": sr_delta},
        {"label": "SHARE", "value": _fmt_int_short(shares), "delta": share_delta},
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
        "creator_median_views,caption"
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


def _diagnostics_legacy(diag: dict[str, Any]) -> bool:
    """True if ``video_diagnostics`` row predates unified errors + narrative schema."""

    if diag.get("analysis_headline"):
        return True
    les = diag.get("lessons") or []
    if isinstance(les, list) and len(les) > 0:
        return True
    for fi in diag.get("flop_issues") or []:
        if isinstance(fi, dict) and not str(fi.get("error_id") or "").strip():
            return True
    return False


# Closed [0, _HOOK_LANG_DEDUPE_WINDOW_END_SEC] — overlap with error [t, end] dedupes vs lang_market.
_HOOK_LANG_DEDUPE_WINDOW_END_SEC = 4.0


def _overlaps_hook_lang_dedupe_window(t: float, end: float) -> bool:
    err_lo = min(t, end)
    err_hi = max(t, end)
    return err_lo <= _HOOK_LANG_DEDUPE_WINDOW_END_SEC and err_hi >= 0.0


def _is_hook_related_error(e: dict[str, Any]) -> bool:
    eid = str(e.get("error_id") or "").lower()
    title_l = str(e.get("title") or "").lower()
    return (
        "hook" in eid
        or eid.startswith("err_hook")
        or "hook" in title_l
        or "mở đầu" in title_l
        or title_l.startswith("mở ")
    )


def _dedupe_hook_window_high_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Single-pass dedupe of multiple high-severity hook errors in the 0–4s window.

    Picks a primary (prefer ``lang_market_mismatch``, else the first
    overlapping high-sev hook error), merges sibling ``fix`` texts
    into the primary as "(Bổ sung: …)", and drops the siblings.
    Preserves relative ordering of non-hook errors and of the primary
    within the output list.

    Replaces the previous two-pass chain
    (``_dedupe_lang_market_hook_errors`` → ``_collapse_hook_window_high_errors``)
    which worked correctly only by accident — pass 1 left exactly one
    hook-high so pass 2 early-returned. Any future tweak that let two
    survive pass 1 would have double-merged with "(Bổ sung: …)
    (Gộp: …)".
    """
    overlapping: list[dict[str, Any]] = []
    for e in errors:
        if (
            str(e.get("sev") or "") == "high"
            and _is_hook_related_error(e)
            and _overlaps_hook_lang_dedupe_window(
                float(e.get("t") or 0.0),
                float(e.get("end") or e.get("t") or 0.0),
            )
        ):
            overlapping.append(e)
    if len(overlapping) <= 1:
        return errors

    primary = next(
        (e for e in overlapping if str(e.get("error_id") or "") == "lang_market_mismatch"),
        overlapping[0],
    )
    merged_fixes: list[str] = []
    for e in overlapping:
        if e is primary:
            continue
        fx = str(e.get("fix") or "").strip()
        if fx and fx not in str(primary.get("fix") or ""):
            merged_fixes.append(fx)
    out_primary = dict(primary)
    if merged_fixes:
        base = str(out_primary.get("fix") or "").strip()
        extra = "; ".join(merged_fixes[:3])
        out_primary["fix"] = f"{base} (Bổ sung: {extra})" if base else extra

    # Walk the original input once, dropping the siblings while
    # preserving every other error's order.
    siblings = {id(e) for e in overlapping if e is not primary}
    out: list[dict[str, Any]] = []
    for e in errors:
        if id(e) in siblings:
            continue
        out.append(out_primary if e is primary else e)
    return out


# Legacy names kept so existing tests + callers still link. Both
# delegate to the canonical single pass.
_collapse_hook_window_high_errors = _dedupe_hook_window_high_errors


def _product_led_silent_visual(analysis: dict[str, Any]) -> bool:
    """True when the opening is intentionally product-forward (no talking head expected)."""
    ha = analysis.get("hook_analysis") if isinstance(analysis.get("hook_analysis"), dict) else None
    if isinstance(ha, dict):
        fft = str(ha.get("first_frame_type") or "").strip().lower()
        if fft == "product":
            return True
    scenes = analysis.get("scenes") or []
    if not isinstance(scenes, list):
        return False
    for s in scenes[:4]:
        if not isinstance(s, dict):
            continue
        start = float(s.get("start") or 0.0)
        if start > 4.0:
            break
        stype = str(s.get("type") or "")
        subj = str(s.get("subject") or "")
        if stype == "product_shot" or subj == "product":
            return True
    return False


_dedupe_lang_market_hook_errors = _dedupe_hook_window_high_errors


def apply_rule_based_video_errors(
    errors: list[dict[str, Any]],
    analysis: dict[str, Any],
    content_format: str,
    *,
    caption_hint: str | None = None,
    duration_sec: float | None = None,
) -> list[dict[str, Any]]:
    """Augment Gemini error extraction with deterministic guards (language, presence)."""

    from getviews_pipeline.analysis_core import detect_language_market_mismatch
    from getviews_pipeline.analysis_guards import clamp_structural_error_timestamps

    out = list(errors)
    ha0 = analysis.get("hook_analysis") if isinstance(analysis.get("hook_analysis"), dict) else None
    hook_phrase = (ha0 or {}).get("hook_phrase") if isinstance(ha0, dict) else ""
    cap = str(caption_hint or "").strip()
    phrase = str(hook_phrase or "").strip()
    hook_text = f"{cap} {phrase}".strip()
    if hook_text:
        lang_error = detect_language_market_mismatch(hook_text)
        if lang_error:
            le = dict(lang_error)
            if le.get("end") is None:
                le["end"] = 0.0
            out.insert(0, le)

    has_human = bool(analysis.get("has_human_speaking_to_camera"))
    has_opinion = bool(analysis.get("has_expressed_opinion_or_question"))
    dur = float(duration_sec or 0.0)
    if dur <= 0:
        dur = float((analysis.get("duration_sec") or analysis.get("video_duration_sec") or 0) or 0.0)
    if dur <= 0:
        scenes = analysis.get("scenes") or []
        if isinstance(scenes, list) and scenes:
            last = scenes[-1]
            if isinstance(last, dict):
                dur = float(last.get("end") or 0.0)
    end_ts = float(dur) if dur > 0 else 11.0
    skip_no_human = (
        content_format in _SILENT_FORMAT_EXCEPTIONS_VIDEO
        or content_format in PRESENTER_NOT_REQUIRED_FORMATS
        or _product_led_silent_visual(analysis)
    )
    if (
        not has_human
        and not has_opinion
        and not skip_no_human
    ):
        out.append(
            {
                "error_id": "no_human_presence",
                "title": "Không có người nói chuyện với camera",
                "detail": (
                    "Video không có mặt người hoặc giọng nói trực tiếp. "
                    "Format này hoạt động tốt hơn khi có người dẫn dắt, "
                    "tạo kết nối cảm xúc với người xem."
                ),
                "fix": (
                    "Thêm ít nhất 2-3 giây mặt người nói chuyện thẳng với camera "
                    "tại hook hoặc giữa video."
                ),
                "sev": "mid",
                "t": 0.0,
                "end": end_ts,
            }
        )
    merged = _dedupe_hook_window_high_errors(out)
    clamp_dur = float(dur) if dur > 0 else None
    return clamp_structural_error_timestamps(merged, clamp_dur)


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
    user_sb: Any | None = None,
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

    nid_kpi = int(video.get("niche_id") or 0)
    (save_p25, save_p75), (share_p25, share_p75) = (
        fetch_niche_save_share_pct_quantiles_sync(user_sb, nid_kpi)
        if user_sb is not None and nid_kpi
        else ((None, None), (None, None))
    )

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
            "engagement_rate": float(video.get("engagement_rate") or 0.0),
            "niche_label": niche_label or None,
            "niche_id": int(video.get("niche_id") or 0),
            "retention_source": retention_source,
            "creator_median_views": creator_median_views,
            "target_vs_creator_median": target_vs_creator_median,
            # Declared on VideoMeta (report_types.py:469) but previously
            # never set — typed FE consumers always read None. Populate
            # from the corpus row's raw counts / classifiers.
            "saves": int(video.get("saves") or 0) if video.get("saves") is not None else None,
            "is_breakout": float(video.get("breakout_multiplier") or 0.0) >= 1.5,
        },
        "enrichment": enrichment,
        "kpis": build_kpis(
            video,
            niche_meta,
            mode=mode,
            retention_end_pct=ret_end,
            cohort_save_p25_pct=save_p25,
            cohort_save_p75_pct=save_p75,
            cohort_share_p25_pct=share_p25,
            cohort_share_p75_pct=share_p75,
        ),
        "segments": diag.get("segments") or [],
        "hook_phases": diag.get("hook_phases") or [],
        "errors": diag.get("flop_issues") or [],
        "retention_curve": ret_curve,
        "niche_benchmark_curve": bench_curve,
        "niche_meta": niche_meta,
        "cross_format_signal": cross_format_signal,
        # Cached narrative-layer fields from video_diagnostics
        # (migration 20260513000003). When present, finalize_video_narrative_layer
        # early-returns and skips the Gemini synthesis call.
        "narrative_vi": diag.get("narrative_vi"),
        "format_cards": diag.get("format_cards"),
        "diagnosis": diag.get("diagnosis"),
        "performance_tier": diag.get("performance_tier"),
        "bright_spot_signal": diag.get("bright_spot_signal"),
        "view_scenarios": diag.get("view_scenarios"),
        "channel_context": diag.get("channel_context"),
        "reference_videos": diag.get("reference_videos"),
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


def extract_video_errors(
    *,
    extraction_mode: Literal["win", "flop"],
    video: dict[str, Any],
    analysis: dict[str, Any],
    niche_label: str,
    niche_row: dict[str, Any] | None,
    retention_curve: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Call 1 — Gemini extracts ``VideoFlopIssue``-shaped errors (+ ``error_id``)."""

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

    if extraction_mode == "win":
        mode_block = """## Chế độ WIN (video đang hoạt động tốt)

- Trích xuất **0–3** vấn đề tiềm ẩn hoặc polish (sev chỉ **mid** hoặc **low**).
- Nếu không có vấn đề đáng kể, trả `"errors": []`.
- **Không** dùng sev **high** trừ khi có lỗi cấu trúc rõ ràng trong phân tích."""
    else:
        mode_block = """## Chế độ FLOP (video yếu so với ngách)

- Trích xuất **ít nhất 1**, tối đa 8 mục ``errors``, xếp theo độ nghiêm trọng (high → low).
- Mỗi mục PHẢI có ``error_id`` ổn định dạng ERR_* (vd ERR_hook_late_face)."""

    prompt = f"""Bạn là chẩn đoán cấu trúc TikTok tiếng Việt.

{mode_block}

Ngách: {niche_label}
{niche_summary}
Video: @{video.get("creator_handle", "")} | views {int(video.get("views") or 0)} | ER {float(video.get("engagement_rate") or 0):.4f}
Hook phrase: {hook.get("hook_phrase") or ""}
{retention_summary}

## Severity (chế độ flop)

- high: retention drop >30% trong <2s, hook miss 0-3s, CTA conflict — phải fix mới hy vọng cải thiện.
- mid: drop 15-30% 2-5s, structure issue — đáng fix.
- low: polish (text, sound, CTA wording).

## Fix vocabulary cho ``fix`` (action-driven, có placeholder cụ thể)

- "Đổi hook sang [type]" | "Cắt scene [N]" | "Đẩy CTA xuống giây [X]" | "Thay sound trending [genre]" | "Thêm text overlay tại giây [X]" | "Compress hook về dưới [X]s"

## Schema JSON — trả về một object duy nhất

`{{ "errors": [ {{ "error_id", "sev", "t", "end", "title", "detail", "fix" }} ] }}`

- ``t`` / ``end``: giây trên timeline video.
- TRÁNH: {_FORBIDDEN_PHRASES_VI}
"""

    config = types.GenerateContentConfig(
        temperature=0.45,
        response_mime_type="application/json",
        response_json_schema=VideoErrorsExtractionLLM.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    parsed = VideoErrorsExtractionLLM.model_validate_json(_normalize_response(raw))
    items = [e.model_dump() for e in parsed.errors]
    if extraction_mode == "flop" and not items:
        items = [
            {
                "error_id": "ERR_fallback_extraction",
                "sev": "mid",
                "t": 0.0,
                "end": 3.0,
                "title": "Cần xem lại hook và pacing mở đầu",
                "detail": (
                    "Không trích xuất được lỗi cụ thể từ model — xem lại 3 giây đầu và retention."
                ),
                "fix": "Compress hook về dưới 1.5s với payoff rõ trong frame đầu.",
            }
        ]
    return items


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


def _corpus_aweme_to_synthesis_ref(aweme: dict[str, Any]) -> dict[str, Any]:
    """Shape a corpus pool aweme like ``run_video_diagnosis`` analyzed refs."""
    from getviews_pipeline.output_redesign import hook_type_vi

    stats = aweme.get("statistics") or {}
    views = int(stats.get("play_count") or 0)
    handle = (aweme.get("author") or {}).get("unique_id") or ""
    corpus_analysis = aweme.get("_corpus_analysis") or {}
    raw_hook_type = (corpus_analysis.get("hook_analysis") or {}).get("hook_type") or ""
    return {
        "aweme_id": aweme["aweme_id"],
        "analysis": corpus_analysis,
        "metadata": {
            "video_id": aweme["aweme_id"],
            "author": {"username": handle},
            "views": views,
            "tiktok_url": aweme.get("_corpus_tiktok_url", ""),
            "thumbnail_url": aweme.get("thumbnail_url"),
            "days_ago": aweme.get("_corpus_days_ago", 0),
            "breakout": aweme.get("_corpus_breakout", 0.0),
            "hook_type": raw_hook_type,
            "hook_type_vi": hook_type_vi(raw_hook_type),
            "content_type": aweme.get("_corpus_content_type", "video"),
        },
    }


def _live_analyzed_to_slim_input(result: dict[str, Any]) -> dict[str, Any]:
    """Shape ``analyze_aweme`` output like an aweme dict for ``_slim_reference_video``."""
    meta = result.get("metadata") or {}
    vid = str(meta.get("video_id") or "")
    author = meta.get("author") if isinstance(meta.get("author"), dict) else {}
    handle = str(author.get("username") or "").lstrip("@")
    metrics = meta.get("metrics") if isinstance(meta.get("metrics"), dict) else {}
    desc = str(meta.get("description") or "")[:120]
    return {
        "aweme_id": vid,
        "author": {"unique_id": handle},
        "thumbnail_url": meta.get("thumbnail_url"),
        "statistics": {"play_count": metrics.get("views")},
        "desc": desc or None,
        "engagement_rate": meta.get("engagement_rate"),
        "analysis": result.get("analysis"),
    }


async def _live_search_references_for_finalize(
    niche_name: str,
    target_video_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """EnsembleData niche pool + ``analyze_aweme`` — mirrors sparse path in ``run_video_diagnosis``."""
    from getviews_pipeline.analysis_core import analyze_aweme
    from getviews_pipeline.helpers import select_reference_videos
    from getviews_pipeline.pipelines import REF_N, _niche_aweme_pool, _slim_reference_video
    from getviews_pipeline.runtime import get_analysis_semaphore

    pool = await _niche_aweme_pool(niche_name, period=30)
    skip = {target_video_id} if target_video_id else set()
    picks = select_reference_videos(
        pool, recency_days=30, n=REF_N, cached_ids=skip, rank_by="er"
    )
    if not picks:
        return [], []

    sem = get_analysis_semaphore()

    async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
        try:
            async with sem:
                return await asyncio.wait_for(
                    analyze_aweme(aweme, include_diagnosis=False, full_analyses=None),
                    timeout=120.0,
                )
        except (TimeoutError, Exception) as exc:
            logger.warning(
                "[finalize_narrative] live ref analyze failed aweme_id=%s: %s",
                aweme.get("aweme_id"),
                exc,
            )
            return {"_skipped": True}

    results = await asyncio.gather(*[_one(a) for a in picks])
    synthesis_refs: list[dict[str, Any]] = []
    slim_refs: list[dict[str, Any]] = []
    for res in results:
        if not isinstance(res, dict) or res.get("_skipped") or "analysis" not in res:
            continue
        meta = res.get("metadata") or {}
        vid = str(meta.get("video_id") or "")
        if not vid:
            continue
        synthesis_refs.append({**res, "aweme_id": vid})
        slim_refs.append(
            _slim_reference_video(_live_analyzed_to_slim_input(res), "live_search")
        )

    if not synthesis_refs:
        return [], []
    return synthesis_refs, slim_refs


def _select_corpus_references_for_finalize(
    niche_name: str,
    target_video_id: str,
    *,
    preferred_content_format: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Corpus refs when pool ≥ REF_N; otherwise Ensemble live search + on-demand analysis."""
    from getviews_pipeline.corpus_context import fetch_corpus_reference_pool_sync
    from getviews_pipeline.pipelines import REF_N, _slim_reference_video

    if not niche_name.strip() or not target_video_id.strip():
        return [], []
    pool = fetch_corpus_reference_pool_sync(
        niche_name, days=30, limit=40, exclude_video_id=target_video_id
    )
    pref = str(preferred_content_format or "").strip().lower()
    if pref:
        pool.sort(
            key=lambda v: (
                0 if str(v.get("_corpus_content_format") or "").strip().lower() == pref else 1,
                -float(v.get("_corpus_er") or 0.0),
            ),
        )
    else:
        pool.sort(key=lambda v: -float(v.get("_corpus_er") or 0.0))
    if len(pool) >= REF_N:
        skip = {target_video_id}
        picks = [v for v in pool if v.get("aweme_id") not in skip][:REF_N]
        if len(picks) >= REF_N:
            synthesis = [_corpus_aweme_to_synthesis_ref(p) for p in picks]
            slim = [_slim_reference_video(p, "corpus") for p in picks]
            return synthesis, slim

    try:
        return asyncio.run(_live_search_references_for_finalize(niche_name, target_video_id))
    except Exception as exc:
        logger.warning("[finalize_narrative] live reference search failed: %s", exc)
        return [], []


def finalize_video_narrative_layer(
    out: dict[str, Any],
    *,
    step_queue: Any | None = None,
) -> None:
    """Call 2 — narrative synthesis + SSE; mutates *out* in place.

    Expects ``out`` to contain private keys ``__narrative_analysis`` and
    ``__narrative_content_format`` (stripped before return to clients) set by
    ``run_video_analyze_pipeline`` / ``run_video_analyze_on_demand``.

    Idempotent: when ``out`` already carries cached narrative fields
    (set by ``_response_from_diagnostics_row`` on a video_diagnostics
    cache hit), this function returns without re-firing the Gemini
    synthesis call. The cache is populated below on the cache-miss path.
    """

    # Cache hit short-circuit. narrative_vi is the anchor — when it
    # exists, every dependent field (format_cards, performance_tier,
    # bright_spot_signal, view_scenarios, channel_context,
    # reference_videos, diagnosis) was written in the same upsert.
    if out.get("narrative_vi"):
        # Strip pipeline-private keys so the response shape stays clean
        # for the caller (matches the post-synthesis branch below).
        out.pop("__narrative_analysis", None)
        out.pop("__narrative_content_format", None)
        return

    from getviews_pipeline.gemini import synthesize_diagnosis_v2
    from getviews_pipeline.pipelines import (
        _estimate_er_percentile_rank,
        _truncate_transcripts,
        classify_performance_tier_corpus,
        compute_bright_spot_signal,
        compute_view_scenarios,
        enrich_format_cards_from_corpus,
        fetch_channel_context_sync,
        refine_performance_tier,
    )
    from getviews_pipeline.step_events import emit

    analysis: dict[str, Any] = out.pop("__narrative_analysis", None) or {}
    content_format: str = str(out.pop("__narrative_content_format", "") or "")
    meta: dict[str, Any] = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    niche_meta: dict[str, Any] = (
        out.get("niche_meta") if isinstance(out.get("niche_meta"), dict) else {}
    )

    niche_name = str(meta.get("niche_label") or "")
    video_id = str(out.get("video_id") or "")
    synthesis_refs, slim_refs = _select_corpus_references_for_finalize(
        niche_name,
        video_id,
        preferred_content_format=content_format or None,
    )
    out["reference_videos"] = slim_refs

    views = int(meta.get("views") or 0)
    corpus_avg_views = float(niche_meta.get("avg_views") or 0.0)
    performance_tier: str = classify_performance_tier_corpus(views, corpus_avg_views or None)

    channel_context_payload: dict[str, Any] | None = None
    creator_handle = str(meta.get("creator") or "").strip()
    if creator_handle and video_id:
        try:
            raw_ctx = fetch_channel_context_sync(creator_handle, video_id)
            if raw_ctx and raw_ctx.get("available"):
                channel_context_payload = raw_ctx
                performance_tier = refine_performance_tier(performance_tier, views, raw_ctx)
        except Exception:
            logger.debug("[video_narrative] channel context fetch failed")

    if step_queue is not None:
        emit(
            step_queue,
            {
                "type": "pre_synthesis",
                "performance_tier": performance_tier,
                "reference_videos": out.get("reference_videos") or [],
            },
        )
        if channel_context_payload:
            emit(
                step_queue,
                {"type": "channel_context", "channel_context": channel_context_payload},
            )

    corpus_size = int(niche_meta.get("sample_size") or niche_meta.get("corpus_size") or 0)
    user_stats: dict[str, Any] = {
        "views": views,
        "likes": int(meta.get("likes") or 0),
        "comments": int(meta.get("comments") or 0),
        "shares": int(meta.get("shares") or 0),
        "duration_sec": float(meta.get("duration_sec") or 0.0),
        "save_rate": float(meta.get("save_rate") or 0.0),
    }

    errors: list[dict[str, Any]] = list(out.get("errors") or [])
    user_er = float(meta.get("engagement_rate") or 0.0)
    raw_ae = niche_meta.get("avg_engagement_rate")
    raw_me = niche_meta.get("median_er")
    try:
        niche_avg_er = float(raw_ae) if raw_ae is not None else None
    except (TypeError, ValueError):
        niche_avg_er = None
    if niche_avg_er is None or niche_avg_er <= 0:
        try:
            niche_avg_er = float(raw_me) if raw_me is not None else None
        except (TypeError, ValueError):
            niche_avg_er = None
    if niche_avg_er is not None and niche_avg_er <= 0:
        niche_avg_er = None
    er_percentile_rank = _estimate_er_percentile_rank(user_er, niche_avg_er)
    try:
        cohort_avg_views = float(niche_meta.get("avg_views") or 0) or None
    except (TypeError, ValueError):
        cohort_avg_views = None
    if cohort_avg_views is not None and cohort_avg_views <= 0:
        cohort_avg_views = None
    views_vs_avg_ratio = (
        float(views) / cohort_avg_views if cohort_avg_views and views >= 0 else None
    )
    curve_raw = out.get("retention_curve")
    retention_end_pct: float | None = None
    if isinstance(curve_raw, list) and curve_raw:
        last_pt = curve_raw[-1]
        if isinstance(last_pt, dict) and last_pt.get("pct") is not None:
            try:
                retention_end_pct = float(last_pt["pct"])
            except (TypeError, ValueError):
                retention_end_pct = None
    ch_ratio_hint = meta.get("target_vs_creator_median")
    try:
        ch_ratio_f = float(ch_ratio_hint) if ch_ratio_hint is not None else None
    except (TypeError, ValueError):
        ch_ratio_f = None
    bright_spot_computed = compute_bright_spot_signal(
        er_percentile_rank,
        views_vs_avg_ratio,
        retention_end_pct=retention_end_pct,
        channel_views_ratio=ch_ratio_f,
    )
    view_scenarios_computed = compute_view_scenarios(
        performance_tier=performance_tier,
        views_vs_avg_ratio=views_vs_avg_ratio,
        channel_views_ratio=ch_ratio_f,
    )
    errors_prompt = list(errors)
    if performance_tier == "hit":
        high_only = [e for e in errors_prompt if str(e.get("sev")) == "high"]
        if high_only:
            errors_prompt = high_only

    diagnosis_md = ""
    narrative_vi_out: dict[str, Any] | None = None
    format_cards_out: list[dict[str, Any]] | None = None
    try:
        diagnosis_md, narrative_vi_out, format_cards_out = synthesize_diagnosis_v2(
            content_format=content_format or "unknown",
            niche_name=niche_name or "unknown",
            corpus_size=corpus_size,
            niche_norms=niche_meta,
            reference_videos=_truncate_transcripts(synthesis_refs),
            user_analysis=analysis,
            user_stats=user_stats,
            performance_tier=performance_tier,
            channel_context=channel_context_payload,
            errors=errors_prompt or None,
            reference_evidence_block="",
        )
    except Exception:
        logger.exception("[video_narrative] synthesize_diagnosis_v2 failed")

    if narrative_vi_out is not None:
        dur_note = float(meta.get("duration_sec") or user_stats.get("duration_sec") or 0.0)
        # er_percentile_rank here is a ratio-derived score (~5–95), not a literal corpus
        # percentile — treat as a low-engagement proxy vs retention on short clips.
        if (
            dur_note > 0
            and dur_note <= 15.0
            and retention_end_pct is not None
            and retention_end_pct >= 75.0
            and er_percentile_rank is not None
            and er_percentile_rank < 40.0
        ):
            note = (
                "Lưu ý: với video ngắn dưới 15 giây, tỷ lệ giữ chân cao thường "
                "phản ánh độ dài clip chứ không phải mức độ quan tâm thực sự — "
                "chỉ số quyết định phân phối vẫn là ER và tỷ lệ lưu."
            )
            vd0 = str(narrative_vi_out.get("van_de_chinh") or "").strip()
            if note not in vd0:
                narrative_vi_out["van_de_chinh"] = f"{vd0} {note}".strip() if vd0 else note

    niche_id_finalize = int(meta.get("niche_id") or 0)
    if format_cards_out and niche_id_finalize:
        format_cards_out = enrich_format_cards_from_corpus(
            format_cards_out,
            niche_id_finalize,
            analyzed_content_format=content_format or None,
        )

    if step_queue is not None:
        emit(
            step_queue,
            {
                "type": "narrative_ready",
                "narrative_vi": narrative_vi_out,
                "format_cards": format_cards_out,
                "errors": errors,
                **(
                    {"bright_spot_signal": bright_spot_computed}
                    if bright_spot_computed is not None
                    else {}
                ),
                **(
                    {"view_scenarios": view_scenarios_computed}
                    if view_scenarios_computed is not None
                    else {}
                ),
            },
        )

    out["errors"] = errors
    out["structural_errors"] = errors
    if bright_spot_computed is not None:
        out["bright_spot_signal"] = bright_spot_computed
    if view_scenarios_computed is not None:
        out["view_scenarios"] = view_scenarios_computed
    out["performance_tier"] = performance_tier
    if channel_context_payload:
        out["channel_context"] = channel_context_payload
    if narrative_vi_out is not None:
        out["narrative_vi"] = narrative_vi_out
    if format_cards_out is not None:
        out["format_cards"] = format_cards_out
    if diagnosis_md:
        out["diagnosis"] = diagnosis_md

    # Persist the narrative layer alongside the deterministic one so
    # the next request on the same video_id within the diagnostics TTL
    # short-circuits at the top of this function. on_demand outputs
    # don't have a corpus row (and aren't cached), so guard by
    # presence of __cache_video_id which run_video_analyze_pipeline
    # sets on the corpus path only.
    cache_vid = out.pop("__cache_video_id", None)
    if cache_vid and narrative_vi_out is not None:
        try:
            from getviews_pipeline.supabase_client import get_service_client

            get_service_client().table("video_diagnostics").update(
                {
                    "narrative_vi": narrative_vi_out,
                    "format_cards": format_cards_out,
                    "diagnosis": diagnosis_md or None,
                    "performance_tier": performance_tier,
                    "bright_spot_signal": bright_spot_computed,
                    "view_scenarios": view_scenarios_computed,
                    "channel_context": channel_context_payload or None,
                    "reference_videos": out.get("reference_videos"),
                },
            ).eq("video_id", cache_vid).execute()
        except Exception as exc:
            # Non-fatal — failing to cache only loses the cost saving,
            # not the user-visible response. Bubble exception to logs.
            logger.warning(
                "[video_narrative] persist failed video_id=%s: %s", cache_vid, exc,
            )


def run_video_analyze_pipeline(
    service_sb: Any,
    user_sb: Any,
    *,
    video_id: str | None,
    tiktok_url: str | None,
    force_refresh: bool = False,
    mode: Literal["win", "flop"] | None = None,
    step_queue: Any | None = None,
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
        user_sb,
        content_class_id=content_class_id,
        content_format=str(video.get("content_format") or "").strip() or None,
    )
    default_niche_meta = {
        "avg_views": None,
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

    if (
        diag_row
        and _diagnostics_fresh(diag_row)
        and not bypass_cache
        and not _diagnostics_legacy(diag_row)
    ):
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
            user_sb=user_sb,
        )
        base["__narrative_analysis"] = analysis
        base["__narrative_content_format"] = str(video.get("content_format") or "")
        # Cache key for finalize_video_narrative_layer's persist step.
        # Set only on the corpus path; on-demand outputs aren't cached.
        base["__cache_video_id"] = vid
        return _merge_sidecars_into_response(
            base,
            video_id=vid,
            comment_count_hint=int(video.get("comments") or 0),
        )

    if diag_row and _diagnostics_fresh(diag_row) and not bypass_cache and _diagnostics_legacy(diag_row):
        logger.info(
            "[video_analyze] stale diagnostics schema — recomputing video_id=%s",
            vid,
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
    extraction_mode: Literal["win", "flop"] = "win" if mode_resolved == "win" else "flop"
    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_process

        emit(step_queue, step_process("Đang trích xuất lỗi cấu trúc (Gemini)..."))
    raw_errs = extract_video_errors(
        extraction_mode=extraction_mode,
        video=video,
        analysis=analysis,
        niche_label=gemini_niche_label,
        niche_row=niche_intel,
        retention_curve=retention_user,
    )
    content_format_str = str(video.get("content_format") or "")
    errors = apply_rule_based_video_errors(
        raw_errs,
        analysis,
        content_format_str,
        caption_hint=(str(video.get("caption") or "").strip() or None),
        duration_sec=float(dur) if dur > 0 else None,
    )
    for _h in hook_cards:
        if isinstance(_h, dict) and "body" in _h:
            del _h["body"]

    upsert_payload = {
        "video_id": vid,
        "analysis_headline": None,
        "analysis_subtext": None,
        "lessons": [],
        "hook_phases": hook_cards,
        "segments": segments,
        "flop_issues": errors,
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
        user_sb=user_sb,
    )
    out["__narrative_analysis"] = analysis
    out["__narrative_content_format"] = content_format_str
    out["__cache_video_id"] = vid
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
        "caption": (metadata.description or str(aweme.get("desc") or "")).strip()
        or None,
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
    step_queue: Any | None = None,
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
    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_process

        emit(
            step_queue,
            step_process("Đang tải video TikTok và phân tích khung hình (Gemini)..."),
        )
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
        user_sb,
        content_class_id=content_class_id,
        content_format=str(video.get("content_format") or "").strip() or None,
    )
    default_niche_meta = {
        "avg_views": None,
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
    extraction_mode_od: Literal["win", "flop"] = "win" if mode_resolved == "win" else "flop"
    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_process

        emit(step_queue, step_process("Đang trích xuất lỗi cấu trúc (Gemini)..."))
    raw_errs_od = extract_video_errors(
        extraction_mode=extraction_mode_od,
        video=video,
        analysis=analysis,
        niche_label=gemini_niche_label,
        niche_row=niche_intel,
        retention_curve=retention_user,
    )
    content_format_str_od = str(video.get("content_format") or "")
    _caption_od = str(video.get("caption") or "").strip()
    errors_od = apply_rule_based_video_errors(
        raw_errs_od,
        analysis,
        content_format_str_od,
        caption_hint=_caption_od or None,
        duration_sec=float(dur) if dur > 0 else None,
    )
    for _h in hook_cards:
        if isinstance(_h, dict) and "body" in _h:
            del _h["body"]

    diag_synth = {
        "video_id": vid,
        "analysis_headline": None,
        "analysis_subtext": None,
        "lessons": [],
        "hook_phases": hook_cards,
        "segments": segments,
        "flop_issues": errors_od,
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
        user_sb=user_sb,
    )
    out["__narrative_analysis"] = analysis
    out["__narrative_content_format"] = content_format_str_od
    # Flag the response so the FE can render a subtle "phân tích trực tiếp"
    # badge — corpus rows don't set this, so the FE only highlights when
    # explicitly truthy.
    out["source"] = "on_demand"
    return out
