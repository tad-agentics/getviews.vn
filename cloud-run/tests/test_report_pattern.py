"""WhatStalled acceptance — empty list requires what_stalled_reason (Phase C.2)."""

from __future__ import annotations

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
