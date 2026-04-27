"""list_sessions scope + cursor (Phase C.1)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from getviews_pipeline.answer_session import list_sessions


def _mock_chain():
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.gte.return_value = chain
    chain.lt.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    return mock_sb, chain


@patch("getviews_pipeline.answer_session.get_service_client")
def test_list_sessions_30d_calls_gte(mock_get):
    mock_sb, chain = _mock_chain()
    mock_get.return_value = mock_sb
    list_sessions("u1", scope="30d")
    chain.gte.assert_called_once()
    assert chain.gte.call_args[0][0] == "updated_at"


@patch("getviews_pipeline.answer_session.get_service_client")
def test_list_sessions_all_skips_gte(mock_get):
    mock_sb, chain = _mock_chain()
    mock_get.return_value = mock_sb
    list_sessions("u1", scope="all")
    chain.gte.assert_not_called()


@patch("getviews_pipeline.answer_session.get_service_client")
def test_list_sessions_cursor_calls_lt(mock_get):
    mock_sb, chain = _mock_chain()
    mock_get.return_value = mock_sb
    list_sessions("u1", scope="all", cursor="2026-01-01T00:00:00+00:00")
    chain.lt.assert_called_once_with("updated_at", "2026-01-01T00:00:00+00:00")


# ── A2: turn_count enrichment ────────────────────────────────────────


def _mock_with_turns(session_rows, turn_rows):
    """Mock service client where the FIRST .execute() returns session
    rows, the SECOND returns answer_turns rows for batched count
    enrichment. Mirrors the two-query pattern in ``list_sessions``."""
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.gte.return_value = chain
    chain.lt.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.in_.return_value = chain
    chain.execute.side_effect = [MagicMock(data=session_rows), MagicMock(data=turn_rows)]
    return mock_sb


@patch("getviews_pipeline.answer_session.get_service_client")
def test_list_sessions_attaches_turn_count_per_session(mock_get):
    sessions_in = [
        {"id": "s-a", "user_id": "u1", "updated_at": "2026-06-01T00:00:00+00:00"},
        {"id": "s-b", "user_id": "u1", "updated_at": "2026-06-01T01:00:00+00:00"},
        {"id": "s-c", "user_id": "u1", "updated_at": "2026-06-01T02:00:00+00:00"},
    ]
    turn_rows = [
        {"session_id": "s-a"},
        {"session_id": "s-a"},
        {"session_id": "s-a"},
        {"session_id": "s-b"},
    ]
    mock_get.return_value = _mock_with_turns(sessions_in, turn_rows)
    out = list_sessions("u1", scope="all")
    counts = {s["id"]: s["turn_count"] for s in out}
    assert counts == {"s-a": 3, "s-b": 1, "s-c": 0}


@patch("getviews_pipeline.answer_session.get_service_client")
def test_list_sessions_empty_returns_no_extra_query(mock_get):
    """No sessions → don't run the answer_turns batch query."""
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.gte.return_value = chain
    chain.lt.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    mock_get.return_value = mock_sb
    out = list_sessions("u1", scope="30d")
    assert out == []
    # Only ONE execute() call (the sessions query); no in_() filter.
    chain.in_.assert_not_called()


@patch("getviews_pipeline.answer_session.get_service_client")
def test_list_sessions_turn_count_is_zero_when_enrichment_query_fails(mock_get):
    """Non-fatal: the drawer renders without ``turn_count`` rather than
    crashing the whole list query."""
    sessions_in = [{"id": "s-a", "user_id": "u1", "updated_at": "2026-06-01T00:00:00+00:00"}]
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.gte.return_value = chain
    chain.lt.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.in_.return_value = chain
    # First execute() returns sessions, second raises.
    chain.execute.side_effect = [MagicMock(data=sessions_in), RuntimeError("turns query down")]
    mock_get.return_value = mock_sb
    out = list_sessions("u1", scope="all")
    assert out[0]["turn_count"] == 0
