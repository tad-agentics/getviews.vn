"""build_diagnosis_posting_context_text — video diagnosis prompt block."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from getviews_pipeline.report_timing_compute import (
    build_diagnosis_posting_context_text,
    compute_diagnosis_posting_bundle,
)


def test_diagnosis_posting_context_zero_niche() -> None:
    assert build_diagnosis_posting_context_text(object(), 0) == ""


def test_diagnosis_posting_bundle_mock_sb_empty() -> None:
    class _Sb:
        pass

    text, ui = compute_diagnosis_posting_bundle(_Sb(), 1)
    assert text == ""
    assert ui is None


def test_compute_diagnosis_posting_bundle_returns_payload_when_corpus_25(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = datetime(2026, 4, 18, 12, 0, tzinfo=UTC)
    rows = [
        {"video_id": f"v{i}", "views": 15000, "posted_at": base.isoformat()} for i in range(25)
    ]

    def fake_load(_sb: object, _niche_id: int, _window_days: int):
        return {"niche_label": "Skincare", "corpus": rows}

    monkeypatch.setattr(
        "getviews_pipeline.report_timing_compute.load_timing_inputs",
        fake_load,
    )
    text, ui = compute_diagnosis_posting_bundle(object(), 3)
    assert ui is not None
    assert "NICHE_POSTING_CONTEXT" in text
    assert len(ui["grid"]) == 7
    assert len(ui["grid"][0]) == 8
