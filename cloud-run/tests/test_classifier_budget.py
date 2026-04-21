"""Phase C.0.1 — CLASSIFIER_GEMINI_DAILY_MAX guard for classify_intent_gemini.

D.2.3 additions at the bottom: observability events fired from
``answer_session.append_turn`` (classifier_low_confidence +
pattern_what_stalled_empty).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from getviews_pipeline import config as gv_config
from getviews_pipeline.answer_session import (
    CLASSIFIER_LOW_CONFIDENCE_THRESHOLD,
    _confidence_label,
    log_usage_event_server,
    resolve_turn_observability_events,
)
from getviews_pipeline.ensemble import (
    ClassifierDailyBudgetExceeded,
    consume_classifier_gemini_budget_or_raise,
    reset_classifier_gemini_budget_for_tests,
)
from getviews_pipeline.gemini import classify_intent_gemini


def test_consume_raises_after_max(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gv_config, "CLASSIFIER_GEMINI_DAILY_MAX", 2)
    reset_classifier_gemini_budget_for_tests()
    consume_classifier_gemini_budget_or_raise()
    consume_classifier_gemini_budget_or_raise()
    with pytest.raises(ClassifierDailyBudgetExceeded) as exc_info:
        consume_classifier_gemini_budget_or_raise()
    assert "Classifier Gemini daily budget" in str(exc_info.value)


def _fake_gemini_json_response() -> Any:
    class _R:
        text = '{"primary": "follow_up", "secondary": null, "niche_hint": null}'

    return _R()


def test_classify_intent_gemini_fallback_when_budget_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second call skips Gemini when daily budget already consumed."""
    monkeypatch.setattr(gv_config, "CLASSIFIER_GEMINI_DAILY_MAX", 1)
    reset_classifier_gemini_budget_for_tests()
    monkeypatch.setattr(
        "getviews_pipeline.gemini._generate_content_models",
        lambda *a, **k: _fake_gemini_json_response(),
    )
    classify_intent_gemini("hello world", has_url=False, has_handle=False)
    out = classify_intent_gemini("second query", has_url=False, has_handle=False)
    assert out["primary"] == "follow_up"
    assert out["secondary"] is None


def test_classify_intent_gemini_structural_fallback_when_budget_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gv_config, "CLASSIFIER_GEMINI_DAILY_MAX", 1)
    reset_classifier_gemini_budget_for_tests()
    monkeypatch.setattr(
        "getviews_pipeline.gemini._generate_content_models",
        lambda *a, **k: _fake_gemini_json_response(),
    )
    url = "https://www.tiktok.com/@x/video/1"
    classify_intent_gemini(f"why {url}", has_url=True, has_handle=False)
    out = classify_intent_gemini(f"again {url}", has_url=True, has_handle=False)
    assert out["primary"] == "video_diagnosis"


# ── D.2.3 — observability event predicates ────────────────────────────────


def test_confidence_label_threshold_boundaries() -> None:
    """Label derivation lives inside append_turn; lock in the boundaries."""
    assert _confidence_label(None) == "medium"
    assert _confidence_label(0.9) == "high"
    assert _confidence_label(0.8) == "high"
    assert _confidence_label(0.79) == "medium"
    assert _confidence_label(CLASSIFIER_LOW_CONFIDENCE_THRESHOLD) == "medium"
    assert _confidence_label(CLASSIFIER_LOW_CONFIDENCE_THRESHOLD - 0.01) == "low"
    assert _confidence_label(0.0) == "low"


def test_resolve_turn_observability_events_fires_low_confidence() -> None:
    """Score below the threshold → classifier_low_confidence with full metadata."""
    events = resolve_turn_observability_events(
        fmt="generic",
        payload={"what_stalled": [], "confidence": {}},
        classifier_confidence_score=0.42,
        intent_id="trend_spike",
        niche_id=3,
        session_id="sess-1",
        turn_index=2,
    )
    assert any(action == "classifier_low_confidence" for action, _ in events)
    action, meta = next(e for e in events if e[0] == "classifier_low_confidence")
    assert meta == {
        "intent_id": "trend_spike",
        "confidence_score": 0.42,
        "session_id": "sess-1",
        "turn_index": 2,
    }


def test_resolve_turn_observability_events_no_event_when_score_missing_or_high() -> None:
    """No score → no event; ≥ threshold → no event."""
    events_none = resolve_turn_observability_events(
        fmt="pattern",
        payload={"what_stalled": ["x"], "confidence": {}},
        classifier_confidence_score=None,
        intent_id="trend_spike",
        niche_id=3,
        session_id="sess-1",
        turn_index=0,
    )
    assert not any(a == "classifier_low_confidence" for a, _ in events_none)

    events_high = resolve_turn_observability_events(
        fmt="pattern",
        payload={"what_stalled": ["x"], "confidence": {}},
        classifier_confidence_score=0.85,
        intent_id="trend_spike",
        niche_id=3,
        session_id="sess-1",
        turn_index=0,
    )
    assert not any(a == "classifier_low_confidence" for a, _ in events_high)


def test_resolve_turn_observability_events_fires_pattern_what_stalled_empty() -> None:
    """pattern format + empty what_stalled + non-null reason → event with niche_id."""
    events = resolve_turn_observability_events(
        fmt="pattern",
        payload={
            "what_stalled": [],
            "confidence": {"what_stalled_reason": "thin_corpus"},
        },
        classifier_confidence_score=0.9,
        intent_id="trend_spike",
        niche_id=7,
        session_id="sess-2",
        turn_index=0,
    )
    assert any(a == "pattern_what_stalled_empty" for a, _ in events)
    _, meta = next(e for e in events if e[0] == "pattern_what_stalled_empty")
    assert meta == {
        "niche_id": 7,
        "reason": "thin_corpus",
        "session_id": "sess-2",
        "turn_index": 0,
    }


def test_resolve_turn_observability_events_skips_what_stalled_when_populated() -> None:
    """Non-empty what_stalled OR missing reason → no event."""
    non_empty = resolve_turn_observability_events(
        fmt="pattern",
        payload={"what_stalled": ["a"], "confidence": {"what_stalled_reason": "x"}},
        classifier_confidence_score=0.9,
        intent_id="trend_spike",
        niche_id=3,
        session_id="s",
        turn_index=0,
    )
    assert not any(a == "pattern_what_stalled_empty" for a, _ in non_empty)

    no_reason = resolve_turn_observability_events(
        fmt="pattern",
        payload={"what_stalled": [], "confidence": {}},
        classifier_confidence_score=0.9,
        intent_id="trend_spike",
        niche_id=3,
        session_id="s",
        turn_index=0,
    )
    assert not any(a == "pattern_what_stalled_empty" for a, _ in no_reason)

    wrong_fmt = resolve_turn_observability_events(
        fmt="ideas",
        payload={"what_stalled": [], "confidence": {"what_stalled_reason": "x"}},
        classifier_confidence_score=0.9,
        intent_id="trend_spike",
        niche_id=3,
        session_id="s",
        turn_index=0,
    )
    assert not any(a == "pattern_what_stalled_empty" for a, _ in wrong_fmt)


def test_log_usage_event_server_inserts_row_via_service_client() -> None:
    """Helper hits usage_events.insert with the expected payload shape."""
    sb = MagicMock()
    log_usage_event_server(
        sb,
        user_id="u-1",
        action="classifier_low_confidence",
        metadata={"intent_id": "trend_spike"},
    )
    sb.table.assert_called_with("usage_events")
    payload = sb.table.return_value.insert.call_args.args[0]
    assert payload == {
        "user_id": "u-1",
        "action": "classifier_low_confidence",
        "metadata": {"intent_id": "trend_spike"},
    }
    sb.table.return_value.insert.return_value.execute.assert_called_once()


def test_log_usage_event_server_swallows_errors() -> None:
    """A logging failure must not raise — fire-and-forget contract."""
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.side_effect = RuntimeError("boom")
    # Should not raise.
    log_usage_event_server(sb, user_id="u-1", action="x", metadata=None)
