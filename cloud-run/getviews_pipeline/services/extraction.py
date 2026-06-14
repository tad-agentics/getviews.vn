"""Gemini error-extraction primitives + extraction core.

This module is the canonical home for:
- The Pydantic schemas that govern Gemini's structured JSON output (VideoErrorsExtractionLLM)
- apply_rule_based_video_errors — deterministic post-processing guards
- extract_video_errors — Gemini Call 1 (structured error list)
- run_extraction_core — typed extraction boundary (Phase 3.1)

Moved here from video_analyze.py during Phase 1.1 (services/ extraction) to break the
circular dependency between pipelines.py and video_analyze.py. pipelines.py now imports
these from services/extraction; video_analyze.py re-exports them from here for backward
compatibility with existing callers and tests.

Import graph: services/extraction → (gemini, config, analysis_core, analysis_guards)
No import from pipelines.py or video_analyze.py.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from getviews_pipeline.models import ExtractionResult
from getviews_pipeline.voice_lint import build_forbidden_phrases_prompt_block

logger = logging.getLogger(__name__)

# ── Pydantic output schemas for Gemini Call 1 ──────────────────────────────


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


# ── Phase 3.7.1 — Typed JSON input contract for extract_video_errors ─────────

class VideoErrorsExtractionInput(BaseModel):
    """Typed input contract for the Gemini error-extraction prompt (Phase 3.7.1).

    Replaces ad-hoc f-string field injection with a validated, serialisable model.
    The entire instance is serialised to JSON and injected into the prompt as a
    structured data block so Gemini always sees the same field names as the
    TypeScript and Pydantic output schemas.

    This is the LLM INPUT boundary — paired with ``VideoErrorsExtractionLLM``
    (output) to give full round-trip auditing via the Phase 2.3 schema-contract
    CI test.
    """

    extraction_mode: Literal["win", "flop", "average"]
    niche_label: str = Field(max_length=80)
    niche_avg_views: float | None = None
    niche_avg_retention: float | None = None
    niche_sample_size: int | None = None
    creator_handle: str = Field(default="", max_length=80)
    views: int = Field(ge=0)
    engagement_rate: float = Field(ge=0.0)
    hook_phrase: str = Field(default="", max_length=300)
    content_format: str = Field(default="", max_length=80)
    """Detected content format (tutorial, review, vlog, etc.)."""
    duration_sec: float | None = None
    """Video duration in seconds; None when unknown."""
    retention_drop_pct_3s: float | None = None
    """Percentage of viewers remaining at 3s (0.0–1.0). None = modeled/unknown."""
    retention_drop_pct_10s: float | None = None
    """Percentage of viewers remaining at 10s."""
    # HI-18 — flattened from HI-9 `analysis` for niche-aware error detection
    content_context_subject_matter: str | None = Field(default=None, max_length=500)
    niche_classification_creator_niche_slug: str | None = Field(default=None, max_length=48)
    niche_classification_format_axis: str | None = Field(default=None, max_length=48)
    # Extraction signals v2 — Tier 1 (deterministic) + Tier 2 hook forensics
    time_to_first_value_sec: float | None = None
    words_per_sec: float | None = None
    dead_air_ratio: float | None = None
    loop_score: float | None = None
    redundancy_runs: int | None = None
    opening_visual_energy: str | None = Field(default=None, max_length=16)
    text_speech_sync: str | None = Field(default=None, max_length=24)
    pattern_interrupt: bool | None = None


# ── Format / presence guards ────────────────────────────────────────────────

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

# Back-compat: tests + video_analyze re-export assert clichés appear in prompt text.
_FORBIDDEN_PHRASES_VI: str = build_forbidden_phrases_prompt_block()

# Closed [0, _HOOK_LANG_DEDUPE_WINDOW_END_SEC] — overlap with error [t, end] dedupes vs lang_market.
_HOOK_LANG_DEDUPE_WINDOW_END_SEC = 4.0


# ── Hook-window dedup helpers ───────────────────────────────────────────────


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


# Legacy aliases kept so existing tests + callers still link.
_collapse_hook_window_high_errors = _dedupe_hook_window_high_errors
_dedupe_lang_market_hook_errors = _dedupe_hook_window_high_errors


# ── Silent-visual guard ─────────────────────────────────────────────────────


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


# ── Prompt-context helpers ──────────────────────────────────────────────────


def _summarise_retention_curve(
    curve: list[dict[str, Any]] | None,
    risk_events: list[dict[str, Any]] | None = None,
) -> str:
    """Compress a retention curve into a 1-line summary for prompt context.

    Identifies the steepest drop (timing + magnitude) so Gemini can anchor
    diagnosis to where viewers actually leave. When ``risk_events`` are present,
    names the structural cause. Returns "" when the curve has fewer than 3 points.
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
    biggest_drop = 0.0
    drop_at = 0.0
    drop_to = 0.0
    for i in range(len(points) - 1):
        delta = points[i + 1][1] - points[i][1]
        if delta < biggest_drop:
            biggest_drop = delta
            drop_at = points[i][0]
            drop_to = points[i + 1][1]
    end_pct = points[-1][1]

    top_risk: dict[str, Any] | None = None
    if isinstance(risk_events, list) and risk_events:
        top_risk = risk_events[0] if isinstance(risk_events[0], dict) else None

    if top_risk and biggest_drop <= -3:
        reason = str(top_risk.get("reason_vi") or "").strip()
        if reason:
            # Honesty: cite a precise second only for ASR-timed drops; scene/approx
            # sources keep the window phrasing already baked into reason_vi.
            if str(top_risk.get("source") or "").lower() == "asr":
                t_risk = float(top_risk.get("t") or drop_at)
                head = f"Drop lớn nhất ~{_format_retention_ts(t_risk)}: {reason}"
            else:
                head = f"Drop lớn nhất: {reason}"
            return (
                f"Retention end {end_pct:.0f}%. {head} "
                f"({abs(biggest_drop):.0f}% → {drop_to:.0f}%)."
            )

    if biggest_drop > -3:
        return f"Retention end {end_pct:.0f}% — không có drop đột biến."
    return (
        f"Retention end {end_pct:.0f}%. Drop lớn nhất: "
        f"{abs(biggest_drop):.0f}% tại {drop_at:.1f}s → {drop_to:.0f}%."
    )


def _format_retention_ts(seconds: float) -> str:
    sec = max(0.0, float(seconds))
    m = int(sec // 60)
    s = int(round(sec % 60))
    return f"{m}:{s:02d}"


def _summarise_extraction_signals_v2(analysis: dict[str, Any]) -> str:
    """One-line grounding for Call 1 — compact measured signals only."""
    info = analysis.get("info_density") if isinstance(analysis.get("info_density"), dict) else {}
    loop = analysis.get("loopability") if isinstance(analysis.get("loopability"), dict) else {}
    hook = analysis.get("hook_analysis") if isinstance(analysis.get("hook_analysis"), dict) else {}
    parts: list[str] = []
    wps = info.get("words_per_sec")
    if wps is not None:
        try:
            parts.append(f"Mật độ {float(wps):.1f} từ/s")
        except (TypeError, ValueError):
            pass
    ttfv = info.get("time_to_first_value_sec")
    if ttfv is not None:
        try:
            parts.append(f"giá trị đầu {_format_retention_ts(float(ttfv))}")
        except (TypeError, ValueError):
            pass
    dead = info.get("dead_air_ratio")
    if dead is not None:
        try:
            parts.append(f"dead-air {float(dead) * 100:.0f}%")
        except (TypeError, ValueError):
            pass
    ls = loop.get("loop_score")
    if ls is not None:
        try:
            parts.append(f"loop {float(ls):.2f}")
        except (TypeError, ValueError):
            pass
    rr = loop.get("redundancy_runs")
    if rr is not None:
        try:
            if int(rr) >= 2:
                parts.append(f"redundancy {int(rr)} cảnh")
        except (TypeError, ValueError):
            pass
    ove = hook.get("opening_visual_energy")
    if ove:
        parts.append(f"visual {ove}")
    tss = hook.get("text_speech_sync")
    if tss and str(tss) != "none":
        parts.append(f"sync {tss}")
    pi = hook.get("pattern_interrupt")
    if pi is True:
        parts.append("pattern_interrupt")
    if not parts:
        return ""
    return "Tín hiệu cấu trúc: " + ", ".join(parts) + "."


def _extraction_signals_rule_block() -> str:
    return """
## Tín hiệu cấu trúc đo được (EXTRACTION_SIGNALS — nếu có trong JSON)

- Dùng `time_to_first_value_sec`, `words_per_sec`, `dead_air_ratio`, `loop_score`, `pattern_interrupt`… để neo lỗi hook/nhịp — KHÔNG bịa số.
- Chọn 1–2 tín hiệu lệch chuẩn mạnh nhất làm bằng chứng chính; KHÔNG liệt kê hết.
- Fix phải gắn mốc giây cụ thể khi ASR/word timing có (vd dồn câu chốt trước 0:02 nếu giá trị đầu ở 0:06).
"""


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


# ── Rule-based post-processing ──────────────────────────────────────────────


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


# ── Gemini Call 1: structured error extraction ──────────────────────────────


def extract_video_errors(
    *,
    extraction_mode: Literal["win", "flop", "average"],
    video: dict[str, Any],
    analysis: dict[str, Any],
    niche_label: str,
    niche_row: dict[str, Any] | None,
    retention_curve: list[dict[str, Any]] | None = None,
    retention_risk_events: list[dict[str, Any]] | None = None,
    max_findings: int = 3,
) -> list[dict[str, Any]]:
    """Call 1 — Gemini extracts ``VideoFlopIssue``-shaped errors (+ ``error_id``)."""

    import json as _json

    from google.genai import types

    from getviews_pipeline.config import (
        GEMINI_EXTRACTION_FALLBACKS,
        GEMINI_EXTRACTION_MODEL,
    )
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _normalize_response,
        _response_text,
    )
    from getviews_pipeline.settings import settings as pipeline_settings

    _ha = analysis.get("hook_analysis")
    hook = _ha if isinstance(_ha, dict) else {}
    niche_summary = _summarise_niche_row(niche_row)
    retention_summary = _summarise_retention_curve(retention_curve, retention_risk_events)
    signals_summary = ""
    signals_rule = ""
    if pipeline_settings.extraction_signals_v2:
        signals_summary = _summarise_extraction_signals_v2(analysis)
        if signals_summary:
            signals_rule = _extraction_signals_rule_block()

    info = analysis.get("info_density") if isinstance(analysis.get("info_density"), dict) else {}
    loop = analysis.get("loopability") if isinstance(analysis.get("loopability"), dict) else {}

    # Phase 3.7.1 — build typed input model and inject as JSON for auditability.
    # Gemini sees the same field names as the TypeScript/Pydantic schemas.
    _niche_row = niche_row or {}
    _retention_pts = retention_curve or []
    _r3 = next((pt.get("pct") for pt in _retention_pts if pt.get("t", 999) <= 3), None)
    _r10 = next((pt.get("pct") for pt in _retention_pts if 3 < (pt.get("t") or 999) <= 10), None)
    _cc = analysis.get("content_context")
    _nc = analysis.get("niche_classification")
    _subject: str | None = None
    if isinstance(_cc, dict):
        _sm = str(_cc.get("subject_matter") or "").strip()
        _subject = _sm[:500] if _sm else None
    _niche_slug: str | None = None
    _fmt_axis: str | None = None
    if isinstance(_nc, dict):
        _ns = _nc.get("creator_niche_slug")
        _fa = _nc.get("carousel_format_axis") or _nc.get("format_axis")
        if _ns is not None and str(_ns).strip():
            _niche_slug = str(_ns).strip()[:48]
        if _fa is not None and str(_fa).strip():
            _fmt_axis = str(_fa).strip()[:48]
    input_model = VideoErrorsExtractionInput(
        extraction_mode=extraction_mode,
        niche_label=niche_label or "unknown",
        niche_avg_views=float(_niche_row.get("avg_views") or 0) or None,
        niche_avg_retention=float(_niche_row.get("avg_retention") or 0) or None,
        niche_sample_size=int(_niche_row.get("sample_size") or 0) or None,
        creator_handle=str(video.get("creator_handle") or ""),
        views=int(video.get("views") or 0),
        engagement_rate=float(video.get("engagement_rate") or 0),
        hook_phrase=str(hook.get("hook_phrase") or "")[:300],
        content_format=str(video.get("content_format") or ""),
        duration_sec=None,  # unknown at this call site
        retention_drop_pct_3s=float(_r3) if _r3 is not None else None,
        retention_drop_pct_10s=float(_r10) if _r10 is not None else None,
        content_context_subject_matter=_subject,
        niche_classification_creator_niche_slug=_niche_slug,
        niche_classification_format_axis=_fmt_axis,
        time_to_first_value_sec=(
            float(info["time_to_first_value_sec"])
            if pipeline_settings.extraction_signals_v2
            and info.get("time_to_first_value_sec") is not None
            else None
        ),
        words_per_sec=(
            float(info["words_per_sec"])
            if pipeline_settings.extraction_signals_v2 and info.get("words_per_sec") is not None
            else None
        ),
        dead_air_ratio=(
            float(info["dead_air_ratio"])
            if pipeline_settings.extraction_signals_v2 and info.get("dead_air_ratio") is not None
            else None
        ),
        loop_score=(
            float(loop["loop_score"])
            if pipeline_settings.extraction_signals_v2 and loop.get("loop_score") is not None
            else None
        ),
        redundancy_runs=(
            int(loop["redundancy_runs"])
            if pipeline_settings.extraction_signals_v2 and loop.get("redundancy_runs") is not None
            else None
        ),
        opening_visual_energy=(
            str(hook.get("opening_visual_energy") or "")[:16] or None
            if pipeline_settings.extraction_signals_v2
            else None
        ),
        text_speech_sync=(
            str(hook.get("text_speech_sync") or "")[:24] or None
            if pipeline_settings.extraction_signals_v2
            else None
        ),
        pattern_interrupt=(
            bool(hook["pattern_interrupt"])
            if pipeline_settings.extraction_signals_v2 and hook.get("pattern_interrupt") is not None
            else None
        ),
    )
    input_json = _json.dumps(input_model.model_dump(exclude_none=True), ensure_ascii=False)

    cap = max(1, min(int(max_findings), 8))
    if extraction_mode == "win":
        mode_block = f"""## Chế độ WIN (video đang hoạt động tốt)

- Trích xuất **0–{min(3, cap)}** vấn đề tiềm ẩn hoặc polish (sev chỉ **mid** hoặc **low**).
- Nếu không có vấn đề đáng kể, trả `"errors": []`.
- **Không** dùng sev **high** trừ khi có lỗi cấu trúc rõ ràng trong phân tích.
- title: tên ngắn gọn (≤5 từ), không dùng emoji, không dùng mã lỗi."""
    elif extraction_mode == "average":
        mode_block = f"""## Chế độ TRUNG BÌNH (video quanh chuẩn ngách — KHÔNG phải flop)

- Đừng viết như đang mổ xẻ một video hỏng. Đây là video quanh mức chuẩn của format.
- Trích xuất **0-{cap}** vấn đề CÓ BẰNG CHỨNG từ phân tích khung hình / retention — sev theo đúng bằng chứng (kể cả high nếu rõ ràng).
- Không có vấn đề rõ → trả `"errors": []`. TUYỆT ĐỐI không bịa lỗi cho đủ danh sách.
- Mỗi mục PHẢI có ``error_id`` ổn định dạng ERR_* (vd ERR_hook_late_face).
- title: tiếng Việt, ≤10 từ, không emoji, không mã lỗi."""
    else:
        mode_block = f"""## Chế độ FLOP (video yếu so với ngách)

- Trích xuất **đúng 1–{cap} lỗi nghiêm trọng nhất**, xếp theo độ nghiêm trọng (high → low).
- Tối đa {cap} mục — chọn lỗi có impact lớn nhất, không liệt kê tất cả.
- Mỗi mục PHẢI có ``error_id`` ổn định dạng ERR_* (vd ERR_hook_late_face).
- title: tiếng Việt, ≤10 từ, không emoji, không mã lỗi. Được dùng em-dash (—) để ghép hai ý trái chiều.
  Ví dụ ĐÚNG: "Không có hook — chỉ có không khí", "Sản phẩm bị lẫn bởi cảnh quay", "Im lặng hoàn toàn — không có giọng người".
  Ví dụ SAI: "Hook mở đầu yếu" (quá chung), "ERR001: hook" (có mã lỗi)."""

    prompt = f"""Bạn là chẩn đoán cấu trúc TikTok tiếng Việt.

{mode_block}

## Dữ liệu đầu vào (JSON)

```json
{input_json}
```

{niche_summary}
{retention_summary}
{signals_summary}
{signals_rule}

## Tín hiệu HI-9 (có thể null trong JSON trên)

Nếu `content_context_subject_matter` hoặc `niche_classification_*` không null:
- Dùng subject_matter để phát hiện lệch lời hứa hook ↔ chủ đề thân bài (promise-content mismatch) khi có bằng chứng từ phân tích khung hình.
- Dùng creator_niche_slug + format_axis để tránh gán lỗi "tone ngách" mù: nếu slug khớp `niche_label` benchmark thì ưu tiên lỗi cấu trúc/cắt hình; nếu lệch rõ, có thể gợi ý **một** lỗi phân phối/định vị (sev mid/low) kèm rationale cụ thể, không phóng đại.

## Severity (chế độ flop)

- high: retention drop >30% trong <2s, hook miss 0-3s, CTA conflict — phải fix mới hy vọng cải thiện.
- mid: drop 15-30% 2-5s, structure issue — đáng fix.
- low: polish (text, sound, CTA wording).

## Fix vocabulary cho ``fix`` (action-driven, có placeholder cụ thể)

Mỗi fix PHẢI có 2 phần: [hành động cụ thể tại giây X] + [ví dụ in thực tế].
Cấu trúc: "[Hành động] — ví dụ '[text/cảnh cụ thể]'"
Ví dụ ĐÚNG:
- "Thêm text overlay ngay giây 0 — ví dụ 'Đồng hồ này phối được với mọi outfit công sở.'"
- "Cắt cảnh cà phê. Mở bằng macro close-up mặt sản phẩm, sau đó mới reveal bối cảnh."
- "Thêm câu hỏi qua text tại giây 10 — ví dụ 'Bạn chọn màu đen hay màu trắng?'"
Ví dụ SAI: "Thêm text overlay" (không có vị trí + không có ví dụ)

{_FORBIDDEN_PHRASES_VI}

## Schema JSON — trả về một object duy nhất

`{{ "errors": [ {{ "error_id", "sev", "t", "end", "title", "detail", "fix" }} ] }}`

- ``t`` / ``end``: giây trên timeline video.
- Áp dụng khối Copy-rules ở trên cho mọi ``title``, ``detail``, ``fix``.
"""

    config = types.GenerateContentConfig(
        temperature=0.45,
        response_mime_type="application/json",
        response_json_schema=VideoErrorsExtractionLLM.model_json_schema(),
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    from getviews_pipeline import telemetry
    with telemetry.span(
        "gemini.extract_video_errors",
        extraction_mode=extraction_mode,
        niche_label=niche_label,
    ):
        response = _generate_content_models(
            [prompt],
            primary_model=GEMINI_EXTRACTION_MODEL,
            fallbacks=GEMINI_EXTRACTION_FALLBACKS,
            config=config,
            call_site="extract_video_errors",
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
    return items[:cap]


# ── Extraction core (Phase 3.1 + 3.3) ────────────────────────────────────────

def run_extraction_core(
    aweme: dict[str, Any],
    video_path: Path | None = None,
    *,
    corpus_hit: dict[str, Any] | None = None,
) -> ExtractionResult:
    """Canonical extraction core — returns a typed ExtractionResult.

    This is the single entry point for all callers that need frame-level
    Gemini analysis. Call paths:

      corpus_ingest  → run_extraction_core(aweme, video_path)   # video downloaded, path known
      corpus_ingest  → run_extraction_core(aweme, video_path=None, corpus_hit=hit)  # cache hit
      video_analyze  → run_extraction_core(aweme)               # on-demand, downloads internally
      batch/douyin   → run_extraction_core(aweme, video_path)   # batch with pre-downloaded path

    ``corpus_hit`` short-circuits Gemini — pass the stored analysis_json dict
    when the video is already in corpus (avoids re-paying the Gemini cost).

    Returns an ExtractionResult with ``error`` set on failure; callers must
    check ``.ok`` before using ``.analysis``.
    """
    from getviews_pipeline import ensemble, telemetry

    vid = str(aweme.get("aweme_id", "") or "")
    metadata_obj = ensemble.parse_metadata(aweme)
    content_type: Literal["video", "carousel"] = (
        "carousel" if ensemble.detect_content_type(aweme) == "carousel" else "video"
    )

    # ── Layer 1: corpus cache hit ─────────────────────────────────────────────
    if corpus_hit is not None:
        from getviews_pipeline.analysis_core import TRANSCRIPT_UNAVAILABLE_MARKER
        from getviews_pipeline.analysis_guards import apply_timestamp_guards, validate_transcript
        from getviews_pipeline.entry_cost import score_entry_cost
        from getviews_pipeline.models import VideoAnalysis

        analysis_dict: dict[str, Any] = dict(corpus_hit)
        try:
            apply_timestamp_guards(analysis_dict, getattr(metadata_obj, "duration_sec", None))
        except Exception as exc:
            logger.warning("[extraction_core] timestamp_guards failed vid=%s: %s", vid, exc)
        transcript_quality = None
        try:
            verdict = validate_transcript(str(analysis_dict.get("audio_transcript") or ""))
            if not verdict.ok:
                analysis_dict["audio_transcript"] = TRANSCRIPT_UNAVAILABLE_MARKER
            transcript_quality = verdict.asdict()
        except Exception as exc:
            logger.warning("[extraction_core] validate_transcript failed vid=%s: %s", vid, exc)
        entry_cost = None
        try:
            tier, reasons = score_entry_cost(analysis_dict)
            entry_cost = {"tier": tier, "reasons": reasons}
        except Exception as exc:
            logger.warning("[extraction_core] score_entry_cost failed vid=%s: %s", vid, exc)
        try:
            analysis_model = VideoAnalysis.model_validate(analysis_dict)
        except Exception as exc:
            return ExtractionResult(
                video_id=vid,
                content_type=content_type,
                metadata=metadata_obj,
                error=f"corpus hit validation failed: {exc}",
            )
        return ExtractionResult(
            video_id=vid,
            content_type=content_type,
            metadata=metadata_obj,
            analysis=analysis_model,
            transcript_quality=transcript_quality,
            entry_cost=entry_cost,
        )

    # ── Layer 2: call Gemini ──────────────────────────────────────────────────
    import asyncio

    from getviews_pipeline.analysis_core import (
        analyze_aweme,
        analyze_aweme_from_path,
    )

    with telemetry.span("extraction_core.analyze", video_id=vid, content_type=content_type):
        if video_path is not None and content_type == "video":
            coro = analyze_aweme_from_path(aweme, video_path, include_diagnosis=False)
        else:
            coro = analyze_aweme(aweme, include_diagnosis=False)

        try:
            loop = asyncio.get_event_loop()
            result_dict: dict[str, Any] = loop.run_until_complete(coro)
        except RuntimeError:
            result_dict = asyncio.run(coro)

    if "error" in result_dict:
        return ExtractionResult(
            video_id=vid,
            content_type=content_type,
            metadata=metadata_obj,
            error=str(result_dict["error"]),
        )

    # Parse analysis object out of result_dict
    from getviews_pipeline.models import VideoAnalysis

    analysis_raw = result_dict.get("analysis") or {}
    try:
        analysis_model = VideoAnalysis.model_validate(analysis_raw)
    except Exception as exc:
        return ExtractionResult(
            video_id=vid,
            content_type=content_type,
            metadata=metadata_obj,
            error=f"VideoAnalysis validation failed: {exc}",
        )

    return ExtractionResult(
        video_id=vid,
        content_type=content_type,
        metadata=metadata_obj,
        analysis=analysis_model,
        transcript_quality=result_dict.get("transcript_quality"),
        entry_cost=result_dict.get("entry_cost"),
    )


async def async_run_extraction_core(
    aweme: dict[str, Any],
    video_path: Path | None = None,
    *,
    corpus_hit: dict[str, Any] | None = None,
) -> ExtractionResult:
    """Async wrapper for run_extraction_core — for use inside async callers.

    corpus_ingest and douyin_ingest call this instead of analyze_aweme_from_path
    directly (Phase 3.3 wiring). Carousels and corpus-cache hits don't need
    the executor; video analysis is wrapped in asyncio.get_event_loop.run_in_executor
    inside analyze_aweme_from_path so this wrapper stays safe.
    """
    # Corpus hit is pure Python — no I/O, can run inline.
    if corpus_hit is not None:
        return run_extraction_core(aweme, video_path, corpus_hit=corpus_hit)

    # Carousel / video: analyze_aweme / analyze_aweme_from_path are async internally
    # (wrap CPU-bound Gemini call in an executor). We call them directly.
    from getviews_pipeline import ensemble
    from getviews_pipeline.analysis_core import analyze_aweme, analyze_aweme_from_path

    vid = str(aweme.get("aweme_id", "") or "")
    metadata_obj = ensemble.parse_metadata(aweme)
    content_type: Literal["video", "carousel"] = (
        "carousel" if ensemble.detect_content_type(aweme) == "carousel" else "video"
    )

    if video_path is not None and content_type == "video":
        result_dict: dict[str, Any] = await analyze_aweme_from_path(
            aweme, video_path, include_diagnosis=False
        )
    else:
        result_dict = await analyze_aweme(aweme, include_diagnosis=False)

    if "error" in result_dict:
        return ExtractionResult(
            video_id=vid,
            content_type=content_type,
            metadata=metadata_obj,
            error=str(result_dict["error"]),
        )

    from getviews_pipeline.models import VideoAnalysis

    analysis_raw = result_dict.get("analysis") or {}
    try:
        analysis_model = VideoAnalysis.model_validate(analysis_raw)
    except Exception as exc:
        return ExtractionResult(
            video_id=vid,
            content_type=content_type,
            metadata=metadata_obj,
            error=f"VideoAnalysis validation failed: {exc}",
        )

    return ExtractionResult(
        video_id=vid,
        content_type=content_type,
        metadata=metadata_obj,
        analysis=analysis_model,
        transcript_quality=result_dict.get("transcript_quality"),
        entry_cost=result_dict.get("entry_cost"),
    )
