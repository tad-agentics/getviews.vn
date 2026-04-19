"""GetViews.vn Cloud Run — FastAPI entry point.

Routes are implemented here as the pipeline grows. This file is the HTTP
boundary between the Vercel frontend/Edge Functions and the Python analysis
pipeline.

JWT validation: Supabase uses ES256 (asymmetric). We validate via JWKS endpoint
— stateless, no shared secret, keys rotatable without redeployment.
JWKS URL: https://lzhiqnxfveqttsujebiv.supabase.co/auth/v1/.well-known/jwks.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import AliasChoices, BaseModel, Field

from getviews_pipeline.config import (
    ENSEMBLEDATA_API_TOKEN,
    GEMINI_API_KEY,
    SUPABASE_JWKS_URL,
    SUPABASE_JWT_SECRET,
)
from getviews_pipeline.gemini import classify_intent_gemini, gemini_text_only
from getviews_pipeline.intents import (
    extract_urls_and_handles,
    split_into_questions,
)
from getviews_pipeline.helpers import infer_niche_from_hashtags
from getviews_pipeline.pipelines import (
    run_brief_generation,
    run_competitor_profile,
    run_content_directions,
    run_creator_search,
    run_own_channel,
    run_shot_list,
    run_trend_spike,
    run_video_diagnosis,
)
from getviews_pipeline.runtime import run_sync
from getviews_pipeline.session_store import (
    build_session_context_from_db,
    get_stream_chunks,
    put_stream_chunks,
)
from getviews_pipeline.supabase_client import user_supabase

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

_PROFILE_HANDLE_RE = re.compile(r"tiktok\.com/@([a-zA-Z0-9_.]+)", re.IGNORECASE)


def _normalize_intent_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    # All KOL-finder aliases resolve to the single seller-first creator_search
    # pipeline. find_creators / kol_search / kol_finder survive only so old
    # clients / cached chat rows keep working.
    aliases = {
        "tiktok_url_diagnosis": "video_diagnosis",
        "kol_search": "creator_search",
        "find_creators": "creator_search",
        "kol_finder": "creator_search",
        "followup": "follow_up",
    }
    return aliases.get(raw, raw)


def is_free_intent(intent: str) -> bool:
    # Free intents match the Vercel Edge FREE_INTENTS set (api/chat.ts:24) so
    # the two gates agree. `creator_search` is the unified KOL finder (formerly
    # kol_search / find_creators — aliased above).
    return intent in ("trend_spike", "creator_search")


# §13 mandate: max 100 free queries per user per day for abuse prevention
FREE_DAILY_LIMIT = 100
# Intents that consume from the daily free quota (not the deep-credit pool)
_FREE_GATED_INTENTS = frozenset({"trend_spike", "creator_search"})


def _resolve_profile_handle(urls: list[str], handles: list[str]) -> str:
    if handles:
        return handles[0].lstrip("@")
    for u in urls:
        m = _PROFILE_HANDLE_RE.search(u)
        if m:
            return m.group(1)
    raise ValueError("Thiếu @handle hoặc URL profile TikTok hợp lệ.")


_SHORT_TIKTOK_HOSTS = {"vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com"}


def _is_short_tiktok_url(url: str) -> bool:
    from urllib.parse import urlparse
    try:
        return urlparse(url).netloc.lower() in _SHORT_TIKTOK_HOSTS
    except Exception:
        return False


def _resolve_short_url(url: str, timeout: float = 8.0) -> str:
    """Follow redirects on a short TikTok URL and return the final URL.
    Falls back to the original URL on any error."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.head(url, headers={"User-Agent": "Mozilla/5.0"})
            final = str(resp.url)
            logger.info("[short_url] resolved %s → %s", url, final)
            return final
    except Exception as exc:
        logger.warning("[short_url] could not resolve %s: %s — using original", url, exc)
        return url


def _pick_video_url(urls: list[str]) -> str | None:
    for u in urls:
        ul = u.lower()
        if "/video/" in ul or "/photo/" in ul or _is_short_tiktok_url(u):
            return u
    return urls[0] if urls else None


def _infer_niche_from_query(query: str) -> str:
    """Best-effort niche from free-text query when session has no niche yet.

    Tries the taxonomy-backed matcher first so prose like
    "review đồ skincare Hàn Quốc cho da dầu mụn" resolves to the canonical
    niche label ("làm đẹp" / "skincare") rather than the raw first 40 chars,
    which downstream fails to match niche_taxonomy and drops the corpus
    into all-niches fallback (off-domain references).
    """
    try:
        from getviews_pipeline.corpus_context import _anon_client
        from getviews_pipeline.niche_match import find_niche_match

        match = find_niche_match(_anon_client(), query)
        if match is not None:
            return match.label
    except Exception:
        # Any import/query failure falls through to the legacy hashtag/desc path.
        pass
    return infer_niche_from_hashtags([], query) or "tiktok"


def _chunk_text(text: str, size: int = 20) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


def _sse_line(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def _classify_stream_error(exc: BaseException) -> str:
    """Map known exceptions to frontend-readable error codes.

    These codes are handled by useChatStream.ts lines 109-111.
    Called only AFTER the SSE stream has opened — do not raise, just return a code.
    """
    msg = str(exc).lower()
    if isinstance(exc, asyncio.TimeoutError):
        return "analysis_timeout"
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 403:
        return "video_download_failed"
    if "unit limit" in msg or "daily unit limit" in msg:
        return "ensembledata_quota"
    # Gemini SDK exceptions live under google.genai or google.generativeai namespaces
    exc_module = type(exc).__module__ or ""
    if exc_module.startswith("google"):
        return "gemini_error"
    return "stream_failed"


class StreamRequest(BaseModel):
    session_id: str
    query: str
    intent_type: str | None = None
    niche_id: int | None = None
    resume_stream_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("resume_stream_id", "stream_id"),
    )
    last_seq: int | None = None


def _insert_chat_message_best_effort(
    *,
    supabase: Any,
    session_id: str,
    user_id: str,
    content: str,
    structured_output: dict[str, Any] | None,
    intent_type: str,
    stream_id: str,
) -> None:
    """Insert the assistant message via RLS-scoped client (non-fatal on failure)."""
    try:
        supabase.table("chat_messages").insert(
            {
                "session_id": session_id,
                "user_id": user_id,
                "role": "assistant",
                "content": content,
                "structured_output": structured_output,
                "intent_type": intent_type,
                "is_free": is_free_intent(intent_type),
                "credits_used": 0 if is_free_intent(intent_type) else 1,
                "stream_id": stream_id,
            }
        ).execute()
    except Exception as exc:
        logger.warning("Supabase chat_messages insert failed (non-fatal): %s", exc)

app = FastAPI(title="GetViews Pipeline", version="0.1.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
# Use allow_origin_regex only — FastAPI CORSMiddleware does not support wildcard
# subdomains in allow_origins. The regex covers production, Vercel previews, and
# local dev on any port.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|https://(www\.)?getviews\.vn|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Global error handler ──────────────────────────────────────────────────────
# Catches unhandled errors BEFORE the response body is opened (e.g. route lookup,
# middleware, dependency injection). Errors that occur DURING an open SSE stream
# cannot change the HTTP status — they are sent as error SSE tokens instead.

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        # Let FastAPI's default handler format 4xx/5xx HTTPExceptions correctly
        return await http_exception_handler(request, exc)
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)},
    )


# ── JWKS cache (refresh at most every 10 minutes) ─────────────────────────────

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 600  # seconds


async def _get_jwks() -> dict[str, Any]:
    global _jwks_cache, _jwks_fetched_at
    now = time.monotonic()
    if not _jwks_cache or now - _jwks_fetched_at > _JWKS_TTL:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(SUPABASE_JWKS_URL)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_fetched_at = now
    return _jwks_cache


# ── JWT dependency ─────────────────────────────────────────────────────────────

async def require_user(request: Request) -> dict[str, Any]:
    """Validate Supabase JWT from Authorization: Bearer header.

    Supports ES256 via JWKS (primary) with HS256 fallback if SUPABASE_JWT_SECRET is set.
    Returns the decoded JWT payload (contains 'sub' = user UUID) plus the raw token
    so callers can build a user-scoped Supabase client via user_supabase(access_token).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")

    token = auth_header[7:]

    # Decode the token header to detect algorithm before attempting verification
    try:
        unverified_header = jwt.get_unverified_header(token)
        token_alg = unverified_header.get("alg", "")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

    try:
        if token_alg == "HS256" and SUPABASE_JWT_SECRET:
            # HS256 via shared secret (legacy / service tokens)
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False, "leeway": 30},
            )
        else:
            # ES256 via JWKS — this project signs user JWTs with ES256 (asymmetric)
            jwks = await _get_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["ES256"],
                options={"verify_aud": False, "leeway": 30},
            )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No sub in token")

    # Include raw token so /stream can build a user-scoped (RLS-aware) Supabase client
    return {"user_id": user_id, "payload": payload, "access_token": token}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> JSONResponse:
    from getviews_pipeline.r2 import r2_configured
    checks = {
        "gemini_key_set": bool(GEMINI_API_KEY),
        "ensemble_key_set": bool(ENSEMBLEDATA_API_TOKEN),
        "jwt_configured": bool(SUPABASE_JWT_SECRET) or bool(SUPABASE_JWKS_URL),
        "cdn_proxy_set": bool(os.environ.get("RESIDENTIAL_PROXY_URL")),
        "r2_configured": r2_configured(),
    }
    # cdn_proxy_set and r2_configured are optional — don't affect health status
    required = {k: v for k, v in checks.items() if k not in ("cdn_proxy_set", "r2_configured")}
    ok = all(required.values())
    return JSONResponse(
        {"status": "ok" if ok else "degraded", "checks": checks},
        status_code=200 if ok else 503,
    )


@app.get("/auth-check")
async def auth_check(user: dict = Depends(require_user)) -> JSONResponse:
    """Smoke-test endpoint — returns user_id if JWT is valid."""
    return JSONResponse({"ok": True, "user_id": user["user_id"]})


class ClassifyIntentRequest(BaseModel):
    query: str


@app.post("/classify-intent")
async def classify_intent_endpoint(
    body: ClassifyIntentRequest,
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Tier-3 semantic intent classification — no credit cost.

    Called by the frontend when tiers 1+2 (structural + keyword) produce a
    low-confidence result (falls through to follow_up with no prior context).
    Returns primary intent, optional secondary intent, and a niche hint.

    Response: {"primary": str, "secondary": str|null, "niche_hint": str|null}
    """
    urls, handles = extract_urls_and_handles(body.query)
    result = await run_sync(
        classify_intent_gemini,
        body.query,
        has_url=bool(urls),
        has_handle=bool(handles),
    )
    return JSONResponse(result)


@app.post("/stream")
async def stream(
    request: Request,
    body: StreamRequest,
    user: dict = Depends(require_user),
) -> StreamingResponse:
    """SSE token stream for video analysis pipeline.

    Only handles the three intents the frontend routes to Cloud Run:
      - video_diagnosis  → run_video_diagnosis (EnsembleData + Gemini multimodal)
      - competitor_profile → run_competitor_profile
      - own_channel      → run_video_diagnosis (user's own video URL — same pipeline)
                           NOTE: own_channel is not in QueryIntent; treated as video_diagnosis.

    All other intents (brief_generation, trend_spike, etc.) go to Vercel Edge /api/chat.

    Credit gate (mirrors api/chat.ts lines 82-96):
      1. Mark is_processing = true before calling pipeline
      2. decrement_credit RPC — returns 402 if balance is zero
      3. Mark is_processing = false after streaming finishes (in generator)

    Uses user_supabase() (anon key + user JWT) so RLS applies correctly.
    """
    user_id: str = user["user_id"]
    access_token: str = user["access_token"]

    # ── Credit gate (pre-flight, before opening the SSE stream) ──────────────
    # Build user-scoped client here so we can return 402 synchronously before
    # streaming starts. The same client is passed into the generator for cleanup.
    sb = user_supabase(access_token)

    try:
        sb.table("profiles").update({"is_processing": True}).eq("id", user_id).execute()
        rpc_resp = sb.rpc("decrement_credit", {"p_user_id": user_id}).execute()
        # decrement_credit returns false (or raises) when balance is zero
        if rpc_resp.data is False:
            sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={"error": "insufficient_credits"},
            )
    except Exception as exc:
        logger.warning("Credit deduction failed: %s", exc)
        sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={"error": "insufficient_credits"},
        )

    # ── Resolve intent ────────────────────────────────────────────────────────
    # Tier 1+2: frontend keyword classification result arrives as intent_type.
    # Tier 3 (backend safety net): only fires when intent_type is completely absent
    # (null/empty). follow_up is intentional — frontend routes it to Vercel or
    # calls /classify-intent first — do NOT reclassify it server-side.
    _raw_intent = _normalize_intent_name(body.intent_type)
    if not _raw_intent:
        _t3_urls, _t3_handles = extract_urls_and_handles(body.query)
        _t3 = await run_sync(
            classify_intent_gemini,
            body.query,
            has_url=bool(_t3_urls),
            has_handle=bool(_t3_handles),
        )
        normalized = _t3["primary"]
        logger.info("[stream] tier-3 classification (null intent): %s (secondary=%s)", normalized, _t3.get("secondary"))
    else:
        normalized = _raw_intent

    async def event_generator() -> AsyncIterator[bytes]:
        stream_id = body.resume_stream_id or str(uuid.uuid4())
        seq = body.last_seq or 0

        try:
            # ── Resume: replay cached chunks the client already missed ────────
            if body.resume_stream_id and body.last_seq is not None:
                cached = get_stream_chunks(body.resume_stream_id)
                if cached:
                    for i, chunk in enumerate(cached, start=1):
                        if i <= body.last_seq:
                            continue
                        seq = i
                        yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": chunk, "done": False})
                        await asyncio.sleep(0.005)
                    seq += 1
                    yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True})
                    sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
                    return

            # ── Free-intent daily abuse gate ──────────────────────────────────
            if normalized in _FREE_GATED_INTENTS:
                try:
                    gate_result = sb.rpc("increment_free_query_count", {"p_user_id": user_id}).execute()
                    new_count = (gate_result.data or {}).get("new_count", 0)
                    if new_count > FREE_DAILY_LIMIT:
                        seq += 1
                        yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True, "error": "daily_free_limit"})
                        sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
                        return
                except Exception as gate_exc:
                    logger.warning("[stream] free query count gate failed (fail-open): %s", gate_exc)

            # ── Run pipeline (with step events) ───────────────────────────────
            session = build_session_context_from_db(body.session_id, sb)
            urls, handles = extract_urls_and_handles(body.query)
            questions = split_into_questions(body.query)

            step_q: asyncio.Queue[dict | None] = asyncio.Queue()

            if normalized == "video_diagnosis":
                url = _pick_video_url(urls)
                if not url:
                    seq += 1
                    yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True, "error": "missing_video_url"})
                    sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
                    return
                # Resolve short URLs (vt.tiktok.com, vm.tiktok.com) to full URLs before
                # passing to EnsembleData — the API requires /video/ or /photo/ path.
                if _is_short_tiktok_url(url):
                    url = await run_sync(_resolve_short_url, url)
                pipeline_coro = run_video_diagnosis(url, session, questions=questions, user_message=body.query, step_queue=step_q)

            elif normalized == "competitor_profile":
                handle = _resolve_profile_handle(urls, handles)
                pipeline_coro = run_competitor_profile(handle, session, questions, step_queue=step_q)

            elif normalized == "content_directions":
                niche = session.get("niche") or _infer_niche_from_query(body.query)
                pipeline_coro = run_content_directions(niche, session, questions, step_queue=step_q)

            elif normalized == "own_channel":
                niche = session.get("niche") or _infer_niche_from_query(body.query)
                pipeline_coro = run_own_channel(niche, session, questions)

            elif normalized == "brief_generation":
                niche = session.get("niche") or _infer_niche_from_query(body.query)
                pipeline_coro = run_brief_generation(body.query, niche, session, questions, step_queue=step_q)

            elif normalized == "trend_spike":
                niche = session.get("niche") or _infer_niche_from_query(body.query)
                pipeline_coro = run_trend_spike(niche, session, questions, step_queue=step_q)

            elif normalized == "shot_list":
                niche = session.get("niche") or _infer_niche_from_query(body.query)
                pipeline_coro = run_shot_list(body.query, niche, session, questions, step_queue=step_q)

            elif normalized == "creator_search":
                niche = session.get("niche") or _infer_niche_from_query(body.query)
                pipeline_coro = run_creator_search(niche, session, questions)

            else:
                # Safety net: unknown intent routed here — treat as follow-up text
                logger.warning("Unexpected intent in /stream: %s — falling back to gemini_text_only", normalized)
                full_text = await run_sync(gemini_text_only, body.query, session)
                structured = None
                chunks = _chunk_text(full_text, 50)
                put_stream_chunks(stream_id, chunks)
                for chunk in chunks:
                    seq += 1
                    yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": chunk, "done": False})
                    await asyncio.sleep(0.005)
                seq += 1
                yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True})
                await run_sync(
                    _insert_chat_message_best_effort,
                    supabase=sb, session_id=body.session_id, user_id=user_id,
                    content=full_text, structured_output=None, intent_type=normalized, stream_id=stream_id,
                )
                sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
                return

            # Run pipeline in background task; yield step events as they arrive
            pipeline_task = asyncio.create_task(
                asyncio.wait_for(pipeline_coro, timeout=180.0)
            )

            # ── Phase 1: stream step events ───────────────────────────────────
            while True:
                try:
                    event = await asyncio.wait_for(step_q.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    if pipeline_task.done():
                        # Drain any remaining events
                        while not step_q.empty():
                            event = step_q.get_nowait()
                            if event is None:
                                break
                            seq += 1
                            yield _sse_line({"stream_id": stream_id, "seq": seq, "step": event})
                        break
                    continue

                if event is None:
                    # Sentinel — pipeline has finished emitting step events
                    break

                seq += 1
                yield _sse_line({"stream_id": stream_id, "seq": seq, "step": event})

            # ── Await pipeline result ─────────────────────────────────────────
            out = await pipeline_task

            if normalized == "video_diagnosis":
                # Video URL analysis: has user_video + diagnosis key
                uv = out.get("user_video") or {}
                if uv.get("error"):
                    # Use structured error_message from _analyze_carousel when present
                    # so carousel errors show a Vietnamese message instead of generic failure.
                    user_error_msg = uv.get("error_message")
                    error_code = uv.get("error") if isinstance(uv.get("error"), str) else "analysis_failed"
                    if user_error_msg:
                        # Stream the Vietnamese message as a text delta so the user sees it
                        for chunk in _chunk_text(user_error_msg, 50):
                            seq += 1
                            yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": chunk})
                    seq += 1
                    yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True, "error": error_code})
                    sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
                    return
                full_text = (out.get("diagnosis") or "").strip()
                structured: dict[str, Any] | None = {
                    k: out[k]
                    for k in (
                        "niche",
                        "user_video",
                        "reference_videos",
                        "metadata",
                        "analysis",
                        "content_type",
                        "coverage",
                        "follow_ups",
                        "comment_radar",
                        "thumbnail_analysis",
                    )
                    if k in out
                } or None
            elif normalized == "competitor_profile":
                full_text = (out.get("synthesis") or "").strip()
                structured = {
                    k: out[k]
                    for k in ("handle", "analyzed_videos", "follow_ups")
                    if k in out
                } or None
            elif normalized == "content_directions":
                full_text = (out.get("synthesis") or "").strip()
                structured = {
                    k: out[k]
                    for k in (
                        "niche",
                        "directions",
                        "analyzed_videos",
                        "coverage",
                        "follow_ups",
                    )
                    if k in out
                } or None
            elif normalized == "own_channel":
                full_text = (out.get("synthesis") or "").strip()
                structured = {
                    k: out[k]
                    for k in ("niche", "analyzed_videos", "coverage", "follow_ups")
                    if k in out
                } or None
            elif normalized == "brief_generation":
                full_text = (out.get("brief") or "").strip()
                structured = {
                    k: out[k]
                    for k in ("topic", "niche", "coverage", "follow_ups")
                    if k in out
                } or None
            elif normalized == "trend_spike":
                full_text = (out.get("synthesis") or "").strip()
                structured = {
                    k: out[k]
                    for k in ("niche", "analyzed_videos", "coverage", "follow_ups", "patterns")
                    if k in out
                } or None
            elif normalized == "shot_list":
                full_text = (out.get("shot_list") or "").strip()
                structured = {
                    k: out[k]
                    for k in ("topic", "niche", "coverage", "follow_ups")
                    if k in out
                } or None
            elif normalized == "creator_search":
                full_text = (out.get("synthesis") or "").strip()
                structured = {
                    k: out[k]
                    for k in ("niche", "creators", "coverage", "follow_ups")
                    if k in out
                } or None
            else:
                full_text = (out.get("synthesis") or out.get("diagnosis") or "").strip()
                structured = None

            # ── Phase 2: stream synthesis text ────────────────────────────────
            chunks = _chunk_text(full_text, 50)
            put_stream_chunks(stream_id, chunks)

            for chunk in chunks:
                seq += 1
                yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": chunk, "done": False})
                await asyncio.sleep(0.005)

            # ── Done token ────────────────────────────────────────────────────
            seq += 1
            yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True})

            # ── Post-stream: persist message + clear is_processing ────────────
            await run_sync(
                _insert_chat_message_best_effort,
                supabase=sb,
                session_id=body.session_id,
                user_id=user_id,
                content=full_text,
                structured_output=structured,
                intent_type=normalized,
                stream_id=stream_id,
            )
            sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()

        except Exception as exc:
            logger.exception("Stream pipeline error: %s", exc)
            error_code = _classify_stream_error(exc)
            seq += 1
            yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True, "error": error_code})
            sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Batch corpus ingest ─────────────────────────────────────────────────────────

_BATCH_SECRET = os.environ.get("BATCH_SECRET", "")


class BatchIngestRequest(BaseModel):
    niche_ids: list[int] | None = Field(
        default=None,
        description="Restrict to specific niche IDs. Omit to ingest all niches.",
    )


@app.post("/batch/ingest")
async def batch_ingest(
    request: Request,
    body: BatchIngestRequest = BatchIngestRequest(),
) -> JSONResponse:
    """Trigger video corpus batch ingest.

    Protected by BATCH_SECRET header (X-Batch-Secret). Intended to be called
    by Cloud Scheduler via HTTP target — not exposed to end users.

    Returns a summary of inserted / skipped / failed counts per niche.
    """
    if _BATCH_SECRET:
        provided = request.headers.get("X-Batch-Secret", "")
        if provided != _BATCH_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid batch secret")

    from getviews_pipeline.corpus_ingest import run_batch_ingest

    logger.info("POST /batch/ingest triggered — niche_ids=%s", body.niche_ids)
    try:
        summary = await run_batch_ingest(niche_ids=body.niche_ids)
    except Exception as exc:
        logger.exception("Batch ingest failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({
        "ok": True,
        "total_inserted": summary.total_inserted,
        "total_skipped": summary.total_skipped,
        "total_failed": summary.total_failed,
        "niches_processed": summary.niches_processed,
        "materialized_view_refreshed": summary.materialized_view_refreshed,
        "niche_results": summary.niche_results,
    })


@app.post("/batch/backfill-thumbnails")
async def batch_backfill_thumbnails(request: Request) -> JSONResponse:
    """One-time backfill: copy TikTok CDN thumbnail URLs → permanent R2 URLs.

    Iterates all video_corpus rows whose thumbnail_url does NOT start with the
    R2 public URL (i.e. still points at tiktokcdn-eu.com or similar CDN).
    Downloads each thumbnail and uploads to R2, then patches the row.

    Protected by X-Batch-Secret. Safe to re-run — skips rows already on R2.
    """
    if _BATCH_SECRET:
        provided = request.headers.get("X-Batch-Secret", "")
        if provided != _BATCH_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid batch secret")

    from getviews_pipeline.r2 import download_and_upload_thumbnail, r2_configured
    from getviews_pipeline.config import R2_PUBLIC_URL
    from getviews_pipeline.supabase_client import get_service_client

    if not r2_configured():
        raise HTTPException(status_code=500, detail="R2 not configured")

    sb = get_service_client()
    logger.info("POST /batch/backfill-thumbnails — starting")

    # Fetch all rows with non-R2 thumbnail URLs
    r2_prefix = R2_PUBLIC_URL.rstrip("/") if R2_PUBLIC_URL else "NONE"
    result = sb.table("video_corpus").select("video_id, thumbnail_url").execute()
    rows = result.data or []
    to_backfill = [
        r for r in rows
        if r.get("thumbnail_url") and not r["thumbnail_url"].startswith(r2_prefix)
    ]
    logger.info("[backfill-thumbnails] %d/%d rows need backfill", len(to_backfill), len(rows))

    updated = 0
    failed = 0
    skipped = 0

    # Process in batches of 10 to avoid overwhelming R2 or TikTok CDN
    CHUNK = 10
    for i in range(0, len(to_backfill), CHUNK):
        chunk = to_backfill[i:i + CHUNK]
        tasks = [
            download_and_upload_thumbnail(r["thumbnail_url"], r["video_id"])
            for r in chunk
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for row, res in zip(chunk, results):
            if isinstance(res, Exception):
                logger.warning("[backfill-thumbnails] error for %s: %s", row["video_id"], res)
                failed += 1
            elif isinstance(res, str) and res:
                try:
                    sb.table("video_corpus").update({"thumbnail_url": res}).eq("video_id", row["video_id"]).execute()
                    updated += 1
                    logger.debug("[backfill-thumbnails] patched %s → %s", row["video_id"], res)
                except Exception as exc:
                    logger.warning("[backfill-thumbnails] DB patch failed for %s: %s", row["video_id"], exc)
                    failed += 1
            else:
                skipped += 1

    logger.info("[backfill-thumbnails] done — updated=%d failed=%d skipped=%d", updated, failed, skipped)
    return JSONResponse({"ok": True, "updated": updated, "failed": failed, "skipped": skipped, "total": len(to_backfill)})


@app.post("/batch/analytics")
async def batch_analytics(request: Request) -> JSONResponse:
    """Trigger weekly analytics: creator velocity + breakout multiplier + signal grading.

    Protected by X-Batch-Secret header. Normally called by Cloud Scheduler on Sundays,
    but available for manual triggering (e.g. after importing a large batch of corpus data).
    """
    if _BATCH_SECRET:
        provided = request.headers.get("X-Batch-Secret", "")
        if provided != _BATCH_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid batch secret")

    from getviews_pipeline.batch_analytics import run_analytics
    from getviews_pipeline.corpus_context import _anon_client
    from getviews_pipeline.pattern_fingerprint import recompute_weekly_counts
    from getviews_pipeline.signal_classifier import run_signal_grading

    logger.info("POST /batch/analytics triggered")
    try:
        analytics = await run_analytics()
        signal = await run_signal_grading()
        # Piggyback the pattern weekly-delta refresh on the analytics cron — the
        # trend_spike "Tuần này pattern X bứt phá +N" callout reads from the
        # columns this touches. Fails open so pattern drift never breaks the
        # analytics job.
        patterns_touched = 0
        try:
            patterns_touched = await recompute_weekly_counts(_anon_client())
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("pattern weekly recompute failed: %s", exc)
    except Exception as exc:
        logger.exception("Batch analytics failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({
        "ok": True,
        "analytics": {
            "creators_updated": analytics.creators_updated,
            "videos_updated": analytics.videos_updated,
            "errors": analytics.errors,
        },
        "signal": {
            "grades_written": signal.grades_written,
            "niches_processed": signal.niches_processed,
            "errors": signal.errors,
        },
        "patterns": {
            "rows_updated": patterns_touched,
        },
    })


@app.post("/batch/layer0")
async def batch_layer0(request: Request) -> JSONResponse:
    """Trigger Layer 0 intelligence extraction independently of corpus ingest.

    Runs all three Layer 0 passes in sequence:
      - Layer 0A: Niche insight synthesis (top formula mechanism extraction)
      - Layer 0B: Emerging sound insights
      - Layer 0C: Cross-niche format migration detection

    Protected by X-Batch-Secret. Safe to re-run — upserts on conflict.
    Useful after code changes or manual data imports without re-ingesting videos.
    """
    if _BATCH_SECRET:
        provided = request.headers.get("X-Batch-Secret", "")
        if provided != _BATCH_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid batch secret")

    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.layer0_niche import run_niche_insights
    from getviews_pipeline.layer0_sound import run_sound_insights
    from getviews_pipeline.layer0_migration import run_cross_niche_migration

    client = get_service_client()
    logger.info("POST /batch/layer0 triggered")

    result: dict = {"ok": True}

    try:
        l0a = await run_niche_insights(client)
        result["layer0a_niche"] = {
            "insights_written": l0a.insights_written,
            "niches_skipped": l0a.niches_skipped,
            "errors": l0a.errors,
        }
        logger.info("[layer0a] insights=%d skipped=%d", l0a.insights_written, l0a.niches_skipped)
    except Exception as exc:
        logger.exception("[layer0a] failed: %s", exc)
        result["layer0a_niche"] = {"error": str(exc)}

    try:
        l0b = await run_sound_insights(client)
        result["layer0b_sound"] = {"analyzed": l0b.get("analyzed", 0)}
        logger.info("[layer0b] analyzed=%d", l0b.get("analyzed", 0))
    except Exception as exc:
        logger.exception("[layer0b] failed: %s", exc)
        result["layer0b_sound"] = {"error": str(exc)}

    try:
        l0c = await run_cross_niche_migration(client)
        result["layer0c_migration"] = {"migrations_found": l0c.get("migrations_found", 0)}
        logger.info("[layer0c] migrations=%d", l0c.get("migrations_found", 0))
    except Exception as exc:
        logger.exception("[layer0c] failed: %s", exc)
        result["layer0c_migration"] = {"error": str(exc)}

    return JSONResponse(result)


@app.get("/admin/corpus-health")
async def admin_corpus_health(request: Request) -> JSONResponse:
    """Per-niche corpus-adequacy snapshot for claim tiers.

    Returns one row per niche with:
      - videos_7d / videos_30d / videos_90d (ingest timestamps)
      - last_ingest_at — most recent video_corpus.created_at
      - last_pattern_at — most recent video_patterns.last_seen_at touching
        this niche (via niche_spread @> ARRAY[niche_id])
      - claim_tiers — pass/fail for each tier given videos_30d

    Plus a summary counting niches per highest-passing tier. Use this to
    answer "which claims are statistically valid today, per niche?".

    Protected by X-Batch-Secret. See artifacts/docs/corpus-health.md.
    """
    if _BATCH_SECRET:
        provided = request.headers.get("X-Batch-Secret", "")
        if provided != _BATCH_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid batch secret")

    from getviews_pipeline.claim_tiers import flags_for_count
    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    try:
        tax_res = client.table("niche_taxonomy").select("id, name_en, name_vn").execute()
        niches = tax_res.data or []
    except Exception as exc:
        logger.exception("[corpus-health] niche_taxonomy fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"niche_taxonomy: {exc}") from exc

    # Pull the last 90 days of (niche_id, created_at) once and aggregate in
    # Python. Corpus is ~700 rows; any per-niche roundtrip would be wasteful.
    try:
        corpus_res = (
            client.table("video_corpus")
            .select("niche_id, created_at")
            .gte("created_at", cutoff_90d.isoformat())
            .execute()
        )
        corpus_rows = corpus_res.data or []
    except Exception as exc:
        logger.exception("[corpus-health] video_corpus fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"video_corpus: {exc}") from exc

    counts_7d: dict[int, int] = {}
    counts_30d: dict[int, int] = {}
    counts_90d: dict[int, int] = {}
    last_ingest: dict[int, str] = {}
    for row in corpus_rows:
        nid = row.get("niche_id")
        created = row.get("created_at")
        if nid is None or not created:
            continue
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue
        counts_90d[nid] = counts_90d.get(nid, 0) + 1
        if created_dt >= cutoff_30d:
            counts_30d[nid] = counts_30d.get(nid, 0) + 1
        if created_dt >= cutoff_7d:
            counts_7d[nid] = counts_7d.get(nid, 0) + 1
        prev = last_ingest.get(nid)
        if prev is None or created > prev:
            last_ingest[nid] = created

    # video_patterns: pull all active rows, fold niche_spread into a per-niche
    # last_seen_at. Pattern table is tiny (hundreds of rows max).
    last_pattern: dict[int, str] = {}
    try:
        pat_res = (
            client.table("video_patterns")
            .select("niche_spread, last_seen_at, is_active")
            .eq("is_active", True)
            .execute()
        )
        for row in pat_res.data or []:
            seen = row.get("last_seen_at")
            if not seen:
                continue
            for nid in row.get("niche_spread") or []:
                prev = last_pattern.get(nid)
                if prev is None or seen > prev:
                    last_pattern[nid] = seen
    except Exception as exc:
        # Fail open — patterns info is nice-to-have, not required for tiers.
        logger.warning("[corpus-health] video_patterns fetch failed: %s", exc)

    per_niche: list[dict[str, Any]] = []
    tier_histogram = {
        "none": 0, "reference_pool": 0, "basic_citation": 0,
        "niche_norms": 0, "hook_effectiveness": 0, "trend_delta": 0,
    }
    for n in niches:
        nid = n.get("id")
        if nid is None:
            continue
        v30 = counts_30d.get(nid, 0)
        flags = flags_for_count(v30)
        tier_histogram[flags.highest_passing_tier] = (
            tier_histogram.get(flags.highest_passing_tier, 0) + 1
        )
        per_niche.append({
            "niche_id": nid,
            "name_en": n.get("name_en"),
            "name_vn": n.get("name_vn"),
            "videos_7d": counts_7d.get(nid, 0),
            "videos_30d": v30,
            "videos_90d": counts_90d.get(nid, 0),
            "last_ingest_at": last_ingest.get(nid),
            "last_pattern_at": last_pattern.get(nid),
            "claim_tiers": flags.asdict(),
            "highest_passing_tier": flags.highest_passing_tier,
        })

    per_niche.sort(key=lambda r: (-r["videos_30d"], r["niche_id"]))

    summary = {
        "niches_total": len(per_niche),
        "videos_7d_total":  sum(counts_7d.values()),
        "videos_30d_total": sum(counts_30d.values()),
        "videos_90d_total": sum(counts_90d.values()),
        "tier_histogram": tier_histogram,
    }

    return JSONResponse({
        "ok": True,
        "as_of": now.isoformat(),
        "summary": summary,
        "niches": per_niche,
    })


# ══════════════════════════════════════════════════════════════════════════
# Phase B · /video — niche benchmark (B.1.2)
# ══════════════════════════════════════════════════════════════════════════

_NICHE_BENCH_CACHE: dict[tuple[int, int], tuple[float, dict[str, Any]]] = {}
_NICHE_BENCH_TTL_SEC = 3600.0


def _niche_bench_cache_key(niche_id: int, duration_sec: float) -> tuple[int, int]:
    return niche_id, int(round(duration_sec))


@app.get("/video/niche-benchmark")
async def video_niche_benchmark(
    user: dict = Depends(require_user),
    niche_id: int = Query(..., ge=1, description="niche_taxonomy.id"),
    duration_sec: float = Query(
        58.0,
        ge=5.0,
        le=600.0,
        description="Video duration for benchmark curve shape (seconds).",
    ),
) -> JSONResponse:
    """Niche aggregates + modeled benchmark retention curve for /video Flop UI.

    Reads ``niche_intelligence`` via the caller's JWT (RLS: authenticated SELECT).
    Cached in-process for ``_NICHE_BENCH_TTL_SEC`` — MV refresh is batch-driven.
    """
    now = time.monotonic()
    ck = _niche_bench_cache_key(niche_id, duration_sec)
    cached = _NICHE_BENCH_CACHE.get(ck)
    if cached and now - cached[0] < _NICHE_BENCH_TTL_SEC:
        return JSONResponse(cached[1])

    from getviews_pipeline.video_niche_benchmark import (
        build_niche_benchmark_payload,
        fetch_niche_intelligence_sync,
    )

    sb = user_supabase(user["access_token"])
    try:
        row = await run_sync(fetch_niche_intelligence_sync, sb, niche_id)
    except Exception as exc:
        logger.exception("[video/niche-benchmark] niche=%s failed: %s", niche_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    payload = build_niche_benchmark_payload(
        row,
        niche_id=niche_id,
        duration_sec=duration_sec,
        user_sb=sb,
    )
    _NICHE_BENCH_CACHE[ck] = (now, payload)
    return JSONResponse(payload)


class VideoAnalyzeRequest(BaseModel):
    video_id: str | None = None
    tiktok_url: str | None = None
    force_refresh: bool = False
    mode: Literal["win", "flop"] | None = None


@app.post("/video/analyze")
async def video_analyze_endpoint(
    body: VideoAnalyzeRequest,
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Phase B · B.1.3 — structural slots + Gemini copy, cached in ``video_diagnostics``.

    ``force_refresh`` bypasses the 1h diagnostics TTL and always re-runs Gemini +
    curve modeling (then upsert). Use only for debugging / prompt iteration — it
    increases latency and model cost.
    """
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.video_analyze import run_video_analyze_pipeline

    vid = (body.video_id or "").strip() if body.video_id else ""
    url = (body.tiktok_url or "").strip() if body.tiktok_url else ""
    if not vid and not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần video_id hoặc tiktok_url",
        )

    sb_user = user_supabase(user["access_token"])
    try:
        out = await run_sync(
            run_video_analyze_pipeline,
            get_service_client(),
            sb_user,
            video_id=vid or None,
            tiktok_url=url or None,
            force_refresh=body.force_refresh,
            mode=body.mode,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg == "video not in corpus" or "Không tìm thấy" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
    except Exception as exc:
        logger.exception("[video/analyze] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


class KolTogglePinRequest(BaseModel):
    handle: str = Field(..., min_length=1, max_length=200)


@app.get("/kol/browse")
async def kol_browse_endpoint(
    user: dict = Depends(require_user),
    tab: Literal["pinned", "discover"] = Query("discover"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    niche_id: int | None = Query(
        None,
        ge=1,
        description="Optional; must equal caller profiles.primary_niche when set.",
    ),
    followers_min: int | None = Query(
        None,
        ge=0,
        description="Optional lower bound on creator followers (discover + pinned).",
    ),
    followers_max: int | None = Query(
        None,
        ge=0,
        description="Optional upper bound on creator followers.",
    ),
    growth_fast: bool = Query(
        False,
        description="When true, keep ~top third by avg_views in the niche pool (growth proxy).",
    ),
    sort: str | None = Query(
        None,
        description="Sort key: pinned | rank | match | followers | avg_views | growth | name.",
    ),
    order_dir: Literal["asc", "desc"] | None = Query(
        None,
        description="asc or desc; server defaults per tab when omitted.",
    ),
    search: str | None = Query(
        None,
        max_length=80,
        description="Optional substring filter on handle or display name (case-insensitive).",
    ),
) -> JSONResponse:
    """B.2.1 — KOL browse rows + rule-based match_score (Phase B / B.0.2)."""
    from getviews_pipeline.kol_browse import KOL_SORT_QUERY_KEYS, run_kol_browse_sync

    token = user["access_token"]
    sb = user_supabase(token)
    nid = niche_id if niche_id is not None else await _resolve_caller_niche_id(token)
    if (
        followers_min is not None
        and followers_max is not None
        and int(followers_min) > int(followers_max)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="followers_min không được lớn hơn followers_max.",
        )
    if sort is not None and sort not in KOL_SORT_QUERY_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"sort không hợp lệ: {sort}",
        )
    sort_desc = None if order_dir is None else (order_dir == "desc")
    try:
        out = await run_sync(
            run_kol_browse_sync,
            sb,
            niche_id=int(nid),
            tab=tab,
            page=page,
            page_size=page_size,
            followers_min=followers_min,
            followers_max=followers_max,
            growth_fast=growth_fast,
            sort=sort,
            sort_desc=sort_desc,
            search=search,
        )
    except ValueError as exc:
        msg = str(exc)
        if "Chưa chọn ngách" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
    except Exception as exc:
        logger.exception("[kol/browse] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


@app.post("/kol/toggle-pin")
async def kol_toggle_pin_endpoint(
    body: KolTogglePinRequest,
    user: dict = Depends(require_user),
) -> JSONResponse:
    """B.2.1 — toggle profiles.reference_channel_handles via Supabase RPC (cap 10)."""
    from getviews_pipeline.kol_browse import normalize_handle

    norm = normalize_handle(body.handle)
    if not norm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="handle rỗng")
    sb = user_supabase(user["access_token"])
    try:
        sb.rpc("toggle_reference_channel", {"p_handle": norm}).execute()
    except Exception as exc:
        logger.exception("[kol/toggle-pin] failed handle=%s: %s", norm, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"ok": True})


@app.get("/channel/analyze")
async def channel_analyze_endpoint(
    user: dict = Depends(require_user),
    handle: str = Query(..., min_length=1, max_length=200, description="TikTok handle, có hoặc không @"),
    force_refresh: bool = Query(
        False,
        description="Bỏ qua cache 7 ngày và gọi lại Gemini (trừ thin_corpus).",
    ),
) -> JSONResponse:
    """B.3.1 — Phân tích kênh: gate ≥10 video, cache ``channel_formulas``, Gemini + trừ credit khi miss."""
    from getviews_pipeline.channel_analyze import InsufficientCreditsError, run_channel_analyze_sync
    from getviews_pipeline.supabase_client import get_service_client

    sb_user = user_supabase(user["access_token"])
    try:
        out = await run_sync(
            run_channel_analyze_sync,
            get_service_client(),
            sb_user,
            user_id=user["user_id"],
            raw_handle=handle,
            force_refresh=force_refresh,
        )
    except InsufficientCreditsError:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={"error": "insufficient_credits"},
        )
    except ValueError as exc:
        msg = str(exc)
        if "Chưa chọn ngách" in msg or "Không thấy kênh" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
    except Exception as exc:
        logger.exception("[channel/analyze] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


@app.get("/script/scene-intelligence")
async def script_scene_intelligence_endpoint(
    user: dict = Depends(require_user),
    niche_id: int | None = Query(
        default=None,
        ge=1,
        description="Ngách; mặc định lấy ``profiles.primary_niche`` của user.",
    ),
) -> JSONResponse:
    """B.4.2 — Rows from ``scene_intelligence`` (nightly aggregate) for script studio."""
    from getviews_pipeline.script_data import fetch_scene_intelligence_for_niche

    token = user["access_token"]
    nid = niche_id if niche_id is not None else await _resolve_caller_niche_id(token)
    sb = user_supabase(token)
    try:
        out = await run_sync(fetch_scene_intelligence_for_niche, sb, nid)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[script/scene-intelligence] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


@app.get("/script/hook-patterns")
async def script_hook_patterns_endpoint(
    user: dict = Depends(require_user),
    niche_id: int | None = Query(
        default=None,
        ge=1,
        description="Ngách; mặc định lấy ``profiles.primary_niche`` của user.",
    ),
) -> JSONResponse:
    """B.4.2 — Hook leaderboard + citation for script studio (wraps ``hook_effectiveness``)."""
    from getviews_pipeline.script_data import fetch_hook_patterns_for_niche

    token = user["access_token"]
    nid = niche_id if niche_id is not None else await _resolve_caller_niche_id(token)
    sb = user_supabase(token)
    try:
        out = await run_sync(fetch_hook_patterns_for_niche, sb, nid)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[script/hook-patterns] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


# ══════════════════════════════════════════════════════════════════════════
# Home screen endpoints — Phase A · A1
# ══════════════════════════════════════════════════════════════════════════
# Each endpoint resolves the caller's niche from profiles.primary_niche. If the
# user hasn't picked one yet (returns 404 rather than inventing one).
# ──────────────────────────────────────────────────────────────────────────


async def _resolve_caller_niche_id(access_token: str) -> int:
    """Fetch profiles.primary_niche for the calling user. 404 if unset."""
    sb = user_supabase(access_token)
    try:
        res = sb.table("profiles").select("primary_niche").single().execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"profile lookup: {exc}") from exc
    nid = (res.data or {}).get("primary_niche")
    if nid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chưa chọn ngách — chạy onboarding trước.",
        )
    return int(nid)


@app.get("/home/pulse")
async def home_pulse(
    user: dict = Depends(require_user),
) -> JSONResponse:
    """PulseCard payload for the caller's primary niche.

    Returns the 4-bignum + delta shape the design's PulseCard renders:
      { views_this_week, views_delta_pct, videos_this_week, new_creators,
        viral_count, new_hooks, top_hook_name, adequacy, as_of }

    `adequacy` is a claim_tiers tier name — the UI uses it to soften deltas
    when the niche is too thin to cite percentages honestly.
    """
    from getviews_pipeline.pulse import compute_pulse
    from getviews_pipeline.supabase_client import get_service_client

    niche_id = await _resolve_caller_niche_id(user["access_token"])
    try:
        stats = await compute_pulse(get_service_client(), niche_id)
    except Exception as exc:
        logger.exception("[home_pulse] niche=%s failed: %s", niche_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(stats.to_json())


@app.get("/home/ticker")
async def home_ticker(
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Marquee ticker items for the caller's primary niche.

    Returns up to 10 TickerItems across 5 buckets (breakout / hook_mới /
    cảnh_báo / kol_nổi / âm_thanh), round-robin-interleaved so the marquee
    reads mixed. Fails open per-bucket — if one query errors, that bucket
    is silently omitted.
    """
    from getviews_pipeline.ticker import compute_ticker
    from getviews_pipeline.supabase_client import get_service_client

    niche_id = await _resolve_caller_niche_id(user["access_token"])
    try:
        items = await compute_ticker(get_service_client(), niche_id)
    except Exception as exc:
        logger.exception("[home_ticker] niche=%s failed: %s", niche_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({
        "niche_id": niche_id,
        "items": [it.to_json() for it in items],
    })


@app.get("/home/starter-creators")
async def home_starter_creators(
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Onboarding step 2 — starter creators to pick reference channels from.

    Returns up to 10 starter_creators rows for the caller's niche, ordered
    by rank. Drives the second step of the onboarding flow where the user
    picks 1–3 kênh tham chiếu.
    """
    sb = user_supabase(user["access_token"])
    niche_id = await _resolve_caller_niche_id(user["access_token"])
    try:
        res = (
            sb.table("starter_creators")
            .select("handle, display_name, followers, avg_views, video_count, rank")
            .eq("niche_id", niche_id)
            .order("rank", desc=False)
            .limit(10)
            .execute()
        )
    except Exception as exc:
        logger.exception("[home_starter_creators] niche=%s failed: %s", niche_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({
        "niche_id": niche_id,
        "creators": res.data or [],
    })


@app.get("/home/daily-ritual")
async def home_daily_ritual(
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Today's 3 ready-to-shoot scripts for the calling creator.

    Returns the most recent daily_ritual row for this user (<= today). If no
    row exists yet, returns 404 — the UI should render a "sắp có" state
    rather than blocking on generation, since generation is async (nightly).

    Response (200):
      {
        "generated_for_date": "2026-04-23",
        "niche_id": 4,
        "adequacy": "niche_norms",
        "scripts": [{hook_type_en, hook_type_vi, title_vi, why_works,
                     retention_est_pct, shot_count, length_sec}, ...]
      }
    """
    sb = user_supabase(user["access_token"])
    try:
        res = (
            sb.table("daily_ritual")
            .select("generated_for_date, niche_id, scripts, adequacy, generated_at")
            .order("generated_for_date", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("[home_daily_ritual] user=%s failed: %s", user["user_id"], exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    rows = res.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sắp có — kịch bản đang được tạo.",
        )
    return JSONResponse(rows[0])


class RitualBatchRequest(BaseModel):
    user_ids: list[str] | None = Field(
        default=None,
        description="Restrict to specific user ids. Omit for all users.",
    )


@app.post("/batch/morning-ritual")
async def batch_morning_ritual(
    request: Request,
    body: RitualBatchRequest = RitualBatchRequest(),
) -> JSONResponse:
    """Nightly cron: generate 3 scripts for every creator with a niche set.

    Protected by X-Batch-Secret. Called by Cloud Scheduler at ~07:00 Asia/
    Ho_Chi_Minh so the ritual is ready when the creator opens the app.
    """
    if _BATCH_SECRET:
        provided = request.headers.get("X-Batch-Secret", "")
        if provided != _BATCH_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid batch secret")

    from getviews_pipeline.morning_ritual import run_morning_ritual_batch
    from getviews_pipeline.supabase_client import get_service_client

    try:
        summary = await run_sync(run_morning_ritual_batch, get_service_client(), body.user_ids)
    except Exception as exc:
        logger.exception("[batch/morning-ritual] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({
        "ok": True,
        "generated":              summary.generated,
        "skipped_thin":           summary.skipped_thin,
        "failed_schema":          summary.failed_schema,
        "failed_gemini":          summary.failed_gemini,
        "failed_duplicate_hooks": summary.failed_duplicate_hooks,
        "failed_upsert":          summary.failed_upsert,
        "users_no_niche":         summary.users_no_niche,
    })


@app.post("/batch/scene-intelligence")
async def batch_scene_intelligence(request: Request) -> JSONResponse:
    """Nightly cron: rebuild ``scene_intelligence`` from ``video_corpus`` scenes.

    Protected by ``X-Batch-Secret`` (same as other batch jobs). Requires
    ``SUPABASE_SERVICE_ROLE_KEY`` on the Cloud Run service.
    """
    if _BATCH_SECRET:
        provided = request.headers.get("X-Batch-Secret", "")
        if provided != _BATCH_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid batch secret")

    from getviews_pipeline.scene_intelligence_refresh import refresh_scene_intelligence_sync
    from getviews_pipeline.supabase_client import get_service_client

    try:
        stats = await run_sync(refresh_scene_intelligence_sync, get_service_client())
    except Exception as exc:
        logger.exception("[batch/scene-intelligence] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({"ok": True, **stats})
