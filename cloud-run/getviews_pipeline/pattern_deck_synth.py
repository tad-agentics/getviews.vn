"""Pattern deck synthesizer — Gemini-backed full-deck content for video_patterns.

Produces the four content fields the design's PatternModal renders
(``screens/trends.jsx`` lines 652-946) for each active pattern in
``video_patterns``: ``structure``, ``why``, ``careful``, ``angles``.

Pipeline:
  1. ``_fetch_pattern_grounding`` — pull the pattern row + up to 12 of
     its corpus videos with hook_phrase + hook_type + views.
  2. ``_call_pattern_gemini`` — single Gemini call (response_json_schema
     enforced via Pydantic). Cheap model — flash-lite tier — since the
     output is pure text composition off a small grounding context.
  3. ``upsert_deck`` — persist back to ``video_patterns`` + stamp
     ``deck_computed_at``.

Stale-row policy: ``run_pattern_decks_batch`` walks active patterns
ordered by ``deck_computed_at NULLS FIRST`` (uses the partial index
added in migration ``20260530000000_video_patterns_deck_columns.sql``)
so the orchestrator naturally pays for un-decked rows first, then
the oldest. ``DECK_STALE_AFTER`` sets the regenerate window.

Sync per-pattern by design — orchestrator iterates one at a time so
a single failure doesn't poison the batch + so we can stop early
when the per-batch cap fires.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Decks regenerate when older than this — same 7-day cadence as
# channel_formulas (``CHANNEL_FORMULA_STALE_AFTER`` in
# channel_analyze.py). Tracking aligns the editorial freshness story.
DECK_STALE_AFTER = timedelta(days=7)

# Per-batch synth cap — keeps the nightly Gemini bill predictable.
# A 60-row cap × ~50K context tokens × flash-lite ≈ pennies per run.
# Bump if the corpus grows past ~400 active patterns and decks lag.
DEFAULT_BATCH_CAP = 60

# Min corpus videos a pattern must have for the synthesizer to run.
# Below this, the deck would be guessing — better to leave fields null.
MIN_GROUNDING_VIDEOS = 3

# Cap how many corpus videos we send to Gemini per pattern. The
# prompt grows with this; 12 is plenty to characterize a pattern
# without ballooning context.
GROUNDING_CAP = 12


# ── Pydantic schema enforced via response_json_schema ────────────────────


class PatternDeckAngleLLM(BaseModel):
    """A content angle creators have used (or could use) inside this pattern."""

    angle: str = Field(
        max_length=120,
        description=(
            "Vietnamese phrase, ≤ 80 characters, naming a concrete content "
            "angle inside this pattern (e.g. 'Sản phẩm Apple', 'AI tools', "
            "'Setup làm việc'). Avoid clichés."
        ),
    )
    filled: int = Field(
        ge=0, le=200,
        description=(
            "Approximate count of corpus videos using this angle, derived "
            "from the grounding sample. Use 0 when no creator has covered it."
        ),
    )
    gap: bool = Field(
        default=False,
        description=(
            "True when no creator in the grounding sample has covered this "
            "angle (filled = 0). Marks high-signal opportunities."
        ),
    )


class PatternDeckLLM(BaseModel):
    """Gemini-emitted deck content for a single ``video_patterns`` row."""

    structure: list[str] = Field(
        min_length=4, max_length=4,
        description=(
            "Exactly 4 lines describing Hook / Setup / Body / Payoff with "
            "approximate timing. Each line ≤ 120 chars, Vietnamese, plain "
            "language. Example: 'Mở: câu hỏi \"tôi đã dùng X trong N "
            "tháng\" (0-2s)'."
        ),
    )
    why: str = Field(
        min_length=40, max_length=320,
        description=(
            "1-2 Vietnamese sentences explaining WHY this pattern works "
            "(audience psychology + algorithm signal). Specific, not "
            "generic. ≤ 320 chars."
        ),
    )
    careful: str = Field(
        min_length=20, max_length=240,
        description=(
            "1 Vietnamese sentence warning about pitfalls / over-use / "
            "authenticity drop-off when remixing this pattern. ≤ 240 chars."
        ),
    )
    angles: list[PatternDeckAngleLLM] = Field(
        min_length=4, max_length=8,
        description=(
            "4-8 content angles inside this pattern. Mix filled (creators "
            "have done it, ``gap=false``) with at least 1 ``gap=true`` "
            "angle nobody has covered yet."
        ),
    )


# ── Result shape for the orchestrator + tests ────────────────────────────


@dataclass
class PatternDeckResult:
    pattern_id: str
    deck: dict[str, Any] | None
    error: str | None  # None on success; "thin_corpus" / "schema_error" / "gemini_error" / "..."


@dataclass
class PatternDeckBatchSummary:
    generated:        int = 0
    skipped_thin:     int = 0
    skipped_fresh:    int = 0  # deck_computed_at within DECK_STALE_AFTER
    failed_schema:    int = 0
    failed_gemini:    int = 0
    failed_upsert:    int = 0
    considered:       int = 0  # patterns the orchestrator looked at this run


# ── Data fetch ────────────────────────────────────────────────────────────


def _fetch_pattern_row(client: Any, pattern_id: str) -> dict[str, Any] | None:
    try:
        res = (
            client.table("video_patterns")
            .select("id, display_name, niche_spread, deck_computed_at")
            .eq("id", pattern_id)
            .single()
            .execute()
        )
        return res.data or None
    except Exception as exc:
        logger.warning("[pattern_deck_synth] pattern fetch failed id=%s: %s", pattern_id, exc)
        return None


def _fetch_pattern_grounding(client: Any, pattern_id: str) -> list[dict[str, Any]]:
    """Top corpus videos tagged with this pattern (by views)."""
    try:
        res = (
            client.table("video_corpus")
            .select("video_id, creator_handle, views, hook_phrase, hook_type")
            .eq("pattern_id", pattern_id)
            .order("views", desc=True)
            .limit(GROUNDING_CAP)
            .execute()
        )
        return list(res.data or [])
    except Exception as exc:
        logger.warning("[pattern_deck_synth] grounding fetch failed id=%s: %s", pattern_id, exc)
        return []


def _resolve_niche_label(client: Any, niche_id: int | None) -> str:
    """Best-effort niche-label lookup so the prompt names the niche
    naturally (``"Tech"`` not ``"niche_4"``)."""
    if niche_id is None:
        return "ngách của bạn"
    try:
        res = (
            client.table("niche_taxonomy")
            .select("name_vn, name_en")
            .eq("id", int(niche_id))
            .single()
            .execute()
        )
        row = res.data or {}
        return str(row.get("name_vn") or row.get("name_en") or f"niche_{niche_id}")
    except Exception:
        return f"niche_{niche_id}"


# ── Gemini call ──────────────────────────────────────────────────────────


_PROMPT_TEMPLATE = """Bạn là biên tập TikTok tiếng Việt. Cho một PATTERN nội dung trong ngách "{niche_name}", hãy tổng hợp một bộ "deck" để creator hiểu nhanh và remix được.

PATTERN: {pattern_name}

Grounding (top {n} video thực tế tagged với pattern này, sắp theo view):
{grounding_json}

Trả về JSON theo schema:

- structure: ĐÚNG 4 chuỗi, mỗi chuỗi mô tả 1 đoạn của video pattern này (Hook / Setup / Body / Payoff) kèm khung giây gợi ý. Tiếng Việt, ngắn gọn, cụ thể.
  Ví dụ:
    "Mở: câu hỏi 'tôi đã dùng X trong N tháng' (0-2s)"
    "Setup: thử thách ban đầu / sự nghi ngờ (2-8s)"

- why: 1-2 câu tiếng Việt giải thích VÌ SAO pattern này hiệu quả — gắn với hành vi audience hoặc thuật toán. Cụ thể, ≤ 320 ký tự. Ví dụ: "Format thử-thách-thời-gian tạo curiosity. Audience muốn biết kết quả cuối — tỉ lệ xem hết cao, save cũng cao vì giống testimonial."

- careful: 1 câu cảnh báo ngắn (≤ 240 ký tự) về cách creator có thể "đập đầu" khi áp pattern (sao chép cứng, mất authenticity, dropout, etc.). Ví dụ: "Nếu chưa thực sự dùng X tháng, đừng giả. TikTok đẩy mạnh signal authenticity drop-off — comment sẽ phát hiện."

- angles: 4-8 góc nội dung CỤ THỂ trong pattern này. Mỗi góc:
  • angle: cụm danh từ tiếng Việt ≤ 80 ký tự, đặc trưng cho ngách (vd "Sản phẩm Apple", "AI tools", "Setup làm việc").
  • filled: số nguyên ≈ số video trong grounding dùng góc này. 0 = chưa creator nào.
  • gap: true nếu filled = 0 (cơ hội còn trống); false ngược lại.
  PHẢI có ít nhất 1 góc với gap=true (cơ hội chưa khai thác).

NGUYÊN TẮC:
- Văn phong tự nhiên tiếng Việt. KHÔNG dùng "bí mật", "công thức vàng", "triệu view", "đột phá".
- Số liệu cụ thể, không hứa hẹn "sẽ viral".
- Nếu grounding mỏng, chấp nhận angle đơn giản — đừng bịa thông tin.
"""


def _build_prompt(pattern_name: str, niche_name: str, videos: list[dict[str, Any]]) -> str:
    trimmed = [
        {
            "video_id":   v.get("video_id"),
            "creator":    v.get("creator_handle"),
            "views":      v.get("views"),
            "hook_type":  v.get("hook_type"),
            "hook_phrase": (str(v.get("hook_phrase") or ""))[:160],
        }
        for v in videos[:GROUNDING_CAP]
    ]
    return _PROMPT_TEMPLATE.format(
        niche_name=niche_name,
        pattern_name=pattern_name or "(chưa có tên)",
        n=len(trimmed),
        grounding_json=json.dumps(trimmed, ensure_ascii=False, indent=2),
    )


def _call_pattern_gemini(prompt: str) -> PatternDeckLLM:
    """Single Gemini call enforced by Pydantic schema. Raises on failure."""
    from google.genai import types  # type: ignore[import-untyped]

    from getviews_pipeline.config import (
        GEMINI_SYNTHESIS_FALLBACKS, GEMINI_SYNTHESIS_MODEL,
    )
    from getviews_pipeline.gemini import (
        _generate_content_models, _normalize_response, _response_text,
    )

    config = types.GenerateContentConfig(
        temperature=0.4,
        response_mime_type="application/json",
        response_json_schema=PatternDeckLLM.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return PatternDeckLLM.model_validate_json(_normalize_response(raw))


# ── Single-pattern synth + persist ───────────────────────────────────────


def synthesize_pattern_deck(
    user_sb: Any,
    pattern_id: str,
) -> PatternDeckResult:
    """Run the full synth pipeline for one pattern. No DB write here —
    callers (``upsert_deck``, the batch orchestrator) decide.

    ``user_sb`` is the read client used for grounding fetches; the
    orchestrator passes its service client for both reads and writes.
    """
    pattern = _fetch_pattern_row(user_sb, pattern_id)
    if not pattern:
        return PatternDeckResult(pattern_id=pattern_id, deck=None, error="pattern_not_found")

    videos = _fetch_pattern_grounding(user_sb, pattern_id)
    if len(videos) < MIN_GROUNDING_VIDEOS:
        return PatternDeckResult(
            pattern_id=pattern_id,
            deck=None,
            error=f"thin_corpus:{len(videos)}",
        )

    niche_spread = list(pattern.get("niche_spread") or [])
    primary_niche = int(niche_spread[0]) if niche_spread else None
    niche_name = _resolve_niche_label(user_sb, primary_niche)

    prompt = _build_prompt(
        pattern_name=str(pattern.get("display_name") or ""),
        niche_name=niche_name,
        videos=videos,
    )

    try:
        llm = _call_pattern_gemini(prompt)
    except Exception as exc:
        # ValidationError (Pydantic schema) vs network/quota — log a hint.
        kind = type(exc).__name__
        logger.warning(
            "[pattern_deck_synth] gemini failed id=%s kind=%s: %s",
            pattern_id, kind, exc,
        )
        if "Validation" in kind or "ValidationError" in kind:
            return PatternDeckResult(pattern_id=pattern_id, deck=None, error="schema_error")
        return PatternDeckResult(pattern_id=pattern_id, deck=None, error="gemini_error")

    deck = {
        "structure": list(llm.structure),
        "why":       llm.why.strip(),
        "careful":   llm.careful.strip(),
        "angles":    [a.model_dump() for a in llm.angles],
    }
    return PatternDeckResult(pattern_id=pattern_id, deck=deck, error=None)


def upsert_deck(client: Any, result: PatternDeckResult) -> bool:
    """Write a successful deck to ``video_patterns``. No-op on errors."""
    if result.error or result.deck is None:
        return False
    payload = {
        **result.deck,
        "deck_computed_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        (
            client.table("video_patterns")
            .update(payload)
            .eq("id", result.pattern_id)
            .execute()
        )
        return True
    except Exception as exc:
        logger.exception(
            "[pattern_deck_synth] upsert failed id=%s: %s",
            result.pattern_id, exc,
        )
        return False


# ── Batch orchestration ──────────────────────────────────────────────────


def _fetch_stale_pattern_ids(client: Any, *, cap: int) -> list[str]:
    """Active patterns ordered by deck staleness — uses the partial
    index ``video_patterns_deck_stale_idx``. Returns the rows whose
    ``deck_computed_at`` is null OR older than ``DECK_STALE_AFTER``."""
    cutoff = (datetime.now(timezone.utc) - DECK_STALE_AFTER).isoformat()
    try:
        res = (
            client.table("video_patterns")
            .select("id, deck_computed_at")
            .eq("is_active", True)
            .or_(f"deck_computed_at.is.null,deck_computed_at.lt.{cutoff}")
            .order("deck_computed_at", desc=False, nullsfirst=True)
            .limit(cap)
            .execute()
        )
        return [str(r["id"]) for r in (res.data or []) if r.get("id")]
    except Exception as exc:
        logger.exception("[pattern_deck_synth] stale fetch failed: %s", exc)
        return []


def run_pattern_decks_batch(
    client: Any,
    *,
    cap: int = DEFAULT_BATCH_CAP,
    pattern_ids: list[str] | None = None,
) -> PatternDeckBatchSummary:
    """Synthesize decks for the staleest ``cap`` active patterns.

    ``pattern_ids`` overrides the staleness query — useful for
    smoke tests + admin manual reruns.
    """
    summary = PatternDeckBatchSummary()
    ids = pattern_ids or _fetch_stale_pattern_ids(client, cap=cap)
    summary.considered = len(ids)
    if not ids:
        return summary

    for pid in ids:
        result = synthesize_pattern_deck(client, pid)
        if result.error is None and result.deck is not None:
            if upsert_deck(client, result):
                summary.generated += 1
            else:
                summary.failed_upsert += 1
            continue
        err = result.error or ""
        if err.startswith("thin_corpus"):
            summary.skipped_thin += 1
        elif err == "schema_error":
            summary.failed_schema += 1
        elif err == "gemini_error":
            summary.failed_gemini += 1
        # ``pattern_not_found`` is rare (race with delete); not worth
        # its own bucket — don't count toward generated/skipped.
    return summary


__all__ = [
    "DECK_STALE_AFTER",
    "DEFAULT_BATCH_CAP",
    "GROUNDING_CAP",
    "MIN_GROUNDING_VIDEOS",
    "PatternDeckAngleLLM",
    "PatternDeckBatchSummary",
    "PatternDeckLLM",
    "PatternDeckResult",
    "_build_prompt",
    "_fetch_pattern_grounding",
    "_fetch_pattern_row",
    "_fetch_stale_pattern_ids",
    "_resolve_niche_label",
    "run_pattern_decks_batch",
    "synthesize_pattern_deck",
    "upsert_deck",
]
