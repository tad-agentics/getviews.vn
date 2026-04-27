"""D4a (2026-06-04) — Kho Douyin · read-only routes (/douyin/*).

Single ``/douyin/feed`` endpoint that returns the full active niche
taxonomy + corpus videos in one call. Powers the ``/app/douyin``
surface (D4b ships the FE shell).

Auth: requires an authenticated user — anyone signed in can browse the
Kho Douyin (no per-user gating; the data is public-by-design,
curated trend research).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from getviews_pipeline.deps import require_user
from getviews_pipeline.runtime import run_sync
from getviews_pipeline.supabase_client import user_supabase

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/douyin/feed")
async def douyin_feed_endpoint(
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Return ``{niches, videos}`` for the Kho Douyin surface.

    Both lists are pre-filtered by ``douyin_niche_taxonomy.active=TRUE``
    so a paused niche never surfaces in the chip strip OR the grid.
    Videos are ordered by ``views DESC`` server-side; FE re-sorts
    client-side for the user's sort dropdown.
    """
    from getviews_pipeline.douyin_data import fetch_douyin_feed

    sb = user_supabase(user["access_token"])
    try:
        payload = await run_sync(fetch_douyin_feed, sb)
    except Exception as exc:
        logger.exception("[douyin/feed] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(payload)
