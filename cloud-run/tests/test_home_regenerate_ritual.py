"""Tests for POST /home/regenerate-ritual.

Background context: PR2 of the single-niche refactor (2026-05-05). The
endpoint queues a ritual regeneration for the caller's current niche so the
Settings → niche change flow can show fresh Home content without waiting for
the nightly morning-ritual cron. 202 + queued, polling via GET
/home/daily-ritual.

Tests run with FastAPI TestClient + dependency_overrides — same pattern as
``test_answer_endpoints_integration.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Allow ``import main`` from cloud-run/ same as the integration suite.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# -- Fake Supabase --------------------------------------------------------

class _Exec:
    def __init__(self, data: Any) -> None:
        self.data = data


class _Query:
    def __init__(self, table_name: str, store: dict[str, Any]) -> None:
        self._table = table_name
        self._store = store
        self._eq_filter: tuple[str, Any] | None = None

    def select(self, *_: Any, **__: Any) -> "_Query":
        return self

    def eq(self, col: str, val: Any) -> "_Query":
        self._eq_filter = (col, val)
        return self

    def single(self) -> "_Query":
        return self

    def execute(self) -> _Exec:
        return _Exec(self._store.get(self._table))


class _FakeSupabase:
    def __init__(self, table_data: dict[str, Any] | None = None) -> None:
        self._store: dict[str, Any] = table_data or {}

    def table(self, name: str) -> _Query:
        return _Query(name, self._store)


# -- Fixtures -------------------------------------------------------------


@pytest.fixture
def fresh_inflight() -> Any:
    """Reset the module-level in-flight set between tests."""
    from getviews_pipeline.routers import home as home_router

    home_router._REGEN_INFLIGHT.clear()
    yield home_router._REGEN_INFLIGHT
    home_router._REGEN_INFLIGHT.clear()


@pytest.fixture
def client_with_user() -> TestClient:
    from main import app  # type: ignore[import-not-found]
    from getviews_pipeline.deps import require_user

    async def _fake_user() -> dict[str, Any]:
        return {
            "user_id": "00000000-0000-0000-0000-0000000000aa",
            "payload": {"sub": "00000000-0000-0000-0000-0000000000aa"},
            "access_token": "fake-token",
        }

    app.dependency_overrides[require_user] = _fake_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(require_user, None)


# -- Tests ----------------------------------------------------------------


def test_returns_202_queued_when_profile_has_niche(
    client_with_user: TestClient, fresh_inflight: set[str]
) -> None:
    fake = _FakeSupabase({"profiles": {"primary_niche": 7}})
    with patch(
        "getviews_pipeline.supabase_client.user_supabase", return_value=fake
    ), patch(
        "getviews_pipeline.routers.home._run_regen_ritual"
    ) as run_mock:
        r = client_with_user.post("/home/regenerate-ritual")

    assert r.status_code == 202
    body = r.json()
    assert body == {"status": "queued", "niche_id": 7}
    # Background task scheduled with the resolved niche.
    run_mock.assert_called_once_with("00000000-0000-0000-0000-0000000000aa", 7)
    # In-flight tracker now contains the user — until the bg task drains it
    # (which the patched _run_regen_ritual never reaches).
    assert "00000000-0000-0000-0000-0000000000aa" in fresh_inflight


def test_returns_202_already_in_flight_when_duplicate(
    client_with_user: TestClient, fresh_inflight: set[str]
) -> None:
    fresh_inflight.add("00000000-0000-0000-0000-0000000000aa")
    with patch(
        "getviews_pipeline.routers.home._run_regen_ritual"
    ) as run_mock:
        r = client_with_user.post("/home/regenerate-ritual")

    assert r.status_code == 202
    assert r.json() == {"status": "already_in_flight"}
    # Must NOT enqueue a second background task.
    run_mock.assert_not_called()


def test_returns_404_when_profile_has_no_niche(
    client_with_user: TestClient, fresh_inflight: set[str]
) -> None:
    fake = _FakeSupabase({"profiles": {"primary_niche": None}})
    with patch(
        "getviews_pipeline.supabase_client.user_supabase", return_value=fake
    ), patch(
        "getviews_pipeline.routers.home._run_regen_ritual"
    ) as run_mock:
        r = client_with_user.post("/home/regenerate-ritual")

    assert r.status_code == 404
    # Pre-onboarding profiles should never reach a regen — the layout guard
    # bounces them to /app/onboarding before they can hit Settings.
    run_mock.assert_not_called()
    assert len(fresh_inflight) == 0
