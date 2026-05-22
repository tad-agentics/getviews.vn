"""HI-17 — carousel analysis must not invoke HI-14 GCP STT (video paths only)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_FAKE_AWEME = {
    "aweme_id": "vid_hi17",
    "image_post_info": {
        "images": [
            {"display_image": {"url_list": ["https://p16-sign.tiktokcdn.com/slide0.jpg"]}},
        ],
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
_FAKE_METADATA.model_dump.return_value = {"aweme_id": "vid_hi17"}
_FAKE_METADATA.model_copy.return_value = _FAKE_METADATA


def _make_downloaded() -> list[tuple[int, Path, str]]:
    p = MagicMock(spec=Path)
    p.read_bytes.return_value = b"\xff\xd8\xff"
    p.exists.return_value = True
    return [(0, p, "image/jpeg")]


@pytest.mark.asyncio
async def test_analyze_carousel_path_never_calls_hi14_stt_prep() -> None:
    """Regression: ``_analyze_carousel`` uses image-only Gemini — no ASR supplement."""
    fake_analysis_obj = MagicMock()
    fake_result = {"metadata": {}, "analysis": {}, "content_type": "carousel"}

    def _forbidden_stt(*_a: object, **_k: object) -> tuple[str, float | None]:
        raise AssertionError("HI-14 STT must not run for carousel content (HI-17)")

    with (
        patch(
            "getviews_pipeline.analysis_core.ensemble.extract_image_url_lists",
            return_value=[["https://slide0.tiktokcdn.com"]],
        ),
        patch(
            "getviews_pipeline.analysis_core.ensemble.download_images",
            new=AsyncMock(return_value=(_make_downloaded(), [])),
        ),
        patch(
            "getviews_pipeline.analysis_core.run_sync",
            new=AsyncMock(return_value=fake_analysis_obj),
        ),
        patch(
            "getviews_pipeline.analysis_core._finish_analysis",
            new=AsyncMock(return_value=dict(fake_result)),
        ),
        patch(
            "getviews_pipeline.analysis_core.sync_prepare_vietnamese_asr_supplement",
            side_effect=_forbidden_stt,
        ) as mock_stt,
        patch("getviews_pipeline.r2.r2_configured", return_value=False),
    ):
        from getviews_pipeline.analysis_core import _analyze_carousel

        out = await _analyze_carousel(
            aweme=_FAKE_AWEME,
            metadata=_FAKE_METADATA,
            include_diagnosis=False,
        )

    assert out.get("content_type") == "carousel"
    mock_stt.assert_not_called()
