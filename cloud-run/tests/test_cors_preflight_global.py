"""Regression — global CORS wrap must answer OPTIONS for cross-origin GETs.

Production user pod (2026-06-14): every OPTIONS preflight returned 500, so
getviews.vn showed ``Failed to fetch`` on Home daily ritual + empty sidebar
(answer session list). Root cause: ``add_middleware(CORSMiddleware)`` sits
inside Starlette's ``ServerErrorMiddleware``; wrapping the finished FastAPI
``api`` as the outermost ASGI ``app`` fixes preflight on Cloud Run.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def asgi_app():  # type: ignore[return]
    if "main" not in sys.modules:
        importlib.import_module("main")
    from main import app  # type: ignore[import-not-found]

    return app


@pytest.fixture
def client(asgi_app: Any) -> TestClient:
    return TestClient(asgi_app, raise_server_exceptions=True)


@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/home/daily-ritual",
        "/answer/sessions",
    ],
)
def test_get_preflight_returns_200(client: TestClient, path: str) -> None:
    res = client.options(
        path,
        headers={
            "Origin": "https://getviews.vn",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert res.status_code == 200, res.text
    assert res.headers.get("access-control-allow-origin") == "https://getviews.vn"
    allowed = res.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allowed


def test_get_preflight_with_private_network_header(client: TestClient) -> None:
    """Chrome may send PNA on some cross-origin fetches — must not 500."""
    res = client.options(
        "/health",
        headers={
            "Origin": "https://getviews.vn",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
            "Access-Control-Request-Private-Network": "true",
        },
    )
    # Public Cloud Run does not enable private-network access; 400 is fine — 500 was the prod bug.
    assert res.status_code in (200, 400), res.text


def test_wrapped_app_is_cors_middleware(asgi_app: Any) -> None:
    from starlette.middleware.cors import CORSMiddleware

    assert isinstance(asgi_app, CORSMiddleware)
