"""Query-aware Vietnamese narrative for Lifecycle reports.

The deterministic aggregation (cell stages, reach deltas, health scores,
optional instance counts) comes from ``report_lifecycle_compute.py``.
This module turns those numbers into Vietnamese copy that *answers the
user's question* — ``subject_line`` + per-cell ``insight`` +
``related_questions`` — so two follow-ups on the same niche produce
different text rather than byte-identical boilerplate (the 2026-04-22
"follow-ups all look the same" bug).

Gemini is optional. When ``GEMINI_API_KEY`` is unset or the call fails
the fallback paths produce deterministic but query-prefixed strings so
the UX stays coherent under budget exhaustion.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from getviews_pipeline.report_types import LifecycleMode

logger = logging.getLogger(__name__)


class LifecycleNarrativeLLM(BaseModel):
    """Schema Gemini must return. Cell insights are addressed by index so
    we can line them up with the deterministic cell list on the way out.

    ``refresh_moves`` is optional — the caller decides whether to include
    them based on the cell stages (the Pydantic invariant on
    ``LifecyclePayload`` rejects moves when no cell is declining/plateau).
    """

    subject_line: str = Field(default="")
    cell_insights: list[str] = Field(default_factory=list)
    refresh_moves: list[dict[str, str]] = Field(default_factory=list)
    related_questions: list[str] = Field(default_factory=list)


def fill_lifecycle_narrative(
    *,
    query: str,
    niche_label: str,
    mode: LifecycleMode,
    cells: list[dict[str, Any]],
    has_weak_cell: bool,
) -> dict[str, Any]:
    """Return ``{subject_line, cell_insights, refresh_moves, related_questions}``.

    ``cells`` is the deterministic cell list (already ranked, already
    stage-classified). The narrative layer doesn't invent numbers — it
    reads off the deltas / scores and phrases them in the user's voice.

    ``has_weak_cell`` gates ``refresh_moves`` at the prompt level; the
    Pydantic invariant on ``LifecyclePayload`` would reject moves on a
    healthy-only report anyway, but skipping the prompt slot saves tokens.
    """
    query_clean = (query or "").strip()
    n_cells = len(cells)

    from getviews_pipeline.config import GEMINI_API_KEY

    if not GEMINI_API_KEY or not query_clean or n_cells == 0:
        return _fallback(
            query=query_clean,
            niche_label=niche_label,
            mode=mode,
            cells=cells,
            has_weak_cell=has_weak_cell,
        )

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
            mode=mode,
            cells=cells,
            has_weak_cell=has_weak_cell,
        )
        cfg = types.GenerateContentConfig(
            temperature=0.35,
            max_output_tokens=768,
            response_mime_type="application/json",
            response_json_schema=LifecycleNarrativeLLM.model_json_schema(),
        )
        resp = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        raw = _response_text(resp)
        try:
            data = LifecycleNarrativeLLM.model_validate_json(_normalize_response(raw))
        except ValidationError as exc:
            logger.warning("[lifecycle] Gemini narrative schema mismatch: %s — fallback", exc)
            return _fallback(
                query=query_clean, niche_label=niche_label,
                mode=mode, cells=cells, has_weak_cell=has_weak_cell,
            )

        subject = (data.subject_line or "").strip()[:240]

        # Align cell insights 1-to-1 with the deterministic cell list.
        # Pad missing / truncate extras; clamp each to 240 chars.
        insights_raw = [str(s or "").strip()[:240] for s in data.cell_insights]
        while len(insights_raw) < n_cells:
            insights_raw.append(_fallback_cell_insight(cells[len(insights_raw)], mode))
        insights_raw = insights_raw[:n_cells]

        moves: list[dict[str, str]] = []
        if has_weak_cell:
            for m in data.refresh_moves[:4]:
                title = str(m.get("title") or "").strip()[:120]
                detail = str(m.get("detail") or "").strip()[:280]
                effort = str(m.get("effort") or "low").strip().lower()
                if effort not in ("low", "medium", "high"):
                    effort = "low"
                if title and detail:
                    moves.append({"title": title, "detail": detail, "effort": effort})

        rq = [s.strip()[:120] for s in data.related_questions if s and s.strip()][:3]
        while len(rq) < 3:
            rq.append(_fallback_related_at(len(rq), niche_label, mode, cells))

        return {
            "subject_line": subject or _fallback_subject(
                query=query_clean, cells=cells, mode=mode,
            ),
            "cell_insights": insights_raw,
            "refresh_moves": moves,
            "related_questions": rq,
        }
    except Exception as exc:
        logger.warning("[lifecycle] Gemini narrative failed: %s — fallback", exc)
        return _fallback(
            query=query_clean, niche_label=niche_label,
            mode=mode, cells=cells, has_weak_cell=has_weak_cell,
        )


# ── Prompt construction ─────────────────────────────────────────────────────


_MODE_BRIEFS: dict[LifecycleMode, str] = {
    "format": (
        "Người dùng muốn biết FORMAT video nào còn chạy được. Mỗi cell là một "
        "format (short-form, carousel, recipe, tutorial, haul...). "
        "``subject_line`` phải nói rõ format nào đang lên và format nào nên giảm."
    ),
    "hook_fatigue": (
        "Người dùng muốn biết HOOK đang hỏi còn dùng được không. Cell đầu là "
        "hook đang bị fatigue (declining). Các cell sau là hook cùng họ để thay thế. "
        "``subject_line`` phải trích số phần trăm giảm cụ thể từ cell đầu."
    ),
    "subniche": (
        "Người dùng muốn biết NGÁCH CON nào đang nổi trong ngách lớn. Mỗi cell "
        "là một sub-niche với instance_count (số creator đang làm). ``subject_line`` "
        "phải liệt kê ngách con đang rising + ngách con đang declining."
    ),
}


def _build_prompt(
    *,
    query: str,
    niche_label: str,
    mode: LifecycleMode,
    cells: list[dict[str, Any]],
    has_weak_cell: bool,
) -> str:
    cell_lines: list[str] = []
    for i, c in enumerate(cells):
        parts = [
            f"#{i + 1} {c.get('name', '—')}",
            f"stage={c.get('stage', '—')}",
            f"Δ reach={float(c.get('reach_delta_pct') or 0):+.0f}%",
            f"health={int(c.get('health_score') or 0)}",
        ]
        if c.get("retention_pct") is not None:
            parts.append(f"retention={float(c['retention_pct']):.0f}%")
        if c.get("instance_count") is not None:
            parts.append(f"instances={int(c['instance_count'])}")
        cell_lines.append(" · ".join(parts))

    brief = _MODE_BRIEFS[mode]
    moves_slot = (
        "\n- refresh_moves: 2-3 object {title, detail, effort:'low'|'medium'|'high'} — "
        "khắc phục cell yếu nhất. Mỗi tactic phải có SỐ LIỆU hoặc BƯỚC CỤ THỂ."
        if has_weak_cell
        else "\n- refresh_moves: mảng rỗng (không có cell nào yếu)."
    )

    return f"""Bạn là trợ lý phân tích TikTok cho creator Việt Nam. Nhiệm vụ: TRẢ LỜI câu hỏi của người dùng bằng dữ liệu chu trình sống (lifecycle) dưới đây, không tóm tắt chung.

{brief}

Trả về DUY NHẤT một JSON object (không markdown) với các khóa:
- subject_line: string ≤240 ký tự — 1 câu trực tiếp trả lời câu hỏi; trích cụ thể cell nào dẫn đầu / cell nào đang yếu + con số.
- cell_insights: đúng {len(cells)} string ≤240 ký tự — mỗi string là insight cho cell thứ i (cùng thứ tự danh sách dưới). Giải thích tại sao cell đó ở stage đó + hành động cụ thể. Không nhắc lại số liệu đã có trong payload.{moves_slot}
- related_questions: đúng 3 string ≤120 ký tự — follow-up đào sâu câu hỏi hiện tại (so sánh, áp dụng, kênh nhỏ), không phải câu hỏi chung.

Ngách: {niche_label}
Câu hỏi người dùng: "{query}"
Cells (đã xếp hạng):
{chr(10).join(cell_lines)}

Quy tắc:
- Tiếng Việt tự nhiên, không emoji, không mở đầu "Chào bạn" hay "Tuyệt vời".
- Không dùng "chắc chắn", "hiệu quả", "bùng nổ", "triệu view", "công thức vàng".
- Số liệu chỉ được trích từ danh sách cell trên; không bịa ra con số.
- ``refresh_moves`` chỉ xuất hiện khi có cell declining/plateau.
"""


# ── Fallback (no Gemini key / call failed) ─────────────────────────────────


def _fallback(
    *,
    query: str,
    niche_label: str,
    mode: LifecycleMode,
    cells: list[dict[str, Any]],
    has_weak_cell: bool,
) -> dict[str, Any]:
    return {
        "subject_line": _fallback_subject(query=query, cells=cells, mode=mode),
        "cell_insights": [_fallback_cell_insight(c, mode) for c in cells],
        "refresh_moves": _fallback_refresh_moves(cells) if has_weak_cell else [],
        "related_questions": [
            _fallback_related_at(0, niche_label, mode, cells),
            _fallback_related_at(1, niche_label, mode, cells),
            _fallback_related_at(2, niche_label, mode, cells),
        ],
    }


def _fallback_subject(
    *,
    query: str,
    cells: list[dict[str, Any]],
    mode: LifecycleMode,
) -> str:
    if not cells:
        return "Chưa đủ dữ liệu để xếp hạng lifecycle."
    lead = cells[0]
    lead_name = str(lead.get("name") or "—")
    delta = float(lead.get("reach_delta_pct") or 0)
    sign = "+" if delta >= 0 else ""
    if mode == "hook_fatigue":
        # Lead cell is the fatigued hook — quote its drop explicitly.
        pct = abs(int(round(delta)))
        head = f"Hook {lead_name} giảm {pct}% — xem 2 hook cùng họ để thay thế"
    elif mode == "subniche":
        rising = [c for c in cells if c.get("stage") == "rising"]
        head = (
            f"{len(rising)} ngách con đang lên — {lead_name} dẫn đầu ({sign}{int(round(delta))}%)"
            if rising
            else f"{lead_name} dẫn đầu ({sign}{int(round(delta))}%)"
        )
    else:
        head = f"{lead_name} dẫn đầu ({sign}{int(round(delta))}% reach)"
    suffix = f" — theo câu hỏi «{query[:80]}»" if query else ""
    return (head + suffix)[:240]


def _fallback_cell_insight(cell: dict[str, Any], mode: LifecycleMode) -> str:
    stage = cell.get("stage") or "—"
    delta = float(cell.get("reach_delta_pct") or 0)
    sign = "+" if delta >= 0 else ""
    base = f"{stage.capitalize()} · {sign}{int(round(delta))}% reach"
    if stage == "rising":
        return (base + " — ưu tiên cho tuần tới.")[:240]
    if stage == "peak":
        return (base + " — tận dụng khi còn đà.")[:240]
    if stage == "plateau":
        return (base + " — chỉ giữ khi có mục đích rõ.")[:240]
    if stage == "declining":
        if mode == "hook_fatigue":
            return (base + " — fatigue rõ, đổi sang hook cùng họ.")[:240]
        return (base + " — giảm tần suất hoặc refresh ngay.")[:240]
    return base[:240]


def _fallback_refresh_moves(cells: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Three generic refresh tactics — sound / hook / visual evidence. These
    map 1:1 with the fixture refresh moves so callers can swap in Gemini
    output without changing the rendering shape."""
    return [
        {
            "title": "Đổi audio sang trending tuần này",
            "detail": (
                "Sound đang dùng đã bão hòa trong ngách — đổi sang top-5 trending "
                "để thuật toán đánh giá lại."
            ),
            "effort": "low",
        },
        {
            "title": "Rút hook về ≤ 1.2 giây",
            "detail": (
                "Cắt câu giới thiệu, đưa thẳng câu hỏi chốt lên khung đầu để "
                "retention 1s tăng."
            ),
            "effort": "medium",
        },
        {
            "title": "Bổ sung visual evidence trong 3–8s",
            "detail": (
                "Số liệu hoặc close-up sản phẩm trong khoảng 3–8s giữ người "
                "xem khỏi swipe."
            ),
            "effort": "medium",
        },
    ]


def _fallback_related_at(
    idx: int,
    niche_label: str,
    mode: LifecycleMode,
    cells: list[dict[str, Any]],
) -> str:
    lead = cells[0].get("name") if cells else "—"
    if mode == "format":
        options = [
            f"Format {lead} phù hợp kênh < 10K không?",
            f"Bao lâu thì format này sẽ chững trong {niche_label}?",
            "Format nào nên kết hợp với format đang dẫn đầu?",
        ]
    elif mode == "hook_fatigue":
        options = [
            "Hook nào sẽ là người thay thế tiếp theo?",
            "Có refresh hook này bằng audio mới được không?",
            f"Kênh nhỏ trong {niche_label} có nên đổi hook sớm không?",
        ]
    else:
        options = [
            f"Ngách con {lead} cần bao nhiêu video để lên?",
            f"Có overlap giữa ngách con top trong {niche_label} không?",
            "Ngách con nào phù hợp creator < 10K follower?",
        ]
    return options[idx % len(options)][:120]
