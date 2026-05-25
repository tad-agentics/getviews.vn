"""``POST /stream`` sunset — returns 410 Gone (Wave 5)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_user() -> TestClient:
    import main as m  # type: ignore[import-not-found]
    from getviews_pipeline.deps import require_user

    app = m.app

    def _fake_user() -> dict[str, str]:
        return {"user_id": "test-user", "access_token": "fake-token"}

    app.dependency_overrides[require_user] = _fake_user
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(require_user, None)


def test_stream_returns_410_gone(client_with_user: TestClient) -> None:
    res = client_with_user.post(
        "/stream",
        json={"session_id": "legacy-chat", "query": "phân tích video"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert res.status_code == 410
    body = res.json()
    assert body.get("error") == "stream_sunset"
    assert "replacement" in body
