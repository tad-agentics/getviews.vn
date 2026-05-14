"""Video niche-benchmark, video analyze, KOL browse/pin, channel analyze, and channel diagnose routes."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse

from getviews_pipeline.deps import require_user
from getviews_pipeline.runtime import run_sync
from getviews_pipeline.session_store import get_stream_chunks, put_stream_chunks
from getviews_pipeline.supabase_client import get_service_client, user_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Channel diagnose in-flight guard (TD-3 mirror from routers/home.py)
# Key: f"{user_id}:{handle}:{video_url}"
# ---------------------------------------------------------------------------
_DIAGNOSE_INFLIGHT: set[str] = set()

_NICHE_BENCH_CACHE: dict[tuple[int, int], tuple[float, dict[str, Any]]] = {}
_NICHE_BENCH_TTL_SEC = 3600.0


def _niche_bench_cache_key(niche_id: int, duration_sec: float) -> tuple[int, int]:
    return niche_id, int(round(duration_sec))


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


def _summarize_user_search_row(row: dict[str, Any]) -> dict[str, Any] | None:
    u = row.get("user") if isinstance(row.get("user"), dict) else row
    if not isinstance(u, dict):
        return None
    unique = str(u.get("uniqueId") or u.get("unique_id") or "").strip()
    if not unique:
        return None
    nick = str(u.get("nickname") or "").strip()
    stats = u.get("statistics") if isinstance(u.get("statistics"), dict) else u.get("stats")
    stats = stats if isinstance(stats, dict) else {}
    followers = int(stats.get("followerCount") or stats.get("follower_count") or 0)
    avatar = str(
        u.get("avatarLarger")
        or u.get("avatar_larger")
        or u.get("avatarMedium")
        or u.get("avatar_medium")
        or "",
    ).strip()
    return {
        "unique_id": unique,
        "nickname": nick,
        "follower_count": followers,
        "avatar_url": avatar or None,
    }


@router.get("/channel/user-search")
async def channel_user_search_endpoint(
    user: dict = Depends(require_user),
    keyword: str = Query(
        ...,
        min_length=2,
        max_length=64,
        description="Từ khóa tìm kênh TikTok (username hoặc tên).",
    ),
) -> JSONResponse:
    """Tìm kênh TikTok (EnsembleData user search) — không trừ credit."""
    from getviews_pipeline import ensemble
    from getviews_pipeline.ensemble import EnsembleDailyBudgetExceeded, fetch_user_search

    _ = user  # JWT gate only
    kw = keyword.strip()
    if len(kw) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Từ khóa quá ngắn")

    try:
        with ensemble.ed_call_site("channel.user_search"):
            raw_users, _next = await fetch_user_search(kw, cursor=0)
    except EnsembleDailyBudgetExceeded as exc:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "ensemble_quota", "detail": str(exc)},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[channel/user-search] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    out: list[dict[str, Any]] = []
    for row in raw_users[:20]:
        if not isinstance(row, dict):
            continue
        item = _summarize_user_search_row(row)
        if item:
            out.append(item)
    return JSONResponse({"users": out})


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

    Reads ``profiles.tiktok_handle`` + ``profiles.creator_niche_id`` for the
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
        pres = sb_user.table("profiles").select(
            "tiktok_handle, creator_niche_id"
        ).single().execute()
    except Exception as exc:
        logger.warning("[channel/refresh-mine] profile read failed: %s", exc)
        raise HTTPException(status_code=500, detail="profile_read_failed") from exc

    profile = pres.data or {}
    handle = (profile.get("tiktok_handle") or "").strip().lstrip("@")

    # Two-axis refactor PR5: prefer creator_niche_id (canonical) and
    # resolve to legacy niche_id for the per-handle corpus query.
    from getviews_pipeline.profile_niches import resolve_legacy_niche_from_profile_row

    niche_id = resolve_legacy_niche_from_profile_row(profile)

    if not handle:
        return JSONResponse({"status": "error", "reason": "no_handle_on_profile"}, status_code=400)
    if niche_id is None:
        return JSONResponse({"status": "error", "reason": "no_niche_on_profile"}, status_code=400)

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


# ---------------------------------------------------------------------------
# POST /channel/diagnose — narrative SSE diagnosis for any TikTok handle
# ---------------------------------------------------------------------------

# Section markers the server parses from Gemini output
_SECTION_HEADER_RE = re.compile(
    r"^=== (verdict|what_worked|what_falling|video_vs_channel"
    r"|competitive_landscape|recommendations) ===$",
    re.MULTILINE,
)
_TITLE_RE = re.compile(r"^TITLE:\s*(.+)$", re.MULTILINE)
# Numbered recommendation: "N. **Bold lead**\nbody"
_REC_RE = re.compile(
    r"^\s*(\d+)\.\s+\*\*(.+?)\*\*\s*\n(.*?)(?=\n\s*\d+\.|\Z)",
    re.DOTALL | re.MULTILINE,
)


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()


def _chunk_text(text: str, chunk_size: int = 30) -> list[str]:
    """Split text into ~chunk_size character chunks for typing UX."""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def _parse_sections_from_narrative(
    narrative: str,
    trajectory: str,
) -> list[dict[str, Any]]:
    """Split narrative on stable section headers, extract TITLE lines."""
    from getviews_pipeline.channel_diagnose_prompts import get_default_title

    parts = _SECTION_HEADER_RE.split(narrative)
    sections = []
    for i in range(1, len(parts), 2):
        section_id = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        title_m = _TITLE_RE.search(body)
        title = title_m.group(1).strip() if title_m else get_default_title(section_id, trajectory)
        # Remove the TITLE line from body
        clean_body = _TITLE_RE.sub("", body, count=1).strip()
        sections.append({"section_id": section_id, "title": title, "text": clean_body})
    return sections


def _parse_recommendations(rec_body: str) -> list[dict[str, Any]]:
    """Parse numbered markdown bold recommendations from a section body."""
    items = []
    for m in _REC_RE.finditer(rec_body):
        idx = int(m.group(1))
        title = m.group(2).strip()
        body = m.group(3).strip()
        items.append({"index": idx, "title": title, "body": body})
    return items


def _fetch_channel_diagnoses_cache(
    sb_service: Any,
    handle: str,
    video_url: str,
    niche_id: int,
    max_age_days: int = 7,
) -> dict[str, Any] | None:
    """Return cached channel_diagnoses row if within max_age_days."""
    try:
        cutoff = (datetime.now(tz=UTC) - timedelta(days=max_age_days)).isoformat()
        res = (
            sb_service.table("channel_diagnoses")
            .select("*")
            .eq("handle", handle)
            .eq("video_url", video_url)
            .eq("niche_id", niche_id)
            .gte("computed_at", cutoff)
            .maybe_single()
            .execute()
        )
        return res.data if res.data else None
    except Exception as exc:
        logger.warning("[channel_diagnose] cache lookup failed: %s", exc)
        return None


def _persist_channel_diagnoses(
    sb_service: Any,
    handle: str,
    video_url: str,
    niche_id: int,
    trajectory_shape: str,
    sections: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    top_performers: list[dict[str, Any]],
    worst_performers: list[dict[str, Any]],
    ugc_creators: list[dict[str, Any]],
    channel_pattern: dict[str, Any],
    inflection: dict[str, Any] | None,
    creator_match: dict[str, Any] | None,
    video_count: int,
) -> None:
    try:
        sb_service.table("channel_diagnoses").upsert({
            "handle": handle,
            "video_url": video_url,
            "niche_id": niche_id,
            "trajectory_shape": trajectory_shape,
            "sections": sections,
            "recommendations": recommendations,
            "top_performers": top_performers,
            "worst_performers": worst_performers,
            "ugc_creators": ugc_creators,
            "channel_pattern": channel_pattern,
            "inflection": inflection,
            "creator_match": creator_match,
            "video_count": video_count,
            "computed_at": datetime.now(tz=UTC).isoformat(),
        }).execute()
    except Exception as exc:
        logger.warning("[channel_diagnose] persist failed: %s", exc)


async def _run_channel_diagnose(
    user_id: str,
    access_token: str,
    handle: str,
    niche_id: int,
    video_url: str,
    step_queue: asyncio.Queue,
) -> dict[str, Any]:
    """Orchestrator: runs the full channel diagnosis pipeline in a thread pool."""
    from getviews_pipeline.channel_diagnose import (
        _fetch_niche_benchmarks,
        normalize_handle,
    )
    from getviews_pipeline.channel_diagnose import (
        build_channel_pattern,
        classify_trajectory,
        compute_creator_match,
        compute_inflection_point,
        compute_recent_window_stats,
        extract_dominant_format,
        fetch_channel_videos_live,
        fetch_ugc_creators,
        select_niche_peer_videos,
        select_quarterly_breakout_videos,
        select_top_performers,
        select_worst_performers,
    )
    from getviews_pipeline.channel_diagnose_prompts import (
        CHANNEL_DIAGNOSIS_SYSTEM_PROMPT,
        build_channel_diagnosis_context,
        get_default_title,
    )

    handle = normalize_handle(handle)

    # --- Step 1: Load channel videos ---
    await step_queue.put({"type": "step_start", "index": 1, "label": "Tải dữ liệu kênh"})
    videos = await fetch_channel_videos_live(handle)
    if not videos:
        return {"error": "channel_not_found"}
    await step_queue.put({"type": "step_done", "index": 1, "count": len(videos)})

    # --- Step 2: Classify format ---
    await step_queue.put({"type": "step_start", "index": 2, "label": "Phân loại format"})
    channel_pattern = build_channel_pattern(videos)
    await step_queue.put({"type": "step_done", "index": 2})

    # --- Step 3: Inflection + trajectory ---
    await step_queue.put({"type": "step_start", "index": 3, "label": "Tìm điểm inflection"})
    recent_window = compute_recent_window_stats(videos)
    inflection = compute_inflection_point(videos)
    trajectory = classify_trajectory(channel_pattern, recent_window, inflection, videos)
    await step_queue.put({"type": "trajectory", "trajectory": trajectory})
    await step_queue.put({"type": "step_done", "index": 3})

    # --- Step 4: UGC creators ---
    await step_queue.put({"type": "step_start", "index": 4, "label": "Tìm UGC creators"})
    # Resolve niche slug for hashtag scouting
    sb_user = user_supabase(access_token)
    sb_svc = get_service_client()
    niche_slug = ""
    try:
        nr = sb_user.table("creator_niches").select("slug").eq("id", niche_id).maybe_single().execute()
        niche_slug = str((nr.data or {}).get("slug") or "")
    except Exception:
        pass

    channel_avg = channel_pattern.get("global_avg_views", 0)
    ugc_creators = await fetch_ugc_creators(handle, niche_slug, videos, channel_avg)
    niche_benchmarks = await run_sync(_fetch_niche_benchmarks, sb_user, niche_id=niche_id)
    await step_queue.put({"type": "step_done", "index": 4, "count": len(ugc_creators)})

    # --- Tile selection (trajectory-aware) ---
    creator_match: dict[str, Any] | None = None
    if video_url:
        try:
            # Try corpus first
            vid_res = (
                sb_user.table("video_corpus")
                .select("views,content_format")
                .eq("video_url", video_url)
                .maybe_single()
                .execute()
            )
            vrow = vid_res.data
            if vrow:
                creator_match = compute_creator_match(
                    str(vrow.get("content_format") or "product_closeup"),
                    int(vrow.get("views") or 0),
                    channel_pattern,
                )
        except Exception as exc:
            logger.debug("[channel_diagnose] creator_match corpus lookup failed: %s", exc)

    top_performers: list[dict[str, Any]] = []
    worst_performers: list[dict[str, Any]] = []

    if trajectory == "breakout":
        top_performers = [dict(t) for t in select_quarterly_breakout_videos(videos)]
    elif trajectory == "new_account":
        peer_tiles = await select_niche_peer_videos(sb_user, niche_id, handle)
        top_performers = [dict(t) for t in peer_tiles]
    else:
        top_performers = [dict(t) for t in select_top_performers(videos, channel_pattern)]
        if trajectory in ("decline_from_peak", "stagnant", "bursty"):
            worst_performers = [dict(t) for t in select_worst_performers(videos)]
        elif trajectory == "steady_growth":
            # §3 = top from latest quarter
            from getviews_pipeline.channel_diagnose import _now, _quarter_key
            now_q = _quarter_key(_now())
            q_vids = [v for v in videos if v.get("posted_at") and _quarter_key(v["posted_at"]) == now_q]
            if q_vids:
                worst_performers = [
                    dict(t) for t in select_top_performers(q_vids, channel_pattern, limit=4)
                ]

    # --- Step 5: Gemini synthesis ---
    await step_queue.put({"type": "step_start", "index": 5, "label": "Đang viết phân tích"})

    context_str = build_channel_diagnosis_context(
        handle=handle,
        videos=videos,
        trajectory=trajectory,
        channel_pattern=channel_pattern,
        recent_window_30d=recent_window,
        inflection=inflection,
        top_performers=top_performers,
        worst_performers=worst_performers,
        creator_match=creator_match,
        ugc_creators=[dict(u) for u in ugc_creators],
        niche_benchmarks=niche_benchmarks,
    )

    from google.genai import types as genai_types

    from getviews_pipeline.config import GEMINI_SYNTHESIS_FALLBACKS, GEMINI_SYNTHESIS_MODEL
    from getviews_pipeline.gemini import _generate_content_models

    try:
        response = await run_sync(
            _generate_content_models,
            context_str,
            primary_model=GEMINI_SYNTHESIS_MODEL,
            fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
            config=genai_types.GenerateContentConfig(
                system_instruction=CHANNEL_DIAGNOSIS_SYSTEM_PROMPT,
                temperature=0.7,
            ),
            call_site="channel_diagnose",
            user_id=user_id,
        )
        narrative = response.text or ""
    except Exception as exc:
        logger.error("[channel_diagnose] Gemini failed user=%s: %s", user_id, exc)
        return {"error": "stream_failed"}

    # --- Parse sections ---
    sections = _parse_sections_from_narrative(narrative, trajectory)
    section_ids = {s["section_id"] for s in sections}

    mandatory = {"verdict", "recommendations"}
    if not mandatory.issubset(section_ids):
        # Hard fallback: emit raw narrative as a single fallback section
        logger.warning(
            "[channel_diagnose] mandatory section missing section_ids=%s trajectory=%s",
            section_ids, trajectory,
        )
        sections = [{
            "section_id": "fallback",
            "title": get_default_title("verdict", trajectory),
            "text": narrative,
        }]

    # Emit sections
    tile_map = {
        "what_worked": top_performers,
        "competitive_landscape": [dict(u) for u in ugc_creators],
        "video_vs_channel": [],
    }
    if trajectory not in ("breakout", "new_account"):
        tile_map["what_falling"] = worst_performers

    recommendations: list[dict[str, Any]] = []
    for section in sections:
        sid = section["section_id"]
        tiles = tile_map.get(sid, [])
        is_ugc = sid == "competitive_landscape"
        section_start_payload: dict[str, Any] = {
            "type": "section_start",
            "section_id": sid,
            "title": section["title"],
        }
        if tiles and not is_ugc:
            section_start_payload["embedded_tiles"] = tiles
        if is_ugc and ugc_creators:
            section_start_payload["embedded_creators"] = [dict(u) for u in ugc_creators]

        await step_queue.put(section_start_payload)

        if sid == "recommendations":
            rec_items = _parse_recommendations(section["text"])
            if len(rec_items) < 3:
                # Fallback: emit raw text chunks
                for chunk in _chunk_text(section["text"]):
                    await step_queue.put({"type": "text_chunk", "content": chunk})
            else:
                recommendations = rec_items
                for item in rec_items:
                    await step_queue.put({"type": "recommendation_item", **item})
        else:
            for chunk in _chunk_text(section["text"]):
                await step_queue.put({"type": "text_chunk", "content": chunk})

        await step_queue.put({"type": "section_done", "section_id": sid})

    # --- Persist ---
    niche_peer_count = int((niche_benchmarks or {}).get("channel_count") or 0)
    niche_thin = niche_peer_count < 10

    now_str = datetime.now(tz=UTC).strftime("%H:%M %d/%m/%Y")
    provenance = (
        f"Phân tích dựa trên {len(videos)} videos · scraped {now_str} · TikTok public data"
    )

    dominant_fmt = extract_dominant_format(channel_pattern)

    await run_sync(
        _persist_channel_diagnoses,
        sb_svc,
        handle,
        video_url,
        niche_id,
        trajectory,
        sections,
        recommendations,
        top_performers,
        worst_performers,
        [dict(u) for u in ugc_creators],
        channel_pattern,
        inflection,
        creator_match,
        len(videos),
    )

    return {
        "sections": sections,
        "recommendations": recommendations,
        "top_performers": top_performers,
        "worst_performers": worst_performers,
        "ugc_creators": [dict(u) for u in ugc_creators],
        "channel_pattern": channel_pattern,
        "inflection": inflection,
        "creator_match": creator_match,
        "trajectory_shape": trajectory,
        "video_count": len(videos),
        "provenance": provenance,
        "niche_thin": niche_thin,
        "cache_hit": False,
        "dominant_format": dominant_fmt,
    }


@router.post("/channel/diagnose", response_model=None)
async def channel_diagnose_endpoint(
    handle: str = Query(..., description="TikTok handle (with or without @)"),
    niche_id: int = Query(..., description="Creator niche ID for benchmarks"),
    video_url: str = Query("", description="Optional target video URL for §4"),
    resume_stream_id: str | None = Query(None),
    resume_from_seq: int | None = Query(None, ge=0),
    user: dict[str, Any] = Depends(require_user),
) -> StreamingResponse | JSONResponse:
    """POST /channel/diagnose — Lightreel-style narrative diagnosis with SSE (TD-4)."""
    from getviews_pipeline.channel_diagnose import (
        InsufficientCreditsError,
        _decrement_credit_or_raise,
        normalize_handle,
    )

    user_id = str(user["user_id"])
    access_token = str(user["access_token"])
    handle_norm = normalize_handle(handle)

    inflight_key = f"{user_id}:{handle_norm}:{video_url}"

    async def event_generator() -> AsyncIterator[bytes]:
        nonlocal inflight_key

        stream_id = resume_stream_id or str(uuid.uuid4())
        seq = 0

        # --- TD-4 replay ---
        if resume_stream_id and resume_from_seq is not None:
            cached = get_stream_chunks(resume_stream_id)
            if cached:
                for item in cached:
                    item_seq = int(item.get("seq") or 0)
                    if item_seq <= resume_from_seq:
                        continue
                    is_terminal = bool(item.get("done"))
                    yield _sse(
                        {"stream_id": stream_id, **item}
                        if is_terminal
                        else {"stream_id": stream_id, **item, "done": False}
                    )
                    await asyncio.sleep(0.005)
                return

        # --- In-flight guard (TD-3) ---
        if inflight_key in _DIAGNOSE_INFLIGHT:
            yield _sse({"stream_id": stream_id, "seq": 0, "done": True, "status": "already_in_flight"})
            return

        # --- Hello frame ---
        yield _sse({"stream_id": stream_id, "seq": 0, "hello": True, "done": False})

        # --- 7-day cache lookup ---
        sb_svc = get_service_client()
        cached_row = _fetch_channel_diagnoses_cache(sb_svc, handle_norm, video_url, niche_id)
        if cached_row:
            # Replay cached narrative via the same section-tagged event sequence
            seq = 1
            yield _sse({"stream_id": stream_id, "seq": seq, "type": "cache_hit", "done": False})
            trajectory = str(cached_row.get("trajectory_shape") or "stagnant")
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "type": "trajectory",
                         "trajectory": trajectory, "done": False})
            sections = cached_row.get("sections") or []
            ugc_creators = cached_row.get("ugc_creators") or []
            top_performers = cached_row.get("top_performers") or []
            worst_performers = cached_row.get("worst_performers") or []
            recommendations = cached_row.get("recommendations") or []

            for section in sections:
                sid = section.get("section_id", "")
                seq += 1
                sec_evt: dict[str, Any] = {
                    "stream_id": stream_id, "seq": seq, "type": "section_start",
                    "section_id": sid, "title": section.get("title", ""),
                    "done": False,
                }
                if sid == "what_worked":
                    sec_evt["embedded_tiles"] = top_performers
                elif sid == "what_falling":
                    sec_evt["embedded_tiles"] = worst_performers
                elif sid == "competitive_landscape" and ugc_creators:
                    sec_evt["embedded_creators"] = ugc_creators
                yield _sse(sec_evt)

                if sid == "recommendations":
                    for item in recommendations:
                        seq += 1
                        yield _sse({"stream_id": stream_id, "seq": seq,
                                     "type": "recommendation_item", "done": False, **item})
                        await asyncio.sleep(0.03)
                else:
                    for chunk in _chunk_text(section.get("text", "")):
                        seq += 1
                        yield _sse({"stream_id": stream_id, "seq": seq,
                                     "type": "text_chunk", "content": chunk, "done": False})
                        await asyncio.sleep(0.03)

                seq += 1
                yield _sse({"stream_id": stream_id, "seq": seq,
                             "type": "section_done", "section_id": sid, "done": False})

            # Terminal payload + done
            computed_at = str(cached_row.get("computed_at") or "")
            niche_thin = int((cached_row.get("channel_pattern") or {}).get("total_videos") or 0) == 0
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "payload": {
                "trajectory_shape": trajectory,
                "sections": sections,
                "recommendations": recommendations,
                "top_performers": top_performers,
                "worst_performers": worst_performers,
                "ugc_creators": ugc_creators,
                "channel_pattern": cached_row.get("channel_pattern") or {},
                "inflection": cached_row.get("inflection"),
                "creator_match": cached_row.get("creator_match"),
                "video_count": cached_row.get("video_count") or 0,
                "provenance": f"Phân tích cập nhật: {computed_at[:16]}",
                "niche_thin": niche_thin,
                "cache_hit": True,
            }, "done": False})
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "done": True})
            return

        # --- Cache miss: deduct credit, then run ---
        sb_user = user_supabase(access_token)
        try:
            await run_sync(_decrement_credit_or_raise, sb_user, user_id=user_id)
        except InsufficientCreditsError:
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "done": True, "error": "insufficient_credits"})
            return
        except Exception as exc:
            logger.error("[channel_diagnose] credit deduction failed user=%s: %s", user_id, exc)
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "done": True, "error": "stream_failed"})
            return

        _DIAGNOSE_INFLIGHT.add(inflight_key)
        step_queue: asyncio.Queue = asyncio.Queue()
        stream_cache: list[dict[str, Any]] = []

        diagnose_task = asyncio.create_task(
            _run_channel_diagnose(user_id, access_token, handle_norm, niche_id, video_url, step_queue)
        )

        _HB = 10.0
        try:
            while not diagnose_task.done():
                while True:
                    try:
                        event = step_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    seq += 1
                    item = {"seq": seq, **event}
                    stream_cache.append(item)
                    yield _sse({"stream_id": stream_id, **item, "done": False})
                done_set, _ = await asyncio.wait({diagnose_task}, timeout=_HB)
                if not done_set:
                    seq += 1
                    yield _sse({"stream_id": stream_id, "seq": seq, "heartbeat": True, "done": False})

            # Drain queue after task completes
            while True:
                try:
                    event = step_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                seq += 1
                item = {"seq": seq, **event}
                stream_cache.append(item)
                yield _sse({"stream_id": stream_id, **item, "done": False})

            try:
                out = diagnose_task.result()
            except Exception as exc:
                logger.exception("[channel_diagnose] task failed user=%s: %s", user_id, exc)
                seq += 1
                yield _sse({"stream_id": stream_id, "seq": seq, "done": True, "error": "stream_failed"})
                return

            error = out.get("error")
            if error:
                seq += 1
                yield _sse({"stream_id": stream_id, "seq": seq, "done": True, "error": error})
                return

            seq += 1
            payload_item = {"seq": seq, "payload": out}
            seq += 1
            done_item = {"seq": seq, "done": True}

            put_stream_chunks(stream_id, stream_cache + [payload_item, done_item])

            yield _sse({"stream_id": stream_id, **payload_item, "done": False})
            yield _sse({"stream_id": stream_id, **done_item})

        finally:
            _DIAGNOSE_INFLIGHT.discard(inflight_key)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
