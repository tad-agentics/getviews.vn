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
