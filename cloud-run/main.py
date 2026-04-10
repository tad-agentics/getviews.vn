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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import AliasChoices, BaseModel, Field

from getviews_pipeline import ensemble
from getviews_pipeline.config import SUPABASE_JWKS_URL, SUPABASE_JWT_SECRET
from getviews_pipeline.gemini import gemini_text_only
from getviews_pipeline.intents import (
    QueryIntent,
    collapse_to_intents,
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


_INTENT_ALIASES: dict[str, str] = {
    "tiktok_url_diagnosis": "video_diagnosis",
    "kol_search": "find_creators",
    "followup": "follow_up",
}


def _normalize_intent(raw: str | None) -> str | None:
    if raw is None:
        return None
    return _INTENT_ALIASES.get(raw, raw)


# Matches FREE_INTENTS in api/chat.ts — no credit deduction for these.
FREE_INTENTS: frozenset[str] = frozenset(
    {"trend_spike", "find_creators", "follow_up", "format_lifecycle", "kol_search"}
)


def is_free_intent(intent: str) -> bool:
    return intent in FREE_INTENTS


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


async def _metadata_only_json(url: str) -> str:
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


async def _dispatch_intent(
    intent: QueryIntent,
    questions: list[str],
    query: str,
    urls: list[str],
    handles: list[str],
    session: dict[str, Any],
) -> tuple[str, dict[str, Any] | None]:
    """Dispatch one classified intent to its pipeline. Returns (text, structured)."""
    niche = infer_niche_from_message(query)

    if intent == QueryIntent.VIDEO_DIAGNOSIS:
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
            for k in ("niche", "user_video", "reference_videos", "metadata", "analysis", "content_type")
            if k in out
        }
        return text, structured or None

    if intent == QueryIntent.COMPETITOR_PROFILE:
        handle = _resolve_profile_handle(urls, handles)
        out = await run_competitor_profile(handle, session, questions)
        structured = {k: out[k] for k in ("handle", "analyzed_videos") if k in out}
        return out["synthesis"], structured or None

    if intent == QueryIntent.TREND_SPIKE:
        out = await run_trend_spike(niche, session, questions)
        structured = {k: out[k] for k in ("niche", "analyzed_videos") if k in out}
        return out["synthesis"], structured or None

    if intent == QueryIntent.CONTENT_DIRECTIONS:
        out = await run_content_directions(niche, session, questions)
        structured = {k: out[k] for k in ("niche", "directions", "analyzed_videos") if k in out}
        return out["synthesis"], structured or None

    if intent == QueryIntent.SERIES_AUDIT:
        if len(urls) < 2:
            return "Cần ít nhất hai link TikTok cho kiểm tra series.", None
        out = await run_series_audit(urls, session, questions)
        structured = {k: out[k] for k in ("analyzed_videos",) if k in out}
        return out["synthesis"], structured or None

    if intent == QueryIntent.BRIEF_GENERATION:
        topic = questions[0] if questions else query.strip()
        out = await run_brief_generation(topic, niche, session, questions)
        structured = {k: v for k, v in out.items() if k != "brief"}
        return out["brief"], structured or None

    if intent == QueryIntent.METADATA_ONLY:
        if not urls:
            return "Cần link TikTok.", None
        text = await _metadata_only_json(urls[0])
        return text, None

    if intent == QueryIntent.FOLLOWUP:
        text = await run_sync(gemini_text_only, query, session)
        record_intent_done(session, "follow_up")
        return text, None

    # Unknown — fall back to knowledge/text
    text = await run_sync(gemini_text_only, query, session)
    return text, None


def _chunk_text(text: str, size: int = 20) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


def _sse_line(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


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
    session_id: str,
    user_id: str,
    content: str,
    structured_output: dict[str, Any] | None,
    intent_type: str,
    stream_id: str,
) -> None:
    try:
        sb = get_supabase()
        sb.table("chat_messages").insert(
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


def _clear_processing(user_id: str) -> None:
    """Best-effort: clear is_processing flag after a paid intent finishes."""
    try:
        sb = get_supabase()
        sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
    except Exception as exc:
        logger.warning("clear is_processing failed (non-fatal): %s", exc)

app = FastAPI(title="GetViews Pipeline", version="0.1.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
# ALLOWED_ORIGINS env var: comma-separated list. Defaults to production + local dev.
_raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://getviews.vn,https://www.getviews.vn,http://localhost:5173,http://localhost:4173",
)
_ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    # Vercel preview deployments have dynamic subdomains — allow via regex.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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
    Returns the decoded JWT payload (contains 'sub' = user UUID).
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

    return {"user_id": user_id, "payload": payload}


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
    body: StreamRequest,
    user: dict = Depends(require_user),
) -> StreamingResponse:
    """SSE token stream — full pipeline implementation.

    Flow:
    1. JWT validated by require_user dependency.
    2. SSE reconnect: replay cached chunks if resume_stream_id + last_seq provided.
    3. Credit gate: decrement_credit RPC for non-free intents; 402 on insufficient balance.
    4. is_processing = true on start (paid intents only).
    5. collapse_to_intents: multi-intent + knowledge question routing.
    6. Knowledge questions → gemini_text_only, streamed first.
    7. Each intent pair → matching pipeline (video_diagnosis, competitor_profile, etc.).
    8. All results concatenated, chunked, streamed as SSE deltas.
    9. chat_messages insert (best-effort) after all chunks sent.
    10. is_processing = false on finish or error (paid intents only).
    """
    user_id: str = user["user_id"]

    # ── Credit gate (before opening the stream) ───────────────────────────────
    # Mirrors api/chat.ts lines 82–96. Done outside the generator so we can
    # return a proper HTTP 402 before the SSE stream starts.
    urls_pre, handles_pre = extract_urls_and_handles(body.query)
    has_session_pre = False  # will be checked properly inside generator
    normalized_pre = _normalize_intent(body.intent_type)
    if normalized_pre:
        primary_intent_str = normalized_pre
    else:
        questions_pre = split_into_questions(body.query)
        session_pre = get_session_context(body.session_id)
        has_session_pre = bool(session_pre.get("completed_intents"))
        collapse_pre = collapse_to_intents(questions_pre, urls_pre, handles_pre, has_session_pre)
        primary_intent_str = (
            collapse_pre.pairs[0][0].value if collapse_pre.pairs
            else ("follow_up" if collapse_pre.knowledge_questions else "content_directions")
        )

    is_free = is_free_intent(primary_intent_str)

    if not is_free:
        try:
            sb = get_supabase()
            sb.table("profiles").update({"is_processing": True}).eq("id", user_id).execute()
            result = sb.rpc("decrement_credit", {"p_user_id": user_id}).execute()
            balance_after = result.data
            if balance_after is None:
                sb.table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
                return JSONResponse(
                    {"error": "insufficient_credits"},
                    status_code=402,
                    headers={"Content-Type": "application/json"},
                )
        except Exception as exc:
            logger.error("Credit deduction failed: %s", exc)
            try:
                get_supabase().table("profiles").update({"is_processing": False}).eq("id", user_id).execute()
            except Exception:
                pass
            return JSONResponse({"error": "credit_check_failed"}, status_code=500)

    async def event_generator() -> AsyncIterator[bytes]:
        stream_id = str(uuid.uuid4())
        seq = body.last_seq or 0

        try:
            # ── SSE reconnect replay ──────────────────────────────────────────
            if body.resume_stream_id and body.last_seq is not None:
                cached = get_stream_chunks(body.resume_stream_id)
                if cached:
                    stream_id = body.resume_stream_id
                    for i, chunk in enumerate(cached, start=1):
                        if i <= body.last_seq:
                            continue
                        yield _sse_line({"stream_id": stream_id, "seq": i, "delta": chunk, "done": False})
                        await asyncio.sleep(0.005)
                    yield _sse_line({"stream_id": stream_id, "seq": len(cached) + 1, "delta": "", "done": True})
                    if not is_free:
                        await run_sync(_clear_processing, user_id)
                    return

            # ── Intent classification ─────────────────────────────────────────
            session = get_session_context(body.session_id)
            urls, handles = extract_urls_and_handles(body.query)
            has_session = bool(session.get("completed_intents"))

            all_chunks: list[str] = []
            full_text_parts: list[str] = []
            last_intent_str = primary_intent_str

            if normalized_pre:
                # Frontend pre-classified — honour it directly as a single intent pair
                try:
                    qi = QueryIntent(normalized_pre)
                except ValueError:
                    qi = QueryIntent.FOLLOWUP
                questions = split_into_questions(body.query)
                pairs: list[tuple[QueryIntent, list[str]]] = [(qi, questions)]
                knowledge_qs: list[str] = []
            else:
                questions = split_into_questions(body.query)
                collapse = collapse_to_intents(questions, urls, handles, has_session)
                pairs = collapse.pairs
                knowledge_qs = collapse.knowledge_questions

            # ── Stream knowledge answers first ───────────────────────────────
            if knowledge_qs:
                k_text = await run_sync(gemini_text_only, "\n\n".join(knowledge_qs), session)
                k_chunks = _chunk_text(k_text, 20)
                for chunk in k_chunks:
                    seq += 1
                    yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": chunk, "done": False})
                    await asyncio.sleep(0.005)
                full_text_parts.append(k_text)
                all_chunks.extend(k_chunks)

            # ── Stream each intent pipeline result ───────────────────────────
            for intent, qs in pairs:
                last_intent_str = intent.value
                text, structured = await _dispatch_intent(
                    intent, qs, body.query, urls, handles, session
                )

                # Separate multiple results with a divider
                if full_text_parts:
                    divider = "\n\n---\n\n"
                    div_chunks = _chunk_text(divider, 20)
                    for chunk in div_chunks:
                        seq += 1
                        yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": chunk, "done": False})
                        await asyncio.sleep(0.002)
                    all_chunks.extend(div_chunks)

                chunks = _chunk_text(text, 20)
                for chunk in chunks:
                    seq += 1
                    yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": chunk, "done": False})
                    await asyncio.sleep(0.005)

                full_text_parts.append(text)
                all_chunks.extend(chunks)

            full_text = "\n\n".join(full_text_parts)

            # Cache for replay
            put_stream_chunks(stream_id, all_chunks)

            # ── Persist to chat_messages ──────────────────────────────────────
            # TODO: pass structured output from last pipeline when multi-intent
            await run_sync(
                _insert_chat_message_best_effort,
                session_id=body.session_id,
                user_id=user_id,
                content=full_text,
                structured_output=None,
                intent_type=last_intent_str,
                stream_id=stream_id,
            )

            seq += 1
            yield _sse_line({"stream_id": stream_id, "seq": seq, "delta": "", "done": True})

            if not is_free:
                await run_sync(_clear_processing, user_id)

        except Exception as exc:
            logger.exception("stream pipeline error: %s", exc)
            err_msg = str(exc).strip() or "stream_failed"
            yield _sse_line({"stream_id": stream_id, "seq": seq + 1, "delta": "", "done": True, "error": err_msg})
            if not is_free:
                await run_sync(_clear_processing, user_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
