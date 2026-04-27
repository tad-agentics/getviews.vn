"""B.4 — POST ``/script/generate``: credit gate + Gemini-bounded shot scaffold.

**D.1.2** upgrade: the deterministic template backbone is now a fallback —
the happy path calls Gemini with a pydantic-bound response schema so
shots carry topic-tailored Vietnamese copy instead of generic placeholder
text.

**Wave 2.5 Phase B PR #6** upgrade: each shot is now paired with up to
3 ``references`` — real creator scenes from ``video_shots`` matched by
``pick_shot_references`` on (niche_id, hook_type, framing, pace, …).
HTTP contract ADDS ``references: [...]`` per shot; existing fields
unchanged so FE clients that don't know about references ignore the
new key cleanly.

Fields Gemini owns (creative):
    cam, voice, viz, overlay, intel_scene_type, overlay_winner,
    framing, pace, overlay_style, subject, motion  (Optional — PR #6)

Fields we own (deterministic — never hallucinated):
    t0, t1          — from _segment_lengths(duration)
    corpus_avg      — positional defaults from _BACKBONE
    winner_avg      — positional defaults from _BACKBONE
    references      — pick_shot_references() against video_shots

On any Gemini error the full deterministic path runs — the response is
still valid, just generic. Client continues to merge
``scene_intelligence`` for corpus/winner bars and tips. Reference
lookup runs even on the fallback path — the positional backbone knows
the canonical framing/pace/overlay_style for each of the 6 shots, so
matcher has a non-empty descriptor either way.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from getviews_pipeline.models import (
    FramingType,
    MotionType,
    OverlayStyleType,
    PaceType,
    SubjectType,
)

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
    # S6 — per-shot regenerate (per design pack ``screens/script.jsx``
    # lines 1149-1157). When set, the response carries only the shot at
    # this index so the FE can splice it back into local state without
    # disturbing the user's other 5 shots. ``None`` keeps the legacy
    # full-script regen behaviour. Validated against the deterministic
    # 6-shot output in ``run_script_generate_sync``.
    shot_index: int | None = Field(default=None, ge=0, le=5)


class ScriptShotLLM(BaseModel):
    """Gemini's per-shot output. t0/t1/corpus_avg/winner_avg are NOT here —
    those stay deterministic so Gemini can't drift the timing or invent
    scene-intel numbers that mislead the frontend bars.

    Wave 2.5 Phase B PR #6: optional enrichment fields feed
    ``pick_shot_references`` with the descriptor the matcher scores on.
    Optional because (a) old Gemini output doesn't have them, (b) the
    deterministic fallback fills them from the positional backbone.
    """

    cam: str = Field(..., min_length=1, max_length=80)
    voice: str = Field(..., min_length=1, max_length=220)
    viz: str = Field(..., min_length=1, max_length=200)
    overlay: OverlayT
    intel_scene_type: IntelSceneT
    overlay_winner: str = Field(default="—", max_length=80)

    # 2026-05-11 — enrichment dimensions mirrored from the Scene model
    # (getviews_pipeline.models). All Optional; see module docstring.
    framing: FramingType | None = None
    pace: PaceType | None = None
    overlay_style: OverlayStyleType | None = None
    subject: SubjectType | None = None
    motion: MotionType | None = None


class ScriptGenerateLLM(BaseModel):
    shots: list[ScriptShotLLM] = Field(..., min_length=6, max_length=6)


# Positional backbone — owns overlay/intel_scene_type order + corpus/winner
# benchmarks. Gemini is asked to respect the overlay + intel_scene_type
# in the prompt, and if it drifts we coerce back to these canonical values
# inside `_assemble_shots`. Wave 2.5 Phase B PR #6 added canonical
# framing/pace/overlay_style/subject/motion per position so the matcher
# has a descriptor even on the deterministic fallback path.
_WEIGHTS: tuple[int, ...] = (3, 5, 8, 8, 6, 2)

# One row per of the 6 shots. Indexes:
#   0 cam, 1 overlay, 2 intel_scene_type, 3 voice_tpl, 4 viz_tpl,
#   5 corpus_avg, 6 winner_avg, 7 overlay_winner,
#   8 framing, 9 pace, 10 overlay_style, 11 subject, 12 motion
_BACKBONE: tuple[
    tuple[
        str, OverlayT, IntelSceneT, str, str, float, float, str,
        FramingType, PaceType, OverlayStyleType, SubjectType, MotionType,
    ],
    ...,
] = (
    ("Cận mặt", "BOLD CENTER", "face_to_camera",
     "Hook: mở với {hook} — {topic}", 'Chữ nổi + "{topic_short}"',
     2.8, 2.4, "white sans 28pt · bottom-center",
     "close_up", "static", "bold_center", "face", "static"),
    ("Cắt nhanh b-roll", "SUB-CAPTION", "product_shot",
     "B-roll: nhấn {topic_short}", "Cắt nhanh, slow-mo nhẹ",
     4.2, 5.0, "yellow outlined · mid-left",
     "medium", "fast", "sub_caption", "product", "handheld"),
    ("Side-by-side", "STAT BURST", "demo",
     "So sánh / demo trung tâm: {topic_short}", "Split-screen, số liệu nổi",
     7.8, 8.0, "number callout 72pt",
     "medium", "medium", "sticker", "mixed", "static"),
    ("POV nghe", "LABEL", "face_to_camera",
     "Giọng {tone}: giải thích {topic_short}", "POV, ánh sáng ấm",
     6.2, 7.5, "caption strip · bottom",
     "medium", "slow", "chyron", "face", "handheld"),
    ("Cận tay + texture", "NONE", "action",
     "Texture + cảm nhận: {topic_short}", "Cận chi tiết, xoay nhẹ",
     5.1, 5.0, "—",
     "extreme_close_up", "slow", "none", "action", "slow_mo"),
    ("Cận mặt + câu hỏi", "QUESTION XL", "face_to_camera",
     "CTA: hỏi người xem về {topic_short}", "Câu hỏi to trên màn",
     2.4, 2.5, "question mark · full bleed",
     "close_up", "static", "bold_center", "face", "static"),
)


def _shot_to_descriptor(
    *,
    intel_scene_type: IntelSceneT,
    framing: FramingType | None,
    pace: PaceType | None,
    overlay_style: OverlayStyleType | None,
    subject: SubjectType | None,
    motion: MotionType | None,
    backbone_idx: int,
) -> dict[str, Any]:
    """Project a shot's creative fields into the ``video_shots``-column
    descriptor shape that ``pick_shot_references`` scores on.

    Prefer Gemini-emitted enrichment fields when present; otherwise fall
    back to the positional backbone. Always emits the legacy
    ``scene_type`` alongside so pre-PR #2 legacy shots still score via
    the scene_type fallback branch inside the matcher.
    """
    row = _BACKBONE[min(backbone_idx, len(_BACKBONE) - 1)]
    canon_framing = row[8]
    canon_pace = row[9]
    canon_overlay_style = row[10]
    canon_subject = row[11]
    canon_motion = row[12]
    return {
        "framing": framing or canon_framing,
        "pace": pace or canon_pace,
        "overlay_style": overlay_style or canon_overlay_style,
        "subject": subject or canon_subject,
        "motion": motion or canon_motion,
        "scene_type": intel_scene_type,  # legacy fallback dimension
    }


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


# Tuple shape emitted by both the Gemini path and the deterministic
# fallback, consumed by _assemble_shots:
#   (cam, overlay, intel_scene, voice, viz, overlay_winner,
#    framing, pace, overlay_style, subject, motion)
_CreativeRow = tuple[
    str, OverlayT, IntelSceneT, str, str, str,
    FramingType | None, PaceType | None, OverlayStyleType | None,
    SubjectType | None, MotionType | None,
]


def _deterministic_creative_rows(
    *, topic: str, hook: str, tone: str,
) -> list[_CreativeRow]:
    """Render the fallback creative fields from the _BACKBONE templates.

    Returns 11-tuples per position — the last five are the canonical
    enrichment fields from the backbone, mirroring what Gemini would
    emit on the happy path.
    """
    topic_short = _sanitize_snippet(topic, 36)
    out: list[_CreativeRow] = []
    for row in _BACKBONE:
        (cam, overlay, intel_scene, voice_tpl, viz_tpl, _cavg, _wavg, owin,
         framing, pace, overlay_style, subject, motion) = row
        voice = voice_tpl.format(hook=hook, topic=topic, topic_short=topic_short, tone=tone)
        viz = viz_tpl.format(hook=hook, topic=topic, topic_short=topic_short, tone=tone)
        out.append((
            cam, overlay, intel_scene, voice, viz, owin,
            framing, pace, overlay_style, subject, motion,
        ))
    return out


def _assemble_shots(
    *,
    duration: int,
    creative: list[_CreativeRow],
) -> list[dict[str, Any]]:
    """Stitch creative + deterministic fields into the frozen shot payload.

    Each shot dict now also carries framing/pace/overlay_style/subject/
    motion (Optional — may be None if Gemini omitted and the backbone
    defaults weren't threaded). The outer runner adds ``references``.
    """
    lens = _segment_lengths(duration)
    t0 = 0
    out: list[dict[str, Any]] = []
    for i, creative_row in enumerate(creative):
        (cam, overlay, intel_scene, voice, viz, owin,
         framing, pace, overlay_style, subject, motion) = creative_row
        span = lens[i] if i < len(lens) else 1
        t1 = t0 + span
        canon_overlay = _BACKBONE[i][1]
        canon_intel = _BACKBONE[i][2]
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
                "framing": framing,
                "pace": pace,
                "overlay_style": overlay_style,
                "subject": subject,
                "motion": motion,
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

Thêm các dimension mô tả shot (dùng để matcher tìm video tham chiếu
tương tự trong corpus — enum phải trùng đúng taxonomy; nếu không chắc
để null):
- framing: close_up | medium | wide | extreme_close_up
- pace: static | slow | medium | fast | cut_heavy
- overlay_style: none | bold_center | sub_caption | chyron | sticker
- subject: face | product | text | action | ambient | mixed
- motion: static | handheld | slow_mo | time_lapse | match_cut

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

    Returns the B.4 response shape — 6 shots each with
    t0/t1/cam/voice/viz/overlay/corpus_avg/winner_avg/intel_scene_type/
    overlay_winner plus the Wave 2.5 Phase B PR #6 enrichment fields
    (framing/pace/overlay_style/subject/motion). ``references`` is
    added by the outer ``run_script_generate_sync`` — matcher needs
    the Supabase client which isn't in scope here.
    """
    topic = _sanitize_snippet(body.topic, 500)
    hook = _sanitize_snippet(body.hook, 200)

    creative: list[_CreativeRow] | None = None
    try:
        llm = _call_script_gemini(body)
        creative = [
            (
                s.cam, s.overlay, s.intel_scene_type,
                s.voice, s.viz, s.overlay_winner or "—",
                s.framing, s.pace, s.overlay_style, s.subject, s.motion,
            )
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


# Per-shot reference cap (Wave 2.5 Phase B PR #6). 3 creator scenes per
# shot is plenty — the UX surfaces them as a horizontal strip of cards.
_REFERENCES_PER_SHOT = 3


def _attach_shot_references(
    shots: list[dict[str, Any]],
    *,
    niche_id: int,
    service_sb: Any,
) -> None:
    """Mutate ``shots`` in place, adding a ``references`` list to each.

    Uses the service-role client (not the user client) because
    ``video_shots`` is writer-only under RLS — readers need the
    service client, same as other corpus-backed surfaces.

    Threads ``exclude_video_ids`` across shots so one creator doesn't
    monopolize the whole reference panel. Never raises — a matcher
    failure just yields ``references: []`` for that shot.
    """
    from getviews_pipeline.shot_reference_matcher import pick_shot_references

    used: set[str] = set()
    for i, shot in enumerate(shots):
        descriptor = _shot_to_descriptor(
            intel_scene_type=shot["intel_scene_type"],
            framing=shot.get("framing"),
            pace=shot.get("pace"),
            overlay_style=shot.get("overlay_style"),
            subject=shot.get("subject"),
            motion=shot.get("motion"),
            backbone_idx=i,
        )
        refs = pick_shot_references(
            shot_descriptor=descriptor,
            niche_id=niche_id,
            limit=_REFERENCES_PER_SHOT,
            exclude_video_ids=used,
            client=service_sb,
        )
        shot["references"] = [r.to_dict() for r in refs]
        for r in refs:
            used.add(r.video_id)


def run_script_generate_sync(
    user_sb: Any,
    *,
    user_id: str,
    body: ScriptGenerateBody,
    service_sb: Any | None = None,
) -> dict[str, Any]:
    _decrement_credit_or_raise(user_sb, user_id=user_id)
    shots = build_script_shots(body)

    # Reference lookup against video_shots. service_sb is optional at
    # this layer so tests can inject a mock; in the route handler we
    # pass the real service client. If it's None, we still return a
    # valid response — every shot just has references=[].
    if service_sb is not None:
        try:
            _attach_shot_references(
                shots, niche_id=body.niche_id, service_sb=service_sb,
            )
        except Exception as exc:
            logger.warning("[script/generate] reference attach failed: %s", exc)
            for s in shots:
                s.setdefault("references", [])
    else:
        for s in shots:
            s.setdefault("references", [])

    ref_count = sum(len(s.get("references") or []) for s in shots)
    logger.info(
        "[script/generate] user=%s niche=%d shots=%d refs=%d",
        user_id, body.niche_id, len(shots), ref_count,
    )
    # S6 — per-shot regen narrows the response to a single shot. We still
    # ran the full Gemini call (cheaper than a new prompt + grounding
    # round-trip) but the FE only needs shot[shot_index] to splice back
    # into its local state. Out-of-range indices return the full set so
    # an old client never breaks.
    if body.shot_index is not None and 0 <= body.shot_index < len(shots):
        shots = [shots[body.shot_index]]
    return {"shots": shots}
