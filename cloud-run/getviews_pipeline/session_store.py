"""Session context helpers for Cloud Run pipeline handlers.

Session context is reconstructed from Supabase ``chat_messages`` on each
``/stream`` request so that it is consistent across Cloud Run instances
(no in-process dict dependency).

The SSE replay buffer (``put_stream_chunks`` / ``get_stream_chunks``) remains
in-process and is intentionally best-effort — a reconnect to a different
instance gets a fresh stream rather than a replay. This is acceptable for MVP.
"""

from __future__ import annotations

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
        "total_videos_analyzed": 0,
        "intents_run": [],
    },
}

# ── SSE replay buffer (in-process, best-effort) ────────────────────────────────
# Inherently per-instance. A reconnect to a different instance misses the cache
# and gets a fresh stream — acceptable at MVP scale.

_STREAM_REPLAY_TTL_SEC = 120.0
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
    - ``niche``              — from any message with a niche in structured_output
    - ``completed_intents``  — list of intent_type values seen in this session
    - ``analyses_summary``   — videos_analyzed + intents_run accumulated count
    - ``directions``         — from the most recent ``content_directions`` message
    - ``diagnosis``          — from the most recent ``video_diagnosis`` message
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

        # Niche — prefer the most recent message that has one
        niche = so.get("niche")
        if niche and not ctx.get("niche"):
            ctx["niche"] = niche

        # Intent-specific fields — set from the most recent message of that type
        if intent == "content_directions" and "directions" not in ctx:
            ctx["directions"] = so.get("directions") or []

        if intent == "video_diagnosis" and "diagnosis" not in ctx:
            uv = so.get("user_video") or {}
            if uv:
                ctx["diagnosis"] = uv

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
