"""D3a (2026-06-04) — Kho Douyin · adapt-level + ETA + translator notes synth.

Per-video Gemini call that grades a Douyin video's "bring-to-Vietnam"
difficulty and emits the human-readable callouts the FE
``DouyinVideoModal`` renders. Inputs come from ``douyin_video_corpus``
rows already populated by D2 ingest:

  • title_zh / title_vi (D2a translator filled title_vi)
  • hook_type / hook_phrase (Gemini analysis from D2c)
  • niche label (joined from douyin_niche_taxonomy)

Output (per design pack ``screens/douyin.jsx`` lines 36-44, 130-145):

  • ``adapt_level`` ∈ {green, yellow, red}
      green  = "Dịch thẳng" — universal, no cultural / language friction
      yellow = "Cần đổi bối cảnh" — context swap needed (props, brands,
               place names) but format works
      red    = "Khó dịch" — deeply Chinese-specific (cuisine, tradition,
               regional dialect) — adapting risks losing the original's appeal

  • ``adapt_reason`` — 1-2 Vietnamese sentences explaining the level
  • ``eta_weeks_min`` / ``eta_weeks_max`` — range estimate for when the
    trend is likely to reach VN (green: 1-4 weeks; yellow: 4-10 weeks;
    red: 12+ weeks). Heuristic, not a forecast.
  • ``sub_vi`` — ≤120-char gloss for the FE card subtitle band (may
    overwrite the translator's sub_vi when the synth has more context).
  • ``translator_notes`` — 2-5 ``{tag, note}`` callouts covering
    terminology / context / music / props / format quirks.

This module is the SYNTH side. D3b ships:
  • ``run_douyin_adapt_batch`` orchestrator (fetches stale rows, calls
    this synth, upserts results, refreshes ``synth_computed_at``).
  • ``/batch/douyin-synth`` HTTP endpoint.
  • pg_cron schedule (daily, 1hr after the D2 ingest finishes).

Cost envelope (flash-preview at ~$0.25/M output tokens):
  Each call emits ~400 output tokens. 50 videos/day × 400 ≈ 20K
  tokens/day ≈ $0.005/day — same order of magnitude as the D2a
  translator. Batch synthesis is bounded by the D1 cap.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


# ── Pydantic schema (enforced by Gemini's response_json_schema) ─────


AdaptLevel = Literal["green", "yellow", "red"]

TranslatorNoteTag = Literal[
    # Mirrors design pack tags exactly so FE can colour-code without a map.
    "TỪ NGỮ",      # terminology / vocabulary swap
    "BỐI CẢNH",    # context / setting (CN supermarket → VN supermarket)
    "NHẠC NỀN",    # background music + copyright path
    "ĐẠO CỤ",      # props / equipment
    "KHÔNG LỜI",   # silent format note (no translation needed)
    "TITLE",       # title-specific note (literal vs. natural rendering)
]


class TranslatorNote(BaseModel):
    """One ``{tag, note}`` callout. Drives the FE modal's NOTE VĂN HOÁ
    section (one card per note, tag pill on the left)."""

    tag: TranslatorNoteTag
    note: str = Field(
        ..., min_length=12, max_length=240,
        description=(
            "Vietnamese cultural / craft note (≤ 240 chars). Be specific: "
            "name the actual brand / dish / ritual when relevant. Avoid "
            "generic 'có thể adapt'-style filler."
        ),
    )


class DouyinAdaptSynth(BaseModel):
    """Gemini-emitted adapt grade for one Douyin video."""

    adapt_level: AdaptLevel = Field(
        ...,
        description=(
            "green = dịch thẳng (universal, no friction); "
            "yellow = cần đổi bối cảnh (context swap needed); "
            "red = khó dịch (deeply CN-specific, risks losing appeal)."
        ),
    )
    adapt_reason: str = Field(
        ..., min_length=20, max_length=200,
        description=(
            "1-2 Vietnamese sentences explaining the level. Specific, not "
            "generic. ≤ 200 chars. e.g. 'Wellness routine ngắn — universal, "
            "đã có 2 creator VN test thành công.'"
        ),
    )
    eta_weeks_min: int = Field(
        ..., ge=1, le=52,
        description=(
            "Lower bound of the ETA range to VN, in weeks. Heuristic: "
            "green typically 1-4, yellow 4-10, red 12+."
        ),
    )
    eta_weeks_max: int = Field(
        ..., ge=1, le=52,
        description=(
            "Upper bound of the ETA range. Must be >= eta_weeks_min. "
            "Range cap 12 weeks for red (anything longer the trend may "
            "never travel)."
        ),
    )
    sub_vi: str = Field(
        ..., min_length=8, max_length=120,
        description=(
            "Short ≤120-char Vietnamese gloss for the FE card subtitle "
            "band. Drives ``DouyinVideoCard`` 'sub' field. May overwrite "
            "the D2a translator's sub_vi when the synth has more context."
        ),
    )
    translator_notes: list[TranslatorNote] = Field(
        ..., min_length=2, max_length=5,
        description=(
            "2-5 cultural / craft callouts covering terminology / context / "
            "music / props / format. Each must use a distinct tag when "
            "possible. KHÔNG LỜI is required when the format is silent "
            "(no narration)."
        ),
    )

    @model_validator(mode="after")
    def _check_eta_range_ordered(self) -> "DouyinAdaptSynth":
        if self.eta_weeks_max < self.eta_weeks_min:
            raise ValueError(
                f"eta_weeks_max ({self.eta_weeks_max}) < "
                f"eta_weeks_min ({self.eta_weeks_min})"
            )
        return self


# ── Public API ──────────────────────────────────────────────────────


def synth_douyin_adapt(
    *,
    title_zh: str,
    title_vi: str | None,
    hook_phrase: str | None,
    hook_type: str | None,
    niche_name_vn: str,
    niche_name_zh: str,
    content_format_hints: str | None = None,
) -> DouyinAdaptSynth | None:
    """Grade one Douyin video's adapt-level + emit translator notes.

    Returns ``None`` on any Gemini / Pydantic-validation failure so the
    D3b orchestrator can skip the row (and re-attempt on the next cron
    run via ``synth_computed_at`` staleness).

    Caching: ``_call_synth_gemini`` is wrapped in lru_cache keyed on the
    full prompt-relevant tuple. Trending Douyin captions repeat across
    the candidate pool so the cache is meaningful inside a single batch.
    """
    if not (title_zh or "").strip():
        return None
    try:
        return _call_synth_gemini(
            title_zh=title_zh.strip(),
            title_vi=(title_vi or "").strip(),
            hook_phrase=(hook_phrase or "").strip(),
            hook_type=(hook_type or "").strip(),
            niche_name_vn=niche_name_vn.strip(),
            niche_name_zh=niche_name_zh.strip(),
            content_format_hints=(content_format_hints or "").strip(),
        )
    except Exception as exc:
        logger.warning(
            "[douyin-synth] failed for niche=%s title_zh=%r: %s",
            niche_name_vn,
            title_zh[:60],
            exc,
        )
        return None


# ── Internal: Gemini call ──────────────────────────────────────────


@lru_cache(maxsize=256)
def _call_synth_gemini(
    *,
    title_zh: str,
    title_vi: str,
    hook_phrase: str,
    hook_type: str,
    niche_name_vn: str,
    niche_name_zh: str,
    content_format_hints: str,
) -> DouyinAdaptSynth:
    """Pydantic-bound Gemini call. Cached on every input so repeated
    captions (trending content surfaces in multiple niches) skip the
    network. Raises on any failure — caller catches.
    """
    from google.genai import types  # type: ignore[import-untyped]

    from getviews_pipeline.config import (
        GEMINI_SYNTHESIS_FALLBACKS,
        GEMINI_SYNTHESIS_MODEL,
    )
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _normalize_response,
        _response_text,
    )

    title_vi_line = (
        f"Title đã dịch (VN): {title_vi}" if title_vi else "Title đã dịch (VN): (chưa có)"
    )
    hook_line = (
        f"Hook (Gemini): {hook_phrase} (loại: {hook_type or 'không rõ'})"
        if hook_phrase
        else "Hook (Gemini): (chưa có)"
    )
    format_line = (
        f"Định dạng nội dung: {content_format_hints}"
        if content_format_hints
        else ""
    )

    prompt = f"""Bạn là editor Việt Nam phân tích video TikTok/Douyin Trung Quốc để đánh giá khả năng "đem về" thị trường VN.

Video Douyin:
- Title gốc (CN): {title_zh}
- {title_vi_line}
- {hook_line}
- Ngách: {niche_name_vn} ({niche_name_zh})
{format_line}

Trả về JSON với 6 trường:

1. ``adapt_level``: chọn 1 trong:
   - "green" = dịch thẳng. Format universal (silent unboxing, wellness routine, productivity tip), KHÔNG phụ thuộc văn hoá / ngôn ngữ. Audience VN hiểu ngay.
   - "yellow" = cần đổi bối cảnh. Format ổn nhưng phải swap props / brands / place names sang VN (siêu thị TQ → Aeon/WinMart, đồ ăn TQ → đồ VN tương đương). Cấu trúc giữ nguyên.
   - "red" = khó dịch. Đặc thù văn hoá TQ (lẩu Tứ Xuyên, Tết Trung, hutong Bắc Kinh, dialect-heavy comedy). Adapt thẳng = mất sức hấp dẫn.

2. ``adapt_reason``: 1-2 câu tiếng Việt giải thích vì sao chọn level đó. Cụ thể, không chung chung. ≤ 200 ký tự.

3. ``eta_weeks_min`` + ``eta_weeks_max``: ước lượng range (đơn vị tuần) trend này về VN. Heuristic:
   - green: 1-4 tuần (lan nhanh)
   - yellow: 4-10 tuần (cần creator VN re-shoot)
   - red: 12-52 tuần (hoặc không bao giờ)

4. ``sub_vi``: gloss ngắn ≤ 120 ký tự cho thẻ video. Dịch ý chính, không dịch sát.

5. ``translator_notes``: 2-5 entry ``{{tag, note}}``. Tags hợp lệ:
   - "TỪ NGỮ" — từ vựng / cách diễn đạt khác biệt VN-CN
   - "BỐI CẢNH" — bối cảnh (siêu thị, ẩm thực, văn hoá địa lý)
   - "NHẠC NỀN" — gợi ý nhạc nền VN tương đương + tránh bản quyền
   - "ĐẠO CỤ" — props / sản phẩm / setup phải đổi
   - "KHÔNG LỜI" — BẮT BUỘC khi format silent (không có lời thoại)
   - "TITLE" — note về cách dịch tiêu đề
   Mỗi note ≤ 240 ký tự, cụ thể. Tránh "có thể adapt", "tuỳ creator".

Quy tắc copy:
- Tự nhiên, đời thường. Tránh "bí mật", "công thức vàng", "triệu view", "bùng nổ".
- Không mở bằng "Đây là", "Video về" — bắt vào nội dung ngay.
- Tiếng Việt natural, không dịch máy.
"""

    config = types.GenerateContentConfig(
        temperature=0.4,
        response_mime_type="application/json",
        response_json_schema=DouyinAdaptSynth.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return DouyinAdaptSynth.model_validate_json(_normalize_response(raw))


# ── Test-only hook (lets pytest reset the lru_cache) ────────────────


def _reset_cache_for_tests() -> None:
    _call_synth_gemini.cache_clear()
