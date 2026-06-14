"""Extraction signals v2 — Tier 1 deterministic + Tier 2 schema + prompt grounding."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from getviews_pipeline.diagnose_prompts import build_diagnosis_v6_user_prompt, build_user_evidence_digest
from getviews_pipeline.models import HookAnalysis, VideoAnalysis
from getviews_pipeline.services import asr_vietnamese as asr
from getviews_pipeline.services.asr_vietnamese import (
    _parse_recognition_results,
    asr_words_from_segments,
    fetch_asr_segments,
)
from getviews_pipeline.services.extraction import (
    VideoErrorsExtractionInput,
    _summarise_extraction_signals_v2,
)
from getviews_pipeline.video_structural import (
    DEAD_AIR_GAP_SEC,
    _asr_silence_gaps,
    _hook_echo_score,
    compute_information_density,
    compute_loopability,
    compute_tier1_extraction_signals,
)


def _word(start: float, end: float, w: str) -> dict:
    return {"w": w, "start": start, "end": end}


def test_asr_parse_preserves_word_entries() -> None:
    w1 = SimpleNamespace(
        word="Xin",
        start_time=SimpleNamespace(seconds=0, nanos=0),
        end_time=SimpleNamespace(seconds=0, nanos=800_000_000),
    )
    w2 = SimpleNamespace(
        word="chào",
        start_time=SimpleNamespace(seconds=1, nanos=0),
        end_time=SimpleNamespace(seconds=1, nanos=500_000_000),
    )
    alt = SimpleNamespace(transcript="Xin chào", words=[w1, w2])
    result = SimpleNamespace(results=[SimpleNamespace(alternatives=[alt])])
    segs = _parse_recognition_results(result)
    assert len(segs) == 1
    assert "words" in segs[0]
    assert len(segs[0]["words"]) == 2
    flat = asr_words_from_segments(segs)
    assert flat[0]["w"] == "Xin"


def test_fetch_asr_segments_passes_words_through() -> None:
    row = {
        "transcript": {
            "segments": [
                {
                    "start_sec": 0.0,
                    "end_sec": 2.0,
                    "text": "Test",
                    "words": [_word(0.0, 1.0, "Test")],
                }
            ]
        }
    }
    with patch.object(asr, "_fetch_cache", return_value=row):
        segs = fetch_asr_segments("vid")
    assert segs[0].get("words")


def test_time_to_first_value_skips_hook_filler() -> None:
    words = [
        _word(0.2, 0.5, "ừ"),
        _word(0.6, 0.9, "nè"),
        _word(3.5, 3.8, "review"),
        _word(3.9, 4.2, "sản"),
    ]
    info = compute_information_density([], words, 30.0, hook_window_sec=3.0)
    assert info["time_to_first_value_sec"] == pytest.approx(3.5)


def test_dead_air_ratio_excludes_silent_track() -> None:
    segs = [{"start_sec": 0.0, "end_sec": 2.0, "text": "A"}]
    info = compute_information_density(
        [],
        [_word(0.0, 2.0, "hello")],
        10.0,
        asr_segments=segs,
        audio_track_role="silent",
    )
    assert info["dead_air_ratio"] == 0.0


def test_asr_silence_gaps_detects_leading_and_trailing_dead_air() -> None:
    segs = [
        {"start_sec": 2.0, "end_sec": 4.0, "text": "A"},
        {"start_sec": 6.0, "end_sec": 7.0, "text": "B"},
    ]
    gaps = _asr_silence_gaps(segs, duration_sec=10.0, min_gap=DEAD_AIR_GAP_SEC)
    assert (0.0, 2.0) in gaps
    assert (4.0, 6.0) in gaps
    assert (7.0, 10.0) in gaps


def test_asr_silence_gaps_ignored_for_silent_track_via_info_density() -> None:
    segs = [{"start_sec": 0.0, "end_sec": 2.0, "text": "A"}]
    words = [_word(0.0, 2.0, "hello")]
    info = compute_information_density(
        [],
        words,
        10.0,
        asr_segments=segs,
        audio_track_role="silent",
    )
    assert info["dead_air_ratio"] == 0.0


def test_hook_echo_score_zero_when_no_overlap() -> None:
    assert _hook_echo_score("câu hỏi mở đầu", "kết bằng lời kêu mua") == 0.0


def test_hook_echo_score_high_when_closing_repeats_hook_tokens() -> None:
    score = _hook_echo_score(
        "mở bằng câu hỏi",
        "và kết lại bằng câu hỏi mở",
    )
    assert score >= 0.5


def test_hook_echo_score_empty_inputs_return_zero() -> None:
    assert _hook_echo_score("", "closing line") == 0.0
    assert _hook_echo_score("hook phrase", "") == 0.0


def test_loop_score_high_when_first_last_match_and_hook_echo() -> None:
    scenes = [
        {"start": 0, "end": 3, "type": "talking_head", "subject": "face", "framing": "close_up"},
        {"start": 3, "end": 10, "type": "b_roll", "subject": "product", "framing": "medium"},
        {"start": 10, "end": 15, "type": "talking_head", "subject": "face", "framing": "close_up"},
    ]
    loop = compute_loopability(
        scenes,
        "mở bằng câu hỏi và kết bằng câu hỏi mở",
        "trending_sound",
        "câu hỏi mở",
    )
    assert loop["loop_score"] >= 0.5


def test_redundancy_runs_counts_consecutive_scenes() -> None:
    scenes = [
        {"start": 0, "end": 2, "type": "demo", "subject": "product"},
        {"start": 2, "end": 4, "type": "demo", "subject": "product"},
        {"start": 4, "end": 6, "type": "demo", "subject": "product"},
        {"start": 6, "end": 8, "type": "cta", "subject": "face"},
    ]
    loop = compute_loopability(scenes, "", "spoken_overlay", "")
    assert loop["redundancy_runs"] == 3


def test_information_density_fallback_without_word_timing() -> None:
    info = compute_information_density([], None, 10.0, transcript="một hai ba bốn năm")
    assert info["words_per_sec"] == pytest.approx(0.5)
    assert info["word_timing"] == "segment_fallback"


def test_hook_analysis_tier2_round_trip() -> None:
    raw = {
        "first_frame_type": "face",
        "hook_phrase": "Test hook",
        "hook_type": "question",
        "hook_notes": "n",
        "opening_visual_energy": "high",
        "text_speech_sync": "text_first",
        "pattern_interrupt": True,
    }
    ha = HookAnalysis.model_validate(raw)
    assert ha.opening_visual_energy == "high"
    assert ha.pattern_interrupt is True


def test_video_analysis_old_json_without_tier2_still_validates() -> None:
    raw = {
        "hook_analysis": {
            "first_frame_type": "face",
            "hook_phrase": "Hi",
            "hook_type": "question",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "has_human_speaking_to_camera": True,
        "has_expressed_opinion_or_question": False,
        "text_overlays": [],
        "scenes": [{"type": "face_to_camera", "start": 0.0, "end": 5.0}],
        "transitions_per_second": 0.5,
        "energy_level": "medium",
        "key_timestamps": [],
        "audio_transcript": "Hi",
        "tone": "conversational",
        "topics": [],
        "key_messages": [],
        "cta": None,
        "content_direction": {"what_works": "x", "suggested_angles": []},
        "target_audience": "",
        "pain_points": [],
        "promotion_type": "organic",
        "style_tags": [],
    }
    va = VideoAnalysis.model_validate(raw)
    assert va.hook_analysis.hook_phrase == "Hi"
    assert va.hook_analysis.opening_visual_energy is None


def test_video_errors_input_excludes_signals_when_not_set() -> None:
    m = VideoErrorsExtractionInput(
        extraction_mode="flop",
        niche_label="x",
        views=1,
        engagement_rate=0.1,
    )
    dumped = m.model_dump(exclude_none=True)
    assert "time_to_first_value_sec" not in dumped
    assert "loop_score" not in dumped


def test_summarise_extraction_signals_v2_compact() -> None:
    s = _summarise_extraction_signals_v2(
        {
            "info_density": {
                "words_per_sec": 2.1,
                "time_to_first_value_sec": 6.0,
                "dead_air_ratio": 0.18,
            },
            "loopability": {"loop_score": 0.2, "redundancy_runs": 3},
            "hook_analysis": {"opening_visual_energy": "low", "pattern_interrupt": True},
        }
    )
    assert "2.1 từ/s" in s
    assert "0:06" in s
    assert "dead-air" in s


def test_video_errors_input_contract_optional_fields() -> None:
    m = VideoErrorsExtractionInput(
        extraction_mode="flop",
        niche_label="x",
        views=1,
        engagement_rate=0.1,
        time_to_first_value_sec=6.0,
        words_per_sec=2.0,
        loop_score=0.3,
    )
    assert m.time_to_first_value_sec == 6.0


def test_build_diagnosis_prompt_includes_extraction_note_when_flag_on() -> None:
    user_analysis = {
        "info_density": {"time_to_first_value_sec": 6.0, "words_per_sec": 2.0},
        "hook_analysis": {"hook_timeline": []},
    }
    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["script_structure", "hook_analysis"],
        manifest_for_llm={},
        ctx={},
        content_format="tutorial",
        niche_name="beauty",
        corpus_size=100,
        reference_videos=[],
        user_analysis=user_analysis,
        user_stats={"views": 1000},
        performance_tier="flop",
        channel_context=None,
        errors=[],
        wants_directions=False,
        extraction_signals_v2=True,
    )
    assert "EXTRACTION_SIGNALS" in prompt
    digest = build_user_evidence_digest(user_analysis, extraction_signals_v2=True)
    assert "info_density" in digest


def test_digest_omits_hook_forensics_when_flag_off() -> None:
    # Tier 2 fields are emitted by Gemini regardless of the flag; the digest
    # must NOT surface them when EXTRACTION_SIGNALS_V2 is off (Call 2 parity).
    user_analysis = {
        "hook_analysis": {
            "opening_visual_energy": "high",
            "pattern_interrupt": True,
        },
        "info_density": {"words_per_sec": 2.0},
        "loopability": {"loop_score": 0.3},
    }
    off = build_user_evidence_digest(user_analysis, extraction_signals_v2=False)
    assert "hook_forensics" not in off
    assert "info_density" not in off
    assert "loopability" not in off
    on = build_user_evidence_digest(user_analysis, extraction_signals_v2=True)
    assert "hook_forensics" in on
    assert "info_density" in on


def test_build_diagnosis_prompt_flag_off_no_extraction_note() -> None:
    user_analysis = {
        "info_density": {"time_to_first_value_sec": 6.0},
    }
    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["script_structure"],
        manifest_for_llm={},
        ctx={},
        content_format="tutorial",
        niche_name="beauty",
        corpus_size=100,
        reference_videos=[],
        user_analysis=user_analysis,
        user_stats={"views": 1000},
        performance_tier="flop",
        channel_context=None,
        errors=[],
        wants_directions=False,
        extraction_signals_v2=False,
    )
    assert "EXTRACTION_SIGNALS" not in prompt


def test_compute_tier1_integration() -> None:
    scenes = [{"start": 0, "end": 10, "type": "a", "subject": "face", "framing": "close_up"}]
    segs = [
        {
            "start_sec": 0.0,
            "end_sec": 5.0,
            "text": "hello world",
            "words": [_word(0.0, 1.0, "hello"), _word(1.1, 2.0, "world")],
        }
    ]
    info, loop = compute_tier1_extraction_signals(
        scenes=scenes,
        duration_sec=10.0,
        asr_segments=segs,
        hook_phrase="hello",
    )
    assert info["words_per_sec"] > 0
    assert "loop_score" in loop
