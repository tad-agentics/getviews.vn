"""Unit tests for ``batch_proxy`` — forward cron calls from user service to batch origin."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from getviews_pipeline.routers.batch_proxy import router

_SECRET = "test-proxy-secret"


@pytest.fixture
def proxy_app() -> FastAPI:
    a = FastAPI()
    a.include_router(router)
    return a


def test_morning_ritual_503_when_batch_base_unset(
    proxy_app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BATCH_SERVICE_BASE_URL", raising=False)
    monkeypatch.setenv("BATCH_SECRET", _SECRET)
    c = TestClient(proxy_app, raise_server_exceptions=False)
    r = c.post(
        "/batch/morning-ritual",
        json={},
        headers={"X-Batch-Secret": _SECRET},
    )
    assert r.status_code == 503
    assert "batch_service_base_url_unset" in (r.json().get("detail") or "")


@patch("getviews_pipeline.routers.batch_proxy.httpx.AsyncClient")
def test_morning_ritual_forwards_to_batch(
    mock_ac: MagicMock,
    proxy_app: FastAPI,
) -> None:
    inner = MagicMock()
    inner.post = AsyncMock(
        return_value=Response(200, json={"ok": True, "generated": 2}),
    )
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=None)
    mock_ac.return_value = cm

    with patch.dict(
        os.environ,
        {
            "BATCH_SECRET": _SECRET,
            "BATCH_SERVICE_BASE_URL": "https://batch-unit.test",
        },
        clear=False,
    ):
        c = TestClient(proxy_app, raise_server_exceptions=False)
        r = c.post(
            "/batch/morning-ritual",
            json={},
            headers={"X-Batch-Secret": _SECRET},
        )

    assert r.status_code == 200
    assert r.json() == {"ok": True, "generated": 2}
    inner.post.assert_called_once()
    posargs, _kwargs = inner.post.call_args
    assert posargs[0] == "https://batch-unit.test/batch/morning-ritual"
