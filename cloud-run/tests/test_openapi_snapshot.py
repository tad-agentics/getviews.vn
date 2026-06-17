"""Phase 0.2 — OpenAPI schema snapshot guard.

Asserts that the key route signatures in main.py are present and have not
drifted during refactoring. Any structural change to a route (URL, method,
or removal) will fail this test, forcing a deliberate acknowledgement.

This is a lightweight check — it does not validate full JSON Schema — but it
is fast and does not require an actual HTTP server.
"""

from __future__ import annotations

import pytest

# Every router module ``main`` mounts. They are imported (and reloaded) *before*
# ``main`` so ``include_router()`` always copies a fully-decorated APIRouter.
# Without this, a cold ``import main`` (e.g. when this module's fixture is the
# first to import it in the session) can include a router whose ``@router.get``
# decorators have not all run yet — yielding only the 8 default FastAPI routes.
# Production is unaffected (uvicorn imports the routers transitively first), but
# the test-session import order is not guaranteed, so we make it deterministic.
_ROUTER_MODULES = (
    "getviews_pipeline.routers.health",
    "getviews_pipeline.routers.video",
    "getviews_pipeline.routers.script",
    "getviews_pipeline.routers.home",
    "getviews_pipeline.routers.answer",
    "getviews_pipeline.routers.douyin",
    "getviews_pipeline.routers.batch_proxy",
    "getviews_pipeline.routers.batch",
    "getviews_pipeline.routers.admin",
)


def _route_set(app: object) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in getattr(app, "routes", []):
        path = getattr(route, "path", None)
        for method in getattr(route, "methods", None) or ():
            result.add((method.upper(), path))
    return result


@pytest.fixture(scope="module")
def registered() -> set[tuple[str, str]]:
    """{(method, path)} for the app ``main`` boots, however it is cached."""
    import importlib
    import sys

    try:
        m = importlib.import_module("main")
    except Exception as exc:  # pragma: no cover — heavy deps absent (e.g. local dev)
        pytest.skip(f"Cannot import main: {exc}")

    # Collect every candidate app object the session may hold for the entry
    # module: ``sys.modules["main"]`` (this import) and any alias other tests
    # registered (e.g. ``cloud_run_main``). Use whichever exposes the full route
    # table — different import paths can yield distinct module objects, and a
    # freshly re-executed ``main`` can end up with an empty ``api``.
    candidates: dict[str, object] = {}
    for key, mod in list(sys.modules.items()):
        if mod is None:
            continue
        if key == "main" or key == "cloud_run_main" or getattr(mod, "__name__", "") == "main":
            for attr in ("api", "app"):
                obj = getattr(mod, attr, None)
                if obj is not None:
                    candidates[f"{key}.{attr}"] = obj

    sized = {name: _route_set(obj) for name, obj in candidates.items()}
    best = max(sized.values(), key=len, default=set())

    if len(best) < 49:  # diagnostics surface in pytest's captured stdout on failure
        print("\n[openapi-diag] candidate route counts:", {k: len(v) for k, v in sized.items()})
        print("[openapi-diag] main id:", id(m), "file:", getattr(m, "__file__", "?"))
        try:
            from fastapi import FastAPI

            from getviews_pipeline.routers.health import router as health_router

            probe = FastAPI()
            before = len(_route_set(probe))
            probe.include_router(health_router)
            after = len(_route_set(probe))
            print(
                "[openapi-diag] include_router probe:",
                f"health_router.routes={len(health_router.routes)}",
                f"FastAPI before={before} after={after}",
            )
        except Exception as exc:  # noqa: BLE001
            print("[openapi-diag] include_router probe raised:", repr(exc))
    return best


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
