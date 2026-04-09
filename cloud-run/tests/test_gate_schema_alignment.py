"""§19 Gate 2b alignment: checklist fields match shipped Pydantic models."""

from __future__ import annotations

from getviews_pipeline.models import CarouselAnalysis, VideoAnalysis


def test_video_analysis_has_hook_analysis_not_hook_slide() -> None:
    schema = VideoAnalysis.model_json_schema()
    props = schema.get("properties", {})
    assert "hook_analysis" in props
    assert "hook_slide" not in props


def test_carousel_analysis_uses_slides_not_story_arc() -> None:
    schema = CarouselAnalysis.model_json_schema()
    props = schema.get("properties", {})
    assert "slides" in props
    assert "story_arc" not in props
    assert "swipe_incentive" not in props


def test_reference_count_default_three_helpers() -> None:
    from getviews_pipeline.helpers import select_reference_videos

    now = 1_700_000_000
    base = {
        "aweme_id": "1",
        "create_time": now - 86400,
        "author": {"uid": "a1"},
        "statistics": {
            "play_count": 1000,
            "digg_count": 100,
            "comment_count": 10,
            "share_count": 5,
        },
    }
    pool = [{**base, "aweme_id": str(i), "author": {"uid": f"a{i}"}} for i in range(10)]
    picked = select_reference_videos(pool, recency_days=30, n=3, now=now)
    assert len(picked) == 3


def test_carousel_gate_extract_cap_matches_config() -> None:
    from getviews_pipeline.config import CAROUSEL_EXTRACT_MAX_SLIDES

    assert CAROUSEL_EXTRACT_MAX_SLIDES >= 5
