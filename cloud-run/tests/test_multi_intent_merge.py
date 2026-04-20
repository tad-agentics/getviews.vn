"""Phase C.5.3 — multi-intent merge tests (plan §A.4).

Four §A.4 merge cases:
  1. Destination + report  — classifier returns destination, secondary is
     surfaced as an ActionCard on the destination screen. Unit-tested at
     the ``detect_pattern_subreports`` keyword boundary + the classifier
     (not covered here; lives in TS intent-router test suite).
  2. Report + report (same family) — classifier merges two pattern-family
     intents into one Pattern with `format_emphasis`. Not part of C.5.3
     scope; the Pattern builder reads `_intent_type` today.
  3. Report + timing — Pattern carries a `subreports.timing` block.
     **This suite covers it**: keyword detection + builder merge + UI
     attachment contract via the §J schema.
  4. Everything else — secondary signals become filter params on the
     primary report. No schema change; covered by existing intent-router
     tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.intent_router import detect_pattern_subreports
from getviews_pipeline.report_pattern import build_pattern_report
from getviews_pipeline.report_types import PatternPayload


# ── §A.4 case 3 — detection ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "query,expected",
    [
        ("giờ nào post tốt cho Tech?", ["timing"]),
        ("tuần này post gì khi nào cho mỹ phẩm", ["timing"]),
        ("thứ mấy đăng hiệu quả nhất?", ["timing"]),
        ("best time to post on TikTok", ["timing"]),
        ("posting time cho niche fitness", ["timing"]),
        ("khung giờ vàng tuần này", ["timing"]),
        ("lịch post cho tuần sau", ["timing"]),
    ],
)
def test_detect_pattern_subreports_matches_timing_cues(query: str, expected: list[str]) -> None:
    assert detect_pattern_subreports(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "",
        "   ",
        "hook nào đang hot tuần này",  # no timing keywords
        "video gì đang viral",
        "5 ý tưởng video tuần này",  # Ideas-shaped, not timing
        "format nào đang work",
    ],
)
def test_detect_pattern_subreports_no_match(query: str) -> None:
    assert detect_pattern_subreports(query) == []


# ── §A.4 case 3 — builder merges timing subreport ────────────────────────


@patch("getviews_pipeline.report_timing.build_timing_report")
def test_build_pattern_report_merges_timing_subreport(mock_timing: MagicMock) -> None:
    """Pattern + timing subreport produces a valid PatternPayload whose
    `subreports.timing` parses as a full TimingPayload shape."""
    mock_timing.return_value = {
        "confidence": {
            "sample_size": 112,
            "window_days": 14,
            "niche_scope": "Tech",
            "freshness_hours": 3,
            "intent_confidence": "high",
        },
        "top_window": {"day": "Thứ 7", "hours": "18–22", "lift_multiplier": 2.8},
        "top_3_windows": [
            {"rank": 1, "day": "Thứ 7", "hours": "18–22", "lift_multiplier": 2.8},
            {"rank": 2, "day": "Thứ 6", "hours": "20–22", "lift_multiplier": 2.2},
            {"rank": 3, "day": "Thứ 5", "hours": "20–22", "lift_multiplier": 2.0},
        ],
        "lowest_window": {"day": "Thứ 2", "hours": "0–3"},
        "grid": [[1.0] * 8 for _ in range(7)],
        "variance_note": {"kind": "strong", "label": "Heatmap CÓ ý nghĩa"},
        "fatigue_band": None,
        "actions": [],
        "sources": [],
        "related_questions": [],
    }
    # Force the builder through the fixture-fallback branch (no service client).
    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        side_effect=ValueError("no env"),
    ):
        inner = build_pattern_report(
            1,
            "post gì khi nào tuần này",
            "content_calendar",
            window_days=14,
            subreports=["timing"],
        )
    p = PatternPayload.model_validate(inner)
    assert p.subreports is not None
    assert "timing" in p.subreports
    timing_sub = p.subreports["timing"]
    assert isinstance(timing_sub, dict)
    assert timing_sub["variance_note"]["kind"] == "strong"
    mock_timing.assert_called_once()


def test_build_pattern_report_no_subreports_when_absent() -> None:
    """Default path: no `subreports` arg → payload.subreports stays None."""
    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        side_effect=ValueError("no env"),
    ):
        inner = build_pattern_report(1, "hook nào đang hot", "trend_spike", window_days=7)
    p = PatternPayload.model_validate(inner)
    assert p.subreports is None


def test_build_pattern_report_unknown_subreport_key_drops_silently() -> None:
    """Unknown keys shouldn't break the primary payload — plan §A.4 says
    'Pattern is primary, subreports are nice-to-have'."""
    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        side_effect=ValueError("no env"),
    ):
        inner = build_pattern_report(
            1,
            "hook nào đang hot",
            "trend_spike",
            window_days=7,
            subreports=["made_up_key"],
        )
    p = PatternPayload.model_validate(inner)
    # Unknown key dropped → subreports is None (serialises null).
    assert p.subreports is None


@patch("getviews_pipeline.report_timing.build_timing_report")
def test_build_pattern_report_timing_subreport_failure_does_not_abort_primary(
    mock_timing: MagicMock,
) -> None:
    """If timing builder raises, Pattern still ships — subreport is dropped."""
    mock_timing.side_effect = RuntimeError("timing blew up")
    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        side_effect=ValueError("no env"),
    ):
        inner = build_pattern_report(
            1,
            "post gì khi nào",
            "content_calendar",
            window_days=14,
            subreports=["timing"],
        )
    p = PatternPayload.model_validate(inner)
    # Subreport failed → None, primary payload still validates.
    assert p.subreports is None
