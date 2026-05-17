"""Narrative synthesis service (Phase 3.5 dedup).

Phase 1.1: thin re-export from gemini.py so callers can migrate to
services.synthesis without a code change on their end.

Phase 3.5 (dedup): _synthesize_core extracts the common Gemini call +
fabrication-guard pattern shared by both video and carousel synthesis.
synthesize_diagnosis_carousel_v2 becomes a thin variant that calls
_synthesize_core with the carousel-specific prompt.

Phase 3.7.2: DiagnosisSynthesisInput Pydantic model will gate the hybrid
JSON/natural-language prompt contract here.
"""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.gemini import (  # noqa: F401
    synthesize_diagnosis_carousel_v2,
    synthesize_diagnosis_v2,
)

logger = logging.getLogger(__name__)

__all__ = [
    "synthesize_diagnosis_v2",
    "synthesize_diagnosis_carousel_v2",
    "synthesize_core",
]


def synthesize_core(
    prompt: str,
    *,
    call_site: str,
    max_output_tokens: int = 3500,
    temperature: float | None = None,
    parse_json_prefix: bool = False,
) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]] | None]:
    """Shared synthesis primitive — Gemini call + fabrication guard.

    Both ``synthesize_diagnosis_v2`` (video) and
    ``synthesize_diagnosis_carousel_v2`` (carousel) share this inner loop.
    The caller is responsible for building the prompt; this function handles:
      1. _generate_content_models (primary → fallback chain, cost log, OTel span)
      2. scan_synthesis_for_fabricated_metrics guard
      3. Optional leading-JSON extraction (narrative_vi / format_cards)

    Returns:
      (body_text, narrative_vi_or_None, format_cards_or_None)
    When ``parse_json_prefix=False``, the second and third elements are always None.
    """
    from google.genai import types

    from getviews_pipeline import telemetry
    from getviews_pipeline.gemini import (
        GEMINI_DIAGNOSIS_MODEL,
        GEMINI_SYNTHESIS_FALLBACKS,
        GEMINI_SYNTHESIS_MODEL,
        GEMINI_TEMPERATURE,
        _generate_content_models,
        _normalize_narrative_vi_dict,
        _response_text,
        _split_diagnosis_leading_json,
        _validate_narrative_citations,
    )

    model = GEMINI_DIAGNOSIS_MODEL or GEMINI_SYNTHESIS_MODEL
    cfg = types.GenerateContentConfig(
        temperature=temperature if temperature is not None else GEMINI_TEMPERATURE,
        max_output_tokens=max_output_tokens,
    )

    with telemetry.span(f"synthesis.{call_site}", call_site=call_site):
        response = _generate_content_models(
            [prompt],
            primary_model=model,
            fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
            config=cfg,
            call_site=call_site,
        )

    text = _response_text(response)
    if not text.strip():
        raise ValueError(f"{call_site} returned empty response")

    # Fabrication guard — non-fatal, logs only
    try:
        from getviews_pipeline.analysis_guards import scan_synthesis_for_fabricated_metrics

        scan = scan_synthesis_for_fabricated_metrics(text)
        if not scan.clean:
            logger.warning(
                "[synthesis_guard] possible fabricated metric(s) in %s: %s",
                call_site,
                scan.flags,
            )
    except Exception as exc:
        logger.warning("[synthesis_guard] scan failed in %s: %s", call_site, exc)

    if not parse_json_prefix:
        return text.strip(), None, None

    raw_obj, remainder = _split_diagnosis_leading_json(text)
    narrative_vi: dict[str, Any] | None = None
    format_cards: list[dict[str, Any]] | None = None
    if raw_obj:
        nv = raw_obj.get("narrative_vi")
        fc = raw_obj.get("format_cards")
        narrative_vi = nv if isinstance(nv, dict) else None
        format_cards = fc if isinstance(fc, list) else None
        # Validate aweme_id citations — only allow ids from the reference set
        # (done inside _validate_narrative_citations in gemini.py)
        narrative_vi, format_cards = _validate_narrative_citations(
            narrative_vi, format_cards, set()  # caller should pass allowed ids
        )
        narrative_vi = _normalize_narrative_vi_dict(narrative_vi)
    body = remainder.strip()
    return body, narrative_vi, format_cards
