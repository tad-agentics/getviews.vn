"""Session context reconstruction tests (offline, no DB connection).

Tests build_session_context_from_db() which was introduced in b67cdc9 to fix
the in-process dict that was lost between Cloud Run instances.  All Supabase
calls are mocked via unittest.mock.MagicMock.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from getviews_pipeline.session_store import (
    build_session_context_from_db,
    fresh_session_context,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_supabase(messages: list[dict]) -> MagicMock:
    """Return a mock Supabase client whose chat_messages query returns *messages*."""
    mock_resp = MagicMock()
    mock_resp.data = messages

    # Chain: supabase.table(...).select(...).eq(...).order(...).limit(...).execute()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = mock_resp

    sb = MagicMock()
    sb.table.return_value = chain
    return sb


def _msg(intent: str, so: dict | None = None) -> dict:
    """Shorthand to build a chat_messages row dict."""
    return {
        "intent_type": intent,
        "structured_output": so or {},
        "created_at": "2026-01-01T00:00:00Z",
    }


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_returns_fresh_context_when_no_messages_exist():
    """Empty data → context equals fresh_session_context() shape."""
    sb = _make_supabase([])
    ctx = build_session_context_from_db("session-empty", sb)

    assert ctx["completed_intents"] == []
    assert ctx["niche"] is None
    # analyses_summary may use either key depending on which setdefault branch ran
    summary = ctx.get("analyses_summary", {})
    videos = summary.get("videos_analyzed", 0) + summary.get("total_videos_analyzed", 0)
    assert videos == 0


def test_reconstructs_completed_intents_from_message_history():
    """Three distinct intents → all appear in completed_intents, in order."""
    messages = [
        # DB returns desc order (newest first); build_session_context walks reversed
        _msg("trend_spike"),
        _msg("content_directions"),
        _msg("video_diagnosis"),
    ]
    sb = _make_supabase(messages)
    ctx = build_session_context_from_db("session-intents", sb)

    # After reversing the desc list: video_diagnosis, content_directions, trend_spike
    assert ctx["completed_intents"] == ["video_diagnosis", "content_directions", "trend_spike"]


def test_niche_first_seen_wins_oldest_first_walk():
    """Niche uses `not ctx.get("niche")` guard → oldest message's niche is kept.

    The DB query returns rows desc (newest first).  build_session_context_from_db
    reverses the list before iterating, so it walks oldest → newest.  The guard
    `if niche and not ctx.get("niche")` means the *first* niche encountered
    (oldest message) wins and subsequent messages cannot overwrite it.

    Messages returned by DB (desc): fitness (newest) → skincare (oldest)
    After reverse: skincare first → fitness second
    Expected: niche == "skincare"
    """
    messages = [
        _msg("video_diagnosis", {"niche": "fitness"}),   # newest (index 0 from DB)
        _msg("video_diagnosis", {"niche": "skincare"}),  # oldest (index 1 from DB)
    ]
    sb = _make_supabase(messages)
    ctx = build_session_context_from_db("session-niche", sb)

    assert ctx["niche"] == "skincare"


def test_accumulates_videos_analyzed_across_messages():
    """reference_videos lists from two messages are accumulated in analyses_summary."""
    ref_videos = [{"id": f"v{i}"} for i in range(3)]
    messages = [
        # Desc order from DB
        _msg("video_diagnosis", {"reference_videos": ref_videos}),
        _msg("video_diagnosis", {"reference_videos": ref_videos}),
    ]
    sb = _make_supabase(messages)
    ctx = build_session_context_from_db("session-vids", sb)

    assert ctx["analyses_summary"]["videos_analyzed"] == 6


def test_falls_back_to_fresh_context_on_db_error():
    """Any DB exception → returns fresh_session_context() without raising."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.side_effect = RuntimeError("connection refused")

    sb = MagicMock()
    sb.table.return_value = chain

    ctx = build_session_context_from_db("session-error", sb)

    expected = fresh_session_context()
    assert ctx["completed_intents"] == expected["completed_intents"]
    assert ctx["niche"] == expected["niche"]
