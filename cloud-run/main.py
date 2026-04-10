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
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import AliasChoices, BaseModel, Field

from getviews_pipeline import ensemble
from getviews_pipeline.config import SUPABASE_JWKS_URL, SUPABASE_JWT_SECRET
from getviews_pipeline.gemini import gemini_text_only
from getviews_pipeline.intents import (
    QueryIntent,
    classify_intent,
    extract_urls_and_handles,
    infer_niche_from_message,
    split_into_questions,
)
from getviews_pipeline.pipelines import (
    run_brief_generation,
    run_competitor_profile,
    run_content_directions,
    run_kol_search,
    run_own_channel,
    run_series_audit,
    run_trend_spike,
    run_video_diagnosis,
)
from getviews_pipeline.runtime import run_sync
from getviews_pipeline.session_store import (
    get_session_context,
    get_stream_chunks,
    put_stream_chunks,
    record_intent_done,
)
from getviews_pipeline.supabase_client import user_supabase

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

_supabase: Any = None


def get_supabase() -> Any:
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        from supabase import create_client

        _supabase = create_client(url, key)
    return _supabase


_PROFILE_HANDLE_RE = re.compile(r"tiktok\.com/@([a-zA-Z0-9_.]+)", re.IGNORECASE)


def _normalize_intent_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    aliases = {
        "tiktok_url_diagnosis": "video_diagnosis",
        "kol_search": "find_creators",
        "followup": "follow_up",
    }
    return aliases.get(raw, raw)


def is_free_intent(intent: str) -> bool:
    return intent in ("trend_spike", "kol_search", "follow_up", "find_creators")


def _classify_to_frontend_intent(qi: QueryIntent) -> str:
    if qi == QueryIntent.FOLLOWUP:
        return "follow_up"
    return qi.value


def _resolve_profile_handle(urls: list[str], handles: list[str]) -> str:
    if handles:
        return handles[0].lstrip("@")
    for u in urls:
        m = _PROFILE_HANDLE_RE.search(u)
        if m:
            return m.group(1)
    raise ValueError("Thiếu @handle hoặc URL profile TikTok hợp lệ.")


def _pick_video_url(urls: list[str]) -> str | None:
    for u in urls:
        ul = u.lower()
        if "/video/" in ul or "vm.tiktok.com" in ul:
            return u
    return urls[0] if urls else None


async def _metadata_only_text(url: str) -> str:
    aweme = await ensemble.fetch_post_info(url)
    meta = ensemble.parse_metadata(aweme)
    m = meta.metrics
    head = " · ".join(
        [
            f"@{meta.author.username}",
            f"{m.views or 0} lượt xem",
            f"{m.likes or 0} thích",
            f"{meta.duration_sec:.1f}s",
        ]
    )
    desc = (meta.description or "").strip()
    return f"{head}\n\n{desc[:800]}"


async def _run_intent_pipeline(
    intent: str,
    query: str,
    session: dict[str, Any],
) -> tuple[str, dict[str, Any] | None]:
    """Run analysis pipeline; returns (assistant_markdown_or_text, structured_json_or_none)."""
    questions = split_into_questions(query)
    niche = infer_niche_from_message(query)
    urls, handles = extract_urls_and_handles(query)

    if intent == "video_diagnosis":
        url = _pick_video_url(urls)
        if not url:
            return "Cần link TikTok (video) hợp lệ.", None
        out = await run_video_diagnosis(url, session, questions=questions)
        uv = out.get("user_video") or {}
        if uv.get("error"):
            return f"Không phân tích được: {uv['error']}", None
        text = (out.get("diagnosis") or "").strip()
        structured = {
            k: out[k]
            for k in (
                "niche",
                "user_video",
                "reference_videos",
                "metadata",
                "analysis",
                "content_type",
            )
            if k in out
        }
        return text, structured or None

    if intent == "competitor_profile":
        handle = _resolve_profile_handle(urls, handles)
        out = await run_competitor_profile(handle, session, questions)
        structured = {k: out[k] for k in ("handle", "analyzed_videos") if k in out}
        return out["synthesis"], structured or None

    if intent == "own_channel":
        out = await run_own_channel(niche, session, questions)
        structured = {k: out[k] for k in ("niche", "analyzed_videos") if k in out}
        return out["synthesis"], structured or None

    if intent == "trend_spike":
        out = await run_trend_spike(niche, session, questions)
        structured = {k: out[k] for k in ("niche", "analyzed_videos") if k in out}
        return out["synthesis"], structured or None

    if intent == "brief_generation":
        topic = questions[0] if questions else query.strip()
        out = await run_brief_generation(topic, niche, session, questions)
        structured = {k: v for k, v in out.items() if k != "brief"}
        return out["brief"], structured or None

    if intent in ("find_creators", "kol_search"):
        out = await run_kol_search(niche, session, questions)
        structured = {k: out[k] for k in ("niche", "analyzed_videos") if k in out}
        return out["synthesis"], structured or None

    if intent in ("follow_up", "followup"):
        text = await run_sync(gemini_text_only, query, session)
        record_intent_done(session, "follow_up")
        return text, None

    if intent == "series_audit":
        if len(urls) < 2:
            return "Cần ít nhất hai link TikTok cho kiểm tra series.", None
        out = await run_series_audit(urls, session, questions)
        structured = {k: out[k] for k in ("analyzed_videos",) if k in out}
        return out["synthesis"], structured or None

    if intent == "content_directions":
        out = await run_content_directions(niche, session, questions)
        structured = {
            k: out[k]
            for k in ("niche", "directions", "analyzed_videos")
            if k in out
        }
        return out["synthesis"], structured or None

    if intent == "metadata_only":
        if not urls:
            return "Cần link TikTok.", None
        text = await _metadata_only_text(urls[0])
        return text, None

    topic = questions[0] if questions else query.strip()
    out = await run_brief_generation(topic, niche, session, questions)
    structured = {k: v for k, v in out.items() if k != "brief"}
    return out["brief"], structured or None


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
    allow_origin_regex=r"https://.*\.vercel\.app|https://getviews\.vn|http://localhost:\d+",
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

    try:
        if SUPABASE_JWT_SECRET:
            # HS256 via shared secret — preferred when available (no network call)
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        else:
            # ES256 via JWKS (stateless, asymmetric fallback)
            jwks = await _get_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["ES256"],
                options={"verify_aud": False},
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
    return JSONResponse({"status": "ok"})


@app.get("/auth-check")
async def auth_check(user: dict = Depends(require_user)) -> JSONResponse:
    """Smoke-test endpoint — returns user_id if JWT is valid."""
    return JSONResponse({"ok": True, "user_id": user["user_id"]})


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
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Credit deduction failed: %s", exc)
        sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={"error": "insufficient_credits"},
        )

    # ── Resolve intent ────────────────────────────────────────────────────────
    normalized = _normalize_intent_name(body.intent_type) or "video_diagnosis"

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

            # ── Run pipeline ──────────────────────────────────────────────────
            session = get_session_context(body.session_id)
            urls, handles = extract_urls_and_handles(body.query)
            questions = split_into_questions(body.query)

            if normalized in ("video_diagnosis", "own_channel"):
                # own_channel = diagnosing the user's own video URL (same pipeline)
                url = _pick_video_url(urls)
                if not url:
                    seq += 1
                    yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True, "error": "missing_video_url"})
                    sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
                    return
                out = await asyncio.wait_for(
                    run_video_diagnosis(url, session, questions=questions),
                    timeout=120.0,
                )
                uv = out.get("user_video") or {}
                if uv.get("error"):
                    seq += 1
                    yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True, "error": "analysis_failed"})
                    sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
                    return
                full_text = (out.get("diagnosis") or "").strip()
                structured: dict[str, Any] | None = {
                    k: out[k]
                    for k in ("niche", "user_video", "reference_videos", "metadata", "analysis", "content_type")
                    if k in out
                } or None

            elif normalized == "competitor_profile":
                handle = _resolve_profile_handle(urls, handles)
                out = await asyncio.wait_for(
                    run_competitor_profile(handle, session, questions),
                    timeout=120.0,
                )
                full_text = (out.get("synthesis") or "").strip()
                structured = {k: out[k] for k in ("handle", "analyzed_videos") if k in out} or None

            else:
                # Safety net: unknown intent routed here — treat as follow-up text
                logger.warning("Unexpected intent in /stream: %s — falling back to gemini_text_only", normalized)
                full_text = await run_sync(gemini_text_only, body.query, session)
                structured = None

            # ── Stream text in chunks ─────────────────────────────────────────
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
