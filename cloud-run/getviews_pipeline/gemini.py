"""Google Gemini client: video analysis (inline or Files API) and batch summaries."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from getviews_pipeline.config import (
    FILES_API_POLL_INTERVAL_SEC,
    FILES_API_POLL_MAX_ATTEMPTS,
    GEMINI_DIAGNOSIS_MODEL,
    GEMINI_EXTRACTION_FALLBACKS,
    GEMINI_EXTRACTION_MODEL,
    GEMINI_KNOWLEDGE_FALLBACKS,
    GEMINI_KNOWLEDGE_MODEL,
    GEMINI_EXTRACTION_TEMPERATURE,
    GEMINI_SYNTHESIS_FALLBACKS,
    GEMINI_SYNTHESIS_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_VIDEO_MEDIA_RESOLUTION,
    MAX_INLINE_SIZE_BYTES,
    require_gemini_api_key,
)
from getviews_pipeline.models import BatchSummary, CarouselAnalysis, ContentType, VideoAnalysis
from getviews_pipeline.prompts import (
    CAROUSEL_EXTRACTION_PROMPT,
    VIDEO_EXTRACTION_PROMPT,
    build_diagnosis_prompt,
    build_diagnosis_synthesis_prompt_v2,
    build_knowledge_prompt,
    build_summary_prompt,
    build_synthesis_prompt,
)

logger = logging.getLogger(__name__)

_client: genai.Client | None = None
_client_lock = threading.Lock()


class SummaryInsights(BaseModel):
    top_patterns: list[str]
    content_gaps: list[str]
    recommendations: list[str]
    winning_formula: str | None = None


def _get_client() -> genai.Client:
    global _client
    with _client_lock:
        if _client is None:
            _client = genai.Client(api_key=require_gemini_api_key())
    return _client


_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _normalize_response(raw: str) -> str:
    """Normalize model text before json.loads (SPEC section 12)."""
    s = raw.strip()
    m = _FENCE_RE.search(s)
    if m:
        return m.group(1).strip()
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start : end + 1].strip()
    return s


def _parse_json_object(text: str) -> dict[str, Any]:
    normalized = _normalize_response(text)
    return json.loads(normalized)


def _video_analysis_config() -> types.GenerateContentConfig | None:
    """Lower media_resolution speeds up Gemini video understanding (opt-in via env)."""
    raw = GEMINI_VIDEO_MEDIA_RESOLUTION
    if not raw or raw == "unspecified":
        return None
    mapping = {
        "low": types.MediaResolution.MEDIA_RESOLUTION_LOW,
        "medium": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
        "high": types.MediaResolution.MEDIA_RESOLUTION_HIGH,
    }
    res = mapping.get(raw)
    if res is None:
        logger.warning(
            "Unknown GEMINI_VIDEO_MEDIA_RESOLUTION=%r (use low, medium, high); ignoring",
            raw,
        )
        return None
    return types.GenerateContentConfig(media_resolution=res)


def _extraction_json_config(schema: dict[str, Any]) -> types.GenerateContentConfig | None:
    """§11 Rule 4 — structured JSON for analysis calls.

    Uses GEMINI_EXTRACTION_TEMPERATURE (default 0.2) — low temperature is
    critical for deterministic transcription and scene detection. The synthesis
    temperature (0.8) is intentionally not used here.
    """
    base = _video_analysis_config()
    updates: dict[str, Any] = {
        "temperature": GEMINI_EXTRACTION_TEMPERATURE,
        "response_mime_type": "application/json",
        "response_json_schema": schema,
    }
    if base is not None:
        return base.model_copy(update=updates)
    return types.GenerateContentConfig(**updates)


_RETRY_DELAYS = (1, 2, 4)  # seconds — §13 mandate: 3 retries at 1s/2s/4s


def _is_transient_gemini_error(exc: Exception) -> bool:
    """Return True for 503 / 429 / rate-limit errors that are safe to retry."""
    msg = str(exc).lower()
    return any(kw in msg for kw in ("503", "429", "rate limit", "quota", "overloaded", "resource exhausted"))


def _generate_content_models(
    contents: Any,
    *,
    primary_model: str,
    fallbacks: list[str],
    config: types.GenerateContentConfig | None = None,
) -> Any:
    client = _get_client()
    chain = [primary_model, *fallbacks]
    seen: set[str] = set()
    last_err: Exception | None = None
    for m in chain:
        if not m or m in seen:
            continue
        seen.add(m)
        for attempt, delay in enumerate(_RETRY_DELAYS):
            try:
                kwargs: dict[str, Any] = {"model": m, "contents": contents}
                if config is not None:
                    kwargs["config"] = config
                return client.models.generate_content(**kwargs)
            except Exception as e:
                is_transient = _is_transient_gemini_error(e)
                is_last_attempt = attempt == len(_RETRY_DELAYS) - 1
                if not is_transient or is_last_attempt:
                    last_err = e
                    logger.warning("Gemini model %s attempt %d/%d failed: %s", m, attempt + 1, len(_RETRY_DELAYS), e)
                    break
                logger.info("Gemini model %s transient error (attempt %d/%d), retrying in %ds: %s", m, attempt + 1, len(_RETRY_DELAYS), delay, e)
                time.sleep(delay)
    if last_err:
        raise last_err
    raise RuntimeError("No Gemini models available")


def analyze_video(video_path: Path) -> VideoAnalysis:
    """Run full forensic analysis on a local video file (sync)."""
    path = video_path.resolve()
    size = path.stat().st_size
    json_cfg = _extraction_json_config(VideoAnalysis.model_json_schema())

    if size <= MAX_INLINE_SIZE_BYTES:
        data = path.read_bytes()
        video_part = types.Part.from_bytes(data=data, mime_type="video/mp4")
        response = _generate_content_models(
            [video_part, VIDEO_EXTRACTION_PROMPT],
            primary_model=GEMINI_EXTRACTION_MODEL,
            fallbacks=GEMINI_EXTRACTION_FALLBACKS,
            config=json_cfg,
        )
    else:
        client = _get_client()
        uploaded = client.files.upload(file=str(path))
        name = uploaded.name
        try:
            info = uploaded
            for _ in range(FILES_API_POLL_MAX_ATTEMPTS):
                info = client.files.get(name=name)
                state = getattr(info.state, "name", None) or str(info.state)
                if state == "ACTIVE":
                    break
                if state == "FAILED":
                    raise RuntimeError(f"Gemini file processing failed: {name}")
                time.sleep(FILES_API_POLL_INTERVAL_SEC)
            else:
                raise TimeoutError("Gemini file never became ACTIVE within 60 seconds")

            response = _generate_content_models(
                [info, VIDEO_EXTRACTION_PROMPT],
                primary_model=GEMINI_EXTRACTION_MODEL,
                fallbacks=GEMINI_EXTRACTION_FALLBACKS,
                config=json_cfg,
            )
        finally:
            try:
                client.files.delete(name=name)
            except Exception:
                pass

    text = _response_text(response)
    if not text.strip():
        raise ValueError("Gemini returned empty response text")
    parsed = _parse_json_object(text)
    return VideoAnalysis.model_validate(parsed)


def _carousel_index_mapping_block(source_indices: list[int]) -> str:
    lines = [
        "SLIDE INDEX MAPPING (mandatory — 0-based positions within the **extracted** slide batch; "
        "use these exact integers in each `slides[].index`, in **image part order**):",
        *[
            f"- Image part {k + 1} → `slides` entry **index** = {j}"
            for k, j in enumerate(source_indices)
        ],
        "If any batch positions failed CDN download they are omitted here; `slides[].index` may "
        "therefore have gaps (e.g. 0, 1, 4) — that is correct.",
    ]
    return "\n".join(lines)


def _normalize_carousel_slide_indices(
    analysis: CarouselAnalysis,
    source_indices: list[int],
) -> CarouselAnalysis:
    """Force ``slides[].index`` to match ground-truth batch positions (image part order)."""
    if len(analysis.slides) != len(source_indices):
        return analysis
    new_slides = [
        s.model_copy(update={"index": idx})
        for s, idx in zip(analysis.slides, source_indices, strict=True)
    ]
    return analysis.model_copy(update={"slides": new_slides})


def analyze_carousel(
    slides: list[tuple[bytes, str]],
    supplemental_prompt: str = "",
    source_indices: list[int] | None = None,
) -> CarouselAnalysis:
    """Analyze carousel: one `generate_content` with image Parts then the text prompt.

    ``source_indices`` lists the 0-based extracted-batch index for each image part
    (same length as ``slides``). When downloads skip slides, indices may be non-consecutive.
    """
    if not slides:
        raise ValueError("Carousel analysis requires at least one image")

    indices = source_indices if source_indices is not None else list(range(len(slides)))
    if len(indices) != len(slides):
        raise ValueError("source_indices length must match number of slide images")

    mapping = _carousel_index_mapping_block(indices)
    tail = f"\n\n{mapping}"
    if supplemental_prompt.strip():
        tail += f"\n\n{supplemental_prompt.strip()}"

    json_cfg = _extraction_json_config(CarouselAnalysis.model_json_schema())
    parts: list[Any] = [
        *[types.Part.from_bytes(data=data, mime_type=mime) for data, mime in slides],
        CAROUSEL_EXTRACTION_PROMPT + tail,
    ]

    response = _generate_content_models(
        parts,
        primary_model=GEMINI_EXTRACTION_MODEL,
        fallbacks=GEMINI_EXTRACTION_FALLBACKS,
        config=json_cfg,
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("Gemini returned empty response text")
    parsed = _parse_json_object(text)
    analysis = CarouselAnalysis.model_validate(parsed)
    return _normalize_carousel_slide_indices(analysis, indices)


def synthesize_diagnosis(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
    content_type: ContentType = "video",
) -> str:
    """Strategist markdown: routes to video vs carousel diagnosis prompt."""
    model = GEMINI_DIAGNOSIS_MODEL or GEMINI_SYNTHESIS_MODEL
    prompt = build_diagnosis_prompt(analysis, metadata, content_type)
    cfg = types.GenerateContentConfig(temperature=GEMINI_TEMPERATURE, max_output_tokens=4096)
    response = _generate_content_models(
        [prompt],
        primary_model=model,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("Gemini returned empty synthesis response")
    return text.strip()


def synthesize_diagnosis_v2(
    content_format: str,
    niche_name: str,
    corpus_size: int,
    niche_norms: dict[str, Any],
    reference_videos: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    collapsed_questions: list[str] | None = None,
) -> str:
    """V2 narrative diagnosis — format-aware, 4-part structure.

    Uses build_diagnosis_synthesis_prompt_v2() from prompts.py.
    max_output_tokens bumped to 3072 to accommodate full 4-part narrative.
    """
    model = GEMINI_DIAGNOSIS_MODEL or GEMINI_SYNTHESIS_MODEL
    prompt = build_diagnosis_synthesis_prompt_v2(
        content_format=content_format,
        niche_name=niche_name,
        corpus_size=corpus_size,
        niche_norms=niche_norms,
        reference_videos=reference_videos,
        user_analysis=user_analysis,
        user_stats=user_stats,
    )
    if collapsed_questions:
        question_block = (
            "\n\nNgười dùng hỏi nhiều câu; thêm mục có tiêu đề rõ cho từng câu:\n"
            + "\n".join(f"- {q}" for q in collapsed_questions)
        )
        prompt = prompt.rstrip() + question_block + "\n\nViết chẩn đoán ngay."

    cfg = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=3072,  # narrative structure needs more room than old checklist
    )
    response = _generate_content_models(
        [prompt],
        primary_model=model,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("synthesize_diagnosis_v2 returned empty response")
    return text.strip()


def _response_text(response: Any) -> str:
    t0 = getattr(response, "text", None)
    if t0 is not None:
        return str(t0)
    parts: list[str] = []
    c = getattr(response, "candidates", None) or []
    if not c:
        return ""
    for cand in c:
        content = getattr(cand, "content", None)
        if content is None:
            continue
        for p in getattr(content, "parts", None) or []:
            t = getattr(p, "text", None)
            if t:
                parts.append(str(t))
    return "".join(parts)


def gemini_text_only(message: str, session_context: dict[str, Any]) -> str:
    """§3a Rule A / FOLLOWUP — knowledge or session-grounded text."""
    prompt = build_knowledge_prompt(message, session_context)
    cfg = types.GenerateContentConfig(temperature=GEMINI_TEMPERATURE, max_output_tokens=1024)
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_KNOWLEDGE_MODEL,
        fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
        config=cfg,
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("gemini_text_only returned empty response")
    return text.strip()


def synthesize_intent_markdown(
    intent_key: str,
    payload: dict[str, Any],
    *,
    collapsed_questions: list[str] | None = None,
    niche_key: str | None = None,
    corpus_citation: str = "",
) -> str:
    """Multi-video / niche synthesis using §18 intent framing.

    Args:
        niche_key:        Optional niche identifier passed through to build_synthesis_prompt
                          so knowledge_base niche guidance is injected (brief_generation,
                          video_diagnosis intents).
        corpus_citation:  Optional pre-built citation block from corpus_context.py
                          (build_corpus_citation_block). Grounds all claims in real
                          corpus size + timeframe. Injected above the framing block.
    """
    prompt = build_synthesis_prompt(
        intent_key,
        payload,
        collapsed_questions=collapsed_questions,
        niche_key=niche_key,
        corpus_citation=corpus_citation,
    )
    cfg = types.GenerateContentConfig(temperature=GEMINI_TEMPERATURE, max_output_tokens=4096)
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("synthesize_intent_markdown returned empty response")
    return text.strip()


def generate_summary(
    analyses: list[dict[str, Any]],
    focus: str,
    computed_stats: dict[str, Any],
) -> dict[str, Any] | BatchSummary:
    """Cross-video summary via Gemini using computed numeric stats plus qualitative synthesis."""
    prompt = build_summary_prompt(analyses, focus, computed_stats)
    cfg = types.GenerateContentConfig(temperature=GEMINI_TEMPERATURE)
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
    )
    text = _response_text(response)
    if not text.strip():
        logger.warning("Gemini returned empty summary response")
        parsed = {"top_patterns": [], "content_gaps": [], "recommendations": []}
    else:
        try:
            parsed = SummaryInsights.model_validate(
                _parse_json_object(text)
            ).model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(
                "Summary insights parsing failed, using empty defaults: %s", e
            )
            parsed = {"top_patterns": [], "content_gaps": [], "recommendations": []}
    combined = {**computed_stats, **parsed}
    try:
        return BatchSummary.model_validate(combined)
    except ValidationError as e:
        logger.warning("Batch summary validation failed, returning raw dict: %s", e)
        return combined
