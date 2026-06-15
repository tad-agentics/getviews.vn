"""GetViews.vn Cloud Run — FastAPI entry point.

All routes are implemented in getviews_pipeline/routers/. This file is the HTTP
boundary between the Vercel frontend/Edge Functions and the Python analysis pipeline.

JWT validation: Supabase uses ES256 (asymmetric). We validate via JWKS endpoint
— stateless, no shared secret, keys rotatable without redeployment.
JWKS URL: derived from ``SUPABASE_URL`` (or override via
``SUPABASE_JWKS_URL``) — resolved in ``getviews_pipeline.config``.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from getviews_pipeline import telemetry
from getviews_pipeline.session_store import replay_buffer_sweeper

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialise OTel as early as possible so all spans — including those from
# FastAPI auto-instrumentation — are captured.
telemetry.setup_telemetry(service_name="getviews-pipeline")

# Shared CORS config — applied as the outermost ASGI wrapper (see ``app`` below).
# Starlette places ``ServerErrorMiddleware`` inside ``FastAPI.add_middleware``;
# wrapping the finished app ensures OPTIONS preflight and 5xx responses still
# carry CORS headers (production was returning bare 500 on OPTIONS → browser
# "Failed to fetch" for every cross-origin GET with Authorization).
_CORS_KWARGS: dict = {
    "allow_origins": [
        "https://getviews.vn",
        "https://www.getviews.vn",
    ],
    "allow_origin_regex": r"https://.*\.vercel\.app|http://localhost:\d+",
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": [
        "Authorization",
        "Content-Type",
        "Accept",
        "Accept-Language",
        "X-Requested-With",
        "apikey",
        "Idempotency-Key",
    ],
    # Public Cloud Run URLs do not need Private Network Access. Leaving this off
    # avoids brittle preflight handling on some Starlette / Cloud Run combos.
    "max_age": 86400,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Size the default executor for the request concurrency (audit
    # 2026-06-10). Every sync Supabase/Gemini call goes through
    # ``run_in_executor(None, …)`` — on a 1-vCPU pod the asyncio default
    # is min(32, cpu+4) = 5 threads, while Cloud Run admits
    # ``--concurrency 20`` requests and a single paid turn can occupy a
    # thread for minutes. Five threads meant at most 5 concurrent paid
    # analyses; the 6th user's stream stalled silently behind them.
    # Threads here are I/O-parked (network waits), so 40 is cheap.
    from concurrent.futures import ThreadPoolExecutor

    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=40, thread_name_prefix="gv-sync")
    )

    # TD-4: prune the SSE replay buffer on a 30s cadence so orphaned
    # stream_ids (client never reconnects) don't sit forever on
    # ``min-instances=1`` pods. Lazy eviction inside ``get_stream_chunks``
    # remains as a defensive net.
    sweeper_task = asyncio.create_task(replay_buffer_sweeper())
    try:
        yield
    finally:
        sweeper_task.cancel()
        try:
            await sweeper_task
        except asyncio.CancelledError:
            pass


api = FastAPI(title="GetViews Pipeline", version="0.1.0", lifespan=lifespan)
telemetry.instrument_fastapi(api)


# ── Global error handler ──────────────────────────────────────────────────────
# Catches unhandled errors BEFORE the response body is opened (e.g. route lookup,
# middleware, dependency injection). Errors that occur DURING an open SSE stream
# cannot change the HTTP status — they are sent as error SSE tokens instead.
@api.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
# SERVICE_ROLE selects which routers this pod exposes. Same image, two
# Cloud Run services so live SSE traffic and 30-minute cron batches don't
# share quota or scaling pressure (CLAUDE.md: "Two deployment shapes").
#   - "all"   → everything (default; suits dev/preview)
#   - "user"  → user-facing surface only (no /batch/* heavy crons)
#   - "batch" → batch + admin only (cron-triggered, min-instances=0)
SERVICE_ROLE = os.environ.get("SERVICE_ROLE", "all").strip().lower()
if SERVICE_ROLE not in {"all", "user", "batch"}:
    logger.warning("SERVICE_ROLE=%r unrecognised — defaulting to 'all'", SERVICE_ROLE)
    SERVICE_ROLE = "all"
logger.info("SERVICE_ROLE=%s", SERVICE_ROLE)

from getviews_pipeline.routers.admin import router as admin_router
from getviews_pipeline.routers.answer import router as answer_router
from getviews_pipeline.routers.batch import router as batch_router
from getviews_pipeline.routers.batch_proxy import router as batch_proxy_router
from getviews_pipeline.routers.douyin import router as douyin_router
from getviews_pipeline.routers.health import router as health_router
from getviews_pipeline.routers.home import router as home_router
from getviews_pipeline.routers.script import router as script_router
from getviews_pipeline.routers.video import router as video_router

# /health is mounted on every shape — Cloud Run liveness probe needs it.
api.include_router(health_router)

if SERVICE_ROLE in {"all", "user"}:
    api.include_router(video_router)
    api.include_router(script_router)
    api.include_router(home_router)
    api.include_router(answer_router)
    api.include_router(douyin_router)

# When split-deployed, pg_cron may still POST to the user service URL. Forward the
# heaviest scheduled jobs to the batch origin (see ``batch_proxy`` module).
if SERVICE_ROLE == "user":
    api.include_router(batch_proxy_router)

if SERVICE_ROLE in {"all", "batch"}:
    api.include_router(batch_router)
    api.include_router(admin_router)

# Uvicorn entry — outermost CORS so preflight never hits ServerErrorMiddleware
# without CORS headers. Tests: use ``api`` for dependency_overrides / OpenAPI.
app = CORSMiddleware(api, **_CORS_KWARGS)
