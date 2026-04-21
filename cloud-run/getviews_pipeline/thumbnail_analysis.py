"""Thumbnail / frame-0 analysis — Gemini image understanding.

One focused call on the t=0 frame URL (R2-hosted for corpus videos). Uses
the extraction-tier Gemini model + structured JSON output enforced by
ThumbnailAnalysis.model_json_schema(). Fails open — on any error the
helper returns None and the caller renders nothing instead of erroring.

Design: artifacts/docs/features/thumbnail-analysis.md
Pydantic model: getviews_pipeline.models.ThumbnailAnalysis
Prompt: getviews_pipeline.prompts.THUMBNAIL_PROMPT
Cache:  getviews_pipeline.thumbnail_analysis_cache.resolve_thumbnail_analysis
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _truncate_text(s: str | None, limit: int) -> str | None:
    if s is None:
        return None
    cleaned = s.strip()
    if not cleaned:
        return None
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 1].rstrip() + "…"
    return cleaned


def analyze_thumbnail(frame_url: str) -> dict[str, Any] | None:
    """Run the thumbnail Gemini call for a single frame URL.

    Sync wrapper — callers should invoke via runtime.run_sync so they don't
    block the FastAPI event loop. Returns the validated dict ready to store
    in video_corpus.thumbnail_analysis, or None on any error.
    """
    if not frame_url or not isinstance(frame_url, str):
        return None

    # Local imports keep this module light when pipelines import it just for
    # type hints — the Gemini SDK + models load on first actual call.
    try:
        from google.genai import types  # type: ignore
    except Exception as exc:
        logger.warning("[thumbnail_analysis] google.genai unavailable: %s", exc)
        return None

    from getviews_pipeline.config import (
        GEMINI_EXTRACTION_FALLBACKS,
        GEMINI_EXTRACTION_MODEL,
        GEMINI_EXTRACTION_TEMPERATURE,
    )
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _parse_json_object,
        _response_text,
    )
    from getviews_pipeline.models import ThumbnailAnalysis
    from getviews_pipeline.prompts import THUMBNAIL_PROMPT

    try:
        image_part = types.Part.from_uri(file_uri=frame_url, mime_type="image/jpeg")
        cfg = types.GenerateContentConfig(
            temperature=GEMINI_EXTRACTION_TEMPERATURE,
            max_output_tokens=512,
            response_mime_type="application/json",
            response_json_schema=ThumbnailAnalysis.model_json_schema(),
        )
        response = _generate_content_models(
            [image_part, THUMBNAIL_PROMPT],
            primary_model=GEMINI_EXTRACTION_MODEL,
            fallbacks=GEMINI_EXTRACTION_FALLBACKS,
            config=cfg,
        )
        text = _response_text(response)
        if not text.strip():
            logger.warning("[thumbnail_analysis] empty Gemini response for %s", frame_url)
            return None
        parsed = _parse_json_object(text)
    except Exception as exc:
        logger.warning("[thumbnail_analysis] Gemini call failed for %s: %s", frame_url, exc)
        return None

    try:
        validated = ThumbnailAnalysis.model_validate(parsed)
    except Exception as exc:
        logger.warning("[thumbnail_analysis] schema validation failed: %s", exc)
        return None

    # Post-validate client-side — schema doesn't enforce char limits.
    out = validated.model_dump()
    out["text_on_thumbnail"] = _truncate_text(out.get("text_on_thumbnail"), limit=40)
    out["why_it_stops"] = (
        _truncate_text(out.get("why_it_stops"), limit=120)
        or "Không đủ tín hiệu dừng scroll — mặt không rõ, contrast thấp."
    )
    return out


__all__ = ["analyze_thumbnail"]
