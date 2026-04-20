"""Phase C.0.1 — deterministic + Gemini merge rules."""
from __future__ import annotations

from getviews_pipeline.intent_router import destination_for_gemini_primary_label
from getviews_pipeline.intents import QueryIntent, merge_deterministic_with_gemini


def test_destination_for_gemini_primary_label_maps_timing() -> None:
    assert destination_for_gemini_primary_label("timing") == "answer:timing"
    assert destination_for_gemini_primary_label("not_a_label") == "answer:generic"


def test_merge_keeps_deterministic_when_gemini_follow_up() -> None:
    r = merge_deterministic_with_gemini(
        QueryIntent.TIMING,
        {"primary": "follow_up", "secondary": None, "niche_hint": None},
    )
    assert r["primary"] == "timing"


def test_merge_gemini_wins_when_deterministic_was_follow_up() -> None:
    r = merge_deterministic_with_gemini(
        QueryIntent.FOLLOW_UP_UNCLASSIFIABLE,
        {"primary": "timing", "secondary": None, "niche_hint": None},
    )
    assert r["primary"] == "timing"


def test_merge_gemini_wins_on_specific_disagreement_when_confident() -> None:
    r = merge_deterministic_with_gemini(
        QueryIntent.TREND_SPIKE,
        {
            "primary": "content_directions",
            "secondary": None,
            "niche_hint": None,
            "primary_confidence": 0.9,
        },
    )
    assert r["primary"] == "content_directions"


def test_merge_disagreement_low_confidence_keeps_deterministic() -> None:
    r = merge_deterministic_with_gemini(
        QueryIntent.TREND_SPIKE,
        {
            "primary": "content_directions",
            "secondary": None,
            "niche_hint": None,
            "primary_confidence": 0.15,
        },
    )
    assert r["primary"] == "trend_spike"


def test_merge_agreement_uses_same_label() -> None:
    r = merge_deterministic_with_gemini(
        QueryIntent.TIMING,
        {"primary": "timing", "secondary": None, "niche_hint": "skincare"},
    )
    assert r["primary"] == "timing"
    assert r.get("niche_hint") == "skincare"


def test_merge_unknown_gemini_primary_normalized() -> None:
    r = merge_deterministic_with_gemini(
        QueryIntent.VIDEO_DIAGNOSIS,
        {"primary": "not_a_real_label", "secondary": None, "niche_hint": None},
    )
    assert r["primary"] == "video_diagnosis"
