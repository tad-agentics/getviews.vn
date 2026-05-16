"""ME-19 — carousel swipe psychology fields on SlideAnalysis / CarouselAnalysis."""

from __future__ import annotations

import pytest

from getviews_pipeline.models import CarouselAnalysis


def _minimal_carousel_dict(**extra: object) -> dict:
    base = {
        "hook_analysis": {
            "first_frame_type": "text_only",
            "hook_phrase": "Hook",
            "hook_type": "how_to",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "slides": [{"index": 0, "visual_type": "text_card", "text_on_slide": ["A"]}],
        "transitions_per_second": 0.0,
        "energy_level": "medium",
        "key_timestamps": [],
        "audio_transcript": "",
        "tone": "educational",
        "topics": [],
        "key_messages": [],
        "cta": None,
        "content_direction": {"what_works": "x", "suggested_angles": []},
    }
    base.update(extra)
    return base


def test_legacy_carousel_without_me19_fields_validates() -> None:
    m = CarouselAnalysis.model_validate(_minimal_carousel_dict())
    assert m.slides[0].swipe_anchor is None
    assert m.slides[0].layout is None
    assert m.audio_track_role is None
    assert m.dominant_color_palette is None
    assert m.slide_pacing_score is None


def test_me19_fields_round_trip() -> None:
    d = _minimal_carousel_dict(
        slides=[
            {
                "index": 0,
                "visual_type": "text_card",
                "text_on_slide": ["7 mẹo"],
                "swipe_anchor": "numbered_progression",
                "layout": "text_only",
            },
            {
                "index": 1,
                "visual_type": "product_shot",
                "text_on_slide": [],
                "swipe_anchor": "cliffhanger_image",
                "layout": "photo_with_caption",
            },
        ],
        audio_track_role="trending_sound",
        dominant_color_palette="hồng pastel + trắng",
        slide_pacing_score=0.85,
    )
    m = CarouselAnalysis.model_validate(d)
    assert m.slides[0].swipe_anchor == "numbered_progression"
    assert m.slides[0].layout == "text_only"
    assert m.slides[1].swipe_anchor == "cliffhanger_image"
    assert m.audio_track_role == "trending_sound"
    assert m.dominant_color_palette == "hồng pastel + trắng"
    assert m.slide_pacing_score == 0.85


def test_slide_pacing_score_out_of_range_rejected() -> None:
    d = _minimal_carousel_dict(slide_pacing_score=1.5)
    with pytest.raises(Exception):
        CarouselAnalysis.model_validate(d)


def test_invalid_swipe_anchor_rejected() -> None:
    d = _minimal_carousel_dict(
        slides=[{"index": 0, "visual_type": "text_card", "swipe_anchor": "not_valid"}]
    )
    with pytest.raises(Exception):
        CarouselAnalysis.model_validate(d)
