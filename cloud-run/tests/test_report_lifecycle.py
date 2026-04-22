"""Lifecycle template — schema + fixture invariants.

Part of the templates-audit implementation series (2026-04-22). This
test suite covers the pure contract: Pydantic schema, the invariant
that refresh_moves only appear when at least one cell is weak, and the
three fixture variants validate cleanly.

Live-pipeline tests (Gemini narrative, thin-corpus gate on real niches,
mode dispatch from intent_type) land with the builder commits.
"""

from __future__ import annotations

import pytest

from getviews_pipeline.report_lifecycle import (
    ANSWER_FIXTURE_LIFECYCLE_FORMAT,
    ANSWER_FIXTURE_LIFECYCLE_HOOK_FATIGUE,
    ANSWER_FIXTURE_LIFECYCLE_SUBNICHE,
    build_fixture_lifecycle_report,
    build_lifecycle_report,
)
from getviews_pipeline.report_types import (
    ConfidenceStrip,
    LifecycleCell,
    LifecyclePayload,
    RefreshMove,
    ReportV1,
    SourceRow,
)


# ── Fixtures validate in all three modes ────────────────────────────────────


@pytest.mark.parametrize("mode", ["format", "hook_fatigue", "subniche"])
def test_fixture_validates_for_mode(mode: str) -> None:
    payload = build_fixture_lifecycle_report(mode)  # type: ignore[arg-type]
    p = LifecyclePayload.model_validate(payload)
    assert p.mode == mode
    assert len(p.cells) >= 1


def test_envelope_accepts_lifecycle_kind() -> None:
    env = ReportV1.model_validate(ANSWER_FIXTURE_LIFECYCLE_FORMAT)
    assert env.kind == "lifecycle"


def test_fixture_format_has_expected_four_cells() -> None:
    p = LifecyclePayload.model_validate(build_fixture_lifecycle_report("format"))
    assert len(p.cells) == 4
    assert {c.stage for c in p.cells} == {"rising", "peak", "plateau", "declining"}


def test_fixture_hook_fatigue_highlights_decline() -> None:
    p = LifecyclePayload.model_validate(build_fixture_lifecycle_report("hook_fatigue"))
    # First cell is the fatigued hook (declining).
    assert p.cells[0].stage == "declining"
    # Subject line must reference the specific fatigue number.
    assert "18%" in p.subject_line


def test_fixture_subniche_uses_instance_counts() -> None:
    p = LifecyclePayload.model_validate(build_fixture_lifecycle_report("subniche"))
    assert len(p.cells) == 6
    # Subniche mode always carries instance_count; retention_pct is None.
    for c in p.cells:
        assert c.instance_count is not None
        assert c.retention_pct is None


def test_every_fixture_has_non_empty_related_questions() -> None:
    for mode in ("format", "hook_fatigue", "subniche"):
        r = build_fixture_lifecycle_report(mode)  # type: ignore[arg-type]
        assert len(r["related_questions"]) >= 3


def test_subject_line_length_capped() -> None:
    for mode in ("format", "hook_fatigue", "subniche"):
        r = build_fixture_lifecycle_report(mode)  # type: ignore[arg-type]
        assert 0 < len(r["subject_line"]) <= 240


# ── refresh_moves invariant ─────────────────────────────────────────────────


def _make_payload(
    *,
    cells: list[LifecycleCell],
    refresh_moves: list[RefreshMove],
) -> dict:
    return {
        "confidence": ConfidenceStrip(
            sample_size=100,
            window_days=30,
            niche_scope="Skincare",
            freshness_hours=1,
            intent_confidence="high",
        ).model_dump(),
        "mode": "format",
        "subject_line": "stub",
        "cells": [c.model_dump() for c in cells],
        "refresh_moves": [m.model_dump() for m in refresh_moves],
        "actions": [],
        "sources": [SourceRow(kind="video", label="Corpus", count=100, sub="Skincare").model_dump()],
        "related_questions": ["q1", "q2", "q3"],
    }


def _cell(stage: str, name: str = "Cell") -> LifecycleCell:
    return LifecycleCell(
        name=name,
        stage=stage,  # type: ignore[arg-type]
        reach_delta_pct=0.0,
        health_score=50,
        insight="stub insight",
    )


def _move() -> RefreshMove:
    return RefreshMove(title="stub move", detail="detail", effort="low")


def test_refresh_moves_allowed_when_cell_declining() -> None:
    payload = _make_payload(
        cells=[_cell("rising"), _cell("declining")],
        refresh_moves=[_move()],
    )
    p = LifecyclePayload.model_validate(payload)
    assert len(p.refresh_moves) == 1


def test_refresh_moves_allowed_when_cell_plateau() -> None:
    payload = _make_payload(
        cells=[_cell("peak"), _cell("plateau")],
        refresh_moves=[_move()],
    )
    p = LifecyclePayload.model_validate(payload)
    assert len(p.refresh_moves) == 1


def test_refresh_moves_rejected_when_all_cells_healthy() -> None:
    """BUG-free guard: rising/peak-only reports must not ship refresh
    prescriptions. Emitting them anyway would be unsolicited advice."""
    payload = _make_payload(
        cells=[_cell("rising"), _cell("peak")],
        refresh_moves=[_move()],
    )
    with pytest.raises(ValueError, match="lifecycle invariant"):
        LifecyclePayload.model_validate(payload)


def test_refresh_moves_empty_always_accepted() -> None:
    # Healthy-only + empty refresh_moves → fine.
    payload = _make_payload(
        cells=[_cell("rising"), _cell("peak")],
        refresh_moves=[],
    )
    p = LifecyclePayload.model_validate(payload)
    assert p.refresh_moves == []


# ── Live builder stub (commit 3c replaces the body) ─────────────────────────


@pytest.mark.parametrize("mode", ["format", "hook_fatigue", "subniche"])
def test_live_builder_returns_valid_payload_stub(mode: str) -> None:
    """The stub returns the fixture so commits 3b (dispatcher wiring)
    can import + call the helper today. Commit 3c replaces the body
    with the real pipeline."""
    r = build_lifecycle_report(niche_id=2, query="stub", mode=mode)  # type: ignore[arg-type]
    p = LifecyclePayload.model_validate(r)
    assert p.mode == mode
