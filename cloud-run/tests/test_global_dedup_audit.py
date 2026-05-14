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


def test_upsert_rows_sync_adds_provenance():
    """_upsert_rows_sync must enrich rows with ingest_source + quality_tier before upsert."""
    from getviews_pipeline.corpus_ingest import _upsert_rows_sync
    source = inspect.getsource(_upsert_rows_sync)
    assert "ingest_source" in source, "_upsert_rows_sync must set ingest_source"
    assert "batch_nightly" in source, "_upsert_rows_sync must default ingest_source to batch_nightly"
    assert "quality_tier" in source, "_upsert_rows_sync must set quality_tier"
    assert "last_refreshed_at" in source, "_upsert_rows_sync must set last_refreshed_at"


def test_upsert_rows_sync_routes_through_rpc():
    """The provenance-safe RPC must be called first; the plain upsert
    path is the fallback for environments where the migration hasn't
    propagated yet. Regression for "RPC shipped but uncalled" — Phase
    6.2 was defeated until this wiring landed."""
    from unittest.mock import MagicMock
    from getviews_pipeline.corpus_ingest import _upsert_rows_sync

    client = MagicMock()
    _upsert_rows_sync(client, [{"video_id": "v1"}])

    # Happy path: RPC called exactly once with the enriched batch.
    client.rpc.assert_called_once()
    rpc_args = client.rpc.call_args
    assert rpc_args[0][0] == "upsert_video_corpus_batch"
    sent_rows = rpc_args[0][1]["p_rows"]
    assert len(sent_rows) == 1
    sent = sent_rows[0]
    assert sent["video_id"] == "v1"
    assert sent["ingest_source"] == "batch_nightly"
    assert sent["quality_tier"] == "high"
    assert "first_seen_at" in sent and "last_refreshed_at" in sent
    # Direct upsert should NOT fire when the RPC succeeds.
    client.table.assert_not_called()


def test_upsert_rows_sync_falls_back_when_rpc_unavailable():
    """If the RPC throws (migration not yet propagated), the plain
    upsert path runs so corpus ingest keeps making progress."""
    from unittest.mock import MagicMock
    from getviews_pipeline.corpus_ingest import _upsert_rows_sync

    client = MagicMock()
    client.rpc.return_value.execute.side_effect = RuntimeError("rpc not found")
    _upsert_rows_sync(client, [{"video_id": "v1"}])
    client.rpc.assert_called_once()
    client.table.assert_called_once_with("video_corpus")
