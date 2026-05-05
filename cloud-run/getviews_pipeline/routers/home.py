"""Home screen routes (/home/*)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from getviews_pipeline.deps import (
    _resolve_caller_niche_id,
    require_user,
    resolve_home_niche_id,
)
from getviews_pipeline.supabase_client import user_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

# In-flight regen tracker for POST /home/regenerate-ritual. Keyed by user_id.
# Module-level set is fine for our scale (low regen frequency, single-niche
# per user); a server restart cancels in-flight requests, which is OK because
# the nightly morning-ritual cron will catch up the next 07:00 VN window.
# Not used by the analyze pipeline (which uses ``profiles.is_processing`` for
# the TD-3 single-flight invariant on credit-spending video work).
_REGEN_INFLIGHT: set[str] = set()


@router.get("/home/pulse")
async def home_pulse(
    user: dict = Depends(require_user),
    niche_id: int | None = Query(default=None, alias="niche_id"),
) -> JSONResponse:
    """PulseCard payload for the caller's niche (profile niche by default (``creator_niche_id`` resolved to legacy id, falls back to ``primary_niche``); ``?niche_id=`` must match the resolved value)."""
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
    """Marquee ticker items for the caller's niche (default = profile niche resolved via ``creator_niche_id`` → legacy id; ``?niche_id=`` must match)."""
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
    """Today's 3 ready-to-shoot scripts for the caller's niche.

    Pass ``niche_id`` only to assert it matches the resolved ``creator_niche_id``
    (single-niche model since 2026-05-05); omitted = use the profile niche.
    Returns 404 when no row exists for that (user, date, niche) yet — the FE
    polls this endpoint after POST /home/regenerate-ritual until a row lands.
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


def _run_regen_ritual(user_id: str, niche_id: int) -> None:
    """Background task — re-runs ritual generation for one (user, niche).

    Always clears the in-flight tracker, even on failure, so the next
    request after a transient Gemini error can retry.
    """
    try:
        from getviews_pipeline.morning_ritual import (
            generate_ritual_for_user,
            upsert_ritual,
        )
        from getviews_pipeline.supabase_client import get_service_client

        client = get_service_client()
        prof_res = (
            client.table("profiles")
            .select("reference_channel_handles")
            .eq("id", user_id)
            .single()
            .execute()
        )
        prof: dict[str, Any] = prof_res.data or {}

        niche_res = (
            client.table("niche_taxonomy")
            .select("name_vn, name_en")
            .eq("id", niche_id)
            .single()
            .execute()
        )
        niche_row: dict[str, Any] = niche_res.data or {}
        niche_name = (
            niche_row.get("name_vn") or niche_row.get("name_en") or str(niche_id)
        )

        result = generate_ritual_for_user(
            client,
            user_id=user_id,
            niche_id=niche_id,
            niche_name=niche_name,
            reference_handles=list(prof.get("reference_channel_handles") or []),
        )
        if result.error is None and result.scripts:
            upsert_ritual(client, result)
        elif result.error:
            logger.warning(
                "[regen_ritual] user=%s niche=%s skipped: %s",
                user_id,
                niche_id,
                result.error,
            )
    except Exception as exc:
        logger.exception(
            "[regen_ritual] user=%s niche=%s failed: %s", user_id, niche_id, exc
        )
    finally:
        _REGEN_INFLIGHT.discard(user_id)


@router.post("/home/regenerate-ritual", status_code=status.HTTP_202_ACCEPTED)
async def home_regenerate_ritual(
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Queue a ritual regeneration for the caller's current niche.

    Fires after Settings → niche change so the user gets fresh Home content
    without waiting for the nightly morning-ritual cron. Returns immediately
    (202 + queued); the FE polls GET /home/daily-ritual to detect completion.
    Idempotent: a duplicate POST while one is in flight returns 202 +
    already_in_flight without re-queuing.
    """
    user_id = user["user_id"]
    if user_id in _REGEN_INFLIGHT:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"status": "already_in_flight"},
        )

    niche_id = await _resolve_caller_niche_id(user["access_token"])

    _REGEN_INFLIGHT.add(user_id)
    background_tasks.add_task(_run_regen_ritual, user_id, niche_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"status": "queued", "niche_id": niche_id},
    )
