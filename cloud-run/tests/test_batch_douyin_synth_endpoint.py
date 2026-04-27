"""D3b (2026-06-04) — /batch/douyin-synth endpoint tests.

Targets the FastAPI route handler shape: response envelope, body
parsing, and the 500 fallback. Auth coverage lives in
``test_batch_auth_smoke.py`` (added ``/batch/douyin-synth`` to the
parameterized endpoint list).

Mocks:
  • ``run_douyin_adapt_batch`` — the orchestrator. Real one would call
    Gemini synth + Supabase DB.
  • ``record_job_run`` — observability context manager.
  • ``run_sync`` — the route uses ``run_sync`` to bridge the sync
    orchestrator into the async handler; we patch it to call through
    immediately.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from getviews_pipeline.douyin_adapt_batch import DouyinAdaptBatchSummary

_SECRET = "test-batch-secret-d3b"


@pytest.fixture(scope="module")
def client():  # type: ignore[return]
    try:
        import main as m  # type: ignore[import-not-found]
        with patch.dict(os.environ, {"BATCH_SECRET": _SECRET}):
            yield TestClient(m.app, raise_server_exceptions=False)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Cannot import main: {exc}")


@asynccontextmanager
async def _fake_record_job_run(_client, _job_name):
    payload: dict = {}
    yield payload


async def _passthrough_run_sync(fn, *args, **kwargs):
    """run_sync stub: just call the function synchronously."""
    return fn(*args, **kwargs)


# ── Happy path ──────────────────────────────────────────────────────


def test_endpoint_returns_summary_envelope_on_success(client: TestClient) -> None:
    summary = DouyinAdaptBatchSummary(
        considered=10,
        generated=8,
        failed_synth=1,
        failed_upsert=0,
        skipped_no_title=1,
    )
    with patch(
        "getviews_pipeline.douyin_adapt_batch.run_douyin_adapt_batch",
        return_value=summary,
    ), patch(
        "getviews_pipeline.batch_observability.record_job_run",
        _fake_record_job_run,
    ), patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=MagicMock(),
    ), patch(
        "getviews_pipeline.routers.batch.run_sync",
        new=_passthrough_run_sync,
    ):
        resp = client.post(
            "/batch/douyin-synth",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["considered"] == 10
    assert body["generated"] == 8
    assert body["failed_synth"] == 1
    assert body["failed_upsert"] == 0
    assert body["skipped_no_title"] == 1


def test_endpoint_threads_cap_and_video_ids_to_orchestrator(
    client: TestClient,
) -> None:
    """Body fields land on ``run_douyin_adapt_batch`` kwargs. Catches
    the regression where the route forgets to pass one of cap or
    video_ids through."""
    captured: dict = {}

    def _fake_run(_sb, *, cap, video_ids):
        captured["cap"] = cap
        captured["video_ids"] = video_ids
        return DouyinAdaptBatchSummary()

    with patch(
        "getviews_pipeline.douyin_adapt_batch.run_douyin_adapt_batch",
        side_effect=_fake_run,
    ), patch(
        "getviews_pipeline.batch_observability.record_job_run",
        _fake_record_job_run,
    ), patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=MagicMock(),
    ), patch(
        "getviews_pipeline.routers.batch.run_sync",
        new=_passthrough_run_sync,
    ):
        resp = client.post(
            "/batch/douyin-synth",
            headers={"X-Batch-Secret": _SECRET},
            json={"cap": 25, "video_ids": ["v1", "v2"]},
        )
    assert resp.status_code == 200
    assert captured["cap"] == 25
    assert captured["video_ids"] == ["v1", "v2"]


def test_endpoint_uses_default_cap_when_body_omits_it(client: TestClient) -> None:
    """``DEFAULT_BATCH_CAP`` (100) when cap is None — this is the
    documented daily-cron behaviour."""
    captured: dict = {}

    def _fake_run(_sb, *, cap, video_ids):
        captured["cap"] = cap
        captured["video_ids"] = video_ids
        return DouyinAdaptBatchSummary()

    with patch(
        "getviews_pipeline.douyin_adapt_batch.run_douyin_adapt_batch",
        side_effect=_fake_run,
    ), patch(
        "getviews_pipeline.batch_observability.record_job_run",
        _fake_record_job_run,
    ), patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=MagicMock(),
    ), patch(
        "getviews_pipeline.routers.batch.run_sync",
        new=_passthrough_run_sync,
    ):
        resp = client.post(
            "/batch/douyin-synth",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 200
    assert captured["cap"] == 100
    assert captured["video_ids"] is None


def test_endpoint_rejects_cap_above_500(client: TestClient) -> None:
    """Pydantic ge=1, le=500 on the body — anything outside the range
    returns 422 before reaching the orchestrator."""
    resp = client.post(
        "/batch/douyin-synth",
        headers={"X-Batch-Secret": _SECRET},
        json={"cap": 1000},
    )
    assert resp.status_code == 422


# ── Error path ──────────────────────────────────────────────────────


def test_endpoint_500_on_unexpected_exception(client: TestClient) -> None:
    with patch(
        "getviews_pipeline.douyin_adapt_batch.run_douyin_adapt_batch",
        side_effect=RuntimeError("orchestrator crashed"),
    ), patch(
        "getviews_pipeline.batch_observability.record_job_run",
        _fake_record_job_run,
    ), patch(
        "getviews_pipeline.supabase_client.get_service_client",
        return_value=MagicMock(),
    ), patch(
        "getviews_pipeline.routers.batch.run_sync",
        new=_passthrough_run_sync,
    ):
        resp = client.post(
            "/batch/douyin-synth",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 500
