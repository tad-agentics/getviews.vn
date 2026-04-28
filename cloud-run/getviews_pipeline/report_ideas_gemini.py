"""Query-aware narrative layer for Ideas reports.

Prior state (2026-04-22 user report): ``build_ideas_report``'s ``lead``
paragraph and ``related_questions`` were hardcoded — they referenced
``sample_n`` + ``niche_label`` but not the user's actual question. A
user asking "ý tưởng nào cho mẹ bỉm?" and one asking "cách làm video
dưới 30s hiệu quả?" got the same lead. This module lets Gemini rewrite
those two fields around the question while keeping the deterministic
ideas / styles / stop_doing cards intact.

Falls back to query-aware deterministic copy when Gemini is
unavailable, so no-key / budget-exhausted environments still produce
responsive-looking text.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class IdeaBlockCopy(BaseModel):
    """Per-rank copy emitted by Gemini for one entry in the top-5
    ideas list. 2026-05-10 — Wave 2 PR #3 content-calendar reframe.

    ``opening_line``: the first 6–12 words a creator would speak on
    camera to open this video. Vietnamese, natural, no emoji, no
    forbidden copy-rule openers ("Chào bạn", "Tuyệt vời", "Wow").

    ``content_angle``: one-line summary of what this video is ABOUT
    (vs. ``opening_line`` which is how it STARTS). Under 120 chars.
    """
    rank: int = Field(ge=1, le=5)
    opening_line: str = Field(default="")
    content_angle: str = Field(default="")


class IdeasNarrativeLLM(BaseModel):
    lead: str = Field(default="")
    related_questions: list[str] = Field(default_factory=list)
    # 2026-05-10 — Wave 2 PR #3: per-rank copy for the "5 video tiếp
    # theo" content-calendar layout. Each entry keyed to ``rank``
    # (1..5). Optional because the fallback path (no Gemini key /
    # budget exhausted) returns an empty list and the caller keeps
    # the deterministic templates from compute_ideas_blocks.
    hook_lines: list[IdeaBlockCopy] = Field(default_factory=list)


def normalize_hook_lines(raw: list[IdeaBlockCopy]) -> list[dict[str, Any]]:
    """Validate + dedup Gemini's ``hook_lines`` list for wire output.

    Drops entries with out-of-range rank, duplicate rank (first wins),
    or empty ``opening_line``. Returns dicts sorted by rank ascending
    with fields trimmed to display caps.
    """
    out: list[dict[str, Any]] = []
    seen_ranks: set[int] = set()
    for entry in raw:
        rank = int(entry.rank)
        if rank < 1 or rank > 5 or rank in seen_ranks:
            continue
        opening = (entry.opening_line or "").strip()[:120]
        angle = (entry.content_angle or "").strip()[:240]
        if not opening:
            continue
        seen_ranks.add(rank)
        out.append({"rank": rank, "opening_line": opening, "content_angle": angle})
    out.sort(key=lambda d: d["rank"])
    return out


def fill_ideas_narrative(
    *,
    query: str,
    niche_label: str,
    sample_n: int,
    top_idea_hooks: list[str],
) -> dict[str, Any]:
    """Return ``{lead, related_questions}`` grounded in the top ideas and
    phrased as an answer to ``query``."""
    query_clean = (query or "").strip()

    from getviews_pipeline.config import GEMINI_API_KEY

    if not GEMINI_API_KEY or not query_clean:
        return _fallback(
            query=query_clean,
            niche_label=niche_label,
            sample_n=sample_n,
            top_idea_hooks=top_idea_hooks,
        )

    try:
        from google.genai import types

        from getviews_pipeline.config import GEMINI_KNOWLEDGE_FALLBACKS, GEMINI_KNOWLEDGE_MODEL
        from getviews_pipeline.gemini import (
            _generate_content_models,
            _normalize_response,
            _response_text,
        )

        # Numbered list so Gemini can key its per-rank copy back to the
        # right entry — critical for the hook_lines structured output.
        numbered_hooks = "\n".join(
            f"  {i + 1}. {h}" for i, h in enumerate(top_idea_hooks[:5])
        ) or "  (chưa đủ dữ liệu xếp hạng)"
        n_hooks = min(len(top_idea_hooks), 5)
        prompt = f"""Bạn là trợ lý kịch bản TikTok cho creator Việt Nam. Nhiệm vụ: TRẢ LỜI câu hỏi của người dùng bằng bộ ý tưởng đã xếp hạng, không tóm tắt chung.

Trả về DUY NHẤT một JSON object (không markdown) với các khóa:
- lead: string ≤260 ký tự — MỞ ĐẦU bằng câu trả lời trực tiếp cho câu hỏi; trích 1–2 ý tưởng đầu danh sách; kết bằng lý do phù hợp.
- related_questions: đúng 3 string ≤120 ký tự — follow-up liên tiếp câu hỏi hiện tại (đào sâu vào ý tưởng cụ thể, hỏi biến thể hook, hoặc hỏi về shot list).
- hook_lines: list gồm {n_hooks} object, mỗi object có `rank` (1..{n_hooks}), `opening_line` (6–12 từ — CÂU NÓI ĐẦU TIÊN creator sẽ nói trên camera, tiếng Việt tự nhiên, phải KHÁC NHAU giữa các rank), `content_angle` (≤120 ký tự — GÓC NHÌN / nội dung cụ thể của video đó).

Ngách: {niche_label}
Câu hỏi người dùng: "{query_clean}"
Top ý tưởng (đã xếp hạng):
{numbered_hooks}
Mẫu: {sample_n} video thắng trong ngách, tuần qua.

Quy tắc:
- Tiếng Việt tự nhiên, không emoji, không mở đầu "Chào bạn" / "Tuyệt vời" / "Wow".
- Không dùng từ "chắc chắn", "hiệu quả", "bùng nổ", "bí mật", "công thức vàng".
- Không bịa thêm ý tưởng ngoài danh sách trên.
- `opening_line` phải đọc được tự nhiên khi creator nói trên camera — TRÁNH các mẫu chung chung như "Hôm nay mình kể" mà ĐỀ XUẤT câu mở cụ thể gắn với pattern của rank đó.
- `hook_lines` phải có đủ {n_hooks} entry theo đúng thứ tự rank 1..{n_hooks}.
"""
        cfg = types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=512,
            response_mime_type="application/json",
            response_json_schema=IdeasNarrativeLLM.model_json_schema(),
        )
        resp = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        raw = _response_text(resp)
        try:
            data = IdeasNarrativeLLM.model_validate_json(_normalize_response(raw))
        except ValidationError as exc:
            logger.warning("[ideas] Gemini narrative schema mismatch: %s — fallback", exc)
            return _fallback(
                query=query_clean,
                niche_label=niche_label,
                sample_n=sample_n,
                top_idea_hooks=top_idea_hooks,
            )

        lead = (data.lead or "").strip()[:260]
        rq = [s.strip()[:120] for s in data.related_questions if s and s.strip()][:3]
        while len(rq) < 3:
            rq.append(_fallback_related_at(len(rq), niche_label, top_idea_hooks))

        # 2026-05-10 — validate + dedup hook_lines via the standalone
        # normalize_hook_lines helper (testable in isolation).
        hook_lines = normalize_hook_lines(data.hook_lines)

        return {
            "lead": lead or _fallback_lead(
                query=query_clean, niche_label=niche_label, sample_n=sample_n,
                top_idea_hooks=top_idea_hooks,
            ),
            "related_questions": rq,
            "hook_lines": hook_lines,
        }
    except Exception as exc:
        logger.warning("[ideas] Gemini narrative failed: %s — fallback", exc)
        return _fallback(
            query=query_clean,
            niche_label=niche_label,
            sample_n=sample_n,
            top_idea_hooks=top_idea_hooks,
        )


def _fallback(
    *,
    query: str,
    niche_label: str,
    sample_n: int,
    top_idea_hooks: list[str],
) -> dict[str, Any]:
    return {
        "lead": _fallback_lead(
            query=query, niche_label=niche_label, sample_n=sample_n,
            top_idea_hooks=top_idea_hooks,
        ),
        "related_questions": [
            _fallback_related_at(0, niche_label, top_idea_hooks),
            _fallback_related_at(1, niche_label, top_idea_hooks),
            _fallback_related_at(2, niche_label, top_idea_hooks),
        ],
        # Empty list — caller falls back to the deterministic templates
        # already populated by compute_ideas_blocks on each IdeaBlockPayload.
        "hook_lines": [],
    }


def _fallback_lead(
    *, query: str, niche_label: str, sample_n: int, top_idea_hooks: list[str]
) -> str:
    head = top_idea_hooks[0] if top_idea_hooks else ""
    if query:
        base = (
            f"Theo câu hỏi «{query[:80]}»: dựa trên {sample_n} video thắng trong "
            f"ngách {niche_label}, top ý tưởng nên thử trước là «{head}»"
            if head
            else f"Theo câu hỏi «{query[:80]}», chưa đủ ý tưởng ranking cho ngách {niche_label}."
        )
    else:
        base = (
            f"Dựa trên {sample_n} video thắng trong ngách {niche_label} tuần này, "
            f"đây là 5 kịch bản đang giữ retention cao nhất."
        )
    return base[:260]


def _fallback_related_at(
    idx: int, niche_label: str, top_idea_hooks: list[str]
) -> str:
    head = top_idea_hooks[0] if top_idea_hooks else "ý tưởng #1"
    options = [
        f"Biến thể hook nào cho «{head}» ({niche_label})?",
        "Shot list nào phù hợp cho kênh < 10K?",
        f"Ý tưởng nào đang suy yếu trong {niche_label}?",
    ]
    return options[idx % len(options)][:120]
