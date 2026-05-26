"""``cover_url_from_aweme_detail`` — thumbnail backfill + corpus refresh."""
from __future__ import annotations

from getviews_pipeline.ensemble import cover_url_from_aweme_detail


def test_video_origin_cover() -> None:
    detail = {
        "aweme_id": "1",
        "video": {
            "origin_cover": {"url_list": ["https://cdn/origin.jpg"]},
            "cover": {"url_list": ["https://cdn/cover.jpg"]},
        },
    }
    assert cover_url_from_aweme_detail(detail) == "https://cdn/origin.jpg"


def test_video_dynamic_cover_fallback() -> None:
    detail = {
        "aweme_id": "2",
        "video": {
            "dynamic_cover": {"url_list": ["https://cdn/dynamic.jpg"]},
        },
    }
    assert cover_url_from_aweme_detail(detail) == "https://cdn/dynamic.jpg"


def test_carousel_first_slide() -> None:
    detail = {
        "aweme_id": "3",
        "aweme_type": 2,
        "image_post_info": {
            "images": [
                {"display_image": {"url_list": ["https://cdn/slide0.jpg"]}},
            ],
        },
    }
    assert cover_url_from_aweme_detail(detail) == "https://cdn/slide0.jpg"


def test_none_when_no_cover_fields() -> None:
    assert cover_url_from_aweme_detail({"aweme_id": "4", "video": {}}) is None
    assert cover_url_from_aweme_detail(None) is None
