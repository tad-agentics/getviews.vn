"""D1 (2026-06-03) — EnsembleData Douyin client wrapper tests.

Mocks ``_ensemble_get`` so tests don't hit the network. Each test
exercises one endpoint wrapper from ``ensemble_douyin.py`` and asserts:
  • The correct ``/douyin/*`` URL is used.
  • Query params match what ED expects.
  • The response payload is parsed into the same shape callers see for
    TikTok awemes (so D2 ingest can reuse downstream code unchanged).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from getviews_pipeline.config import (
    ENSEMBLEDATA_DOUYIN_HASHTAG_POSTS_URL,
    ENSEMBLEDATA_DOUYIN_KEYWORD_SEARCH_URL,
    ENSEMBLEDATA_DOUYIN_POST_INFO_URL,
    ENSEMBLEDATA_DOUYIN_POST_MULTI_INFO_URL,
    ENSEMBLEDATA_DOUYIN_USER_POSTS_URL,
)
from getviews_pipeline.ensemble_douyin import (
    fetch_douyin_hashtag_posts,
    fetch_douyin_keyword_search,
    fetch_douyin_post_info,
    fetch_douyin_post_multi_info,
    fetch_douyin_user_posts,
)


# ── URL routing ──────────────────────────────────────────────────────


def test_endpoint_urls_route_to_douyin_paths() -> None:
    """Defensive: a regression that flipped a URL constant back to /tt/*
    would silently route Douyin queries to the TikTok search engine."""
    assert ENSEMBLEDATA_DOUYIN_POST_INFO_URL.endswith("/douyin/post/info")
    assert ENSEMBLEDATA_DOUYIN_POST_MULTI_INFO_URL.endswith("/douyin/post/multi-info")
    assert ENSEMBLEDATA_DOUYIN_KEYWORD_SEARCH_URL.endswith("/douyin/keyword/search")
    assert ENSEMBLEDATA_DOUYIN_HASHTAG_POSTS_URL.endswith("/douyin/hashtag/posts")
    assert ENSEMBLEDATA_DOUYIN_USER_POSTS_URL.endswith("/douyin/user/posts")


# ── fetch_douyin_post_info ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_info_extracts_aweme_detail_from_nested_response() -> None:
    """ED commonly returns ``data: {aweme_detail: {...}}`` — wrapper
    must surface the bare aweme dict so analyzers can treat Douyin and
    TikTok awemes uniformly."""
    payload = {"data": {"aweme_detail": {"aweme_id": "9999", "desc": "测试"}}}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ) as mock_get:
        out = await fetch_douyin_post_info("https://www.douyin.com/video/9999")
    assert out == {"aweme_id": "9999", "desc": "测试"}
    # URL routing + query shape.
    args, _ = mock_get.call_args
    assert args[0] == ENSEMBLEDATA_DOUYIN_POST_INFO_URL
    assert args[1] == {"url": "https://www.douyin.com/video/9999"}


@pytest.mark.asyncio
async def test_post_info_extracts_aweme_when_data_is_aweme_directly() -> None:
    """Some ED responses unwrap to ``data: {aweme_id: ..., video: ...}``
    (no ``aweme_detail`` envelope) — wrapper must accept both shapes."""
    payload = {"data": {"aweme_id": "1", "video": {"play_addr_h264": []}}}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ):
        out = await fetch_douyin_post_info("1")
    assert out["aweme_id"] == "1"


@pytest.mark.asyncio
async def test_post_info_extracts_aweme_from_list_data() -> None:
    """Rare but seen: ``data: [{...aweme...}]``."""
    payload = {"data": [{"aweme_id": "1"}]}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ):
        out = await fetch_douyin_post_info("1")
    assert out["aweme_id"] == "1"


@pytest.mark.asyncio
async def test_post_info_raises_on_empty_url() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        await fetch_douyin_post_info("")


@pytest.mark.asyncio
async def test_post_info_raises_on_unparseable_payload() -> None:
    """A payload with no ``aweme_detail`` and no ``aweme_id``-shaped data
    should raise so the caller can skip the video instead of silently
    storing junk."""
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value={"data": {}}),
    ):
        with pytest.raises(ValueError, match="no aweme_detail"):
            await fetch_douyin_post_info("1")


# ── fetch_douyin_post_multi_info ─────────────────────────────────────


@pytest.mark.asyncio
async def test_post_multi_info_joins_ids_with_semicolon() -> None:
    payload = {"data": [{"aweme_id": "1"}, {"aweme_id": "2"}]}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ) as mock_get:
        out = await fetch_douyin_post_multi_info(["1", "2"])
    args, _ = mock_get.call_args
    assert args[1] == {"aweme_ids": "1;2"}
    assert len(out) == 2


@pytest.mark.asyncio
async def test_post_multi_info_skips_call_on_empty_input() -> None:
    """No IDs → don't waste an ED unit (or fail with a 400)."""
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(),
    ) as mock_get:
        out = await fetch_douyin_post_multi_info([])
    assert out == []
    mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_post_multi_info_handles_nested_data_envelope() -> None:
    """Some ED endpoints return ``data: {data: [...]}``; both envelopes
    must surface the inner list."""
    payload = {"data": {"data": [{"aweme_id": "1"}]}}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ):
        out = await fetch_douyin_post_multi_info(["1"])
    assert len(out) == 1
    assert out[0]["aweme_id"] == "1"


# ── fetch_douyin_keyword_search ──────────────────────────────────────


@pytest.mark.asyncio
async def test_keyword_search_strips_hash_prefix() -> None:
    payload: dict[str, Any] = {"data": [{"aweme_id": "1"}]}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ) as mock_get:
        await fetch_douyin_keyword_search("#养生")
    args, _ = mock_get.call_args
    assert args[0] == ENSEMBLEDATA_DOUYIN_KEYWORD_SEARCH_URL
    assert args[1]["keyword"] == "养生"


@pytest.mark.asyncio
async def test_keyword_search_returns_awemes_and_next_cursor() -> None:
    payload = {"data": {"data": [{"aweme_id": "1"}], "nextCursor": 20}}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ):
        awemes, cursor = await fetch_douyin_keyword_search("美妆")
    assert len(awemes) == 1
    assert cursor == 20


@pytest.mark.asyncio
async def test_keyword_search_returns_none_cursor_on_flat_list() -> None:
    """When ED returns just ``data: [awemes]`` (no nextCursor key), the
    wrapper surfaces ``cursor=None`` to signal end-of-pages."""
    payload = {"data": [{"aweme_id": "1"}]}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ):
        _, cursor = await fetch_douyin_keyword_search("美妆")
    assert cursor is None


@pytest.mark.asyncio
async def test_keyword_search_raises_on_empty_keyword() -> None:
    with pytest.raises(ValueError, match="non-empty keyword"):
        await fetch_douyin_keyword_search("")
    with pytest.raises(ValueError, match="non-empty keyword"):
        # A bare "#" with no body should also reject — easy mistake.
        await fetch_douyin_keyword_search("#")


# ── fetch_douyin_hashtag_posts ───────────────────────────────────────


@pytest.mark.asyncio
async def test_hashtag_posts_strips_hash_and_routes_to_douyin() -> None:
    payload = {"data": {"data": [{"aweme_id": "1"}], "nextCursor": 12}}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ) as mock_get:
        awemes, cursor = await fetch_douyin_hashtag_posts("#护肤", cursor=0)
    args, _ = mock_get.call_args
    assert args[0] == ENSEMBLEDATA_DOUYIN_HASHTAG_POSTS_URL
    assert args[1] == {"name": "护肤", "cursor": 0}
    assert len(awemes) == 1
    assert cursor == 12


@pytest.mark.asyncio
async def test_hashtag_posts_raises_on_empty_name() -> None:
    with pytest.raises(ValueError, match="non-empty name"):
        await fetch_douyin_hashtag_posts("")


# ── fetch_douyin_user_posts ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_posts_strips_at_prefix_and_passes_depth() -> None:
    payload = {"data": [{"aweme_id": "1"}, {"aweme_id": "2"}]}
    with patch(
        "getviews_pipeline.ensemble_douyin._ensemble_get",
        new=AsyncMock(return_value=payload),
    ) as mock_get:
        out = await fetch_douyin_user_posts("@silent.unbox", depth=2, start_cursor=20)
    args, _ = mock_get.call_args
    assert args[0] == ENSEMBLEDATA_DOUYIN_USER_POSTS_URL
    assert args[1] == {"user_id": "silent.unbox", "depth": 2, "start_cursor": 20}
    assert len(out) == 2


@pytest.mark.asyncio
async def test_user_posts_raises_on_empty_handle() -> None:
    with pytest.raises(ValueError, match="username or sec_uid"):
        await fetch_douyin_user_posts("")
