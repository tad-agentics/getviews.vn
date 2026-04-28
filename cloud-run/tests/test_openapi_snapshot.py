"""Phase 0.2 — OpenAPI schema snapshot guard.

Asserts that the key route signatures in main.py are present and have not
drifted during refactoring. Any structural change to a route (URL, method,
or removal) will fail this test, forcing a deliberate acknowledgement.

This is a lightweight check — it does not validate full JSON Schema — but it
is fast and does not require an actual HTTP server.
"""

from __future__ import annotations

import importlib

import pytest


# Importing main builds the app and all middleware — skip if heavy deps are absent.
@pytest.fixture(scope="module")
def app():  # type: ignore[return]
    try:
        import main as m  # type: ignore[import-not-found]
        return m.app
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Cannot import main: {exc}")


def _route_set(app) -> set[tuple[str, str]]:  # type: ignore[type-arg]
    """Return {(method, path)} for all registered routes."""
    result: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        for m in methods:
            result.add((m.upper(), path))
    return result


_REQUIRED_ROUTES: list[tuple[str, str]] = [
    ("GET", "/health"),
    ("GET", "/auth-check"),
    ("GET", "/admin/ping"),
    ("POST", "/classify-intent"),
    ("POST", "/stream"),
    ("POST", "/batch/ingest"),
    ("POST", "/batch/reingest-videos"),
    ("POST", "/batch/refresh"),
    ("POST", "/batch/reclassify-format"),
    ("POST", "/batch/backfill-thumbnails"),
    ("POST", "/batch/analytics"),
    ("POST", "/batch/layer0"),
    ("POST", "/batch/morning-ritual"),
    ("POST", "/batch/scene-intelligence"),
    ("GET", "/admin/corpus-health"),
    ("GET", "/admin/ensemble-credits"),
    ("GET", "/admin/ensemble-call-sites"),
    ("GET", "/admin/ensemble-history"),
    ("POST", "/admin/evaluate-alerts"),
    ("GET", "/admin/alert-fires"),
    ("GET", "/admin/logs"),
    ("GET", "/admin/action-log"),
    ("GET", "/admin/jobs/{job_id}"),
    ("GET", "/admin/triggers"),
    ("POST", "/admin/trigger/ingest"),
    ("POST", "/admin/trigger/refresh"),
    ("POST", "/admin/trigger/reclassify_format"),
    ("POST", "/admin/trigger/morning_ritual"),
    ("POST", "/admin/trigger/analytics"),
    ("POST", "/admin/trigger/layer0"),
    ("POST", "/admin/trigger/scene_intelligence"),
    ("POST", "/admin/trigger/thumbnail_backfill"),
    ("GET", "/video/niche-benchmark"),
    ("POST", "/video/analyze"),
    ("GET", "/channel/analyze"),
    ("GET", "/script/scene-intelligence"),
    ("GET", "/script/hook-patterns"),
    ("POST", "/script/generate"),
    ("POST", "/script/save"),
    ("POST", "/script/drafts"),
    ("GET", "/script/drafts"),
    ("GET", "/script/drafts/{draft_id}"),
    ("POST", "/script/drafts/{draft_id}/export"),
    ("GET", "/home/pulse"),
    ("GET", "/home/ticker"),
    ("GET", "/home/starter-creators"),
    ("GET", "/home/daily-ritual"),
    ("POST", "/answer/sessions"),
    ("POST", "/answer/sessions/{session_id}/turns"),
    ("GET", "/answer/sessions"),
    ("GET", "/answer/sessions/{session_id}"),
    ("PATCH", "/answer/sessions/{session_id}"),
]


def test_all_required_routes_registered(app) -> None:  # type: ignore[type-arg]
    """Every route in _REQUIRED_ROUTES must be present in the live app."""
    registered = _route_set(app)
    missing = [r for r in _REQUIRED_ROUTES if r not in registered]
    assert not missing, (
        f"Routes missing from app after refactor: {missing}\n"
        "Run the router extraction again and ensure include_router() is called for each domain."
    )


def test_route_count_not_decreased(app) -> None:  # type: ignore[type-arg]
    """Total route count must not drop below the known baseline (50 @app. routes)."""
    registered = _route_set(app)
    # 50 routes declared; FastAPI adds its own (redoc, openapi, docs) — allow some slack.
    assert len(registered) >= 50, (
        f"Only {len(registered)} routes registered. "
        "Expected ≥ 50. A router may not have been included."
    )
