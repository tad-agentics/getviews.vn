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
# /channel/diagnose now uses the DB-side ``begin_processing`` RPC for the
# TD-3 atomic single-flight lock (mirrors routers/intent.py) so cross-pod
# requests can't double-deduct credits. The previous module-level
# ``_DIAGNOSE_INFLIGHT`` set was per-instance and TOCTOU-racy.

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
    r"|competitive_landscape|next_video|recommendations) ===$",
    re.MULTILINE,
)
_TITLE_RE = re.compile(r"^TITLE:\s*(.+)$", re.MULTILINE)
# Numbered recommendation: "N. **Bold lead**\nbody"
_REC_RE = re.compile(
    r"^\s*(\d+)\.\s+\*\*(.+?)\*\*\s*\n(.*?)(?=\n\s*\d+\.|\Z)",
    re.DOTALL | re.MULTILINE,
)
_REC_STOP_SPLIT = re.compile(r"\n---\s*NGỪNG LÀM\s*---\s*\n", re.IGNORECASE | re.MULTILINE)


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
    """Parse recommendations + optional --- NGỪNG LÀM --- anti-block."""
    parts = _REC_STOP_SPLIT.split(rec_body, maxsplit=1)
    main = parts[0].strip()
    anti_raw = parts[1].strip() if len(parts) > 1 else ""
    items: list[dict[str, Any]] = []
    for m in _REC_RE.finditer(main):
        idx = int(m.group(1))
        title = m.group(2).strip()
        body = m.group(3).strip()
        kind = "hero" if idx == 1 else "regular"
        if "ƯU TIÊN" in title.upper():
            kind = "hero"
        items.append({"index": idx, "title": title, "body": body, "kind": kind})
    if anti_raw:
        items.append({"index": 99, "title": "Ngừng làm", "body": anti_raw, "kind": "anti"})
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
    *,
    score_card: dict[str, Any] | None = None,
    score_card_captions: dict[str, str] | None = None,
    verdict_tiles: list[dict[str, Any]] | None = None,
    hashtag_insights: list[dict[str, Any]] | None = None,
    next_video: dict[str, Any] | None = None,
    channel_persona: dict[str, Any] | None = None,
    peer_source: str | None = None,
) -> None:
    payload_card = dict(score_card or {})
    if score_card_captions:
        payload_card["captions"] = score_card_captions
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
            "score_card": payload_card,
            "verdict_tiles": verdict_tiles or [],
            "hashtag_insights": hashtag_insights or [],
            "next_video": next_video,
            "channel_persona": channel_persona or {},
            "peer_source": peer_source,
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
        build_channel_pattern,
        classify_trajectory,
        compute_creator_match,
        compute_hashtag_insights,
        compute_inflection_point,
        compute_recent_window_stats,
        compute_score_card,
        derive_channel_persona,
        derive_next_video_concept,
        fetch_channel_videos_live,
        hashtag_caption_for_insight,
        normalize_handle,
        normalize_peer_creator_for_fe,
        render_score_card_captions,
        select_niche_peer_creators,
        select_niche_peer_videos,
        select_quarterly_breakout_videos,
        select_top_performers,
        select_verdict_tiles,
        select_worst_performers,
    )
    from getviews_pipeline.channel_diagnose_prompts import (
        CHANNEL_DIAGNOSIS_SYSTEM_PROMPT,
        build_channel_diagnosis_context,
        get_default_title,
    )
    from getviews_pipeline.profile_niches import legacy_niche_id_for_creator_niche

    handle = normalize_handle(handle)
    legacy_nid = legacy_niche_id_for_creator_niche(niche_id) or niche_id

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

    # --- Step 4: Persona, corpus peers, benchmarks, score card ---
    await step_queue.put({"type": "step_start", "index": 4, "label": "So sánh ngách & peer"})
    sb_user = user_supabase(access_token)
    sb_svc = get_service_client()
    niche_slug = ""
    try:
        nr = sb_user.table("creator_niches").select("slug").eq("id", niche_id).maybe_single().execute()
        niche_slug = str((nr.data or {}).get("slug") or "")
    except Exception:
        pass

    channel_avg = float(channel_pattern.get("global_avg_views") or 0)
    persona = await derive_channel_persona(sb_user, handle, legacy_nid, channel_pattern)
    peer_creators_raw, peer_source = await select_niche_peer_creators(
        sb_user,
        legacy_nid,
        persona.get("dominant_content_class_id"),
        handle,
        channel_avg,
        limit=3,
    )
    ugc_creators = [
        normalize_peer_creator_for_fe(dict(u), niche_slug=niche_slug)
        for u in peer_creators_raw
    ]
    niche_benchmarks = await run_sync(_fetch_niche_benchmarks, sb_user, niche_id=legacy_nid)

    score_card = compute_score_card(
        videos,
        channel_pattern,
        recent_window,
        inflection,
        niche_benchmarks,
        persona,
        trajectory,
    )
    score_captions = render_score_card_captions(score_card)
    await step_queue.put({
        "type": "score_card",
        "data": score_card,
        "captions": score_captions,
    })
    ch_avg_float = float(channel_pattern.get("global_avg_views") or 1)
    hashtag_insights_raw = compute_hashtag_insights(videos)
    hashtag_payload = [
        {**h, "caption": hashtag_caption_for_insight(h, ch_avg_float)}
        for h in hashtag_insights_raw
    ]
    verdict_tiles = [dict(t) for t in select_verdict_tiles(videos)]
    next_video_seed = derive_next_video_concept(peer_creators_raw, channel_pattern, videos)

    await step_queue.put({"type": "step_done", "index": 4, "count": len(ugc_creators)})

    # --- creator_match + trajectory-aware performer tiles ---
    creator_match: dict[str, Any] | None = None
    if video_url:
        try:
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
        peer_tiles = await select_niche_peer_videos(sb_user, legacy_nid, handle)
        top_performers = [dict(t) for t in peer_tiles]
    else:
        top_performers = [dict(t) for t in select_top_performers(videos, channel_pattern)]
        if trajectory in ("decline_from_peak", "stagnant", "bursty"):
            worst_performers = [dict(t) for t in select_worst_performers(videos)]
        elif trajectory == "steady_growth":
            from getviews_pipeline.channel_diagnose import _now, _quarter_key
            now_q = _quarter_key(_now())
            q_vids = [
                v for v in videos
                if v.get("posted_at") and _quarter_key(v["posted_at"]) == now_q
            ]
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
        ugc_creators=peer_creators_raw,
        niche_benchmarks=niche_benchmarks,
        channel_persona=persona,
        peer_source=peer_source,
        next_video_concept=next_video_seed,
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
                temperature=0.7,
            ),
            call_site="channel_diagnose",
            user_id=user_id,
            synthesis_cache_kind="channel_diagnose",
            synthesis_cache_system_text=CHANNEL_DIAGNOSIS_SYSTEM_PROMPT,
        )
        narrative = response.text or ""
    except Exception as exc:
        logger.error("[channel_diagnose] Gemini failed user=%s: %s", user_id, exc)
        return {"error": "stream_failed"}

    sections_raw = _parse_sections_from_narrative(narrative, trajectory)
    section_ids = {s["section_id"] for s in sections_raw}

    mandatory = {"verdict", "recommendations"}
    if not mandatory.issubset(section_ids):
        logger.warning(
            "[channel_diagnose] mandatory section missing section_ids=%s trajectory=%s",
            section_ids,
            trajectory,
        )
        sections_raw = [{
            "section_id": "fallback",
            "title": get_default_title("verdict", trajectory),
            "text": narrative,
        }]

    if "fallback" not in {s["section_id"] for s in sections_raw}:
        if "next_video" not in {s["section_id"] for s in sections_raw} and next_video_seed:
            sections_raw.append({
                "section_id": "next_video",
                "title": get_default_title("next_video", trajectory),
                "text": str(next_video_seed.get("rationale_struct") or ""),
            })

    parsed_map = {s["section_id"]: s for s in sections_raw}

    order = [
        "verdict", "what_worked", "what_falling", "video_vs_channel",
        "competitive_landscape", "hashtag_insights", "next_video", "recommendations",
    ]

    tile_map: dict[str, list[dict[str, Any]]] = {
        "verdict": verdict_tiles,
        "what_worked": top_performers,
        "competitive_landscape": [],
        "video_vs_channel": [],
    }
    if trajectory not in ("breakout", "new_account"):
        tile_map["what_falling"] = worst_performers

    recommendations: list[dict[str, Any]] = []
    sections_ordered: list[dict[str, Any]] = []

    async def _emit_one(section: dict[str, Any]) -> None:
        sid = section["section_id"]
        tiles = tile_map.get(sid, [])
        is_landscape = sid == "competitive_landscape"
        start: dict[str, Any] = {
            "type": "section_start",
            "section_id": sid,
            "title": section["title"],
        }
        if sid == "verdict" and verdict_tiles:
            start["embedded_tiles"] = verdict_tiles
        elif tiles and not is_landscape:
            start["embedded_tiles"] = tiles
        if is_landscape and ugc_creators:
            start["embedded_creators"] = ugc_creators
        if sid == "next_video" and next_video_seed:
            start["next_video"] = next_video_seed
        await step_queue.put(start)
        if sid == "recommendations":
            rec_items = _parse_recommendations(section["text"])
            non_anti = [r for r in rec_items if r.get("kind") != "anti"]
            if len(non_anti) < 2:
                for chunk in _chunk_text(section["text"]):
                    await step_queue.put({"type": "text_chunk", "content": chunk})
            else:
                for item in rec_items:
                    await step_queue.put({"type": "recommendation_item", **item})
        else:
            for chunk in _chunk_text(section["text"]):
                await step_queue.put({"type": "text_chunk", "content": chunk})
        await step_queue.put({"type": "section_done", "section_id": sid})

    if sections_raw and sections_raw[0].get("section_id") == "fallback":
        sections_ordered = list(sections_raw)
        for section in sections_ordered:
            await _emit_one(section)
    else:
        for sid in order:
            if sid == "what_falling" and trajectory in ("breakout", "new_account"):
                continue
            if sid == "video_vs_channel" and not video_url:
                continue
            if sid == "hashtag_insights":
                sec_title = get_default_title("hashtag_insights", trajectory)
                hint = f"Dựa trên {len(videos)} video đã phân tích (caption public)."
                sections_ordered.append({"section_id": sid, "title": sec_title, "text": hint})
                await step_queue.put({
                    "type": "section_start",
                    "section_id": sid,
                    "title": sec_title,
                    "hashtag_insights": hashtag_payload,
                })
                for chunk in _chunk_text(hint):
                    await step_queue.put({"type": "text_chunk", "content": chunk})
                await step_queue.put({"type": "section_done", "section_id": sid})
                continue

            sec = parsed_map.get(sid)
            if not sec:
                continue
            sections_ordered.append(sec)
            await _emit_one(sec)

    now_str = datetime.now(tz=UTC).strftime("%H:%M %d/%m/%Y")
    provenance = (
        f"Phân tích dựa trên {len(videos)} videos · scraped {now_str} · TikTok public data"
    )

    nv_sec = parsed_map.get("next_video")
    next_video_out: dict[str, Any] | None = None
    if next_video_seed:
        next_video_out = dict(next_video_seed)
        if nv_sec:
            next_video_out["narrative"] = nv_sec.get("text") or ""

    await run_sync(
        _persist_channel_diagnoses,
        sb_svc,
        handle,
        video_url,
        niche_id,
        trajectory,
        sections_ordered,
        recommendations,
        top_performers,
        worst_performers,
        ugc_creators,
        channel_pattern,
        inflection,
        creator_match,
        len(videos),
        score_card=score_card,
        score_card_captions=score_captions,
        verdict_tiles=verdict_tiles,
        hashtag_insights=hashtag_payload,
        next_video=next_video_out,
        channel_persona=persona,
        peer_source=peer_source,
    )

    return {
        "sections": sections_ordered,
        "recommendations": recommendations,
        "top_performers": top_performers,
        "worst_performers": worst_performers,
        "ugc_creators": ugc_creators,
        "channel_pattern": channel_pattern,
        "inflection": inflection,
        "creator_match": creator_match,
        "trajectory_shape": trajectory,
        "video_count": len(videos),
        "provenance": provenance,
        "cache_hit": False,
        "score_card": score_card,
        "score_card_captions": score_captions,
        "verdict_tiles": verdict_tiles,
        "hashtag_insights": hashtag_payload,
        "next_video": next_video_out,
        "channel_persona": persona,
        "peer_source": peer_source,
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
    # Canonicalise the URL before it touches the (handle, video_url,
    # niche_id) cache key. Without this, share-sheet pastes with
    # trailing slashes / ``?_r=1`` / http vs https / www-vs-bare miss
    # the cache and re-charge a credit — same bug normalize_tiktok_url
    # was added to prevent on /video/analyze.
    from getviews_pipeline.video_analyze import normalize_tiktok_url
    video_url = normalize_tiktok_url(video_url) if video_url else video_url

    async def event_generator() -> AsyncIterator[bytes]:
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
            verdict_tiles = cached_row.get("verdict_tiles") or []
            hashtag_insights_row = cached_row.get("hashtag_insights") or []
            next_video_row = cached_row.get("next_video")
            channel_persona_row = cached_row.get("channel_persona") or {}
            peer_source_row = cached_row.get("peer_source")

            score_all = dict(cached_row.get("score_card") or {})
            score_captions_replay: dict[str, str] | None = None
            captions_raw = score_all.pop("captions", None)
            if isinstance(captions_raw, dict):
                score_captions_replay = {str(k): str(v) for k, v in captions_raw.items()}
            if score_all:
                seq += 1
                sc_evt: dict[str, Any] = {
                    "stream_id": stream_id,
                    "seq": seq,
                    "type": "score_card",
                    "data": score_all,
                    "done": False,
                }
                if score_captions_replay:
                    sc_evt["captions"] = score_captions_replay
                yield _sse(sc_evt)

            for section in sections:
                sid = section.get("section_id", "")
                seq += 1
                sec_evt: dict[str, Any] = {
                    "stream_id": stream_id, "seq": seq, "type": "section_start",
                    "section_id": sid, "title": section.get("title", ""),
                    "done": False,
                }
                if sid == "verdict" and verdict_tiles:
                    sec_evt["embedded_tiles"] = verdict_tiles
                elif sid == "what_worked":
                    sec_evt["embedded_tiles"] = top_performers
                elif sid == "what_falling":
                    sec_evt["embedded_tiles"] = worst_performers
                elif sid == "competitive_landscape" and ugc_creators:
                    sec_evt["embedded_creators"] = ugc_creators
                elif sid == "hashtag_insights":
                    sec_evt["hashtag_insights"] = hashtag_insights_row
                elif sid == "next_video" and next_video_row:
                    sec_evt["next_video"] = next_video_row
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
                "cache_hit": True,
                "score_card": score_all,
                "score_card_captions": score_captions_replay or {},
                "verdict_tiles": verdict_tiles,
                "hashtag_insights": hashtag_insights_row,
                "next_video": next_video_row,
                "channel_persona": channel_persona_row,
                "peer_source": peer_source_row,
            }, "done": False})
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "done": True})
            return

        # --- Cache miss path: TD-3 atomic lock BEFORE credit deduction ---
        # Mirrors routers/intent.py:284. ``begin_processing`` flips
        # ``profiles.is_processing`` atomically and returns the prior
        # value; True means the lock was already held (concurrent tab,
        # double-click). Acquire BEFORE decrement_credit so two parallel
        # requests can't both pass the pre-check and both charge a
        # credit — the previous in-process set guard (``_DIAGNOSE_INFLIGHT``)
        # was per-instance and TOCTOU-racy.
        sb_user = user_supabase(access_token)
        try:
            lock_resp = await run_sync(
                lambda: sb_user.rpc("begin_processing", {"p_user_id": user_id}).execute(),
            )
        except Exception as exc:
            logger.warning("[channel_diagnose] begin_processing failed user=%s: %s", user_id, exc)
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "done": True, "error": "stream_failed"})
            return
        if lock_resp.data is True:
            # Lock was already held — concurrent request from this user.
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "done": True, "status": "already_in_flight"})
            return

        # From here on we MUST release the lock on every exit path,
        # including credit-failure returns.
        async def _release_lock() -> None:
            try:
                await run_sync(
                    lambda: sb_user.rpc("end_processing", {"p_user_id": user_id}).execute(),
                )
            except Exception as exc:
                logger.warning("[channel_diagnose] end_processing failed user=%s: %s", user_id, exc)

        try:
            await run_sync(_decrement_credit_or_raise, sb_user, user_id=user_id)
        except InsufficientCreditsError:
            await _release_lock()
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "done": True, "error": "insufficient_credits"})
            return
        except Exception as exc:
            await _release_lock()
            logger.error("[channel_diagnose] credit deduction failed user=%s: %s", user_id, exc)
            seq += 1
            yield _sse({"stream_id": stream_id, "seq": seq, "done": True, "error": "stream_failed"})
            return

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
            await _release_lock()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
