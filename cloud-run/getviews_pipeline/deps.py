"""Shared FastAPI dependencies — auth, JWKS cache, batch caller gate, niche helper.

All auth dependencies live here so routers don't need to import from main.py
and we avoid circular-import issues. main.py imports these back; routers import
them directly from this module.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status
from jose import ExpiredSignatureError, JWTError, jwt

from getviews_pipeline.config import SUPABASE_JWKS_URL, SUPABASE_JWT_SECRET

logger = logging.getLogger(__name__)

# ── JWKS cache (refreshed at most every 10 minutes) ───────────────────────────

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 600  # seconds


async def _get_jwks() -> dict[str, Any]:
    global _jwks_cache, _jwks_fetched_at
    if not SUPABASE_JWKS_URL:
        # Surfaces as 401 "Invalid token" rather than a confusing
        # ``TypeError: ... expected str``. Resolution is documented
        # in cloud-run/.env.example: set SUPABASE_URL or
        # SUPABASE_JWKS_URL.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="jwks_url_unset",
        )
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
    Returns the decoded JWT payload (contains 'sub' = user UUID) plus the raw token
    so callers can build a user-scoped Supabase client via user_supabase(access_token).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")

    token = auth_header[7:]

    try:
        unverified_header = jwt.get_unverified_header(token)
        token_alg = unverified_header.get("alg", "")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

    try:
        if token_alg == "HS256" and SUPABASE_JWT_SECRET:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False, "leeway": 30},
            )
        else:
            jwks = await _get_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["ES256"],
                options={"verify_aud": False, "leeway": 30},
            )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No sub in token")

    return {"user_id": user_id, "payload": payload, "access_token": token}


async def require_admin(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    """Admin gate: layered on require_user so 401 vs 403 stays clean.

    ``profiles.is_admin`` is read through the service-role client so the flag
    is not forgeable via RLS tricks.
    """
    from getviews_pipeline.supabase_client import get_service_client

    try:
        resp = (
            get_service_client()
            .table("profiles")
            .select("is_admin")
            .eq("id", user["user_id"])
            .single()
            .execute()
        )
        row = resp.data or {}
    except Exception as exc:
        logger.warning("[require_admin] profiles lookup failed for %s: %s", user["user_id"], exc)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_check_failed") from exc

    if not row.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")

    return user


# ── Batch caller dependency ────────────────────────────────────────────────────
# Accepts EITHER:
#   A) A valid X-Batch-Secret header (legacy Cloud Scheduler cron jobs)
#   B) A valid admin JWT (preferred — migrate all Scheduler jobs to OIDC)
#
# When A is used, a deprecation warning is logged. Once all Scheduler jobs have
# been migrated to OIDC admin tokens, remove _BATCH_SECRET and this fallback.

async def require_batch_caller(request: Request) -> dict[str, Any] | None:
    """Gate for cron/batch endpoints.

    Accepts either:
      - X-Batch-Secret header (legacy Cloud Scheduler — deprecated Q3-2026)
      - Admin JWT via Authorization: Bearer (preferred)

    Returns None when access was granted via the batch secret (no user context);
    returns the admin user dict when access was granted via JWT.
    """
    # Read at call time so env-var overrides in tests take effect without
    # re-importing the module (module-level constants are frozen at first import).
    batch_secret = os.environ.get("BATCH_SECRET", "")
    provided_secret = request.headers.get("X-Batch-Secret", "")
    if batch_secret and provided_secret == batch_secret:
        logger.warning(
            "[batch_auth] X-Batch-Secret used on %s — will be removed Q3-2026; "
            "migrate Cloud Scheduler job to OIDC admin JWT",
            request.url.path,
        )
        return None

    # No valid batch secret — require admin JWT instead
    try:
        user = await require_user(request)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="batch_caller_required: provide X-Batch-Secret or admin JWT",
        )

    from getviews_pipeline.supabase_client import get_service_client

    try:
        resp = (
            get_service_client()
            .table("profiles")
            .select("is_admin")
            .eq("id", user["user_id"])
            .single()
            .execute()
        )
        row = resp.data or {}
    except Exception as exc:
        logger.warning("[require_batch_caller] admin check failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_check_failed") from exc

    if not row.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")

    return user


# ── Shared route helper ────────────────────────────────────────────────────────

def _default_niche_id_from_profile_row(row: dict) -> int | None:
    """Resolve the legacy niche_id for a profile row.

    PR5 of the two-axis refactor: prefers ``creator_niche_id`` (canonical
    UX-facing column from PR3) and resolves it to the representative
    ``niche_taxonomy.id`` so downstream queries
    (video_corpus / daily_ritual / cross_creator_patterns) that still
    filter on ``niche_id`` keep working unchanged. Falls back to
    legacy ``primary_niche`` for rows not yet backfilled — defensive,
    PR3 backfilled every populated row.
    """
    from getviews_pipeline.profile_niches import resolve_legacy_niche_from_profile_row

    return resolve_legacy_niche_from_profile_row(row)


async def _resolve_caller_niche_id(access_token: str) -> int:
    """Default legacy niche_id for the caller.

    Reads both ``creator_niche_id`` (new canonical) and ``primary_niche``
    (legacy fallback). Returns the representative legacy niche_id so
    callers (compute_pulse, ticker, /script/*, /channel/*) that filter
    on ``niche_id`` keep working through the transition window.
    """
    from getviews_pipeline.supabase_client import user_supabase

    sb = user_supabase(access_token)
    try:
        res = (
            sb.table("profiles")
            .select("creator_niche_id")
            .single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"profile lookup: {exc}") from exc
    nid = _default_niche_id_from_profile_row(res.data or {})
    if nid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chưa chọn ngách — chạy onboarding trước.",
        )
    return int(nid)


async def resolve_home_niche_id(access_token: str, requested: int | None) -> int:
    """Resolve the legacy niche_id for /home/* given an optional override.

    - ``requested`` is ``None``: use the caller's profile niche (resolved
      via ``creator_niche_id`` → legacy mapping).
    - Otherwise: must equal the resolved legacy niche_id. The Trends
      pill row lets users *browse* other niches; the home surfaces
      stay anchored to the user's own niche.

    Raises ``HTTPException`` 400 when ``requested`` mismatches, 404 when
    the profile has no niche configured.
    """
    from getviews_pipeline.supabase_client import user_supabase

    sb = user_supabase(access_token)
    try:
        res = (
            sb.table("profiles")
            .select("creator_niche_id")
            .single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"profile lookup: {exc}"
        ) from exc

    row = res.data or {}
    legacy_nid = _default_niche_id_from_profile_row(row)
    if legacy_nid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chưa chọn ngách — chạy onboarding trước.",
        )

    if requested is None:
        return legacy_nid

    try:
        rid = int(requested)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_niche_id"
        ) from exc
    if rid != legacy_nid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="niche_not_in_profile",
        )
    return rid
