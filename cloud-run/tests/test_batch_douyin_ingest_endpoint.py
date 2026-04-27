"""D2d (2026-06-03) — /batch/douyin-ingest endpoint tests.

Targets the FastAPI route handler shape: response envelope, body
parsing, EnsembleData budget exhaustion → 503, and arbitrary Exception
→ 500. Auth coverage lives in ``test_batch_auth_smoke.py`` (added
``/batch/douyin-ingest`` to the parameterized endpoint list).

Mocks:
  • ``run_douyin_batch_ingest`` — the orchestrator. Real one would
    hit ED + Gemini + Supabase.
  • ``record_job_run`` — the observability context manager. We replace
    it with a simple async-cm stub that yields a mutable dict so the
    handler can write into it.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from getviews_pipeline.douyin_ingest import DouyinBatchSummary

_SECRET = "test-batch-secret-d2d"


@pytest.fixture(scope="module")
def client():  # type: ignore[return]
    try:
        import main as m  # type: ignore[import-not-found]
        with patch.dict(os.environ, {"BATCH_SECRET": _SECRET}):
            yield TestClient(m.app, raise_server_exceptions=False)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Cannot import main: {exc}")


# ── Stub for record_job_run async-cm ────────────────────────────────


@asynccontextmanager
async def _fake_record_job_run(_client, _job_name):
    """Yields a mutable dict the handler writes summary fields into.
    Mirrors the real ``record_job_run`` shape just enough."""
    payload: dict = {}
    yield payload


# ── Happy path ──────────────────────────────────────────────────────


def test_endpoint_returns_summary_envelope_on_success(client: TestClient) -> None:
    summary = DouyinBatchSummary(
        total_inserted=4,
        total_skipped=2,
        total_failed=0,
        niches_processed=2,
        niche_results=[
            {"niche_id": 1, "slug": "wellness", "inserted": 3},
            {"niche_id": 2, "slug": "tech", "inserted": 1},
        ],
    )
    with patch(
        "getviews_pipeline.douyin_ingest.run_douyin_batch_ingest",
        new=AsyncMock(return_value=summary),
    ), patch(
        "getviews_pipeline.batch_observability.record_job_run",
        _fake_record_job_run,
    ), patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=MagicMock(),
    ):
        resp = client.post(
            "/batch/douyin-ingest",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["total_inserted"] == 4
    assert body["total_skipped"] == 2
    assert body["total_failed"] == 0
    assert body["niches_processed"] == 2
    assert len(body["niche_results"]) == 2


def test_endpoint_passes_niche_ids_and_deep_through_to_orchestrator(
    client: TestClient,
) -> None:
    """Body fields land on the run_douyin_batch_ingest call kwargs.
    Catches the regression where the route forgets to thread one of the
    request fields through."""
    captured: dict = {}

    async def _fake_run(*, niche_ids=None, deep=False):
        captured["niche_ids"] = niche_ids
        captured["deep"] = deep
        return DouyinBatchSummary()

    with patch(
        "getviews_pipeline.douyin_ingest.run_douyin_batch_ingest",
        new=AsyncMock(side_effect=_fake_run),
    ), patch(
        "getviews_pipeline.batch_observability.record_job_run",
        _fake_record_job_run,
    ), patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=MagicMock(),
    ):
        resp = client.post(
            "/batch/douyin-ingest",
            headers={"X-Batch-Secret": _SECRET},
            json={"niche_ids": [2, 6], "deep": True},
        )
    assert resp.status_code == 200
    assert captured["niche_ids"] == [2, 6]
    assert captured["deep"] is True


def test_endpoint_defaults_when_body_omitted(client: TestClient) -> None:
    """POST with empty body should still work — niche_ids=None + deep=False
    are the documented defaults."""
    captured: dict = {}

    async def _fake_run(*, niche_ids=None, deep=False):
        captured["niche_ids"] = niche_ids
        captured["deep"] = deep
        return DouyinBatchSummary()

    with patch(
        "getviews_pipeline.douyin_ingest.run_douyin_batch_ingest",
        new=AsyncMock(side_effect=_fake_run),
    ), patch(
        "getviews_pipeline.batch_observability.record_job_run",
        _fake_record_job_run,
    ), patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=MagicMock(),
    ):
        resp = client.post(
            "/batch/douyin-ingest",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 200
    assert captured["niche_ids"] is None
    assert captured["deep"] is False


# ── Error paths ─────────────────────────────────────────────────────


def test_endpoint_503_on_ensemble_budget_exceeded(client: TestClient) -> None:
    """ED daily-budget exhaustion returns 503 (Service Unavailable) so
    the cron retries / alerts on next day cleanly. Mirrors VN
    ``/batch/ingest``'s behaviour."""
    from getviews_pipeline.ensemble import EnsembleDailyBudgetExceeded

    with patch(
        "getviews_pipeline.douyin_ingest.run_douyin_batch_ingest",
        new=AsyncMock(side_effect=EnsembleDailyBudgetExceeded("daily ED cap")),
    ), patch(
        "getviews_pipeline.batch_observability.record_job_run",
        _fake_record_job_run,
    ), patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=MagicMock(),
    ):
        resp = client.post(
            "/batch/douyin-ingest",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 503


def test_endpoint_500_on_unexpected_exception(client: TestClient) -> None:
    """Any other Exception bubbles up as 500 (visible in pg_cron failure
    log + Cloud Run access logs)."""
    with patch(
        "getviews_pipeline.douyin_ingest.run_douyin_batch_ingest",
        new=AsyncMock(side_effect=RuntimeError("orchestrator crashed")),
    ), patch(
        "getviews_pipeline.batch_observability.record_job_run",
        _fake_record_job_run,
    ), patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=MagicMock(),
    ):
        resp = client.post(
            "/batch/douyin-ingest",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 500
