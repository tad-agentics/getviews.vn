"""Unit tests for ``_evaluate_pg_net_batch_http_4xx`` alert evaluator."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch


def _mock_client_rpc(rows: list[dict[str, Any]]) -> MagicMock:
    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(data=rows)
    return client


def _run(rule: dict[str, Any], client: MagicMock) -> tuple[bool, str, dict[str, Any]]:
    from getviews_pipeline.routers.admin import _evaluate_pg_net_batch_http_4xx

    with patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=client,
    ):
        return _evaluate_pg_net_batch_http_4xx(rule)


def test_zero_4xx_is_not_breached() -> None:
    rule = {"threshold_json": {"max_4xx": 0, "hours": 6}}
    breached, msg, ctx = _run(rule, _mock_client_rpc([]))
    assert breached is False
    assert ctx["count_4xx"] == 0
    assert "ok" in msg


def test_one_4xx_is_breached() -> None:
    rule = {"threshold_json": {"max_4xx": 0, "hours": 6}}
    rows = [
        {
            "response_id": 1,
            "status_code": 404,
            "created_at": "2026-05-10T12:00:00Z",
            "request_url": "https://batch.example.run.app/batch/ingest",
        },
    ]
    breached, msg, ctx = _run(rule, _mock_client_rpc(rows))
    assert breached is True
    assert ctx["count_4xx"] == 1
    assert "404" in msg


def test_rpc_failure_is_non_breaching() -> None:
    rule = {"threshold_json": {"max_4xx": 0, "hours": 6}}
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = RuntimeError("rpc down")
    breached, msg, ctx = _run(rule, client)
    assert breached is False
    assert "query failed" in msg
    assert ctx.get("reason") == "query_error"
