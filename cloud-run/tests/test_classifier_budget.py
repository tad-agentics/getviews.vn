"""Phase C.0.1 — CLASSIFIER_GEMINI_DAILY_MAX guard for classify_intent_gemini."""

from __future__ import annotations

from typing import Any

import pytest

from getviews_pipeline import config as gv_config
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
