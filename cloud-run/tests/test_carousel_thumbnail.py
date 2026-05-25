"""Tests for carousel slide[0] → R2 thumbnail upload in analysis_core._analyze_carousel.

Verifies that:
  - After a successful Gemini analysis of a carousel, slide[0] is uploaded to R2
    via ``upload_thumbnail_bytes`` and the URL is returned in the result dict under
    ``r2_thumbnail_url``.
  - If R2 is not configured, the upload is skipped and no error is raised.
  - If the upload itself raises, the analysis result is still returned (non-fatal).
  - If there are no downloaded slides (all failed), no upload is attempted.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_R2_URL = "https://pub-abc.r2.dev/thumbnails/vid42.webp"

_FAKE_AWEME = {
    "aweme_id": "vid42",
    "image_post_info": {
        "images": [
            {"display_image": {"url_list": ["https://p16-sign.tiktokcdn.com/slide0.jpg"]}}
        ]
    },
}

_FAKE_METADATA = MagicMock()
_FAKE_METADATA.content_type = "carousel"
_FAKE_METADATA.slide_count = 1
# ``_analyze_carousel`` feeds ``metadata.description`` / ``metadata.hashtags``
# into ``build_tiktok_caption_extraction_prefix`` (prompts.py), which joins
# them with ``"\n".join`` — they must be real str/list values, not bare
# MagicMock attributes.
_FAKE_METADATA.description = "caption tiktok mẫu"
_FAKE_METADATA.hashtags = ["fyp", "review"]
_FAKE_METADATA.model_dump.return_value = {"aweme_id": "vid42"}
_FAKE_METADATA.model_copy.return_value = _FAKE_METADATA


def _fake_slide_bytes() -> list[tuple[bytes, str]]:
    return [(b"\xff\xd8\xff fake jpeg bytes", "image/jpeg")]


def _make_downloaded(slide_bytes_list: list[tuple[bytes, str]]) -> list[tuple[int, Path, str]]:
    """Build a ``downloaded`` list mirroring ensemble.download_images output."""
    results = []
    for i, (data, mime) in enumerate(slide_bytes_list):
        p = MagicMock(spec=Path)
        p.read_bytes.return_value = data
        p.exists.return_value = True
        results.append((i, p, mime))
    return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_carousel_uploads_slide0_to_r2_when_configured() -> None:
    """Successful carousel analysis → slide[0] bytes uploaded to R2."""
    slide_bytes = _fake_slide_bytes()
    downloaded = _make_downloaded(slide_bytes)

    fake_analysis_obj = MagicMock()
    fake_analysis_result = {"metadata": {}, "analysis": {}, "content_type": "carousel"}

    with (
        patch(
            "getviews_pipeline.analysis_core.ensemble.extract_image_url_lists",
            return_value=[["https://slide0.tiktokcdn.com"]],
        ),
        patch(
            "getviews_pipeline.analysis_core.ensemble.download_images",
            new=AsyncMock(return_value=(downloaded, [])),
        ),
        patch(
            "getviews_pipeline.analysis_core.run_sync",
            new=AsyncMock(return_value=fake_analysis_obj),
        ),
        patch(
            "getviews_pipeline.analysis_core._finish_analysis",
            new=AsyncMock(return_value=dict(fake_analysis_result)),
        ),
        patch("getviews_pipeline.r2.r2_configured", return_value=True),
        patch(
            "getviews_pipeline.r2.upload_thumbnail_bytes",
            return_value=_FAKE_R2_URL,
        ) as mock_upload,
    ):
        from getviews_pipeline.analysis_core import _analyze_carousel

        result = await _analyze_carousel(
            aweme=_FAKE_AWEME,
            metadata=_FAKE_METADATA,
            include_diagnosis=False,
        )

    assert result.get("r2_thumbnail_url") == _FAKE_R2_URL
    mock_upload.assert_called_once()
    call_args = mock_upload.call_args
    assert call_args.args[0] == "vid42"          # video_id
    assert call_args.args[1] == b"\xff\xd8\xff fake jpeg bytes"  # bytes
    assert call_args.args[2] == "image/jpeg"     # mime type


@pytest.mark.asyncio
async def test_carousel_skips_upload_when_r2_not_configured() -> None:
    """When R2 is not configured, no upload attempt is made and no error raised."""
    slide_bytes = _fake_slide_bytes()
    downloaded = _make_downloaded(slide_bytes)

    with (
        patch(
            "getviews_pipeline.analysis_core.ensemble.extract_image_url_lists",
            return_value=[["https://slide0.tiktokcdn.com"]],
        ),
        patch(
            "getviews_pipeline.analysis_core.ensemble.download_images",
            new=AsyncMock(return_value=(downloaded, [])),
        ),
        patch(
            "getviews_pipeline.analysis_core.run_sync",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "getviews_pipeline.analysis_core._finish_analysis",
            new=AsyncMock(return_value={"metadata": {}, "analysis": {}}),
        ),
        patch("getviews_pipeline.r2.r2_configured", return_value=False),
        patch("getviews_pipeline.r2.upload_thumbnail_bytes") as mock_upload,
    ):
        from getviews_pipeline.analysis_core import _analyze_carousel

        result = await _analyze_carousel(
            aweme=_FAKE_AWEME,
            metadata=_FAKE_METADATA,
            include_diagnosis=False,
        )

    assert "r2_thumbnail_url" not in result
    mock_upload.assert_not_called()


@pytest.mark.asyncio
async def test_carousel_returns_result_even_if_r2_upload_raises() -> None:
    """An exception during thumbnail upload must not propagate — analysis result returned."""
    slide_bytes = _fake_slide_bytes()
    downloaded = _make_downloaded(slide_bytes)
    base_result = {"metadata": {}, "analysis": {}}

    with (
        patch(
            "getviews_pipeline.analysis_core.ensemble.extract_image_url_lists",
            return_value=[["https://slide0.tiktokcdn.com"]],
        ),
        patch(
            "getviews_pipeline.analysis_core.ensemble.download_images",
            new=AsyncMock(return_value=(downloaded, [])),
        ),
        patch(
            "getviews_pipeline.analysis_core.run_sync",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "getviews_pipeline.analysis_core._finish_analysis",
            new=AsyncMock(return_value=dict(base_result)),
        ),
        patch("getviews_pipeline.r2.r2_configured", return_value=True),
        patch(
            "getviews_pipeline.r2.upload_thumbnail_bytes",
            side_effect=RuntimeError("boto3 error"),
        ),
    ):
        from getviews_pipeline.analysis_core import _analyze_carousel

        result = await _analyze_carousel(
            aweme=_FAKE_AWEME,
            metadata=_FAKE_METADATA,
            include_diagnosis=False,
        )

    # Analysis result intact; r2_thumbnail_url absent (upload failed gracefully)
    assert result.get("metadata") == {}
    assert "r2_thumbnail_url" not in result
