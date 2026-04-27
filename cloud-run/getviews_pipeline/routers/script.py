"""Script studio routes (/script/*)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response

from getviews_pipeline.deps import _resolve_caller_niche_id, require_user
from getviews_pipeline.runtime import run_sync
from getviews_pipeline.script_generate import InsufficientCreditsError as ScriptInsufficientCreditsError
from getviews_pipeline.script_generate import ScriptGenerateBody
from getviews_pipeline.script_save import DraftCreateBody, DraftExportBody
from getviews_pipeline.supabase_client import user_supabase

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_script_save(user: dict[str, Any], body: DraftCreateBody) -> JSONResponse:
    from getviews_pipeline.script_save import insert_draft

    sb = user_supabase(user["access_token"])
    try:
        row = await run_sync(insert_draft, sb, user_id=user["user_id"], body=body)
    except Exception as exc:
        logger.exception("[script/save] insert failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"draft_id": row.get("id"), "draft": row})


@router.get("/script/scene-intelligence")
async def script_scene_intelligence_endpoint(
    user: dict = Depends(require_user),
    niche_id: int | None = Query(default=None, ge=1, description="Ngách; mặc định lấy ``profiles.primary_niche`` của user."),
) -> JSONResponse:
    """B.4.2 — Rows from ``scene_intelligence`` (nightly aggregate) for script studio."""
    from getviews_pipeline.script_data import fetch_scene_intelligence_for_niche

    token = user["access_token"]
    nid = niche_id if niche_id is not None else await _resolve_caller_niche_id(token)
    sb = user_supabase(token)
    try:
        out = await run_sync(fetch_scene_intelligence_for_niche, sb, nid)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[script/scene-intelligence] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


@router.get("/script/idea-references")
async def script_idea_references_endpoint(
    user: dict = Depends(require_user),
    niche_id: int | None = Query(default=None, ge=1, description="Ngách; mặc định lấy ``profiles.primary_niche`` của user."),
    hook_type: str | None = Query(default=None, description="Raw enum (``question``) or VN label (``Câu hỏi mở đầu``); resolver accepts both."),
    limit: int = Query(default=5, ge=1, le=10, description="Number of references to return."),
) -> JSONResponse:
    """S3 — Top N viral videos in the niche matching the chosen idea's
    hook_type. Drives the IdeaRefStrip above the storyboard in /app/script.
    Falls back to overall top-views in the niche when the hook_type pool
    is thin (< limit)."""
    from getviews_pipeline.script_data import fetch_idea_references_for_niche

    token = user["access_token"]
    nid = niche_id if niche_id is not None else await _resolve_caller_niche_id(token)
    sb = user_supabase(token)
    try:
        out = await run_sync(fetch_idea_references_for_niche, sb, nid, hook_type, limit)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[script/idea-references] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


@router.get("/script/hook-patterns")
async def script_hook_patterns_endpoint(
    user: dict = Depends(require_user),
    niche_id: int | None = Query(default=None, ge=1, description="Ngách; mặc định lấy ``profiles.primary_niche`` của user."),
) -> JSONResponse:
    """B.4.2 — Hook leaderboard + citation for script studio (wraps ``hook_effectiveness``)."""
    from getviews_pipeline.script_data import fetch_hook_patterns_for_niche

    token = user["access_token"]
    nid = niche_id if niche_id is not None else await _resolve_caller_niche_id(token)
    sb = user_supabase(token)
    try:
        out = await run_sync(fetch_hook_patterns_for_niche, sb, nid)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[script/hook-patterns] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


@router.post("/script/generate")
async def script_generate_endpoint(
    body: ScriptGenerateBody,
    user: dict = Depends(require_user),
) -> JSONResponse:
    """B.4 — Generate shot scaffold (v1 deterministic template). Deducts one credit."""
    from getviews_pipeline.script_generate import run_script_generate_sync

    token = user["access_token"]
    sb = user_supabase(token)
    try:
        nid = await _resolve_caller_niche_id(token)
    except HTTPException:
        raise
    if body.niche_id != nid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="niche_id phải trùng ngách chính trong hồ sơ.")
    # Wave 2.5 Phase B PR #6 — matcher needs the service client to
    # read video_shots (RLS: writer-only, service_role readers).
    from getviews_pipeline.supabase_client import get_service_client
    service_sb = get_service_client()
    try:
        out = await run_sync(
            run_script_generate_sync, sb,
            user_id=user["user_id"], body=body, service_sb=service_sb,
        )
    except ScriptInsufficientCreditsError:
        return JSONResponse(status_code=status.HTTP_402_PAYMENT_REQUIRED, content={"error": "insufficient_credits"})
    except Exception as exc:
        logger.exception("[script/generate] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


@router.post("/script/save")
async def script_save_endpoint(
    body: DraftCreateBody,
    user: dict[str, Any] = Depends(require_user),
) -> JSONResponse:
    """Phase D.1.1 — persist a script draft (RLS: caller owns row)."""
    return await _run_script_save(user, body)


@router.post("/script/drafts")
async def script_drafts_create(
    body: DraftCreateBody,
    user: dict[str, Any] = Depends(require_user),
) -> JSONResponse:
    """Alias for ``POST /script/save`` — keeps the B.4 scaffold URL working."""
    return await _run_script_save(user, body)


@router.get("/script/drafts")
async def script_drafts_list(
    user: dict[str, Any] = Depends(require_user),
    limit: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    """List recent script drafts for the authenticated user."""
    from getviews_pipeline.script_save import list_drafts

    sb = user_supabase(user["access_token"])
    try:
        rows = await run_sync(list_drafts, sb, user_id=user["user_id"], limit=limit)
    except Exception as exc:
        logger.exception("[script/drafts] list failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"drafts": rows})


@router.get("/script/drafts/{draft_id}")
async def script_draft_get(
    draft_id: str,
    user: dict[str, Any] = Depends(require_user),
) -> JSONResponse:
    """Single-draft restoration endpoint (D.1.1)."""
    from getviews_pipeline.script_save import DraftNotFoundError, fetch_draft

    sb = user_supabase(user["access_token"])
    try:
        draft = await run_sync(fetch_draft, sb, user_id=user["user_id"], draft_id=draft_id)
    except DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản") from None
    except Exception as exc:
        logger.exception("[script/drafts/%s] fetch failed: %s", draft_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"draft": draft})


@router.post("/script/drafts/{draft_id}/export")
async def script_draft_export(
    draft_id: str,
    body: DraftExportBody,
    user: dict[str, Any] = Depends(require_user),
) -> Response:
    """Export the draft as clipboard-friendly text."""
    from getviews_pipeline.script_save import DraftNotFoundError, export_draft, fetch_draft

    sb = user_supabase(user["access_token"])
    try:
        draft = await run_sync(fetch_draft, sb, user_id=user["user_id"], draft_id=draft_id)
    except DraftNotFoundError:
        raise HTTPException(status_code=404, detail="Không tìm thấy kịch bản") from None

    try:
        payload, content_type = await run_sync(export_draft, draft, fmt=body.format)
    except Exception as exc:
        logger.exception("[script/drafts/%s/export] failed: %s", draft_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return Response(content=payload, media_type=content_type)
