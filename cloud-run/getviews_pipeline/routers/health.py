"""Health, auth-check, and admin ping routes."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from getviews_pipeline.config import ENSEMBLEDATA_API_TOKEN, GEMINI_API_KEY, SUPABASE_JWKS_URL, SUPABASE_JWT_SECRET
from getviews_pipeline.deps import require_admin, require_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health() -> JSONResponse:
    from getviews_pipeline.r2 import r2_configured
    checks = {
        "gemini_key_set": bool(GEMINI_API_KEY),
        "ensemble_key_set": bool(ENSEMBLEDATA_API_TOKEN),
        "jwt_configured": bool(SUPABASE_JWT_SECRET) or bool(SUPABASE_JWKS_URL),
        "cdn_proxy_set": bool(os.environ.get("RESIDENTIAL_PROXY_URL")),
        "r2_configured": r2_configured(),
    }
    required = {k: v for k, v in checks.items() if k not in ("cdn_proxy_set", "r2_configured")}
    ok = all(required.values())
    return JSONResponse(
        {"status": "ok" if ok else "degraded", "checks": checks},
        status_code=200 if ok else 503,
    )


@router.get("/auth-check")
async def auth_check(user: dict = Depends(require_user)) -> JSONResponse:
    """Smoke-test endpoint — returns user_id if JWT is valid."""
    return JSONResponse({"ok": True, "user_id": user["user_id"]})


@router.get("/admin/ping")
async def admin_ping(admin: dict = Depends(require_admin)) -> JSONResponse:
    """Admin-only smoke test — returns 403 if the JWT owner isn't flagged
    admin, 200 if they are. The SPA probes this once on /app/admin mount to
    decide between rendering the dashboard and redirecting to /app.
    """
    return JSONResponse({"ok": True, "user_id": admin["user_id"]})
