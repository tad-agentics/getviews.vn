"""Unit tests for ``_evaluate_cron_batch_failures`` alert evaluator.

Pins three behaviours:
  1. Zero failures in window → not breached, cleared message.
  2. One or more failures in window → breached, message includes
     per-job breakdown.
  3. Supabase query failure → returns (False, error_msg, context)
     gracefully, not an exception (matches sibling evaluators'
     error-isolation pattern).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch


def _mock_client_returning(rows: list[dict[str, Any]]) -> MagicMock:
    """Build a Supabase mock that returns ``rows`` from the chain:
    ``client.table(...).select(...).eq(...).gte(...).order(...).limit(...).execute()``.
    """
    client = MagicMock()
    chain = client.table.return_value.select.return_value
    chain = chain.eq.return_value.gte.return_value.order.return_value.limit.return_value
    chain.execute.return_value = MagicMock(data=rows)
    return client


def _run(rule: dict[str, Any], client: MagicMock) -> tuple[bool, str, dict[str, Any]]:
    """Helper — call the evaluator with the given mock client."""
    from getviews_pipeline.routers.admin import _evaluate_cron_batch_failures
    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=client,
    ):
        return _evaluate_cron_batch_failures(rule)


def test_zero_failures_is_not_breached() -> None:
    rule = {"threshold_json": {"failures_max": 0, "window_days": 7}}
    client = _mock_client_returning([])

    breached, msg, ctx = _run(rule, client)

    assert breached is False
    assert "0 failures" in msg
    assert ctx["failures"] == 0
    assert ctx["window_days"] == 7
    assert ctx["by_job"] == {}


def test_single_failure_is_breached() -> None:
    """Threshold is failures_max=0, so even 1 fails. Rare enough to page."""
    rule = {"threshold_json": {"failures_max": 0, "window_days": 7}}
    client = _mock_client_returning([
        {
            "job_name": "batch/ingest",
            "error": "EnsembleDailyBudgetExceeded: quota hit",
            "started_at": "2026-05-10T03:00:00Z",
        },
    ])

    breached, msg, ctx = _run(rule, client)

    assert breached is True
    assert ctx["failures"] == 1
    assert ctx["by_job"] == {"batch/ingest": 1}
    assert "EnsembleDailyBudget" in (ctx["latest_error"] or "")
    assert "batch/ingest×1" in msg


def test_multiple_failures_groups_by_job() -> None:
    """Breakdown surfaces which job is repeat-failing vs mixed."""
    rule = {"threshold_json": {"failures_max": 0, "window_days": 7}}
    client = _mock_client_returning([
        {"job_name": "batch/ingest", "error": "foo", "started_at": "2026-05-10T03:00:00Z"},
        {"job_name": "batch/ingest", "error": "foo", "started_at": "2026-05-09T03:00:00Z"},
        {"job_name": "batch/refresh", "error": "bar", "started_at": "2026-05-08T05:30:00Z"},
    ])

    breached, msg, ctx = _run(rule, client)

    assert breached is True
    assert ctx["by_job"] == {"batch/ingest": 2, "batch/refresh": 1}
    assert "batch/ingest×2" in msg
    assert "batch/refresh×1" in msg


def test_query_failure_is_non_breaching() -> None:
    """Supabase down shouldn't cascade into a false-positive alert fire."""
    rule = {"threshold_json": {"failures_max": 0, "window_days": 7}}
    client = MagicMock()
    chain = client.table.return_value.select.return_value
    chain = chain.eq.return_value.gte.return_value.order.return_value.limit.return_value
    chain.execute.side_effect = RuntimeError("supabase down")

    breached, msg, ctx = _run(rule, client)

    assert breached is False
    assert "query failed" in msg
    assert ctx.get("reason") == "query_error"


def test_custom_failures_max_respected() -> None:
    """Operator can raise threshold if the alert turns noisy."""
    rule = {"threshold_json": {"failures_max": 3, "window_days": 7}}
    client = _mock_client_returning([
        {"job_name": "batch/ingest", "error": "x", "started_at": "2026-05-10T03:00:00Z"},
        {"job_name": "batch/ingest", "error": "x", "started_at": "2026-05-09T03:00:00Z"},
        {"job_name": "batch/ingest", "error": "x", "started_at": "2026-05-08T03:00:00Z"},
    ])
    # 3 failures, threshold 3 — not breached (strict >).
    breached, _, _ = _run(rule, client)
    assert breached is False
