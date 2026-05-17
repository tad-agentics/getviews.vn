"""Phase 5.5 — unit tests for channel snapshot caching."""
from unittest.mock import patch

from getviews_pipeline.services.channel import (
    _channel_cache,
    _normalize_handle,
    clear_channel_cache,
    fetch_channel_context_sync,
)

_FAKE_CONTEXT = {
    "available": True,
    "top_videos": [],
    "bottom_videos": [],
    "best_performing_format": None,
    "sample_size": 5,
    "median_views": 10000,
    "per_format_views": None,
}


def _mock_fetch(handle: str, video_id: str) -> dict:
    return {**_FAKE_CONTEXT, "_handle": handle}


def setup_function() -> None:
    clear_channel_cache()


def teardown_function() -> None:
    clear_channel_cache()


def test_normalize_handle():
    assert _normalize_handle("@CreaTor") == "creator"
    assert _normalize_handle("creator") == "creator"
    assert _normalize_handle("  @ABC  ") == "abc"


def test_cache_hit_on_second_call():
    call_count = 0

    def counting_fetch(handle: str, video_id: str) -> dict:
        nonlocal call_count
        call_count += 1
        return _FAKE_CONTEXT

    with patch(
        "getviews_pipeline.services.channel._fetch_channel_context_sync",
        side_effect=counting_fetch,
    ):
        fetch_channel_context_sync("@creator", "vid1")
        fetch_channel_context_sync("@creator", "vid2")  # same handle, different video

    assert call_count == 1, "second call should hit cache, not re-fetch"


def test_different_handles_fetch_separately():
    call_count = 0

    def counting_fetch(handle: str, video_id: str) -> dict:
        nonlocal call_count
        call_count += 1
        return _FAKE_CONTEXT

    with patch(
        "getviews_pipeline.services.channel._fetch_channel_context_sync",
        side_effect=counting_fetch,
    ):
        fetch_channel_context_sync("@creator_a", "vid1")
        fetch_channel_context_sync("@creator_b", "vid1")

    assert call_count == 2, "different handles must fetch independently"


def test_unavailable_context_not_cached():
    unavailable = {"available": False, "reason": "too few videos"}
    call_count = 0

    def counting_fetch(handle: str, video_id: str) -> dict:
        nonlocal call_count
        call_count += 1
        return unavailable

    with patch(
        "getviews_pipeline.services.channel._fetch_channel_context_sync",
        side_effect=counting_fetch,
    ):
        fetch_channel_context_sync("@nocreator", "vid1")
        fetch_channel_context_sync("@nocreator", "vid2")

    assert call_count == 2, "unavailable responses must NOT be cached"


def test_force_refresh_bypasses_cache():
    call_count = 0

    def counting_fetch(handle: str, video_id: str) -> dict:
        nonlocal call_count
        call_count += 1
        return _FAKE_CONTEXT

    with patch(
        "getviews_pipeline.services.channel._fetch_channel_context_sync",
        side_effect=counting_fetch,
    ):
        fetch_channel_context_sync("@creator", "vid1")
        fetch_channel_context_sync("@creator", "vid2", force_refresh=True)

    assert call_count == 2, "force_refresh=True must bypass cache"


def test_clear_cache_specific_handle():
    with patch(
        "getviews_pipeline.services.channel._fetch_channel_context_sync",
        return_value=_FAKE_CONTEXT,
    ):
        fetch_channel_context_sync("@creator_x", "vid1")

    assert "creator_x" in _channel_cache
    clear_channel_cache("@creator_x")
    assert "creator_x" not in _channel_cache
