"""Tests for ``batch_observability.record_job_run``.

Pins the three contractual behaviours needed for Axis 5 (state-of-corpus):
  1. Clean exit → one INSERT (running) + one UPDATE (status='ok').
  2. Exception → one INSERT + one UPDATE (status='failed', error=…) and
     the exception is re-raised.
  3. Observability write failures don't block the cron body — if the
     INSERT itself raises, the context manager still yields and the
     body runs to completion.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from getviews_pipeline.batch_observability import record_job_run


def _build_client(insert_row: dict[str, Any] | None = None) -> MagicMock:
    """Minimal Supabase chain: ``client.table(x).insert(…).execute()``
    and ``.update(…).eq(…).execute()``.
    """
    client = MagicMock()

    insert_resp = MagicMock(data=[insert_row] if insert_row else [])
    client.table.return_value.insert.return_value.execute.return_value = insert_resp

    update_resp = MagicMock(data=[])
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = update_resp

    return client


# ── happy path ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_clean_exit_marks_ok() -> None:
    client = _build_client(insert_row={"id": "run-1"})

    async with record_job_run(client, "batch/analytics") as summary:
        summary["videos"] = 42

    # INSERT call
    insert_call = client.table.return_value.insert.call_args
    insert_payload = insert_call.args[0]
    assert insert_payload["job_name"] == "batch/analytics"
    assert insert_payload["status"] == "running"
    assert "started_at" in insert_payload

    # UPDATE call
    update_call = client.table.return_value.update.call_args
    update_payload = update_call.args[0]
    assert update_payload["status"] == "ok"
    assert update_payload["summary"] == {"videos": 42}
    assert update_payload["duration_ms"] is not None
    assert update_payload["duration_ms"] >= 0
    assert "finished_at" in update_payload
    assert "error" not in update_payload

    # Row scoped by .eq("id", "run-1")
    eq_call = client.table.return_value.update.return_value.eq.call_args
    assert eq_call.args == ("id", "run-1")


@pytest.mark.asyncio
async def test_empty_summary_stored_as_null() -> None:
    """When the caller doesn't populate the summary, JSONB should be
    NULL rather than {}. Keeps the audit log tidy."""
    client = _build_client(insert_row={"id": "run-2"})

    async with record_job_run(client, "batch/ingest"):
        pass

    update_payload = client.table.return_value.update.call_args.args[0]
    assert update_payload["summary"] is None


# ── exception path ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exception_marks_failed_and_reraises() -> None:
    client = _build_client(insert_row={"id": "run-3"})

    with pytest.raises(RuntimeError, match="boom"):
        async with record_job_run(client, "batch/layer0") as summary:
            summary["partial"] = True
            raise RuntimeError("boom")

    update_payload = client.table.return_value.update.call_args.args[0]
    assert update_payload["status"] == "failed"
    assert "RuntimeError" in update_payload["error"]
    assert "boom" in update_payload["error"]
    assert update_payload["summary"] == {"partial": True}


@pytest.mark.asyncio
async def test_error_string_truncated_at_5000_chars() -> None:
    """A monster traceback shouldn't blow row size. 5000 cap is the
    configured ``_ERROR_MAX_LEN``."""
    client = _build_client(insert_row={"id": "run-4"})
    massive = "x" * 10_000

    with pytest.raises(ValueError):
        async with record_job_run(client, "batch/ingest"):
            raise ValueError(massive)

    update_payload = client.table.return_value.update.call_args.args[0]
    assert len(update_payload["error"]) == 5000


# ── best-effort isolation ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_insert_failure_does_not_block_body() -> None:
    """If the initial INSERT against ``batch_job_runs`` raises, the
    context manager must still yield. Losing an observability row is
    strictly better than aborting the real cron."""
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
        "supabase down"
    )

    body_ran = False
    async with record_job_run(client, "batch/analytics") as summary:
        body_ran = True
        summary["done"] = True

    assert body_ran is True
    # No UPDATE call should have been attempted — we never got a run_id
    client.table.return_value.update.assert_not_called()


@pytest.mark.asyncio
async def test_insert_returns_empty_data_is_handled() -> None:
    """Supabase can return ``data=[]`` on insert if the row was filtered
    by RLS or a trigger. Must not crash — just skip the UPDATE."""
    client = _build_client(insert_row=None)

    async with record_job_run(client, "batch/analytics"):
        pass

    client.table.return_value.update.assert_not_called()


@pytest.mark.asyncio
async def test_update_failure_does_not_propagate() -> None:
    """If the terminal UPDATE fails, the context manager must still
    exit cleanly — we don't want to mask the fact that the body
    succeeded with an observability-infrastructure error."""
    client = _build_client(insert_row={"id": "run-5"})
    client.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
        RuntimeError("db flake")
    )

    # Should not raise
    async with record_job_run(client, "batch/analytics"):
        pass


# ── summary propagation ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_is_serializable_dict() -> None:
    """Summary contents flow through to the stored JSONB unchanged.

    Nested dicts + primitives round-trip. Protects against a future
    refactor that swaps the yielded object for something exotic."""
    client = _build_client(insert_row={"id": "run-6"})

    nested = {
        "analytics": {"creators_updated": 10, "errors": []},
        "signal": {"grades_written": 21, "niches_processed": 21},
        "flag": True,
    }

    async with record_job_run(client, "batch/analytics") as summary:
        summary.update(nested)

    update_payload = client.table.return_value.update.call_args.args[0]
    assert update_payload["summary"] == nested
