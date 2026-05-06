"""JWKS fetch resilience — stale-while-revalidate (ISSUE-016 / deploy blips)."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

import getviews_pipeline.deps as deps


@pytest.fixture(autouse=True)
def reset_jwks_globals() -> None:
    deps._jwks_cache = {}
    deps._jwks_fetched_at = 0.0
    yield
    deps._jwks_cache = {}
    deps._jwks_fetched_at = 0.0


def _good_response() -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.raise_for_status = MagicMock()
    r.json = MagicMock(return_value={"keys": [{"kid": "k1", "kty": "EC"}]})
    return r


@pytest.mark.asyncio
async def test_jwks_initial_fetch_populates_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "SUPABASE_JWKS_URL", "https://proj.supabase.co/auth/v1/.well-known/jwks.json")
    good = _good_response()
    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = None
    fake_client.get = AsyncMock(return_value=good)

    with patch.object(deps.httpx, "AsyncClient", return_value=fake_client):
        out = await deps._get_jwks()

    assert out["keys"]
    fake_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_jwks_initial_fetch_failure_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "SUPABASE_JWKS_URL", "https://proj.supabase.co/auth/v1/.well-known/jwks.json")
    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = None
    fake_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

    with patch.object(deps.httpx, "AsyncClient", return_value=fake_client):
        with pytest.raises(HTTPException) as ei:
            await deps._get_jwks()
    assert ei.value.status_code == 503
    assert ei.value.detail == "jwks_fetch_failed"


@pytest.mark.asyncio
async def test_jwks_stale_served_when_refresh_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "SUPABASE_JWKS_URL", "https://proj.supabase.co/auth/v1/.well-known/jwks.json")
    stale: dict[str, Any] = {"keys": [{"kid": "old"}]}
    deps._jwks_cache = stale
    deps._jwks_fetched_at = time.monotonic() - 9999.0

    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = None
    fake_client.get = AsyncMock(side_effect=httpx.TimeoutException("slow"))

    with patch.object(deps.httpx, "AsyncClient", return_value=fake_client):
        out = await deps._get_jwks()

    assert out is stale
    fake_client.get.assert_called_once()
