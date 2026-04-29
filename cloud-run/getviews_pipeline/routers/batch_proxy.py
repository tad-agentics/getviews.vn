"""Proxy a small set of ``POST /batch/*`` calls from the user service to the batch service.

``SERVICE_ROLE=user`` does not mount the full ``batch`` router (see ``main.py``). Supabase
pg_cron and Cloud Scheduler often store a single ``cloud_run_api_url`` which historically
pointed at one Cloud Run service. If that URL is the **user** service, ``POST
/batch/morning-ritual`` would 404 and ``daily_ritual`` would never populate.

This module registers thin forwarders (same auth as real batch: ``require_batch_caller``) so
operators can keep ``cloud_run_api_url`` = user URL while setting
``BATCH_SERVICE_BASE_URL`` to the **batch** service origin; cron then succeeds without
re-pointing every secret.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from getviews_pipeline.deps import require_batch_caller

logger = logging.getLogger(__name__)

router = APIRouter()

_TIMEOUT_MORNING_S = 25.0 * 60.0
_TIMEOUT_SCENE_S = 45.0 * 60.0


def _batch_base() -> str:
    return os.environ.get("BATCH_SERVICE_BASE_URL", "").strip().rstrip("/")


async def _forward_batch_post(
    request: Request,
    path: str,
    timeout_s: float,
) -> JSONResponse:
    base = _batch_base()
    if not base:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "batch_service_base_url_unset: set BATCH_SERVICE_BASE_URL to the "
                "getviews-pipeline-batch Cloud Run URL (no trailing slash) on this user "
                "service, and ensure BATCH_SECRET matches the batch service. Or point "
                "cron at the batch URL directly."
            ),
        )

    url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
    secret = request.headers.get("X-Batch-Secret", "")
    body = await request.body()
    headers = {
        "Content-Type": request.headers.get("content-type") or "application/json",
        "X-Batch-Secret": secret,
    }
    timeout = httpx.Timeout(timeout_s, connect=30.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, content=body, headers=headers)
    except httpx.RequestError as exc:
        logger.exception("[batch_proxy] forward failed %s: %s", path, exc)
        return JSONResponse(
            status_code=502,
            content={"ok": False, "detail": "batch_proxy_unavailable", "error": str(exc)},
        )

    payload: Any
    try:
        payload = r.json() if r.content else {}
    except Exception:
        payload = {"ok": False, "detail": "non_json_from_batch", "raw": r.text[:2000]}

    return JSONResponse(content=payload, status_code=r.status_code)


@router.post("/batch/morning-ritual")
async def proxy_morning_ritual(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    return await _forward_batch_post(request, "/batch/morning-ritual", _TIMEOUT_MORNING_S)


@router.post("/batch/scene-intelligence")
async def proxy_scene_intelligence(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    return await _forward_batch_post(request, "/batch/scene-intelligence", _TIMEOUT_SCENE_S)
