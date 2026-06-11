"""TD-1 completion — failed paid turns must refund the deducted credits.

Audit 2026-06-10 finding C-1: ``append_turn`` deducted 1–3 credits before the
builder ran, and every failure path re-raised without compensation. A user
pasting one malformed compare link deterministically lost 2 credits; a Gemini
429 mid-build kept the charge. These tests pin the refund contract.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.answer_session import append_turn


def _mock_service_sb(session_fmt: str) -> MagicMock:
    sb = MagicMock()
    session_row = {
        "id": "sess-1",
        "user_id": "u1",
        "format": session_fmt,
        "niche_id": 2,
        "intent_type": "trend_spike",
    }

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "answer_sessions":
            chain = m.select.return_value.eq.return_value.single.return_value
            chain.execute.return_value = MagicMock(data=session_row)
            upd = m.update.return_value.eq.return_value
            upd.execute.return_value = MagicMock(data=[session_row])
        elif name == "answer_turns":
            m.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            m.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "turn-x", "turn_index": 0, "kind": "primary"}]
            )
        elif name == "usage_events":
            m.insert.return_value.execute.return_value = MagicMock(data=[])
        else:
            raise AssertionError(f"unexpected table {name!r}")
        return m

    sb.table.side_effect = table
    return sb


def _mock_user_sb(*, deduct_ok: bool = True) -> MagicMock:
    """User client whose ``decrement_credit`` RPC succeeds (or returns NULL)."""
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(data=5 if deduct_ok else None)
    return sb


@patch("getviews_pipeline.answer_session.refund_credits")
@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_pattern_report")
def test_builder_crash_refunds_primary_charge(
    mock_pattern: MagicMock,
    mock_get_svc: MagicMock,
    mock_user_supabase: MagicMock,
    mock_refund: MagicMock,
) -> None:
    """Pattern primary turn: deduct 1 → builder raises → refund 1 + re-raise."""
    mock_get_svc.return_value = _mock_service_sb("pattern")
    mock_user_supabase.return_value = _mock_user_sb()
    mock_pattern.side_effect = Exception("gemini exploded")

    with pytest.raises(Exception, match="gemini exploded"):
        append_turn(
            "u1",
            access_token="fake-jwt",
            session_id="sess-1",
            query="trend gì đang lên?",
            kind="primary",
        )

    mock_refund.assert_called_once()
    args, kwargs = mock_refund.call_args
    assert args[0] == "u1"
    assert args[1] == 1


@patch("getviews_pipeline.answer_session.refund_credits")
@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
def test_compare_missing_url_refunds_two_credits(
    mock_get_svc: MagicMock,
    mock_user_supabase: MagicMock,
    mock_refund: MagicMock,
) -> None:
    """Compare turn charges 2 up front; a query without two TikTok links
    raises ``missing_video_url`` — both credits must come back."""
    mock_get_svc.return_value = _mock_service_sb("compare")
    mock_user_supabase.return_value = _mock_user_sb()

    with pytest.raises(RuntimeError, match="missing_video_url"):
        append_turn(
            "u1",
            access_token="fake-jwt",
            session_id="sess-1",
            query="so sánh giúp mình",  # no URLs at all
            kind="primary",
        )

    mock_refund.assert_called_once()
    args, _ = mock_refund.call_args
    assert args[0] == "u1"
    assert args[1] == 2


@patch("getviews_pipeline.answer_session.refund_credits")
@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
def test_insufficient_credits_never_refunds(
    mock_get_svc: MagicMock,
    mock_user_supabase: MagicMock,
    mock_refund: MagicMock,
) -> None:
    """Deduction itself failing (NULL balance) is not a charge — no refund."""
    mock_get_svc.return_value = _mock_service_sb("pattern")
    mock_user_supabase.return_value = _mock_user_sb(deduct_ok=False)

    with pytest.raises(RuntimeError, match="insufficient_credits"):
        append_turn(
            "u1",
            access_token="fake-jwt",
            session_id="sess-1",
            query="trend gì đang lên?",
            kind="primary",
        )

    mock_refund.assert_not_called()


@patch("getviews_pipeline.answer_session.refund_credits")
@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_generic_report")
def test_free_follow_up_failure_refunds_nothing(
    mock_generic: MagicMock,
    mock_get_svc: MagicMock,
    mock_user_supabase: MagicMock,
    mock_refund: MagicMock,
) -> None:
    """Generic follow-ups are free — a crash there must not mint credits."""
    mock_get_svc.return_value = _mock_service_sb("pattern")
    mock_user_supabase.return_value = _mock_user_sb()
    mock_generic.side_effect = Exception("boom")

    with pytest.raises(Exception, match="boom"):
        append_turn(
            "u1",
            access_token="fake-jwt",
            session_id="sess-1",
            query="còn gì nữa không?",
            kind="generic",
        )

    mock_refund.assert_not_called()


# ---------------------------------------------------------------------------
# refund_credits helper
# ---------------------------------------------------------------------------


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_refund_credits_calls_service_rpc(mock_get_svc: MagicMock) -> None:
    from getviews_pipeline.credits import refund_credits

    rpc = mock_get_svc.return_value.rpc
    rpc.return_value.execute.return_value = MagicMock(data=7)

    assert refund_credits("u1", 2, context="test") is True
    rpc.assert_called_once_with("refund_credit", {"p_user_id": "u1", "p_amount": 2})


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_refund_credits_swallows_transport_errors(mock_get_svc: MagicMock) -> None:
    """A refund failure must not mask the original pipeline error."""
    from getviews_pipeline.credits import refund_credits

    mock_get_svc.return_value.rpc.side_effect = Exception("supabase down")
    assert refund_credits("u1", 1, context="test") is False  # no raise


def test_refund_credits_ignores_non_positive_amounts() -> None:
    from getviews_pipeline.credits import refund_credits

    assert refund_credits("u1", 0, context="test") is False
    assert refund_credits("u1", -3, context="test") is False
