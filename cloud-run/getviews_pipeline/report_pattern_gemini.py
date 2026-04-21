"""Phase C.2.2 — optional Gemini copy for pattern reports (bounded, fallbacks).

D.2.5.b upgrade: swap manual ``json.loads`` + hand-validated dict schema
for pydantic ``response_json_schema`` binding so the parse-side mirrors
the D.1.2 Script-generate pattern. Hand-tuned per-field truncation +
padding stays identical; only the parser changes.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class PatternNarrativeLLM(BaseModel):
    """Gemini response schema for fill_pattern_narrative.

    List lengths aren't pinned at the schema level — the number of hooks
    varies per call (n_top / n_st), and the post-processing loop pads /
    truncates with deterministic fallbacks. We enforce the outer shape
    (four required keys, each a string or list of strings) so
    model_validate_json raises cleanly on drift.
    """

    thesis: str = Field(default="")
    hook_insights: list[str] = Field(default_factory=list)
    stalled_insights: list[str] = Field(default_factory=list)
    related_questions: list[str] = Field(default_factory=list)


def build_why_won_list(top_hook_labels: list[str]) -> list[str]:
    """Runner-up contrast: each hook vs next-ranked hook in the list."""
    out: list[str] = []
    for i, a in enumerate(top_hook_labels):
        b = top_hook_labels[i + 1] if i + 1 < len(top_hook_labels) else ""
        out.append(_fallback_why_won(a, b)[:200])
    return out


def fill_pattern_narrative(
    *,
    query: str,
    niche_label: str,
    top_hook_labels: list[str],
    stalled_hook_labels: list[str],
) -> dict[str, Any]:
    """Return thesis, hook_insights, stalled_insights, related_questions.

    Uses Gemini JSON when ``GEMINI_API_KEY`` is available; otherwise deterministic
    Vietnamese copy grounded in labels (still bounded).
    """
    from getviews_pipeline.config import GEMINI_API_KEY

    if not GEMINI_API_KEY:
        return _fallback_narrative(query, niche_label, top_hook_labels, stalled_hook_labels)

    try:
        from google.genai import types

        from getviews_pipeline.config import GEMINI_KNOWLEDGE_FALLBACKS, GEMINI_KNOWLEDGE_MODEL
        from getviews_pipeline.gemini import (
            _generate_content_models,
            _normalize_response,
            _response_text,
        )

        n_top = len(top_hook_labels)
        n_st = len(stalled_hook_labels)
        prompt = f"""Bạn là trợ lý phân tích TikTok cho creator Việt Nam.
Trả về DUY NHẤT một JSON object (không markdown) với các khóa:
- thesis: string ≤280 ký tự — tóm tắt xu hướng hook trong ngách.
- hook_insights: đúng {n_top} string, mỗi string ≤200 ký tự — insight cho từng hook thắng theo thứ tự.
- stalled_insights: đúng {n_st} string, mỗi string ≤200 ký tự — vì sao hook suy (theo thứ tự).
- related_questions: đúng 4 string ngắn — câu hỏi follow-up.

Ngách: {niche_label}
Câu hỏi người dùng: {query}
Hook đang thắng (đã xếp hạng): {top_hook_labels}
Hook suy (nếu có): {stalled_hook_labels}
"""
        cfg = types.GenerateContentConfig(
            temperature=0.35,
            max_output_tokens=1024,
            response_mime_type="application/json",
            response_json_schema=PatternNarrativeLLM.model_json_schema(),
        )
        resp = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        raw = _response_text(resp)
        try:
            data = PatternNarrativeLLM.model_validate_json(_normalize_response(raw))
        except ValidationError as exc:
            logger.warning("[pattern] Gemini narrative schema mismatch: %s — fallback", exc)
            return _fallback_narrative(query, niche_label, top_hook_labels, stalled_hook_labels)
        thesis = data.thesis[:280]
        hi = [s[:200] for s in data.hook_insights]
        si = [s[:200] for s in data.stalled_insights]
        rq = [s[:120] for s in data.related_questions][:4]
        while len(hi) < n_top:
            hi.append(_fallback_insight(top_hook_labels[len(hi)]))
        while len(si) < n_st:
            si.append(_fallback_stalled(stalled_hook_labels[len(si)]))
        while len(rq) < 4:
            rq.append(f"Xu hướng nào đang nổi trong {niche_label}?")
        return {
            "thesis": thesis or _fallback_thesis(niche_label, top_hook_labels),
            "hook_insights": hi[:n_top],
            "stalled_insights": si[:n_st],
            "related_questions": rq[:4],
        }
    except Exception as exc:
        logger.warning("[pattern] Gemini narrative failed: %s — fallback", exc)
        return _fallback_narrative(query, niche_label, top_hook_labels, stalled_hook_labels)


def _fallback_thesis(niche_label: str, hooks: list[str]) -> str:
    h = ", ".join(hooks[:3]) if hooks else "các hook đang được ưa chuộng"
    return f"Trong {niche_label}, {h} đang mang lại tín hiệu xem ổn định so với baseline ngách."


def _fallback_insight(label: str) -> str:
    return f"{label} giữ được retention tốt hơn trung vị — phù hợp để test trong 3 video tiếp theo."


def _fallback_stalled(label: str) -> str:
    return f"{label} đang tụt retention; cân nhắc giảm tần suất hoặc đổi hook mở đầu."


def _fallback_why_won(a: str, b: str) -> str:
    if not b:
        return f"{a} khớp với xu hướng xem hiện tại trong ngách."
    return f"{a} bám sát tốc độ tăng view tốt hơn {b} trong cùng cửa sổ."


def _fallback_narrative(
    query: str,
    niche_label: str,
    top_hook_labels: list[str],
    stalled_hook_labels: list[str],
) -> dict[str, Any]:
    thesis = _fallback_thesis(niche_label, top_hook_labels)
    if query:
        thesis = (thesis + f" (Gợi ý từ câu hỏi: {query[:80]})")[:280]
    hi = [_fallback_insight(h) for h in top_hook_labels]
    si = [_fallback_stalled(h) for h in stalled_hook_labels]
    rq = [
        f"Hook nào đang giảm tốc trong {niche_label}?",
        "Format nào đang oversaturated?",
        "Nên test hook mới hay tối ưu hook cũ?",
        "Niche con nào đang breakout tuần này?",
    ]
    return {
        "thesis": thesis,
        "hook_insights": hi,
        "stalled_insights": si,
        "related_questions": rq,
    }
