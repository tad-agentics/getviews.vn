"""Home screen routes (/home/*)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from getviews_pipeline.deps import (
    _resolve_caller_niche_id,
    require_user,
    resolve_home_niche_id,
)
from getviews_pipeline.supabase_client import user_supabase

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/home/pulse")
async def home_pulse(
    user: dict = Depends(require_user),
    niche_id: int | None = Query(default=None, alias="niche_id"),
) -> JSONResponse:
    """PulseCard payload for the caller's niche (first in ``niche_ids`` by default, or ``?niche_id=``)."""
    from getviews_pipeline.pulse import compute_pulse
    from getviews_pipeline.supabase_client import get_service_client

    resolved = await resolve_home_niche_id(user["access_token"], niche_id)
    try:
        stats = await compute_pulse(get_service_client(), resolved)
    except Exception as exc:
        logger.exception("[home_pulse] niche=%s failed: %s", resolved, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(stats.to_json())


@router.get("/home/ticker")
async def home_ticker(
    user: dict = Depends(require_user),
    niche_id: int | None = Query(default=None, alias="niche_id"),
) -> JSONResponse:
    """Marquee ticker items for the caller's niche (default = first ``niche_ids`` slot, or ``?niche_id=``)."""
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.ticker import compute_ticker

    resolved = await resolve_home_niche_id(user["access_token"], niche_id)
    try:
        items = await compute_ticker(get_service_client(), resolved)
    except Exception as exc:
        logger.exception("[home_ticker] niche=%s failed: %s", resolved, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"niche_id": resolved, "items": [it.to_json() for it in items]})


@router.get("/home/starter-creators")
async def home_starter_creators(user: dict = Depends(require_user)) -> JSONResponse:
    """Onboarding step 2 — starter creators to pick reference channels from."""
    sb = user_supabase(user["access_token"])
    niche_id = await _resolve_caller_niche_id(user["access_token"])
    try:
        res = (
            sb.table("starter_creators")
            .select("handle, display_name, followers, avg_views, video_count, rank")
            .eq("niche_id", niche_id)
            .order("rank", desc=False)
            .limit(10)
            .execute()
        )
    except Exception as exc:
        logger.exception("[home_starter_creators] niche=%s failed: %s", niche_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"niche_id": niche_id, "creators": res.data or []})


@router.get("/home/daily-ritual")
async def home_daily_ritual(
    user: dict = Depends(require_user),
    niche_id: int | None = Query(default=None, alias="niche_id"),
) -> JSONResponse:
    """Today's 3 ready-to-shoot scripts for one of the caller's followed niches.

    Pass ``niche_id`` to select which slot; omitted = first niche in ``niche_ids``.
    Returns 404 when no row exists for that (user, date, niche) yet.
    """
    resolved = await resolve_home_niche_id(user["access_token"], niche_id)
    sb = user_supabase(user["access_token"])
    try:
        res = (
            sb.table("daily_ritual")
            .select("generated_for_date, niche_id, scripts, adequacy, generated_at")
            .eq("niche_id", resolved)
            .order("generated_for_date", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("[home_daily_ritual] user=%s failed: %s", user["user_id"], exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    rows = res.data or []
    if not rows:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"code": "ritual_no_row", "message": "Sắp có — kịch bản đang được tạo."},
        )
    return JSONResponse(rows[0])
