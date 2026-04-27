"""Session context helpers for Cloud Run pipeline handlers.

Session context is reconstructed from Supabase ``chat_messages`` on each
``/stream`` request so that it is consistent across Cloud Run instances
(no in-process dict dependency).

The SSE replay buffer (``put_stream_chunks`` / ``get_stream_chunks``) remains
in-process and is intentionally best-effort — a reconnect to a different
instance gets a fresh stream rather than a replay. This is acceptable for MVP.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

_EMPTY_CONTEXT: dict[str, Any] = {
    "completed_intents": [],
    "niche": None,
    "analyses_summary": {
        "videos_analyzed": 0,
        "intents_run": [],
    },
}

# ── SSE replay buffer (in-process, best-effort) ────────────────────────────────
# Inherently per-instance. A reconnect to a different instance misses the cache
# and gets a fresh stream — acceptable at MVP scale.

# CLAUDE.md TD-4: 60s replay window. Past this the client's reconnect
# attempt falls through to a fresh stream rather than a replay.
_STREAM_REPLAY_TTL_SEC = 60.0
# How often the background sweeper runs. Half the TTL keeps mean
# residency for an expired entry under one TTL window without
# burning CPU.
_REPLAY_SWEEP_INTERVAL_SEC = 30.0
_stream_chunks: dict[str, dict[str, Any]] = {}


def put_stream_chunks(stream_id: str, chunks: list[str]) -> None:
    """Cache token chunks for reconnect replay (same seq indices as first send)."""
    _stream_chunks[stream_id] = {
        "chunks": chunks,
        "expires_at": time.monotonic() + _STREAM_REPLAY_TTL_SEC,
    }


def get_stream_chunks(stream_id: str) -> list[str] | None:
    entry = _stream_chunks.get(stream_id)
    if not entry:
        return None
    if time.monotonic() > float(entry["expires_at"]):
        _stream_chunks.pop(stream_id, None)
        return None
    return list(entry["chunks"])


def sweep_expired_stream_chunks(now: float | None = None) -> int:
    """Drop every replay entry whose TTL has passed.

    Without a sweep, lazy eviction (in ``get_stream_chunks``) only
    fires when the same stream_id is looked up again. Orphaned
    entries — client never reconnects — sat in memory forever on
    ``min-instances=1`` pods. Returns the number of entries removed
    so the lifespan task can log churn.
    """
    cutoff = now if now is not None else time.monotonic()
    expired = [sid for sid, entry in _stream_chunks.items() if cutoff > float(entry["expires_at"])]
    for sid in expired:
        _stream_chunks.pop(sid, None)
    return len(expired)


async def replay_buffer_sweeper(interval: float = _REPLAY_SWEEP_INTERVAL_SEC) -> None:
    """Long-running coroutine that periodically prunes the replay buffer.

    Started from the FastAPI lifespan; cancelled at shutdown. Logs at
    DEBUG when no entries expired and at INFO when at least one did,
    so production logs surface buffer churn without spamming.
    """
    while True:
        try:
            removed = sweep_expired_stream_chunks()
            if removed:
                logger.info("[replay-buffer] swept %d expired entries", removed)
            else:
                logger.debug("[replay-buffer] sweep ran, no entries expired")
        except Exception as exc:  # never let a sweep failure kill the loop
            logger.warning("[replay-buffer] sweep failed: %s", exc)
        await asyncio.sleep(interval)


# ── Session context from Supabase ──────────────────────────────────────────────

def fresh_session_context() -> dict[str, Any]:
    return copy.deepcopy(_EMPTY_CONTEXT)


def build_session_context_from_db(
    session_id: str,
    supabase: "Client",
    *,
    lookback: int = 10,
) -> dict[str, Any]:
    """Reconstruct pipeline session context from the last ``lookback`` chat messages.

    Reads ``chat_messages`` for ``session_id`` ordered by ``created_at`` desc,
    then walks them oldest-first to replay state mutations in order. Falls back
    to a fresh empty context on any DB error so the pipeline always gets a valid
    dict.

    Fields reconstructed (mirrors what pipelines read from ``session``):
    - ``niche``              — from the most recent message that has one
    - ``completed_intents``  — list of intent_type values seen in this session
    - ``analyses_summary``   — videos_analyzed + intents_run accumulated count
    - ``directions``         — from the most recent ``content_directions`` message
    - ``diagnosis``          — markdown string from the most recent ``video_diagnosis`` message
    - ``competitor_profile`` — from the most recent ``competitor_profile`` message
    """
    ctx = fresh_session_context()
    try:
        resp = (
            supabase.table("chat_messages")
            .select("intent_type, structured_output, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(lookback)
            .execute()
        )
        messages: list[dict[str, Any]] = resp.data or []
    except Exception as exc:
        logger.warning(
            "[session] DB fetch failed for session %s — using empty context: %s",
            session_id,
            exc,
        )
        return ctx

    # Walk oldest-first so later messages overwrite earlier ones
    for msg in reversed(messages):
        intent = msg.get("intent_type") or ""
        so: dict[str, Any] = msg.get("structured_output") or {}

        if not intent:
            continue

        # Track completed intents
        completed: list[str] = ctx.setdefault("completed_intents", [])
        if intent not in completed:
            completed.append(intent)

        # Accumulate analyses_summary
        summary: dict[str, Any] = ctx.setdefault("analyses_summary", {})
        analyzed = so.get("analyzed_videos") or so.get("reference_videos") or []
        summary["videos_analyzed"] = int(summary.get("videos_analyzed") or 0) + len(analyzed)
        ir: list[str] = list(summary.get("intents_run") or [])
        if intent not in ir:
            ir.append(intent)
        summary["intents_run"] = ir

        # Niche — always overwrite so the most recent message's niche wins.
        # Messages are walked oldest-first, so the last write here is the newest value.
        niche = so.get("niche")
        if niche:
            ctx["niche"] = niche

        # Intent-specific fields — set from the most recent message of that type
        if intent == "content_directions" and "directions" not in ctx:
            ctx["directions"] = so.get("directions") or []

        if intent == "video_diagnosis" and "diagnosis" not in ctx:
            # structured_output["diagnosis"] is the markdown string written by run_video_diagnosis.
            # structured_output["user_video"] is the raw analysis dict — do not use it here.
            md = so.get("diagnosis")
            if md and isinstance(md, str):
                ctx["diagnosis"] = md

        if intent == "competitor_profile" and "competitor_profile" not in ctx:
            ctx["competitor_profile"] = so.get("handle") or ""

    return ctx


# ── Legacy in-process store (tests / local dev only) ──────────────────────────
# Not used by production /stream handler. Kept for unit tests that run without
# a DB connection.

_store: dict[str, dict[str, Any]] = {}


def get_session_context(session_id: str) -> dict[str, Any]:
    """In-process fallback — use build_session_context_from_db in production."""
    if session_id not in _store:
        _store[session_id] = fresh_session_context()
    return _store[session_id]


def reset_session(session_id: str) -> None:
    _store[session_id] = fresh_session_context()


def record_intent_done(session: dict[str, Any], intent_value: str) -> None:
    completed = session.setdefault("completed_intents", [])
    summary = session.setdefault("analyses_summary", {"intents_run": []})
    if intent_value not in completed:
        completed.append(intent_value)
    if intent_value not in summary.get("intents_run", []):
        summary.setdefault("intents_run", []).append(intent_value)


def record_knowledge_turn(session: dict[str, Any]) -> None:
    record_intent_done(session, "knowledge")
