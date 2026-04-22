"""Query-aware narrative layer for Timing reports.

Prior state (2026-04-22 user report — "follow-up questions generate the
same report every time"): ``build_timing_report`` had
``query: str  # noqa: ARG001 — reserved for future niche refinement``.
The query was accepted and dropped on the floor. Every timing follow-up
for a given niche + window produced byte-identical output, so asking
"khi nào nên post?" and "giờ nào engagement cao nhất?" got the same
copy. This module threads the query through the insight + follow-up
slots so a timing follow-up reads as an answer instead of a template.

Gemini is optional — the fallback still produces query-aware strings
using the ranked window data so no Gemini key / budget exhaustion still
feels responsive to the question.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class TimingNarrativeLLM(BaseModel):
    """Gemini output schema — keep shape minimal so the model can focus
    on producing good Vietnamese copy, not wrangling JSON."""

    insight: str = Field(default="")
    related_questions: list[str] = Field(default_factory=list)


def fill_timing_narrative(
    *,
    query: str,
    niche_label: str,
    top_window: dict[str, Any] | None,
    top_3_windows: list[dict[str, Any]],
    lowest_window: dict[str, str] | None,
    variance_note: str | None,
) -> dict[str, Any]:
    """Return ``{insight, related_questions}`` grounded in the ranked
    window data and phrased as an answer to ``query``."""
    query_clean = (query or "").strip()

    from getviews_pipeline.config import GEMINI_API_KEY

    if not GEMINI_API_KEY or not query_clean:
        return _fallback(
            query=query_clean,
            niche_label=niche_label,
            top_window=top_window,
            lowest_window=lowest_window,
            variance_note=variance_note,
        )

    try:
        from google.genai import types

        from getviews_pipeline.config import GEMINI_KNOWLEDGE_FALLBACKS, GEMINI_KNOWLEDGE_MODEL
        from getviews_pipeline.gemini import (
            _generate_content_models,
            _normalize_response,
            _response_text,
        )

        top_3_summary = ", ".join(
            f"#{w['rank']} {w['day']} {w['hours']} ({w['lift_multiplier']:.1f}×)"
            for w in top_3_windows[:3]
        )
        lowest_summary = (
            f"{lowest_window['day']} {lowest_window['hours']}" if lowest_window else "—"
        )
        prompt = f"""Bạn là trợ lý phân tích TikTok cho creator Việt Nam. Nhiệm vụ: TRẢ LỜI câu hỏi của người dùng bằng dữ liệu cửa sổ đăng, không tóm tắt chung.

Trả về DUY NHẤT một JSON object (không markdown) với các khóa:
- insight: string ≤280 ký tự — MỞ ĐẦU bằng câu trả lời trực tiếp cho câu hỏi; trích rõ ngày + khung giờ + hệ số view; kết bằng gợi ý hành động ngắn.
- related_questions: đúng 3 string ≤120 ký tự — follow-up liên tiếp câu hỏi hiện tại (đào sâu, so sánh, hoặc áp dụng), không phải câu hỏi chung.

Ngách: {niche_label}
Câu hỏi người dùng: "{query_clean}"
Top 3 cửa sổ: {top_3_summary or '—'}
Thấp nhất: {lowest_summary}
Ghi chú biến động: {variance_note or '—'}

Quy tắc:
- Tiếng Việt tự nhiên, không emoji, không mở đầu "Chào bạn".
- Không dùng từ "chắc chắn", "hiệu quả", "bùng nổ".
- Số liệu chỉ được trích từ danh sách trên; không bịa ra %.
"""
        cfg = types.GenerateContentConfig(
            temperature=0.35,
            max_output_tokens=512,
            response_mime_type="application/json",
            response_json_schema=TimingNarrativeLLM.model_json_schema(),
        )
        resp = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        raw = _response_text(resp)
        try:
            data = TimingNarrativeLLM.model_validate_json(_normalize_response(raw))
        except ValidationError as exc:
            logger.warning("[timing] Gemini narrative schema mismatch: %s — fallback", exc)
            return _fallback(
                query=query_clean,
                niche_label=niche_label,
                top_window=top_window,
                lowest_window=lowest_window,
                variance_note=variance_note,
            )

        insight = (data.insight or "").strip()[:280]
        rq = [s.strip()[:120] for s in data.related_questions if s and s.strip()][:3]
        while len(rq) < 3:
            rq.append(_fallback_related_at(len(rq), niche_label, top_window))
        return {
            "insight": insight or _fallback_insight(
                query=query_clean, top_window=top_window, lowest_window=lowest_window,
            ),
            "related_questions": rq,
        }
    except Exception as exc:
        logger.warning("[timing] Gemini narrative failed: %s — fallback", exc)
        return _fallback(
            query=query_clean,
            niche_label=niche_label,
            top_window=top_window,
            lowest_window=lowest_window,
            variance_note=variance_note,
        )


def _fallback(
    *,
    query: str,
    niche_label: str,
    top_window: dict[str, Any] | None,
    lowest_window: dict[str, str] | None,
    variance_note: str | None,  # noqa: ARG001 — reserved for future fallback enrichment
) -> dict[str, Any]:
    return {
        "insight": _fallback_insight(query=query, top_window=top_window, lowest_window=lowest_window),
        "related_questions": [
            _fallback_related_at(0, niche_label, top_window),
            _fallback_related_at(1, niche_label, top_window),
            _fallback_related_at(2, niche_label, top_window),
        ],
    }


def _fallback_insight(
    *,
    query: str,
    top_window: dict[str, Any] | None,
    lowest_window: dict[str, str] | None,
) -> str:
    if not top_window:
        return "Chưa đủ tín hiệu để xếp hạng cửa sổ đăng."
    day = top_window.get("day", "—")
    hours = top_window.get("hours", "—")
    lift = float(top_window.get("lift_multiplier") or 1.0)
    low = (
        f"Thấp nhất: {lowest_window['hours']} {lowest_window['day']}."
        if lowest_window
        else ""
    )
    lead = (
        f"Theo câu hỏi «{query[:80]}», khung {day} {hours} đang dẫn đầu"
        if query
        else f"Khung {day} {hours} đang dẫn đầu"
    )
    return (f"{lead} — view gấp {lift:.1f}× trung bình ngách. {low}").strip()


def _fallback_related_at(
    idx: int, niche_label: str, top_window: dict[str, Any] | None
) -> str:
    day = (top_window or {}).get("day", "—")
    options = [
        f"Khung {day} giữ #1 được bao lâu trong ngách {niche_label}?",
        "Cửa sổ phụ nào phù hợp cho kênh nhỏ?",
        f"Nên điều chỉnh giờ đăng theo ngách con nào trong {niche_label}?",
    ]
    return options[idx % len(options)]
