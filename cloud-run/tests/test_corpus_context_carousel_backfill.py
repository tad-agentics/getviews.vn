"""Tests for lazy carousel thumbnail backfill in refresh_stale_thumbnails.

Verifies that carousel rows (no aweme.video.cover) use the carousel slide URL
extracted via ensemble.extract_image_url_lists when refresh_stale_thumbnails
processes them on-read.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


_CAROUSEL_AWEME = {
    "aweme_id": "carousel_42",
    "thumbnail_url": "https://p16-sign.tiktokcdn.com/expired_thumb.jpg",
}

_VIDEO_AWEME = {
    "aweme_id": "video_99",
    "thumbnail_url": "https://p16-sign.tiktokcdn.com/expired_vid_thumb.jpg",
}

_FRESH_CAROUSEL_SLIDE_URL = "https://p16-sign.tiktokcdn.com/fresh_slide0.jpg"
_FRESH_VIDEO_COVER_URL = "https://p16-sign.tiktokcdn.com/fresh_cover.jpg"
_R2_RESULT_URL = "https://pub-abc.r2.dev/thumbnails/carousel_42.jpg"


def _make_carousel_detail(vid_id: str, slide_url: str) -> dict:
    return {
        "aweme_id": vid_id,
        # No aweme.video — carousel
        "image_post_info": {
            "images": [
                {"display_image": {"url_list": [slide_url]}}
            ]
        },
    }


def _make_video_detail(vid_id: str, cover_url: str) -> dict:
    return {
        "aweme_id": vid_id,
        "video": {
            "cover": {"url_list": [cover_url]},
        },
    }


@pytest.mark.asyncio
async def test_carousel_slide_url_extracted_for_backfill() -> None:
    """A stale carousel row should have its thumbnail repaired via the slide URL."""
    fresh_detail = _make_carousel_detail("carousel_42", _FRESH_CAROUSEL_SLIDE_URL)

    with (
        patch(
            "getviews_pipeline.corpus_context._is_r2_url",
            return_value=False,  # force the aweme to be treated as stale
        ),
        patch(
            "getviews_pipeline.ensemble.fetch_post_multi_info",
            new=AsyncMock(return_value=[{"aweme_detail": fresh_detail}]),
        ),
        patch(
            "getviews_pipeline.corpus_context._refresh_thumbnail_async",
            new=AsyncMock(return_value=_R2_RESULT_URL),
        ) as mock_repair,
    ):
        from getviews_pipeline.corpus_context import refresh_stale_thumbnails
        awemes = [dict(_CAROUSEL_AWEME)]
        await refresh_stale_thumbnails(awemes)

    # _refresh_thumbnail_async must be called with the slide CDN URL
    mock_repair.assert_called_once_with("carousel_42", _FRESH_CAROUSEL_SLIDE_URL)
    # In-place update applied
    assert awemes[0]["thumbnail_url"] == _R2_RESULT_URL


@pytest.mark.asyncio
async def test_video_cover_url_still_used_for_video_rows() -> None:
    """Existing video cover path is not broken by the carousel fix."""
    fresh_detail = _make_video_detail("video_99", _FRESH_VIDEO_COVER_URL)

    with (
        patch(
            "getviews_pipeline.corpus_context._is_r2_url",
            return_value=False,
        ),
        patch(
            "getviews_pipeline.ensemble.fetch_post_multi_info",
            new=AsyncMock(return_value=[{"aweme_detail": fresh_detail}]),
        ),
        patch(
            "getviews_pipeline.corpus_context._refresh_thumbnail_async",
            new=AsyncMock(return_value="https://pub-abc.r2.dev/thumbnails/video_99.jpg"),
        ) as mock_repair,
    ):
        from getviews_pipeline.corpus_context import refresh_stale_thumbnails
        awemes = [dict(_VIDEO_AWEME)]
        await refresh_stale_thumbnails(awemes)

    mock_repair.assert_called_once_with("video_99", _FRESH_VIDEO_COVER_URL)


@pytest.mark.asyncio
async def test_carousel_skipped_when_no_slide_url_in_multi_info() -> None:
    """If EnsembleData returns no images for the carousel, the row is skipped gracefully."""
    fresh_detail = {
        "aweme_id": "carousel_42",
        # No video, no image_post_info → no fresh URL
    }

    with (
        patch("getviews_pipeline.corpus_context._is_r2_url", return_value=False),
        patch(
            "getviews_pipeline.ensemble.fetch_post_multi_info",
            new=AsyncMock(return_value=[{"aweme_detail": fresh_detail}]),
        ),
        patch(
            "getviews_pipeline.corpus_context._refresh_thumbnail_async",
            new=AsyncMock(),
        ) as mock_repair,
    ):
        from getviews_pipeline.corpus_context import refresh_stale_thumbnails
        await refresh_stale_thumbnails([dict(_CAROUSEL_AWEME)])

    mock_repair.assert_not_called()
