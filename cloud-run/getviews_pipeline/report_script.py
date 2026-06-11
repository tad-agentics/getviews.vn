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


class _ScriptNarrativeSection(BaseModel):
    section_id: str = Field(..., max_length=40)
    title_vi: str = Field(..., max_length=120)
    text_vi: str = Field(..., max_length=2000)


class _ScriptNarrativeDiagnosis(BaseModel):
    sections: list[_ScriptNarrativeSection] = Field(min_length=3, max_length=3)


class _ScriptNarrativeVi(BaseModel):
    headline_vi: str = Field(..., max_length=200)
    ket_luan_nhanh: str = Field(..., max_length=600)
    diagnosis_vi: _ScriptNarrativeDiagnosis


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


def _shots_summary_for_narrative(shots: list[dict[str, Any]]) -> str:
    """Per-shot summary incl. the matched reference (when one exists) so the
    narrative can prove each move with a real creator's scene — the report
    must read 'mirror cách @handle mở (250K view)', not generic advice."""
    lines: list[str] = []
    for i, shot in enumerate(shots[:6], start=1):
        t0 = shot.get("t0", 0)
        t1 = shot.get("t1", 0)
        cam = str(shot.get("cam") or "").strip()
        voice = str(shot.get("voice") or "").strip()[:120]
        overlay = str(shot.get("overlay") or "").strip()
        line = (
            f"Cảnh {i} ({t0}-{t1}s): cam={cam}; voice=\"{voice}\"; overlay={overlay}"
        )
        refs = shot.get("references") or []
        if refs and isinstance(refs[0], dict):
            r = refs[0]
            handle = str(r.get("creator_handle") or "").lstrip("@")
            views = r.get("views")
            views_s = f"{int(views):,}".replace(",", ".") if views else "?"
            desc = str(r.get("description") or "")[:60]
            line += f"\n  ref: @{handle or '?'} ({views_s} view) — {desc}"
        lines.append(line)
    return "\n".join(lines)


def synthesize_script_narrative_vi(
    *,
    topic: str,
    hook: str,
    duration: int,
    tone: str,
    niche_label: str,
    shots: list[dict[str, Any]],
    user_id: str | None = None,
) -> dict[str, Any]:
    """Narrative-first script report layer — ``_schema_version: script_v1``."""
    shots_block = _shots_summary_for_narrative(shots)
    niche_line = niche_label.strip() or "ngách TikTok VN"
    prompt = f"""Viết báo cáo kịch bản TikTok bằng tiếng Việt (peer creator, data-backed).

Chủ đề: {topic}
Hook mở: {hook}
Độ dài: {duration}s · Tone: {tone} · Ngách: {niche_line}

6 cảnh đã soạn:
{shots_block}

Trả về JSON:
- headline_vi: một câu headline (≤20 từ) — nêu góc quay rõ ràng
- ket_luan_nhanh: 1-2 câu CHỨNG MINH format này không phải đoán — nếu cảnh nào có
  "ref: @handle (X view)" thì nêu thẳng: "Format này đã được @handle chứng minh (X view)."
- diagnosis_vi.sections: đúng 3 section theo thứ tự:
  1) section_id "hook_analysis" — title_vi + text_vi (phân tích hook 0-3s; nếu Cảnh 1
     có ref: so sánh trực tiếp với cách creator đó mở — "mirror cách @handle mở")
  2) section_id "script_structure" — title_vi + text_vi (dòng chảy 6 cảnh; cảnh nào
     có ref thì gắn 1 mệnh đề ngắn nêu creator + view làm bằng chứng cho nhịp/khung đó)
  3) section_id "next_video" — title_vi + text_vi (video tiếp theo nên quay gì)

Kỷ luật câu: câu ngắn, mỗi câu một ý, mỗi câu mang số hoặc tên creator cụ thể; CẤM câu
đệm ("có thể thấy rằng", "nhìn chung"). Cite số cụ thể khi có; không dùng từ cấm
(bí mật, công thức vàng, triệu view); không mở bằng "Chào bạn"."""

    cfg = types.GenerateContentConfig(
        temperature=0.35,
        response_mime_type="application/json",
        response_json_schema=_ScriptNarrativeVi.model_json_schema(),
    )
    try:
        response = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=[GEMINI_INTENT_MODEL],
            config=cfg,
            call_site="script_narrative_vi",
            user_id=user_id,
        )
        raw = _response_text(response)
        parsed = _ScriptNarrativeVi.model_validate_json(raw)
        data = parsed.model_dump()
        data["_schema_version"] = "script_v1"
        return data
    except Exception as exc:
        logger.warning("[report_script] narrative synthesis failed, fallback: %s", exc)
        return {
            "headline_vi": hook[:200] or topic[:200],
            "ket_luan_nhanh": (
                f"Kịch bản {duration}s theo tone {tone} — hook mở trong 3 giây đầu, "
                f"6 cảnh giữ nhịp xuyên suốt cho {niche_line}."
            ),
            "_schema_version": "script_v1",
            "diagnosis_vi": {
                "sections": [
                    {
                        "section_id": "hook_analysis",
                        "title_vi": "Hook 0–3 giây",
                        "text_vi": f"Mở bằng: «{hook}». Hook cần lộ trong ~1 giây đầu — trùng video top trong kho ngách {niche_line}.",
                    },
                    {
                        "section_id": "script_structure",
                        "title_vi": "Cấu trúc 6 cảnh",
                        "text_vi": f"Chủ đề «{topic}» chia {duration}s thành 6 cảnh — xen cận mặt, b-roll và chữ overlay để giữ retention.",
                    },
                    {
                        "section_id": "next_video",
                        "title_vi": "Video tiếp theo",
                        "text_vi": "Quay biến thể cùng hook với góc setup khác (POV hoặc so sánh trước/sau) để test retention tuần sau.",
                    },
                ],
            },
        }


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
    if step_queue is not None:
        emit(step_queue, step_start("Đang viết phân tích kịch bản…"))
    narrative_vi = synthesize_script_narrative_vi(
        topic=body.topic,
        hook=body.hook,
        duration=body.duration,
        tone=str(body.tone),
        niche_label=niche_label,
        shots=shots,
        user_id=user_id,
    )
    inner: dict[str, Any] = {
        "topic": body.topic,
        "hook": body.hook,
        "hook_delay_ms": body.hook_delay_ms,
        "duration": body.duration,
        "tone": body.tone,
        "niche_label": niche_label,
        "narrative_vi": narrative_vi,
        "shots": shots,
        "format_rationale": out.get("format_rationale"),
        "sources": [],
        "related_questions": [],
    }

    if step_queue is not None:
        emit(step_queue, step_done("Đã soạn kịch bản."))
    return inner
