"""Intent classification and SSE stream routes (/classify-intent, /stream)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import AliasChoices, BaseModel, Field

from getviews_pipeline.deps import require_user
from getviews_pipeline.gemini import classify_intent_gemini, gemini_text_only
from getviews_pipeline.intent_router import destination_for_gemini_primary_label
from getviews_pipeline.intents import (
    classify_intent,
    extract_urls_and_handles,
    merge_deterministic_with_gemini,
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
from getviews_pipeline.report_compare import run_compare_pipeline
from getviews_pipeline.runtime import run_sync
from getviews_pipeline.session_store import (
    build_session_context_from_db,
    get_stream_chunks,
    put_stream_chunks,
)
from getviews_pipeline.supabase_client import user_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

# §13 mandate: max 100 free queries per user per day for abuse prevention
FREE_DAILY_LIMIT = 100
_FREE_GATED_INTENTS = frozenset({"trend_spike", "creator_search"})

_PROFILE_HANDLE_RE = re.compile(r"tiktok\.com/@([a-zA-Z0-9_.]+)", re.IGNORECASE)
_SHORT_TIKTOK_HOSTS = {"vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com"}


def _normalize_intent_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    aliases = {
        "tiktok_url_diagnosis": "video_diagnosis",
        "kol_search": "creator_search",
        "find_creators": "creator_search",
        "kol_finder": "creator_search",
        "followup": "follow_up",
    }
    return aliases.get(raw, raw)


def is_free_intent(intent: str) -> bool:
    return intent in ("trend_spike", "creator_search")


def _is_short_tiktok_url(url: str) -> bool:
    try:
        return urlparse(url).netloc.lower() in _SHORT_TIKTOK_HOSTS
    except Exception:
        return False


def _resolve_short_url(url: str, timeout: float = 8.0) -> str:
    """Follow redirects on a short TikTok URL and return the final URL."""
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


def _pick_two_video_urls(urls: list[str]) -> tuple[str | None, str | None]:
    """Wave 4 PR #2 — pick the first two video-style URLs, in source
    order, for the compare pipeline. Falls back to the first two of
    any ordering when fewer than two video-style matches are found —
    the orchestrator will surface a "missing_video_url"-style error
    if either side fails to resolve. Mirrors ``_pick_video_url``'s
    "video > photo > short-link > anything" precedence per slot."""
    video_like = [
        u for u in urls
        if "/video/" in u.lower()
        or "/photo/" in u.lower()
        or _is_short_tiktok_url(u)
    ]
    pool = video_like if len(video_like) >= 2 else urls
    a = pool[0] if len(pool) >= 1 else None
    b = pool[1] if len(pool) >= 2 else None
    return a, b


def _resolve_profile_handle(urls: list[str], handles: list[str]) -> str:
    if handles:
        return handles[0].lstrip("@")
    for u in urls:
        m = _PROFILE_HANDLE_RE.search(u)
        if m:
            return m.group(1)
    raise ValueError("Thiếu @handle hoặc URL profile TikTok hợp lệ.")


def _infer_niche_from_query(query: str) -> str:
    try:
        from getviews_pipeline.corpus_context import _anon_client
        from getviews_pipeline.niche_match import find_niche_match

        match = find_niche_match(_anon_client(), query)
        if match is not None:
            return match.label
    except Exception:
        pass
    return infer_niche_from_hashtags([], query) or "tiktok"


def _chunk_text(text: str, size: int = 20) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


def _sse_line(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def _classify_stream_error(exc: BaseException) -> str:
    msg = str(exc).lower()
    if isinstance(exc, asyncio.TimeoutError):
        return "analysis_timeout"
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 403:
        return "video_download_failed"
    if "unit limit" in msg or "daily unit limit" in msg:
        return "ensembledata_quota"
    exc_module = type(exc).__module__ or ""
    if exc_module.startswith("google"):
        return "gemini_error"
    return "stream_failed"


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


class ClassifyIntentRequest(BaseModel):
    query: str
    has_session: bool = False


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


@router.post("/classify-intent")
async def classify_intent_endpoint(
    body: ClassifyIntentRequest,
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Tier-3 semantic intent classification — no credit cost."""
    urls, handles = extract_urls_and_handles(body.query)
    det = classify_intent(body.query, urls, handles, body.has_session)
    gem = await run_sync(
        classify_intent_gemini,
        body.query,
        has_url=bool(urls),
        has_handle=bool(handles),
    )
    merged = merge_deterministic_with_gemini(det, gem)
    primary = str(merged.get("primary") or "follow_up")
    merged_out: dict[str, object] = dict(merged)
    merged_out["destination_or_format"] = destination_for_gemini_primary_label(primary)
    return JSONResponse(merged_out)


@router.post("/stream")
async def stream(
    request: Request,
    body: StreamRequest,
    user: dict = Depends(require_user),
) -> StreamingResponse:
    """SSE token stream for video analysis pipeline."""
    import uuid

    user_id: str = user["user_id"]
    access_token: str = user["access_token"]

    sb = user_supabase(access_token)

    try:
        sb.table("profiles").update({"is_processing": True}).eq("id", user_id).execute()
        rpc_resp = sb.rpc("decrement_credit", {"p_user_id": user_id}).execute()
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
                if _is_short_tiktok_url(url):
                    url = await run_sync(_resolve_short_url, url)
                pipeline_coro = run_video_diagnosis(url, session, questions=questions, user_message=body.query, step_queue=step_q)
            elif normalized == "compare_videos":
                # Wave 4 PR #2 — two URLs in one /stream call. Bundle
                # streaming: one start/done envelope around the pair;
                # per-side step events are suppressed inside
                # run_compare_pipeline so the FE doesn't have to
                # multiplex two parallel progress streams.
                url_a, url_b = _pick_two_video_urls(urls)
                if not url_a or not url_b:
                    seq += 1
                    yield _sse_line({
                        "stream_id": stream_id, "seq": seq,
                        "delta": "", "done": True,
                        "error": "missing_video_url",
                    })
                    sb.table("profiles").update(
                        {"is_processing": False},
                    ).eq("id", user_id).execute()
                    return
                if _is_short_tiktok_url(url_a):
                    url_a = await run_sync(_resolve_short_url, url_a)
                if _is_short_tiktok_url(url_b):
                    url_b = await run_sync(_resolve_short_url, url_b)
                pipeline_coro = run_compare_pipeline(
                    url_a, url_b, session,
                    user_message=body.query, step_queue=step_q,
                )
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
                logger.warning("Unexpected intent in /stream: %s — falling back to gemini_text_only", normalized)
                full_text = await run_sync(gemini_text_only, body.query, session)
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

            pipeline_task = asyncio.create_task(
                asyncio.wait_for(pipeline_coro, timeout=180.0)
            )

            while True:
                try:
                    event = await asyncio.wait_for(step_q.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    if pipeline_task.done():
                        while not step_q.empty():
                            event = step_q.get_nowait()
                            if event is None:
                                break
                            seq += 1
                            yield _sse_line({"stream_id": stream_id, "seq": seq, "step": event})
                        break
                    continue
                if event is None:
                    break
                seq += 1
                yield _sse_line({"stream_id": stream_id, "seq": seq, "step": event})

            out = await pipeline_task

            if normalized == "video_diagnosis":
                uv = out.get("user_video") or {}
                if uv.get("error"):
                    user_error_msg = uv.get("error_message")
                    error_code = uv.get("error") if isinstance(uv.get("error"), str) else "analysis_failed"
                    if user_error_msg:
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
                    for k in ("niche", "user_video", "reference_videos", "metadata", "analysis",
                              "content_type", "coverage", "follow_ups", "comment_radar", "thumbnail_analysis")
                    if k in out
                } or None
            elif normalized == "competitor_profile":
                full_text = (out.get("synthesis") or "").strip()
                structured = {k: out[k] for k in ("handle", "analyzed_videos", "follow_ups") if k in out} or None
            elif normalized == "content_directions":
                full_text = (out.get("synthesis") or "").strip()
                structured = {k: out[k] for k in ("niche", "directions", "analyzed_videos", "coverage", "follow_ups") if k in out} or None
            elif normalized == "own_channel":
                full_text = (out.get("synthesis") or "").strip()
                structured = {k: out[k] for k in ("niche", "analyzed_videos", "coverage", "follow_ups") if k in out} or None
            elif normalized == "brief_generation":
                full_text = (out.get("brief") or "").strip()
                structured = {k: out[k] for k in ("topic", "niche", "coverage", "follow_ups") if k in out} or None
            elif normalized == "trend_spike":
                full_text = (out.get("synthesis") or "").strip()
                structured = {k: out[k] for k in ("niche", "analyzed_videos", "coverage", "follow_ups", "patterns") if k in out} or None
            elif normalized == "shot_list":
                full_text = (out.get("shot_list") or "").strip()
                structured = {k: out[k] for k in ("topic", "niche", "coverage", "follow_ups") if k in out} or None
            elif normalized == "creator_search":
                full_text = (out.get("synthesis") or "").strip()
                structured = {k: out[k] for k in ("niche", "creators", "coverage", "follow_ups") if k in out} or None
            else:
                full_text = (out.get("synthesis") or out.get("diagnosis") or "").strip()
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
