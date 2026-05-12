"""Answer-session report builder for ``format=script`` / shot_list intent."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from google.genai import types
from pydantic import BaseModel, Field

from getviews_pipeline.config import GEMINI_INTENT_MODEL, GEMINI_KNOWLEDGE_MODEL
from getviews_pipeline.gemini import _generate_content_models, _response_text
from getviews_pipeline.script_generate import (
    InsufficientCreditsError,
    ScriptGenerateBody,
    ScriptTone,
    run_script_generate_sync,
)
from getviews_pipeline.step_events import emit, step_done, step_start
from getviews_pipeline.supabase_client import get_service_client

logger = logging.getLogger(__name__)

_VALID_TONES: frozenset[str] = frozenset(
    {"Hài", "Chuyên gia", "Tâm sự", "Năng lượng", "Mỉa mai"},
)


class _ScriptQueryExtract(BaseModel):
    """LLM extraction of script params from free-form Vietnamese."""

    topic: str = Field(..., max_length=500)
    hook: str = Field(..., max_length=200)
    duration: int = Field(default=30, ge=15, le=90)
    tone: str = Field(default="Chuyên gia", max_length=20)


def _normalize_duration_from_text(q: str) -> int | None:
    m = re.search(r"(\d{2,3})\s*(?:s|giây|sec)", q, re.I)
    if m:
        d = int(m.group(1))
        if 15 <= d <= 90:
            return d
    return None


def _coerce_tone(raw: str) -> ScriptTone:
    s = (raw or "").strip()
    if s in _VALID_TONES:
        return s  # type: ignore[return-value]
    return "Chuyên gia"


def _extract_script_params_from_query(
    query: str,
    *,
    niche_id: int,
    user_id: str | None = None,
) -> ScriptGenerateBody:
    """Map composer text → ScriptGenerateBody (Gemini with heuristic fallback)."""
    q = query.strip()
    dur_hint = _normalize_duration_from_text(q)
    topic_fb = (q[:500] if q else "Video TikTok").strip() or "Video TikTok"
    hook_fb = (q[:200] if len(q) <= 200 else q[:197] + "…").strip() or "Hook mở đầu rõ ràng"

    try:
        prompt = f"""Trích xuất tham số kịch bản TikTok từ tin nhắn người dùng (tiếng Việt).

Tin nhắn:
---
{q[:8000]}
---

Trả về JSON:
- topic: chủ đề chính (ngắn gọn, ≤500 ký tự)
- hook: câu mở đầu / ý hook (≤200 ký tự)
- duration: số nguyên 15–90 (giây); nếu không rõ thì 30
- tone: MỘT trong: Hài | Chuyên gia | Tâm sự | Năng lượng | Mỉa mai (mặc định Chuyên gia)

Ưu tiên nội dung gợi ý sửa / shot-list / chẩn đoán trong tin nhắn để làm topic và hook."""

        cfg = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_json_schema=_ScriptQueryExtract.model_json_schema(),
        )
        response = _generate_content_models(
            [prompt],
            primary_model=GEMINI_INTENT_MODEL,
            fallbacks=[GEMINI_KNOWLEDGE_MODEL],
            config=cfg,
            call_site="script_query_extract",
            user_id=user_id,
        )
        raw = _response_text(response)
        ext = _ScriptQueryExtract.model_validate_json(raw)
        duration = ext.duration
        if dur_hint is not None:
            duration = dur_hint
        return ScriptGenerateBody(
            topic=ext.topic.strip()[:500] or topic_fb,
            hook=ext.hook.strip()[:200] or hook_fb,
            hook_delay_ms=1000,
            duration=duration,
            tone=_coerce_tone(ext.tone),
            niche_id=niche_id,
            shot_index=None,
        )
    except Exception as exc:
        logger.warning("[report_script] extract failed, heuristic fallback: %s", exc)
        duration = dur_hint or 30
        return ScriptGenerateBody(
            topic=topic_fb,
            hook=hook_fb,
            hook_delay_ms=1000,
            duration=duration,
            tone="Chuyên gia",
            niche_id=niche_id,
            shot_index=None,
        )


def _niche_label_sync(niche_id: int) -> str:
    if niche_id <= 0:
        return ""
    try:
        sb = get_service_client()
        row = (
            sb.table("niche_taxonomy")
            .select("name_vn, name_en")
            .eq("id", niche_id)
            .maybe_single()
            .execute()
        )
        d = row.data or {}
        return str(d.get("name_vn") or d.get("name_en") or "").strip()
    except Exception:
        return ""


def build_script_report(
    *,
    service_sb: Any,
    user_sb: Any,
    user_id: str,
    query: str,
    niche_id: int,
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    """Build validated ``script`` report dict for ``validate_and_store_report``.

    Credits: caller (``append_turn``) deducts 3× ``decrement_credit`` before
    this runs — ``run_script_generate_sync(..., deduct_credit=False)``.
    """
    if step_queue is not None:
        emit(step_queue, step_start("Đang soạn kịch bản 6 cảnh…"))

    body = _extract_script_params_from_query(query, niche_id=niche_id, user_id=user_id)
    try:
        out = run_script_generate_sync(
            user_sb,
            user_id=user_id,
            body=body,
            service_sb=service_sb,
            deduct_credit=False,
        )
    except InsufficientCreditsError:
        raise
    shots = out.get("shots") or []
    if len(shots) != 6:
        logger.error("[report_script] expected 6 shots, got %d", len(shots))
        raise RuntimeError("script_incomplete")

    niche_label = _niche_label_sync(niche_id)
    inner: dict[str, Any] = {
        "topic": body.topic,
        "hook": body.hook,
        "hook_delay_ms": body.hook_delay_ms,
        "duration": body.duration,
        "tone": body.tone,
        "niche_label": niche_label,
        "shots": shots,
        "sources": [],
        "related_questions": [],
    }

    if step_queue is not None:
        emit(step_queue, step_done("Đã soạn kịch bản."))
    return inner
