"""Phase 1 — Douyin full-video banking + reference serializer tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline import ensemble
from getviews_pipeline.config import DOUYIN_CDN_HEADERS
from getviews_pipeline.douyin_batch_extract import build_douyin_caption_extraction_prefix
from getviews_pipeline.douyin_data import _serialize_video
from getviews_pipeline.douyin_metadata import build_douyin_corpus_row
from getviews_pipeline.douyin_reference import _build_douyin_reference_aweme


def test_build_douyin_caption_extraction_prefix_includes_cn_desc() -> None:
    prefix = build_douyin_caption_extraction_prefix("睡前护肤", ["#养生", "#护肤"])
    assert "Chinese" in prefix or "Douyin" in prefix
    assert "睡前护肤" in prefix
    assert "#养生" in prefix


def test_serialize_video_includes_playback_url() -> None:
    row = {
        "video_id": "dy1",
        "niche_id": 1,
        "views": 1000,
        "likes": 10,
        "saves": 0,
        "playback_url": "https://r2.example/videos/dy1.mp4",
    }
    out = _serialize_video(row)
    assert out["playback_url"] == "https://r2.example/videos/dy1.mp4"


def test_build_douyin_corpus_row_persists_playback_url() -> None:
    aweme = {
        "aweme_id": "dy99",
        "desc": "测试",
        "author": {"unique_id": "creator"},
        "statistics": {"play_count": 200_000, "digg_count": 10_000},
        "video": {"cover": {"url_list": ["https://cdn/cover.jpg"]}},
    }
    analysis = {
        "metadata": {"video_id": "dy99"},
        "analysis": {
            "hook_analysis": {"hook_type": "question", "hook_phrase": "?" },
            "niche_classification": {
                "creator_niche_slug": "beauty_skincare",
                "format_axis": "talking_head",
            },
        },
        "content_type": "video",
    }
    with patch(
        "getviews_pipeline.douyin_metadata.resolve_content_class_from_analysis",
        return_value=(42, "talking_head"),
    ):
        row = build_douyin_corpus_row(
            aweme,
            analysis,
            niche_id=3,
            playback_url="https://r2.example/videos/dy99.mp4",
        )
    assert row is not None
    assert row["playback_url"] == "https://r2.example/videos/dy99.mp4"
    assert row["content_class_id"] == 42
    assert row["content_format"] == "talking_head"


def test_build_douyin_reference_aweme_tags_douyin_corpus() -> None:
    row = {
        "video_id": "dy1",
        "creator_handle": "alice",
        "creator_name": "Alice",
        "views": 50_000,
        "likes": 2_000,
        "comments": 100,
        "shares": 50,
        "engagement_rate": 4.2,
        "title_vi": "Tiêu đề VN",
        "playback_url": "https://r2.example/videos/dy1.mp4",
        "douyin_url": "https://www.douyin.com/video/dy1",
        "thumbnail_url": "https://cdn/t.jpg",
        "analysis_json": {"hook_analysis": {"hook_type": "listicle"}},
        "content_format": "listicle",
        "content_class_id": 7,
    }
    aweme = _build_douyin_reference_aweme(row)
    assert aweme["_from_douyin_corpus"] is True
    assert aweme["_corpus_analysis"] == row["analysis_json"]
    assert aweme["_corpus_video_url"] == "https://r2.example/videos/dy1.mp4"
    assert aweme["douyin_url"] == "https://www.douyin.com/video/dy1"


@pytest.mark.asyncio
async def test_fetch_douyin_reference_awemes_skips_rows_without_analysis() -> None:
    """Hot-path safety: rows lacking analysis_json never enter the ref pool."""
    from getviews_pipeline import douyin_reference

    rows = [
        {  # valid
            "video_id": "dy_ok",
            "playback_url": "https://r2.example/videos/dy_ok.mp4",
            "analysis_json": {"hook_analysis": {"hook_type": "question"}},
            "engagement_rate": 3.0,
        },
        {  # no analysis_json → must be skipped (would trigger live analyze)
            "video_id": "dy_bad",
            "playback_url": "https://r2.example/videos/dy_bad.mp4",
            "analysis_json": {},
            "engagement_rate": 9.0,
        },
        {  # no playback_url → skipped
            "video_id": "dy_noplay",
            "playback_url": None,
            "analysis_json": {"hook_analysis": {}},
        },
    ]

    with patch.object(douyin_reference, "douyin_reference_pool_enabled", return_value=True):
        with patch.object(
            douyin_reference, "map_creator_niche_to_douyin_niche_id", return_value=1
        ):
            with patch.object(
                douyin_reference, "fetch_douyin_peer_rows", return_value=rows
            ):
                out = await douyin_reference.fetch_douyin_reference_awemes(
                    MagicMock(),
                    creator_niche_slug="beauty",
                    hook_type="question",
                )

    ids = [a["aweme_id"] for a in out]
    assert ids == ["dy_ok"]
    assert all(a.get("_corpus_analysis") for a in out)


@pytest.mark.asyncio
async def test_fetch_douyin_reference_awemes_disabled_returns_empty() -> None:
    from getviews_pipeline import douyin_reference

    with patch.object(douyin_reference, "douyin_reference_pool_enabled", return_value=False):
        out = await douyin_reference.fetch_douyin_reference_awemes(
            MagicMock(),
            creator_niche_slug="beauty",
            hook_type="question",
        )
    assert out == []


def test_download_video_accepts_custom_max_bytes_and_headers() -> None:
    """Douyin path passes higher cap + Douyin Referer without changing TikTok default."""
    assert DOUYIN_CDN_HEADERS.get("Referer") == "https://www.douyin.com/"

    import inspect

    sig = inspect.signature(ensemble.download_video)
    assert "max_bytes" in sig.parameters
    assert "headers" in sig.parameters


@patch("getviews_pipeline.r2.r2_configured", return_value=True)
@patch("getviews_pipeline.r2.upload_video", return_value="https://r2.example/videos/dy1.mp4")
@patch("getviews_pipeline.r2.remux_video_faststart", return_value=True)
def test_bank_local_video_to_r2_remuxes_and_uploads(
    mock_remux: MagicMock,
    _mock_upload: MagicMock,
    _mock_cfg: MagicMock,
    tmp_path: Path,
) -> None:
    from getviews_pipeline.r2 import bank_local_video_to_r2

    src = tmp_path / "raw.mp4"
    src.write_bytes(b"fake-mp4-bytes" * 100)

    url = bank_local_video_to_r2("dy1", src, max_bytes=10 * 1024 * 1024)

    assert url == "https://r2.example/videos/dy1.mp4"
    mock_remux.assert_called_once()
