"""Google Gemini client: video analysis (inline or Files API) and batch summaries."""

from __future__ import annotations

import hashlib
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
    FILES_API_POLL_INITIAL_SEC,
    FILES_API_POLL_MAX_SEC,
    FILES_API_POLL_TIMEOUT_SEC,
    GEMINI_API_KEY,
    GEMINI_DIAGNOSIS_MODEL,
    GEMINI_EXTRACTION_CONTEXT_CACHE,
    GEMINI_EXTRACTION_FALLBACKS,
    GEMINI_EXTRACTION_MODEL,
    GEMINI_EXTRACTION_TEMPERATURE,
    GEMINI_INTENT_MODEL,
    GEMINI_KNOWLEDGE_FALLBACKS,
    GEMINI_KNOWLEDGE_MODEL,
    GEMINI_SYNTHESIS_FALLBACKS,
    GEMINI_SYNTHESIS_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_VIDEO_MEDIA_RESOLUTION,
    MAX_INLINE_SIZE_BYTES,
    require_gemini_api_key,
)
from getviews_pipeline.ensemble import (
    ClassifierDailyBudgetExceeded,
    consume_classifier_gemini_budget_or_raise,
)
from getviews_pipeline.models import BatchSummary, CarouselAnalysis, ContentType, VideoAnalysis
from getviews_pipeline.prompts import (
    CAROUSEL_EXTRACTION_USER_PREFIX_VI,
    VIDEO_EXTRACTION_USER_TURN_VI,
    build_carousel_diagnosis_prompt_v2,
    build_carousel_extraction_system_instruction,
    build_diagnosis_synthesis_prompt_v2,
    build_knowledge_system_instruction,
    build_knowledge_user_prompt,
    build_summary_prompt,
    build_synthesis_prompt,
    build_video_extraction_system_instruction,
    build_voice_domain_system_instruction,
)

logger = logging.getLogger(__name__)

_client: genai.Client | None = None
_client_lock = threading.Lock()


def _prefix_user_sections(prefixes: list[str], body: str) -> str:
    """Join optional dynamic context blocks before the main user prompt."""
    parts = [p.strip() for p in prefixes if p and str(p).strip()]
    if not parts:
        return body
    return "\n\n---\n\n".join(parts) + "\n\n---\n\n" + body


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

    ``thinking_budget=0`` disables reasoning on Gemini 3 — extraction is a
    deterministic JSON-schema fill, not a reasoning task. Thinking tokens
    bill at full output rate, so leaving the default on silently triples
    the per-call output cost (observed: ~6× output-token inflation on
    extraction days). See ``MODEL_PRICING_USD_PER_MTOK``.
    """
    base = _video_analysis_config()
    updates: dict[str, Any] = {
        "temperature": GEMINI_EXTRACTION_TEMPERATURE,
        "response_mime_type": "application/json",
        "response_json_schema": schema,
        "thinking_config": types.ThinkingConfig(thinking_budget=0),
    }
    if base is not None:
        return base.model_copy(update=updates)
    return types.GenerateContentConfig(**updates)


_EXTRACTION_CONTEXT_CACHE_SLOT: dict[str, dict[str, str | None]] = {
    "video": {"sig": None, "name": None},
    "carousel": {"sig": None, "name": None},
}
_EXTRACTION_CONTEXT_CACHE_LOCK = threading.Lock()


def _extraction_context_cache_signature(kind: str, system_text: str) -> str:
    h = hashlib.sha256()
    h.update(kind.encode("utf-8"))
    h.update(b"\n")
    h.update(GEMINI_EXTRACTION_MODEL.encode("utf-8"))
    h.update(b"\n")
    h.update(system_text.encode("utf-8"))
    return h.hexdigest()[:32]


def _get_extraction_cached_content_name(client: Any, kind: str, system_text: str) -> str | None:
    """HI-8 Phase B — optional explicit context cache; falls back to system_instruction."""
    if not GEMINI_EXTRACTION_CONTEXT_CACHE or not GEMINI_API_KEY:
        return None
    sig = _extraction_context_cache_signature(kind, system_text)
    with _EXTRACTION_CONTEXT_CACHE_LOCK:
        slot = _EXTRACTION_CONTEXT_CACHE_SLOT[kind]
        if slot["name"] and slot["sig"] == sig:
            return str(slot["name"])
    try:
        cc = client.caches.create(
            model=GEMINI_EXTRACTION_MODEL,
            config=types.CreateCachedContentConfig(
                display_name=f"gv-extract-{kind}-hi8",
                system_instruction=system_text,
                ttl="3600s",
            ),
        )
        name = cc.name
        if not name:
            return None
        with _EXTRACTION_CONTEXT_CACHE_LOCK:
            slot = _EXTRACTION_CONTEXT_CACHE_SLOT[kind]
            slot["sig"] = sig
            slot["name"] = name
        logger.info("[gemini] explicit context cache created name=%s kind=%s", name, kind)
        return name
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[gemini] extraction context cache create failed (%s) — using system_instruction",
            exc,
        )
        return None


def _configure_extraction_generate_config(
    client: Any,
    schema: dict[str, Any],
    *,
    kind: str,
    system_text: str,
) -> types.GenerateContentConfig:
    base = _extraction_json_config(schema)
    cached = _get_extraction_cached_content_name(client, kind, system_text)
    if cached:
        return base.model_copy(update={"cached_content": cached})
    return base.model_copy(update={"system_instruction": system_text})


_RETRY_DELAYS = (1, 2, 4)  # seconds — §13 mandate: 3 retries at 1s/2s/4s


def _is_transient_gemini_error(exc: Exception) -> bool:
    """Return True for 503 / overloaded errors that are safe to retry.

    Does NOT retry on 429 / quota / rate limit / resource exhausted: those
    mean Google is already throttling us, and Google bills the input tokens
    on every failed attempt. Retrying a 429 sleeps 1s/2s/4s then bills the
    same input 4× — observed amplifying ~330 daily 429s into a multi-dollar
    spike on the Tier-1 dashboard.
    """
    msg = str(exc).lower()
    return any(kw in msg for kw in ("503", "overloaded"))


# Vietnamese creator content includes everyday-life topics (drinking, dating
# advice, weight loss, finance hooks) that the SDK default
# BLOCK_MEDIUM_AND_ABOVE will silently refuse — those refusals show up as
# generic "synthesis failed" toasts in the UI. We pin BLOCK_ONLY_HIGH so
# only clearly harmful output is filtered, and we know we're explicit
# about it instead of inheriting the SDK default.
def _default_safety_settings() -> list[types.SafetySetting]:
    threshold = types.HarmBlockThreshold.BLOCK_ONLY_HIGH
    categories = (
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    )
    return [types.SafetySetting(category=c, threshold=threshold) for c in categories]


def _ensure_safety_settings(
    config: types.GenerateContentConfig | None,
) -> types.GenerateContentConfig:
    """Return a config with default safety_settings applied unless the
    caller already specified some. Never overwrites caller intent."""
    if config is None:
        return types.GenerateContentConfig(safety_settings=_default_safety_settings())
    if getattr(config, "safety_settings", None):
        return config
    return config.model_copy(update={"safety_settings": _default_safety_settings()})


def _generate_content_models(
    contents: Any,
    *,
    primary_model: str,
    fallbacks: list[str],
    config: types.GenerateContentConfig | None = None,
    call_site: str = "unknown",
    user_id: str | None = None,
    session_id: str | None = None,
) -> Any:
    """Dispatch a ``generate_content`` call through the primary → fallback
    chain, logging token usage + cost per successful response.

    ``call_site`` names the calling helper (e.g. ``"video_extraction"``,
    ``"pattern_narrative"``) and is the group-by column on the D.5.1
    dashboard. Every call site should pass an explicit value — the
    ``"unknown"`` default only exists so older helpers keep compiling
    while migrations land, and shows up as its own column on the
    dashboard so regressions surface immediately.
    """
    from getviews_pipeline.gemini_cost import (
        check_gemini_daily_budget,
        extract_usage,
        log_gemini_call,
        log_gemini_failure,
    )

    # B3: daily USD ceiling. Raises GeminiDailyBudgetExceeded when today's
    # gemini_calls.cost_usd sum has hit GEMINI_DAILY_USD_MAX and enforce
    # is on. No-op when the cap is 0 (legacy / dev).
    check_gemini_daily_budget(call_site)

    # M2: pin explicit safety_settings so we don't inherit the SDK default
    # (BLOCK_MEDIUM_AND_ABOVE), which silently refuses benign Vietnamese
    # creator content. The helper preserves caller-supplied settings.
    effective_config = _ensure_safety_settings(config)

    client = _get_client()
    chain = [primary_model, *fallbacks]
    seen: set[str] = set()
    last_err: Exception | None = None
    last_model: str = primary_model
    overall_started = time.monotonic()
    for m in chain:
        if not m or m in seen:
            continue
        seen.add(m)
        last_model = m
        for attempt, delay in enumerate(_RETRY_DELAYS):
            try:
                started = time.monotonic()
                kwargs: dict[str, Any] = {
                    "model": m,
                    "contents": contents,
                    "config": effective_config,
                }
                from getviews_pipeline import telemetry as _tel
                with _tel.span("gemini.generate_content", model=m, call_site=call_site, attempt=attempt):
                    response = client.models.generate_content(**kwargs)
                duration_ms = int((time.monotonic() - started) * 1000)
                tokens_in, tokens_out = extract_usage(response)
                log_gemini_call(
                    user_id=user_id,
                    call_site=call_site,
                    model_name=m,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    duration_ms=duration_ms,
                    session_id=session_id,
                )
                return response
            except Exception as e:
                is_transient = _is_transient_gemini_error(e)
                is_last_attempt = attempt == len(_RETRY_DELAYS) - 1
                if not is_transient or is_last_attempt:
                    last_err = e
                    logger.warning("Gemini model %s attempt %d/%d failed: %s", m, attempt + 1, len(_RETRY_DELAYS), e)
                    break
                logger.info("Gemini model %s transient error (attempt %d/%d), retrying in %ds: %s", m, attempt + 1, len(_RETRY_DELAYS), delay, e)
                time.sleep(delay)
    # All models + retries exhausted. Log a failure row to gemini_calls
    # so the dashboard surfaces the outage — best-effort, never blocks
    # the raise path.
    overall_ms = int((time.monotonic() - overall_started) * 1000)
    if last_err is not None:
        try:
            log_gemini_failure(
                user_id=user_id,
                call_site=call_site,
                model_name=last_model,
                exc=last_err,
                duration_ms=overall_ms,
                session_id=session_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[gemini] log_gemini_failure crashed: %s", exc)
        raise last_err
    raise RuntimeError("No Gemini models available")


def analyze_video(video_path: Path) -> VideoAnalysis:
    """Run full forensic analysis on a local video file (sync)."""
    path = video_path.resolve()
    size = path.stat().st_size
    client = _get_client()
    sys_inst = build_video_extraction_system_instruction()
    json_cfg = _configure_extraction_generate_config(
        client,
        VideoAnalysis.model_json_schema(),
        kind="video",
        system_text=sys_inst,
    )

    if size <= MAX_INLINE_SIZE_BYTES:
        data = path.read_bytes()
        video_part = types.Part.from_bytes(data=data, mime_type="video/mp4")
        response = _generate_content_models(
            [video_part, VIDEO_EXTRACTION_USER_TURN_VI],
            primary_model=GEMINI_EXTRACTION_MODEL,
            fallbacks=GEMINI_EXTRACTION_FALLBACKS,
            config=json_cfg,
            call_site="video_extraction",
        )
    else:
        uploaded = client.files.upload(file=str(path))
        name = uploaded.name
        try:
            # Exponential backoff with a 90s overall budget. Creators uploading
            # dense 60s videos occasionally need 40-60s for ACTIVE state — the
            # previous 30s hard cap silently failed those.
            info = uploaded
            deadline = time.monotonic() + FILES_API_POLL_TIMEOUT_SEC
            delay = FILES_API_POLL_INITIAL_SEC
            while True:
                info = client.files.get(name=name)
                state = getattr(info.state, "name", None) or str(info.state)
                if state == "ACTIVE":
                    break
                if state == "FAILED":
                    raise RuntimeError(f"Gemini file processing failed: {name}")
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Gemini file never became ACTIVE within "
                        f"{FILES_API_POLL_TIMEOUT_SEC:.0f}s (last state={state})"
                    )
                time.sleep(delay)
                delay = min(delay * 1.5, FILES_API_POLL_MAX_SEC)

            response = _generate_content_models(
                [info, VIDEO_EXTRACTION_USER_TURN_VI],
                primary_model=GEMINI_EXTRACTION_MODEL,
                fallbacks=GEMINI_EXTRACTION_FALLBACKS,
                config=json_cfg,
                call_site="video_extraction_filesapi",
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

    client = _get_client()
    sys_car = build_carousel_extraction_system_instruction()
    json_cfg = _configure_extraction_generate_config(
        client,
        CarouselAnalysis.model_json_schema(),
        kind="carousel",
        system_text=sys_car,
    )
    user_text = CAROUSEL_EXTRACTION_USER_PREFIX_VI + tail
    parts: list[Any] = [
        *[types.Part.from_bytes(data=data, mime_type=mime) for data, mime in slides],
        user_text,
    ]

    response = _generate_content_models(
        parts,
        primary_model=GEMINI_EXTRACTION_MODEL,
        fallbacks=GEMINI_EXTRACTION_FALLBACKS,
        config=json_cfg,
        call_site="carousel_extraction",
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("Gemini returned empty response text")
    parsed = _parse_json_object(text)
    analysis = CarouselAnalysis.model_validate(parsed)
    return _normalize_carousel_slide_indices(analysis, indices)


def _infer_carousel_format(analysis: dict[str, Any]) -> str:
    """Infer carousel sub-format from content_arc in analysis dict."""
    arc = (analysis.get("content_arc") or "").lower()
    if arc in ("list", "gallery"):
        return "carousel_product_roundup"
    if arc in ("tutorial_steps",):
        return "carousel_tutorial"
    if arc in ("story", "narrative"):
        return "carousel_story"
    return "carousel"


_NO_NICHE_NOTE: dict[str, Any] = {
    "_note": "Không có data niche — phân tích dựa trên video này, không so sánh với chuẩn niche"
}


def synthesize_diagnosis(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
    content_type: ContentType = "video",
    include_carousel_directions: bool = False,
    user_message: str = "",
) -> str:
    """Strategist markdown: routes to video vs carousel v2 diagnosis prompt.

    Both paths use their respective v2 narrative builders with zero corpus context
    (analysis_core callers don't have niche/corpus data). Output is analysis-only —
    lacks niche benchmarks but uses the correct 2-layer narrative structure.

    Full corpus-enriched v2 diagnosis runs via pipelines.run_video_diagnosis.
    """
    model = GEMINI_DIAGNOSIS_MODEL or GEMINI_SYNTHESIS_MODEL
    _no_niche = _NO_NICHE_NOTE
    user_stats = {
        "views": metadata.get("views") or 0,
        "likes": metadata.get("likes") or 0,
        "comments": metadata.get("comments") or 0,
        "shares": metadata.get("shares") or 0,
        "breakout_multiplier": metadata.get("breakout") or 0.0,
        "duration": metadata.get("duration") or 0,
    }

    if content_type == "carousel":
        carousel_format = _infer_carousel_format(analysis)
        prompt = build_carousel_diagnosis_prompt_v2(
            carousel_format=carousel_format,
            niche_name=metadata.get("niche") or "",
            corpus_size=0,
            niche_meta=_no_niche,
            reference_carousels=[],
            user_analysis=analysis,
            user_stats=user_stats,
            wants_directions=include_carousel_directions,
        )
    else:
        content_format = (analysis.get("content_format") or "other").lower()
        prompt = build_diagnosis_synthesis_prompt_v2(
            content_format=content_format,
            niche_name=metadata.get("niche") or "",
            corpus_size=0,
            niche_meta=_no_niche,
            reference_videos=[],
            user_analysis=analysis,
            user_stats=user_stats,
        )
    sys_inst = build_voice_domain_system_instruction(
        include_diagnosis_examples=content_type != "carousel",
    )
    cfg = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=3072,
        system_instruction=sys_inst,
    )

    response = _generate_content_models(
        [prompt],
        primary_model=model,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
        call_site="diagnosis_synthesis_v1",
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("Gemini returned empty synthesis response")
    return text.strip()


def _allowed_aweme_ids(reference_videos: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for r in reference_videos:
        aid = r.get("aweme_id")
        if aid is not None and str(aid):
            ids.add(str(aid))
    return ids


def _split_diagnosis_leading_json(full_text: str) -> tuple[dict[str, Any] | None, str]:
    """Extract the narrative JSON block from Gemini's response.

    Handles three formats Gemini 3.x may produce:
    1. Leading fenced block:  ```json\\n{...}\\n```  then markdown
    2. Fenced block preceded by a preamble line (model ignores "at the top" instruction)
    3. Plain JSON object as the entire response (no fences)
    """
    s = full_text.strip()

    # ── Format 3: entire response is valid JSON ────────────────────────────
    if s.startswith("{"):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj, ""
        except json.JSONDecodeError:
            pass  # Fall through to fence scanning

    # ── Formats 1 & 2: find the first ```json ... ``` fence ───────────────
    fence_start = s.find("```")
    if fence_start == -1:
        logger.warning(
            "[diagnosis_v2] no fenced JSON block found — full markdown path. "
            "response_prefix=%r",
            s[:200],
        )
        return None, s

    nl = s.find("\n", fence_start + 3)
    if nl == -1:
        logger.warning("[diagnosis_v2] malformed fence (no newline after opening ```)")
        return None, s

    close = s.find("```", nl + 1)
    if close == -1:
        logger.warning("[diagnosis_v2] unclosed json fence")
        return None, s

    inner = s[nl + 1 : close].strip()
    if inner.lower().startswith("json"):
        inner = inner[4:].lstrip()

    try:
        obj = json.loads(inner)
    except json.JSONDecodeError as exc:
        logger.warning("[diagnosis_v2] JSON parse failed: %s — prefix=%r", exc, inner[:400])
        return None, s

    rest = s[close + 3 :].strip()
    if fence_start > 0:
        logger.info(
            "[diagnosis_v2] JSON found after %d-char preamble — model skipped leading-block rule",
            fence_start,
        )
    return obj if isinstance(obj, dict) else None, rest


def _validate_narrative_citations(
    narrative_vi: dict[str, Any] | None,
    format_cards: list[dict[str, Any]] | None,
    allowed_aweme: set[str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None]:
    if narrative_vi:
        for item in narrative_vi.get("loi_chinh_narrative") or []:
            if not isinstance(item, dict):
                continue
            eid = item.get("evidence_aweme_id")
            if eid is not None and str(eid) not in allowed_aweme:
                item["evidence_aweme_id"] = None
    if format_cards:
        for card in format_cards:
            if not isinstance(card, dict):
                continue
            eid = card.get("evidence_aweme_id")
            if eid is not None and str(eid) not in allowed_aweme:
                card["evidence_aweme_id"] = None
    return narrative_vi, format_cards


def _normalize_narrative_vi_dict(narrative_vi: dict[str, Any] | None) -> dict[str, Any] | None:
    """Ensure ``headline_vi`` and ``lessons`` exist for the unified video report schema."""
    if not narrative_vi:
        return narrative_vi
    headline = str(narrative_vi.get("headline_vi") or "").strip()
    if not headline:
        fallback = str(narrative_vi.get("ket_luan_nhanh") or "").strip()
        narrative_vi = {
            **narrative_vi,
            "headline_vi": (fallback[:400] if fallback else "—"),
        }
    lessons_raw = narrative_vi.get("lessons")
    if lessons_raw is None or not isinstance(lessons_raw, list):
        narrative_vi = {**narrative_vi, "lessons": []}
    return narrative_vi


def synthesize_diagnosis_v2(
    content_format: str,
    niche_name: str,
    corpus_size: int,
    niche_meta: dict[str, Any],
    reference_videos: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    collapsed_questions: list[str] | None = None,
    wants_directions: bool = False,
    layer0_context: str = "",
    corpus_citation: str = "",
    persona_block: str = "",
    *,
    performance_tier: str = "unknown",
    channel_context: dict[str, Any] | None = None,
    errors: list[dict[str, Any]] | None = None,
    reference_evidence_block: str = "",
) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]] | None]:
    """V2 narrative diagnosis — Markdown body plus optional structured narrative/format cards."""

    allowed = _allowed_aweme_ids(reference_videos)
    model = GEMINI_DIAGNOSIS_MODEL or GEMINI_SYNTHESIS_MODEL
    sys_inst = build_voice_domain_system_instruction(include_diagnosis_examples=True)
    prompt = build_diagnosis_synthesis_prompt_v2(
        content_format=content_format,
        niche_name=niche_name,
        corpus_size=corpus_size,
        niche_meta=niche_meta,
        reference_videos=reference_videos,
        user_analysis=user_analysis,
        user_stats=user_stats,
        wants_directions=wants_directions,
        corpus_citation=corpus_citation,
        persona_block=persona_block,
        performance_tier=performance_tier,
        channel_context=channel_context,
        errors=errors,
        reference_evidence_block=reference_evidence_block,
    )
    prompt = _prefix_user_sections([layer0_context or ""], prompt)
    if collapsed_questions:
        question_block = (
            "\n\nNgười dùng hỏi nhiều câu; thêm mục có tiêu đề rõ cho từng câu:\n"
            + "\n".join(f"- {q}" for q in collapsed_questions)
        )
        prompt = prompt.rstrip() + question_block + "\n\nViết chẩn đoán ngay."

    max_tokens = 6000 if wants_directions else 3500
    cfg = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=max_tokens,
        system_instruction=sys_inst,
    )
    response = _generate_content_models(
        [prompt],
        primary_model=model,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
        call_site="diagnosis_synthesis_v2",
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("synthesize_diagnosis_v2 returned empty response")

    raw_obj, remainder = _split_diagnosis_leading_json(text)
    narrative_vi: dict[str, Any] | None = None
    format_cards: list[dict[str, Any]] | None = None
    if raw_obj:
        nv = raw_obj.get("narrative_vi")
        fc = raw_obj.get("format_cards")
        narrative_vi = nv if isinstance(nv, dict) else None
        format_cards = fc if isinstance(fc, list) else None
        narrative_vi, format_cards = _validate_narrative_citations(
            narrative_vi, format_cards, allowed
        )
        narrative_vi = _normalize_narrative_vi_dict(narrative_vi)
    body = remainder.strip()

    scan_target = body if raw_obj else text.strip()
    try:
        from getviews_pipeline.analysis_guards import (
            scan_synthesis_for_fabricated_metrics,
        )

        scan = scan_synthesis_for_fabricated_metrics(scan_target)
        if not scan.clean:
            logger.warning(
                "[synthesis_guard] possible fabricated metric(s) in diagnosis_v2 output: %s",
                scan.flags,
            )
    except Exception as exc:  # pragma: no cover — pure helper
        logger.warning("[synthesis_guard] scan failed: %s", exc)
    return body, narrative_vi, format_cards


def synthesize_diagnosis_carousel_v2(
    carousel_format: str,
    niche_name: str,
    corpus_size: int,
    niche_meta: dict[str, Any],
    reference_carousels: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    wants_directions: bool = False,
    collapsed_questions: list[str] | None = None,
    layer0_context: str = "",
    corpus_citation: str = "",
    persona_block: str = "",
    creator_format_history_block: str = "",
) -> str:
    """V2 carousel diagnosis — 2-layer narrative (distribution + swipe logic), corpus-aware.

    Mirrors synthesize_diagnosis_v2() for video but uses:
    - build_carousel_diagnosis_prompt_v2() from prompts.py
    - carousel-specific FORMAT_ANALYSIS_WEIGHTS and CAROUSEL_NARRATIVE_OUTPUT_STRUCTURE
    max_output_tokens set to 3072 to match video v2 — narrative structure needs room.
    """
    model = GEMINI_DIAGNOSIS_MODEL or GEMINI_SYNTHESIS_MODEL
    sys_inst = build_voice_domain_system_instruction(include_diagnosis_examples=False)
    prompt = build_carousel_diagnosis_prompt_v2(
        carousel_format=carousel_format,
        niche_name=niche_name,
        corpus_size=corpus_size,
        niche_meta=niche_meta,
        reference_carousels=reference_carousels,
        user_analysis=user_analysis,
        user_stats=user_stats,
        wants_directions=wants_directions,
        corpus_citation=corpus_citation,
        persona_block=persona_block,
    )
    prompt = _prefix_user_sections(
        [layer0_context or "", creator_format_history_block or ""],
        prompt,
    )
    if collapsed_questions:
        question_block = (
            "\n\nNgười dùng hỏi nhiều câu; thêm mục có tiêu đề rõ cho từng câu:\n"
            + "\n".join(f"- {q}" for q in collapsed_questions)
        )
        prompt = prompt.rstrip() + question_block + "\n\nViết chẩn đoán ngay."

    # Directions block adds ~1000 tokens — extend budget so it isn't truncated.
    max_tokens = 6000 if wants_directions else 3072
    cfg = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=max_tokens,
        system_instruction=sys_inst,
    )
    response = _generate_content_models(
        [prompt],
        primary_model=model,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
        call_site="carousel_diagnosis_v2",
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("synthesize_diagnosis_carousel_v2 returned empty response")
    try:
        from getviews_pipeline.analysis_guards import (
            scan_synthesis_for_fabricated_metrics,
        )

        scan = scan_synthesis_for_fabricated_metrics(text)
        if not scan.clean:
            logger.warning(
                "[synthesis_guard] possible fabricated metric(s) in diagnosis_carousel_v2: %s",
                scan.flags,
            )
    except Exception as exc:  # pragma: no cover
        logger.warning("[synthesis_guard] carousel scan failed: %s", exc)
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


# Gemini-side intent labels. ``query_intent_to_gemini_primary`` (the BE
# enum→label mapper) was removed L1.5 audit follow-up along with the
# deterministic classifier; this list is now self-contained — keep it
# in sync with the frontend FixedIntentId union in
# ``src/routes/_app/intent-router.ts`` instead.
# Historical removals: ``series_audit`` (2026-04-22), ``comparison`` /
# ``find_creators`` / ``followup`` / ``metadata_only`` (L1.5). Legacy
# Gemini outputs that still emit these are normalised to current values
# at the router edge in
#     ``routers/intent.py``; this list drives the prompt the model sees
#     today.
GEMINI_CLASSIFIER_PRIMARY_LABELS: tuple[str, ...] = (
    "video_diagnosis",
    "content_directions",
    "trend_spike",
    "brief_generation",
    "shot_list",
    "competitor_profile",
    "own_channel",
    "creator_search",
    "timing",
    "fatigue",
    "hook_variants",
    "content_calendar",
    "subniche_breakdown",
    "format_lifecycle_optimize",
    "own_flop_no_url",
    "follow_up",
)

_INTENT_LABELS = GEMINI_CLASSIFIER_PRIMARY_LABELS

_INTENT_CLASSIFICATION_PROMPT = """\
You are an intent classifier for a Vietnamese TikTok content strategy assistant.

Classify the user message into ONE primary intent from this fixed list:
- video_diagnosis      — user shares a TikTok URL and asks why it performs the way it does, or wants it analyzed
- content_directions   — user wants content format/hook/direction suggestions for a niche (no URL, or URL + directions request)
- trend_spike          — user wants to know what is trending RIGHT NOW in a niche
- brief_generation     — user wants a production brief or content plan for a specific video
- shot_list            — user wants a shot-by-shot filming plan
- competitor_profile   — user wants analysis of another creator's account (@handle or profile URL)
- own_channel          — user wants analysis of their OWN channel
- creator_search       — user wants to find/discover TikTok creators in a niche (formerly ``find_creators``)
- timing               — best time/day to post, posting window, schedule
- fatigue              — declining format, pattern dying, trend exhaustion
- hook_variants        — rewrite hooks, hook variations
- content_calendar     — what to post this week, content calendar
- subniche_breakdown   — sub-niche breakdown within a niche
- format_lifecycle_optimize — carousel vs video, short vs long format tradeoffs
- own_flop_no_url      — user's own videos/channel underperforming but no URL given
- follow_up            — general question, follow-up to previous response, or unclear

Also output a secondary intent if the message clearly requests TWO things (e.g. "why is this video low?" + "suggest formats").
Secondary intent is null if there is only one clear intent.

``primary_confidence`` must be a number from 0.0 to 1.0 — your estimated probability that ``primary`` is correct.

Output valid JSON only — no markdown, no explanation:
{{"primary": "<intent>", "secondary": "<intent or null>", "niche_hint": "<detected niche name in Vietnamese or English, or null>", "primary_confidence": 0.85}}

User message: {message}
"""


def classify_intent_gemini(
    message: str,
    has_url: bool = False,
    has_handle: bool = False,
) -> dict[str, str | None]:
    """Tier-3 semantic intent classification via Gemini (Flash-Lite, JSON output).

    Returns a dict with keys:
        primary   — one of ``GEMINI_CLASSIFIER_PRIMARY_LABELS``
        secondary — second intent if compound query, else None
        niche_hint — detected niche name string, or None
        primary_confidence — 0.0–1.0 when present (omitted on budget / error fallback)

    Falls back to {"primary": "follow_up", "secondary": None, "niche_hint": None}
    on any Gemini error so callers never crash.
    """
    # Fast structural override — don't spend a Gemini call if answer is obvious
    if has_url:
        structural = "video_diagnosis"
    elif has_handle:
        structural = "competitor_profile"
    else:
        structural = None

    prompt = _INTENT_CLASSIFICATION_PROMPT.format(message=message)
    cfg = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=192,
        response_mime_type="application/json",
    )
    try:
        consume_classifier_gemini_budget_or_raise()
    except ClassifierDailyBudgetExceeded as exc:
        logger.warning(
            "[classifier-budget] [classify_intent_gemini] %s — deterministic fallback (no Gemini call)",
            exc,
        )
        return {
            "primary": structural or "follow_up",
            "secondary": None,
            "niche_hint": None,
        }
    try:
        response = _generate_content_models(
            [prompt],
            primary_model=GEMINI_INTENT_MODEL,
            fallbacks=[GEMINI_KNOWLEDGE_MODEL],
            config=cfg,
            call_site="intent_classifier",
        )
        raw = _response_text(response).strip()
        result: dict[str, Any] = json.loads(raw)
        primary = result.get("primary") or "follow_up"
        if primary not in _INTENT_LABELS:
            primary = "follow_up"
        secondary = result.get("secondary")
        if secondary and secondary not in _INTENT_LABELS:
            secondary = None
        # Structural URL/handle signals always win for primary
        if structural and primary == "follow_up":
            primary = structural
        conf_raw = result.get("primary_confidence")
        pconf: float | None
        try:
            if conf_raw is None:
                pconf = None
            else:
                pconf = max(0.0, min(1.0, float(conf_raw)))
        except (TypeError, ValueError):
            pconf = None
        out: dict[str, str | float | None] = {
            "primary": primary,
            "secondary": secondary,
            "niche_hint": result.get("niche_hint") if isinstance(result.get("niche_hint"), str) else None,
        }
        if pconf is not None:
            out["primary_confidence"] = pconf
        return out
    except Exception as exc:
        logger.warning("[classify_intent_gemini] failed: %s — falling back to follow_up", exc)
        return {"primary": structural or "follow_up", "secondary": None, "niche_hint": None}


def gemini_text_only(message: str, session_context: dict[str, Any]) -> str:
    """§3a Rule A / follow-up — knowledge or session-grounded text."""
    sys_inst = build_knowledge_system_instruction(message)
    prompt = build_knowledge_user_prompt(message, session_context)
    cfg = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=1024,
        system_instruction=sys_inst,
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_KNOWLEDGE_MODEL,
        fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
        config=cfg,
        call_site="gemini_text_only",
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
    persona_block: str = "",
) -> str:
    """Multi-video / niche synthesis using §18 intent framing.

    Args:
        niche_key:        Optional niche identifier passed through to build_synthesis_prompt
                          so knowledge_base niche guidance is injected (brief_generation,
                          video_diagnosis intents).
        corpus_citation:  Optional pre-built citation block from corpus_context.py
                          (build_corpus_citation_block). Grounds all claims in real
                          corpus size + timeframe. Injected above the framing block.
        persona_block:    Optional persona-slot block from persona.py
                          (build_persona_block). Instructs the model to target
                          the audience attributes (age, pain points, geography)
                          the user mentioned instead of dropping them.
    """
    prompt = build_synthesis_prompt(
        intent_key,
        payload,
        collapsed_questions=collapsed_questions,
        niche_key=niche_key,
        corpus_citation=corpus_citation,
        persona_block=persona_block,
    )
    sys_inst = build_voice_domain_system_instruction(include_diagnosis_examples=False)
    cfg = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=4096,
        system_instruction=sys_inst,
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
        call_site="intent_markdown",
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("synthesize_intent_markdown returned empty response")
    try:
        from getviews_pipeline.analysis_guards import (
            scan_synthesis_for_fabricated_metrics,
        )

        scan = scan_synthesis_for_fabricated_metrics(text)
        if not scan.clean:
            logger.warning(
                "[synthesis_guard] possible fabricated metric(s) in intent_markdown "
                "intent=%s: %s",
                intent_key, scan.flags,
            )
    except Exception as exc:  # pragma: no cover
        logger.warning("[synthesis_guard] intent_markdown scan failed: %s", exc)
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
        call_site="batch_summary",
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


def generate_niche_insight(
    niche_name: str,
    formula_hook: str,
    formula_format: str,
    top_videos: list[dict[str, Any]],
    baseline_videos: list[dict[str, Any]],
) -> dict[str, Any]:
    """Layer 0A — mechanism extraction with contrastive framing (Pearl's Ladder).

    Uses GEMINI_EXTRACTION_MODEL (Flash) for strongest causal reasoning.
    Temperature 0.2 for analytical precision, not creative output.
    """
    from getviews_pipeline.layer0_prompts import (
        LAYER0_NICHE_RESPONSE_SCHEMA,
        NICHE_INSIGHT_FEW_SHOT_EXAMPLES,
        NICHE_INSIGHT_SYSTEM_INSTRUCTION,
        NICHE_INSIGHT_USER_PROMPT_TEMPLATE,
    )

    top_json = json.dumps(top_videos, ensure_ascii=False, indent=2)
    baseline_json = json.dumps(baseline_videos, ensure_ascii=False, indent=2)
    user_prompt = NICHE_INSIGHT_USER_PROMPT_TEMPLATE.format(
        niche_name=niche_name,
        hook_type=formula_hook,
        content_format=formula_format,
        top_videos_json=top_json,
        baseline_videos_json=baseline_json,
    )
    full_prompt = (
        f"{NICHE_INSIGHT_SYSTEM_INSTRUCTION}\n\n"
        f"## FEW-SHOT EXAMPLES\n{NICHE_INSIGHT_FEW_SHOT_EXAMPLES}\n\n"
        f"---\n\n{user_prompt}"
    )

    # _extraction_json_config already sets temperature=GEMINI_EXTRACTION_TEMPERATURE (0.2),
    # response_mime_type, response_json_schema, and preserves media_resolution from
    # _video_analysis_config() via model_copy. Do not replace it.
    cfg = _extraction_json_config(LAYER0_NICHE_RESPONSE_SCHEMA)

    response = _generate_content_models(
        [full_prompt],
        primary_model=GEMINI_EXTRACTION_MODEL,
        fallbacks=GEMINI_EXTRACTION_FALLBACKS,
        config=cfg,
        call_site="niche_insight",
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError(f"generate_niche_insight: empty response for niche={niche_name}")
    return json.loads(_normalize_response(text))
