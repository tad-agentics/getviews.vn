"""Phase 1.2 — Postgres-backed idempotency tests for create_session.

Tests the two-level (L1 in-process + L2 Postgres) idempotency introduced in
the 20260503000000 migration. Key scenario: same Idempotency-Key arriving on
two different Cloud Run instances (simulated by clearing _IDEMPOTENCY between
calls so the second call bypasses L1 and hits L2).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from getviews_pipeline.answer_session import (
    _idem_db_get,
    _idem_db_store,
    clean_expired_idempotency_rows,
    create_session,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_sb_mock(insert_row: dict, existing_session: dict | None = None) -> MagicMock:
    """Return a mock Supabase client whose chain returns consistent data."""
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.insert.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.delete.return_value = chain
    chain.lt.return_value = chain
    chain.on_conflict.return_value = chain
    chain.ignore.return_value = chain

    if existing_session:
        # For L2 check: first .single().execute() → the idempotency row,
        # second .single().execute() → the full session row
        chain.execute.side_effect = [
            MagicMock(data={"session_id": existing_session["id"]}),
            MagicMock(data=existing_session),
        ]
    else:
        # No L2 hit: first .single().execute() raises (no row found),
        # insert().execute() → new session, idem_db_store → ignored, L1 warm
        no_row = MagicMock()
        no_row.data = None
        chain.execute.side_effect = [
            MagicMock(data=None),  # L2 get → no existing mapping
            MagicMock(data=[insert_row]),  # answer_sessions.insert
            MagicMock(),  # idem_db_store
        ]
    return mock_sb


# ── _idem_db_get ──────────────────────────────────────────────────────────────


@patch("getviews_pipeline.answer_session.get_service_client")
def test_idem_db_get_returns_session_id(mock_get: MagicMock) -> None:
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute.return_value = MagicMock(data={"session_id": "abc-123"})

    result = _idem_db_get(mock_sb, "u1", "key-1")
    assert result == "abc-123"


@patch("getviews_pipeline.answer_session.get_service_client")
def test_idem_db_get_returns_none_on_error(mock_get: MagicMock) -> None:
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute.side_effect = Exception("DB error")

    result = _idem_db_get(mock_sb, "u1", "key-1")
    assert result is None  # fail-open


# ── create_session — cross-instance scenario ───────────────────────────────────


@patch("getviews_pipeline.answer_session.get_service_client")
def test_create_session_uses_l2_when_l1_cold(mock_get: MagicMock) -> None:
    """Simulates two Cloud Run instances with the same Idempotency-Key.

    The second instance has no L1 entry (cold cache). It must detect the
    existing session via L2 (Postgres) and NOT insert a duplicate row.
    """
    import getviews_pipeline.answer_session as mod

    mod._IDEMPOTENCY.clear()

    sid = "00000000-0000-0000-0000-000000000042"
    existing_session = {
        "id": sid, "user_id": "u1", "title": "q",
        "initial_q": "q", "intent_type": "trend_spike", "format": "pattern",
    }

    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.insert.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute.side_effect = [
        MagicMock(data={"session_id": sid}),  # L2 _idem_db_get → hit
        MagicMock(data=existing_session),      # answer_sessions SELECT full row
    ]
    mock_get.return_value = mock_sb

    out = create_session(
        "u1",
        initial_q="q",
        intent_type="trend_spike",
        niche_id=None,
        format="pattern",
        idempotency_key="idem-cross-instance",
    )

    assert out["id"] == sid
    # INSERT must NOT have been called — we replayed from L2
    insert_called = any(
        c == call("answer_sessions") for c in [mock_sb.table.call_args]
        if mock_sb.table.call_args is not None
    )
    # Verify only one table("answer_sessions") call happened (the SELECT, not INSERT)
    answer_sessions_calls = [
        c for c in mock_sb.table.call_args_list if c == call("answer_sessions")
    ]
    assert len(answer_sessions_calls) == 1, "Only SELECT should run, not INSERT"

    # L1 should now be warmed
    assert "u1:idem-cross-instance" in mod._IDEMPOTENCY

    mod._IDEMPOTENCY.clear()


@patch("getviews_pipeline.answer_session.get_service_client")
def test_create_session_different_users_same_key_independent(mock_get: MagicMock) -> None:
    """Two users with the same idempotency_key must create independent sessions."""
    import getviews_pipeline.answer_session as mod

    mod._IDEMPOTENCY.clear()

    sid_u1 = "00000000-0000-0000-0000-0000000000a1"
    sid_u2 = "00000000-0000-0000-0000-0000000000b2"
    row_u1 = {"id": sid_u1, "user_id": "u1", "title": "t", "initial_q": "t", "intent_type": "trend_spike", "format": "pattern"}
    row_u2 = {"id": sid_u2, "user_id": "u2", "title": "t", "initial_q": "t", "intent_type": "trend_spike", "format": "pattern"}

    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.insert.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.on_conflict.return_value = chain
    chain.ignore.return_value = chain
    chain.execute.side_effect = [
        MagicMock(data=None),       # L2 get u1 → miss
        MagicMock(data=[row_u1]),   # insert u1
        MagicMock(),                # idem store u1
        MagicMock(data=None),       # L2 get u2 → miss
        MagicMock(data=[row_u2]),   # insert u2
        MagicMock(),                # idem store u2
    ]
    mock_get.return_value = mock_sb

    out1 = create_session("u1", initial_q="t", intent_type="trend_spike", niche_id=None, format="pattern", idempotency_key="shared-key")
    out2 = create_session("u2", initial_q="t", intent_type="trend_spike", niche_id=None, format="pattern", idempotency_key="shared-key")

    assert out1["id"] == sid_u1
    assert out2["id"] == sid_u2

    mod._IDEMPOTENCY.clear()


# ── clean_expired_idempotency_rows ─────────────────────────────────────────────


def test_clean_expired_rows_counts_deleted() -> None:
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.delete.return_value = chain
    chain.lt.return_value = chain
    chain.execute.return_value = MagicMock(data=[{"user_id": "x"}, {"user_id": "y"}])

    count = clean_expired_idempotency_rows(mock_sb)
    assert count == 2


def test_clean_expired_rows_fails_open() -> None:
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.delete.return_value = chain
    chain.lt.return_value = chain
    chain.execute.side_effect = Exception("Supabase down")

    count = clean_expired_idempotency_rows(mock_sb)
    assert count == 0  # fail-open, never raises
