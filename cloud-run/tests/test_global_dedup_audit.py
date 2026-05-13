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
