"""Intent pipelines: Ensemble search + parallel Gemini analysis + synthesis."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import analyze_aweme, analyze_tiktok_url
from getviews_pipeline.corpus_context import (
    build_corpus_citation_block,
    get_corpus_count_cached,
    get_signal_grades_for_niche,
    get_top_breakout_videos,
)
from getviews_pipeline.gemini import synthesize_intent_markdown
from getviews_pipeline.helpers import (
    filter_recency,
    infer_niche_from_hashtags,
    merge_aweme_lists,
    select_reference_videos,
)
from getviews_pipeline.intents import QueryIntent
from getviews_pipeline.runtime import get_analysis_semaphore, run_sync
from getviews_pipeline.step_events import (
    emit,
    emit_sentinel,
    step_count,
    step_creator,
    step_done,
    step_process,
    step_search,
    step_start,
)

logger = logging.getLogger(__name__)

REF_N = 3


async def _empty_dict() -> dict:
    """No-op coroutine returning an empty dict — used as a gather placeholder."""
    return {}


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
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    try:
        sem = get_analysis_semaphore()
        emit(step_queue, step_start(f"Đang tìm hướng nội dung cho '{niche}'..."))
        emit(step_queue, step_search("ensemble", niche))
        pool = await _niche_aweme_pool(niche, period=30)
        emit(step_queue, step_count(len(pool)))
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

        emit(step_queue, step_process("Đang phân tích video tham chiếu..."))
        tasks = [_one(a) for a in picks]
        results = await asyncio.gather(*tasks)
        for r in results:
            if "analysis" in r:
                analyzed.append(r)

        count, niche_name = await get_corpus_count_cached(
            session, niche_id=None, days=30, niche_name=niche
        )
        citation = build_corpus_citation_block(count, niche_name, days=30)
        emit(step_queue, step_done("Đã phân tích xong — đang tổng hợp hướng nội dung..."))

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
            corpus_citation=citation,
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
    finally:
        await emit_sentinel(step_queue)


async def run_trend_spike(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    try:
        sem = get_analysis_semaphore()
        emit(step_queue, step_start(f"Đang tìm xu hướng '{niche}'..."))
        emit(step_queue, step_search("ensemble", niche))
        pool = await _niche_aweme_pool(niche, period=7)
        emit(step_queue, step_count(len(pool)))
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

        emit(step_queue, step_process("Đang phân tích video bứt phá..."))
        results = await asyncio.gather(*[_one(a) for a in picks])
        analyzed = [r for r in results if "analysis" in r]

        count, niche_name = await get_corpus_count_cached(
            session, niche_id=None, days=7, niche_name=niche
        )
        citation = build_corpus_citation_block(count, niche_name, days=7)

        # Enrich with real breakout + signal data (P1-7 + P1-8)
        # niche_id lookup: use session if available, else omit (signal grades require integer id)
        niche_id: int | None = session.get("niche_id")
        emit(step_queue, step_search("corpus", f"breakout videos {niche}"))

        breakout_task = get_top_breakout_videos(niche_id, days=7, limit=10)
        signal_task = (
            get_signal_grades_for_niche(niche_id)
            if niche_id is not None
            else _empty_dict()
        )

        breakout_videos, signal_grades = await asyncio.gather(
            breakout_task,
            signal_task,
            return_exceptions=True,
        )
        if isinstance(breakout_videos, Exception):
            breakout_videos = []
        if isinstance(signal_grades, Exception):
            signal_grades = {}

        emit(step_queue, step_done("Đã tổng hợp dữ liệu — đang viết phân tích..."))
        payload = {
            "niche": niche,
            "window_days": 7,
            "analyzed_videos": analyzed,
            "breakout_videos": breakout_videos,
            "signal_grades": signal_grades,
        }
        synthesis = await run_sync(
            synthesize_intent_markdown,
            "trend_spike",
            payload,
            collapsed_questions=questions if len(questions) > 1 else None,
            niche_key=niche,
            corpus_citation=citation,
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
    finally:
        await emit_sentinel(step_queue)


async def run_competitor_profile(
    handle: str,
    session: dict[str, Any],
    questions: list[str],
    *,
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    sem = get_analysis_semaphore()

    emit(step_queue, step_start(f"Đang tải trang TikTok @{handle}..."))
    emit(step_queue, step_creator(handle))

    posts = await ensemble.fetch_user_posts(handle, depth=2)
    fa = session.setdefault("full_analyses", {})
    cached_ids = set(fa.keys())
    picks = select_reference_videos(
        posts, recency_days=30, n=REF_N, cached_ids=cached_ids, rank_by="er"
    )
    emit(step_queue, step_count(len(posts)))

    emit(step_queue, step_process("Đang phân tích video tốt nhất..."))

    async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(
                aweme, include_diagnosis=False, full_analyses=fa
            )

    results = await asyncio.gather(*[_one(a) for a in picks])
    analyzed = [r for r in results if "analysis" in r]

    emit(step_queue, step_done(f"Đã phân tích {len(analyzed)} video — đang viết báo cáo..."))

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
    await emit_sentinel(step_queue)
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
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    try:
        emit(step_queue, step_start("Đang chuẩn bị brief quay phim..."))
        emit(step_queue, step_search("corpus", niche or topic))
        count, niche_name = await get_corpus_count_cached(
            session, niche_id=None, days=30, niche_name=niche
        )
        citation = build_corpus_citation_block(count, niche_name, days=30)
        emit(step_queue, step_process("Đang tạo brief dựa trên dữ liệu corpus..."))

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
            corpus_citation=citation,
        )
        emit(step_queue, step_done("Brief xong — đang hiển thị..."))
        _append_completed(session, QueryIntent.BRIEF_GENERATION)
        _bump_analyses_summary(
            session,
            niche=niche or session.get("niche"),
            delta_videos=0,
            intent_label="brief_generation",
        )
        return {"intent": "brief_generation", "topic": topic, "niche": niche, "brief": brief}
    finally:
        await emit_sentinel(step_queue)


async def run_video_diagnosis(
    url: str,
    session: dict[str, Any],
    *,
    include_diagnosis: bool = True,
    niche_override: str | None = None,
    questions: list[str] | None = None,
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    sem = get_analysis_semaphore()
    fa = session.setdefault("full_analyses", {})

    emit(step_queue, step_start("Đang tải và đọc video..."))
    user_aweme = await ensemble.fetch_post_info(url)
    meta = ensemble.parse_metadata(user_aweme)
    handle = meta.author.username if meta.author else ""
    if handle:
        emit(step_queue, step_creator(handle))

    niche = niche_override or infer_niche_from_hashtags(
        meta.hashtags, meta.description
    )

    emit(step_queue, step_search("corpus", f"video tương tự trong niche {niche}"))
    pool = await _niche_aweme_pool(niche, period=30)
    cached_ids = set(fa.keys())
    uid = str(user_aweme.get("aweme_id", "") or "")
    if uid:
        cached_ids.add(uid)
    picks = select_reference_videos(
        pool, recency_days=30, n=REF_N, cached_ids=cached_ids, rank_by="er"
    )
    emit(step_queue, step_count(len(pool)))

    emit(step_queue, step_process("Đang phân tích từng video..."))

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

    count, niche_name = await get_corpus_count_cached(
        session, niche_id=None, days=30, niche_name=niche
    )
    citation = build_corpus_citation_block(count, niche_name, days=30)

    emit(step_queue, step_done(f"Đã phân tích {1 + len(references)} video — đang viết báo cáo..."))

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
            corpus_citation=citation,
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
    await emit_sentinel(step_queue)

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
