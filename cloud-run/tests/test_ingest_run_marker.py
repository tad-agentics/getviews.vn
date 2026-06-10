"""H-3 — corpus ingest shift run-marker (corpus_ingest_runs claim)."""

from __future__ import annotations

from unittest.mock import MagicMock

from getviews_pipeline.corpus_ingest import (
    BatchSummary,
    _claim_ingest_shift_sync,
    _complete_ingest_shift_sync,
)


def _client(upsert_data: list | None, raises: bool = False) -> MagicMock:
    sb = MagicMock()
    if raises:
        sb.table.return_value.upsert.side_effect = Exception("db down")
    else:
        sb.table.return_value.upsert.return_value.execute.return_value = MagicMock(
            data=upsert_data
        )
    return sb


def test_first_claim_wins() -> None:
    sb = _client([{"utc_day": "2026-06-10", "ingest_shift": "a"}])
    assert _claim_ingest_shift_sync(sb, "a") is True
    _, kwargs = sb.table.return_value.upsert.call_args
    assert kwargs.get("ignore_duplicates") is True
    assert kwargs.get("on_conflict") == "utc_day,ingest_shift"


def test_duplicate_claim_is_rejected() -> None:
    # ignore_duplicates upsert returns no rows when the slot is taken.
    sb = _client([])
    assert _claim_ingest_shift_sync(sb, "a") is False


def test_claim_fails_open_on_infra_error() -> None:
    # The guard must never block the nightly ingest itself.
    sb = _client(None, raises=True)
    assert _claim_ingest_shift_sync(sb, "a") is True


def test_completion_stamp_never_raises() -> None:
    sb = MagicMock()
    sb.table.return_value.update.side_effect = Exception("db down")
    _complete_ingest_shift_sync(sb, "a", BatchSummary())  # no raise
