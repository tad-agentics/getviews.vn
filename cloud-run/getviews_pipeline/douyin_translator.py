"""D2a (2026-06-03) — Chinese → Vietnamese translator for Douyin captions.

The Kho Douyin surface needs every video card + modal to display a
natural Vietnamese title + a short ≤120-char gloss. The Gemini analysis
pipeline (``analysis_core.analyze_aweme``) operates on the video itself
and emits structural fields (hook_type, scenes, etc.) but does NOT
translate the caption — Douyin awemes carry ``desc`` in Chinese.

This module is the seam. One Gemini call per caption returns:

  • ``title_vi`` — natural-Vietnamese rendering of the full caption.
    Drives the ``DouyinVideoModal`` H2. Preserves named entities
    (creators, products, places) verbatim.
  • ``sub_vi`` — ≤120-char trimmed gloss. Drives the
    ``DouyinVideoCard`` "{v.sub}" subtitle band.

Why per-video instead of a batch translate-many call:

  • The D2c ingest orchestrator analyzes videos in parallel via
    ``get_analysis_semaphore`` — wiring translate into the same
    coroutine keeps the dependency graph linear.
  • Per-video calls let us cache by exact ``desc_zh`` (lru_cache); a
    batch call's request-level cache would be wasted on partial hits
    (the same trending caption can repeat across 5+ videos in a niche).

Cost envelope (flash-preview at ~$0.25/M output tokens):
  Each call emits <80 output tokens. 50 videos/day × 80 tokens ≈
  4K tokens/day ≈ $0.001/day — a rounding error against the existing
  Gemini budget.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CaptionTranslation(BaseModel):
    """Pydantic-validated Gemini output."""

    title_vi: str = Field(..., min_length=1, max_length=400)
    sub_vi: str = Field(..., min_length=1, max_length=120)


# ── Public API ──────────────────────────────────────────────────────


def translate_douyin_caption(
    desc_zh: str,
    *,
    creator_handle: str | None = None,
) -> CaptionTranslation | None:
    """Translate one Douyin caption to Vietnamese.

    Returns ``None`` on any failure so the D2c ingest pipeline can land
    the row with empty translation fields (D3 synth can re-grade later)
    instead of failing the whole video.

    ``creator_handle`` is passed in so the prompt can keep the handle
    verbatim — creators are named entities, not to be translated.

    Caching: ``_call_translation_gemini`` is wrapped in ``lru_cache``;
    passing the same ``desc_zh`` twice in one process skips the second
    Gemini call. This is meaningful inside one batch run because trending
    captions repeat across the candidate pool.
    """
    cleaned = (desc_zh or "").strip()
    if not cleaned:
        return None
    pruned = _strip_caption_noise(cleaned)
    if not pruned:
        return None
    try:
        return _call_translation_gemini(pruned, (creator_handle or "").strip())
    except Exception as exc:
        logger.warning(
            "[douyin-translator] failed for %s: %s",
            (creator_handle or "<unknown>"),
            exc,
        )
        return None


# ── Internal helpers ────────────────────────────────────────────────


# @mentions (CJK + ASCII), URLs, and runs of whitespace.
# Hashtags stay inline because they often carry semantic content for
# the translator (e.g. ``#美食探店`` tells Gemini "food exploration");
# the prompt drops them from ``title_vi`` if they don't add meaning.
_CAPTION_NOISE_RE = re.compile(
    r"@[\w一-鿿·.\-_]+|"
    r"https?://\S+|"
    r"\s+",
)


def _strip_caption_noise(text: str) -> str:
    """Drop @mentions + URLs and collapse whitespace."""
    return _CAPTION_NOISE_RE.sub(" ", text).strip()


@lru_cache(maxsize=512)
def _call_translation_gemini(
    desc_zh: str,
    creator_handle: str,
) -> CaptionTranslation:
    """Pydantic-bound Gemini call. Cached per (desc_zh, creator_handle).

    Raises on any failure — public ``translate_douyin_caption`` catches
    and returns None.
    """
    from google.genai import types

    from getviews_pipeline.config import (
        GEMINI_EXTRACTION_FALLBACKS,
        GEMINI_EXTRACTION_MODEL,
        GEMINI_EXTRACTION_TEMPERATURE,
    )
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _response_text,
    )

    handle_line = (
        f"\nHandle creator (giữ nguyên, không dịch): {creator_handle}"
        if creator_handle
        else ""
    )

    prompt = f"""Bạn là dịch giả tiếng Trung sang tiếng Việt cho nội dung TikTok / Douyin.

Caption gốc tiếng Trung:
\"\"\"{desc_zh}\"\"\"
{handle_line}

Trả về JSON với 2 trường:
- ``title_vi``: dịch tự nhiên toàn bộ caption sang tiếng Việt. Giữ nguyên tên người, sản phẩm, địa danh. Bỏ hashtag không cần thiết. ≤ 400 ký tự.
- ``sub_vi``: bản dịch ngắn ≤ 120 ký tự, dùng làm phụ đề thẻ video. Dịch ý chính, không dịch sát từng chữ.

Quy tắc:
- Không thêm "Đây là", "Video về", "Bạn sẽ thấy" — bắt vào nội dung ngay.
- Không dùng từ cấm: "bí mật", "công thức vàng", "triệu view", "bùng nổ".
- Tự nhiên, đời thường, không dịch máy.
"""

    config = types.GenerateContentConfig(
        temperature=GEMINI_EXTRACTION_TEMPERATURE,
        response_mime_type="application/json",
        response_json_schema=CaptionTranslation.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_EXTRACTION_MODEL,
        fallbacks=GEMINI_EXTRACTION_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return CaptionTranslation.model_validate_json(raw)


# ── Test-only hook (lets pytest reset the lru_cache between cases) ──


def _reset_cache_for_tests() -> None:
    _call_translation_gemini.cache_clear()
