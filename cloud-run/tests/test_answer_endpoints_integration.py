"""FastAPI route-level integration tests for ``/answer/*``.

Why this file exists: the /answer/sessions endpoint has had unit coverage for
``create_session`` (C.1.2) but no test that exercises the HTTP boundary —
CORS preflight, Pydantic body validation, ``require_user`` dependency, the
``run_sync`` wrapper, and the 500-wrapping try/except in the handler.

When the DB logs showed 14 ``studio_composer_submit`` events with 0 rows in
``answer_sessions``, every failure hypothesis pointed at the request-handling
chain rather than the business function. A TestClient round-trip proves the
endpoint works (or exposes exactly where it breaks) without requiring a
Cloud Run deploy.

We override ``require_user`` via FastAPI's ``dependency_overrides`` — the
same pattern FastAPI's docs recommend for auth in tests. Supabase clients
are patched so ``answer_session.create_session`` runs its real logic against
an in-memory fake.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class _FakeSupabaseChain:
    """Enough of the supabase-py chain to back create_session / list / patch."""

    def __init__(self, store: dict[str, list[dict[str, Any]]], table_name: str) -> None:
        self._store = store
        self._table = table_name
        self._filters: list[tuple[str, str, Any]] = []
        self._op: str = "select"
        self._payload: Any = None
        self._single = False
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None

    def select(self, *_cols: str) -> _FakeSupabaseChain:
        self._op = "select"
        return self

    def insert(self, payload: Any) -> _FakeSupabaseChain:
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload: Any) -> _FakeSupabaseChain:
        self._op = "update"
        self._payload = payload
        return self

    def delete(self) -> _FakeSupabaseChain:
        self._op = "delete"
        return self

    def eq(self, col: str, val: Any) -> _FakeSupabaseChain:
        self._filters.append(("eq", col, val))
        return self

    def is_(self, col: str, val: Any) -> _FakeSupabaseChain:
        self._filters.append(("is", col, val))
        return self

    def gte(self, col: str, val: Any) -> _FakeSupabaseChain:
        self._filters.append(("gte", col, val))
        return self

    def lt(self, col: str, val: Any) -> _FakeSupabaseChain:
        self._filters.append(("lt", col, val))
        return self

    def order(self, col: str, desc: bool = False) -> _FakeSupabaseChain:
        self._order = (col, desc)
        return self

    def limit(self, n: int) -> _FakeSupabaseChain:
        self._limit = n
        return self

    def single(self) -> _FakeSupabaseChain:
        self._single = True
        return self

    def _matches(self, row: dict[str, Any]) -> bool:
        for op, col, val in self._filters:
            if op == "eq" and row.get(col) != val:
                return False
            if op == "is" and val == "null" and row.get(col) is not None:
                return False
        return True

    def execute(self) -> MagicMock:
        rows = self._store.setdefault(self._table, [])
        if self._op == "insert":
            import uuid as _uuid
            from datetime import datetime

            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for p in payloads:
                row = dict(p)
                row.setdefault("id", str(_uuid.uuid4()))
                row.setdefault("created_at", datetime.now(UTC).isoformat())
                row.setdefault("updated_at", datetime.now(UTC).isoformat())
                row.setdefault("archived_at", None)
                rows.append(row)
                inserted.append(row)
            return MagicMock(data=inserted)
        matched = [r for r in rows if self._matches(r)]
        if self._op == "select":
            if self._single:
                return MagicMock(data=matched[0] if matched else None)
            return MagicMock(data=matched)
        if self._op == "update":
            for r in matched:
                r.update(self._payload or {})
            return MagicMock(data=matched)
        if self._op == "delete":
            for r in matched:
                rows.remove(r)
            return MagicMock(data=matched)
        return MagicMock(data=[])


class _FakeSupabase:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str) -> _FakeSupabaseChain:
        return _FakeSupabaseChain(self._store, name)


@pytest.fixture
def client_with_user() -> TestClient:
    from cloud_run_main import app  # type: ignore  # noqa: F401
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


# -----------------------------------------------------------------------------
# The ``main`` module is at cloud-run/main.py, not on the package path — tests
# run from cloud-run/ so we can import it as ``main``. We alias to a module
# name Python can actually find: ``main.py`` is on sys.path because pytest runs
# from ``cloud-run/`` (see pyproject ``testpaths = ["tests"]``, rootdir is
# ``cloud-run``).
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fake_service_client() -> Any:
    fake = _FakeSupabase()
    with patch("getviews_pipeline.answer_session.get_service_client", return_value=fake):
        yield fake


@pytest.fixture(autouse=True)
def _import_alias() -> None:
    """Allow ``from cloud_run_main import app`` inside the client fixture.

    main.py is the Cloud Run entry; we re-expose it as ``cloud_run_main`` so
    tests can import the FastAPI app cleanly without colliding with ``main``
    from other packages.
    """
    import importlib
    import sys

    if "cloud_run_main" not in sys.modules:
        sys.modules["cloud_run_main"] = importlib.import_module("main")


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


def test_create_answer_session_happy_path(client_with_user: TestClient) -> None:
    """``POST /answer/sessions`` returns the newly inserted row + 200."""
    res = client_with_user.post(
        "/answer/sessions",
        json={
            "initial_q": "Hook nào đang chạy trong ngách skincare?",
            "intent_type": "trend_spike",
            "niche_id": 1,
            "format": "pattern",
        },
        headers={"Authorization": "Bearer fake", "Idempotency-Key": "test-key-1"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["user_id"] == "00000000-0000-0000-0000-0000000000aa"
    assert body["format"] == "pattern"
    assert body["initial_q"].startswith("Hook nào")
    assert body["intent_type"] == "trend_spike"


def test_create_answer_session_rejects_unknown_format(
    client_with_user: TestClient,
) -> None:
    """Pydantic validation returns 422 for a bogus ``format``."""
    res = client_with_user.post(
        "/answer/sessions",
        json={
            "initial_q": "x",
            "intent_type": "trend_spike",
            "niche_id": None,
            "format": "not-a-format",
        },
        headers={"Authorization": "Bearer fake"},
    )
    assert res.status_code == 422


def test_create_answer_session_cors_preflight_allows_idempotency_key(
    client_with_user: TestClient,
) -> None:
    """The 2026-04 CORS fix allows ``Idempotency-Key`` through preflight —
    regression guard so nobody reverts it silently."""
    res = client_with_user.options(
        "/answer/sessions",
        headers={
            "Origin": "https://getviews.vn",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
        },
    )
    assert res.status_code == 200, res.text
    allowed = res.headers.get("access-control-allow-headers", "").lower()
    assert "idempotency-key" in allowed
    assert "authorization" in allowed


def test_create_answer_session_maps_fk_violation_to_invalid_niche(
    client_with_user: TestClient,
) -> None:
    """DB FK violations on ``niche_id`` come back as ``{"error":"invalid_niche"}``
    (400) — the client maps that code to a Vietnamese explanation instead of
    rendering the raw Postgres error text."""
    with patch(
        "getviews_pipeline.answer_session.get_service_client",
        side_effect=RuntimeError(
            'insert or update on table "answer_sessions" violates foreign key '
            'constraint "answer_sessions_niche_id_fkey" on column niche_id',
        ),
    ):
        res = client_with_user.post(
            "/answer/sessions",
            json={
                "initial_q": "x",
                "intent_type": "trend_spike",
                "niche_id": 999,
                "format": "pattern",
            },
            headers={"Authorization": "Bearer fake"},
        )
    assert res.status_code == 400
    assert res.json() == {"error": "invalid_niche"}


def test_create_answer_session_unclassified_error_returns_start_failed(
    client_with_user: TestClient,
) -> None:
    """Unrecognised backend failures return ``start_failed`` + 500 and omit
    the raw exception detail so the client's Vietnamese copy wins."""
    with patch(
        "getviews_pipeline.answer_session.get_service_client",
        side_effect=RuntimeError("supabase unreachable"),
    ):
        res = client_with_user.post(
            "/answer/sessions",
            json={
                "initial_q": "x",
                "intent_type": "trend_spike",
                "niche_id": None,
                "format": "pattern",
            },
            headers={"Authorization": "Bearer fake"},
        )
    assert res.status_code == 500
    body = res.json()
    assert body == {"error": "start_failed"}


def test_create_answer_session_missing_auth_returns_401() -> None:
    """Without the dep override, no Bearer header → 401.

    This guards the common failure mode where CORS or an Edge proxy strips
    the ``Authorization`` header — the client would see 401 and the SSE flow
    would abort before reaching ``create_session``."""
    import importlib
    import sys

    if "cloud_run_main" not in sys.modules:
        sys.modules["cloud_run_main"] = importlib.import_module("main")
    from cloud_run_main import app  # type: ignore

    c = TestClient(app)
    res = c.post(
        "/answer/sessions",
        json={
            "initial_q": "x",
            "intent_type": "trend_spike",
            "niche_id": None,
            "format": "pattern",
        },
    )
    assert res.status_code == 401
