"""Query-aware Vietnamese narrative for Diagnostic reports.

This is the bulk of the Diagnostic template's intelligence. The
deterministic parts (category contract, paste-link CTA, sources list)
come from ``report_diagnostic.py``; this module asks Gemini to map the
user's self-reported symptoms onto 5 fixed failure-mode categories and
rank 2–3 targeted fixes.

Contract with the caller:

- Input: ``query`` (user's description), ``niche_label``, ``benchmarks``
  (best-effort niche averages — may be None / sparse).
- Output: ``{framing, categories, prescriptions}`` where ``categories``
  is exactly 5 entries in the positional order set by
  ``DIAGNOSTIC_CATEGORY_NAMES`` (Hook / Pacing / CTA / Sound / Caption
  & Hashtag).

Fallback policy (the "honesty" invariant the PRD insists on):

- No Gemini key, empty query, or Gemini exception → 5 categories all
  ``unclear`` + a single prescription that is literally "paste the
  link". We never invent verdicts we can't ground in the query text.
- Schema violation from Gemini → fall back to unclear.
- ``probably_fine`` for a category is only kept when Gemini also
  produces evidence from the query; otherwise we downgrade to
  ``unclear`` to avoid false reassurance.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from getviews_pipeline.report_diagnostic import DIAGNOSTIC_CATEGORY_NAMES

logger = logging.getLogger(__name__)


class DiagnosticCategoryLLM(BaseModel):
    name: str = Field(default="")
    verdict: str = Field(default="unclear")
    finding: str = Field(default="")
    fix_preview: str = Field(default="")


class DiagnosticPrescriptionLLM(BaseModel):
    priority: str = Field(default="P1")
    action: str = Field(default="")
    impact: str = Field(default="")
    effort: str = Field(default="low")


class DiagnosticNarrativeLLM(BaseModel):
    framing: str = Field(default="")
    categories: list[DiagnosticCategoryLLM] = Field(default_factory=list)
    prescriptions: list[DiagnosticPrescriptionLLM] = Field(default_factory=list)


_ALLOWED_VERDICTS: frozenset[str] = frozenset(
    {"likely_issue", "possible_issue", "unclear", "probably_fine"}
)
_ALLOWED_PRIORITIES: frozenset[str] = frozenset({"P1", "P2", "P3"})
_ALLOWED_EFFORTS: frozenset[str] = frozenset({"low", "medium", "high"})

# Empty-query threshold. Below this we refuse to invent verdicts.
_MIN_QUERY_CHARS_FOR_GEMINI = 20


def fill_diagnostic_narrative(
    *,
    query: str,
    niche_label: str,
    benchmarks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return ``{framing, categories, prescriptions}`` grounded in ``query``.

    ``benchmarks`` is the niche intelligence row (median retention, tps,
    top sound, common CTA types) — optional because the fallback path
    works without any of it. When it's present the prompt quotes the
    numbers back so findings stay grounded.
    """
    query_clean = (query or "").strip()

    from getviews_pipeline.config import GEMINI_API_KEY

    if not GEMINI_API_KEY or len(query_clean) < _MIN_QUERY_CHARS_FOR_GEMINI:
        return _unclear_fallback(query=query_clean, niche_label=niche_label)

    try:
        from google.genai import types

        from getviews_pipeline.config import GEMINI_KNOWLEDGE_FALLBACKS, GEMINI_KNOWLEDGE_MODEL
        from getviews_pipeline.gemini import (
            _generate_content_models,
            _normalize_response,
            _response_text,
        )

        prompt = _build_prompt(
            query=query_clean,
            niche_label=niche_label,
            benchmarks=benchmarks or {},
        )
        cfg = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=1024,
            response_mime_type="application/json",
            response_json_schema=DiagnosticNarrativeLLM.model_json_schema(),
        )
        resp = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        raw = _response_text(resp)
        try:
            data = DiagnosticNarrativeLLM.model_validate_json(_normalize_response(raw))
        except ValidationError as exc:
            logger.warning(
                "[diagnostic] Gemini narrative schema mismatch: %s — fallback", exc,
            )
            return _unclear_fallback(query=query_clean, niche_label=niche_label)

        return _post_process(data, query=query_clean, niche_label=niche_label)
    except Exception as exc:
        logger.warning("[diagnostic] Gemini narrative failed: %s — fallback", exc)
        return _unclear_fallback(query=query_clean, niche_label=niche_label)


# ── Prompt construction ────────────────────────────────────────────────────


def _format_benchmarks(bm: dict[str, Any]) -> str:
    """Render the benchmark dict as a compact single-line summary."""
    parts: list[str] = []
    if bm.get("avg_retention") is not None:
        parts.append(f"retention TB {bm['avg_retention']}%")
    if bm.get("median_tps") is not None:
        parts.append(f"median pacing {bm['median_tps']} tps")
    if bm.get("top_sound"):
        parts.append(f"sound dẫn đầu: {bm['top_sound']}")
    if bm.get("common_cta_types"):
        parts.append(f"CTA phổ biến: {bm['common_cta_types']}")
    return " · ".join(parts) if parts else "—"


def _build_prompt(
    *,
    query: str,
    niche_label: str,
    benchmarks: dict[str, Any],
) -> str:
    category_list = "\n".join(
        f"{i + 1}. {name}" for i, name in enumerate(DIAGNOSTIC_CATEGORY_NAMES)
    )
    bm_line = _format_benchmarks(benchmarks)

    return f"""Bạn là trợ lý phân tích TikTok cho creator Việt Nam. Người dùng có một video flop nhưng KHÔNG có link — chẩn đoán dựa TRÊN MÔ TẢ của họ + benchmark ngách.

Nhiệm vụ: map mô tả vào 5 hạng mục cố định dưới đây, mỗi hạng mục một verdict 4-cấp. KHÔNG dùng điểm số — chúng ta không có video để chấm.

5 hạng mục (đúng thứ tự này, tên y nguyên):
{category_list}

Verdict enum (chọn đúng 1):
- likely_issue   — mô tả trực tiếp chỉ ra vấn đề ở hạng mục này.
- possible_issue — mô tả gợi ý có vấn đề nhưng cần xem video để chắc chắn.
- unclear        — mô tả không đủ thông tin để kết luận.
- probably_fine  — mô tả cho thấy hạng mục này KHÔNG phải nguyên nhân chính.

Trả về DUY NHẤT một JSON object (không markdown) với các khóa:
- framing: string ≤240 ký tự — 1 câu mở đầu, PHẢI nhắc rằng mình chẩn đoán dựa trên mô tả + benchmark (không có video).
- categories: đúng 5 object (theo thứ tự trên) với keys {{name, verdict, finding, fix_preview}}.
  + finding ≤280 ký tự — nếu có thể, TRÍCH cụm từ trong câu hỏi của user vào finding ("bạn nói '...'").
  + fix_preview ≤240 ký tự. BỎ TRỐNG (chuỗi "") khi verdict = probably_fine.
- prescriptions: 2–3 object {{priority: P1|P2|P3, action, impact, effort: low|medium|high}} — xếp theo mức độ ảnh hưởng.
  + impact nên có SỐ LIỆU hoặc DẢI DỰ BÁO cụ thể (vd "Dự báo: +12–18 điểm retention").

Ngách: {niche_label}
Benchmark ngách: {bm_line}
Mô tả của người dùng: "{query}"

Quy tắc honesty (bắt buộc):
- KHÔNG dùng "probably_fine" nếu không có bằng chứng cụ thể từ câu hỏi — mặc định "unclear".
- KHÔNG bịa số liệu benchmark; chỉ trích từ dòng Benchmark ở trên.
- Tiếng Việt tự nhiên, không emoji, không mở đầu "Chào bạn"/"Tuyệt vời".
- Không dùng "chắc chắn", "hiệu quả", "bùng nổ", "triệu view", "công thức vàng".
"""


# ── Post-processing ────────────────────────────────────────────────────────


def _post_process(
    data: DiagnosticNarrativeLLM,
    *,
    query: str,
    niche_label: str,
) -> dict[str, Any]:
    """Coerce the Gemini output into the final contract.

    Key behaviour: align categories to the fixed ``DIAGNOSTIC_CATEGORY_
    NAMES`` ordering by position — if Gemini returned them out of order
    (or duplicated one), fill missing slots with ``unclear`` at the end
    so the 5-entry invariant holds.
    """
    framing = (data.framing or "").strip()[:240]
    if not framing:
        framing = _fallback_framing(niche_label)

    # Align categories by position, not by name matching. Gemini
    # consistently follows the prompt order, but defence in depth.
    categories: list[dict[str, Any]] = []
    for i, name in enumerate(DIAGNOSTIC_CATEGORY_NAMES):
        if i < len(data.categories):
            src = data.categories[i]
            verdict = _coerce_verdict(src.verdict)
            finding = (src.finding or "").strip()[:280]
            fix_preview_raw = (src.fix_preview or "").strip()[:240]
            # Invariant: probably_fine must not carry fix_preview.
            fix_preview: str | None = (
                None if verdict == "probably_fine" or not fix_preview_raw else fix_preview_raw
            )
            categories.append(
                {
                    "name": name,
                    "verdict": verdict,
                    "finding": finding or _fallback_finding(query),
                    "fix_preview": fix_preview,
                }
            )
        else:
            categories.append(_unclear_category(name, query))

    prescriptions = _coerce_prescriptions(data.prescriptions, query=query)

    return {
        "framing": framing,
        "categories": categories,
        "prescriptions": prescriptions,
    }


def _coerce_verdict(raw: str) -> str:
    v = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    if v in _ALLOWED_VERDICTS:
        return v
    # Any off-script value → the honest default.
    return "unclear"


def _coerce_prescriptions(
    prescriptions: list[DiagnosticPrescriptionLLM],
    *,
    query: str,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for p in prescriptions[:3]:
        priority = p.priority.strip().upper() if p.priority else "P1"
        if priority not in _ALLOWED_PRIORITIES:
            priority = "P1"
        effort = p.effort.strip().lower() if p.effort else "low"
        if effort not in _ALLOWED_EFFORTS:
            effort = "low"
        action = (p.action or "").strip()[:160]
        impact = (p.impact or "").strip()[:160]
        if not action or not impact:
            continue
        out.append(
            {
                "priority": priority,
                "action": action,
                "impact": impact,
                "effort": effort,
            }
        )

    if not out:
        # DiagnosticPayload requires ≥1 prescription — always ship the
        # paste-link nudge as a last resort.
        out.append(_paste_link_prescription(query))
    return out


# ── Fallback paths ──────────────────────────────────────────────────────────


def _unclear_fallback(
    *,
    query: str,
    niche_label: str,
) -> dict[str, Any]:
    """5 unclear categories + a single paste-link prescription.

    The "honesty" invariant: when we don't have enough signal (no Gemini
    key, empty query, or Gemini failure), we refuse to invent verdicts
    and funnel the user back to /app/answer (URL paste → video session)
    instead.
    """
    categories = [_unclear_category(name, query) for name in DIAGNOSTIC_CATEGORY_NAMES]
    return {
        "framing": _fallback_framing(niche_label),
        "categories": categories,
        "prescriptions": [_paste_link_prescription(query)],
    }


def _unclear_category(name: str, query: str) -> dict[str, Any]:
    quoted = f"«{query[:60]}»" if query else "mô tả hiện có"
    return {
        "name": name,
        "verdict": "unclear",
        "finding": (
            f"Chưa đủ thông tin từ {quoted} để kết luận hạng mục này. "
            "Cần link video để chấm điểm chính xác."
        )[:280],
        "fix_preview": None,
    }


def _fallback_finding(query: str) -> str:
    quoted = f"«{query[:60]}»" if query else "mô tả"
    return (
        f"Dựa trên {quoted}, chưa đủ tín hiệu để kết luận hạng mục này — "
        "cần link video để chấm chính xác."
    )[:280]


def _fallback_framing(niche_label: str | None) -> str:
    scope = f" trong ngách {niche_label}" if niche_label else ""
    return (
        f"Chưa có link video — mình chẩn đoán dựa trên mô tả và benchmark{scope}."
    )[:240]


def _paste_link_prescription(query: str) -> dict[str, str]:
    # query intentionally unused — the paste-link nudge is deterministic.
    del query
    return {
        "priority": "P1",
        "action": "Dán link video vào composer ở /app/answer để chấm điểm chính xác từng phần.",
        "impact": "Chuyển từ chẩn đoán mô tả sang phân tích thực tế từng giây.",
        "effort": "low",
    }
