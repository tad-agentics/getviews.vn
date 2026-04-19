"""B.4 — POST ``/script/generate``: credit gate + deterministic shot scaffold.

v1 returns a **template** shot list shaped like the studio merge contract (no Gemini).
Client continues to merge ``scene_intelligence`` for corpus/winner bars and tips.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ScriptTone = Literal["Hài", "Chuyên gia", "Tâm sự", "Năng lượng", "Mỉa mai"]


class InsufficientCreditsError(Exception):
    """``decrement_credit`` returned false or raised."""


class ScriptGenerateBody(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    hook: str = Field(..., min_length=1, max_length=200)
    hook_delay_ms: int = Field(ge=400, le=3000)
    duration: int = Field(ge=15, le=90)
    tone: ScriptTone
    niche_id: int = Field(ge=1)


# Relative weights match ``ScriptScreen`` BASE_SHOTS spans (3+5+8+8+6+2 = 32).
_WEIGHTS: tuple[int, ...] = (3, 5, 8, 8, 6, 2)
_BACKBONE: tuple[tuple[str, str, str, str, str, str, float, float, str], ...] = (
    (
        "Cận mặt",
        "BOLD CENTER",
        "face_to_camera",
        "Hook: mở với {hook} — {topic}",
        'Chữ nổi + "{topic_short}"',
        2.8,
        2.4,
        "white sans 28pt · bottom-center",
    ),
    (
        "Cắt nhanh b-roll",
        "SUB-CAPTION",
        "product_shot",
        "B-roll: nhấn {topic_short}",
        "Cắt nhanh, slow-mo nhẹ",
        4.2,
        5.0,
        "yellow outlined · mid-left",
    ),
    (
        "Side-by-side",
        "STAT BURST",
        "demo",
        "So sánh / demo trung tâm: {topic_short}",
        "Split-screen, số liệu nổi",
        7.8,
        8.0,
        "number callout 72pt",
    ),
    (
        "POV nghe",
        "LABEL",
        "face_to_camera",
        "Giọng {tone}: giải thích {topic_short}",
        "POV, ánh sáng ấm",
        6.2,
        7.5,
        "caption strip · bottom",
    ),
    (
        "Cận tay + texture",
        "NONE",
        "action",
        "Texture + cảm nhận: {topic_short}",
        "Cận chi tiết, xoay nhẹ",
        5.1,
        5.0,
        "—",
    ),
    (
        "Cận mặt + câu hỏi",
        "QUESTION XL",
        "face_to_camera",
        "CTA: hỏi người xem về {topic_short}",
        "Câu hỏi to trên màn",
        2.4,
        2.5,
        "question mark · full bleed",
    ),
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


def build_script_shots(body: ScriptGenerateBody) -> list[dict[str, Any]]:
    topic = _sanitize_snippet(body.topic, 500)
    hook = _sanitize_snippet(body.hook, 200)
    topic_short = _sanitize_snippet(topic, 36)
    tone = body.tone
    lens = _segment_lengths(body.duration)
    t0 = 0
    out: list[dict[str, Any]] = []
    for i, row in enumerate(_BACKBONE):
        cam, overlay, intel_scene, voice_tpl, viz_tpl, cavg, wavg, owin = row
        span = lens[i] if i < len(lens) else 1
        t1 = t0 + span
        voice = voice_tpl.format(hook=hook, topic=topic, topic_short=topic_short, tone=tone)
        viz = viz_tpl.format(hook=hook, topic=topic, topic_short=topic_short, tone=tone)
        out.append(
            {
                "t0": t0,
                "t1": t1,
                "cam": cam,
                "voice": _sanitize_snippet(voice, 220),
                "viz": _sanitize_snippet(viz, 200),
                "overlay": overlay,
                "corpus_avg": cavg,
                "winner_avg": wavg,
                "intel_scene_type": intel_scene,
                "overlay_winner": owin,
            }
        )
        t0 = t1
    return out


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
