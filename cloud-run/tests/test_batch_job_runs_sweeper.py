"""Stale ``batch_job_runs`` sweeper — Cloud Run timeout orphans."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from getviews_pipeline.batch_observability import (
    is_swept_stale_batch_job_run,
    sweep_stale_running_job_runs,
)


def _client_with_stale(rows: list[dict]) -> MagicMock:
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = (
        MagicMock(data=rows)
    )
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[],
    )
    return client


def test_sweeps_stale_running_rows() -> None:
    stale_started = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    client = _client_with_stale([
        {"id": "run-1", "job_name": "batch/ingest", "started_at": stale_started, "summary": {}},
    ])
    swept = sweep_stale_running_job_runs(client, stale_after_min=65)
    assert swept == 1
    payload = client.table.return_value.update.call_args.args[0]
    assert payload["status"] == "failed"
    assert payload["summary"]["swept_stale_running"] is True
    assert payload["summary"]["aborted_early"] is True


def test_no_stale_rows_is_noop() -> None:
    client = _client_with_stale([])
    assert sweep_stale_running_job_runs(client) == 0
    client.table.return_value.update.assert_not_called()


def test_is_swept_stale_detects_summary_and_error() -> None:
    assert is_swept_stale_batch_job_run({"summary": {"swept_stale_running": True}}) is True
    assert is_swept_stale_batch_job_run({"error": "auto-swept: still running >65m"}) is True
    assert is_swept_stale_batch_job_run({"error": "ingest shard failed", "summary": {}}) is False
