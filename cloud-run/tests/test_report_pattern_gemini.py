"""D.2.5.b — pydantic response_format binding for fill_pattern_narrative."""

from __future__ import annotations

import json
from typing import Any

import pytest

from getviews_pipeline.report_pattern_gemini import (
    PatternNarrativeLLM,
    _fallback_narrative,
    fill_pattern_narrative,
)


def test_pattern_narrative_llm_schema_has_required_keys() -> None:
    """Response schema must still document all four keys for Gemini prompt-shaping."""
    schema = PatternNarrativeLLM.model_json_schema()
    assert set(schema["properties"].keys()) == {
        "thesis",
        "hook_insights",
        "stalled_insights",
        "related_questions",
    }


def _fake_resp(payload: dict[str, Any]) -> Any:
    class _R:
        text = json.dumps(payload, ensure_ascii=False)

    return _R()


def test_pattern_narrative_happy_path_uses_pydantic_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid JSON → model_validate_json succeeds → per-field truncation/padding runs."""
    monkeypatch.setattr("getviews_pipeline.config.GEMINI_API_KEY", "fake-key", raising=False)

    payload = {
        "thesis": "Trong ngách Tech, BOLD CENTER hook đang dẫn retention ổn định so với baseline.",
        "hook_insights": [
            "BOLD CENTER mở với số liệu thu hút người đang scroll nhanh.",
            "QUESTION XL giữ comment tốt hơn trung vị ngách.",
        ],
        "stalled_insights": ["LABEL overlay đang tụt retention — cân nhắc giảm tần suất."],
        "related_questions": [
            "Hook nào đang giảm tốc?",
            "Format nào oversaturated?",
            "Test hook mới hay tối ưu hook cũ?",
            "Niche con nào breakout?",
        ],
    }
    monkeypatch.setattr(
        "getviews_pipeline.gemini._generate_content_models",
        lambda *a, **k: _fake_resp(payload),
    )
    monkeypatch.setattr(
        "getviews_pipeline.gemini._response_text",
        lambda resp: resp.text,
    )

    out = fill_pattern_narrative(
        query="pattern tech",
        niche_label="Tech",
        top_hook_labels=["BOLD CENTER", "QUESTION XL"],
        stalled_hook_labels=["LABEL"],
    )

    assert out["thesis"].startswith("Trong ngách Tech")
    assert len(out["hook_insights"]) == 2
    assert len(out["stalled_insights"]) == 1
    assert len(out["related_questions"]) == 4
    assert out["related_questions"][0] == "Hook nào đang giảm tốc?"


def test_pattern_narrative_invalid_json_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed JSON → ValidationError caught → deterministic fallback."""
    monkeypatch.setattr("getviews_pipeline.config.GEMINI_API_KEY", "fake-key", raising=False)

    class _RawResp:
        text = "not-json-garbage {"

    monkeypatch.setattr(
        "getviews_pipeline.report_pattern_gemini._generate_content_models",
        lambda *a, **k: _RawResp(),
        raising=False,
    )
    monkeypatch.setattr(
        "getviews_pipeline.report_pattern_gemini._response_text",
        lambda resp: resp.text,
        raising=False,
    )

    out = fill_pattern_narrative(
        query="pattern",
        niche_label="Tech",
        top_hook_labels=["BOLD CENTER"],
        stalled_hook_labels=[],
    )
    # Fallback thesis mentions the niche label, confirming we routed to
    # `_fallback_narrative` rather than returning the garbage.
    assert "Tech" in out["thesis"]
    assert len(out["hook_insights"]) == 1
    assert out["related_questions"] and len(out["related_questions"]) == 4


def test_pattern_narrative_schema_drift_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid JSON but wrong types (e.g. thesis is int) → ValidationError → fallback."""
    monkeypatch.setattr("getviews_pipeline.config.GEMINI_API_KEY", "fake-key", raising=False)

    drifted = _fake_resp(
        {"thesis": 42, "hook_insights": "not-a-list", "stalled_insights": [], "related_questions": []}
    )
    monkeypatch.setattr(
        "getviews_pipeline.report_pattern_gemini._generate_content_models",
        lambda *a, **k: drifted,
        raising=False,
    )
    monkeypatch.setattr(
        "getviews_pipeline.report_pattern_gemini._response_text",
        lambda resp: resp.text,
        raising=False,
    )

    out = fill_pattern_narrative(
        query="pattern",
        niche_label="Tech",
        top_hook_labels=["A"],
        stalled_hook_labels=[],
    )
    # Same shape as a pure fallback.
    direct = _fallback_narrative("pattern", "Tech", ["A"], [])
    assert out["thesis"] == direct["thesis"]


def test_pattern_narrative_no_api_key_falls_back_without_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No GEMINI_API_KEY → deterministic path, no Gemini call."""
    monkeypatch.setattr("getviews_pipeline.config.GEMINI_API_KEY", "", raising=False)

    calls: list[int] = []

    def fake_generate(*_a: object, **_k: object) -> Any:  # pragma: no cover — must not run
        calls.append(1)
        raise AssertionError("must not call gemini without API key")

    monkeypatch.setattr(
        "getviews_pipeline.report_pattern_gemini._generate_content_models",
        fake_generate,
        raising=False,
    )

    out = fill_pattern_narrative(
        query="pattern",
        niche_label="Lifestyle",
        top_hook_labels=["X", "Y"],
        stalled_hook_labels=["Z"],
    )
    assert not calls
    assert "Lifestyle" in out["thesis"]
