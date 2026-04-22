"""Tests for the daily ``video_corpus`` freshness refresh.

Covers the three pieces that have to stay correct:

  1. ``_select_refresh_candidates`` — NULL bucket first, then stale-by-age,
     both filtered by views threshold and capped at ``limit``.
  2. ``_extract_fresh_metrics`` — pulls play_count/digg_count/etc. out of
     ED's response shape; returns None on missing/zero stats.
  3. ``run_corpus_refresh`` — end-to-end with mocked client + ensemble.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from getviews_pipeline.corpus_refresh import (
    REFRESH_BATCH_LIMIT,
    _engagement_rate,
    _extract_fresh_metrics,
    _save_rate,
    _select_refresh_candidates,
    run_corpus_refresh,
)

# ── _extract_fresh_metrics ────────────────────────────────────────────


def test_extract_metrics_happy_path() -> None:
    post = {
        "aweme_detail": {
            "aweme_id": "100",
            "statistics": {
                "play_count": 50_000,
                "digg_count": 4_000,
                "comment_count": 200,
                "share_count": 100,
                "collect_count": 600,
            },
        }
    }
    metrics = _extract_fresh_metrics(post)
    assert metrics == {
        "views": 50_000,
        "likes": 4_000,
        "comments": 200,
        "shares": 100,
        "saves": 600,
    }


def test_extract_metrics_camelcase_keys_also_work() -> None:
    """ED occasionally returns camelCase. We accept both."""
    post = {
        "aweme_detail": {
            "statistics": {
                "playCount": 1000,
                "diggCount": 50,
                "commentCount": 5,
                "shareCount": 1,
                "collectCount": 10,
            }
        }
    }
    metrics = _extract_fresh_metrics(post)
    assert metrics is not None
    assert metrics["views"] == 1000
    assert metrics["likes"] == 50


def test_extract_metrics_zero_play_count_returns_none() -> None:
    """Zero play_count = ED returned a deleted/private shell. Skip."""
    post = {"aweme_detail": {"statistics": {"play_count": 0, "digg_count": 1}}}
    assert _extract_fresh_metrics(post) is None


def test_extract_metrics_missing_statistics_returns_none() -> None:
    post = {"aweme_detail": {}}
    assert _extract_fresh_metrics(post) is None


def test_extract_metrics_handles_top_level_response_shape() -> None:
    """Some ED responses don't nest under aweme_detail."""
    post = {"aweme_id": "200", "statistics": {"play_count": 100}}
    metrics = _extract_fresh_metrics(post)
    assert metrics is not None
    assert metrics["views"] == 100


# ── _engagement_rate / _save_rate ─────────────────────────────────────


def test_engagement_rate_matches_corpus_ingest_formula() -> None:
    # (likes + comments + shares) / views, 6 decimal places
    assert _engagement_rate(views=1000, likes=40, comments=10, shares=5) == 0.055


def test_engagement_rate_zero_views_is_safe() -> None:
    assert _engagement_rate(views=0, likes=10, comments=5, shares=2) == 0.0


def test_save_rate() -> None:
    assert _save_rate(views=1000, saves=30) == 0.03
    assert _save_rate(views=0, saves=10) == 0.0


# ── _select_refresh_candidates ────────────────────────────────────────


def _build_query_chain(rows: list[dict[str, Any]]) -> MagicMock:
    """Build a chain mock that returns rows from .execute()."""
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=rows)
    return chain


def _build_select_client(
    null_rows: list[dict[str, Any]],
    stale_rows: list[dict[str, Any]],
) -> MagicMock:
    """Mock client where the NULL-bucket .is_(...) chain returns null_rows
    and the stale-bucket .lt(...) chain returns stale_rows."""
    client = MagicMock()

    null_chain = _build_query_chain(null_rows)
    null_select = MagicMock()
    null_chain_attr = null_select.is_.return_value.gte.return_value.order.return_value.limit
    null_chain_attr.return_value = null_chain

    stale_chain = _build_query_chain(stale_rows)
    stale_select = MagicMock()
    stale_chain_attr = stale_select.lt.return_value.gte.return_value.order.return_value.limit
    stale_chain_attr.return_value = stale_chain

    # Both .select() calls share the same return value chain — but the
    # caller distinguishes via .is_ vs .lt. We expose both on one mock.
    select_chain = MagicMock()
    select_chain.is_ = null_select.is_
    select_chain.lt = stale_select.lt

    client.table.return_value.select.return_value = select_chain
    return client


def test_select_candidates_null_bucket_only() -> None:
    """When NULL bucket fills the limit, stale bucket isn't queried."""
    null_rows = [{"video_id": str(i), "niche_id": 1, "views": 1000 * i} for i in range(1, 6)]
    client = _build_select_client(null_rows=null_rows, stale_rows=[])

    rows = _select_refresh_candidates(client, limit=5)
    assert len(rows) == 5
    assert [r["video_id"] for r in rows] == ["1", "2", "3", "4", "5"]


def test_select_candidates_falls_through_to_stale_when_null_short() -> None:
    """When NULLs don't fill the limit, the stale bucket fills the rest."""
    null_rows = [{"video_id": "n1", "niche_id": 1, "views": 5000}]
    stale_rows = [{"video_id": "s1", "niche_id": 1, "views": 3000}]
    client = _build_select_client(null_rows=null_rows, stale_rows=stale_rows)

    rows = _select_refresh_candidates(client, limit=5)
    assert [r["video_id"] for r in rows] == ["n1", "s1"]


def test_select_candidates_default_limit_is_batch_constant() -> None:
    null_rows = [
        {"video_id": str(i), "niche_id": 1, "views": 9999}
        for i in range(REFRESH_BATCH_LIMIT)
    ]
    client = _build_select_client(null_rows=null_rows, stale_rows=[])

    rows = _select_refresh_candidates(client)
    assert len(rows) == REFRESH_BATCH_LIMIT


# ── run_corpus_refresh — end-to-end ──────────────────────────────────


def _build_run_client(candidates: list[dict[str, Any]]) -> MagicMock:
    """Mock the candidates query + the per-row update chain."""
    client = MagicMock()

    # _select_refresh_candidates path: NULL bucket gets all candidates,
    # stale bucket returns []. Limit short-circuits.
    null_chain = MagicMock(execute=MagicMock(return_value=MagicMock(data=candidates)))
    null_select = MagicMock()
    null_chain_attr = null_select.is_.return_value.gte.return_value.order.return_value.limit
    null_chain_attr.return_value = null_chain

    stale_chain = MagicMock(execute=MagicMock(return_value=MagicMock(data=[])))
    stale_select = MagicMock()
    stale_chain_attr = stale_select.lt.return_value.gte.return_value.order.return_value.limit
    stale_chain_attr.return_value = stale_chain

    select_chain = MagicMock()
    select_chain.is_ = null_select.is_
    select_chain.lt = stale_select.lt
    client.table.return_value.select.return_value = select_chain

    # Update chain.
    update_chain = client.table.return_value.update.return_value.eq.return_value.execute
    update_chain.return_value = MagicMock(data=[])
    return client


def _build_post(aweme_id: str, *, views: int, likes: int = 0, saves: int = 0) -> dict[str, Any]:
    return {
        "aweme_detail": {
            "aweme_id": aweme_id,
            "statistics": {
                "play_count": views,
                "digg_count": likes,
                "comment_count": 0,
                "share_count": 0,
                "collect_count": saves,
            },
        }
    }


@pytest.mark.asyncio
async def test_run_refresh_zero_candidates_is_noop() -> None:
    client = _build_run_client(candidates=[])
    with patch("getviews_pipeline.ensemble.fetch_post_multi_info", new=AsyncMock(return_value=[])):
        result = await run_corpus_refresh(client=client)
    assert result == {
        "candidates": 0,
        "refreshed": 0,
        "skipped": 0,
        "missing": 0,
        "errors": 0,
        "delta_views_total": 0,
    }
    client.table.return_value.update.assert_not_called()


@pytest.mark.asyncio
async def test_run_refresh_updates_each_row_with_fresh_stats() -> None:
    candidates = [
        {"video_id": "100", "niche_id": 1, "views": 10_000},
        {"video_id": "101", "niche_id": 1, "views": 5_000},
    ]
    fresh_posts = [
        _build_post("100", views=15_000, likes=800, saves=120),
        _build_post("101", views=8_000, likes=300, saves=40),
    ]
    client = _build_run_client(candidates=candidates)

    with patch(
        "getviews_pipeline.ensemble.fetch_post_multi_info",
        new=AsyncMock(return_value=fresh_posts),
    ):
        result = await run_corpus_refresh(client=client)

    assert result["candidates"] == 2
    assert result["refreshed"] == 2
    assert result["missing"] == 0
    assert result["errors"] == 0
    # delta_views_total = (15k - 10k) + (8k - 5k) = 8k
    assert result["delta_views_total"] == 8_000

    # Both updates fired. Inspect one payload to confirm shape.
    update_call = client.table.return_value.update.call_args_list[0]
    payload = update_call.args[0]
    assert "last_refetched_at" in payload
    assert "engagement_rate" in payload
    assert "save_rate" in payload
    assert payload["views"] in (15_000, 8_000)


@pytest.mark.asyncio
async def test_run_refresh_skips_deleted_posts() -> None:
    """ED returns play_count=0 for deleted/private posts. We must skip
    those (counted as ``missing``) instead of writing 0s to good rows."""
    candidates = [
        {"video_id": "100", "niche_id": 1, "views": 10_000},
        {"video_id": "999_deleted", "niche_id": 1, "views": 500},
    ]
    fresh_posts = [
        _build_post("100", views=12_000, likes=400),
        _build_post("999_deleted", views=0),  # deleted shell
    ]
    client = _build_run_client(candidates=candidates)

    with patch(
        "getviews_pipeline.ensemble.fetch_post_multi_info",
        new=AsyncMock(return_value=fresh_posts),
    ):
        result = await run_corpus_refresh(client=client)

    assert result["refreshed"] == 1
    assert result["missing"] == 1
    # Only the live row got an UPDATE.
    assert client.table.return_value.update.call_count == 1


@pytest.mark.asyncio
async def test_run_refresh_handles_ensemble_failure_per_chunk() -> None:
    """If ED fails on a chunk, the whole chunk counts as errors but the
    cron continues to the next chunk."""
    # 25 candidates → 2 chunks (20 + 5)
    candidates = [
        {"video_id": str(i), "niche_id": 1, "views": 9999}
        for i in range(25)
    ]
    client = _build_run_client(candidates=candidates)

    # First call (chunk 1, 20 IDs) raises; second call (chunk 2, 5 IDs) returns fresh stats
    second_chunk_posts = [_build_post(str(i), views=11_111, likes=100) for i in range(20, 25)]
    side_effects = [Exception("ED rate limit"), second_chunk_posts]

    with patch(
        "getviews_pipeline.ensemble.fetch_post_multi_info",
        new=AsyncMock(side_effect=side_effects),
    ):
        result = await run_corpus_refresh(client=client)

    assert result["errors"] == 20
    assert result["refreshed"] == 5
    assert result["candidates"] == 25
