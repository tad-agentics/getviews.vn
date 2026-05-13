"""Rule-based error post-processing: duration window + lang/hook dedup."""

from __future__ import annotations

from getviews_pipeline.video_analyze import (
    _dedupe_lang_market_hook_errors,
    apply_rule_based_video_errors,
)


def test_no_human_presence_spans_full_duration() -> None:
    analysis = {
        "has_human_speaking_to_camera": False,
        "has_expressed_opinion_or_question": False,
    }
    errors = apply_rule_based_video_errors(
        [],
        analysis,
        "product_unboxing",
        duration_sec=12.5,
    )
    nh = next(e for e in errors if e.get("error_id") == "no_human_presence")
    assert nh["t"] == 0.0
    assert nh["end"] == 12.5


def test_dedupe_merges_hook_high_when_lang_market_present() -> None:
    errs = [
        {
            "error_id": "lang_market_mismatch",
            "sev": "high",
            "t": 0.0,
            "end": 3.0,
            "title": "EN hook",
            "detail": "",
            "fix": "Viết lại bằng tiếng Việt.",
        },
        {
            "error_id": "ERR_hook_generic",
            "sev": "high",
            "t": 0.0,
            "end": 2.0,
            "title": "Hook không định hướng",
            "detail": "",
            "fix": "Thêm câu hỏi cụ thể.",
        },
    ]
    out = _dedupe_lang_market_hook_errors(errs)
    assert len(out) == 1
    assert out[0]["error_id"] == "lang_market_mismatch"
    assert "Bổ sung" in str(out[0].get("fix") or "")
    assert "Thêm câu hỏi" in str(out[0].get("fix") or "")


def test_dedupe_hook_high_overlaps_hook_window_even_if_end_past_4s() -> None:
    """Range [0,5] overlaps [0,4]; must dedupe (old logic required end<=4 and missed this)."""
    errs = [
        {
            "error_id": "lang_market_mismatch",
            "sev": "high",
            "t": 0.0,
            "end": 3.0,
            "title": "EN hook",
            "detail": "",
            "fix": "Viết lại bằng tiếng Việt.",
        },
        {
            "error_id": "ERR_hook_generic",
            "sev": "high",
            "t": 0.0,
            "end": 5.0,
            "title": "Hook yếu",
            "detail": "",
            "fix": "Nói rõ lợi ích trong 2 giây đầu.",
        },
    ]
    out = _dedupe_lang_market_hook_errors(errs)
    assert len(out) == 1
    assert out[0]["error_id"] == "lang_market_mismatch"
    assert "Nói rõ lợi ích" in str(out[0].get("fix") or "")


def test_collapse_two_hook_high_without_lang_market() -> None:
    analysis = {
        "has_human_speaking_to_camera": True,
        "has_expressed_opinion_or_question": True,
    }
    raw = [
        {
            "error_id": "ERR_hook_open",
            "sev": "high",
            "t": 0.0,
            "end": 2.0,
            "title": "Hook một",
            "detail": "",
            "fix": "Fix A",
        },
        {
            "error_id": "ERR_hook_second",
            "sev": "high",
            "t": 0.0,
            "end": 3.0,
            "title": "Hook hai",
            "detail": "",
            "fix": "Fix B",
        },
    ]
    out = apply_rule_based_video_errors(
        raw,
        analysis,
        "tutorial",
        caption_hint="",
        duration_sec=30.0,
    )
    highs = [e for e in out if str(e.get("sev")) == "high"]
    assert len(highs) == 1
    assert "Gộp" in str(highs[0].get("fix") or "")


def test_no_human_skipped_when_product_first_frame() -> None:
    analysis = {
        "has_human_speaking_to_camera": False,
        "has_expressed_opinion_or_question": False,
        "hook_analysis": {"first_frame_type": "product"},
    }
    out = apply_rule_based_video_errors([], analysis, "tutorial", duration_sec=10.0)
    assert not any(e.get("error_id") == "no_human_presence" for e in out)


def test_dedupe_keeps_hook_high_outside_hook_window() -> None:
    errs = [
        {
            "error_id": "lang_market_mismatch",
            "sev": "high",
            "t": 0.0,
            "end": 3.0,
            "title": "EN hook",
            "detail": "",
            "fix": "Viết lại bằng tiếng Việt.",
        },
        {
            "error_id": "ERR_hook_generic",
            "sev": "high",
            "t": 5.0,
            "end": 6.0,
            "title": "Hook không định hướng",
            "detail": "",
            "fix": "Giữ nguyên fix riêng.",
        },
    ]
    out = _dedupe_lang_market_hook_errors(errs)
    assert len(out) == 2
    assert {e["error_id"] for e in out} == {"lang_market_mismatch", "ERR_hook_generic"}
