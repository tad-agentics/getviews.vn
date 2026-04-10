"""Intent pipelines: Ensemble search + parallel Gemini analysis + synthesis."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import analyze_aweme, analyze_tiktok_url
from getviews_pipeline.gemini import synthesize_intent_markdown
from getviews_pipeline.helpers import (
    filter_recency,
    infer_niche_from_hashtags,
    merge_aweme_lists,
    select_reference_videos,
)
from getviews_pipeline.intents import QueryIntent
from getviews_pipeline.runtime import get_analysis_semaphore, run_sync

logger = logging.getLogger(__name__)

REF_N = 3


def _niche_query_terms(niche: str) -> str:
    return niche.strip().lstrip("#") or "tiktok"


async def _niche_aweme_pool(niche: str, *, period: int) -> list[dict[str, Any]]:
    term = _niche_query_terms(niche)
    kw_aw, _ = await ensemble.fetch_keyword_search(term, period=period)
    ht_aw, _ = await ensemble.fetch_hashtag_posts(term, cursor=0)
    ht_f = filter_recency(ht_aw, period)
    return merge_aweme_lists(kw_aw, ht_f)


def _append_completed(session: dict[str, Any], intent: QueryIntent) -> None:
    # Session tracking is handled by Supabase chat_sessions in GetViews — no-op here.
    completed = session.setdefault("completed_intents", [])
    if intent.value not in completed:
        completed.append(intent.value)


def _bump_analyses_summary(
    session: dict[str, Any],
    *,
    niche: str | None,
    delta_videos: int,
    intent_label: str,
    patterns: list[str] | None = None,
) -> None:
    s = session.setdefault("analyses_summary", {})
    if niche:
        s["niche"] = niche
        session["niche"] = niche
    s["videos_analyzed"] = int(s.get("videos_analyzed") or 0) + delta_videos
    ir = list(s.get("intents_run") or [])
    if intent_label not in ir:
        ir.append(intent_label)
    s["intents_run"] = ir
    if patterns:
        prev = list(s.get("top_patterns") or [])
        s["top_patterns"] = (prev + patterns)[:8]


async def run_content_directions(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    sem = get_analysis_semaphore()
    pool = await _niche_aweme_pool(niche, period=30)
    fa: dict[str, Any] = session.setdefault("full_analyses", {})
    cached_ids = set(fa.keys())
    picks = select_reference_videos(
        pool, recency_days=30, n=REF_N, cached_ids=cached_ids, rank_by="er"
    )

    analyzed: list[dict[str, Any]] = []

    async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(
                aweme, include_diagnosis=False, full_analyses=fa
            )

    tasks = [_one(a) for a in picks]
    results = await asyncio.gather(*tasks)
    for r in results:
        if "analysis" in r:
            analyzed.append(r)

    payload = {
        "niche": niche,
        "reference_count": len(analyzed),
        "analyzed_videos": analyzed,
    }
    synthesis = await run_sync(
        synthesize_intent_markdown,
        "content_directions",
        payload,
        collapsed_questions=questions if len(questions) > 1 else None,
        niche_key=niche,
    )
    directions_struct = [
        {
            "label": f"direction_{i + 1}",
            "summary": a.get("analysis", {})
            .get("content_direction", {})
            .get("what_works", ""),
        }
        for i, a in enumerate(analyzed[:3])
    ]
    session["directions"] = directions_struct
    _append_completed(session, QueryIntent.CONTENT_DIRECTIONS)
    _bump_analyses_summary(
        session,
        niche=niche,
        delta_videos=len(analyzed),
        intent_label="content_directions",
        patterns=[
            str(a.get("analysis", {}).get("content_direction", {}).get("what_works", ""))[
                :120
            ]
            for a in analyzed
            if a.get("analysis")
        ],
    )
    return {
        "intent": "content_directions",
        "niche": niche,
        "synthesis": synthesis,
        "analyzed_videos": analyzed,
        "directions": directions_struct,
    }


async def run_trend_spike(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    sem = get_analysis_semaphore()
    pool = await _niche_aweme_pool(niche, period=7)
    fa = session.setdefault("full_analyses", {})
    cached_ids = set(fa.keys())
    picks = select_reference_videos(
        pool, recency_days=7, n=REF_N, cached_ids=cached_ids, rank_by="velocity"
    )

    async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(
                aweme, include_diagnosis=False, full_analyses=fa
            )

    results = await asyncio.gather(*[_one(a) for a in picks])
    analyzed = [r for r in results if "analysis" in r]

    payload = {"niche": niche, "window_days": 7, "analyzed_videos": analyzed}
    synthesis = await run_sync(
        synthesize_intent_markdown,
        "trend_spike",
        payload,
        collapsed_questions=questions if len(questions) > 1 else None,
        niche_key=niche,
    )
    session["directions"] = session.get("directions") or []
    _append_completed(session, QueryIntent.TREND_SPIKE)
    _bump_analyses_summary(
        session,
        niche=niche,
        delta_videos=len(analyzed),
        intent_label="trend_spike",
    )
    return {
        "intent": "trend_spike",
        "niche": niche,
        "synthesis": synthesis,
        "analyzed_videos": analyzed,
    }


async def run_competitor_profile(
    handle: str,
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    sem = get_analysis_semaphore()
    posts = await ensemble.fetch_user_posts(handle, depth=2)
    fa = session.setdefault("full_analyses", {})
    cached_ids = set(fa.keys())
    picks = select_reference_videos(
        posts, recency_days=30, n=REF_N, cached_ids=cached_ids, rank_by="er"
    )

    async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(
                aweme, include_diagnosis=False, full_analyses=fa
            )

    results = await asyncio.gather(*[_one(a) for a in picks])
    analyzed = [r for r in results if "analysis" in r]

    payload = {"handle": handle, "analyzed_videos": analyzed}
    synthesis = await run_sync(
        synthesize_intent_markdown,
        "competitor_profile",
        payload,
        collapsed_questions=questions if len(questions) > 1 else None,
    )
    session["competitor_profile"] = synthesis
    _append_completed(session, QueryIntent.COMPETITOR_PROFILE)
    _bump_analyses_summary(
        session,
        niche=session.get("niche"),
        delta_videos=len(analyzed),
        intent_label="competitor_profile",
    )
    return {
        "intent": "competitor_profile",
        "handle": handle,
        "synthesis": synthesis,
        "analyzed_videos": analyzed,
    }


async def run_series_audit(
    urls: list[str],
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    sem = get_analysis_semaphore()
    fa: dict[str, Any] = session.setdefault("full_analyses", {})

    async def _one(u: str) -> dict[str, Any]:
        async with sem:
            return await analyze_tiktok_url(
                u, include_diagnosis=False, full_analyses=fa
            )

    results = await asyncio.gather(*[_one(u) for u in urls])
    analyzed = [r for r in results if "analysis" in r]

    payload = {"user_urls": urls, "analyzed_videos": analyzed}
    synthesis = await run_sync(
        synthesize_intent_markdown,
        "series_audit",
        payload,
        collapsed_questions=questions if len(questions) > 1 else None,
    )
    session["series_audit"] = synthesis
    _append_completed(session, QueryIntent.SERIES_AUDIT)
    _bump_analyses_summary(
        session,
        niche=session.get("niche"),
        delta_videos=len(analyzed),
        intent_label="series_audit",
    )
    return {
        "intent": "series_audit",
        "synthesis": synthesis,
        "analyzed_videos": analyzed,
    }


async def run_brief_generation(
    topic: str,
    niche: str,
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    payload = {
        "topic": topic,
        "niche": niche,
        "session_diagnosis": session.get("diagnosis"),
        "session_directions": session.get("directions"),
        "session_competitor": session.get("competitor_profile"),
        "analyses_summary": session.get("analyses_summary", {}),
    }
    brief = await run_sync(
        synthesize_intent_markdown,
        "brief_generation",
        payload,
        collapsed_questions=questions if len(questions) > 1 else None,
        niche_key=niche,
    )
    _append_completed(session, QueryIntent.BRIEF_GENERATION)
    _bump_analyses_summary(
        session,
        niche=niche or session.get("niche"),
        delta_videos=0,
        intent_label="brief_generation",
    )
    return {"intent": "brief_generation", "topic": topic, "niche": niche, "brief": brief}


async def run_video_diagnosis(
    url: str,
    session: dict[str, Any],
    *,
    include_diagnosis: bool = True,
    niche_override: str | None = None,
    questions: list[str] | None = None,
) -> dict[str, Any]:
    sem = get_analysis_semaphore()
    fa = session.setdefault("full_analyses", {})

    user_aweme = await ensemble.fetch_post_info(url)
    meta = ensemble.parse_metadata(user_aweme)
    niche = niche_override or infer_niche_from_hashtags(
        meta.hashtags, meta.description
    )

    pool = await _niche_aweme_pool(niche, period=30)
    cached_ids = set(fa.keys())
    uid = str(user_aweme.get("aweme_id", "") or "")
    if uid:
        cached_ids.add(uid)
    picks = select_reference_videos(
        pool, recency_days=30, n=REF_N, cached_ids=cached_ids, rank_by="er"
    )

    async def _user() -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(
                user_aweme, include_diagnosis=False, full_analyses=fa
            )

    async def _ref(aweme: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(
                aweme, include_diagnosis=False, full_analyses=fa
            )

    user_task = asyncio.create_task(_user())
    ref_tasks = [asyncio.create_task(_ref(a)) for a in picks]
    user_res = await user_task
    ref_results = await asyncio.gather(*ref_tasks)
    references = [r for r in ref_results if "analysis" in r]

    diagnosis: str
    if include_diagnosis:
        payload = {
            "user_video": user_res,
            "reference_videos": references,
            "niche": niche,
        }
        diagnosis = await run_sync(
            synthesize_intent_markdown,
            "video_diagnosis",
            payload,
            collapsed_questions=questions if questions and len(questions) > 1 else None,
            niche_key=niche,
        )
    else:
        diagnosis = (
            "Diagnosis skipped (`include_diagnosis=false`). "
            "Structured analyses for user and references are available."
        )

    session["diagnosis"] = diagnosis
    _append_completed(session, QueryIntent.VIDEO_DIAGNOSIS)
    session["niche"] = niche
    _bump_analyses_summary(
        session,
        niche=niche,
        delta_videos=1 + len(references),
        intent_label="video_diagnosis",
    )

    # Flatten user result for backward compatibility with VideoAnalyzeResult consumers
    out: dict[str, Any] = {
        "intent": "video_diagnosis",
        "niche": niche,
        "user_video": user_res,
        "reference_videos": references,
        "diagnosis": diagnosis,
    }
    if "metadata" in user_res:
        out["metadata"] = user_res["metadata"]
    if "analysis" in user_res:
        out["analysis"] = user_res["analysis"]
    if "content_type" in user_res:
        out["content_type"] = user_res["content_type"]
    return out


async def run_kol_search(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    """KOL / creator discovery — reference posts + synthesis (free intent on product)."""
    sem = get_analysis_semaphore()
    pool = await _niche_aweme_pool(niche, period=30)
    fa: dict[str, Any] = session.setdefault("full_analyses", {})
    cached_ids = set(fa.keys())
    picks = select_reference_videos(
        pool, recency_days=30, n=REF_N, cached_ids=cached_ids, rank_by="er"
    )

    async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(
                aweme, include_diagnosis=False, full_analyses=fa
            )

    results = await asyncio.gather(*[_one(a) for a in picks])
    analyzed = [r for r in results if "analysis" in r]

    payload = {
        "niche": niche,
        "reference_count": len(analyzed),
        "analyzed_videos": analyzed,
    }
    synthesis = await run_sync(
        synthesize_intent_markdown,
        "find_creators",
        payload,
        collapsed_questions=questions if len(questions) > 1 else None,
    )
    session["kol_search"] = synthesis
    completed = session.setdefault("completed_intents", [])
    if "find_creators" not in completed:
        completed.append("find_creators")
    _bump_analyses_summary(
        session,
        niche=niche,
        delta_videos=len(analyzed),
        intent_label="find_creators",
    )
    return {
        "intent": "find_creators",
        "niche": niche,
        "synthesis": synthesis,
        "analyzed_videos": analyzed,
    }


async def run_own_channel(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    """Soi kênh — same reference pull as content directions, own-channel framing."""
    sem = get_analysis_semaphore()
    pool = await _niche_aweme_pool(niche, period=30)
    fa: dict[str, Any] = session.setdefault("full_analyses", {})
    cached_ids = set(fa.keys())
    picks = select_reference_videos(
        pool, recency_days=30, n=REF_N, cached_ids=cached_ids, rank_by="er"
    )

    analyzed: list[dict[str, Any]] = []

    async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(
                aweme, include_diagnosis=False, full_analyses=fa
            )

    tasks = [_one(a) for a in picks]
    results = await asyncio.gather(*tasks)
    for r in results:
        if "analysis" in r:
            analyzed.append(r)

    payload = {
        "niche": niche,
        "reference_count": len(analyzed),
        "analyzed_videos": analyzed,
    }
    synthesis = await run_sync(
        synthesize_intent_markdown,
        "own_channel",
        payload,
        collapsed_questions=questions if len(questions) > 1 else None,
    )
    session["own_channel_audit"] = synthesis
    completed = session.setdefault("completed_intents", [])
    if "own_channel" not in completed:
        completed.append("own_channel")
    _bump_analyses_summary(
        session,
        niche=niche,
        delta_videos=len(analyzed),
        intent_label="own_channel",
        patterns=[
            str(a.get("analysis", {}).get("content_direction", {}).get("what_works", ""))[
                :120
            ]
            for a in analyzed
            if a.get("analysis")
        ],
    )
    return {
        "intent": "own_channel",
        "niche": niche,
        "synthesis": synthesis,
        "analyzed_videos": analyzed,
    }
