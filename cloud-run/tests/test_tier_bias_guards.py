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


def test_resolve_mode_win_intent_unknown_tier_is_neutral() -> None:
    # Unified flow: no cohort + win intent → neutral balanced prompt, not a
    # forced win (we can't confirm a hit without measurement).
    assert resolve_extraction_mode("win", {"views": 10}, None) == "average"


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


def test_resolve_mode_channel_breakout_maps_to_win() -> None:
    # No corpus benchmark, but ≥2× the channel median upgrades the early tier
    # to hit. Unified flow maps hit → the win (strength-led) extraction prompt.
    out = resolve_extraction_mode(
        "flop",
        {"views": 50_000, "creator_median_views": 10_000},
        None,
    )
    assert out == "win"


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


def test_v6_headline_multiplier_names_its_baseline() -> None:
    """2026-06-12 audit: headline said «X× mức view thường» without naming the
    baseline. The prompt must demand the comparison standard — niche-format
    average or the channel's own normal — and forbid the bare phrasing."""
    from getviews_pipeline.diagnose_prompts import DIAGNOSIS_V6_JSON_INSTRUCTION as v6

    assert "khi nêu bội số phải nói rõ chuẩn nào" in v6
    assert "«so với TB format ngách»" in v6
    assert "«so với mức thường của kênh»" in v6
    assert "không nói trống «mức view thường»" in v6


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
    assert "SECTION diagnosis (tier=average" in prompt
    assert "≤90 từ" in prompt
    assert "ưu tiên 4 câu trong ngân sách ≤90 từ" in prompt
    assert "≤50 từ" not in prompt


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
    """Pin the generative Lightreel moves applied to video diagnosis:
    mechanism-level headline, coined archetype + keep-rule in diagnosis,
    and pattern-lock over reference tiles."""
    from getviews_pipeline.diagnose_prompts import DIAGNOSIS_V6_JSON_INSTRUCTION as v6

    # Headline names the mechanism with a timestamp, not the symptom.
    assert "gọi đúng CƠ CHẾ kèm mốc giây" in v6
    # Diagnosis: optional coined pattern name + keep-one-thing rule.
    assert "tên hình mẫu 2-4 từ" in v6
    assert "KHÔNG bịa archetype" in v6
    assert "GIỮ NGUYÊN có bằng chứng" in v6
    # Niche pattern: induced common denominator of the cited tiles only.
    assert "KHÓA PATTERN" in v6
    assert "Không bịa mẫu số chung ngoài tile đã trích" in v6
    # Findings: second-level evidence from the digest.
    assert "trích đúng mốc giây từ digest" in v6


# ── Salience-structure audit fixes (2026-06-11) ──────────────────────


def test_section_cap_keeps_highest_salience_not_display_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the 7-section cap bites, non-priority slots go to the sections
    with the strongest signals — not to whichever has the lowest static
    display_order."""
    from getviews_pipeline.diagnose_sections import _reorder_and_cap_sections
    from getviews_pipeline.settings import settings
    from getviews_pipeline.signals.base import Signal

    # Guards the legacy cap-DROP path; rank-only mode (default on) keeps all
    # sections by design, so pin it off to exercise the cap.
    monkeypatch.setattr(settings, "diagnosis_salience_rank_only", False)

    def sig(sid: str, sal: float) -> Signal:
        return Signal(id=f"{sid}_s", section_id=sid, taxonomy_ref="t",
                      salience=sal, claim="c")

    # 4 priority sections + 4 non-priority candidates competing for 3 slots.
    sections = [
        "diagnosis", "compliance", "hook_analysis", "niche_pattern",
        "metadata", "editing", "sound", "persona",
    ]
    manifest = {
        "metadata": [sig("metadata", 0.50)],   # lowest display_order of the four
        "editing": [sig("editing", 0.55)],
        "sound": [sig("sound", 0.62)],
        "persona": [sig("persona", 0.90)],     # highest salience, last display_order
    }
    out = _reorder_and_cap_sections(sections, manifest=manifest)
    assert len(out) == 7
    # persona (0.90), sound (0.62), editing (0.55) win; metadata (0.50) drops.
    assert "persona" in out and "sound" in out and "editing" in out
    assert "metadata" not in out
    # Legacy fallback without a manifest keeps the old display-order slice.
    legacy = _reorder_and_cap_sections(sections)
    assert "metadata" not in legacy
    assert "persona" in legacy and "sound" in legacy and "editing" in legacy


def test_section_cap_reserves_script_structure_over_context_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anatomy (script_structure) survives the cap even with zero signal salience,
    displacing the weakest context section (mukbang regression — the structure
    block was lost to channel/commerce/boost)."""
    from getviews_pipeline.diagnose_sections import _reorder_and_cap_sections
    from getviews_pipeline.settings import settings
    from getviews_pipeline.signals.base import Signal

    # Guards the legacy cap-DROP path; rank-only mode (default on) keeps all
    # sections by design, so pin it off to exercise the cap.
    monkeypatch.setattr(settings, "diagnosis_salience_rank_only", False)

    def sig(sid: str, sal: float) -> Signal:
        return Signal(id=f"{sid}_s", section_id=sid, taxonomy_ref="t",
                      salience=sal, claim="c")

    # 4 priority present + 3 high-salience context + script_structure (no signals).
    sections = [
        "diagnosis", "hook_analysis", "niche_pattern", "compliance",
        "channel_pattern", "commerce", "boost_attribution", "script_structure",
    ]
    manifest = {
        "channel_pattern": [sig("channel_pattern", 0.85)],
        "commerce": [sig("commerce", 0.76)],
        "boost_attribution": [sig("boost_attribution", 0.84)],
        # script_structure intentionally has no signals → _max_salience 0.0
    }
    out = _reorder_and_cap_sections(sections, manifest=manifest)
    assert len(out) == 7
    assert "script_structure" in out, "reserved anatomy must survive the cap"
    # The lowest-salience context section (commerce 0.76) is displaced instead.
    assert "commerce" not in out
    assert "channel_pattern" in out and "boost_attribution" in out
    # Reserved section keeps its display-order position (after channel, before boost).
    assert out.index("channel_pattern") < out.index("script_structure")
    assert out.index("script_structure") < out.index("boost_attribution")


def test_v6_salience_semantics_and_orphan_sections_classified() -> None:
    from getviews_pipeline.diagnose_prompts import DIAGNOSIS_V6_JSON_INSTRUCTION as v6

    # The LLM is told what salience means and to track the manifest.
    assert "BÁM SIGNAL_MANIFEST" in v6
    assert "salience CAO NHẤT" in v6
    assert "khớp đúng 1 signal_id" in v6
    # commerce is issue-based; boost_attribution is non-issue.
    assert "script_structure, commerce)" in v6
    assert "niche_pattern, channel_pattern, douyin_origin, boost_attribution)" in v6
    assert "persona: khi emit riêng" in v6
