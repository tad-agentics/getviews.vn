"""Regression tests for turn-kind → builder dispatch in ``append_turn``.

Before this landed (2026-04-22 user report): every follow-up turn rebuilt
the session's primary report (e.g. pattern) regardless of whether the
user asked a timing question, a creator-search question, or a shot-list
question. Users saw the same report verbatim on every follow-up.

These tests pin the dispatch contract so a future refactor can't
silently regress it.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from getviews_pipeline.answer_session import append_turn, select_builder_for_turn


# -----------------------------------------------------------------------------
# Pure dispatch — select_builder_for_turn
# -----------------------------------------------------------------------------


def test_primary_turn_uses_session_format() -> None:
    assert select_builder_for_turn("pattern", "primary") == "pattern"
    assert select_builder_for_turn("ideas", "primary") == "ideas"
    assert select_builder_for_turn("timing", "primary") == "timing"
    assert select_builder_for_turn("generic", "primary") == "generic"


def test_primary_turn_clamps_unknown_session_format_to_pattern() -> None:
    # Defensive fallback — an unknown/corrupt session.format should not
    # blow up the builder dispatch.
    assert select_builder_for_turn("weird", "primary") == "pattern"


def test_timing_kind_always_picks_timing_builder() -> None:
    # Even when the session is Pattern, a timing follow-up gets a timing
    # report — the fix for the bug.
    assert select_builder_for_turn("pattern", "timing") == "timing"
    assert select_builder_for_turn("ideas", "timing") == "timing"
    assert select_builder_for_turn("generic", "timing") == "timing"


def test_script_kind_maps_to_ideas_builder() -> None:
    # Shot-list / script feedback lives on the ideas report (brief_generation).
    assert select_builder_for_turn("pattern", "script") == "ideas"


def test_creators_kind_maps_to_generic_builder() -> None:
    # No dedicated creators report yet — generic narrates corpus evidence.
    assert select_builder_for_turn("pattern", "creators") == "generic"


def test_unknown_kind_falls_back_to_generic() -> None:
    assert select_builder_for_turn("pattern", "mystery_kind") == "generic"


# -----------------------------------------------------------------------------
# Integration — append_turn calls the right builder for each kind
# -----------------------------------------------------------------------------


def _mock_supabase_for_turn(session_fmt: str) -> MagicMock:
    """Stitch a Supabase mock that answers ``append_turn``'s reads / inserts."""
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
            # PATCH path used at the end of append_turn.
            upd = m.update.return_value.eq.return_value
            upd.execute.return_value = MagicMock(data=[session_row])
        elif name == "answer_turns":
            # SELECT turn_index (list of existing turns) — empty so turn_index = 0
            m.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            # INSERT the new turn row.
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


def _fake_ideas_payload() -> dict[str, Any]:
    """Real fixture payload — guaranteed to validate against ReportV1.ideas."""
    from getviews_pipeline.report_ideas import build_fixture_ideas_report

    return build_fixture_ideas_report()


def _fake_timing_payload() -> dict[str, Any]:
    from getviews_pipeline.report_timing import build_fixture_timing_report

    return build_fixture_timing_report()


def _fake_generic_payload() -> dict[str, Any]:
    from getviews_pipeline.report_generic import build_fixture_generic_report

    return build_fixture_generic_report(query="stub")


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_pattern_report")
@patch("getviews_pipeline.answer_session.build_ideas_report")
@patch("getviews_pipeline.answer_session.build_timing_report")
@patch("getviews_pipeline.answer_session.build_generic_report")
def test_timing_follow_up_builds_timing_not_session_format(
    mock_generic: MagicMock,
    mock_timing: MagicMock,
    mock_ideas: MagicMock,
    mock_pattern: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    """Pattern session + timing follow-up → build_timing_report runs, NOT build_pattern_report."""
    mock_get_svc.return_value = _mock_supabase_for_turn("pattern")
    mock_timing.return_value = _fake_timing_payload()

    out = append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="khi nào nên post?",
        kind="timing",
    )
    # Dispatcher picked the timing builder.
    mock_timing.assert_called_once()
    # NOT the pattern builder.
    mock_pattern.assert_not_called()
    # The persisted payload has the timing shape, not pattern's.
    assert out["payload"]["kind"] == "timing"


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_pattern_report")
@patch("getviews_pipeline.answer_session.build_ideas_report")
@patch("getviews_pipeline.answer_session.build_timing_report")
@patch("getviews_pipeline.answer_session.build_generic_report")
def test_script_follow_up_builds_ideas_not_pattern(
    mock_generic: MagicMock,
    mock_timing: MagicMock,
    mock_ideas: MagicMock,
    mock_pattern: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    mock_get_svc.return_value = _mock_supabase_for_turn("pattern")
    mock_ideas.return_value = _fake_ideas_payload()

    out = append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="viết shot list giúp mình",
        kind="script",
    )
    mock_ideas.assert_called_once()
    mock_pattern.assert_not_called()
    assert out["payload"]["kind"] == "ideas"


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_pattern_report")
@patch("getviews_pipeline.answer_session.build_ideas_report")
@patch("getviews_pipeline.answer_session.build_timing_report")
@patch("getviews_pipeline.answer_session.build_generic_report")
def test_creators_follow_up_builds_generic(
    mock_generic: MagicMock,
    mock_timing: MagicMock,
    mock_ideas: MagicMock,
    mock_pattern: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    mock_get_svc.return_value = _mock_supabase_for_turn("pattern")
    mock_generic.return_value = _fake_generic_payload()

    out = append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="creator nào đang nổi lên",
        kind="creators",
    )
    mock_generic.assert_called_once()
    mock_pattern.assert_not_called()
    assert out["payload"]["kind"] == "generic"


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_pattern_report")
@patch("getviews_pipeline.answer_session.build_ideas_report")
@patch("getviews_pipeline.answer_session.build_timing_report")
@patch("getviews_pipeline.answer_session.build_generic_report")
def test_primary_turn_still_uses_session_format(
    mock_generic: MagicMock,
    mock_timing: MagicMock,
    mock_ideas: MagicMock,
    mock_pattern: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    """Primary turn on a Pattern session still runs the pattern builder —
    the fix must not regress the initial-turn behaviour."""
    mock_get_svc.return_value = _mock_supabase_for_turn("pattern")
    # Pattern builder needs a payload that validates — reuse the fixture.
    from getviews_pipeline.report_pattern import build_fixture_pattern_report

    mock_pattern.return_value = build_fixture_pattern_report()

    out = append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="xu hướng tuần này",
        kind="primary",
    )
    mock_pattern.assert_called_once()
    mock_timing.assert_not_called()
    mock_ideas.assert_not_called()
    assert out["payload"]["kind"] == "pattern"
