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

from getviews_pipeline.answer_session import (
    append_turn,
    lifecycle_mode_for_intent,
    select_builder_for_turn,
)


# -----------------------------------------------------------------------------
# Pure dispatch — select_builder_for_turn
# -----------------------------------------------------------------------------


def test_primary_turn_uses_session_format() -> None:
    assert select_builder_for_turn("pattern", "primary") == "pattern"
    assert select_builder_for_turn("ideas", "primary") == "ideas"
    assert select_builder_for_turn("timing", "primary") == "timing"
    assert select_builder_for_turn("generic", "primary") == "generic"
    # Lifecycle template (2026-04-22) — primary turns on lifecycle
    # sessions must dispatch to the lifecycle builder.
    assert select_builder_for_turn("lifecycle", "primary") == "lifecycle"
    # Diagnostic template (2026-04-22) — own_flop_no_url sessions must
    # dispatch to the diagnostic builder, not pattern.
    assert select_builder_for_turn("diagnostic", "primary") == "diagnostic"


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


def _mock_supabase_for_turn(
    session_fmt: str,
    *,
    intent_type: str = "trend_spike",
) -> MagicMock:
    """Stitch a Supabase mock that answers ``append_turn``'s reads / inserts.

    ``intent_type`` matters for the lifecycle builder (it maps to the
    ``LifecyclePayload.mode`` discriminator); default is ``trend_spike``
    so existing Pattern/Ideas/Timing tests stay unchanged.
    """
    sb = MagicMock()

    session_row = {
        "id": "sess-1",
        "user_id": "u1",
        "format": session_fmt,
        "niche_id": 2,
        "intent_type": intent_type,
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


# -----------------------------------------------------------------------------
# content_calendar absorption — 2026-04-22 (PR #91 timing calendar)
# -----------------------------------------------------------------------------


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_pattern_report")
@patch("getviews_pipeline.answer_session.build_ideas_report")
@patch("getviews_pipeline.answer_session.build_timing_report")
@patch("getviews_pipeline.answer_session.build_generic_report")
def test_content_calendar_intent_passes_calendar_mode_to_timing(
    mock_generic: MagicMock,
    mock_timing: MagicMock,
    mock_ideas: MagicMock,
    mock_pattern: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    """2026-04-22 content_calendar absorption: a session with
    ``intent_type = 'content_calendar'`` and ``format = 'timing'`` must
    call ``build_timing_report`` with ``mode='calendar'`` so the
    expanded ``TimingPayload.calendar_slots`` gets populated. Before
    this change, content_calendar was force-fit into pattern and
    returned a hook leaderboard for a scheduling question."""
    mock_get_svc.return_value = _mock_supabase_for_turn(
        "timing", intent_type="content_calendar",
    )
    mock_timing.return_value = _fake_timing_payload()

    append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="lên lịch post tuần tới cho mình",
        kind="primary",
    )

    mock_timing.assert_called_once()
    # Mode is a kwarg in the new signature.
    _, kwargs = mock_timing.call_args
    assert kwargs.get("mode") == "calendar", (
        "content_calendar intent must dispatch with mode='calendar' so "
        "calendar_slots populates in the payload"
    )
    mock_pattern.assert_not_called()


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_timing_report")
def test_timing_intent_does_not_force_calendar_mode(
    mock_timing: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    """A regular ``timing`` intent must NOT force calendar mode — the
    builder falls back to its keyword heuristic (empty query keywords =
    no calendar). Protects against the dispatcher regressing to always
    populate slots."""
    mock_get_svc.return_value = _mock_supabase_for_turn(
        "timing", intent_type="timing",
    )
    mock_timing.return_value = _fake_timing_payload()

    append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="giờ nào post tốt nhất?",
        kind="primary",
    )

    mock_timing.assert_called_once()
    _, kwargs = mock_timing.call_args
    assert kwargs.get("mode") is None


# -----------------------------------------------------------------------------
# Lifecycle template — 2026-04-22 (commit 3b)
# -----------------------------------------------------------------------------


def test_lifecycle_mode_for_intent_maps_three_intents() -> None:
    assert lifecycle_mode_for_intent("format_lifecycle_optimize") == "format"
    assert lifecycle_mode_for_intent("fatigue") == "hook_fatigue"
    assert lifecycle_mode_for_intent("subniche_breakdown") == "subniche"


def test_lifecycle_mode_for_intent_defaults_to_format() -> None:
    # Missing / unknown intent types fall back to the safest mode so a
    # lifecycle session never fails to build.
    assert lifecycle_mode_for_intent(None) == "format"
    assert lifecycle_mode_for_intent("") == "format"
    assert lifecycle_mode_for_intent("trend_spike") == "format"


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_pattern_report")
@patch("getviews_pipeline.answer_session.build_ideas_report")
@patch("getviews_pipeline.answer_session.build_timing_report")
@patch("getviews_pipeline.answer_session.build_generic_report")
@patch("getviews_pipeline.answer_session.build_lifecycle_report")
def test_lifecycle_primary_turn_dispatches_to_lifecycle_builder(
    mock_lifecycle: MagicMock,
    mock_generic: MagicMock,
    mock_timing: MagicMock,
    mock_ideas: MagicMock,
    mock_pattern: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    """Lifecycle session + primary turn → build_lifecycle_report runs.

    Previously ``format_lifecycle_optimize`` / ``fatigue`` / ``subniche_
    breakdown`` were routed through ``answer:pattern`` and rendered a
    hook leaderboard — not the stage pill / reach delta / health score
    shape users actually need. Pin the new dispatch behaviour here.
    """
    from getviews_pipeline.report_lifecycle import build_fixture_lifecycle_report

    mock_get_svc.return_value = _mock_supabase_for_turn(
        "lifecycle", intent_type="format_lifecycle_optimize"
    )
    mock_lifecycle.return_value = build_fixture_lifecycle_report("format")

    out = append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="30s vs 60s format nào tốt hơn",
        kind="primary",
    )
    mock_lifecycle.assert_called_once()
    # Mode keyword must be the format mapped from intent_type.
    call_args = mock_lifecycle.call_args
    # build_lifecycle_report(niche_pk, query, mode, window_days=...)
    assert call_args.args[2] == "format"
    mock_pattern.assert_not_called()
    mock_timing.assert_not_called()
    mock_ideas.assert_not_called()
    mock_generic.assert_not_called()
    assert out["payload"]["kind"] == "lifecycle"


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_lifecycle_report")
def test_lifecycle_fatigue_intent_sets_hook_fatigue_mode(
    mock_lifecycle: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    from getviews_pipeline.report_lifecycle import build_fixture_lifecycle_report

    mock_get_svc.return_value = _mock_supabase_for_turn(
        "lifecycle", intent_type="fatigue"
    )
    mock_lifecycle.return_value = build_fixture_lifecycle_report("hook_fatigue")

    append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="hook này còn hiệu quả không",
        kind="primary",
    )
    assert mock_lifecycle.call_args.args[2] == "hook_fatigue"


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_lifecycle_report")
def test_lifecycle_subniche_intent_sets_subniche_mode(
    mock_lifecycle: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    from getviews_pipeline.report_lifecycle import build_fixture_lifecycle_report

    mock_get_svc.return_value = _mock_supabase_for_turn(
        "lifecycle", intent_type="subniche_breakdown"
    )
    mock_lifecycle.return_value = build_fixture_lifecycle_report("subniche")

    append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="ngách con nào đang nổi",
        kind="primary",
    )
    assert mock_lifecycle.call_args.args[2] == "subniche"


# -----------------------------------------------------------------------------
# Diagnostic template — 2026-04-22 (commit 4b)
# -----------------------------------------------------------------------------


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_pattern_report")
@patch("getviews_pipeline.answer_session.build_ideas_report")
@patch("getviews_pipeline.answer_session.build_timing_report")
@patch("getviews_pipeline.answer_session.build_generic_report")
@patch("getviews_pipeline.answer_session.build_lifecycle_report")
@patch("getviews_pipeline.answer_session.build_diagnostic_report")
def test_diagnostic_primary_turn_dispatches_to_diagnostic_builder(
    mock_diagnostic: MagicMock,
    mock_lifecycle: MagicMock,
    mock_generic: MagicMock,
    mock_timing: MagicMock,
    mock_ideas: MagicMock,
    mock_pattern: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    """Diagnostic session + primary turn → build_diagnostic_report runs.

    Before this wiring, ``own_flop_no_url`` routed to ``answer:pattern``
    and returned a niche hook leaderboard for someone asking about their
    flopped video. Pin the new dispatch behaviour here.
    """
    from getviews_pipeline.report_diagnostic import build_fixture_diagnostic_report

    mock_get_svc.return_value = _mock_supabase_for_turn(
        "diagnostic", intent_type="own_flop_no_url",
    )
    mock_diagnostic.return_value = build_fixture_diagnostic_report()

    out = append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="video tuần trước flop mà mình không còn link",
        kind="primary",
    )
    mock_diagnostic.assert_called_once()
    mock_pattern.assert_not_called()
    mock_timing.assert_not_called()
    mock_ideas.assert_not_called()
    mock_generic.assert_not_called()
    mock_lifecycle.assert_not_called()
    assert out["payload"]["kind"] == "diagnostic"


@patch("getviews_pipeline.supabase_client.user_supabase")
@patch("getviews_pipeline.answer_session.get_service_client")
@patch("getviews_pipeline.answer_session.build_diagnostic_report")
def test_diagnostic_builder_receives_query_and_window_days(
    mock_diagnostic: MagicMock,
    mock_get_svc: MagicMock,
    _mock_user_sb: MagicMock,
) -> None:
    """Diagnostic is Gemini-heavy — the builder needs the query threaded
    through so follow-up turns produce different framings."""
    from getviews_pipeline.report_diagnostic import build_fixture_diagnostic_report

    mock_get_svc.return_value = _mock_supabase_for_turn(
        "diagnostic", intent_type="own_flop_no_url",
    )
    mock_diagnostic.return_value = build_fixture_diagnostic_report()

    append_turn(
        "u1",
        access_token="fake-jwt",
        session_id="sess-1",
        query="pacing chậm + CTA yếu",
        kind="primary",
    )
    args, kwargs = mock_diagnostic.call_args
    # Positional: niche_pk, query
    assert args[1] == "pacing chậm + CTA yếu"
    # window_days passed as kwarg.
    assert "window_days" in kwargs
