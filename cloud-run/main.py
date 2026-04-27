"""GetViews.vn Cloud Run — FastAPI entry point.

All routes are implemented in getviews_pipeline/routers/. This file is the HTTP
boundary between the Vercel frontend/Edge Functions and the Python analysis pipeline.

JWT validation: Supabase uses ES256 (asymmetric). We validate via JWKS endpoint
— stateless, no shared secret, keys rotatable without redeployment.
JWKS URL: https://lzhiqnxfveqttsujebiv.supabase.co/auth/v1/.well-known/jwks.json
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from getviews_pipeline.session_store import replay_buffer_sweeper

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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


app = FastAPI(title="GetViews Pipeline", version="0.1.0", lifespan=lifespan)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Use allow_origin_regex only — FastAPI CORSMiddleware does not support wildcard
# subdomains in allow_origins. The regex covers production, Vercel previews, and
# local dev on any port.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|https://(www\.)?getviews\.vn|http://localhost:\d+",
    allow_credentials=True,
    # ``*`` → all methods (Starlette); avoids preflight 400 when clients add PATCH/HEAD/etc.
    allow_methods=["*"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Accept-Language",
        "X-Requested-With",
        "apikey",
        "Idempotency-Key",
    ],
    # Chrome Private Network Access: without this, preflight can return 400 and the
    # browser reports "CORS ... does not have HTTP ok status" for cross-origin fetches.
    allow_private_network=True,
    max_age=86400,
)


# ── Global error handler ──────────────────────────────────────────────────────
# Catches unhandled errors BEFORE the response body is opened (e.g. route lookup,
# middleware, dependency injection). Errors that occur DURING an open SSE stream
# cannot change the HTTP status — they are sent as error SSE tokens instead.
@app.exception_handler(Exception)
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

from getviews_pipeline.routers.health import router as health_router
from getviews_pipeline.routers.intent import router as intent_router
from getviews_pipeline.routers.video import router as video_router
from getviews_pipeline.routers.script import router as script_router
from getviews_pipeline.routers.home import router as home_router
from getviews_pipeline.routers.answer import router as answer_router
from getviews_pipeline.routers.douyin import router as douyin_router
from getviews_pipeline.routers.batch import router as batch_router
from getviews_pipeline.routers.admin import router as admin_router

# /health is mounted on every shape — Cloud Run liveness probe needs it.
app.include_router(health_router)

if SERVICE_ROLE in {"all", "user"}:
    app.include_router(intent_router)
    app.include_router(video_router)
    app.include_router(script_router)
    app.include_router(home_router)
    app.include_router(answer_router)
    app.include_router(douyin_router)

if SERVICE_ROLE in {"all", "batch"}:
    app.include_router(batch_router)
    app.include_router(admin_router)
