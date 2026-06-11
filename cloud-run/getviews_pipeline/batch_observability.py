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
from datetime import UTC, datetime, timedelta
from time import perf_counter_ns
from typing import Any

logger = logging.getLogger(__name__)

# Truncate stored error strings so a monster traceback can't blow the
# row size past reasonable. The full traceback is still in Cloud Run
# stdout logs for debugging.
_ERROR_MAX_LEN = 5000

# Audit Pass-3 fix #1 — concurrency guard window. A run still marked
# ``running`` and started within this window blocks a new run with
# the same ``job_name``. Wide enough to cover the longest legitimate
# batch (``/batch/pattern-decks`` cap is 20-min Gemini × 60 patterns
# ≈ 12 min in practice; we add headroom). Stuck rows older than this
# are treated as "probably crashed" and don't block.
_CONCURRENT_RUN_WINDOW_MIN = 30

# Cloud Run batch pod timeout is 3600s; rows orphaned by a hard kill stay
# ``running`` forever unless swept. cron-batch-job-runs-stale-sweeper
# closes anything older than this threshold.
STALE_RUNNING_SWEEP_MIN = 65


def is_swept_stale_batch_job_run(row: dict[str, Any]) -> bool:
    """True for timeout orphans closed by ``sweep_stale_*`` — not real pipeline failures."""
    summary = row.get("summary")
    if isinstance(summary, dict) and summary.get("swept_stale_running"):
        return True
    err = row.get("error") or ""
    return str(err).startswith("auto-swept:")


class BatchAlreadyRunning(Exception):
    """A previous ``/batch/{job_name}`` run is still marked ``running``.

    Cloud Run min:0 single-instance assumption usually prevents overlap,
    but pg_cron retries after pod-restart can race. Defensive raise.

    To bypass when a previous run is genuinely stuck (e.g., pod killed
    mid-execution), mark the offending ``batch_job_runs`` row as
    ``status='failed'`` manually — the next cron tick will then pass.
    """


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

    Audit Pass-3 fix #1 — refuses to start a second run for the same
    ``job_name`` while a previous run is still ``status='running'``
    (and started < ``_CONCURRENT_RUN_WINDOW_MIN`` minutes ago).
    Raises ``BatchAlreadyRunning``; caller's ``except Exception`` will
    surface it as a 500 to pg_cron.
    """
    _check_no_active_run(client, job_name)
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


def _check_no_active_run(client: Any, job_name: str) -> None:
    """Raise ``BatchAlreadyRunning`` if a recent run for ``job_name``
    is still marked ``status='running'``. Best-effort — fails open on
    DB errors (better to over-run a job than miss a cron entirely)."""
    try:
        cutoff = (
            datetime.now(UTC) - timedelta(minutes=_CONCURRENT_RUN_WINDOW_MIN)
        ).isoformat()
        active = (
            client.table("batch_job_runs")
            .select("id, started_at")
            .eq("job_name", job_name)
            .eq("status", "running")
            .gte("started_at", cutoff)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "[batch_observability] concurrency check failed for %s: %s — proceeding",
            job_name, exc,
        )
        return
    if active.data:
        existing = active.data[0]
        logger.warning(
            "[batch_observability] %s overlap: refusing to start "
            "(existing id=%s started_at=%s)",
            job_name, existing.get("id"), existing.get("started_at"),
        )
        raise BatchAlreadyRunning(
            f"{job_name} already running (id={existing.get('id')})",
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


def sweep_stale_running_job_runs(
    client: Any,
    *,
    stale_after_min: int = STALE_RUNNING_SWEEP_MIN,
    job_names: list[str] | None = None,
) -> int:
    """Close ``batch_job_runs`` rows stuck in ``running`` after Cloud Run timeout.

    Typical orphan: batch pod killed at 3600s before ``record_job_run`` finalizes
    (shift B/C ingest). Marks ``status='failed'`` with ``aborted_early`` in summary.

    Returns the number of rows updated. Best-effort — never raises.
    """
    cutoff = (datetime.now(UTC) - timedelta(minutes=stale_after_min)).isoformat()
    try:
        query = (
            client.table("batch_job_runs")
            .select("id, job_name, started_at, summary")
            .eq("status", "running")
            .lt("started_at", cutoff)
        )
        if job_names:
            query = query.in_("job_name", job_names)
        resp = query.execute()
    except Exception as exc:
        logger.warning("[batch_observability] stale-run select failed: %s", exc)
        return 0

    rows = resp.data or []
    swept = 0
    for row in rows:
        run_id = row.get("id")
        if not run_id:
            continue
        started_at = row.get("started_at")
        summary = dict(row.get("summary") or {})
        summary.update({
            "aborted_early": True,
            "swept_stale_running": True,
        })
        if started_at:
            try:
                started_dt = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
                duration_ms = int(
                    max(0, (datetime.now(UTC) - started_dt).total_seconds() * 1000),
                )
            except (TypeError, ValueError):
                duration_ms = stale_after_min * 60 * 1000
        else:
            duration_ms = stale_after_min * 60 * 1000
        payload: dict[str, Any] = {
            "finished_at": datetime.now(UTC).isoformat(),
            "status": "failed",
            "duration_ms": duration_ms,
            "summary": summary,
            "error": (
                f"auto-swept: still running >{stale_after_min}m "
                f"(likely Cloud Run 3600s timeout orphan)"
            )[:_ERROR_MAX_LEN],
        }
        try:
            client.table("batch_job_runs").update(payload).eq("id", run_id).execute()
            swept += 1
            logger.warning(
                "[batch_observability] swept stale run id=%s job=%s started_at=%s",
                run_id, row.get("job_name"), started_at,
            )
        except Exception as exc:
            logger.warning(
                "[batch_observability] stale-run update failed for %s: %s", run_id, exc,
            )
    return swept
