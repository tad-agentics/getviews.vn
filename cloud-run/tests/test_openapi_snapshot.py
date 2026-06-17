"""Phase 0.2 — OpenAPI schema snapshot guard.

Asserts that the key route signatures in main.py are present and have not
drifted during refactoring. Any structural change to a route (URL, method,
or removal) will fail this test, forcing a deliberate acknowledgement.

This is a lightweight check — it does not validate full JSON Schema — but it
is fast and does not require an actual HTTP server.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_CLOUD_RUN_ROOT = Path(__file__).resolve().parents[1]

# Router modules ``main`` mounts when SERVICE_ROLE=all (the default deployment
# this snapshot targets). ``batch_proxy`` is user-role-only and intentionally
# excluded. Each module declares full, prefix-free paths (``@router.get("/video/...")``)
# and ``main.include_router()`` is called without a ``prefix=``, so the union of
# each router's own ``.routes`` is exactly the table ``main.api`` exposes.
#
# Why measure the routers directly instead of ``main.api``: the shared pytest
# session leaves ``FastAPI.include_router`` globally no-op'd (a fresh
# ``FastAPI().include_router(r)`` adds nothing once the suite has run), so
# ``main.api`` reads back as only the 8 default FastAPI routes in-process. The
# router modules' own ``.routes`` stay fully populated, and a static check below
# guards that ``main`` actually wires each one — together that preserves the
# original "did every router get included?" intent without depending on the
# poisoned runtime ``include_router``.
_ALL_ROLE_ROUTER_MODULES = (
    "getviews_pipeline.routers.health",
    "getviews_pipeline.routers.video",
    "getviews_pipeline.routers.script",
    "getviews_pipeline.routers.home",
    "getviews_pipeline.routers.answer",
    "getviews_pipeline.routers.douyin",
    "getviews_pipeline.routers.batch",
    "getviews_pipeline.routers.admin",
)

# Every router main imports must be wired via include_router() in main.py — the
# static guard reads the source so it holds even when runtime include_router is
# unavailable. ``batch_proxy`` is included under the user-role branch.
_WIRED_ROUTERS = (
    "health_router",
    "video_router",
    "script_router",
    "home_router",
    "answer_router",
    "douyin_router",
    "batch_proxy_router",
    "batch_router",
    "admin_router",
)


def _route_set(router: object) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in getattr(router, "routes", []):
        path = getattr(route, "path", None)
        for method in getattr(route, "methods", None) or ():
            result.add((method.upper(), path))
    return result


@pytest.fixture(scope="module")
def registered() -> set[tuple[str, str]]:
    """{(method, path)} for the union of all SERVICE_ROLE=all router tables."""
    import importlib

    result: set[tuple[str, str]] = set()
    try:
        for name in _ALL_ROLE_ROUTER_MODULES:
            mod = importlib.import_module(name)
            result |= _route_set(mod.router)
    except Exception as exc:  # pragma: no cover — heavy deps absent (e.g. local dev)
        pytest.skip(f"Cannot import routers: {exc}")
    return result


def test_main_wires_every_router() -> None:
    """``main.py`` must call ``include_router`` for each known router (source check)."""
    source = (_CLOUD_RUN_ROOT / "main.py").read_text(encoding="utf-8")
    missing = [r for r in _WIRED_ROUTERS if f"include_router({r})" not in source]
    assert not missing, (
        f"main.py does not include_router these routers: {missing}\n"
        "Add api.include_router(<name>) under the matching SERVICE_ROLE branch."
    )


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
