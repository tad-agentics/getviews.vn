"""Phase C.2.2 — optional Gemini copy for pattern reports (bounded, fallbacks)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def build_why_won_list(top_hook_labels: list[str]) -> list[str]:
    """Runner-up contrast: each hook vs next-ranked hook in the list."""
    out: list[str] = []
    for i, a in enumerate(top_hook_labels):
        b = top_hook_labels[i + 1] if i + 1 < len(top_hook_labels) else ""
        out.append(_fallback_why_won(a, b)[:200])
    return out


def _strip_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


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

        from getviews_pipeline.config import GEMINI_KNOWLEDGE_MODEL, GEMINI_KNOWLEDGE_FALLBACKS
        from getviews_pipeline.gemini import _generate_content_models, _response_text

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
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "thesis": {"type": "string"},
                "hook_insights": {"type": "array", "items": {"type": "string"}},
                "stalled_insights": {"type": "array", "items": {"type": "string"}},
                "related_questions": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
            },
            "required": ["thesis", "hook_insights", "stalled_insights", "related_questions"],
        }
        cfg = types.GenerateContentConfig(
            temperature=0.35,
            max_output_tokens=1024,
            response_mime_type="application/json",
            response_json_schema=schema,
        )
        resp = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        raw = _response_text(resp)
        data = json.loads(_strip_json(raw))
        thesis = str(data.get("thesis") or "")[:280]
        hi = [str(x)[:200] for x in (data.get("hook_insights") or [])]
        si = [str(x)[:200] for x in (data.get("stalled_insights") or [])]
        rq = [str(x)[:120] for x in (data.get("related_questions") or [])][:4]
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
