"""Phase C.5.1 — optional Gemini hedging narrative for Generic reports.

Generic is the humility landing, so the Gemini prompt is deliberately
hedge-heavy: the model is instructed to:

- Open by acknowledging the query is outside the trained taxonomy.
- Offer a best-effort rough interpretation based on the broad corpus
  slice, NOT a confident recommendation.
- Close by pointing at the three destination tools (OffTaxonomyBanner).

The result is capped at 2 paragraphs × 320 chars by
``report_generic_compute.cap_paragraphs`` before the payload is
validated. Gemini failures fall through to the deterministic hedging
copy in ``report_generic._generate_narrative``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _strip_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


_SYSTEM_HEDGE = (
    "Bạn đang trả lời câu hỏi ngoài taxonomy (confidence thấp). "
    "QUY TẮC:\n"
    "1. Không hứa chắc, không dùng từ 'chắc chắn', 'hiệu quả', 'sẽ'.\n"
    "2. Chỉ nêu hướng gần đúng dựa trên corpus rộng, không kết luận ngách cụ thể.\n"
    "3. Kết bằng câu gợi ý mở công cụ chuyên biệt (Soi Kênh / Xưởng Viết / Tìm KOL).\n"
    "Trả về JSON đúng shape: "
    '{"paragraphs": ["đoạn 1 ≤ 260 ký tự", "đoạn 2 ≤ 260 ký tự"]}.'
)


def fill_generic_narrative(
    *,
    query: str,
    niche_label: str | None,
    sample_n: int,
    window_days: int,
) -> list[str]:
    """Return 1–2 hedged paragraphs. Empty list on Gemini error or budget
    exceeded — caller supplies deterministic fallback copy.

    D.2.5.a — shares the classifier Gemini daily budget
    (``CLASSIFIER_GEMINI_DAILY_MAX``). When the pool is exhausted, skip
    the Gemini call entirely + log ``[generic-budget]`` so D.5.1 can
    surface how often Generic turns ran deterministic vs hedged.
    """
    try:
        from getviews_pipeline.gemini import gemini_text_only  # type: ignore[attr-defined]
    except Exception as exc:
        logger.info("[generic-gemini] SDK not available: %s", exc)
        return []

    # D.2.5.a — gate on the shared classifier-Gemini budget BEFORE the
    # outbound call. Keeps the $70/mo cost ceiling honest even on
    # Generic-heavy days without a second budget counter to track.
    try:
        from getviews_pipeline.ensemble import (
            ClassifierDailyBudgetExceeded,
            consume_classifier_gemini_budget_or_raise,
        )
        consume_classifier_gemini_budget_or_raise()
    except ClassifierDailyBudgetExceeded as exc:
        logger.warning(
            "[generic-budget] [fill_generic_narrative] %s — deterministic fallback (no Gemini call)",
            exc,
        )
        return []
    except Exception as exc:  # pragma: no cover — defensive
        logger.info("[generic-budget] budget check failed: %s", exc)

    scope_line = f"niche {niche_label}" if niche_label else "corpus rộng đa ngách"
    prompt = (
        f"{_SYSTEM_HEDGE}\n\n"
        f"USER QUERY: {query[:200]}\n"
        f"CONTEXT: {sample_n} video trong {scope_line}, {window_days} ngày qua.\n"
        "Viết tiếng Việt tự nhiên, không có emoji, không dùng 'Chào bạn'."
    )
    try:
        raw = gemini_text_only(prompt=prompt, max_output_tokens=320)
    except Exception as exc:
        logger.info("[generic-gemini] call failed: %s", exc)
        return []

    if not raw:
        return []

    try:
        data: dict[str, Any] = json.loads(_strip_json(str(raw)))
    except Exception:
        logger.info("[generic-gemini] parse failed; falling back")
        return []

    paras_raw = data.get("paragraphs")
    if not isinstance(paras_raw, list):
        return []
    return [str(p) for p in paras_raw if isinstance(p, str) and p.strip()]
