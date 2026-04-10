"""In-process session store — used for unit tests and single-request context.

In production, session state is persisted to Supabase `chat_sessions` by the
FastAPI request handlers. This module provides the same dict-based interface
so that intent-routing logic and tests can run without a database connection.
"""

from __future__ import annotations

import copy
import time
from typing import Any

_EMPTY_CONTEXT: dict[str, Any] = {
    "completed_intents": [],
    "niche": None,
    "analyses_summary": {
        "total_videos_analyzed": 0,
        "intents_run": [],
    },
}

_store: dict[str, dict[str, Any]] = {}

# SSE replay buffer (in-process; TD-4 style replay within TTL).
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


def fresh_session_context() -> dict[str, Any]:
    return copy.deepcopy(_EMPTY_CONTEXT)


def get_session_context(session_id: str) -> dict[str, Any]:
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
