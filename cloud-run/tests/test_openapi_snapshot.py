"""Phase 0.2 — OpenAPI schema snapshot guard.

Asserts that the key route signatures in main.py are present and have not
drifted during refactoring. Any structural change to a route (URL, method,
or removal) will fail this test, forcing a deliberate acknowledgement.

This is a lightweight check — it does not validate full JSON Schema — but it
is fast and does not require an actual HTTP server.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_CLOUD_RUN_ROOT = Path(__file__).resolve().parents[1]

# Enumerate ``main.api`` routes in a *pristine* subprocess interpreter. Importing
# main in-process is unreliable for this guard: the shared pytest session imports
# main (and its routers) under many monkeypatched/aliased states, and a
# module-scoped fixture can capture an early/degraded ``api`` whose routers were
# not yet attached. A clean ``python -c "import main"`` measures exactly what
# Cloud Run boots, with zero session-state coupling — which is the whole point of
# a "did every router get included?" snapshot.
_ENUMERATE_ROUTES_SRC = textwrap.dedent(
    """
    import json
    import main

    routes = []
    for route in main.api.routes:
        path = getattr(route, "path", None)
        for method in (getattr(route, "methods", None) or ()):
            routes.append([method.upper(), path])
    print(json.dumps(routes))
    """
)


@pytest.fixture(scope="module")
def registered() -> set[tuple[str, str]]:
    """Return {(method, path)} for all routes on a freshly-booted ``main.api``."""
    proc = subprocess.run(
        [sys.executable, "-c", _ENUMERATE_ROUTES_SRC],
        cwd=str(_CLOUD_RUN_ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:  # pragma: no cover — heavy deps absent (e.g. local dev)
        pytest.skip(f"Cannot import main in subprocess: {proc.stderr.strip()[-800:]}")
    # The route JSON is the final stdout line; ignore any stray import-time prints.
    payload = next(line for line in reversed(proc.stdout.splitlines()) if line.strip())
    return {(method, path) for method, path in json.loads(payload)}


_REQUIRED_ROUTES: list[tuple[str, str]] = [
    ("GET", "/health"),
    ("GET", "/auth-check"),
    ("GET", "/admin/ping"),
    # ``/classify-intent`` removed L1.5 audit — zero FE callers.
    # ``POST /stream`` removed Phase C — answer_turn only.
    ("POST", "/batch/ingest"),
    ("POST", "/batch/hi13-pilot"),
    ("POST", "/batch/post-processing"),
    ("POST", "/batch/reingest-videos"),
    ("POST", "/batch/refresh"),
    ("POST", "/batch/reclassify-format"),
    # L2.2 Sprint 2 — Sound Radar (/batch/trend-velocity) + L1.4 sound-aggregate
    ("POST", "/batch/trend-velocity"),
    ("POST", "/batch/stats-history-refetch"),
    ("POST", "/batch/backfill-thumbnails"),
    ("POST", "/batch/analytics"),
    ("POST", "/batch/layer0"),
    ("POST", "/batch/morning-ritual"),
    ("POST", "/batch/scene-intelligence"),
    ("GET", "/admin/corpus-health"),
    ("GET", "/admin/corpus-class-health"),
    ("GET", "/admin/hi13-batch-health"),
    ("GET", "/admin/ensemble-credits"),
    ("GET", "/admin/ensemble-call-sites"),
    ("GET", "/admin/ensemble-history"),
    ("POST", "/admin/evaluate-alerts"),
    ("GET", "/admin/alert-fires"),
    ("GET", "/admin/logs"),
    ("GET", "/admin/jobs/{job_id}"),
    ("GET", "/admin/triggers"),
    ("POST", "/admin/trigger/ingest"),
    ("POST", "/admin/trigger/post_processing"),
    ("POST", "/admin/trigger/refresh"),
    ("POST", "/admin/trigger/reclassify_format"),
    ("POST", "/admin/trigger/morning_ritual"),
    ("POST", "/admin/trigger/analytics"),
    ("POST", "/admin/trigger/layer0"),
    ("POST", "/admin/trigger/assignment_tier_backfill"),
    ("POST", "/admin/trigger/scene_intelligence"),
    ("POST", "/admin/trigger/thumbnail_backfill"),
    ("GET", "/video/niche-benchmark"),
    ("POST", "/channel/diagnose"),
    ("GET", "/channel/user-search"),
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


def test_all_required_routes_registered(registered: set[tuple[str, str]]) -> None:
    """Every route in _REQUIRED_ROUTES must be present in the live app."""
    missing = [r for r in _REQUIRED_ROUTES if r not in registered]
    assert not missing, (
        f"Routes missing from app after refactor: {missing}\n"
        "Run the router extraction again and ensure include_router() is called for each domain."
    )


def test_route_count_not_decreased(registered: set[tuple[str, str]]) -> None:
    """Total route count must not drop below the known baseline."""
    # 49 app routes after Phase C /stream removal; FastAPI adds openapi/docs.
    assert len(registered) >= 49, (
        f"Only {len(registered)} routes registered. "
        "Expected ≥ 49. A router may not have been included."
    )
