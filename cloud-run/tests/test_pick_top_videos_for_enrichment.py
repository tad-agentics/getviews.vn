"""Wave 2.5 Phase A PR #4c — top-N selector for the enrich_shots trigger.

Pins:
  * Already-enriched video_ids (any shot with non-null framing) are excluded
  * Ordering is views DESC (delegated to Supabase — we verify the query builder
    got the right .order() call)
  * Caps at the passed ``limit`` even if the over-fetch returned more
  * Empty results return []
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from getviews_pipeline.corpus_ingest import _pick_top_videos_for_enrichment_sync


def _mk_client(
    *,
    enriched_video_ids: list[str],
    corpus_rows: list[dict[str, object]],
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Build a MagicMock client that mimics the two .table(...) chains
    used inside _pick_top_videos_for_enrichment_sync. Returns
    (client, shots_chain, corpus_chain) so individual assertions can
    inspect each chain.
    """
    shots_chain = MagicMock(name="shots_chain")
    shots_chain.select.return_value = shots_chain
    shots_chain.not_.is_.return_value = shots_chain
    shots_chain.execute.return_value = SimpleNamespace(
        data=[{"video_id": vid} for vid in enriched_video_ids],
    )

    corpus_chain = MagicMock(name="corpus_chain")
    corpus_chain.select.return_value = corpus_chain
    corpus_chain.not_.is_.return_value = corpus_chain
    corpus_chain.eq.return_value = corpus_chain
    corpus_chain.order.return_value = corpus_chain
    corpus_chain.limit.return_value = corpus_chain
    corpus_chain.execute.return_value = SimpleNamespace(data=corpus_rows)

    client = MagicMock()

    def _table_dispatch(name: str) -> MagicMock:
        if name == "video_shots":
            return shots_chain
        if name == "video_corpus":
            return corpus_chain
        raise AssertionError(f"unexpected table {name!r}")

    client.table.side_effect = _table_dispatch
    return client, shots_chain, corpus_chain


def test_excludes_already_enriched_video_ids() -> None:
    client, _, _ = _mk_client(
        enriched_video_ids=["v1", "v3"],
        corpus_rows=[
            {"video_id": "v1", "niche_id": 7},
            {"video_id": "v2", "niche_id": 7},
            {"video_id": "v3", "niche_id": 4},
            {"video_id": "v4", "niche_id": 4},
        ],
    )
    picked = _pick_top_videos_for_enrichment_sync(client, limit=10)
    assert [p["video_id"] for p in picked] == ["v2", "v4"]


def test_caps_at_limit_even_when_corpus_has_more() -> None:
    client, _, corpus_chain = _mk_client(
        enriched_video_ids=[],
        corpus_rows=[
            {"video_id": f"v{i}", "niche_id": 7} for i in range(100)
        ],
    )
    picked = _pick_top_videos_for_enrichment_sync(client, limit=5)
    assert len(picked) == 5
    # Over-fetch multiplier: limit*2 + 50 = 60
    corpus_chain.limit.assert_called_once_with(60)


def test_orders_by_views_desc() -> None:
    client, _, corpus_chain = _mk_client(
        enriched_video_ids=[],
        corpus_rows=[{"video_id": "v1", "niche_id": 7}],
    )
    _pick_top_videos_for_enrichment_sync(client, limit=1)
    corpus_chain.order.assert_called_once_with("views", desc=True)


def test_filters_rows_missing_video_id_or_niche() -> None:
    client, _, _ = _mk_client(
        enriched_video_ids=[],
        corpus_rows=[
            {"video_id": None, "niche_id": 7},
            {"video_id": "v2", "niche_id": None},
            {"video_id": "", "niche_id": 7},
            {"video_id": "v4", "niche_id": 4},
        ],
    )
    picked = _pick_top_videos_for_enrichment_sync(client, limit=10)
    assert [p["video_id"] for p in picked] == ["v4"]


def test_empty_corpus_returns_empty_list() -> None:
    client, _, _ = _mk_client(
        enriched_video_ids=["v1"],
        corpus_rows=[],
    )
    assert _pick_top_videos_for_enrichment_sync(client, limit=50) == []


def test_niche_id_coerces_to_int() -> None:
    """niche_id comes back from Supabase as int, but guard against a
    stray string slipping through older schemas."""
    client, _, _ = _mk_client(
        enriched_video_ids=[],
        corpus_rows=[{"video_id": "v1", "niche_id": "7"}],
    )
    picked = _pick_top_videos_for_enrichment_sync(client, limit=1)
    assert picked == [{"video_id": "v1", "niche_id": 7}]


def test_filters_to_content_type_video() -> None:
    """Carousels have empty scenes — no point re-extracting them."""
    client, _, corpus_chain = _mk_client(
        enriched_video_ids=[],
        corpus_rows=[{"video_id": "v1", "niche_id": 7}],
    )
    _pick_top_videos_for_enrichment_sync(client, limit=1)
    corpus_chain.eq.assert_called_once_with("content_type", "video")


def test_shots_query_filters_on_non_null_framing() -> None:
    """Verify the 'enriched = any shot with framing IS NOT NULL' filter."""
    client, shots_chain, _ = _mk_client(
        enriched_video_ids=[],
        corpus_rows=[{"video_id": "v1", "niche_id": 7}],
    )
    _pick_top_videos_for_enrichment_sync(client, limit=1)
    shots_chain.not_.is_.assert_called_once_with("framing", "null")
