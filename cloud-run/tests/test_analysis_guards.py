"""Unit tests for analysis_guards.

Pure functions only — no Supabase / Gemini / network. Covers the four trust
guards shipped to close the video-frame-analysis audit P0/P1 findings.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from getviews_pipeline.analysis_guards import (
    apply_timestamp_guards,
    clamp_scene_range,
    clamp_timestamp,
    is_cached_analysis_fresh,
    scan_synthesis_for_fabricated_metrics,
    validate_transcript,
)


# ── validate_transcript ────────────────────────────────────────────────────


def test_transcript_ok_for_real_vietnamese() -> None:
    v = validate_transcript(
        "Chào mọi người hôm nay mình review serum Hàn Quốc cho da dầu mụn. "
        "Cùng mình thử xem nhé!"
    )
    assert v.ok is True
    assert v.reason == "ok"
    assert v.vi_ratio > 0.05


def test_transcript_flags_english_as_no_vietnamese() -> None:
    v = validate_transcript(
        "Hello guys, today I'm reviewing a Korean serum for oily acne-prone skin. "
        "Let's try it together."
    )
    assert v.ok is False
    assert v.reason == "no_vietnamese"


def test_transcript_short_clip_accepted() -> None:
    # Genuine short product cutaway — 2 words is legit.
    v = validate_transcript("Xem ngay.")
    assert v.ok is True
    assert v.reason == "too_short"


def test_transcript_placeholder_only_rejected() -> None:
    v = validate_transcript("[không rõ]")
    assert v.ok is False
    assert v.reason == "placeholder_only"


def test_transcript_mostly_noise_rejected() -> None:
    # 40+ chars but mostly punctuation + numbers.
    v = validate_transcript("!!!!!!! ???? ---- ///// 1234 5678 !!!! ???? $$$$ %%%%")
    assert v.ok is False
    assert v.reason == "mostly_noise"


def test_transcript_empty_is_ok_too_short() -> None:
    assert validate_transcript("").ok is True
    assert validate_transcript("   ").ok is True


def test_transcript_vietnamese_with_unclear_marker_still_ok() -> None:
    v = validate_transcript(
        "Mình sẽ thử sản phẩm này hôm nay [không rõ] và cảm nhận sau vài tuần."
    )
    assert v.ok is True


# ── clamp_timestamp ────────────────────────────────────────────────────────


def test_clamp_none_passes_through() -> None:
    assert clamp_timestamp(None, 30.0) is None


def test_clamp_accepts_valid() -> None:
    assert clamp_timestamp(0.5, 30.0) == 0.5
    assert clamp_timestamp(29.9, 30.0) == 29.9


def test_clamp_negative_becomes_none() -> None:
    assert clamp_timestamp(-1.0, 30.0) is None


def test_clamp_way_out_of_range_becomes_none() -> None:
    # Past the 0.5s slack.
    assert clamp_timestamp(45.0, 30.0) is None


def test_clamp_within_slack_clamps_to_duration() -> None:
    # Off by one frame (~0.033s) — accepted, clamped to duration.
    assert clamp_timestamp(30.2, 30.0) == 30.0


def test_clamp_no_duration_returns_unchanged() -> None:
    # When duration is None we can't validate; return as-is.
    assert clamp_timestamp(5.0, None) == 5.0
    assert clamp_timestamp(5.0, 0) == 5.0


def test_clamp_nan_becomes_none() -> None:
    assert clamp_timestamp(float("nan"), 30.0) is None


def test_clamp_inf_becomes_none() -> None:
    assert clamp_timestamp(float("inf"), 30.0) is None


def test_clamp_scene_inverted_drops_both() -> None:
    # Gemini sometimes returns start > end on a mis-extracted cut.
    s, e = clamp_scene_range(5.0, 2.0, 30.0)
    assert s is None and e is None


def test_clamp_scene_normal_keeps_both() -> None:
    s, e = clamp_scene_range(2.0, 5.0, 30.0)
    assert s == 2.0 and e == 5.0


# ── apply_timestamp_guards ─────────────────────────────────────────────────


def test_apply_guards_nulls_ooo_face_appears_at() -> None:
    analysis = {
        "hook_analysis": {"face_appears_at": 45.0, "first_speech_at": 0.2},
        "text_overlays": [],
        "scenes": [],
    }
    apply_timestamp_guards(analysis, duration=12.0)
    assert analysis["hook_analysis"]["face_appears_at"] is None
    assert analysis["hook_analysis"]["first_speech_at"] == 0.2


def test_apply_guards_drops_bad_scenes() -> None:
    analysis = {
        "hook_analysis": {},
        "scenes": [
            {"type": "face", "start": 0.0, "end": 3.0},
            {"type": "action", "start": 8.0, "end": 100.0},  # OOR
            {"type": "text_card", "start": 5.0, "end": 2.0},  # inverted
        ],
        "text_overlays": [],
    }
    apply_timestamp_guards(analysis, duration=15.0)
    assert len(analysis["scenes"]) == 1
    assert analysis["scenes"][0]["type"] == "face"


def test_apply_guards_cleans_hook_timeline() -> None:
    analysis = {
        "hook_analysis": {
            "hook_timeline": [
                {"t": 0.2, "event": "face_enter"},
                {"t": 99.0, "event": "cut"},          # OOR
                {"t": 1.8, "event": "text_overlay"},
            ],
        },
        "scenes": [],
        "text_overlays": [],
    }
    apply_timestamp_guards(analysis, duration=15.0)
    timeline = analysis["hook_analysis"]["hook_timeline"]
    assert len(timeline) == 2
    assert [e["event"] for e in timeline] == ["face_enter", "text_overlay"]


def test_apply_guards_no_duration_is_noop_on_ranges() -> None:
    # Missing duration → leave timestamps alone (except NaN/Inf handled by clamp).
    analysis = {
        "hook_analysis": {"face_appears_at": 5.0},
        "scenes": [{"type": "face", "start": 1.0, "end": 4.0}],
        "text_overlays": [],
    }
    apply_timestamp_guards(analysis, duration=None)
    assert analysis["hook_analysis"]["face_appears_at"] == 5.0


def test_apply_guards_on_empty_analysis_noop() -> None:
    assert apply_timestamp_guards({}, duration=30.0) == {}


# ── is_cached_analysis_fresh ───────────────────────────────────────────────


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_fresh_recent() -> None:
    recent = datetime.now(tz=timezone.utc) - timedelta(days=3)
    assert is_cached_analysis_fresh(_iso(recent)) is True


def test_stale_past_ttl() -> None:
    stale = datetime.now(tz=timezone.utc) - timedelta(days=30)
    assert is_cached_analysis_fresh(_iso(stale)) is False


def test_custom_ttl() -> None:
    age = datetime.now(tz=timezone.utc) - timedelta(days=10)
    assert is_cached_analysis_fresh(_iso(age), ttl_days=7) is False
    assert is_cached_analysis_fresh(_iso(age), ttl_days=30) is True


def test_malformed_timestamp_treated_as_fresh() -> None:
    # We don't want a cache miss just because we can't parse the timestamp —
    # that would spike Gemini cost for every corrupted row.
    assert is_cached_analysis_fresh("not-a-date") is True


def test_none_is_not_fresh() -> None:
    assert is_cached_analysis_fresh(None) is False


def test_accepts_datetime_directly() -> None:
    assert is_cached_analysis_fresh(
        datetime.now(tz=timezone.utc) - timedelta(hours=1)
    ) is True


def test_naive_datetime_is_treated_as_utc() -> None:
    assert is_cached_analysis_fresh(
        (datetime.utcnow() - timedelta(days=1)).isoformat()
    ) is True


# ── scan_synthesis_for_fabricated_metrics ─────────────────────────────────


def test_scan_clean_on_anchored_prediction() -> None:
    text = (
        "Dựa trên 412 video skincare tháng này, hook dạng cảnh báo dự kiến tăng "
        "ER khoảng 3% trong tuần tới."
    )
    scan = scan_synthesis_for_fabricated_metrics(text)
    assert scan.clean
    assert scan.flags == ()


def test_scan_flags_unanchored_prediction() -> None:
    text = "Hook này dự kiến đạt 45% hook rate trong niche skincare."
    scan = scan_synthesis_for_fabricated_metrics(text)
    assert not scan.clean
    assert len(scan.flags) == 1


def test_scan_flags_english_prediction_words() -> None:
    text = "This hook is expected to drive 3x engagement in the first week."
    scan = scan_synthesis_for_fabricated_metrics(text)
    assert not scan.clean


def test_scan_ignores_number_without_prediction_word() -> None:
    text = "Video này đạt 180 nghìn views sau 5 ngày."
    scan = scan_synthesis_for_fabricated_metrics(text)
    assert scan.clean


def test_scan_handles_empty_text() -> None:
    assert scan_synthesis_for_fabricated_metrics("").clean
    assert scan_synthesis_for_fabricated_metrics("   ").clean


def test_scan_reports_multiple_violations() -> None:
    text = (
        "Hook rate dự kiến >45%. Completion rate ước tính tăng 20%. "
        "Ngoài ra content này có hook mạnh mẽ (không có số)."
    )
    scan = scan_synthesis_for_fabricated_metrics(text)
    assert len(scan.flags) == 2
