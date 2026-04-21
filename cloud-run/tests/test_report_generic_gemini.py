"""D.2.5.a — budget-guard contract for fill_generic_narrative."""

from __future__ import annotations

import logging

import pytest

from getviews_pipeline import config as gv_config
from getviews_pipeline.ensemble import (
    consume_classifier_gemini_budget_or_raise,
    reset_classifier_gemini_budget_for_tests,
)
from getviews_pipeline.report_generic_gemini import fill_generic_narrative


def test_generic_narrative_falls_back_to_empty_when_budget_exceeded(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the classifier daily budget is already exhausted,
    fill_generic_narrative must skip the Gemini call + log [generic-budget]
    + return an empty list so the caller renders deterministic copy."""
    # Budget = 1; pre-consume once so the next call trips the raise.
    monkeypatch.setattr(gv_config, "CLASSIFIER_GEMINI_DAILY_MAX", 1)
    reset_classifier_gemini_budget_for_tests()
    consume_classifier_gemini_budget_or_raise()

    called: list[int] = []

    def fake_text_only(*_args: object, **_kwargs: object) -> str:  # pragma: no cover — must not run
        called.append(1)
        return '{"paragraphs": ["should not ship"]}'

    # Patch the resolution point used inside fill_generic_narrative.
    monkeypatch.setattr("getviews_pipeline.gemini.gemini_text_only", fake_text_only, raising=False)

    with caplog.at_level(logging.WARNING, logger="getviews_pipeline.report_generic_gemini"):
        out = fill_generic_narrative(
            query="câu hỏi ngoài taxonomy",
            niche_label=None,
            sample_n=12,
            window_days=30,
        )

    assert out == []
    assert not called, "gemini_text_only must not be invoked when budget is exhausted"
    assert any(
        "[generic-budget]" in rec.message and "deterministic fallback" in rec.message
        for rec in caplog.records
    )


def test_generic_narrative_consumes_budget_and_calls_gemini_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Budget non-zero → Gemini call runs + budget counter decrements by one."""
    monkeypatch.setattr(gv_config, "CLASSIFIER_GEMINI_DAILY_MAX", 2)
    reset_classifier_gemini_budget_for_tests()

    def fake_text_only(**_kwargs: object) -> str:
        return '{"paragraphs": ["đoạn hedged 1", "đoạn hedged 2"]}'

    monkeypatch.setattr("getviews_pipeline.gemini.gemini_text_only", fake_text_only, raising=False)

    out = fill_generic_narrative(
        query="test",
        niche_label="Tech",
        sample_n=30,
        window_days=30,
    )
    assert out == ["đoạn hedged 1", "đoạn hedged 2"]

    # Subsequent call should still have budget (1/2 consumed).
    out2 = fill_generic_narrative(
        query="test-2",
        niche_label="Tech",
        sample_n=30,
        window_days=30,
    )
    assert out2 == ["đoạn hedged 1", "đoạn hedged 2"]

    # Third call exhausts the budget → empty list, no crash.
    out3 = fill_generic_narrative(
        query="test-3",
        niche_label="Tech",
        sample_n=30,
        window_days=30,
    )
    assert out3 == []
