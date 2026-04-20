"""WhatStalled acceptance — empty list requires what_stalled_reason (Phase C.2)."""

from __future__ import annotations

import copy

import pytest

from getviews_pipeline.report_pattern import build_fixture_pattern_report
from getviews_pipeline.report_types import PatternPayload, validate_and_store_report


def test_fixture_what_stalled_invariant() -> None:
    inner = build_fixture_pattern_report()
    p = PatternPayload.model_validate(inner)
    assert p.what_stalled == []
    assert p.confidence.what_stalled_reason is not None


def test_validate_and_store_pattern_envelope() -> None:
    inner = build_fixture_pattern_report()
    env = validate_and_store_report("pattern", inner)
    assert env["kind"] == "pattern"
    assert "report" in env


def test_empty_stalled_without_reason_raises() -> None:
    """Regression — §C.2 invariant must reject empty list + null reason."""
    inner = copy.deepcopy(build_fixture_pattern_report())
    inner["confidence"]["what_stalled_reason"] = None
    assert inner["what_stalled"] == []
    with pytest.raises(ValueError, match="what_stalled invariant violated"):
        PatternPayload.model_validate(inner)


def test_what_stalled_cap_at_three() -> None:
    """Regression — §C.2 invariant caps what_stalled at 3 entries."""
    inner = copy.deepcopy(build_fixture_pattern_report())
    # Synthesise 4 stalled findings by duplicating the first finding shape.
    if not inner["findings"]:
        pytest.skip("fixture has no findings to clone")
    base = inner["findings"][0]
    inner["what_stalled"] = [base] * 4
    with pytest.raises(ValueError, match="at most 3 entries"):
        PatternPayload.model_validate(inner)


def test_validate_and_store_rejects_invariant_violation() -> None:
    """Envelope validator must propagate the invariant error, not swallow it."""
    inner = copy.deepcopy(build_fixture_pattern_report())
    inner["confidence"]["what_stalled_reason"] = None
    with pytest.raises(ValueError, match="what_stalled invariant violated"):
        validate_and_store_report("pattern", inner)
