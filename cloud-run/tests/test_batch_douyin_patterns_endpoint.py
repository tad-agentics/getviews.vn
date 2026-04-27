"""D5c (2026-06-05) — /batch/douyin-patterns endpoint tests.

Mirrors the D3b /batch/douyin-synth endpoint test taxonomy: response
envelope, body parsing, validation, and the 500 fallback. Auth coverage
lives in ``test_batch_auth_smoke.py``.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from getviews_pipeline.douyin_patterns_batch import DouyinPatternsBatchSummary

_SECRET = "test-batch-secret-d5c"


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
    return fn(*args, **kwargs)


# ── Happy path ──────────────────────────────────────────────────────


def test_endpoint_returns_summary_envelope_on_success(client: TestClient) -> None:
    summary = DouyinPatternsBatchSummary(
        considered_niches=10,
        written_rows=27,
        skipped_fresh=1,
        skipped_thin_pool=0,
        failed_synth=0,
        failed_upsert=0,
        week_of="2026-06-01",
    )
    with patch(
        "getviews_pipeline.douyin_patterns_batch.run_douyin_patterns_batch",
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
            "/batch/douyin-patterns",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["week_of"] == "2026-06-01"
    assert body["considered_niches"] == 10
    assert body["written_rows"] == 27
    assert body["skipped_fresh"] == 1
    assert body["skipped_thin_pool"] == 0
    assert body["failed_synth"] == 0
    assert body["failed_upsert"] == 0


def test_endpoint_threads_niche_ids_pool_size_force_to_orchestrator(
    client: TestClient,
) -> None:
    captured: dict = {}

    def _fake_run(_sb, *, niche_ids, pool_size, force):
        captured["niche_ids"] = niche_ids
        captured["pool_size"] = pool_size
        captured["force"] = force
        return DouyinPatternsBatchSummary(week_of="2026-06-01")

    with patch(
        "getviews_pipeline.douyin_patterns_batch.run_douyin_patterns_batch",
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
            "/batch/douyin-patterns",
            headers={"X-Batch-Secret": _SECRET},
            json={"niche_ids": [1, 2], "pool_size": 50, "force": True},
        )
    assert resp.status_code == 200
    assert captured["niche_ids"] == [1, 2]
    assert captured["pool_size"] == 50
    assert captured["force"] is True


def test_endpoint_uses_default_pool_size_when_body_omits_it(
    client: TestClient,
) -> None:
    captured: dict = {}

    def _fake_run(_sb, *, niche_ids, pool_size, force):
        captured["pool_size"] = pool_size
        captured["force"] = force
        return DouyinPatternsBatchSummary(week_of="2026-06-01")

    with patch(
        "getviews_pipeline.douyin_patterns_batch.run_douyin_patterns_batch",
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
            "/batch/douyin-patterns",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 200
    assert captured["pool_size"] == 30  # DEFAULT_POOL_PER_NICHE
    assert captured["force"] is False


def test_endpoint_rejects_pool_size_above_100(client: TestClient) -> None:
    """Pydantic ge=6, le=100 — anything outside returns 422."""
    resp = client.post(
        "/batch/douyin-patterns",
        headers={"X-Batch-Secret": _SECRET},
        json={"pool_size": 500},
    )
    assert resp.status_code == 422


def test_endpoint_rejects_pool_size_below_6(client: TestClient) -> None:
    resp = client.post(
        "/batch/douyin-patterns",
        headers={"X-Batch-Secret": _SECRET},
        json={"pool_size": 1},
    )
    assert resp.status_code == 422


# ── Error path ──────────────────────────────────────────────────────


def test_endpoint_500_on_unexpected_exception(client: TestClient) -> None:
    with patch(
        "getviews_pipeline.douyin_patterns_batch.run_douyin_patterns_batch",
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
            "/batch/douyin-patterns",
            headers={"X-Batch-Secret": _SECRET},
            json={},
        )
    assert resp.status_code == 500
