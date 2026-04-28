"""Narrative layer tests for Diagnostic reports.

The fallback path is covered exhaustively here because the whole point
of the template is honest diagnosis — fabricating verdicts when we
don't have signal is the regression class we're guarding against.

Gemini-happy and Gemini-exception paths are covered with mocks; the
post-processing path (coercing malformed Gemini output) has dedicated
cases.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from getviews_pipeline.report_diagnostic import DIAGNOSTIC_CATEGORY_NAMES
from getviews_pipeline.report_diagnostic_gemini import (
    DiagnosticNarrativeLLM,
    fill_diagnostic_narrative,
)
from getviews_pipeline.report_types import (
    ConfidenceStrip,
    DiagnosticCategory,
    DiagnosticPayload,
    DiagnosticPrescription,
    SourceRow,
)


def _validate_payload_shape(narrative: dict[str, Any]) -> None:
    """Assemble the minimum payload around the narrative output and
    validate through Pydantic — catches shape drift between the
    narrative module and the payload contract."""
    payload = {
        "confidence": ConfidenceStrip(
            sample_size=0,
            window_days=14,
            niche_scope="Skincare",
            freshness_hours=24,
            intent_confidence="medium",
        ).model_dump(),
        "framing": narrative["framing"],
        "categories": narrative["categories"],
        "prescriptions": narrative["prescriptions"],
        "sources": [
            SourceRow(
                kind="datapoint",
                label="Benchmark",
                count=0,
                sub="Skincare · 14d",
            ).model_dump(),
        ],
        "related_questions": ["q1", "q2", "q3"],
    }
    DiagnosticPayload.model_validate(payload)


# ── Empty / short query → honesty fallback ──────────────────────────────────


@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_empty_query_returns_all_unclear() -> None:
    """The honesty invariant: no query, no verdicts."""
    out = fill_diagnostic_narrative(query="", niche_label="Skincare")
    verdicts = [c["verdict"] for c in out["categories"]]
    assert verdicts == ["unclear"] * 5
    # Must ship a paste-link prescription — DiagnosticPayload requires ≥1.
    assert len(out["prescriptions"]) == 1
    assert "/app/answer" in out["prescriptions"][0]["action"]


@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_short_query_below_threshold_returns_all_unclear() -> None:
    """Query < 20 chars is below the "enough to diagnose" threshold."""
    out = fill_diagnostic_narrative(query="flop", niche_label="Skincare")
    verdicts = [c["verdict"] for c in out["categories"]]
    assert verdicts == ["unclear"] * 5


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_no_gemini_key_returns_fallback_even_with_long_query() -> None:
    out = fill_diagnostic_narrative(
        query="pacing chậm và CTA yếu không ai xem hết video",
        niche_label="Skincare",
    )
    verdicts = [c["verdict"] for c in out["categories"]]
    assert verdicts == ["unclear"] * 5


# ── Fallback shape is always 5 categories in the right order ────────────────


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_categories_match_pinned_order() -> None:
    out = fill_diagnostic_narrative(query="", niche_label="Skincare")
    names = [c["name"] for c in out["categories"]]
    assert names == list(DIAGNOSTIC_CATEGORY_NAMES)


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_framing_mentions_no_link() -> None:
    out = fill_diagnostic_narrative(query="", niche_label="Skincare")
    framing = out["framing"].lower()
    assert "link" in framing or "mô tả" in framing


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_payload_validates_cleanly() -> None:
    out = fill_diagnostic_narrative(query="", niche_label="Skincare")
    _validate_payload_shape(out)


@patch("getviews_pipeline.config.GEMINI_API_KEY", "")
def test_fallback_unclear_categories_have_no_fix_preview() -> None:
    """The invariant is only enforced on probably_fine, but the fallback
    path keeps fix_preview=None for all unclear categories so the UI
    hides the row consistently."""
    out = fill_diagnostic_narrative(query="", niche_label="Skincare")
    for c in out["categories"]:
        assert c["verdict"] == "unclear"
        assert c["fix_preview"] is None


# ── Gemini-happy path (mocked) ──────────────────────────────────────────────


@patch("getviews_pipeline.gemini._generate_content_models")
@patch("getviews_pipeline.gemini._normalize_response")
@patch("getviews_pipeline.gemini._response_text")
@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_gemini_happy_path_threads_query_into_findings(
    mock_response_text: MagicMock,
    mock_normalize: MagicMock,
    mock_gen: MagicMock,
) -> None:
    mock_gen.return_value = MagicMock()
    mock_response_text.return_value = """
{
  "framing": "Chưa có link video — chẩn đoán dựa trên 'pacing chậm' và benchmark Skincare.",
  "categories": [
    {"name": "Hook (0–3s)", "verdict": "likely_issue", "finding": "Bạn nói 'không ai xem hết video' — hook thường là thủ phạm.", "fix_preview": "Rút hook về ≤ 1.2 giây."},
    {"name": "Pacing (3–20s)", "verdict": "likely_issue", "finding": "Bạn mô tả 'pacing chậm' trực tiếp.", "fix_preview": "Cắt scene ≤ 3s + overlay."},
    {"name": "CTA", "verdict": "possible_issue", "finding": "Chưa rõ dạng CTA từ mô tả.", "fix_preview": "Thử CTA dạng câu hỏi."},
    {"name": "Sound", "verdict": "unclear", "finding": "Không có thông tin về audio trong mô tả.", "fix_preview": ""},
    {"name": "Caption & Hashtag", "verdict": "probably_fine", "finding": "Không phải nguyên nhân chính cho retention thấp.", "fix_preview": ""}
  ],
  "prescriptions": [
    {"priority": "P1", "action": "Viết lại hook.", "impact": "Dự báo +12–18% retention 3s.", "effort": "low"},
    {"priority": "P2", "action": "Tăng pacing.", "impact": "Giảm drop-off 8–12%.", "effort": "medium"}
  ]
}
"""
    mock_normalize.side_effect = lambda x: x

    out = fill_diagnostic_narrative(
        query="pacing chậm, không ai xem hết video",
        niche_label="Skincare",
        benchmarks={"avg_retention": 68, "median_tps": 1.4},
    )
    # Framing reflects the Gemini output (query phrase preserved).
    assert "pacing chậm" in out["framing"].lower()
    # 5 categories in the pinned order.
    assert [c["name"] for c in out["categories"]] == list(DIAGNOSTIC_CATEGORY_NAMES)
    # probably_fine category had its fix_preview stripped.
    last = out["categories"][4]
    assert last["verdict"] == "probably_fine"
    assert last["fix_preview"] is None
    # Prescription count = 2 (from Gemini).
    assert len(out["prescriptions"]) == 2
    # Validates end-to-end.
    _validate_payload_shape(out)


@patch("getviews_pipeline.gemini._generate_content_models")
@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_gemini_exception_falls_back_to_unclear(mock_gen: MagicMock) -> None:
    mock_gen.side_effect = RuntimeError("gemini boom")

    out = fill_diagnostic_narrative(
        query="pacing chậm không ai xem hết",
        niche_label="Skincare",
    )
    verdicts = [c["verdict"] for c in out["categories"]]
    assert verdicts == ["unclear"] * 5


@patch("getviews_pipeline.gemini._generate_content_models")
@patch("getviews_pipeline.gemini._normalize_response")
@patch("getviews_pipeline.gemini._response_text")
@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_gemini_schema_mismatch_falls_back_to_unclear(
    mock_response_text: MagicMock,
    mock_normalize: MagicMock,
    mock_gen: MagicMock,
) -> None:
    mock_gen.return_value = MagicMock()
    mock_response_text.return_value = '{"not_the_expected_schema": 42}'
    mock_normalize.side_effect = lambda x: x

    out = fill_diagnostic_narrative(
        query="pacing chậm không ai xem hết",
        niche_label="Skincare",
    )
    # Parsing succeeded but schema had no categories — post-process
    # fills all 5 slots with unclear defaults.
    verdicts = [c["verdict"] for c in out["categories"]]
    assert verdicts == ["unclear"] * 5


# ── Post-processing invariants ─────────────────────────────────────────────


@patch("getviews_pipeline.gemini._generate_content_models")
@patch("getviews_pipeline.gemini._normalize_response")
@patch("getviews_pipeline.gemini._response_text")
@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_probably_fine_with_fix_preview_is_stripped(
    mock_response_text: MagicMock,
    mock_normalize: MagicMock,
    mock_gen: MagicMock,
) -> None:
    """If Gemini returns ``probably_fine`` + a fix_preview, the
    post-processor must drop the fix_preview — otherwise the payload
    would fail the Pydantic invariant."""
    mock_gen.return_value = MagicMock()
    mock_response_text.return_value = """
{
  "framing": "stub",
  "categories": [
    {"name": "Hook (0–3s)", "verdict": "probably_fine", "finding": "ok", "fix_preview": "but do this anyway"},
    {"name": "Pacing (3–20s)", "verdict": "unclear", "finding": "stub", "fix_preview": ""},
    {"name": "CTA", "verdict": "unclear", "finding": "stub", "fix_preview": ""},
    {"name": "Sound", "verdict": "unclear", "finding": "stub", "fix_preview": ""},
    {"name": "Caption & Hashtag", "verdict": "unclear", "finding": "stub", "fix_preview": ""}
  ],
  "prescriptions": [
    {"priority": "P1", "action": "x", "impact": "y", "effort": "low"}
  ]
}
"""
    mock_normalize.side_effect = lambda x: x

    out = fill_diagnostic_narrative(
        query="pacing chậm không ai xem hết",
        niche_label="Skincare",
    )
    first = out["categories"][0]
    assert first["verdict"] == "probably_fine"
    assert first["fix_preview"] is None
    _validate_payload_shape(out)


@patch("getviews_pipeline.gemini._generate_content_models")
@patch("getviews_pipeline.gemini._normalize_response")
@patch("getviews_pipeline.gemini._response_text")
@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_unknown_verdict_coerced_to_unclear(
    mock_response_text: MagicMock,
    mock_normalize: MagicMock,
    mock_gen: MagicMock,
) -> None:
    mock_gen.return_value = MagicMock()
    mock_response_text.return_value = """
{
  "framing": "stub",
  "categories": [
    {"name": "Hook (0–3s)", "verdict": "definitely_broken", "finding": "stub", "fix_preview": ""},
    {"name": "Pacing (3–20s)", "verdict": "unclear", "finding": "stub", "fix_preview": ""},
    {"name": "CTA", "verdict": "unclear", "finding": "stub", "fix_preview": ""},
    {"name": "Sound", "verdict": "unclear", "finding": "stub", "fix_preview": ""},
    {"name": "Caption & Hashtag", "verdict": "unclear", "finding": "stub", "fix_preview": ""}
  ],
  "prescriptions": [
    {"priority": "Px", "action": "x", "impact": "y", "effort": "low"}
  ]
}
"""
    mock_normalize.side_effect = lambda x: x

    out = fill_diagnostic_narrative(
        query="pacing chậm không ai xem hết",
        niche_label="Skincare",
    )
    # Out-of-enum verdict silently coerced to unclear.
    assert out["categories"][0]["verdict"] == "unclear"
    # Out-of-enum priority coerced to P1.
    assert out["prescriptions"][0]["priority"] == "P1"


@patch("getviews_pipeline.gemini._generate_content_models")
@patch("getviews_pipeline.gemini._normalize_response")
@patch("getviews_pipeline.gemini._response_text")
@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_two_different_queries_produce_different_framings(
    mock_response_text: MagicMock,
    mock_normalize: MagicMock,
    mock_gen: MagicMock,
) -> None:
    """The 2026-04-22 "follow-ups don't collide" regression guard."""
    mock_gen.return_value = MagicMock()
    # Different queries → different Gemini outputs. Simulate by keying
    # the canned response on a counter.
    call_count = {"n": 0}

    def response_text(*_args: Any, **_kwargs: Any) -> str:
        call_count["n"] += 1
        framing = "stub framing %d" % call_count["n"]
        return (
            '{"framing": "%s", '
            '"categories": [{"name": "Hook (0\\u20133s)", "verdict": "unclear", "finding": "stub", "fix_preview": ""},'
            '{"name": "Pacing (3\\u201320s)", "verdict": "unclear", "finding": "stub", "fix_preview": ""},'
            '{"name": "CTA", "verdict": "unclear", "finding": "stub", "fix_preview": ""},'
            '{"name": "Sound", "verdict": "unclear", "finding": "stub", "fix_preview": ""},'
            '{"name": "Caption & Hashtag", "verdict": "unclear", "finding": "stub", "fix_preview": ""}],'
            '"prescriptions": [{"priority": "P1", "action": "x", "impact": "y", "effort": "low"}]}'
            % framing
        )

    mock_response_text.side_effect = response_text
    mock_normalize.side_effect = lambda x: x

    a = fill_diagnostic_narrative(
        query="pacing chậm không ai xem hết video",
        niche_label="Skincare",
    )
    b = fill_diagnostic_narrative(
        query="CTA không rõ và hook quá dài 2 giây",
        niche_label="Skincare",
    )
    assert a["framing"] != b["framing"]


# ── Schema defaults ────────────────────────────────────────────────────────


def test_llm_schema_tolerates_missing_optional_keys() -> None:
    # Gemini occasionally drops optional fields — parser must not reject.
    m = DiagnosticNarrativeLLM.model_validate({"framing": "only framing"})
    assert m.categories == []
    assert m.prescriptions == []
