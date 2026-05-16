"""HI-15 — dual video Part + VideoMetadata for hook-window FPS (video-only)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from google.genai import types

from getviews_pipeline import gemini
from getviews_pipeline.prompts import build_video_extraction_user_turn_vi


def test_build_video_extraction_user_turn_dual_mentions_hook_window() -> None:
    s = build_video_extraction_user_turn_vi(
        dual_hook_window=True,
        hook_window_seconds=3.0,
        base_fps_display=1.0,
    )
    assert "Hai đoạn video" in s
    assert "3 giây" in s
    assert "FPS cao" in s
    assert "~1 FPS" in s or "1 FPS" in s


def test_build_video_extraction_user_turn_single_matches_legacy_constant() -> None:
    from getviews_pipeline.prompts import VIDEO_EXTRACTION_USER_TURN_VI

    s = build_video_extraction_user_turn_vi(
        dual_hook_window=False,
        hook_window_seconds=3.0,
        base_fps_display=2.0,
    )
    assert s == VIDEO_EXTRACTION_USER_TURN_VI


@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_DUAL_PART", True)
@patch("getviews_pipeline.gemini.GEMINI_VIDEO_BASE_FPS", 1.0)
@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_FPS", 4.0)
@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_END_SEC", 3.0)
def test_hi15_dual_inline_parts_metadata() -> None:
    parts = gemini._build_video_extraction_content_parts(
        video_bytes=b"x",
        mime_type="video/mp4",
        file_resource=None,
    )
    assert len(parts) == 2
    assert parts[0].inline_data is not None
    assert parts[0].video_metadata == types.VideoMetadata(fps=1.0)
    assert parts[1].video_metadata == types.VideoMetadata(
        fps=4.0,
        start_offset="0s",
        end_offset="3s",
    )


@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_DUAL_PART", True)
@patch("getviews_pipeline.gemini.GEMINI_VIDEO_BASE_FPS", 1.0)
@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_FPS", 2.0)
@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_END_SEC", 3.0)
def test_hi15_hook_fps_clamped_to_minimum_three() -> None:
    parts = gemini._build_video_extraction_content_parts(
        video_bytes=b"x",
        mime_type="video/mp4",
        file_resource=None,
    )
    assert parts[1].video_metadata is not None
    assert parts[1].video_metadata.fps == 3.0


@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_DUAL_PART", False)
def test_hi15_disabled_single_inline_part() -> None:
    parts = gemini._build_video_extraction_content_parts(
        video_bytes=b"x",
        mime_type="video/mp4",
        file_resource=None,
    )
    assert len(parts) == 1
    assert parts[0].inline_data is not None
    assert parts[0].video_metadata is None


@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_DUAL_PART", False)
def test_hi15_disabled_files_api_passes_resource_through() -> None:
    sentinel = object()
    parts = gemini._build_video_extraction_content_parts(
        video_bytes=None,
        mime_type="video/mp4",
        file_resource=sentinel,
    )
    assert parts == [sentinel]


class _FakeFile:
    uri = "https://generativelanguage.googleapis.com/v1beta/files/abc"
    mime_type = "video/mp4"


@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_DUAL_PART", True)
@patch("getviews_pipeline.gemini.GEMINI_VIDEO_BASE_FPS", 1.0)
@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_FPS", 4.0)
@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_END_SEC", 2.5)
def test_hi15_dual_file_parts_use_file_uri() -> None:
    parts = gemini._build_video_extraction_content_parts(
        video_bytes=None,
        mime_type="video/mp4",
        file_resource=_FakeFile(),
    )
    assert len(parts) == 2
    assert parts[0].file_data is not None
    assert parts[0].file_data.file_uri == _FakeFile.uri
    assert parts[1].video_metadata is not None
    assert parts[1].video_metadata.end_offset == "2.5s"


def test_hi15_build_parts_rejects_both_bytes_and_file() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        gemini._build_video_extraction_content_parts(
            video_bytes=b"a",
            mime_type="video/mp4",
            file_resource=_FakeFile(),
        )


@patch("getviews_pipeline.gemini.GEMINI_HOOK_WINDOW_DUAL_PART", True)
def test_hi15_dual_file_without_uri_raises() -> None:
    class NoUri:
        uri = None
        mime_type = "video/mp4"

    with pytest.raises(RuntimeError, match="missing uri"):
        gemini._build_video_extraction_content_parts(
            video_bytes=None,
            mime_type="video/mp4",
            file_resource=NoUri(),
        )


def test_carousel_image_parts_default_no_video_metadata() -> None:
    """Guardrail aligned with analyze_carousel — Part.video_metadata is video-only (HI-17)."""
    p = types.Part.from_bytes(data=b"\xff\xd8\xff", mime_type="image/jpeg")
    assert p.video_metadata is None
