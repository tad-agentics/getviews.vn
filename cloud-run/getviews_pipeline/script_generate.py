"""B.4 — POST ``/script/generate``: credit gate + Gemini-bounded shot scaffold.

**D.1.2** upgrade: the deterministic template backbone is now a fallback —
the happy path calls Gemini with a pydantic-bound response schema so
shots carry topic-tailored Vietnamese copy instead of generic placeholder
text. HTTP contract is **frozen** from B.4: the response shape is
``{"shots": [{t0, t1, cam, voice, viz, overlay, corpus_avg, winner_avg,
intel_scene_type, overlay_winner}, ...]}`` regardless of which path wins.

Fields Gemini owns (creative):
    cam, voice, viz, overlay, intel_scene_type, overlay_winner

Fields we own (deterministic — never hallucinated):
    t0, t1          — from _segment_lengths(duration)
    corpus_avg      — positional defaults from _BACKBONE
    winner_avg      — positional defaults from _BACKBONE

On any Gemini error the full deterministic path runs — the response is
still valid, just generic. Client continues to merge
``scene_intelligence`` for corpus/winner bars and tips.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ScriptTone = Literal["Hài", "Chuyên gia", "Tâm sự", "Năng lượng", "Mỉa mai"]

OverlayT = Literal["BOLD CENTER", "SUB-CAPTION", "STAT BURST", "LABEL", "QUESTION XL", "NONE"]
IntelSceneT = Literal["face_to_camera", "product_shot", "demo", "action"]


class InsufficientCreditsError(Exception):
    """``decrement_credit`` returned false or raised."""


class ScriptGenerateBody(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    hook: str = Field(..., min_length=1, max_length=200)
    hook_delay_ms: int = Field(ge=400, le=3000)
    duration: int = Field(ge=15, le=90)
    tone: ScriptTone
    niche_id: int = Field(ge=1)


class ScriptShotLLM(BaseModel):
    """Gemini's per-shot output. t0/t1/corpus_avg/winner_avg are NOT here —
    those stay deterministic so Gemini can't drift the timing or invent
    scene-intel numbers that mislead the frontend bars."""

    cam: str = Field(..., min_length=1, max_length=80)
    voice: str = Field(..., min_length=1, max_length=220)
    viz: str = Field(..., min_length=1, max_length=200)
    overlay: OverlayT
    intel_scene_type: IntelSceneT
    overlay_winner: str = Field(default="—", max_length=80)


class ScriptGenerateLLM(BaseModel):
    shots: list[ScriptShotLLM] = Field(..., min_length=6, max_length=6)


# Positional backbone — owns overlay/intel_scene_type order + corpus/winner
# benchmarks. Gemini is asked to respect the overlay + intel_scene_type
# in the prompt, and if it drifts we coerce back to these canonical values
# inside `_assemble_shots`.
_WEIGHTS: tuple[int, ...] = (3, 5, 8, 8, 6, 2)
_BACKBONE: tuple[tuple[str, OverlayT, IntelSceneT, str, str, float, float, str], ...] = (
    ("Cận mặt", "BOLD CENTER", "face_to_camera",
     "Hook: mở với {hook} — {topic}", 'Chữ nổi + "{topic_short}"',
     2.8, 2.4, "white sans 28pt · bottom-center"),
    ("Cắt nhanh b-roll", "SUB-CAPTION", "product_shot",
     "B-roll: nhấn {topic_short}", "Cắt nhanh, slow-mo nhẹ",
     4.2, 5.0, "yellow outlined · mid-left"),
    ("Side-by-side", "STAT BURST", "demo",
     "So sánh / demo trung tâm: {topic_short}", "Split-screen, số liệu nổi",
     7.8, 8.0, "number callout 72pt"),
    ("POV nghe", "LABEL", "face_to_camera",
     "Giọng {tone}: giải thích {topic_short}", "POV, ánh sáng ấm",
     6.2, 7.5, "caption strip · bottom"),
    ("Cận tay + texture", "NONE", "action",
     "Texture + cảm nhận: {topic_short}", "Cận chi tiết, xoay nhẹ",
     5.1, 5.0, "—"),
    ("Cận mặt + câu hỏi", "QUESTION XL", "face_to_camera",
     "CTA: hỏi người xem về {topic_short}", "Câu hỏi to trên màn",
     2.4, 2.5, "question mark · full bleed"),
)


def _sanitize_snippet(s: str, max_len: int) -> str:
    t = re.sub(r"\s+", " ", (s or "").strip())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _segment_lengths(total: int) -> list[int]:
    if total < 15:
        total = 15
    wsum = sum(_WEIGHTS)
    parts: list[int] = []
    acc = 0
    for i, w in enumerate(_WEIGHTS):
        if i == len(_WEIGHTS) - 1:
            parts.append(max(1, total - acc))
            break
        seg = max(1, round(total * w / wsum))
        if acc + seg >= total:
            seg = max(1, total - acc - (len(_WEIGHTS) - i - 1))
        parts.append(seg)
        acc += seg
    drift = total - sum(parts)
    if parts and drift != 0:
        parts[-1] = max(1, parts[-1] + drift)
    return parts


def _deterministic_creative_rows(
    *, topic: str, hook: str, tone: str
) -> list[tuple[str, OverlayT, IntelSceneT, str, str, str]]:
    """Render the fallback creative fields from the _BACKBONE templates.

    Returns (cam, overlay, intel_scene_type, voice, viz, overlay_winner) per
    position so ``_assemble_shots`` can stitch in t0/t1 + corpus/winner.
    """
    topic_short = _sanitize_snippet(topic, 36)
    out: list[tuple[str, OverlayT, IntelSceneT, str, str, str]] = []
    for row in _BACKBONE:
        cam, overlay, intel_scene, voice_tpl, viz_tpl, _cavg, _wavg, owin = row
        voice = voice_tpl.format(hook=hook, topic=topic, topic_short=topic_short, tone=tone)
        viz = viz_tpl.format(hook=hook, topic=topic, topic_short=topic_short, tone=tone)
        out.append((cam, overlay, intel_scene, voice, viz, owin))
    return out


def _assemble_shots(
    *,
    duration: int,
    creative: list[tuple[str, OverlayT, IntelSceneT, str, str, str]],
) -> list[dict[str, Any]]:
    """Stitch creative + deterministic fields into the frozen shot payload."""
    lens = _segment_lengths(duration)
    t0 = 0
    out: list[dict[str, Any]] = []
    for i, (cam, overlay, intel_scene, voice, viz, owin) in enumerate(creative):
        span = lens[i] if i < len(lens) else 1
        t1 = t0 + span
        _, canon_overlay, canon_intel, _, _, _cavg, _wavg, _ = _BACKBONE[i]
        # Coerce overlay + intel_scene_type to the canonical backbone for
        # this position if Gemini drifted — the frontend scene merge
        # relies on the positional overlay/intel mapping.
        final_overlay: OverlayT = overlay if overlay == canon_overlay else canon_overlay
        final_intel: IntelSceneT = intel_scene if intel_scene == canon_intel else canon_intel
        out.append(
            {
                "t0": t0,
                "t1": t1,
                "cam": _sanitize_snippet(cam, 80),
                "voice": _sanitize_snippet(voice, 220),
                "viz": _sanitize_snippet(viz, 200),
                "overlay": final_overlay,
                "corpus_avg": _BACKBONE[i][5],
                "winner_avg": _BACKBONE[i][6],
                "intel_scene_type": final_intel,
                "overlay_winner": _sanitize_snippet(owin, 80) or "—",
            }
        )
        t0 = t1
    return out


def _call_script_gemini(body: ScriptGenerateBody) -> ScriptGenerateLLM:
    """Pydantic-bound Gemini synthesis for 6 shots. Raises on any failure."""
    from google.genai import types

    from getviews_pipeline.config import GEMINI_SYNTHESIS_FALLBACKS, GEMINI_SYNTHESIS_MODEL
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _normalize_response,
        _response_text,
    )

    topic = _sanitize_snippet(body.topic, 500)
    hook = _sanitize_snippet(body.hook, 200)
    delay_s = round(body.hook_delay_ms / 1000.0, 2)

    prompt = f"""Bạn là biên kịch TikTok tiếng Việt ngắn (dưới {body.duration}s). Viết kịch bản 6 shot cho video.

Chủ đề: {topic}
Hook (dùng cho shot 1): {hook}
Hook rơi lúc: {delay_s}s
Tone: {body.tone}
Thời lượng tổng: {body.duration}s

Cấu trúc 6 shot CỐ ĐỊNH (phải giữ đúng overlay + intel_scene_type theo template):
1. cam="Cận mặt", overlay="BOLD CENTER", intel_scene_type="face_to_camera" — hook mạnh trong 3s đầu.
2. cam="Cắt nhanh b-roll", overlay="SUB-CAPTION", intel_scene_type="product_shot" — mở rộng ngữ cảnh.
3. cam="Side-by-side", overlay="STAT BURST", intel_scene_type="demo" — demo / so sánh có số liệu.
4. cam="POV nghe", overlay="LABEL", intel_scene_type="face_to_camera" — POV giải thích, giọng {body.tone}.
5. cam="Cận tay + texture", overlay="NONE", intel_scene_type="action" — chi tiết / texture, không text.
6. cam="Cận mặt + câu hỏi", overlay="QUESTION XL", intel_scene_type="face_to_camera" — CTA câu hỏi.

Với mỗi shot, viết:
- cam: giữ đúng như template ở trên.
- voice: voiceover 1–2 câu tiếng Việt tự nhiên, tone={body.tone}, nhắc chủ đề hoặc hook.
- viz: chỉ dẫn visual ngắn (< 20 từ) tiếng Việt.
- overlay: theo template — KHÔNG đổi.
- intel_scene_type: theo template — KHÔNG đổi.
- overlay_winner: gợi ý style overlay ngắn (có thể tiếng Anh) — ví dụ "white sans 28pt · bottom-center".

Quy tắc copy:
- Tự nhiên, đời thường; tránh "bí mật", "công thức vàng", "triệu view", "bùng nổ".
- Không mở bằng "Chào bạn" / "Tuyệt vời" / "Wow".
- Tôn trọng độ dài: voice ≤ 220 ký tự, viz ≤ 200 ký tự.
"""
    config = types.GenerateContentConfig(
        temperature=0.7,
        response_mime_type="application/json",
        response_json_schema=ScriptGenerateLLM.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return ScriptGenerateLLM.model_validate_json(_normalize_response(raw))


def build_script_shots(body: ScriptGenerateBody) -> list[dict[str, Any]]:
    """Gemini-first shot builder with deterministic fallback.

    Returns the frozen B.4 response shape — 6 shots each with
    t0/t1/cam/voice/viz/overlay/corpus_avg/winner_avg/intel_scene_type/
    overlay_winner.
    """
    topic = _sanitize_snippet(body.topic, 500)
    hook = _sanitize_snippet(body.hook, 200)

    creative: list[tuple[str, OverlayT, IntelSceneT, str, str, str]] | None = None
    try:
        llm = _call_script_gemini(body)
        creative = [
            (s.cam, s.overlay, s.intel_scene_type, s.voice, s.viz, s.overlay_winner or "—")
            for s in llm.shots
        ]
        logger.info("[script/generate] source=gemini niche=%s duration=%ds", body.niche_id, body.duration)
    except Exception as exc:
        logger.warning("[script/generate] Gemini path failed, falling back deterministic: %s", exc)
        creative = None

    if creative is None:
        creative = _deterministic_creative_rows(topic=topic, hook=hook, tone=body.tone)
        logger.info("[script/generate] source=fallback niche=%s duration=%ds", body.niche_id, body.duration)

    return _assemble_shots(duration=body.duration, creative=creative)


def _decrement_credit_or_raise(user_sb: Any, *, user_id: str) -> None:
    try:
        rpc_resp = user_sb.rpc("decrement_credit", {"p_user_id": user_id}).execute()
        if rpc_resp.data is False:
            raise InsufficientCreditsError()
    except InsufficientCreditsError:
        raise
    except Exception as exc:
        logger.warning("[script/generate] decrement_credit failed: %s", exc)
        raise InsufficientCreditsError() from exc


def run_script_generate_sync(user_sb: Any, *, user_id: str, body: ScriptGenerateBody) -> dict[str, Any]:
    _decrement_credit_or_raise(user_sb, user_id=user_id)
    shots = build_script_shots(body)
    logger.info("[script/generate] user=%s niche=%d shots=%d", user_id, body.niche_id, len(shots))
    return {"shots": shots}
