"""C.1.2 — ANSWER_FIXTURE_PATTERN + create / get / patch flows (mocked Supabase)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.answer_session import (
    create_session,
    get_session_turns,
    patch_session,
)
from getviews_pipeline.report_pattern import ANSWER_FIXTURE_PATTERN
from getviews_pipeline.report_types import ReportV1


def test_answer_fixture_pattern_is_valid_report_v1() -> None:
    """Smoke: named fixture matches §J ReportV1 (pattern)."""
    r = ReportV1.model_validate(ANSWER_FIXTURE_PATTERN)
    assert r.kind == "pattern"
    assert r.report.confidence.sample_size == 47


@patch("getviews_pipeline.answer_session.get_service_client")
def test_create_session_inserts_row(mock_get: MagicMock) -> None:
    sid = "00000000-0000-0000-0000-000000000001"
    row = {
        "id": sid,
        "user_id": "u1",
        "niche_id": None,
        "title": "hello",
        "initial_q": "hello",
        "intent_type": "trend_spike",
        "format": "pattern",
    }
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.insert.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute.return_value = MagicMock(data=[row])
    mock_get.return_value = mock_sb

    out = create_session(
        "u1",
        initial_q="hello",
        intent_type="trend_spike",
        niche_id=None,
        format="pattern",
        idempotency_key=None,
    )
    assert out["id"] == sid
    chain.insert.assert_called_once()


@patch("getviews_pipeline.answer_session.get_service_client")
def test_create_session_idempotent_returns_cached_row(mock_get: MagicMock) -> None:
    """Second call with same Idempotency-Key hits DB select, not insert."""
    import getviews_pipeline.answer_session as mod

    mod._IDEMPOTENCY.clear()

    sid = "00000000-0000-0000-0000-000000000002"
    cached = {
        "id": sid,
        "user_id": "u1",
        "title": "q",
        "initial_q": "q",
        "intent_type": "trend_spike",
        "format": "pattern",
    }

    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.insert.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute.side_effect = [
        MagicMock(data=[cached]),  # insert().execute()
        MagicMock(data=cached),  # idempotent select().single().execute()
    ]
    mock_get.return_value = mock_sb

    out1 = create_session(
        "u1",
        initial_q="q",
        intent_type="trend_spike",
        niche_id=None,
        format="pattern",
        idempotency_key="idem-1",
    )
    assert out1["id"] == sid
    assert chain.insert.call_count == 1

    out2 = create_session(
        "u1",
        initial_q="different",
        intent_type="trend_spike",
        niche_id=None,
        format="pattern",
        idempotency_key="idem-1",
    )
    assert out2["id"] == sid
    assert chain.insert.call_count == 1
    mod._IDEMPOTENCY.clear()


@patch("getviews_pipeline.answer_session.get_service_client")
def test_get_session_turns_wrong_user(mock_get: MagicMock) -> None:
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute.return_value = MagicMock(
        data={"id": "s1", "user_id": "other", "initial_q": "x"}
    )
    mock_get.return_value = mock_sb

    with pytest.raises(PermissionError):
        get_session_turns("u1", "s1")


@patch("getviews_pipeline.answer_session.get_service_client")
def test_patch_session_updates_title(mock_get: MagicMock) -> None:
    mock_sb = MagicMock()
    chain = MagicMock()
    mock_sb.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.update.return_value = chain
    full_row = {
        "id": "s1",
        "user_id": "u1",
        "title": "New",
        "initial_q": "q",
        "intent_type": "trend_spike",
        "format": "pattern",
    }
    chain.execute.side_effect = [
        MagicMock(data={"user_id": "u1"}),
        MagicMock(),
        MagicMock(data=full_row),
    ]
    mock_get.return_value = mock_sb

    out = patch_session("u1", "s1", title="New")
    assert out["title"] == "New"
