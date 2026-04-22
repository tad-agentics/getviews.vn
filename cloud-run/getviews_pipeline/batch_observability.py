"""Cron job observability — wrap /batch/* endpoints in a ``batch_job_runs`` lifecycle row.

Closes the Axis 5 gap surfaced in ``artifacts/docs/state-of-corpus.md``:
today, if a data-pipeline cron silently fails we only notice when the
downstream tables stop growing. This helper records one row per
invocation (``status='running' → 'ok' | 'failed'``), with duration and
a caller-supplied summary blob.

Usage::

    from getviews_pipeline.batch_observability import record_job_run

    async with record_job_run(client, 'batch/analytics') as summary:
        analytics = await run_analytics()
        summary['analytics'] = {
            'creators_updated': analytics.creators_updated,
            # ...
        }

Observability writes are best-effort — if the INSERT or UPDATE against
``batch_job_runs`` itself fails, we log a warning but never block the
cron body. Losing an observability row is strictly better than failing
a real pipeline run because the audit log is unreachable.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter_ns
from typing import Any

logger = logging.getLogger(__name__)

# Truncate stored error strings so a monster traceback can't blow the
# row size past reasonable. The full traceback is still in Cloud Run
# stdout logs for debugging.
_ERROR_MAX_LEN = 5000


@asynccontextmanager
async def record_job_run(
    client: Any,
    job_name: str,
) -> AsyncIterator[dict[str, Any]]:
    """Record a cron-job lifecycle row in ``batch_job_runs``.

    Yields a mutable ``summary`` dict — the caller mutates it during
    the run; the final contents are stored as ``summary`` JSONB on the
    row at exit.

    On exception, the row is marked ``status='failed'`` with the error
    string (truncated to %d chars) and the exception is re-raised.
    """
    started_ns = perf_counter_ns()
    summary: dict[str, Any] = {}
    run_id = _insert_running(client, job_name)

    try:
        yield summary
    except Exception as exc:
        _finalize(
            client, run_id, status="failed",
            started_ns=started_ns, summary=summary,
            error=_format_error(exc),
        )
        raise
    else:
        _finalize(
            client, run_id, status="ok",
            started_ns=started_ns, summary=summary,
            error=None,
        )


def _insert_running(client: Any, job_name: str) -> str | None:
    """Insert the start row and return its ID. Returns None on failure."""
    try:
        resp = (
            client.table("batch_job_runs")
            .insert({
                "job_name": job_name,
                "started_at": datetime.now(UTC).isoformat(),
                "status": "running",
            })
            .execute()
        )
        data = resp.data or []
        if data:
            return data[0].get("id")
    except Exception as exc:
        logger.warning(
            "[batch_observability] insert failed for %s: %s", job_name, exc,
        )
    return None


def _finalize(
    client: Any,
    run_id: str | None,
    *,
    status: str,
    started_ns: int,
    summary: dict[str, Any],
    error: str | None,
) -> None:
    """Write the terminal row state. No-op if we never inserted."""
    if run_id is None:
        return
    duration_ms = max(0, (perf_counter_ns() - started_ns) // 1_000_000)
    payload: dict[str, Any] = {
        "finished_at": datetime.now(UTC).isoformat(),
        "status": status,
        "duration_ms": int(duration_ms),
        "summary": summary or None,
    }
    if error is not None:
        payload["error"] = error[:_ERROR_MAX_LEN]
    try:
        client.table("batch_job_runs").update(payload).eq("id", run_id).execute()
    except Exception as exc:
        logger.warning(
            "[batch_observability] update failed for run %s (status=%s): %s",
            run_id, status, exc,
        )


def _format_error(exc: BaseException) -> str:
    """Format an exception for storage — type + message, no traceback."""
    return f"{type(exc).__name__}: {exc}"
