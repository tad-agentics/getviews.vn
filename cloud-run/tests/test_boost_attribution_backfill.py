"""Tests for boost_attribution backfill."""

from __future__ import annotations

from unittest.mock import MagicMock

from getviews_pipeline.boost_attribution_backfill import (
    _percentiles_from_rows,
    run_boost_attribution_backfill_sync,
)


def test_percentiles_from_rows_marks_thin_when_small_sample() -> None:
    pct = _percentiles_from_rows([{"views": 1000, "engagement_rate": 2.0, "comments": 10}])
    assert pct.thin is True
    assert pct.sample_size == 1


def test_backfill_classifies_unknown_rows() -> None:
    pct_chain = MagicMock()
    pct_chain.execute.return_value = MagicMock(
        data=[
            {"views": 100_000, "engagement_rate": 1.0, "comments": 0},
            {"views": 50_000, "engagement_rate": 5.0, "comments": 500},
        ]
    )
    row_chain = MagicMock()
    row_chain.execute.return_value = MagicMock(
        data=[
            {
                "video_id": "v1",
                "views": 100_000,
                "engagement_rate": 1.0,
                "comments": 0,
                "boost_attribution": "unknown",
                "reference_eligible": True,
            },
            {
                "video_id": "v2",
                "views": 50_000,
                "engagement_rate": 5.0,
                "comments": 500,
                "boost_attribution": "unknown",
                "reference_eligible": True,
            },
        ]
    )

    def _table(name: str) -> MagicMock:
        tbl = MagicMock()
        sel = tbl.select.return_value
        sel.eq.return_value.gt.return_value.gte.return_value = pct_chain
        sel.eq.return_value.gt.return_value.gte.return_value.in_.return_value = row_chain
        tbl.upsert.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    client = MagicMock()
    client.table.side_effect = _table

    stats = run_boost_attribution_backfill_sync(client, dry_run=True)
    assert stats["scanned"] == 2
    assert stats["suspect_medium"] >= 1
    assert stats["organic_confident"] >= 1
    client.table.return_value.upsert.assert_not_called()
