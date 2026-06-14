"""Presentation & synthesis-surface v1 — lint, peer ts, wide digest, proposed findings."""

from __future__ import annotations

from getviews_pipeline.diagnose_prompts import build_user_evidence_digest
from getviews_pipeline.diagnosis_quality import (
    DIAGNOSIS_V6_TOTAL_RETRY_MAX,
    diagnosis_v6_word_budget_exceeded,
)
from getviews_pipeline.gemini import _normalize_proposed_findings
from getviews_pipeline.voice_lint import lint_forbidden_copy, scrub_forbidden_copy


def test_scrub_forbidden_copy_soft_scrubs_guru_words() -> None:
    raw = "Video có tiềm năng bùng nổ nếu sửa hook."
    cleaned, violations = scrub_forbidden_copy(raw)
    assert violations
    assert "bùng nổ" not in cleaned.lower()
    assert lint_forbidden_copy(cleaned) == []


def test_scrub_forbidden_copy_respects_word_boundaries() -> None:
    # "hack" inside "hackathon" must survive; the standalone "bùng nổ" is scrubbed.
    raw = "Dùng hackathon để bùng nổ view."
    cleaned, violations = scrub_forbidden_copy(raw)
    assert "hackathon" in cleaned
    assert "bùng nổ" not in cleaned.lower()
    assert lint_forbidden_copy(cleaned) == []


def test_wide_context_digest_includes_retention_and_benchmark() -> None:
    digest = build_user_evidence_digest(
        {"scenes": [{"start_s": 0, "end_s": 2, "framing": "close_up"}]},
        wide_context=True,
        user_stats={
            "retention_curve": [{"t": 0, "pct": 100}, {"t": 3, "pct": 70}],
            "niche_benchmark_curve": [{"t": 0, "pct": 100}, {"t": 3, "pct": 80}],
            "distribution_shape": "spike_then_flat",
        },
    )
    assert "retention_curve" in digest
    assert "niche_benchmark_curve" in digest
    assert digest["distribution_shape"] == "spike_then_flat"
    assert len(digest["scene_pattern"]) >= 1


def test_proposed_findings_stripped_when_flag_off() -> None:
    diag = {
        "sections": [
            {
                "section_id": "diagnosis",
                "findings": [
                    {"title_vi": "A", "confidence_tier": "proposed"},
                    {"title_vi": "B"},
                ],
            }
        ]
    }
    _normalize_proposed_findings(diag, enabled=False)
    assert len(diag["sections"][0]["findings"]) == 1


def test_total_retry_budget_is_600() -> None:
    assert DIAGNOSIS_V6_TOTAL_RETRY_MAX == 600
    diag = {"sections": [{"section_id": "diagnosis", "text": "w " * 601}]}
    assert diagnosis_v6_word_budget_exceeded(diag) is True
