"""Video niche-benchmark, video analyze, KOL browse/pin, and channel analyze routes."""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from getviews_pipeline.api_models import StrictBody
from getviews_pipeline.deps import require_user
from getviews_pipeline.runtime import run_sync
from getviews_pipeline.supabase_client import user_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

_NICHE_BENCH_CACHE: dict[tuple[int, int], tuple[float, dict[str, Any]]] = {}
_NICHE_BENCH_TTL_SEC = 3600.0


def _niche_bench_cache_key(niche_id: int, duration_sec: float) -> tuple[int, int]:
    return niche_id, int(round(duration_sec))


class VideoAnalyzeRequest(StrictBody):
    video_id: str | None = None
    tiktok_url: str | None = None
    force_refresh: bool = False
    mode: Literal["win", "flop"] | None = None


@router.get("/video/niche-benchmark")
async def video_niche_benchmark(
    user: dict = Depends(require_user),
    niche_id: int = Query(..., ge=1, description="niche_taxonomy.id"),
    duration_sec: float = Query(58.0, ge=5.0, le=600.0, description="Video duration for benchmark curve shape (seconds)."),
) -> JSONResponse:
    """Niche aggregates + modeled benchmark retention curve for /video Flop UI."""
    now = time.monotonic()
    ck = _niche_bench_cache_key(niche_id, duration_sec)
    cached = _NICHE_BENCH_CACHE.get(ck)
    if cached and now - cached[0] < _NICHE_BENCH_TTL_SEC:
        return JSONResponse(cached[1])

    from getviews_pipeline.video_niche_benchmark import (
        build_niche_benchmark_payload,
        fetch_niche_intelligence_sync,
    )

    sb = user_supabase(user["access_token"])
    try:
        row = await run_sync(fetch_niche_intelligence_sync, sb, niche_id)
    except Exception as exc:
        logger.exception("[video/niche-benchmark] niche=%s failed: %s", niche_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    payload = build_niche_benchmark_payload(row, niche_id=niche_id, duration_sec=duration_sec, user_sb=sb)
    _NICHE_BENCH_CACHE[ck] = (now, payload)
    return JSONResponse(payload)


@router.post("/video/analyze")
async def video_analyze_endpoint(
    body: VideoAnalyzeRequest,
    user: dict = Depends(require_user),
) -> JSONResponse:
    """Phase B · B.1.3 — structural slots + Gemini copy, cached in ``video_diagnostics``.

    On-demand fallback: when the user pastes a URL that isn't in
    ``video_corpus`` (composer → ``/app/video?url=…``), fall through to
    ``run_video_analyze_on_demand`` so they get a working analysis
    instead of a 404 dead-end. The fallback never persists — pure
    one-shot Gemini run, result flagged ``source: "on_demand"``.
    The fallback only triggers when the user supplied a ``tiktok_url``;
    a ``video_id`` miss (UUID or numeric aweme_id that's not in corpus)
    still 404s, since we have no URL to fetch from EnsembleData.
    """
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.video_analyze import (
        run_video_analyze_on_demand,
        run_video_analyze_pipeline,
    )

    vid = (body.video_id or "").strip() if body.video_id else ""
    url = (body.tiktok_url or "").strip() if body.tiktok_url else ""
    if not vid and not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cần video_id hoặc tiktok_url")

    sb_user = user_supabase(user["access_token"])
    try:
        out = await run_sync(run_video_analyze_pipeline, get_service_client(), sb_user, video_id=vid or None, tiktok_url=url or None, force_refresh=body.force_refresh, mode=body.mode)
    except ValueError as exc:
        msg = str(exc)
        url_miss = (msg == "video not in corpus" and url) or "Không tìm thấy video trong corpus cho URL này" in msg
        if url_miss and url:
            try:
                out = await run_sync(
                    run_video_analyze_on_demand,
                    get_service_client(),
                    sb_user,
                    tiktok_url=url,
                    mode=body.mode,
                )
                return JSONResponse(out)
            except ValueError as ondemand_exc:
                # Bad URL shape, missing aweme_id, etc. — caller's request
                # was structurally invalid; surface as 400.
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(ondemand_exc),
                ) from ondemand_exc
            except Exception as ondemand_exc:
                logger.exception("[video/analyze] on-demand failed: %s", ondemand_exc)
                raise HTTPException(status_code=500, detail=str(ondemand_exc)) from ondemand_exc
        if msg == "video not in corpus" or "Không tìm thấy" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
    except Exception as exc:
        logger.exception("[video/analyze] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


@router.get("/channel/analyze")
async def channel_analyze_endpoint(
    user: dict = Depends(require_user),
    handle: str = Query(..., min_length=1, max_length=200, description="TikTok handle, có hoặc không @"),
    force_refresh: bool = Query(False, description="Bỏ qua cache 7 ngày và gọi lại Gemini (trừ thin_corpus)."),
) -> JSONResponse:
    """B.3.1 — Phân tích kênh: gate ≥10 video, cache ``channel_formulas``, Gemini + trừ credit khi miss."""
    from getviews_pipeline.channel_analyze import InsufficientCreditsError, run_channel_analyze_sync
    from getviews_pipeline.supabase_client import get_service_client

    sb_user = user_supabase(user["access_token"])
    try:
        out = await run_sync(run_channel_analyze_sync, get_service_client(), sb_user, user_id=user["user_id"], raw_handle=handle, force_refresh=force_refresh)
    except InsufficientCreditsError:
        return JSONResponse(status_code=status.HTTP_402_PAYMENT_REQUIRED, content={"error": "insufficient_credits"})
    except ValueError as exc:
        msg = str(exc)
        if "Chưa chọn ngách" in msg or "Không thấy kênh" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
    except Exception as exc:
        logger.exception("[channel/analyze] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(out)


@router.post("/channel/refresh-mine")
async def channel_refresh_mine_endpoint(
    user: dict = Depends(require_user),
    force: bool = Query(
        False,
        description=(
            "Bỏ qua cửa sổ stale 18h. Chỉ dùng cho debug — "
            "vẫn bị giới hạn bởi MAX_PER_REFRESH."
        ),
    ),
) -> JSONResponse:
    """Per-handle on-demand corpus refresh for the connected creator's own
    channel. Closes the ~24h staleness gap between TikTok-live and the
    nightly ``cron-batch-ingest``.

    Reads ``profiles.tiktok_handle`` + ``profiles.primary_niche`` for the
    caller — a creator can only refresh their OWN channel via this route.
    Server-side 18h staleness gate prevents tab-spam from burning ED units.

    Returns one of:
      ``cached``     — within freshness window, no scrape (200 OK)
      ``refreshed``  — ED scrape ran; ``count`` new rows landed
      ``error``      — handle missing on profile, niche missing, or ED failure
    """
    from getviews_pipeline.channel_refresh import refresh_channel_corpus
    from getviews_pipeline.supabase_client import get_service_client

    sb_user = user_supabase(user["access_token"])

    try:
        pres = sb_user.table("profiles").select("tiktok_handle, primary_niche").single().execute()
    except Exception as exc:
        logger.warning("[channel/refresh-mine] profile read failed: %s", exc)
        raise HTTPException(status_code=500, detail="profile_read_failed") from exc

    profile = pres.data or {}
    handle = (profile.get("tiktok_handle") or "").strip().lstrip("@")
    niche_id_raw = profile.get("primary_niche")

    if not handle:
        return JSONResponse({"status": "error", "reason": "no_handle_on_profile"}, status_code=400)
    if niche_id_raw is None:
        return JSONResponse({"status": "error", "reason": "no_niche_on_profile"}, status_code=400)

    niche_id = int(niche_id_raw)

    # Fetch niche_name for IngestResult tagging + log lines.
    niche_name = ""
    try:
        nres = (
            sb_user.table("niche_taxonomy")
            .select("name_vn, name_en")
            .eq("id", niche_id)
            .single()
            .execute()
        )
        nrow = nres.data or {}
        niche_name = str(nrow.get("name_vn") or nrow.get("name_en") or f"niche_{niche_id}")
    except Exception:
        niche_name = f"niche_{niche_id}"

    out = await refresh_channel_corpus(
        get_service_client(),
        handle=handle,
        niche_id=niche_id,
        niche_name=niche_name,
        force=force,
    )
    return JSONResponse(out)
