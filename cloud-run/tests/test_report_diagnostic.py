"""Diagnostic template — schema + fixture invariants (commit 4a).

Part of the templates-audit implementation series (2026-04-22). This
file covers the pure Pydantic contract + fixture shape. The live
pipeline tests (Gemini narrative, query threading, thin-corpus
fallback) land in commit 4c.
"""

from __future__ import annotations

import pytest

from getviews_pipeline.report_diagnostic import (
    ANSWER_FIXTURE_DIAGNOSTIC,
    DIAGNOSTIC_CATEGORY_NAMES,
    build_diagnostic_report,
    build_fixture_diagnostic_report,
)
from getviews_pipeline.report_types import (
    ConfidenceStrip,
    DiagnosticCategory,
    DiagnosticPayload,
    DiagnosticPrescription,
    ReportV1,
    SourceRow,
)


# ── Fixture validates cleanly ───────────────────────────────────────────────


def test_fixture_validates_against_payload() -> None:
    p = DiagnosticPayload.model_validate(build_fixture_diagnostic_report())
    assert len(p.categories) == 5
    assert len(p.prescriptions) == 3


def test_envelope_accepts_diagnostic_kind() -> None:
    env = ReportV1.model_validate(ANSWER_FIXTURE_DIAGNOSTIC)
    assert env.kind == "diagnostic"


def test_fixture_has_exactly_the_five_category_names() -> None:
    p = DiagnosticPayload.model_validate(build_fixture_diagnostic_report())
    names = [c.name for c in p.categories]
    assert names == list(DIAGNOSTIC_CATEGORY_NAMES)


def test_fixture_exercises_all_four_verdict_types() -> None:
    p = DiagnosticPayload.model_validate(build_fixture_diagnostic_report())
    seen = {c.verdict for c in p.categories}
    # Fixture should include at least 3 distinct verdicts so the
    # frontend storybook can render every badge variant against one
    # payload. (4th variant covered by dedicated test below.)
    assert "likely_issue" in seen
    assert "unclear" in seen
    assert "probably_fine" in seen


def test_fixture_framing_acknowledges_no_url() -> None:
    """Copy invariant from the PRD: the framing sentence must be explicit
    about the URL-less constraint so users aren't surprised by the
    verdict-based output."""
    p = DiagnosticPayload.model_validate(build_fixture_diagnostic_report())
    assert "link video" in p.framing.lower() or "mô tả" in p.framing.lower()


def test_fixture_confidence_never_exceeds_medium() -> None:
    """PRD rule: no video + no verified benchmarks means we cap at medium.
    Shipping 'high' confidence here would be dishonest."""
    p = DiagnosticPayload.model_validate(build_fixture_diagnostic_report())
    assert p.confidence.intent_confidence in ("medium", "low")


def test_fixture_paste_link_cta_points_to_video_screen() -> None:
    p = DiagnosticPayload.model_validate(build_fixture_diagnostic_report())
    assert p.paste_link_cta["route"] == "/app/video"
    assert "link" in p.paste_link_cta["title"].lower()


def test_fixture_related_questions_non_empty() -> None:
    r = build_fixture_diagnostic_report()
    assert len(r["related_questions"]) >= 3


# ── Invariant: probably_fine must not carry a fix_preview ───────────────────


def _make_payload(categories: list[DiagnosticCategory]) -> dict:
    return {
        "confidence": ConfidenceStrip(
            sample_size=100,
            window_days=14,
            niche_scope="Skincare",
            freshness_hours=6,
            intent_confidence="medium",
        ).model_dump(),
        "framing": "stub framing",
        "categories": [c.model_dump() for c in categories],
        "prescriptions": [
            DiagnosticPrescription(
                priority="P1",
                action="stub action",
                impact="stub impact",
                effort="low",
            ).model_dump(),
        ],
        "sources": [
            SourceRow(
                kind="datapoint",
                label="Benchmark",
                count=100,
                sub="Skincare · 14d",
            ).model_dump(),
        ],
        "related_questions": ["q1", "q2", "q3"],
    }


def _five_categories_with_override(
    idx: int, override: DiagnosticCategory,
) -> list[DiagnosticCategory]:
    base = [
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[i],
            verdict="unclear",
            finding="stub finding",
        )
        for i in range(5)
    ]
    base[idx] = override
    return base


def test_probably_fine_category_may_omit_fix_preview() -> None:
    cats = _five_categories_with_override(
        0,
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[0],
            verdict="probably_fine",
            finding="looks fine",
            fix_preview=None,
        ),
    )
    DiagnosticPayload.model_validate(_make_payload(cats))


def test_probably_fine_category_with_fix_preview_is_rejected() -> None:
    """Invariant: a category marked ``probably_fine`` must not carry
    ``fix_preview``. Otherwise the UI would surface a fix we don't
    actually think is needed."""
    cats = _five_categories_with_override(
        0,
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[0],
            verdict="probably_fine",
            finding="looks fine",
            fix_preview="You should still change the hook",
        ),
    )
    with pytest.raises(ValueError, match="diagnostic invariant"):
        DiagnosticPayload.model_validate(_make_payload(cats))


def test_other_verdicts_may_carry_fix_preview() -> None:
    for verdict in ("likely_issue", "possible_issue", "unclear"):
        cats = _five_categories_with_override(
            0,
            DiagnosticCategory(
                name=DIAGNOSTIC_CATEGORY_NAMES[0],
                verdict=verdict,  # type: ignore[arg-type]
                finding="something to fix",
                fix_preview="concrete tactic",
            ),
        )
        DiagnosticPayload.model_validate(_make_payload(cats))


# ── Cardinality invariants ──────────────────────────────────────────────────


def test_fewer_than_5_categories_rejected() -> None:
    cats = [
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[i],
            verdict="unclear",
            finding="stub",
        )
        for i in range(4)
    ]
    with pytest.raises(Exception):
        DiagnosticPayload.model_validate(_make_payload(cats))


def test_more_than_5_categories_rejected() -> None:
    cats = [
        DiagnosticCategory(
            name=f"Category {i}",
            verdict="unclear",
            finding="stub",
        )
        for i in range(6)
    ]
    with pytest.raises(Exception):
        DiagnosticPayload.model_validate(_make_payload(cats))


def test_empty_prescriptions_rejected() -> None:
    """``min_length=1`` on prescriptions — even in the all-unclear case
    we ship at least the "paste the link" recommendation."""
    cats = [
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[i],
            verdict="unclear",
            finding="stub",
        )
        for i in range(5)
    ]
    payload = _make_payload(cats)
    payload["prescriptions"] = []
    with pytest.raises(Exception):
        DiagnosticPayload.model_validate(payload)


def test_more_than_3_prescriptions_rejected() -> None:
    cats = [
        DiagnosticCategory(
            name=DIAGNOSTIC_CATEGORY_NAMES[i],
            verdict="unclear",
            finding="stub",
        )
        for i in range(5)
    ]
    payload = _make_payload(cats)
    payload["prescriptions"] = [
        {
            "priority": "P1",
            "action": f"stub {i}",
            "impact": "stub impact",
            "effort": "low",
        }
        for i in range(4)
    ]
    with pytest.raises(Exception):
        DiagnosticPayload.model_validate(payload)


# ── Live builder stub ──────────────────────────────────────────────────────


def test_live_builder_stub_returns_validated_payload() -> None:
    """Commit 4b can import + call this helper; 4c replaces the body."""
    r = build_diagnostic_report(niche_id=2, query="stub", window_days=14)
    DiagnosticPayload.model_validate(r)
