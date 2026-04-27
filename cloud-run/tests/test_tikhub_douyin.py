"""``tikhub_douyin`` adapter — request shape + envelope unwrap + caches.

These tests run without a TikHub key — every HTTP call is mocked at
``httpx.AsyncClient``. They pin:

  • The URL + HTTP method we send to TikHub for each public function.
  • The request-body / query-param shape (including the ``period`` /
    ``sorting`` translation to TikHub's ``publish_time`` / ``sort_type``).
  • The envelope unwrap (``{"code": 200, "data": …}`` → returned data).
  • Resolution caching (handle → sec_user_id, name → challenge_id).
  • The two-step flow (resolve → fetch posts) for hashtag + user calls.
  • Budget guard fires before the network call.
  • Error mapping (401, 429, envelope ``code != 200``).

Once a TIKHUB_API_KEY is provisioned, capture real responses for the
five endpoints into ``tests/fixtures/tikhub_douyin/*.json`` and
add a parametrised "real shape" test that loads each fixture and
asserts ``iter_awemes_from_search_payload`` produces the right
canonical aweme list. That validates production with zero call cost.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from getviews_pipeline import config as gv_config
from getviews_pipeline import ensemble as gv_ensemble
from getviews_pipeline import tikhub_douyin


def _envelope(data: Any, code: int = 200) -> dict[str, Any]:
    """Build a TikHub-shaped response envelope."""
    return {"code": code, "router": "/test", "params": {}, "data": data}


def _mock_response(payload: dict[str, Any], status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json = MagicMock(return_value=payload)
    resp.text = ""
    return resp


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with a key set, caches clean, budget reset."""
    monkeypatch.setattr(tikhub_douyin, "TIKHUB_API_KEY", "test-key")
    monkeypatch.setattr(gv_config, "TIKHUB_DOUYIN_DAILY_REQUEST_MAX", 0)
    tikhub_douyin.reset_resolution_caches_for_tests()
    gv_ensemble.reset_tikhub_douyin_budget_for_tests()


def _patch_async_client(method_responses: dict[str, MagicMock]) -> Any:
    """Patch ``httpx.AsyncClient`` so ``client.<method>(...)`` returns
    a queued response keyed by ``method`` (one per call). Pop-based so
    tests can queue multiple responses for multi-step flows."""
    queues = {k: [v] if not isinstance(v, list) else list(v) for k, v in method_responses.items()}

    def _make_async_call(method_name: str) -> AsyncMock:
        async def _call(*_args: Any, **_kwargs: Any) -> MagicMock:
            q = queues.get(method_name) or []
            if not q:
                raise AssertionError(f"unexpected {method_name} call — no response queued")
            return q.pop(0)
        return AsyncMock(side_effect=_call)

    fake_client = MagicMock()
    fake_client.get = _make_async_call("GET")
    fake_client.post = _make_async_call("POST")
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    return patch.object(tikhub_douyin.httpx, "AsyncClient", return_value=fake_client), fake_client


# ── Public API: fetch_douyin_post_info ─────────────────────────────────


@pytest.mark.asyncio
async def test_post_info_extracts_aweme_id_from_url() -> None:
    aweme = {"aweme_id": "7350123", "desc": "x"}
    patcher, client = _patch_async_client({"GET": _mock_response(_envelope({"aweme_detail": aweme}))})
    with patcher:
        result = await tikhub_douyin.fetch_douyin_post_info(
            "https://www.douyin.com/video/7350123"
        )
    assert result == aweme
    # Path + query params we sent.
    call = client.get.call_args
    assert call.args[0].endswith("/api/v1/douyin/web/fetch_one_video_v2")
    assert call.kwargs["params"] == {"aweme_id": "7350123"}


@pytest.mark.asyncio
async def test_post_info_passes_through_bare_aweme_id() -> None:
    aweme = {"aweme_id": "7350123", "desc": "x"}
    patcher, client = _patch_async_client({"GET": _mock_response(_envelope({"aweme_detail": aweme}))})
    with patcher:
        result = await tikhub_douyin.fetch_douyin_post_info("7350123")
    assert result == aweme
    assert client.get.call_args.kwargs["params"] == {"aweme_id": "7350123"}


@pytest.mark.asyncio
async def test_post_info_raises_on_empty_input() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        await tikhub_douyin.fetch_douyin_post_info("   ")


@pytest.mark.asyncio
async def test_post_info_unwraps_data_when_aweme_lives_at_root() -> None:
    aweme = {"aweme_id": "7350123", "video": {"play_addr": {}}, "desc": "x"}
    patcher, _ = _patch_async_client({"GET": _mock_response(_envelope(aweme))})
    with patcher:
        result = await tikhub_douyin.fetch_douyin_post_info("7350123")
    assert result == aweme


# ── Public API: fetch_douyin_post_multi_info ───────────────────────────


@pytest.mark.asyncio
async def test_multi_info_skips_call_on_empty_input() -> None:
    patcher, client = _patch_async_client({})  # No responses queued — must not be called.
    with patcher:
        result = await tikhub_douyin.fetch_douyin_post_multi_info([])
    assert result == []
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_multi_info_sends_aweme_ids_as_list_of_dicts() -> None:
    awemes = [{"aweme_id": "1"}, {"aweme_id": "2"}]
    patcher, client = _patch_async_client(
        {"POST": _mock_response(_envelope({"aweme_details": awemes}))},
    )
    with patcher:
        result = await tikhub_douyin.fetch_douyin_post_multi_info(["1", "2", "  "])
    assert result == awemes
    assert client.post.call_args.kwargs["json"] == [{"aweme_id": "1"}, {"aweme_id": "2"}]


# ── Public API: fetch_douyin_keyword_search ────────────────────────────


@pytest.mark.asyncio
async def test_keyword_search_translates_period_and_sorting() -> None:
    patcher, client = _patch_async_client(
        {"POST": _mock_response(_envelope({"data": [{"aweme_id": "1"}], "cursor": 20}))},
    )
    with patcher:
        awemes, next_cursor = await tikhub_douyin.fetch_douyin_keyword_search(
            "猫咪", period=7, sorting=1, cursor=0,
        )
    assert len(awemes) == 1
    assert next_cursor == 20
    body = client.post.call_args.kwargs["json"]
    assert body["keyword"] == "猫咪"
    assert body["sort_type"] == "1"  # sorting=1 → "1"
    assert body["publish_time"] == "7"  # period=7 → "7"
    assert body["cursor"] == 0


@pytest.mark.asyncio
async def test_keyword_search_strips_hash_prefix() -> None:
    patcher, client = _patch_async_client(
        {"POST": _mock_response(_envelope({"data": []}))},
    )
    with patcher:
        await tikhub_douyin.fetch_douyin_keyword_search("#猫咪")
    assert client.post.call_args.kwargs["json"]["keyword"] == "猫咪"


@pytest.mark.asyncio
async def test_keyword_search_raises_on_empty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        await tikhub_douyin.fetch_douyin_keyword_search("  ")


# ── Public API: fetch_douyin_hashtag_posts (two-step) ──────────────────


@pytest.mark.asyncio
async def test_hashtag_posts_resolves_challenge_id_then_fetches() -> None:
    resolve_resp = _mock_response(
        _envelope({"challenge_list": [{"cha_name": "养生", "cid": "ch-123"}]}),
    )
    posts_resp = _mock_response(_envelope({"data": [{"aweme_id": "1"}]}))
    patcher, client = _patch_async_client({"POST": [resolve_resp, posts_resp]})
    with patcher:
        awemes, _ = await tikhub_douyin.fetch_douyin_hashtag_posts("#养生")
    assert len(awemes) == 1
    # First POST → resolve. Second POST → fetch_challenge_posts with cid.
    assert client.post.call_count == 2
    second_call = client.post.call_args_list[1]
    assert second_call.kwargs["json"]["challenge_id"] == "ch-123"


@pytest.mark.asyncio
async def test_hashtag_posts_caches_challenge_id_across_calls() -> None:
    resolve_resp = _mock_response(
        _envelope({"challenge_list": [{"cha_name": "养生", "cid": "ch-123"}]}),
    )
    posts_resp_1 = _mock_response(_envelope({"data": [{"aweme_id": "1"}]}))
    posts_resp_2 = _mock_response(_envelope({"data": [{"aweme_id": "2"}]}))
    patcher, client = _patch_async_client(
        {"POST": [resolve_resp, posts_resp_1, posts_resp_2]},
    )
    with patcher:
        await tikhub_douyin.fetch_douyin_hashtag_posts("养生")
        await tikhub_douyin.fetch_douyin_hashtag_posts("养生")
    # Only ONE resolve call across two ingest passes.
    assert client.post.call_count == 3
    assert client.post.call_args_list[0].args[0].endswith(
        "/api/v1/douyin/search/fetch_challenge_search_v2"
    )


@pytest.mark.asyncio
async def test_hashtag_posts_returns_empty_when_resolve_fails() -> None:
    # ``challenge_list`` empty → no challenge_id → return empty page
    # (orchestrator continues to the next hashtag).
    patcher, _ = _patch_async_client(
        {"POST": _mock_response(_envelope({"challenge_list": []}))},
    )
    with patcher:
        awemes, cur = await tikhub_douyin.fetch_douyin_hashtag_posts("doesnotexist")
    assert awemes == []
    assert cur is None


# ── Public API: fetch_douyin_user_posts (two-step) ─────────────────────


@pytest.mark.asyncio
async def test_user_posts_resolves_handle_to_sec_uid() -> None:
    resolve_resp = _mock_response(
        _envelope({"user_info": {"sec_uid": "MS4wLjABAAAA-test-sec-uid-1234567890"}}),
    )
    posts_resp = _mock_response(_envelope({"aweme_list": [{"aweme_id": "1"}]}))
    patcher, client = _patch_async_client(
        {"POST": [resolve_resp], "GET": [posts_resp]},
    )
    with patcher:
        awemes = await tikhub_douyin.fetch_douyin_user_posts("@somebody")
    assert len(awemes) == 1
    # GET to fetch_user_post_videos with the resolved sec_uid.
    get_call = client.get.call_args
    assert get_call.args[0].endswith("/api/v1/douyin/web/fetch_user_post_videos")
    assert get_call.kwargs["params"]["sec_user_id"].startswith("MS4")


@pytest.mark.asyncio
async def test_user_posts_passes_sec_uid_through_without_resolve() -> None:
    # Already-resolved sec_uid skips fetch_query_user.
    posts_resp = _mock_response(_envelope({"aweme_list": [{"aweme_id": "1"}]}))
    patcher, client = _patch_async_client({"GET": [posts_resp]})
    with patcher:
        awemes = await tikhub_douyin.fetch_douyin_user_posts("MS4wLjABAAAA-already-resolved-1234")
    assert len(awemes) == 1
    client.post.assert_not_called()


# ── Envelope error mapping ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_request_raises_on_401() -> None:
    patcher, _ = _patch_async_client({"GET": _mock_response({}, status=401)})
    with patcher:
        with pytest.raises(ValueError, match="401 unauthorized"):
            await tikhub_douyin.fetch_douyin_post_info("7350123")


@pytest.mark.asyncio
async def test_request_raises_on_429() -> None:
    patcher, _ = _patch_async_client({"GET": _mock_response({}, status=429)})
    with patcher:
        with pytest.raises(ValueError, match="429 rate-limited"):
            await tikhub_douyin.fetch_douyin_post_info("7350123")


@pytest.mark.asyncio
async def test_request_raises_on_envelope_error_code() -> None:
    patcher, _ = _patch_async_client(
        {"GET": _mock_response(_envelope({}, code=403))},
    )
    with patcher:
        with pytest.raises(ValueError, match="envelope error code=403"):
            await tikhub_douyin.fetch_douyin_post_info("7350123")


@pytest.mark.asyncio
async def test_request_raises_when_api_key_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tikhub_douyin, "TIKHUB_API_KEY", None)
    with pytest.raises(ValueError, match="TIKHUB_API_KEY not configured"):
        await tikhub_douyin.fetch_douyin_post_info("7350123")


# ── Budget guard ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_budget_guard_fires_before_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gv_config, "TIKHUB_DOUYIN_DAILY_REQUEST_MAX", 1)
    # First call consumes the budget; second must raise without ever
    # touching httpx.AsyncClient.
    aweme = {"aweme_id": "1", "desc": ""}
    patcher, client = _patch_async_client({"GET": _mock_response(_envelope({"aweme_detail": aweme}))})
    with patcher:
        await tikhub_douyin.fetch_douyin_post_info("1")
        with pytest.raises(gv_ensemble.TikHubDailyBudgetExceeded):
            await tikhub_douyin.fetch_douyin_post_info("2")
    # Only one HTTP call landed.
    assert client.get.call_count == 1


# ── Cursor extraction ──────────────────────────────────────────────────


def test_next_cursor_picks_first_non_zero_key() -> None:
    assert tikhub_douyin._next_cursor({"max_cursor": 100}) == 100
    assert tikhub_douyin._next_cursor({"cursor": 0, "next_cursor": 50}) == 50
    assert tikhub_douyin._next_cursor({"cursor": "0"}) is None
    assert tikhub_douyin._next_cursor({"nothing": 1}) is None
    assert tikhub_douyin._next_cursor({}) is None


def test_extract_aweme_id_handles_url_or_bare() -> None:
    assert tikhub_douyin._extract_aweme_id("7350123") == "7350123"
    assert (
        tikhub_douyin._extract_aweme_id("https://www.douyin.com/video/7350123")
        == "7350123"
    )
    assert (
        tikhub_douyin._extract_aweme_id("https://www.douyin.com/video/7350123/")
        == "7350123"
    )
    assert tikhub_douyin._extract_aweme_id("") == ""


def test_looks_like_sec_uid() -> None:
    assert tikhub_douyin._looks_like_sec_uid("MS4wLjABAAAA-typical-sec-uid-payload-12345")
    assert not tikhub_douyin._looks_like_sec_uid("elon_musk_yt")
    assert not tikhub_douyin._looks_like_sec_uid("@elon_musk_yt")
    assert not tikhub_douyin._looks_like_sec_uid("MS4short")
