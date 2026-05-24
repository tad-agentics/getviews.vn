"""Phase 6.3 — verify _existing_video_ids is global (not per-niche)."""
import inspect

from getviews_pipeline.corpus_ingest import _existing_video_ids, _existing_video_ids_sync


def test_async_existing_video_ids_is_global():
    """_existing_video_ids must not filter by niche_id — it must be a global dedup."""
    source = inspect.getsource(_existing_video_ids)
    # The old per-niche query had .eq("niche_id", niche_id) — this must be gone.
    assert '.eq("niche_id"' not in source, (
        "_existing_video_ids still filters by niche_id (per-niche scope). "
        "Must be global to prevent cross-niche dedup leak."
    )


def test_sync_existing_video_ids_is_global():
    """_existing_video_ids_sync must not filter by niche_id — it must be a global dedup."""
    source = inspect.getsource(_existing_video_ids_sync)
    assert '.eq("niche_id"' not in source, (
        "_existing_video_ids_sync still filters by niche_id (per-niche scope). "
        "Must be global to prevent cross-niche dedup leak."
    )


def test_load_all_existing_video_ids_sync_paginates():
    """CR-1: paginate past PostgREST's default row cap; merge all pages."""
    from unittest.mock import MagicMock, call

    from getviews_pipeline.corpus_ingest import _load_all_existing_video_ids_sync

    page = {"i": 0}

    def _execute() -> MagicMock:
        page["i"] += 1
        if page["i"] == 1:
            return MagicMock(data=[{"video_id": str(i)} for i in range(1000)])
        return MagicMock(data=[{"video_id": "1000"}, {"video_id": "1001"}])

    chain = MagicMock()
    chain.select.return_value = chain
    chain.range.return_value = chain
    chain.execute.side_effect = _execute
    client = MagicMock()
    client.table.return_value = chain

    out = _load_all_existing_video_ids_sync(client, page_size=1000)
    assert len(out) == 1002
    assert chain.range.call_args_list == [call(0, 999), call(1000, 1999)]


def test_load_all_existing_video_ids_sync_is_global():
    """Loader must not filter by niche_id."""
    from getviews_pipeline.corpus_ingest import _load_all_existing_video_ids_sync

    source = inspect.getsource(_load_all_existing_video_ids_sync)
    assert '.eq("niche_id"' not in source, (
        "_load_all_existing_video_ids_sync must stay global (no per-niche filter)."
    )


def test_upsert_rows_sync_adds_provenance():
    """_upsert_rows_sync must enrich rows with ingest_source + quality_tier before upsert."""
    from getviews_pipeline.corpus_ingest import _upsert_rows_sync
    source = inspect.getsource(_upsert_rows_sync)
    assert "ingest_source" in source, "_upsert_rows_sync must set ingest_source"
    assert "batch_nightly" in source, "_upsert_rows_sync must default ingest_source to batch_nightly"
    assert "quality_tier" in source, "_upsert_rows_sync must set quality_tier"
    assert "last_refreshed_at" in source, "_upsert_rows_sync must set last_refreshed_at"


def test_upsert_rows_sync_merges_provenance_and_full_upserts():
    """Provenance merge + full PostgREST upsert (not subset RPC)."""
    from unittest.mock import MagicMock

    from getviews_pipeline.corpus_ingest import _upsert_rows_sync

    client = MagicMock()
    select_chain = MagicMock()
    select_chain.in_.return_value = select_chain
    select_chain.execute.return_value = MagicMock(
        data=[
            {
                "video_id": "v1",
                "ingest_source": "user_diagnosis",
                "first_seen_at": "2026-05-01T00:00:00+00:00",
                "quality_tier": "high",
                "stats_history": [{"phase": "t0", "views": 1}],
            }
        ]
    )
    table_mock = MagicMock()
    table_mock.select.return_value = select_chain
    upsert_mock = MagicMock()
    table_mock.upsert.return_value = upsert_mock
    upsert_mock.execute.return_value = MagicMock(data=[])
    client.table.return_value = table_mock

    _upsert_rows_sync(
        client,
        [
            {
                "video_id": "v1",
                "boost_attribution": "organic_confident",
                "stats_history": [{"phase": "t0", "views": 99}],
            }
        ],
    )

    client.rpc.assert_not_called()
    client.table.assert_called_with("video_corpus")
    sent_rows = table_mock.upsert.call_args[0][0]
    assert sent_rows[0]["ingest_source"] == "user_diagnosis"
    assert sent_rows[0]["first_seen_at"] == "2026-05-01T00:00:00+00:00"
    assert sent_rows[0]["stats_history"] == [{"phase": "t0", "views": 1}]
    assert sent_rows[0]["boost_attribution"] == "organic_confident"
    assert table_mock.upsert.call_args[1]["on_conflict"] == "video_id"


def test_upsert_rows_sync_falls_back_when_rpc_unavailable():
    """Legacy name — full upsert always runs; no RPC attempt."""
    from unittest.mock import MagicMock

    from getviews_pipeline.corpus_ingest import _upsert_rows_sync

    client = MagicMock()
    select_chain = MagicMock()
    select_chain.in_.return_value = select_chain
    select_chain.execute.return_value = MagicMock(data=[])
    table_mock = MagicMock()
    table_mock.select.return_value = select_chain
    upsert_mock = MagicMock()
    table_mock.upsert.return_value = upsert_mock
    upsert_mock.execute.return_value = MagicMock(data=[])
    client.table.return_value = table_mock

    _upsert_rows_sync(client, [{"video_id": "v1"}])
    client.rpc.assert_not_called()
    client.table.assert_called_with("video_corpus")


def test_enrich_breakout_ratio_uses_cohort_p50_when_no_author_median():
    """R3 proxy — persist breakout_ratio from niche/class p50 when ED median missing."""
    from getviews_pipeline.corpus_instructiveness import IngestBatchContext, NicheViewStats
    from getviews_pipeline.corpus_ingest import _enrich_breakout_ratio_for_row

    ctx = IngestBatchContext(
        niche_stats={
            3: NicheViewStats(niche_id=3, p50_views=10_000, p75_views=20_000, corpus_count=200),
        },
    )
    aweme = {
        "author": {"unique_id": "creator_x"},
        "statistics": {"play_count": 50_000},
    }
    row: dict = {"video_id": "v1", "views": 50_000}

    _enrich_breakout_ratio_for_row(
        row,
        aweme,
        niche_id=3,
        ingest_batch_ctx=ctx,
        content_class_id=None,
    )

    assert row["breakout_ratio"] == 5.0
