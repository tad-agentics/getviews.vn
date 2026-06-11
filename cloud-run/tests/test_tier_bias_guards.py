"""2026-06-11 — outcome-bias guards on the video diagnosis pipeline.

Background: the performance tier conditioned the whole report in two
biased ways — (a) error extraction was binary, so measured-AVERAGE videos
got the forced-error flop prompt (and a fabricated fallback error when
Gemini found nothing), and (b) the synthesis saw only the tier label,
never the ratio/age behind it. These tests pin the fixes:

* ``resolve_extraction_mode`` — tier-aware three-mode mapping.
* ``extract_video_errors(extraction_mode="average")`` — balanced prompt,
  empty error list allowed (no fabricated fallback).
* V6 synthesis prompt — anti-bias rules + ratio/age in user_stats_trim.
* ``default_section_title`` — "early" tier never gets flop titles.
* ``_video_age_days_from_meta`` — timestamp parsing for the age guard.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from getviews_pipeline.video_report_coherence import resolve_extraction_mode

# ── resolve_extraction_mode ──────────────────────────────────────────


def test_resolve_mode_win_passthrough() -> None:
    assert resolve_extraction_mode("win", {"views": 10}, None) == "win"


def test_resolve_mode_measured_flop_stays_flop() -> None:
    out = resolve_extraction_mode(
        "flop", {"views": 100}, {"avg_views": 10_000},
    )
    assert out == "flop"


def test_resolve_mode_measured_average_softens() -> None:
    out = resolve_extraction_mode(
        "flop", {"views": 8_000}, {"avg_views": 10_000},
    )
    assert out == "average"


def test_resolve_mode_unknown_benchmark_respects_flop_intent() -> None:
    # No corpus average → no evidence against the caller's flop framing.
    assert resolve_extraction_mode("flop", {"views": 100}, None) == "flop"
    assert resolve_extraction_mode("flop", {"views": 100}, {"avg_views": 0}) == "flop"


def test_resolve_mode_channel_breakout_softens() -> None:
    # No corpus benchmark, but ≥2× the channel median upgrades the early
    # tier to hit — the flop prompt would contradict measured performance.
    out = resolve_extraction_mode(
        "flop",
        {"views": 50_000, "creator_median_views": 10_000},
        None,
    )
    assert out == "average"


def test_resolve_mode_measured_corpus_flop_beats_channel_breakout() -> None:
    # Existing coherence semantics: a measured corpus flop is not overridden
    # by the channel-median hint inside infer_early_performance_tier.
    out = resolve_extraction_mode(
        "flop",
        {"views": 50_000, "creator_median_views": 10_000},
        {"avg_views": 200_000},
    )
    assert out == "flop"


# ── extraction "average" mode — balanced prompt, no fabricated error ──


def _run_extraction(monkeypatch: pytest.MonkeyPatch, mode: str) -> tuple[list, str]:
    seen: dict[str, str] = {}

    def fake_generate(contents, **kwargs):
        seen["prompt"] = contents[0]
        out = MagicMock()
        out.text = '{"errors": []}'
        return out

    monkeypatch.setattr(
        "getviews_pipeline.gemini._generate_content_models", fake_generate,
    )
    from getviews_pipeline.services.extraction import extract_video_errors

    errs = extract_video_errors(
        extraction_mode=mode,  # type: ignore[arg-type]
        video={"creator_handle": "x", "views": 8_000, "engagement_rate": 0.05,
               "content_format": "talk"},
        analysis={"hook_analysis": {"hook_phrase": "test"}},
        niche_label="Beauty",
        niche_row={"avg_views": 10_000, "avg_retention": 0.4, "sample_size": 100},
        retention_curve=None,
    )
    return errs, seen["prompt"]


def test_average_mode_prompt_and_empty_errors_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    errs, prompt = _run_extraction(monkeypatch, "average")
    assert "Chế độ TRUNG BÌNH" in prompt
    assert "không bịa lỗi" in prompt
    # Crucially: NO fabricated ERR_fallback_extraction for average mode.
    assert errs == []


def test_flop_mode_keeps_fallback_error(monkeypatch: pytest.MonkeyPatch) -> None:
    errs, prompt = _run_extraction(monkeypatch, "flop")
    assert "Chế độ FLOP" in prompt
    assert len(errs) == 1
    assert errs[0]["error_id"] == "ERR_fallback_extraction"


# ── V6 synthesis prompt — anti-bias rules + ratio/age context ────────


def test_v6_rules_contain_anti_bias_block() -> None:
    from getviews_pipeline.diagnose_prompts import DIAGNOSIS_V6_JSON_INSTRUCTION

    assert "KHÁCH QUAN VỚI PERFORMANCE_TIER" in DIAGNOSIS_V6_JSON_INSTRUCTION
    assert "KẾT QUẢ cần giải thích" in DIAGNOSIS_V6_JSON_INSTRUCTION
    # Symmetric guard: hits must still name an improvement.
    assert "tier=hit: vẫn nêu ít nhất 1 điểm cải thiện" in DIAGNOSIS_V6_JSON_INSTRUCTION
    # Early tier never concluded as flop.
    assert "tier=early" in DIAGNOSIS_V6_JSON_INSTRUCTION


def test_v6_user_stats_trim_carries_ratio_and_age() -> None:
    from getviews_pipeline.diagnose_prompts import build_diagnosis_v6_user_prompt

    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["diagnosis"],
        manifest_for_llm={},
        ctx={},
        content_format="talking_head",
        niche_name="Beauty",
        corpus_size=120,
        reference_videos=[],
        user_analysis={},
        user_stats={
            "caption": "c", "views": 8000,
            "views_vs_avg_ratio": 0.8, "video_age_days": 12.0,
        },
        performance_tier="average",
        channel_context=None,
        errors=None,
        wants_directions=False,
    )
    assert "views_vs_avg_ratio" in prompt
    assert "0.8" in prompt
    assert "video_age_days" in prompt
    assert "12.0" in prompt


# ── section titles — early tier maps to neutral set ──────────────────


def test_default_section_title_early_uses_average_titles() -> None:
    from getviews_pipeline.diagnose_sections import default_section_title

    assert default_section_title("diagnosis", "early") == default_section_title(
        "diagnosis", "average",
    )
    # And never the flop title when they differ.
    flop_title = default_section_title("diagnosis", "flop")
    early_title = default_section_title("diagnosis", "early")
    if flop_title != default_section_title("diagnosis", "average"):
        assert early_title != flop_title


# ── _video_age_days_from_meta ─────────────────────────────────────────


def test_video_age_days_parses_iso_and_epoch() -> None:
    from getviews_pipeline.video_analyze import _video_age_days_from_meta

    two_days_ago = datetime.now(tz=UTC) - timedelta(days=2)
    iso = two_days_ago.isoformat().replace("+00:00", "Z")
    age = _video_age_days_from_meta({"created_at": iso})
    assert age is not None and 1.9 < age < 2.1

    epoch = int(two_days_ago.timestamp())
    age2 = _video_age_days_from_meta({"create_time": epoch})
    assert age2 is not None and 1.9 < age2 < 2.1


def test_video_age_days_graceful_on_garbage() -> None:
    from getviews_pipeline.video_analyze import _video_age_days_from_meta

    assert _video_age_days_from_meta({}) is None
    assert _video_age_days_from_meta({"created_at": "not-a-date"}) is None
    # Future timestamp (clock skew) → None, never negative.
    future = (datetime.now(tz=UTC) + timedelta(days=2)).isoformat()
    assert _video_age_days_from_meta({"created_at": future}) is None


# ── Lightreel contract on the V6 video prompt (2026-06-11 follow-up) ──


def test_v6_lightreel_generative_rules_pinned() -> None:
    """Pin the four generative Lightreel moves applied to video diagnosis:
    mechanism-level headline, coined archetype + keep-rule in diagnosis,
    pattern-lock over reference tiles, and GIỮ/ĐỔI + rhythm-mirror in
    next_video."""
    from getviews_pipeline.diagnose_prompts import DIAGNOSIS_V6_JSON_INSTRUCTION as v6

    # Headline names the mechanism with a timestamp, not the symptom.
    assert "gọi đúng CƠ CHẾ kèm mốc giây" in v6
    # Diagnosis: coined archetype reused downstream + keep-one-thing rule.
    assert "tên archetype 2-4 từ tự đặt" in v6
    assert "GIỮ NGUYÊN có bằng chứng" in v6
    # Niche pattern: induced common denominator of the cited tiles only.
    assert "KHÓA PATTERN" in v6
    assert "Không bịa mẫu số chung ngoài tile đã trích" in v6
    # Next video: anti-repeat ledger + structure mirrored from one reference.
    assert "GIỮ / ĐỔI" in v6
    assert "bám NHỊP của đúng 1 video trong REFERENCE_EVIDENCE" in v6
    # Findings: second-level evidence from the digest.
    assert "trích đúng mốc giây từ digest" in v6
