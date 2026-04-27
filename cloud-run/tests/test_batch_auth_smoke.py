"""Phase 0.3 — Batch endpoint auth behaviour smoke tests.

Verifies that batch routes correctly gate access:
  - No auth → 401
  - Wrong secret → 401
  - Correct secret → not-401 (may 500/503 due to missing deps, but auth passes)

Uses FastAPI's TestClient so no real network calls occur.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_SECRET = "test-batch-secret-smoke"

_BATCH_ENDPOINTS: list[tuple[str, str]] = [
    ("POST", "/batch/ingest"),
    ("POST", "/batch/douyin-ingest"),  # D2d (2026-06-03)
    ("POST", "/batch/douyin-synth"),   # D3b (2026-06-04)
    ("POST", "/batch/reingest-videos"),
    ("POST", "/batch/refresh"),
    ("POST", "/batch/reclassify-format"),
    ("POST", "/batch/backfill-thumbnails"),
    ("POST", "/batch/analytics"),
    ("POST", "/batch/layer0"),
    ("POST", "/batch/morning-ritual"),
    ("POST", "/batch/scene-intelligence"),
    ("POST", "/admin/evaluate-alerts"),
]


@pytest.fixture(scope="module")
def client():  # type: ignore[return]
    try:
        import main as m  # type: ignore[import-not-found]
        with patch.dict(os.environ, {"BATCH_SECRET": _SECRET}):
            yield TestClient(m.app, raise_server_exceptions=False)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Cannot import main: {exc}")


@pytest.mark.parametrize("method,path", _BATCH_ENDPOINTS)
def test_batch_endpoint_requires_auth(client: TestClient, method: str, path: str) -> None:
    """Without any auth header the endpoint must return 401, not 200/5xx."""
    fn = getattr(client, method.lower())
    resp = fn(path, json={})
    assert resp.status_code == 401, (
        f"{method} {path}: expected 401, got {resp.status_code}. "
        "Batch endpoint may be missing the require_batch_caller dependency."
    )


@pytest.mark.parametrize("method,path", _BATCH_ENDPOINTS)
def test_batch_endpoint_rejects_wrong_secret(client: TestClient, method: str, path: str) -> None:
    """A wrong X-Batch-Secret must also return 401."""
    fn = getattr(client, method.lower())
    resp = fn(path, json={}, headers={"X-Batch-Secret": "wrong-secret"})
    assert resp.status_code == 401, (
        f"{method} {path}: expected 401 on wrong secret, got {resp.status_code}."
    )


@pytest.mark.parametrize("method,path", _BATCH_ENDPOINTS)
def test_batch_endpoint_passes_with_correct_secret(
    client: TestClient, method: str, path: str
) -> None:
    """Correct X-Batch-Secret must NOT return 401.

    The endpoint may still 422/500/503 because downstream deps (Supabase, Gemini)
    aren't available in tests, but the auth layer itself must pass.
    """
    fn = getattr(client, method.lower())
    resp = fn(
        path,
        json={"items": [{"video_id": "1", "niche_id": 1}]} if path == "/batch/reingest-videos" else {},
        headers={"X-Batch-Secret": _SECRET},
    )
    assert resp.status_code != 401, (
        f"{method} {path}: got 401 even with correct batch secret. "
        "Check require_batch_caller logic."
    )
