"""Wave 4 PR #2 — Compare-videos pipeline + delta synthesis.

Public surface:

    run_compare_pipeline(url_a, url_b, session, *, ...) -> dict
        Top-level orchestrator: runs ``run_video_diagnosis`` on each URL
        in parallel via ``asyncio.gather`` (each with its own shallow
        session copy so cache state can't trample), assembles a
        ``ComparePayload`` with both diagnoses + a Gemini-generated
        Vietnamese delta verdict that's been routed through the
        ``voice_lint`` peer-expert gate.

    ComparePayload
        Pydantic model — pins the response shape so the FE can't
        accidentally start consuming a field that isn't part of the
        contract.

Design notes:

- **Bundle streaming, not progressive.** The outer ``/stream`` SSE
  handler emits one envelope (start → done) around the whole compare
  call. Per-side step events would double the FE complexity (skeleton-
  fill-replace) for marginal UX gain — total latency is bounded by
  the slower of the two diagnoses anyway. Trade-off documented in
  the Wave 4 design discussion (PR #2 kickoff).
- **Independent session copies.** ``run_video_diagnosis`` mutates
  ``session["full_analyses"]`` and other caches; running two
  in parallel against the same dict would race. Each side gets
  ``dict(session)`` — shallow is enough because the mutation happens
  at top-level keys and we don't need to merge state back.
- **Voice-lint enforced verdict.** Gemini-generated VN delta sentence
  passes through ``voice_lint.assert_copy_clean`` before emission. On
  any violation OR Gemini failure the orchestrator falls back to a
  deterministic templated sentence built from the numeric deltas —
  the worst case is "boring but factually correct copy", never
  forbidden-word leakage.
- **No new credit deduction.** /stream already charges one credit at
  entry; compare costs ~3× the Gemini spend of a single diagnosis but
  the charge stays at 1. If abuse surfaces in dogfood we'll revisit.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from getviews_pipeline.voice_lint import lint_forbidden_copy

logger = logging.getLogger(__name__)


# ── Schema ────────────────────────────────────────────────────────────


HookAlignment = Literal["match", "conflict", "unknown"]
HigherSide = Literal["left", "right", "tie", "unknown"]


class CompareDelta(BaseModel):
    """Per-pair delta — numeric comparisons + 1-2 sentence VN verdict.

    Numeric fields use ``left - right`` orientation (positive = left
    side higher). Set to ``None`` when either side lacks the input
    metric so the FE can render "—" instead of a misleading 0.
    """

    verdict: str = Field(..., min_length=1, max_length=240)
    hook_alignment: HookAlignment
    higher_breakout_side: HigherSide
    breakout_gap: float | None = None
    scene_count_diff: int | None = None
    transitions_per_second_diff: float | None = None
    left_hook_type: str | None = None
    right_hook_type: str | None = None
    # ``true`` when the verdict was templated because Gemini failed or
    # produced forbidden copy — surfaces in observability without
    # changing the FE rendering contract.
    verdict_fallback: bool = False


class ComparePayload(BaseModel):
    intent: Literal["compare_videos"] = "compare_videos"
    niche: str | None = None
    left: dict[str, Any]
    right: dict[str, Any]
    delta: CompareDelta


class CompareDeltaCopyLLM(BaseModel):
    """Schema bound to the Gemini call for the verdict sentence only.

    Kept narrow (one field) so the LLM response stays small + cheap;
    everything else on ``CompareDelta`` is derived in Python from the
    two diagnosis dicts.
    """

    verdict: str = Field(..., min_length=1, max_length=240)


# ── Numeric delta derivation (deterministic — no LLM) ─────────────────


def _stats(side: dict[str, Any]) -> dict[str, Any]:
    """Normalize the run_video_diagnosis output into a flat metrics
    dict. Tolerates missing keys (returns ``None`` per metric)."""
    metadata = side.get("metadata") or {}
    metrics = metadata.get("metrics") or {}
    analysis = side.get("analysis") or {}
    return {
        "views": metrics.get("views"),
        "breakout": metadata.get("breakout") or metadata.get("breakout_multiplier"),
        "engagement_rate": metadata.get("engagement_rate"),
        "scene_count": len(analysis.get("scenes") or []) or None,
        "transitions_per_second": analysis.get("transitions_per_second"),
        "hook_type": (analysis.get("hook_analysis") or {}).get("hook_type"),
        "handle": (metadata.get("author") or {}).get("username"),
    }


def _signed_diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return float(a) - float(b)


def _hook_alignment(left_hook: str | None, right_hook: str | None) -> HookAlignment:
    if not left_hook or not right_hook:
        return "unknown"
    return "match" if left_hook == right_hook else "conflict"


def _higher_breakout(
    left_breakout: float | None, right_breakout: float | None,
) -> HigherSide:
    if left_breakout is None or right_breakout is None:
        return "unknown"
    if abs(left_breakout - right_breakout) < 0.05:
        return "tie"
    return "left" if left_breakout > right_breakout else "right"


# ── Templated fallback verdict ────────────────────────────────────────


def _templated_verdict(
    left_stats: dict[str, Any],
    right_stats: dict[str, Any],
    higher_side: HigherSide,
    hook_align: HookAlignment,
) -> str:
    """Deterministic Vietnamese sentence used when Gemini fails or its
    output trips the voice_lint gate. Stays factual + short."""
    if higher_side == "tie":
        spine = "Hai video chạy gần như tương đương nhau"
    elif higher_side == "unknown":
        spine = "Chưa đủ data breakout để so điểm chính"
    else:
        side_label = "trái" if higher_side == "left" else "phải"
        spine = f"Video {side_label} đang chạy mạnh hơn"

    if hook_align == "match":
        spine += " — cùng kiểu hook, khác biệt nằm ở pacing/visual."
    elif hook_align == "conflict":
        l_hook = left_stats.get("hook_type") or "khác"
        r_hook = right_stats.get("hook_type") or "khác"
        spine += f" — hook khác nhau ({l_hook} vs {r_hook})."
    else:
        spine += "."
    return spine[:240]


# ── Gemini-backed verdict (with voice-lint enforcement) ───────────────


def _build_delta_prompt(
    niche: str | None,
    left_stats: dict[str, Any],
    right_stats: dict[str, Any],
    breakout_gap: float | None,
    scene_diff: int | None,
    higher_side: HigherSide,
    hook_align: HookAlignment,
) -> str:
    """Compose the prompt for the verdict sentence.

    The prompt restates the numeric comparison as inputs so Gemini
    can't fabricate numbers, and asks for one sentence in peer-expert
    voice. The Wave 3 voice_lint gate runs on the response — listing
    the forbidden words here is belt-and-braces (the gate catches
    anything that slips).
    """
    niche_label = niche or "TikTok Việt Nam"
    higher_label = {
        "left": "video trái",
        "right": "video phải",
        "tie": "tương đương",
        "unknown": "chưa rõ",
    }[higher_side]

    lh = left_stats.get("handle") or "trái"
    rh = right_stats.get("handle") or "phải"
    l_hook = left_stats.get("hook_type")
    l_sc = left_stats.get("scene_count")
    l_bo = left_stats.get("breakout")
    l_v = left_stats.get("views")
    r_hook = right_stats.get("hook_type")
    r_sc = right_stats.get("scene_count")
    r_bo = right_stats.get("breakout")
    r_v = right_stats.get("views")
    return f"""Bạn là creator TikTok Việt Nam đang nhắn cho đồng nghiệp. \
Viết MỘT câu tiếng Việt (≤ 30 từ) tổng hợp khác biệt giữa hai video, \
dùng dữ liệu dưới đây.

Ngách: {niche_label}
Trái (@{lh}): hook={l_hook}, scene={l_sc}, breakout={l_bo}, views={l_v}
Phải (@{rh}): hook={r_hook}, scene={r_sc}, breakout={r_bo}, views={r_v}

So sánh đã tính sẵn:
- Bên chạy mạnh hơn: {higher_label}
- Hook trùng/khác: {hook_align}
- Chênh breakout: {breakout_gap}
- Chênh số scene: {scene_diff}

Quy tắc giọng:
- Peer expert nhắn Zalo, KHÔNG guru, KHÔNG sale pitch.
- KHÔNG mở bằng "Chào", "Tuyệt vời", "Đây là", "Dưới đây là", "Wow".
- KHÔNG dùng: "tuyệt vời", "hoàn hảo", "bí mật", "công thức vàng",
  "đột phá", "kỷ lục", "triệu view", "bùng nổ", "siêu hot", "thần
  thánh", "hack", "chiến lược độc quyền", "ai cũng phải biết",
  "không thể bỏ qua", "chắc chắn thành công".
- Trả về JSON: {{"verdict": "<câu tiếng Việt>"}}
"""


def _call_delta_gemini(prompt: str) -> str | None:
    """Single Gemini call → bounded JSON. Returns the verdict string
    on success, ``None`` on any failure (the orchestrator then falls
    back to the templated verdict)."""
    try:
        from google.genai import types

        from getviews_pipeline.config import (
            GEMINI_SYNTHESIS_FALLBACKS,
            GEMINI_SYNTHESIS_MODEL,
        )
        from getviews_pipeline.gemini import (
            _generate_content_models,
            _normalize_response,
            _response_text,
        )

        config = types.GenerateContentConfig(
            temperature=0.4,
            response_mime_type="application/json",
            response_json_schema=CompareDeltaCopyLLM.model_json_schema(),
        )
        response = _generate_content_models(
            [prompt],
            primary_model=GEMINI_SYNTHESIS_MODEL,
            fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
            config=config,
        )
        raw = _response_text(response)
        parsed = CompareDeltaCopyLLM.model_validate_json(_normalize_response(raw))
        return parsed.verdict
    except Exception as exc:
        logger.warning("[compare] delta Gemini call failed (non-fatal): %s", exc)
        return None


def build_delta(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    niche: str | None,
    gemini_enabled: bool = True,
) -> CompareDelta:
    """Compose the full ``CompareDelta`` from two diagnosis dicts.

    Numeric fields are derived deterministically. The verdict sentence
    tries Gemini first, runs the response through ``voice_lint``, and
    falls back to a deterministic templated sentence on Gemini failure
    OR on any voice-lint violation. ``verdict_fallback`` flips True
    when the fallback fires so observability can monitor the rate.
    """
    l_stats = _stats(left)
    r_stats = _stats(right)
    breakout_gap = _signed_diff(l_stats["breakout"], r_stats["breakout"])
    scene_diff: int | None
    if l_stats["scene_count"] is not None and r_stats["scene_count"] is not None:
        scene_diff = int(l_stats["scene_count"]) - int(r_stats["scene_count"])
    else:
        scene_diff = None
    tps_diff = _signed_diff(
        l_stats["transitions_per_second"], r_stats["transitions_per_second"],
    )
    higher_side = _higher_breakout(l_stats["breakout"], r_stats["breakout"])
    hook_align = _hook_alignment(l_stats["hook_type"], r_stats["hook_type"])

    verdict_text: str | None = None
    fallback = True
    if gemini_enabled:
        prompt = _build_delta_prompt(
            niche=niche,
            left_stats=l_stats, right_stats=r_stats,
            breakout_gap=breakout_gap, scene_diff=scene_diff,
            higher_side=higher_side, hook_align=hook_align,
        )
        candidate = _call_delta_gemini(prompt)
        if candidate:
            violations = lint_forbidden_copy(candidate)
            if violations:
                logger.warning(
                    "[compare] delta verdict tripped voice_lint (n=%d) — falling back. "
                    "First violation: %s",
                    len(violations), violations[0],
                )
            else:
                verdict_text = candidate.strip()[:240]
                fallback = False
    if verdict_text is None:
        verdict_text = _templated_verdict(
            l_stats, r_stats, higher_side, hook_align,
        )

    return CompareDelta(
        verdict=verdict_text,
        hook_alignment=hook_align,
        higher_breakout_side=higher_side,
        breakout_gap=breakout_gap,
        scene_count_diff=scene_diff,
        transitions_per_second_diff=tps_diff,
        left_hook_type=l_stats["hook_type"],
        right_hook_type=r_stats["hook_type"],
        verdict_fallback=fallback,
    )


# ── Top-level orchestrator ───────────────────────────────────────────


async def run_compare_pipeline(
    url_a: str,
    url_b: str,
    session: dict[str, Any],
    *,
    user_message: str = "",
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    """Side-by-side video diagnosis.

    Runs ``run_video_diagnosis`` on each URL in parallel using
    independent shallow session copies (cache mutations are top-level
    keys; deeper objects are read-only inside the diagnosis flow).
    Bundle streaming — no per-side step events; the outer /stream
    handler wraps the call with one start/done envelope of its own.
    """
    # Local import to avoid a circular dep with pipelines.py at module
    # import time. /stream + tests both import this module directly.
    from getviews_pipeline.pipelines import run_video_diagnosis
    from getviews_pipeline.step_events import emit_sentinel, step_done, step_start

    if step_queue is not None:
        await step_queue.put(step_start("Đang so sánh hai video..."))

    session_left = dict(session)
    session_right = dict(session)

    results = await asyncio.gather(
        run_video_diagnosis(
            url_a, session_left,
            user_message=user_message, step_queue=None,
        ),
        run_video_diagnosis(
            url_b, session_right,
            user_message=user_message, step_queue=None,
        ),
        return_exceptions=True,
    )
    left_res, right_res = results

    # Partial-failure path: if exactly one side raised, surface the
    # other as a single-video fallback rather than aborting. Both-side
    # failure re-raises so /stream can emit its standard error envelope.
    if isinstance(left_res, Exception) and isinstance(right_res, Exception):
        raise left_res
    if isinstance(left_res, Exception):
        logger.warning("[compare] left side failed, returning single-video right: %s", left_res)
        if step_queue is not None:
            await step_queue.put(step_done("Một video lỗi — chỉ trả kết quả video còn lại."))
            await emit_sentinel(step_queue)
        return right_res
    if isinstance(right_res, Exception):
        logger.warning("[compare] right side failed, returning single-video left: %s", right_res)
        if step_queue is not None:
            await step_queue.put(step_done("Một video lỗi — chỉ trả kết quả video còn lại."))
            await emit_sentinel(step_queue)
        return left_res

    niche = None
    if isinstance(left_res, dict):
        niche = left_res.get("niche") or right_res.get("niche")
    delta = build_delta(left_res, right_res, niche=niche)
    payload = ComparePayload(
        niche=niche, left=left_res, right=right_res, delta=delta,
    )

    if step_queue is not None:
        await step_queue.put(step_done("Đã so sánh xong — đang viết tổng kết..."))
        await emit_sentinel(step_queue)

    return payload.model_dump()
