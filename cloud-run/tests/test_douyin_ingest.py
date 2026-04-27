"""D2c (2026-06-03) — Kho Douyin ingest orchestrator tests.

Mocks ED fetchers, Gemini analysis, R2, and the Supabase client so
tests don't hit any network or DB. Covers the orchestration shape,
not the leaf pure-functions (those live in test_douyin_metadata.py and
test_douyin_translator.py).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from getviews_pipeline.douyin_ingest import (
    BATCH_DOUYIN_MIN_ER,
    BATCH_DOUYIN_MIN_VIEWS,
    BATCH_DOUYIN_VIDEOS_PER_NICHE,
    DouyinBatchSummary,
    _existing_douyin_video_ids,
    _fetch_active_douyin_niches,
    _fetch_douyin_pool,
    _passes_quality_gates,
    build_douyin_shot_rows,
    ingest_douyin_niche,
    run_douyin_batch_ingest,
)


# ── Quality gates ───────────────────────────────────────────────────


def _aweme_with_stats(views: int, likes: int = 0, saves: int = 0) -> dict[str, Any]:
    return {
        "aweme_id": "1",
        "statistics": {
            "play_count": views,
            "digg_count": likes,
            "comment_count": 0,
            "share_count": 0,
            "collect_count": saves,
        },
    }


def test_quality_gate_rejects_low_views() -> None:
    aweme = _aweme_with_stats(views=BATCH_DOUYIN_MIN_VIEWS - 1, likes=10_000)
    ok, reason = _passes_quality_gates(aweme)
    assert ok is False
    assert reason is not None
    assert "views=" in reason


def test_quality_gate_rejects_low_engagement_rate() -> None:
    """High views but ER below threshold → rejected. Sets ER ≈ 0%."""
    aweme = _aweme_with_stats(views=BATCH_DOUYIN_MIN_VIEWS * 10, likes=0, saves=0)
    ok, reason = _passes_quality_gates(aweme)
    assert ok is False
    assert reason is not None
    assert "er=" in reason


def test_quality_gate_passes_when_views_and_er_meet_threshold() -> None:
    """Saves contribute to ER (Douyin signal), so a save-heavy aweme
    can pass even with modest like counts."""
    views = BATCH_DOUYIN_MIN_VIEWS
    needed_engagement = int(views * (BATCH_DOUYIN_MIN_ER / 100.0)) + 100
    aweme = _aweme_with_stats(views=views, likes=0, saves=needed_engagement)
    ok, reason = _passes_quality_gates(aweme)
    assert ok is True
    assert reason is None


def test_quality_gate_handles_garbage_play_count() -> None:
    aweme = {"aweme_id": "1", "statistics": {"play_count": "not-a-number"}}
    ok, _ = _passes_quality_gates(aweme)
    assert ok is False


# ── _fetch_active_douyin_niches ─────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_active_niches_filters_by_active_flag() -> None:
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.execute.return_value = MagicMock(data=[
        {"id": 1, "slug": "wellness", "name_vn": "Wellness",
         "name_zh": "养生", "signal_hashtags_zh": ["#养生"]},
    ])
    client = MagicMock()
    client.table.return_value = chain

    out = await _fetch_active_douyin_niches(client)
    assert len(out) == 1
    assert out[0]["slug"] == "wellness"
    chain.eq.assert_called_with("active", True)


# ── _existing_douyin_video_ids ──────────────────────────────────────


@pytest.mark.asyncio
async def test_existing_video_ids_scoped_per_niche() -> None:
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = MagicMock(data=[
        {"video_id": "100"}, {"video_id": "200"}, {"video_id": ""},
    ])
    client = MagicMock()
    client.table.return_value = chain

    out = await _existing_douyin_video_ids(client, niche_id=4)
    assert out == {"100", "200"}
    chain.eq.assert_called_with("niche_id", 4)


# ── _fetch_douyin_pool ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pool_dedupes_keyword_and_hashtag_overlap() -> None:
    """A video that surfaces in both keyword + hashtag pool only goes
    through Gemini once."""
    niche = {
        "id": 1, "slug": "wellness", "name_zh": "养生",
        "signal_hashtags_zh": ["#养生"],
    }
    keyword_payload = ([{"aweme_id": "shared"}, {"aweme_id": "kw_only"}], None)
    hashtag_payload = ([{"aweme_id": "shared"}, {"aweme_id": "ht_only"}], None)
    with patch(
        "getviews_pipeline.douyin_ingest.fetch_douyin_keyword_search",
        new=AsyncMock(return_value=keyword_payload),
    ), patch(
        "getviews_pipeline.douyin_ingest.fetch_douyin_hashtag_posts",
        new=AsyncMock(return_value=hashtag_payload),
    ):
        out = await _fetch_douyin_pool(niche)
    ids = sorted([str(a["aweme_id"]) for a in out])
    assert ids == ["ht_only", "kw_only", "shared"]


@pytest.mark.asyncio
async def test_pool_resilient_to_keyword_fetch_failure() -> None:
    """Keyword search raising must NOT fail the whole pool — hashtag
    pool still contributes."""
    niche = {
        "id": 1, "slug": "wellness", "name_zh": "养生",
        "signal_hashtags_zh": ["#养生"],
    }
    with patch(
        "getviews_pipeline.douyin_ingest.fetch_douyin_keyword_search",
        new=AsyncMock(side_effect=RuntimeError("ED 503")),
    ), patch(
        "getviews_pipeline.douyin_ingest.fetch_douyin_hashtag_posts",
        new=AsyncMock(return_value=([{"aweme_id": "1"}], None)),
    ):
        out = await _fetch_douyin_pool(niche)
    assert [str(a["aweme_id"]) for a in out] == ["1"]


@pytest.mark.asyncio
async def test_pool_returns_empty_when_no_name_zh_or_hashtags() -> None:
    niche = {"id": 1, "slug": "x", "name_zh": "", "signal_hashtags_zh": []}
    with patch(
        "getviews_pipeline.douyin_ingest.fetch_douyin_keyword_search",
        new=AsyncMock(),
    ) as kw, patch(
        "getviews_pipeline.douyin_ingest.fetch_douyin_hashtag_posts",
        new=AsyncMock(),
    ) as ht:
        out = await _fetch_douyin_pool(niche)
    assert out == []
    kw.assert_not_called()
    ht.assert_not_called()


# ── build_douyin_shot_rows ──────────────────────────────────────────


def _corpus_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "video_id": "vid-1",
        "niche_id": 7,
        "douyin_url": "https://www.douyin.com/video/vid-1",
        "thumbnail_url": "https://cdn/thumb.jpg",
        "creator_handle": "alice",
        "hook_type": "curiosity_gap",
        "views": 1_000_000,
        "analysis_json": {
            "scenes": [
                {"type": "face_to_camera", "start": 0.0, "end": 2.0,
                 "framing": "close_up", "pace": "slow"},
                {"type": "demo", "start": 2.0, "end": 5.5,
                 "framing": "medium"},
            ],
        },
    }
    base.update(overrides)
    return base


def test_shot_rows_project_all_enrichment_fields() -> None:
    rows = build_douyin_shot_rows(_corpus_row())
    assert len(rows) == 2
    s0 = rows[0]
    assert s0["video_id"] == "vid-1"
    assert s0["niche_id"] == 7
    assert s0["scene_index"] == 0
    assert s0["framing"] == "close_up"
    assert s0["pace"] == "slow"
    assert s0["douyin_url"] == "https://www.douyin.com/video/vid-1"
    assert s0["views"] == 1_000_000
    assert s0["frame_url"] is None  # no scene_frame_urls passed


def test_shot_rows_drop_invalid_bounds() -> None:
    """Scenes with end <= start, missing bounds, or non-numeric must be
    silently dropped (CHECK constraint would fail the upsert otherwise)."""
    row = _corpus_row(analysis_json={
        "scenes": [
            {"start": 0.0, "end": 2.0},          # OK
            {"start": 3.0, "end": 2.0},          # inverted
            {"start": 5.0, "end": 5.0},          # zero-length
            {"start": None, "end": 5.0},         # missing
            {"start": 6.0, "end": 9.0},          # OK
        ],
    })
    rows = build_douyin_shot_rows(row)
    assert [r["scene_index"] for r in rows] == [0, 4]


def test_shot_rows_attach_frame_urls_from_mapping() -> None:
    rows = build_douyin_shot_rows(
        _corpus_row(), {0: "https://r2/v/0.jpg"},
    )
    assert rows[0]["frame_url"] == "https://r2/v/0.jpg"
    # Scene index 1 has no entry — stays None.
    assert rows[1]["frame_url"] is None


def test_shot_rows_empty_when_no_scenes() -> None:
    row = _corpus_row(analysis_json={"scenes": []})
    assert build_douyin_shot_rows(row) == []


def test_shot_rows_empty_when_video_id_missing() -> None:
    row = _corpus_row()
    row.pop("video_id")
    assert build_douyin_shot_rows(row) == []


# ── ingest_douyin_niche ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_niche_dedupes_against_existing_video_ids() -> None:
    """Pool returns 3 awemes, 2 already in corpus → only 1 candidate
    survives dedupe; the analyzer is called exactly once."""
    niche = {"id": 1, "slug": "wellness", "name_zh": "养生", "signal_hashtags_zh": []}

    pool = [{"aweme_id": "a"}, {"aweme_id": "b"}, {"aweme_id": "c"}]
    existing = {"a", "c"}

    with patch(
        "getviews_pipeline.douyin_ingest._fetch_douyin_pool",
        new=AsyncMock(return_value=pool),
    ), patch(
        "getviews_pipeline.douyin_ingest._existing_douyin_video_ids",
        new=AsyncMock(return_value=existing),
    ), patch(
        "getviews_pipeline.douyin_ingest._passes_quality_gates",
        return_value=(False, "low views"),
    ):
        # ``_passes_quality_gates`` rejects everything → the analyzer
        # never runs. Counts surface in the result.
        result = await ingest_douyin_niche(niche, client=MagicMock())

    assert result.fetched == 3
    assert result.skipped_dedupe == 2
    # ``b`` survives dedupe but quality-gate kicks it out.
    assert result.skipped_quality == 1
    assert result.inserted == 0


@pytest.mark.asyncio
async def test_niche_caps_qualified_at_videos_per_niche() -> None:
    """Even if many awemes pass dedupe + quality, only
    ``BATCH_DOUYIN_VIDEOS_PER_NICHE`` reach the analyzer."""
    niche = {"id": 1, "slug": "wellness", "name_zh": "养生", "signal_hashtags_zh": []}
    # 2× the cap so we know we're truncating.
    pool = [
        {"aweme_id": str(i)}
        for i in range(BATCH_DOUYIN_VIDEOS_PER_NICHE * 2)
    ]

    captured: dict[str, list[dict[str, Any]]] = {}

    async def _fake_ingest_candidate(_client, _niche, candidates):
        captured["candidates"] = candidates
        from getviews_pipeline.douyin_ingest import DouyinIngestResult
        r = DouyinIngestResult(niche_id=1, niche_name="wellness")
        r.inserted = len(candidates)
        return r

    with patch(
        "getviews_pipeline.douyin_ingest._fetch_douyin_pool",
        new=AsyncMock(return_value=pool),
    ), patch(
        "getviews_pipeline.douyin_ingest._existing_douyin_video_ids",
        new=AsyncMock(return_value=set()),
    ), patch(
        "getviews_pipeline.douyin_ingest._passes_quality_gates",
        return_value=(True, None),
    ), patch(
        "getviews_pipeline.douyin_ingest._ingest_candidate_awemes_douyin",
        new=AsyncMock(side_effect=_fake_ingest_candidate),
    ):
        result = await ingest_douyin_niche(niche, client=MagicMock())

    assert len(captured["candidates"]) == BATCH_DOUYIN_VIDEOS_PER_NICHE
    assert result.inserted == BATCH_DOUYIN_VIDEOS_PER_NICHE


@pytest.mark.asyncio
async def test_niche_short_circuits_on_empty_pool() -> None:
    niche = {"id": 1, "slug": "wellness", "name_zh": "养生", "signal_hashtags_zh": []}
    with patch(
        "getviews_pipeline.douyin_ingest._fetch_douyin_pool",
        new=AsyncMock(return_value=[]),
    ), patch(
        "getviews_pipeline.douyin_ingest._existing_douyin_video_ids",
        new=AsyncMock(),
    ) as existing_mock:
        result = await ingest_douyin_niche(niche, client=MagicMock())
    assert result.fetched == 0
    assert result.inserted == 0
    # Don't waste a DB round-trip when the pool is empty.
    existing_mock.assert_not_called()


# ── run_douyin_batch_ingest ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_run_aggregates_per_niche_results() -> None:
    """Top-level entrypoint runs each niche concurrently and rolls up
    inserted/skipped/failed counts into a single summary."""
    niches = [
        {"id": 1, "slug": "wellness", "name_zh": "养生"},
        {"id": 2, "slug": "tech", "name_zh": "科技"},
    ]

    async def _fake_ingest(n, _client, deep=False):  # noqa: ARG001
        from getviews_pipeline.douyin_ingest import DouyinIngestResult
        r = DouyinIngestResult(niche_id=int(n["id"]), niche_name=n["slug"])
        r.fetched = 5
        r.inserted = 2
        r.skipped_dedupe = 1
        r.skipped_quality = 2
        return r

    with patch(
        "getviews_pipeline.douyin_ingest._service_client",
        return_value=MagicMock(),
    ), patch(
        "getviews_pipeline.douyin_ingest._fetch_active_douyin_niches",
        new=AsyncMock(return_value=niches),
    ), patch(
        "getviews_pipeline.douyin_ingest.ingest_douyin_niche",
        new=AsyncMock(side_effect=_fake_ingest),
    ):
        summary: DouyinBatchSummary = await run_douyin_batch_ingest()

    assert summary.niches_processed == 2
    assert summary.total_inserted == 4   # 2 + 2
    # Each niche reports skipped_dedupe=1 + skipped_quality=2 = 3 → total 6.
    assert summary.total_skipped == 6
    assert summary.total_failed == 0
    assert len(summary.niche_results) == 2


@pytest.mark.asyncio
async def test_batch_run_isolates_per_niche_failures() -> None:
    """One niche raising must NOT abort the others — surface the failure
    in summary.total_failed and continue."""
    niches = [
        {"id": 1, "slug": "wellness", "name_zh": "养生"},
        {"id": 2, "slug": "tech", "name_zh": "科技"},
    ]

    async def _fake_ingest(n, _client, deep=False):  # noqa: ARG001
        from getviews_pipeline.douyin_ingest import DouyinIngestResult
        if int(n["id"]) == 1:
            raise RuntimeError("niche 1 broke")
        r = DouyinIngestResult(niche_id=2, niche_name="tech")
        r.inserted = 3
        return r

    with patch(
        "getviews_pipeline.douyin_ingest._service_client",
        return_value=MagicMock(),
    ), patch(
        "getviews_pipeline.douyin_ingest._fetch_active_douyin_niches",
        new=AsyncMock(return_value=niches),
    ), patch(
        "getviews_pipeline.douyin_ingest.ingest_douyin_niche",
        new=AsyncMock(side_effect=_fake_ingest),
    ):
        summary = await run_douyin_batch_ingest()

    # Niche 2 still inserted; niche 1 surfaces as failed.
    assert summary.niches_processed == 2
    assert summary.total_inserted == 3
    assert summary.total_failed == 1


@pytest.mark.asyncio
async def test_batch_run_filters_by_niche_ids() -> None:
    """``niche_ids=[2]`` runs only niche 2 even though the taxonomy has
    multiple active rows."""
    niches = [
        {"id": 1, "slug": "wellness", "name_zh": "养生"},
        {"id": 2, "slug": "tech", "name_zh": "科技"},
    ]

    seen_niche_ids: list[int] = []

    async def _fake_ingest(n, _client, deep=False):  # noqa: ARG001
        seen_niche_ids.append(int(n["id"]))
        from getviews_pipeline.douyin_ingest import DouyinIngestResult
        return DouyinIngestResult(niche_id=int(n["id"]), niche_name=n["slug"])

    with patch(
        "getviews_pipeline.douyin_ingest._service_client",
        return_value=MagicMock(),
    ), patch(
        "getviews_pipeline.douyin_ingest._fetch_active_douyin_niches",
        new=AsyncMock(return_value=niches),
    ), patch(
        "getviews_pipeline.douyin_ingest.ingest_douyin_niche",
        new=AsyncMock(side_effect=_fake_ingest),
    ):
        await run_douyin_batch_ingest(niche_ids=[2])

    assert seen_niche_ids == [2]


@pytest.mark.asyncio
async def test_batch_run_returns_empty_summary_when_no_active_niches() -> None:
    with patch(
        "getviews_pipeline.douyin_ingest._service_client",
        return_value=MagicMock(),
    ), patch(
        "getviews_pipeline.douyin_ingest._fetch_active_douyin_niches",
        new=AsyncMock(return_value=[]),
    ), patch(
        "getviews_pipeline.douyin_ingest.ingest_douyin_niche",
        new=AsyncMock(),
    ) as ingest_mock:
        summary = await run_douyin_batch_ingest()
    assert summary.niches_processed == 0
    ingest_mock.assert_not_called()
