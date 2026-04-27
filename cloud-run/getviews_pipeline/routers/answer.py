"""Answer session routes (/answer/sessions, /answer/sessions/{id}/turns)."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any, Literal

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from getviews_pipeline.api_models import StrictBody

from getviews_pipeline.deps import require_user
from getviews_pipeline.runtime import run_sync
from getviews_pipeline.session_store import get_stream_chunks, put_stream_chunks

logger = logging.getLogger(__name__)

router = APIRouter()


def _sse_line(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


class AnswerSessionCreateBody(StrictBody):
    initial_q: str
    intent_type: str
    niche_id: int | None = None
    format: Literal["pattern", "ideas", "timing", "generic"] = "pattern"


class AnswerTurnAppendBody(StrictBody):
    query: str
    kind: Literal["primary", "timing", "creators", "script", "generic"] = "primary"
    classifier_confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    intent_id: str | None = Field(default=None, max_length=80)


class AnswerSessionPatchBody(StrictBody):
    title: str | None = None
    archived_at: str | None = None


def _classify_create_session_error(exc: Exception, niche_id: int | None) -> tuple[str, int]:
    msg = str(exc).lower()
    if "violates foreign key" in msg and "niche_id" in msg and niche_id is not None:
        return "invalid_niche", 400
    if "violates check constraint" in msg:
        return "invalid_payload", 400
    if "duplicate key" in msg:
        return "idempotency_conflict", 409
    return "start_failed", 500


@router.post("/answer/sessions")
async def answer_create_session(
    request: Request,
    body: AnswerSessionCreateBody,
    user: dict[str, Any] = Depends(require_user),
) -> JSONResponse:
    """Create an empty answer session (C.1). Optional Idempotency-Key header (120s)."""
    from getviews_pipeline.answer_session import create_session

    idem = request.headers.get("Idempotency-Key")
    logger.info(
        "[answer/sessions] POST user=%s fmt=%s intent=%s niche=%s idem=%s q_len=%d",
        user["user_id"], body.format, body.intent_type, body.niche_id, bool(idem), len(body.initial_q or ""),
    )
    try:
        row = await run_sync(
            create_session,
            user["user_id"],
            initial_q=body.initial_q,
            intent_type=body.intent_type,
            niche_id=body.niche_id,
            format=body.format,
            idempotency_key=idem,
        )
    except Exception as exc:
        code, status_code = _classify_create_session_error(exc, body.niche_id)
        logger.error("[answer/sessions] create failed code=%s user=%s niche=%s fmt=%s: %s", code, user["user_id"], body.niche_id, body.format, exc, exc_info=True)
        return JSONResponse({"error": code}, status_code=status_code)
    logger.info("[answer/sessions] created id=%s user=%s fmt=%s", row.get("id"), user["user_id"], body.format)
    return JSONResponse(row)


@router.post("/answer/sessions/{session_id}/turns")
async def answer_append_turn(
    session_id: str,
    body: AnswerTurnAppendBody,
    user: dict[str, Any] = Depends(require_user),
    resume_stream_id: str | None = Query(None),
    resume_from_seq: int | None = Query(None, ge=0),
) -> StreamingResponse:
    """Append primary or follow-up turn, streamed as SSE with TD-4 replay."""
    from getviews_pipeline.answer_session import append_turn

    async def event_generator() -> AsyncIterator[bytes]:
        stream_id = resume_stream_id or str(uuid.uuid4())
        seq = resume_from_seq or 0

        if resume_stream_id and resume_from_seq is not None:
            cached = get_stream_chunks(resume_stream_id)
            if cached:
                # Each item carries the seq the client saw on the live
                # wire. Re-emit any seq above last_seq verbatim, then
                # close with the exact same done-seq used live.
                replayed_any = False
                last_replay_seq = int(resume_from_seq)
                for item in cached:
                    item_seq = int(item.get("seq") or 0)
                    if item_seq <= resume_from_seq:
                        continue
                    # ``done`` is part of the cached item for the
                    # terminal frame; everything else flushes as
                    # done=False.
                    is_terminal = bool(item.get("done"))
                    yield _sse_line({"stream_id": stream_id, **item} if is_terminal
                                    else {"stream_id": stream_id, **item, "done": False})
                    last_replay_seq = item_seq
                    replayed_any = True
                    await asyncio.sleep(0.005)
                if replayed_any:
                    return
                logger.info(
                    "[answer/turns] cached but everything ≤ resume_from_seq — running fresh stream_id=%s last_seq=%d",
                    resume_stream_id, last_replay_seq,
                )
            else:
                logger.info("[answer/turns] resume cache miss stream_id=%s — running fresh", resume_stream_id)

        try:
            out = await run_sync(
                append_turn,
                user["user_id"],
                user["access_token"],
                session_id,
                query=body.query,
                kind=body.kind,
                classifier_confidence_score=body.classifier_confidence_score,
                intent_id=body.intent_id,
            )
        except PermissionError:
            seq += 1
            yield _sse_line({"stream_id": stream_id, "seq": seq, "done": True, "error": "session_not_found"})
            return
        except RuntimeError as exc:
            if str(exc) == "insufficient_credits":
                seq += 1
                yield _sse_line({"stream_id": stream_id, "seq": seq, "done": True, "error": "insufficient_credits"})
                return
            raise
        except Exception as exc:
            logger.exception("[answer/turns] append failed: %s", exc)
            seq += 1
            yield _sse_line({"stream_id": stream_id, "seq": seq, "done": True, "error": "stream_failed"})
            return

        seq += 1
        report_payload = out.get("payload", out)
        turn_meta = out.get("turn")
        payload_seq = seq
        payload_item = {"seq": payload_seq, "payload": report_payload, "turn": turn_meta}
        yield _sse_line({"stream_id": stream_id, **payload_item, "done": False})

        seq += 1
        done_seq = seq
        done_item = {"seq": done_seq, "delta": "", "done": True}
        yield _sse_line({"stream_id": stream_id, **done_item})

        # Cache the exact items (with their original seq) so a reconnect
        # replays the same wire-level frames.
        put_stream_chunks(stream_id, [payload_item, done_item])

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/answer/sessions")
async def answer_list_sessions(
    user: dict[str, Any] = Depends(require_user),
    limit: int = Query(20, ge=1, le=100),
    include_archived: bool = False,
    scope: Literal["30d", "all"] = Query("30d"),
    cursor: str | None = Query(None),
) -> JSONResponse:
    """Drawer default ``scope=30d``; ``scope=all`` for unbounded history-style lists."""
    from getviews_pipeline.answer_session import list_sessions

    rows = await run_sync(list_sessions, user["user_id"], limit=limit, include_archived=include_archived, scope=scope, cursor=cursor)
    next_cursor: str | None = None
    if rows and len(rows) == limit:
        last = rows[-1].get("updated_at")
        if last is not None:
            next_cursor = last if isinstance(last, str) else getattr(last, "isoformat", lambda: str(last))()
    return JSONResponse({"sessions": rows, "next_cursor": next_cursor})


@router.get("/answer/sessions/{session_id}")
async def answer_get_session(session_id: str, user: dict[str, Any] = Depends(require_user)) -> JSONResponse:
    from getviews_pipeline.answer_session import get_session_turns

    try:
        session, turns = await run_sync(get_session_turns, user["user_id"], session_id)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")
    return JSONResponse({"session": session, "turns": turns})


@router.patch("/answer/sessions/{session_id}")
async def answer_patch_session(
    session_id: str,
    body: AnswerSessionPatchBody,
    user: dict[str, Any] = Depends(require_user),
) -> JSONResponse:
    from getviews_pipeline.answer_session import patch_session

    try:
        row = await run_sync(patch_session, user["user_id"], session_id, title=body.title, archived_at=body.archived_at)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")
    return JSONResponse(row)
