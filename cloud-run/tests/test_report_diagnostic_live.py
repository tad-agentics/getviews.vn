"""Live-builder orchestration tests for ``build_diagnostic_report``.

Covers the three branches that matter for the "honest diagnosis"
contract:

1. Service client unavailable → fallback to 5-unclear + paste-link.
2. Benchmark fetch partially fails → continues (benchmarks optional).
3. Substantial query + benchmarks → full Gemini path (mocked).
4. Two different queries → different framings (follow-ups don't collide).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from getviews_pipeline.report_diagnostic import (
    DIAGNOSTIC_CATEGORY_NAMES,
    build_diagnostic_report,
)
from getviews_pipeline.report_types import DiagnosticPayload


def _mock_sb_with_benchmarks(
    execution_tip: str | None = None,
) -> MagicMock:
    sb = MagicMock()

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "niche_taxonomy":
            m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(  # noqa: E501
                data={"name_vn": "Skincare", "name_en": "Skincare"},
            )
        elif name == "niche_intelligence":
            m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(  # noqa: E501
                data={
                    "avg_retention": 68,
                    "median_tps": 1.4,
                    "top_sound": "skincare_trending_1",
                    "common_cta_types": "follow|save",
                },
            )
        elif name == "niche_insights":
            # Wave 3 — _fetch_niche_execution_tip lookup. Return the
            # parametrized tip (or no rows when None).
            data = (
                [{"execution_tip": execution_tip}] if execution_tip else []
            )
            m.select.return_value.eq.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(  # noqa: E501
                data=data,
            )
        else:
            raise AssertionError(f"unexpected table {name!r}")
        return m

    sb.table.side_effect = table
    return sb


def _mock_sb_no_intelligence() -> MagicMock:
    """Niche row exists but niche_intelligence row is absent — builder
    must still succeed with empty benchmarks."""
    sb = MagicMock()

    def table(name: str) -> MagicMock:
        m = MagicMock()
        if name == "niche_taxonomy":
            m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(  # noqa: E501
                data={"name_vn": "Skincare", "name_en": "Skincare"},
            )
        elif name == "niche_intelligence":
            # Simulate a fetch exception.
            chain = m.select.return_value.eq.return_value.maybe_single.return_value
            chain.execute.side_effect = RuntimeError("no intelligence row")
        elif name == "niche_insights":
            # No tip for this niche — execution_tip surface stays null.
            m.select.return_value.eq.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(  # noqa: E501
                data=[],
            )
        else:
            raise AssertionError(f"unexpected table {name!r}")
        return m

    sb.table.side_effect = table
    return sb


# ── Service client failures ────────────────────────────────────────────────


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_service_client_unavailable_falls_back_to_unclear(
    mock_get_svc: MagicMock,
) -> None:
    mock_get_svc.side_effect = RuntimeError("no SUPABASE_URL")

    r = build_diagnostic_report(
        niche_id=2, query="pacing chậm không ai xem hết video", window_days=14,
    )
    DiagnosticPayload.model_validate(r)
    # Fallback path: 5 unclear categories + 1 paste-link prescription.
    verdicts = [c["verdict"] for c in r["categories"]]
    assert verdicts == ["unclear"] * 5
    assert len(r["prescriptions"]) == 1
    assert "/app/answer" in r["prescriptions"][0]["action"]


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_niche_intelligence_missing_continues_with_empty_benchmarks(
    mock_get_svc: MagicMock,
) -> None:
    """niche_intelligence is optional enrichment — its absence must not
    block the diagnostic. Without a Gemini key the narrative layer
    falls back to unclear, but the payload still validates."""
    mock_get_svc.return_value = _mock_sb_no_intelligence()

    r = build_diagnostic_report(
        niche_id=2, query="pacing chậm không ai xem hết video", window_days=14,
    )
    DiagnosticPayload.model_validate(r)
    # Niche label was picked up from niche_taxonomy.
    assert r["confidence"]["niche_scope"] == "Skincare"


# ── Gemini happy path via the public builder ──────────────────────────────


@patch("getviews_pipeline.gemini._generate_content_models")
@patch("getviews_pipeline.gemini._normalize_response")
@patch("getviews_pipeline.gemini._response_text")
@patch("getviews_pipeline.supabase_client.get_service_client")
@patch("getviews_pipeline.config.GEMINI_API_KEY", "fake-key")
def test_live_path_produces_query_aware_framing(
    mock_get_svc: MagicMock,
    mock_response_text: MagicMock,
    mock_normalize: MagicMock,
    mock_gen: MagicMock,
) -> None:
    mock_get_svc.return_value = _mock_sb_with_benchmarks()
    mock_gen.return_value = MagicMock()
    mock_response_text.return_value = """
{
  "framing": "Chưa có link video — chẩn đoán dựa trên 'pacing chậm' và benchmark Skincare.",
  "categories": [
    {"name": "Hook (0–3s)", "verdict": "likely_issue", "finding": "bạn nói 'không ai xem hết' — hook yếu.", "fix_preview": "Rút hook 1.2s."},
    {"name": "Pacing (3–20s)", "verdict": "likely_issue", "finding": "mô tả 'pacing chậm' trực tiếp.", "fix_preview": "Cắt ≤3s."},
    {"name": "CTA", "verdict": "unclear", "finding": "không rõ CTA", "fix_preview": ""},
    {"name": "Sound", "verdict": "unclear", "finding": "không rõ audio", "fix_preview": ""},
    {"name": "Caption & Hashtag", "verdict": "unclear", "finding": "không rõ caption", "fix_preview": ""}
  ],
  "prescriptions": [
    {"priority": "P1", "action": "Viết lại hook.", "impact": "+12-18% retention.", "effort": "low"},
    {"priority": "P2", "action": "Tăng pacing.", "impact": "-8% drop-off.", "effort": "medium"}
  ]
}
"""
    mock_normalize.side_effect = lambda x: x

    r = build_diagnostic_report(
        niche_id=2,
        query="pacing chậm không ai xem hết video",
        window_days=14,
    )
    DiagnosticPayload.model_validate(r)

    # Categories in pinned order.
    assert [c["name"] for c in r["categories"]] == list(DIAGNOSTIC_CATEGORY_NAMES)
    # First two categories picked up the query signal.
    assert r["categories"][0]["verdict"] == "likely_issue"
    assert r["categories"][1]["verdict"] == "likely_issue"
    # Two Gemini-generated prescriptions (not the fallback single one).
    assert len(r["prescriptions"]) == 2
    # Niche label + sub from niche_taxonomy.
    assert r["confidence"]["niche_scope"] == "Skincare"


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_two_queries_produce_different_framings(mock_get_svc: MagicMock) -> None:
    """Even on the fallback path, two different queries must produce
    distinguishable output somewhere in the payload (findings quote the
    query back). Without a Gemini key, verdicts are all unclear — but
    the ``finding`` strings still embed a query excerpt so follow-ups
    don't collide."""
    mock_get_svc.return_value = _mock_sb_with_benchmarks()

    a = build_diagnostic_report(
        niche_id=2,
        query="pacing chậm, không ai xem hết video tuần trước",
        window_days=14,
    )
    b = build_diagnostic_report(
        niche_id=2,
        query="CTA không rõ và hook quá dài 2 giây đầu",
        window_days=14,
    )
    DiagnosticPayload.model_validate(a)
    DiagnosticPayload.model_validate(b)

    # findings differ because the query excerpt is quoted back.
    a_findings = [c["finding"] for c in a["categories"]]
    b_findings = [c["finding"] for c in b["categories"]]
    assert a_findings != b_findings


# ── Related questions threading ─────────────────────────────────────────────


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_related_questions_embed_query_excerpt(mock_get_svc: MagicMock) -> None:
    mock_get_svc.return_value = _mock_sb_with_benchmarks()
    r = build_diagnostic_report(
        niche_id=2,
        query="pacing chậm và hook dài không ai xem hết",
        window_days=14,
    )
    DiagnosticPayload.model_validate(r)
    assert len(r["related_questions"]) == 3
    # First related question reflects the specific query.
    assert "pacing" in r["related_questions"][0].lower() or "link" in r["related_questions"][0].lower()


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_confidence_is_capped_below_high(mock_get_svc: MagicMock) -> None:
    """No video = no high confidence, ever. The PRD invariant."""
    mock_get_svc.return_value = _mock_sb_with_benchmarks()
    r = build_diagnostic_report(
        niche_id=2,
        query="pacing chậm và không ai xem hết video",
        window_days=14,
    )
    assert r["confidence"]["intent_confidence"] in ("medium", "low")


# ── Wave 3 — niche_execution_tip surface ───────────────────────────────────


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_niche_execution_tip_is_surfaced_when_available(
    mock_get_svc: MagicMock,
) -> None:
    tip = "Dùng hook câu hỏi 1.2s + product shot ngay sau để bắt trend."
    mock_get_svc.return_value = _mock_sb_with_benchmarks(execution_tip=tip)
    r = build_diagnostic_report(
        niche_id=2, query="pacing chậm không ai xem hết video", window_days=14,
    )
    DiagnosticPayload.model_validate(r)
    assert r["niche_execution_tip"] == tip


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_niche_execution_tip_is_null_when_row_absent(
    mock_get_svc: MagicMock,
) -> None:
    mock_get_svc.return_value = _mock_sb_with_benchmarks(execution_tip=None)
    r = build_diagnostic_report(
        niche_id=2, query="pacing chậm", window_days=14,
    )
    DiagnosticPayload.model_validate(r)
    assert r["niche_execution_tip"] is None


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_niche_execution_tip_truncated_when_too_long(
    mock_get_svc: MagicMock,
) -> None:
    """DiagnosticPayload caps the field at 240 chars; _fetch helper
    pre-trims so a verbose Layer 0 tip never blocks validation."""
    long_tip = "A" * 400
    mock_get_svc.return_value = _mock_sb_with_benchmarks(execution_tip=long_tip)
    r = build_diagnostic_report(
        niche_id=2, query="pacing chậm", window_days=14,
    )
    DiagnosticPayload.model_validate(r)
    assert r["niche_execution_tip"] is not None
    assert len(r["niche_execution_tip"]) <= 240
    # Ellipsis applied on truncation.
    assert r["niche_execution_tip"].endswith("…")


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_niche_execution_tip_null_on_fallback_path(
    mock_get_svc: MagicMock,
) -> None:
    """When the service client itself is unavailable we never hit the
    tip table — ``niche_execution_tip`` must be explicitly null, not
    missing."""
    mock_get_svc.side_effect = RuntimeError("no SUPABASE_URL")
    r = build_diagnostic_report(
        niche_id=2, query="pacing chậm", window_days=14,
    )
    DiagnosticPayload.model_validate(r)
    assert r["niche_execution_tip"] is None


@patch("getviews_pipeline.supabase_client.get_service_client")
def test_niche_execution_tip_empty_string_coerced_to_null(
    mock_get_svc: MagicMock,
) -> None:
    """Layer 0 rows may carry an empty-string execution_tip; the helper
    must normalize that to None so the FE doesn't render an empty
    callout."""
    mock_get_svc.return_value = _mock_sb_with_benchmarks(execution_tip="   ")
    r = build_diagnostic_report(
        niche_id=2, query="pacing chậm", window_days=14,
    )
    DiagnosticPayload.model_validate(r)
    assert r["niche_execution_tip"] is None
