"""GetViews.vn Cloud Run — FastAPI entry point.

Routes are implemented here as the pipeline grows. This file is the HTTP
boundary between the Vercel frontend/Edge Functions and the Python analysis
pipeline.

JWT validation: Supabase uses ES256 (asymmetric). We validate via JWKS endpoint
— stateless, no shared secret, keys rotatable without redeployment.
JWKS URL: https://lzhiqnxfveqttsujebiv.supabase.co/auth/v1/.well-known/jwks.json
"""

from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from jose import ExpiredSignatureError, JWTError, jwt

from getviews_pipeline.config import SUPABASE_JWKS_KID, SUPABASE_JWKS_URL, SUPABASE_JWT_SECRET

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="GetViews Pipeline", version="0.1.0")

# ── JWKS cache (refresh at most every 10 minutes) ─────────────────────────────

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 600  # seconds


async def _get_jwks() -> dict[str, Any]:
    global _jwks_cache, _jwks_fetched_at
    now = time.monotonic()
    if not _jwks_cache or now - _jwks_fetched_at > _JWKS_TTL:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(SUPABASE_JWKS_URL)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_fetched_at = now
    return _jwks_cache


# ── JWT dependency ─────────────────────────────────────────────────────────────

async def require_user(request: Request) -> dict[str, Any]:
    """Validate Supabase JWT from Authorization: Bearer header.

    Supports ES256 via JWKS (primary) with HS256 fallback if SUPABASE_JWT_SECRET is set.
    Returns the decoded JWT payload (contains 'sub' = user UUID).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")

    token = auth_header[7:]

    try:
        if SUPABASE_JWT_SECRET:
            # HS256 fallback (legacy — prefer JWKS)
            payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"])
        else:
            # ES256 via JWKS
            jwks = await _get_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["ES256"],
                options={"verify_aud": False},
            )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No sub in token")

    return {"user_id": user_id, "payload": payload}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/auth-check")
async def auth_check(user: dict = Depends(require_user)) -> JSONResponse:
    """Smoke-test endpoint — returns user_id if JWT is valid."""
    return JSONResponse({"ok": True, "user_id": user["user_id"]})
