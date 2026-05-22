"""Google Gemini client: video analysis (inline or Files API) and batch summaries."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import tempfile
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
    GEMINI_CONTEXT_CACHE_TTL_SEC,
    GEMINI_DIAGNOSIS_MODEL,
    GEMINI_EXTRACTION_CONTEXT_CACHE,
    GEMINI_EXTRACTION_FALLBACKS,
    GEMINI_EXTRACTION_MODEL,
    GEMINI_EXTRACTION_TEMPERATURE,
    GEMINI_HOOK_WINDOW_DUAL_PART,
    GEMINI_HOOK_WINDOW_END_SEC,
    GEMINI_HOOK_WINDOW_FPS,
    GEMINI_INTENT_MODEL,
    GEMINI_KNOWLEDGE_FALLBACKS,
    GEMINI_KNOWLEDGE_MODEL,
    GEMINI_SYNTHESIS_CONTEXT_CACHE,
    GEMINI_SYNTHESIS_FALLBACKS,
    GEMINI_SYNTHESIS_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_VIDEO_BASE_FPS,
    GEMINI_VIDEO_MEDIA_RESOLUTION,
    GETVIEWS_DIAGNOSIS_SECTION_MODE,
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
    build_carousel_diagnosis_prompt_v2,
    build_carousel_extraction_system_instruction,
    build_diagnosis_synthesis_prompt_v2,
    build_knowledge_system_instruction,
    build_knowledge_user_prompt,
    build_summary_prompt,
    build_synthesis_prompt,
    build_video_extraction_system_instruction,
    build_video_extraction_user_turn_vi,
    build_voice_domain_system_instruction,
)
from getviews_pipeline.vietnamese_slang import merge_lexicon_slang_into_video_analysis_dict

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
    """Optional ``media_resolution`` on the API config (not hook FPS).

    HI-15 hook-window sampling uses **per-Part** ``video_metadata`` on the
    inline / Files API video Parts in ``_build_video_extraction_content_parts``,
    not this top-level field.
    """
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


def _build_video_extraction_content_parts(
    *,
    video_bytes: bytes | None,
    mime_type: str,
    file_resource: Any | None,
) -> list[Any]:
    """Build one or two video Parts — HI-15 dual-window high FPS on the hook (0–N s).

    When ``GEMINI_HOOK_WINDOW_DUAL_PART`` is false, behaviour matches pre-HI-15
    (single Part, API default ~1 FPS). Carousel / image-only paths must never
    call this — ``video_metadata`` applies to video bytes only.
    """
    if (video_bytes is None) == (file_resource is None):
        raise ValueError("Exactly one of video_bytes or file_resource must be set")

    if not GEMINI_HOOK_WINDOW_DUAL_PART:
        if video_bytes is not None:
            return [types.Part.from_bytes(data=video_bytes, mime_type=mime_type)]
        return [file_resource]

    base_fps = max(0.1, min(24.0, float(GEMINI_VIDEO_BASE_FPS)))
    hook_fps = max(3.0, min(5.0, float(GEMINI_HOOK_WINDOW_FPS)))
    end_sec = max(0.5, min(10.0, float(GEMINI_HOOK_WINDOW_END_SEC)))
    end_offset = f"{end_sec:g}s"
    vm_full = types.VideoMetadata(fps=base_fps)
    vm_hook = types.VideoMetadata(
        fps=hook_fps,
        start_offset="0s",
        end_offset=end_offset,
    )
    if video_bytes is not None:
        blob = types.Blob(data=video_bytes, mime_type=mime_type)
        return [
            types.Part(inline_data=blob, video_metadata=vm_full),
            types.Part(inline_data=blob, video_metadata=vm_hook),
        ]
    uri = getattr(file_resource, "uri", None)
    if not uri:
        raise RuntimeError("Files API file missing uri — cannot build video Parts")
    mime = getattr(file_resource, "mime_type", None) or mime_type
    fd = types.FileData(file_uri=uri, mime_type=mime)
    return [
        types.Part(file_data=fd, video_metadata=vm_full),
        types.Part(file_data=fd, video_metadata=vm_hook),
    ]


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


_EXTRACTION_CONTEXT_CACHE_SLOT: dict[str, dict[str, Any]] = {
    "video": {"sig": None, "name": None, "created_monotonic": None},
    "carousel": {"sig": None, "name": None, "created_monotonic": None},
}
_EXTRACTION_CONTEXT_CACHE_LOCK = threading.Lock()


def _extraction_context_cache_max_age_sec() -> float:
    """Age after ``caches.create`` when we force refresh (HI-8 batch runway).

    Google measures TTL from cache creation. Batch poll-max (40m) plus prep/queue
    can exceed a naive reuse of an hour-old slot — recreate with a 600s margin
    before nominal expiry. If ``GEMINI_CONTEXT_CACHE_TTL_SEC`` is too small for
    that margin, fall back to half the TTL.
    """
    ttl_s = max(1, int(GEMINI_CONTEXT_CACHE_TTL_SEC))
    raw = float(ttl_s) - 600.0
    if raw <= 0:
        return max(1.0, float(ttl_s) * 0.5)
    return raw


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
    max_age = _extraction_context_cache_max_age_sec()
    with _EXTRACTION_CONTEXT_CACHE_LOCK:
        slot = _EXTRACTION_CONTEXT_CACHE_SLOT[kind]
        created = slot.get("created_monotonic")
        if (
            slot.get("name")
            and slot.get("sig") == sig
            and created is not None
            and (time.monotonic() - float(created)) < max_age
        ):
            return str(slot["name"])
        slot["name"] = None
        slot["sig"] = None
        slot["created_monotonic"] = None
    ttl_s = max(1, int(GEMINI_CONTEXT_CACHE_TTL_SEC))
    try:
        cc = client.caches.create(
            model=GEMINI_EXTRACTION_MODEL,
            config=types.CreateCachedContentConfig(
                display_name=f"gv-extract-{kind}-hi8",
                system_instruction=system_text,
                ttl=f"{ttl_s}s",
            ),
        )
        name = cc.name
        if not name:
            return None
        with _EXTRACTION_CONTEXT_CACHE_LOCK:
            slot = _EXTRACTION_CONTEXT_CACHE_SLOT[kind]
            slot["sig"] = sig
            slot["name"] = name
            slot["created_monotonic"] = time.monotonic()
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


_SYNTHESIS_CONTEXT_CACHE_SLOT: dict[str, dict[str, str | None]] = {}
_SYNTHESIS_CONTEXT_CACHE_LOCK = threading.Lock()


def _synthesis_cache_slot_key(kind: str, model: str) -> str:
    return f"{kind}\x00{model}"


def _synthesis_context_cache_signature(kind: str, model: str, system_text: str) -> str:
    h = hashlib.sha256()
    h.update(kind.encode("utf-8"))
    h.update(b"\n")
    h.update(model.encode("utf-8"))
    h.update(b"\n")
    h.update(system_text.encode("utf-8"))
    return h.hexdigest()[:32]


def _get_synthesis_cached_content_name(
    client: Any,
    kind: str,
    model: str,
    system_text: str,
) -> str | None:
    """HI-8 — optional explicit context cache for synthesis; falls back to system_instruction."""
    if not GEMINI_SYNTHESIS_CONTEXT_CACHE or not GEMINI_API_KEY:
        return None
    slot_key = _synthesis_cache_slot_key(kind, model)
    sig = _synthesis_context_cache_signature(kind, model, system_text)
    with _SYNTHESIS_CONTEXT_CACHE_LOCK:
        slot = _SYNTHESIS_CONTEXT_CACHE_SLOT.get(slot_key)
        if slot and slot.get("name") and slot.get("sig") == sig:
            logger.debug("[gemini] synthesis context cache HIT kind=%s model=%s", kind, model)
            return str(slot["name"])
    ttl_s = GEMINI_CONTEXT_CACHE_TTL_SEC
    try:
        cc = client.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                display_name=f"gv-synth-{kind}-hi8",
                system_instruction=system_text,
                ttl=f"{ttl_s}s",
            ),
        )
        name = cc.name
        if not name:
            return None
        with _SYNTHESIS_CONTEXT_CACHE_LOCK:
            _SYNTHESIS_CONTEXT_CACHE_SLOT[slot_key] = {"sig": sig, "name": name}
        logger.info(
            "[gemini] synthesis context cache CREATED name=%s kind=%s model=%s",
            name,
            kind,
            model,
        )
        return name
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[gemini] synthesis context cache create failed (%s) — using system_instruction",
            exc,
        )
        return None


def _apply_synthesis_context_for_model(
    client: Any,
    base: types.GenerateContentConfig,
    *,
    kind: str,
    model: str,
    system_text: str,
) -> types.GenerateContentConfig:
    """Attach static system text via ``cached_content`` or ``system_instruction``."""
    cached = _get_synthesis_cached_content_name(client, kind, model, system_text)
    if cached:
        return base.model_copy(update={"cached_content": cached, "system_instruction": None})
    return base.model_copy(update={"system_instruction": system_text, "cached_content": None})


_RETRY_DELAYS = (1, 2, 4)  # seconds — §13 mandate: 3 retries at 1s/2s/4s

# ── HI-13 — Gemini Batch API (JSONL file source) for corpus extraction ───────
_BATCH_TERMINAL_STATES = frozenset({
    "JOB_STATE_SUCCEEDED",
    "JOB_STATE_FAILED",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_EXPIRED",
})


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
    synthesis_cache_kind: str | None = None,
    synthesis_cache_system_text: str | None = None,
    gcp_stt_cost_usd: float | None = None,
) -> Any:
    """Dispatch a ``generate_content`` call through the primary → fallback
    chain, logging token usage + cost per successful response.

    ``call_site`` names the calling helper (e.g. ``"video_extraction"``,
    ``"pattern_narrative"``) and is the group-by column on the D.5.1
    dashboard. Every call site should pass an explicit value — the
    ``"unknown"`` default only exists so older helpers keep compiling
    while migrations land, and shows up as its own column on the
    dashboard so regressions surface immediately.

    When ``synthesis_cache_kind`` and ``synthesis_cache_system_text`` are
    set, ``config`` must not carry ``system_instruction`` / ``cached_content``
    — those are merged per fallback ``model`` so each model gets a valid
    cache name (HI-8). Dynamic per-request system text (e.g. knowledge)
    should omit these args and set ``system_instruction`` on ``config``.
    """
    from getviews_pipeline.gemini_cost import (
        check_gemini_daily_budget,
        extract_usage_detail,
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
    if synthesis_cache_kind is not None and synthesis_cache_system_text is None:
        logger.warning(
            "[gemini] synthesis_cache_kind without synthesis_cache_system_text — "
            "ignoring cache path",
        )
        synthesis_cache_kind = None
    if synthesis_cache_system_text is not None and synthesis_cache_kind is None:
        logger.warning(
            "[gemini] synthesis_cache_system_text without synthesis_cache_kind — "
            "ignoring cache path",
        )
        synthesis_cache_system_text = None

    # Merge static synthesis system text when call sites pass
    # ``synthesis_cache_kind`` + ``synthesis_cache_system_text``.
    # This runs regardless of ``GEMINI_SYNTHESIS_CONTEXT_CACHE``; that flag
    # only toggles ``cached_content`` vs ``system_instruction`` inside
    # ``_apply_synthesis_context_for_model`` (HI-8 Phase B optional).
    apply_synthesis_static_system = bool(
        synthesis_cache_kind
        and synthesis_cache_system_text
        and str(synthesis_cache_system_text).strip()
    )
    client = _get_client()

    if apply_synthesis_static_system:
        safe_cfg = _ensure_safety_settings(config)
        base_template = safe_cfg.model_copy(
            update={"system_instruction": None, "cached_content": None}
        )
    else:
        shared_config = _ensure_safety_settings(config)

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
                if apply_synthesis_static_system:
                    effective_config = _apply_synthesis_context_for_model(
                        client,
                        base_template,
                        kind=synthesis_cache_kind or "",
                        model=m,
                        system_text=synthesis_cache_system_text or "",
                    )
                else:
                    effective_config = shared_config
                kwargs: dict[str, Any] = {
                    "model": m,
                    "contents": contents,
                    "config": effective_config,
                }
                from getviews_pipeline import telemetry as _tel
                with _tel.span(
                    "gemini.generate_content",
                    model=m,
                    call_site=call_site,
                    attempt=attempt,
                ):
                    response = client.models.generate_content(**kwargs)
                duration_ms = int((time.monotonic() - started) * 1000)
                tokens_in, tokens_out, tcached = extract_usage_detail(response)
                used_ctx_cache = bool(getattr(effective_config, "cached_content", None))
                log_gemini_call(
                    user_id=user_id,
                    call_site=call_site,
                    model_name=m,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    duration_ms=duration_ms,
                    session_id=session_id,
                    used_context_cache=used_ctx_cache,
                    cached_content_token_count=tcached,
                    gcp_stt_cost_usd=gcp_stt_cost_usd,
                )
                return response
            except Exception as e:
                is_transient = _is_transient_gemini_error(e)
                is_last_attempt = attempt == len(_RETRY_DELAYS) - 1
                if not is_transient or is_last_attempt:
                    last_err = e
                    logger.warning(
                        "Gemini model %s attempt %d/%d failed: %s",
                        m,
                        attempt + 1,
                        len(_RETRY_DELAYS),
                        e,
                    )
                    break
                logger.info(
                    "Gemini model %s transient error (attempt %d/%d), retrying in %ds: %s",
                    m,
                    attempt + 1,
                    len(_RETRY_DELAYS),
                    delay,
                    e,
                )
                # ME-15: log each recoverable transient attempt as a zero-token
                # failure row so Cloud Logging / cost dashboards surface 503
                # bursts. Google bills input tokens on every attempt even on
                # error — the row marks the cost blind-spot without double-
                # counting (success row follows only on the winning attempt).
                try:
                    log_gemini_call(
                        user_id=user_id,
                        call_site=call_site,
                        model_name=m,
                        tokens_in=0,
                        tokens_out=0,
                        duration_ms=int((time.monotonic() - started) * 1000),
                        session_id=session_id,
                        success=False,
                        error_code=f"{type(e).__name__}_attempt_{attempt + 1}",
                    )
                except Exception:  # noqa: BLE001
                    pass
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
                gcp_stt_cost_usd=gcp_stt_cost_usd,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[gemini] log_gemini_failure crashed: %s", exc)
        raise last_err
    raise RuntimeError("No Gemini models available")


def analyze_video(
    video_path: Path,
    *,
    supplemental_user_prefix: str | None = None,
    gcp_stt_cost_usd: float | None = None,
) -> VideoAnalysis:
    """Run full forensic analysis on a local video file (sync).

    ``supplemental_user_prefix`` — optional Vietnamese text (e.g. HI-14 STT block)
    prepended to the extraction user turn. ``gcp_stt_cost_usd`` is recorded on
    the ``gemini_calls`` row for this extraction when set (fresh STT charge).
    """
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
    user_turn = build_video_extraction_user_turn_vi(
        dual_hook_window=GEMINI_HOOK_WINDOW_DUAL_PART,
        hook_window_seconds=max(
            0.5,
            min(10.0, float(GEMINI_HOOK_WINDOW_END_SEC)),
        ),
        base_fps_display=max(0.1, min(24.0, float(GEMINI_VIDEO_BASE_FPS))),
    )
    prefix = (supplemental_user_prefix or "").strip()
    if prefix:
        user_turn = prefix + "\n\n" + user_turn

    if size <= MAX_INLINE_SIZE_BYTES:
        data = path.read_bytes()
        video_parts = _build_video_extraction_content_parts(
            video_bytes=data,
            mime_type="video/mp4",
            file_resource=None,
        )
        response = _generate_content_models(
            [*video_parts, user_turn],
            primary_model=GEMINI_EXTRACTION_MODEL,
            fallbacks=GEMINI_EXTRACTION_FALLBACKS,
            config=json_cfg,
            call_site="video_extraction",
            gcp_stt_cost_usd=gcp_stt_cost_usd,
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
                [
                    *_build_video_extraction_content_parts(
                        video_bytes=None,
                        mime_type=getattr(info, "mime_type", None) or "video/mp4",
                        file_resource=info,
                    ),
                    user_turn,
                ],
                primary_model=GEMINI_EXTRACTION_MODEL,
                fallbacks=GEMINI_EXTRACTION_FALLBACKS,
                config=json_cfg,
                call_site="video_extraction_filesapi",
                gcp_stt_cost_usd=gcp_stt_cost_usd,
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
    if isinstance(parsed, dict):
        merge_lexicon_slang_into_video_analysis_dict(parsed)
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
    # HI-15 / HI-17: hook FPS + HI-14 STT supplement are video-only — carousels use
    # image Parts only (no ``video_metadata``, no spoken-audio ASR prefix).
    for p in parts:
        if isinstance(p, types.Part) and p.video_metadata is not None:
            raise AssertionError(
                "carousel extraction must not set Part.video_metadata (HI-15 is video-only)"
            )

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
    )

    response = _generate_content_models(
        [prompt],
        primary_model=model,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
        call_site="diagnosis_synthesis_v1",
        synthesis_cache_kind="diag_v1",
        synthesis_cache_system_text=sys_inst,
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


_EMBEDDED_TILE_MIN_PROXIMITY = 1
_EMBED_TILE_SECTION_IDS: frozenset[str] = frozenset(
    {"hook_analysis", "diagnosis", "niche_pattern", "distribution", "script_structure"},
)

# Bump when embedded-tile sanitize/inject contract changes (finalize-lite repair gate).
EMBED_CONTRACT_VERSION = 1


def count_valid_embedded_tiles(diagnosis_vi: dict[str, Any] | None) -> int:
    """Count tiles that survive BE display rules (aweme + url/thumb/caption)."""
    if not isinstance(diagnosis_vi, dict):
        return 0
    sections = diagnosis_vi.get("sections")
    if not isinstance(sections, list):
        return 0
    total = 0
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        tiles = sec.get("embedded_tiles")
        if not isinstance(tiles, list):
            continue
        for t in tiles:
            if not isinstance(t, dict):
                continue
            aid = str(t.get("aweme_id") or t.get("video_id") or "")
            if not aid:
                continue
            if t.get("video_url") or t.get("thumbnail_url") or t.get("caption_snippet"):
                total += 1
    return total


def repair_diagnosis_vi_embedded_tiles(
    diagnosis_vi: dict[str, Any],
    reference_videos: list[dict[str, Any]],
) -> int:
    """Re-run sanitize + fallback inject; return valid tile count after."""
    allowed = _allowed_aweme_ids(reference_videos)
    if not allowed or not reference_videos:
        return count_valid_embedded_tiles(diagnosis_vi)
    _sanitize_diagnosis_embedded_tiles(diagnosis_vi, reference_videos, allowed)
    return count_valid_embedded_tiles(diagnosis_vi)


def _reference_ids_with_content_proximity(
    reference_videos: list[dict[str, Any]],
) -> set[str]:
    """Aweme ids whose caption/hashtag overlap scored at least ``_EMBEDDED_TILE_MIN_PROXIMITY``."""
    out: set[str] = set()
    for r in reference_videos:
        aid = str(r.get("aweme_id") or r.get("video_id") or "")
        if not aid:
            continue
        score = int(r.get("content_proximity_score") or r.get("_proximity_score") or 0)
        if score >= _EMBEDDED_TILE_MIN_PROXIMITY:
            out.add(aid)
    return out


def _embed_allowed_for_tiles(
    reference_videos: list[dict[str, Any]],
    allowed_aweme: set[str],
) -> set[str]:
    """Aweme ids Gemini may resolve into ``embedded_tiles``.

    When any pool row has caption/hashtag overlap (score ≥ 1), only those ids are
    embeddable — blocks citing a high-ER but off-caption corpus row. When the whole
    pool scores 0 (common for same-niche peers with different hooks), the pool was
    already niche-filtered in ``select_synthesis_references_for_video`` — allow the
    top two ids by proximity then views so in-section evidence still renders.
    """
    relevant = _reference_ids_with_content_proximity(reference_videos)
    if relevant:
        return allowed_aweme & relevant

    scored: list[tuple[int, int, str]] = []
    for r in reference_videos:
        aid = str(r.get("aweme_id") or r.get("video_id") or "")
        if not aid or aid not in allowed_aweme:
            continue
        prox = int(r.get("content_proximity_score") or r.get("_proximity_score") or 0)
        views = int(r.get("views") or 0)
        scored.append((prox, views, aid))
    if not scored:
        return set()
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return {aid for _, _, aid in scored[:2]}


def _inject_fallback_embedded_tiles(
    diagnosis_vi: dict[str, Any],
    reference_videos: list[dict[str, Any]],
    embed_allowed: set[str],
) -> None:
    """When the pool is non-empty but Gemini left ``embedded_tiles`` blank, attach one peer."""
    from getviews_pipeline.diagnose_parse import resolve_embedded_tiles

    if not embed_allowed:
        return
    sections = diagnosis_vi.get("sections")
    if not isinstance(sections, list):
        return

    ranked = sorted(
        embed_allowed,
        key=lambda aid: -max(
            (
                int(
                    r.get("content_proximity_score") or r.get("_proximity_score") or 0
                )
                for r in reference_videos
                if str(r.get("aweme_id") or r.get("video_id") or "") == aid
            ),
            default=0,
        ),
    )
    by_sid: dict[str, dict[str, Any]] = {}
    for sec in sections:
        if isinstance(sec, dict):
            sid = str(sec.get("section_id") or "")
            if sid:
                by_sid[sid] = sec

    aid_idx = 0
    for sid in (
        "hook_analysis",
        "diagnosis",
        "niche_pattern",
        "distribution",
        "script_structure",
    ):
        if aid_idx >= len(ranked):
            break
        if sid not in _EMBED_TILE_SECTION_IDS:
            continue
        sec = by_sid.get(sid)
        if not sec:
            continue
        existing = sec.get("embedded_tiles")
        if isinstance(existing, list) and existing:
            continue
        aid = ranked[aid_idx]
        resolved = resolve_embedded_tiles([{"aweme_id": aid}], reference_videos)
        resolved = [
            t
            for t in resolved
            if t.get("aweme_id")
            and (t.get("video_url") or t.get("thumbnail_url") or t.get("caption_snippet"))
        ]
        if resolved:
            sec["embedded_tiles"] = resolved[:1]
            aid_idx += 1


def _strip_disallowed_embedded_tile_ids(
    diagnosis_vi: dict[str, Any],
    allowed_aweme: set[str],
) -> None:
    """Null ``aweme_id`` / ``video_id`` on tiles outside the synthesis pool (no resolve pass)."""
    sections = diagnosis_vi.get("sections")
    if not isinstance(sections, list):
        return
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        tiles = sec.get("embedded_tiles")
        if not isinstance(tiles, list):
            continue
        for t in tiles:
            if not isinstance(t, dict):
                continue
            for key in ("aweme_id", "video_id"):
                v = t.get(key)
                if v is not None and str(v) not in allowed_aweme:
                    t[key] = None


def _sanitize_diagnosis_embedded_tiles(
    diagnosis_vi: dict[str, Any],
    reference_videos: list[dict[str, Any]],
    allowed_aweme: set[str],
) -> None:
    """Resolve ``embedded_tiles`` from the reference pool only — drop hallucinated or off-topic ids."""
    from getviews_pipeline.diagnose_parse import resolve_embedded_tiles

    embed_allowed = _embed_allowed_for_tiles(reference_videos, allowed_aweme)

    sections = diagnosis_vi.get("sections")
    if not isinstance(sections, list):
        return

    for sec in sections:
        if not isinstance(sec, dict):
            continue
        raw_tiles = sec.get("embedded_tiles")
        if not isinstance(raw_tiles, list) or not raw_tiles:
            sec["embedded_tiles"] = []
            continue
        if not embed_allowed:
            sec["embedded_tiles"] = []
            continue

        hints: list[dict[str, Any]] = []
        for t in raw_tiles:
            if not isinstance(t, dict):
                continue
            aid = str(t.get("aweme_id") or t.get("video_id") or "").strip()
            if aid.isdigit() and aid in embed_allowed:
                hints.append({"aweme_id": aid})

        if not hints:
            sec["embedded_tiles"] = []
            continue

        by_prox: dict[str, int] = {}
        for r in reference_videos:
            rid = str(r.get("aweme_id") or r.get("video_id") or "")
            if rid:
                by_prox[rid] = int(
                    r.get("content_proximity_score") or r.get("_proximity_score") or 0
                )
        hints.sort(key=lambda h: -by_prox.get(str(h.get("aweme_id") or ""), 0))
        hints = hints[:2]

        resolved = resolve_embedded_tiles(hints, reference_videos)
        sec["embedded_tiles"] = [
            t
            for t in resolved
            if t.get("aweme_id")
            and (t.get("video_url") or t.get("thumbnail_url") or t.get("caption_snippet"))
        ]

    _inject_fallback_embedded_tiles(diagnosis_vi, reference_videos, embed_allowed)


def _validate_diagnosis_vi_citations(
    diagnosis_vi: dict[str, Any],
    allowed_aweme: set[str],
    reference_videos: list[dict[str, Any]] | None = None,
) -> None:
    """Mutate v6 ``diagnosis_vi`` in place: drop aweme citations outside ``allowed_aweme``.

    Mirrors ``_validate_narrative_citations`` for nested ``evidence_anchors`` and
    ``sections[].embedded_tiles`` — Gemini may invent ``aweme_id`` values in
    anchors (``type=aweme_id`` / numeric ``location``) or tile payloads.
    """
    anchors = diagnosis_vi.get("evidence_anchors")
    if isinstance(anchors, list):
        for a in anchors:
            if not isinstance(a, dict):
                continue
            typ = str(a.get("type") or "").lower().replace("-", "_")
            quote_raw = a.get("quote")
            quote_s = str(quote_raw).strip() if quote_raw is not None else ""
            loc_raw = a.get("location")
            loc_s = str(loc_raw).strip() if loc_raw is not None else ""

            def _strip_aweme_value(s: str) -> bool:
                """True if *s* looks like a bare aweme id and is not allowed."""
                if not s or not s.isdigit():
                    return False
                return s not in allowed_aweme

            if typ == "aweme_id":
                if _strip_aweme_value(quote_s):
                    a["quote"] = None
                if _strip_aweme_value(loc_s):
                    a["location"] = None
            else:
                # Model may still place a numeric aweme id in ``location``.
                if _strip_aweme_value(loc_s):
                    a["location"] = None
                if quote_s.isdigit() and len(quote_s) >= 12 and _strip_aweme_value(quote_s):
                    a["quote"] = None

    _strip_disallowed_embedded_tile_ids(diagnosis_vi, allowed_aweme)
    if reference_videos is not None:
        _sanitize_diagnosis_embedded_tiles(diagnosis_vi, reference_videos, allowed_aweme)


def _validate_narrative_citations(
    narrative_vi: dict[str, Any] | None,
    format_cards: list[dict[str, Any]] | None,
    allowed_aweme: set[str],
    reference_videos: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None]:
    if narrative_vi:
        diag = narrative_vi.get("diagnosis_vi")
        if isinstance(diag, dict):
            _validate_diagnosis_vi_citations(diag, allowed_aweme, reference_videos)
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


def _v6_section_body_and_narrative(
    diag_vi: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Build streaming markdown body + legacy narrative_vi fields from v6 ``diagnosis_vi``."""

    def _sec_txt(s: dict[str, Any]) -> str:
        return str(s.get("text_vi") or s.get("text") or "").strip()

    def _sec_tit(s: dict[str, Any]) -> str:
        return str(s.get("title_vi") or s.get("title") or "").strip()

    headline = str(diag_vi.get("headline_vi") or "").strip()
    sections = diag_vi.get("sections") or []
    body_parts: list[str] = []
    first_para = ""
    if isinstance(sections, list):
        for s in sections:
            if not isinstance(s, dict):
                continue
            sid = str(s.get("section_id") or "")
            tit = _sec_tit(s)
            txt = _sec_txt(s)
            if txt:
                if not first_para:
                    chunk = txt.split("\n\n")[0].strip()
                    first_para = chunk[:800]
                body_parts.append(f"### {tit or sid}\n\n{txt}")
    body_md = "\n\n".join(body_parts).strip()
    van_de = (first_para or headline or body_md)[:1200]
    ket_luan = headline if headline else (van_de[:280] if van_de else "—")
    if not ket_luan:
        ket_luan = "—"
    loi_narr: list[dict[str, Any]] = []
    if headline:
        loi_narr.append(
            {
                "error_id": "v6_summary",
                "narrative": headline,
                "evidence_aweme_id": None,
            }
        )
    narrative_vi: dict[str, Any] = {
        "_schema_version": "v6",
        "headline_vi": headline or ket_luan,
        "ket_luan_nhanh": ket_luan,
        "van_de_chinh": van_de or ket_luan,
        "loi_chinh_narrative": loi_narr,
        "diagnosis_vi": diag_vi,
        "dinh_huong_chien_luoc": "",
    }
    return body_md, narrative_vi


def _synthesize_diagnosis_v6_section_pool(
    content_format: str,
    niche_name: str,
    corpus_size: int,
    niche_meta: dict[str, Any],
    reference_videos: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    collapsed_questions: list[str] | None,
    wants_directions: bool,
    layer0_context: str,
    corpus_citation: str,
    persona_block: str,
    *,
    performance_tier: str,
    channel_context: dict[str, Any] | None,
    errors: list[dict[str, Any]] | None,
    reference_evidence_block: str,
    creator_format_history_block: str,
    cross_format_signal: dict[str, Any] | None = None,
    niche_posting_context_block: str = "",
    analysis_depth: str = "basic",
) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]] | None]:
    """Section-pool diagnosis: signals → section pick list → JSON-first v6 prompt."""
    from getviews_pipeline.compliance import collect_compliance_flags
    from getviews_pipeline.diagnose_prompts import build_diagnosis_v6_user_prompt
    from getviews_pipeline.diagnose_sections import select_sections_to_emit
    from getviews_pipeline.diagnosis_quality import score_diagnosis_output_v6
    from getviews_pipeline.signals.registry import (
        build_diagnosis_ctx,
        build_signal_manifest,
        manifest_for_prompt,
    )

    allowed = _allowed_aweme_ids(reference_videos)
    ctx_dict = build_diagnosis_ctx(
        user_analysis=user_analysis,
        user_stats=user_stats,
        reference_videos=reference_videos,
        channel_context=channel_context,
        performance_tier=performance_tier,
        niche_meta=niche_meta,
        compliance_flags=collect_compliance_flags(user_analysis, user_stats),
        content_format=content_format,
        niche_name=niche_name,
        corpus_size=corpus_size,
    )
    manifest = build_signal_manifest(ctx_dict)
    depth = "basic" if analysis_depth == "basic" else "deep"
    sections_ordered = select_sections_to_emit(manifest, ctx_dict, depth=depth)
    manifest_trim = manifest_for_prompt(manifest, depth=depth)

    model = GEMINI_DIAGNOSIS_MODEL or GEMINI_SYNTHESIS_MODEL
    sys_inst = build_voice_domain_system_instruction(include_diagnosis_examples=True)
    user_prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=sections_ordered,
        manifest_for_llm=manifest_trim,
        ctx=ctx_dict,
        content_format=content_format,
        niche_name=niche_name,
        corpus_size=corpus_size,
        reference_videos=reference_videos,
        user_analysis=user_analysis,
        user_stats=user_stats,
        performance_tier=performance_tier,
        channel_context=channel_context,
        errors=errors,
        wants_directions=wants_directions,
        corpus_citation=corpus_citation,
        persona_block=persona_block,
        reference_evidence_block=reference_evidence_block,
        collapsed_questions=collapsed_questions,
        cross_format_signal=cross_format_signal,
        niche_posting_context_block=niche_posting_context_block,
    )
    prompt = _prefix_user_sections(
        [layer0_context or "", creator_format_history_block or ""],
        user_prompt,
    )

    max_tokens = 8192 if wants_directions else 6000
    cfg = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=max_tokens,
    )
    response = _generate_content_models(
        [prompt],
        primary_model=model,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
        call_site="diagnosis_synthesis_v6_section_pool",
        synthesis_cache_kind="diag_v6",
        synthesis_cache_system_text=sys_inst,
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("synthesize_diagnosis_v6_section_pool returned empty response")

    raw_obj, remainder = _split_diagnosis_leading_json(text)
    narrative_vi: dict[str, Any] | None = None
    format_cards: list[dict[str, Any]] | None = None
    body = ""

    if raw_obj:
        diag_vi = raw_obj.get("diagnosis_vi")
        if isinstance(diag_vi, dict):
            body, narrative_vi = _v6_section_body_and_narrative(diag_vi)
            fc = raw_obj.get("format_cards")
            format_cards = fc if isinstance(fc, list) else None
            narrative_vi, format_cards = _validate_narrative_citations(
                narrative_vi, format_cards, allowed, reference_videos
            )
            narrative_vi = _normalize_narrative_vi_dict(narrative_vi)
            q = score_diagnosis_output_v6(
                diag_vi, section_ids_expected=sections_ordered
            )
            logger.debug(
                "[diagnosis_v6] quality footprint sections=%s scores=%s",
                sections_ordered,
                q,
            )
            if not body.strip():
                body = remainder.strip()
        else:
            nv = raw_obj.get("narrative_vi")
            fc = raw_obj.get("format_cards")
            narrative_vi = nv if isinstance(nv, dict) else None
            format_cards = fc if isinstance(fc, list) else None
            narrative_vi, format_cards = _validate_narrative_citations(
                narrative_vi, format_cards, allowed, reference_videos
            )
            narrative_vi = _normalize_narrative_vi_dict(narrative_vi)
            body = remainder.strip()
    else:
        body = text.strip()

    scan_target = body if raw_obj else text.strip()
    try:
        from getviews_pipeline.analysis_guards import (
            scan_synthesis_for_fabricated_metrics,
        )

        scan = scan_synthesis_for_fabricated_metrics(scan_target)
        if not scan.clean:
            logger.warning(
                "[synthesis_guard] possible fabricated metric(s) in diagnosis_v6 output: %s",
                scan.flags,
            )
    except Exception as exc:  # pragma: no cover — pure helper
        logger.warning("[synthesis_guard] scan failed: %s", exc)
    return body, narrative_vi, format_cards


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
    creator_format_history_block: str = "",
    cross_format_signal: dict[str, Any] | None = None,
    niche_posting_context_block: str = "",
    analysis_depth: str = "basic",
) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]] | None]:
    """V2 narrative diagnosis — Markdown body plus optional structured narrative/format cards."""

    if GETVIEWS_DIAGNOSIS_SECTION_MODE:
        return _synthesize_diagnosis_v6_section_pool(
            content_format,
            niche_name,
            corpus_size,
            niche_meta,
            reference_videos,
            user_analysis,
            user_stats,
            collapsed_questions,
            wants_directions,
            layer0_context,
            corpus_citation,
            persona_block,
            performance_tier=performance_tier,
            channel_context=channel_context,
            errors=errors,
            reference_evidence_block=reference_evidence_block,
            creator_format_history_block=creator_format_history_block,
            cross_format_signal=cross_format_signal,
            niche_posting_context_block=niche_posting_context_block,
            analysis_depth=analysis_depth,
        )

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
    prompt = _prefix_user_sections(
        [layer0_context or "", creator_format_history_block or "", niche_posting_context_block or ""],
        prompt,
    )
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
    )
    response = _generate_content_models(
        [prompt],
        primary_model=model,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
        call_site="diagnosis_synthesis_v2",
        synthesis_cache_kind="diag_v2",
        synthesis_cache_system_text=sys_inst,
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
            narrative_vi, format_cards, allowed, reference_videos
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
    niche_posting_context_block: str = "",
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
        [
            layer0_context or "",
            creator_format_history_block or "",
            niche_posting_context_block or "",
        ],
        prompt,
    )
    if (niche_posting_context_block or "").strip():
        prompt = (
            prompt.rstrip()
            + "\n\nNếu có khối bắt đầu bằng NICHE_POSTING_CONTEXT phía trên: nhúng vào "
            "**TẦNG 1 — PHÂN PHỐI** (ưu tiên PHẦN 1B — phân phối carousel này); "
            "không mở mục “khung giờ đăng” hay timing riêng.\n"
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
    )
    response = _generate_content_models(
        [prompt],
        primary_model=model,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
        call_site="carousel_diagnosis_v2",
        synthesis_cache_kind="diag_carousel_v2",
        synthesis_cache_system_text=sys_inst,
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
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=cfg,
        call_site="intent_markdown",
        synthesis_cache_kind="intent_markdown",
        synthesis_cache_system_text=sys_inst,
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


def upload_local_video_file_active(video_path: Path) -> Any:
    """Upload a local video to the Files API and block until ACTIVE.

    Caller deletes the remote object with ``client.files.delete`` when done.
    """
    client = _get_client()
    uploaded = client.files.upload(file=str(video_path.resolve()))
    name = uploaded.name
    info = uploaded
    deadline = time.monotonic() + FILES_API_POLL_TIMEOUT_SEC
    delay = FILES_API_POLL_INITIAL_SEC
    while True:
        info = client.files.get(name=name)
        state = getattr(info.state, "name", None) or str(info.state)
        if state == "ACTIVE":
            return info
        if state == "FAILED":
            raise RuntimeError(f"Gemini file processing failed: {name}")
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Gemini file never became ACTIVE within "
                f"{FILES_API_POLL_TIMEOUT_SEC:.0f}s (last state={state})"
            )
        time.sleep(delay)
        delay = min(delay * 1.5, FILES_API_POLL_MAX_SEC)


def build_video_corpus_batch_jsonl_record(
    video_id: str,
    file_resource: Any,
    *,
    supplemental_user_prefix: str | None = None,
) -> dict[str, Any]:
    """One Batch API JSONL object: ``{\"key\", \"request\"}`` (file source)."""
    client = _get_client()
    sys_inst = build_video_extraction_system_instruction()
    json_cfg = _configure_extraction_generate_config(
        client,
        VideoAnalysis.model_json_schema(),
        kind="video",
        system_text=sys_inst,
    )
    json_cfg = _ensure_safety_settings(json_cfg)
    config_dict = json_cfg.model_dump(mode="json", exclude_none=True)

    mime = getattr(file_resource, "mime_type", None) or "video/mp4"
    video_parts = _build_video_extraction_content_parts(
        video_bytes=None,
        mime_type=mime,
        file_resource=file_resource,
    )
    user_turn = build_video_extraction_user_turn_vi(
        dual_hook_window=GEMINI_HOOK_WINDOW_DUAL_PART,
        hook_window_seconds=max(
            0.5,
            min(10.0, float(GEMINI_HOOK_WINDOW_END_SEC)),
        ),
        base_fps_display=max(0.1, min(24.0, float(GEMINI_VIDEO_BASE_FPS))),
    )
    prefix = (supplemental_user_prefix or "").strip()
    if prefix:
        user_turn = prefix + "\n\n" + user_turn

    part_dicts = [p.model_dump(mode="json", exclude_none=True) for p in video_parts]
    part_dicts.append({"text": user_turn})
    request_body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": part_dicts}],
        "config": config_dict,
    }
    return {"key": video_id, "request": request_body}


def _usage_from_batch_response_dict(resp: dict[str, Any]) -> tuple[int, int, int]:
    um = resp.get("usageMetadata") or resp.get("usage_metadata") or {}
    if not isinstance(um, dict):
        return (0, 0, 0)
    tin = int(um.get("promptTokenCount") or um.get("prompt_token_count") or 0)
    tout = int(
        um.get("candidatesTokenCount") or um.get("candidates_token_count") or 0
    )
    tthought = int(
        um.get("thoughtsTokenCount") or um.get("thoughts_token_count") or 0
    )
    tcached = int(
        um.get("cachedContentTokenCount") or um.get("cached_content_token_count") or 0
    )
    return (tin, tout + tthought, tcached)


def _text_from_batch_response_dict(resp: dict[str, Any]) -> str:
    cands = resp.get("candidates") or []
    if not cands:
        return ""
    content = (cands[0] or {}).get("content") or {}
    parts = content.get("parts") or []
    texts: list[str] = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        t = p.get("text")
        if t:
            texts.append(str(t))
    return "\n".join(texts)


def parse_batch_extraction_analysis_json(text: str) -> dict[str, Any]:
    """Parse ``VideoAnalysis`` JSON from a batch result line (markdown fences OK)."""
    parsed = _parse_json_object(text)
    if not isinstance(parsed, dict):
        raise ValueError("batch extraction response must be a JSON object")
    return parsed


def _batch_job_state_name(job: Any) -> str:
    st = job.state
    return getattr(st, "name", None) or str(st)


def _batch_stats_dict(job: Any) -> dict[str, int]:
    """Best-effort ``batchStats`` from a completed batch job object."""
    raw = getattr(job, "batch_stats", None)
    if raw is None:
        return {}
    out: dict[str, int] = {}
    for key in ("request_count", "successful_request_count", "failed_request_count"):
        if isinstance(raw, dict):
            val = raw.get(key)
        else:
            val = getattr(raw, key, None)
        if val is None:
            continue
        try:
            out[key] = int(val)
        except (TypeError, ValueError):
            continue
    return out


def _log_batch_job_stats(job: Any, *, display_name: str, n_records: int) -> None:
    stats = _batch_stats_dict(job)
    if not stats:
        return
    logger.info(
        "[gemini] corpus extraction batch stats display_name=%s n_records=%d "
        "request_count=%s successful_request_count=%s failed_request_count=%s",
        display_name,
        n_records,
        stats.get("request_count"),
        stats.get("successful_request_count"),
        stats.get("failed_request_count"),
        extra={"event": "gemini_batch_stats", "display_name": display_name, **stats},
    )


def _cancel_batch_job_best_effort(client: Any, job_name: str) -> None:
    try:
        client.batches.cancel(name=job_name)
        logger.info("[gemini] batch cancel requested name=%s", job_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[gemini] batch cancel failed name=%s: %s", job_name, exc)


def _parse_batch_output_jsonl_line(
    line_obj: dict[str, Any],
) -> tuple[str | None, str | None, str | None, int, int, int]:
    """``(..., tokens_in, tokens_out, cached_content_token_count)`` per results line."""
    raw_key = line_obj.get("key")
    key = str(raw_key) if raw_key is not None else None
    err = line_obj.get("error")
    if err is not None:
        return key, None, str(err), 0, 0, 0
    resp = line_obj.get("response")
    if not isinstance(resp, dict):
        return key, None, "missing_response", 0, 0, 0
    tin, tout, tcached = _usage_from_batch_response_dict(resp)
    text = _text_from_batch_response_dict(resp)
    if not text.strip():
        return key, None, "empty_response_text", tin, tout, tcached
    return key, text, None, tin, tout, tcached


def run_corpus_extraction_batch_file_job(
    *,
    records: list[dict[str, Any]],
    display_name: str,
    poll_interval_s: float,
    poll_max_s: float,
    gemini_file_names: list[str],
    gcp_stt_cost_by_video_id: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    """Submit JSONL (File API), poll, map per-key results, log ``gemini_calls``.

    On poll timeout, requests batch cancel and **does not** delete uploaded
    video Files until the job reaches a terminal state (avoids breaking an
    in-flight batch). JSONL input file is always deleted best-effort.
    """
    from getviews_pipeline.gemini_cost import log_gemini_call

    if not records:
        return {"ok": True, "state": "JOB_STATE_SUCCEEDED", "by_video_id": {}}

    client = _get_client()
    stt_map = gcp_stt_cost_by_video_id or {}
    job_name: str | None = None
    job_terminal = False
    uploaded_jsonl = None
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".jsonl",
        prefix="gv-corpus-batch-",
        delete=False,
        encoding="utf-8",
    )
    tmp_path = Path(tmp.name)
    try:
        for rec in records:
            tmp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tmp.close()

        uploaded_jsonl = client.files.upload(
            file=str(tmp_path),
            config=types.UploadFileConfig(
                display_name=f"{display_name}-requests",
                mime_type="jsonl",
            ),
        )
        batch_job = client.batches.create(
            model=GEMINI_EXTRACTION_MODEL,
            src=uploaded_jsonl.name,
            config={"display_name": display_name},
        )
        req0 = records[0].get("request") if records else None
        cfg0 = (req0 or {}).get("config") if isinstance(req0, dict) else None
        cc_ref = None
        if isinstance(cfg0, dict):
            cc_ref = cfg0.get("cached_content") or cfg0.get("cachedContent")
        logger.info(
            "[gemini] corpus extraction batch submitted",
            extra={
                "event": "gemini_batch_submit",
                "display_name": display_name,
                "batch_job_name": getattr(batch_job, "name", None),
                "model_name": GEMINI_EXTRACTION_MODEL,
                "n_records": len(records),
                "used_context_cache": bool(cc_ref),
                "context_cache_name": cc_ref,
            },
        )
        job_name = batch_job.name
        if not job_name:
            return {
                "ok": False,
                "state": "JOB_STATE_FAILED",
                "by_video_id": {},
                "job_error": "batch job missing name",
            }

        deadline = time.monotonic() + poll_max_s
        job = batch_job
        state_name = _batch_job_state_name(job)
        while time.monotonic() < deadline:
            job = client.batches.get(name=job_name)
            state_name = _batch_job_state_name(job)
            if state_name in _BATCH_TERMINAL_STATES:
                job_terminal = True
                break
            time.sleep(max(1.0, poll_interval_s))
        else:
            job = client.batches.get(name=job_name)
            state_name = _batch_job_state_name(job)

        if not job_terminal:
            _cancel_batch_job_best_effort(client, job_name)
            job = client.batches.get(name=job_name)
            state_name = _batch_job_state_name(job)
            job_terminal = state_name in _BATCH_TERMINAL_STATES

        _log_batch_job_stats(job, display_name=display_name, n_records=len(records))

        by_video_id: dict[str, dict[str, Any]] = {}

        if not job_terminal:
            logger.warning(
                "[gemini] batch poll timeout — job not terminal; "
                "keeping Files API video uploads name=%s state=%s",
                job_name,
                state_name,
            )
            return {
                "ok": False,
                "state": state_name,
                "by_video_id": by_video_id,
                "job_error": "poll_timeout_or_stuck",
                "batch_stats": _batch_stats_dict(job),
            }

        if state_name != "JOB_STATE_SUCCEEDED":
            err_msg = None
            if hasattr(job, "error") and job.error:
                err_msg = str(job.error)
            return {
                "ok": False,
                "state": state_name,
                "by_video_id": by_video_id,
                "job_error": err_msg or state_name,
                "batch_stats": _batch_stats_dict(job),
            }

        dest = job.dest
        result_file = getattr(dest, "file_name", None) if dest else None
        if not result_file:
            return {
                "ok": False,
                "state": state_name,
                "by_video_id": {},
                "job_error": "batch succeeded but no result file",
            }

        raw_bytes = client.files.download(file=result_file)
        body = raw_bytes.decode("utf-8")
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            vid_k, resp_text, err_k, tin, tout, tcached = _parse_batch_output_jsonl_line(obj)
            if not vid_k:
                continue
            if err_k or not resp_text:
                by_video_id[vid_k] = {
                    "ok": False,
                    "error": err_k or "no_text",
                    "tokens_in": tin,
                    "tokens_out": tout,
                    "cached_content_token_count": tcached,
                }
                continue
            by_video_id[vid_k] = {
                "ok": True,
                "text": resp_text,
                "tokens_in": tin,
                "tokens_out": tout,
                "cached_content_token_count": tcached,
            }
            stt_usd = stt_map.get(vid_k)
            log_gemini_call(
                user_id=None,
                call_site="video_extraction_batch",
                model_name=GEMINI_EXTRACTION_MODEL,
                tokens_in=tin,
                tokens_out=tout,
                duration_ms=0,
                used_context_cache=bool(cc_ref) or tcached > 0,
                cached_content_token_count=tcached,
                gcp_stt_cost_usd=stt_usd,
                is_batch=True,
            )

        line_ok = sum(1 for v in by_video_id.values() if v.get("ok"))
        line_fail = len(by_video_id) - line_ok
        stats = _batch_stats_dict(job)
        logger.info(
            "[gemini] corpus extraction batch complete display_name=%s "
            "line_ok=%d line_fail=%d n_records=%d",
            display_name,
            line_ok,
            line_fail,
            len(records),
            extra={
                "event": "gemini_batch_complete",
                "display_name": display_name,
                "line_ok": line_ok,
                "line_fail": line_fail,
                **stats,
            },
        )
        return {
            "ok": True,
            "state": state_name,
            "by_video_id": by_video_id,
            "batch_stats": stats,
        }
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        if job_terminal:
            for fname in gemini_file_names:
                if not fname:
                    continue
                try:
                    client.files.delete(name=fname)
                except Exception:
                    pass
        elif gemini_file_names:
            logger.warning(
                "[gemini] skipping Files API video delete — batch job not terminal "
                "(name=%s)",
                job_name,
            )
        if uploaded_jsonl is not None:
            try:
                client.files.delete(name=uploaded_jsonl.name)
            except Exception:
                pass
