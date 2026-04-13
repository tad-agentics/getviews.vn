"""Intent pipelines: Ensemble search + parallel Gemini analysis + synthesis."""

from __future__ import annotations

import asyncio
import json as _json
import logging
import re
from datetime import date, timedelta
from typing import Any

from getviews_pipeline.supabase_client import get_service_client

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import analyze_aweme, analyze_tiktok_url
from getviews_pipeline.corpus_context import (
    build_corpus_citation_block,
    fetch_corpus_reference_pool,
    get_corpus_count_cached,
    get_niche_intelligence,
    get_signal_grades_for_niche,
    get_top_breakout_videos,
    resolve_niche_id_cached,
)
from getviews_pipeline.corpus_ingest import classify_format
from getviews_pipeline.output_redesign import hook_type_vi
from getviews_pipeline.gemini import (
    synthesize_diagnosis,
    synthesize_diagnosis_carousel_v2,
    synthesize_diagnosis_v2,
    synthesize_intent_markdown,
)
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

# audio_transcript character limit before synthesis — full transcripts can be
# 500+ tokens each; 3 refs × 500 tokens = 1500 extra tokens for low-value text.
_TRANSCRIPT_CHAR_LIMIT = 500


def _truncate_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of an analysis dict with audio_transcript truncated."""
    transcript = analysis.get("audio_transcript")
    if not transcript or len(transcript) <= _TRANSCRIPT_CHAR_LIMIT:
        return analysis
    return {**analysis, "audio_transcript": transcript[:_TRANSCRIPT_CHAR_LIMIT] + "…"}


def _truncate_transcripts(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return reference video list with audio_transcript truncated in each analysis."""
    result = []
    for ref in refs:
        analysis = ref.get("analysis")
        if analysis and analysis.get("audio_transcript"):
            ref = {**ref, "analysis": _truncate_analysis(analysis)}
        result.append(ref)
    return result


async def _empty_dict() -> dict:
    """No-op coroutine returning an empty dict — used as a gather placeholder."""
    return {}


def _niche_query_terms(niche: str) -> str:
    return niche.strip().lstrip("#") or "tiktok"


async def _niche_aweme_pool(niche: str, *, period: int) -> list[dict[str, Any]]:
    """Fetch keyword + hashtag pool for a niche. Fails open on EnsembleData quota errors
    so the pipeline can still return a carousel/video diagnosis without reference videos."""
    term = _niche_query_terms(niche)
    kw_aw: list[dict[str, Any]] = []
    ht_aw: list[dict[str, Any]] = []
    try:
        kw_aw, _ = await ensemble.fetch_keyword_search(term, period=period)
    except ValueError as exc:
        if "unit limit" in str(exc).lower() or "quota" in str(exc).lower():
            logger.warning("[niche_pool] EnsembleData quota exhausted — skipping keyword search for niche=%s", niche)
        else:
            raise
    try:
        ht_aw, _ = await ensemble.fetch_hashtag_posts(term, cursor=0)
    except ValueError as exc:
        if "unit limit" in str(exc).lower() or "quota" in str(exc).lower():
            logger.warning("[niche_pool] EnsembleData quota exhausted — skipping hashtag search for niche=%s", niche)
        else:
            raise
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
        emit(step_queue, step_search("corpus", niche))
        fa: dict[str, Any] = session.setdefault("full_analyses", {})
        cached_ids = set(fa.keys())

        corpus_pool = await fetch_corpus_reference_pool(niche, days=30, limit=20)
        if len(corpus_pool) >= REF_N:
            corpus_pool.sort(key=lambda v: float(v.get("_corpus_er") or 0.0), reverse=True)
            picks = [v for v in corpus_pool if v.get("aweme_id") not in cached_ids][:REF_N]
            pool = corpus_pool
        else:
            logger.info(
                "[content_directions] corpus pool too small (%d) for niche '%s', using live search",
                len(corpus_pool), niche,
            )
            emit(step_queue, step_search("ensemble", niche))
            pool = await _niche_aweme_pool(niche, period=30)
            picks = select_reference_videos(
                pool, recency_days=30, n=REF_N, cached_ids=cached_ids, rank_by="er"
            )
        emit(step_queue, step_count(len(pool)))

        analyzed: list[dict[str, Any]] = []

        async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
            if aweme.get("_from_corpus") and aweme.get("_corpus_analysis"):
                stats = aweme.get("statistics") or {}
                handle = (aweme.get("author") or {}).get("unique_id") or ""
                return {
                    "aweme_id": aweme["aweme_id"],
                    "analysis": aweme["_corpus_analysis"],
                    "metadata": {
                        "video_id": aweme["aweme_id"],
                        "author": {"username": handle},
                        "views": int(stats.get("play_count") or 0),
                        "tiktok_url": aweme.get("_corpus_tiktok_url", ""),
                        "thumbnail_url": aweme.get("thumbnail_url"),
                        "days_ago": aweme.get("_corpus_days_ago", 0),
                        "breakout": aweme.get("_corpus_breakout", 0.0),
                    },
                }
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

        niche_id = await resolve_niche_id_cached(session, niche)
        count, niche_name = await get_corpus_count_cached(
            session, niche_id=niche_id, days=30, niche_name=niche
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
        emit(step_queue, step_search("corpus", niche))
        fa = session.setdefault("full_analyses", {})
        cached_ids = set(fa.keys())

        # Prefer corpus (7-day window) for niche-accurate trend videos.
        corpus_pool = await fetch_corpus_reference_pool(niche, days=7, limit=20)
        if len(corpus_pool) >= REF_N:
            # Sort by breakout_multiplier for trend spike — highest breakout wins
            corpus_pool.sort(key=lambda v: float(v.get("_corpus_breakout") or 0.0), reverse=True)
            picks = [v for v in corpus_pool if v.get("aweme_id") not in cached_ids][:REF_N]
            pool = corpus_pool
        else:
            logger.info(
                "[trend_spike] corpus pool too small (%d) for niche '%s' (7d), using live search",
                len(corpus_pool), niche,
            )
            emit(step_queue, step_search("ensemble", niche))
            pool = await _niche_aweme_pool(niche, period=7)
            picks = select_reference_videos(
                pool, recency_days=7, n=REF_N, cached_ids=cached_ids, rank_by="velocity"
            )
        emit(step_queue, step_count(len(pool)))

        async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
            if aweme.get("_from_corpus") and aweme.get("_corpus_analysis"):
                stats = aweme.get("statistics") or {}
                handle = (aweme.get("author") or {}).get("unique_id") or ""
                return {
                    "aweme_id": aweme["aweme_id"],
                    "analysis": aweme["_corpus_analysis"],
                    "metadata": {
                        "video_id": aweme["aweme_id"],
                        "author": {"username": handle},
                        "views": int(stats.get("play_count") or 0),
                        "tiktok_url": aweme.get("_corpus_tiktok_url", ""),
                        "thumbnail_url": aweme.get("thumbnail_url"),
                        "days_ago": aweme.get("_corpus_days_ago", 0),
                        "breakout": aweme.get("_corpus_breakout", 0.0),
                    },
                }
            async with sem:
                return await analyze_aweme(
                    aweme, include_diagnosis=False, full_analyses=fa
                )

        emit(step_queue, step_process("Đang phân tích video bứt phá..."))
        results = await asyncio.gather(*[_one(a) for a in picks])
        analyzed = [r for r in results if "analysis" in r]

        # Resolve niche_id once — used for count, breakout, and signal grades
        niche_id: int | None = await resolve_niche_id_cached(session, niche)
        count, niche_name = await get_corpus_count_cached(
            session, niche_id=niche_id, days=7, niche_name=niche
        )
        citation = build_corpus_citation_block(count, niche_name, days=7)

        # Enrich with real breakout + signal data (P1-7 + P1-8)
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

        trending_sounds: list[dict[str, Any]] = []
        if niche_id is not None:
            try:
                sb = get_service_client()
                _week_of = date.today() - timedelta(days=date.today().weekday())
                _sounds_res = (
                    sb.table("trending_sounds")
                    .select("sound_name,usage_count,total_views,commerce_signal")
                    .eq("niche_id", niche_id)
                    .eq("week_of", _week_of.isoformat())
                    .order("usage_count", desc=True)
                    .limit(5)
                    .execute()
                )
                trending_sounds = _sounds_res.data or []
            except Exception as exc:
                logger.warning("trending_sounds fetch failed: %s", exc)

        emit(step_queue, step_done("Đã tổng hợp dữ liệu — đang viết phân tích..."))
        payload = {
            "niche": niche,
            "window_days": 7,
            "analyzed_videos": analyzed,
            "breakout_videos": breakout_videos,
            "signal_grades": signal_grades,
            "trending_sounds": trending_sounds,
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
        niche_id = await resolve_niche_id_cached(session, niche)
        count, niche_name = await get_corpus_count_cached(
            session, niche_id=niche_id, days=30, niche_name=niche
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


async def run_shot_list(
    topic: str,
    niche: str,
    session: dict[str, Any],
    questions: list[str],
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    """Generate a structured shot-by-shot production list for a video topic."""
    try:
        emit(step_queue, step_start("Đang tạo danh sách cảnh quay..."))
        emit(step_queue, step_search("corpus", niche or topic))
        niche_id = await resolve_niche_id_cached(session, niche)
        count, niche_name = await get_corpus_count_cached(
            session, niche_id=niche_id, days=30, niche_name=niche
        )
        citation = build_corpus_citation_block(count, niche_name, days=30)
        emit(step_queue, step_process("Đang xây dựng shot list dựa trên corpus..."))

        payload = {
            "topic": topic,
            "niche": niche,
            "format": session.get("video_format", "standard"),
            "session_directions": session.get("directions"),
            "session_diagnosis": session.get("diagnosis"),
            "analyses_summary": session.get("analyses_summary", {}),
        }
        shot_list = await run_sync(
            synthesize_intent_markdown,
            "shot_list",
            payload,
            collapsed_questions=questions if len(questions) > 1 else None,
            niche_key=niche,
            corpus_citation=citation,
        )
        emit(step_queue, step_done("Shot list xong — đang hiển thị..."))
        _append_completed(session, QueryIntent.BRIEF_GENERATION)
        _bump_analyses_summary(
            session,
            niche=niche or session.get("niche"),
            delta_videos=0,
            intent_label="shot_list",
        )
        return {
            "intent": "shot_list",
            "topic": topic,
            "niche": niche,
            "shot_list": shot_list,
        }
    finally:
        await emit_sentinel(step_queue)


_DIRECTION_KEYWORDS = (
    "gợi ý", "định dạng", "ý tưởng", "hướng content",
    "kịch bản", "cho tôi", "cho mình", "ý kiến",
)


def _wants_directions(user_message: str) -> bool:
    """Return True if the user message requests content direction suggestions."""
    lower = user_message.lower()
    return any(kw in lower for kw in _DIRECTION_KEYWORDS)


async def run_video_diagnosis(
    url: str,
    session: dict[str, Any],
    *,
    include_diagnosis: bool = True,
    niche_override: str | None = None,
    questions: list[str] | None = None,
    user_message: str = "",
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
    uid = str(user_aweme.get("aweme_id", "") or "")
    cached_ids = set(fa.keys())
    if uid:
        cached_ids.add(uid)

    # Prefer curated corpus (niche-tagged, ≥20k views) over live search to
    # ensure reference videos are actually in the same niche as the user's video.
    corpus_pool = await fetch_corpus_reference_pool(
        niche, days=30, limit=20, exclude_video_id=uid or None
    )
    if len(corpus_pool) >= REF_N:
        # Corpus has enough — sort by pre-computed engagement_rate (most accurate)
        corpus_pool.sort(key=lambda v: float(v.get("_corpus_er") or 0.0), reverse=True)
        picks = [v for v in corpus_pool if v.get("aweme_id") not in cached_ids][:REF_N]
        pool = corpus_pool
        logger.info(
            "[ref_source] niche=%s corpus_hit=true corpus_size=%d",
            niche,
            len(corpus_pool),
        )
    else:
        # Corpus too sparse for this niche — fall back to live EnsembleData search.
        # Each fallback costs EnsembleData API units (keyword + hashtag search).
        # Monitor corpus_hit=false frequency per niche in Cloud Run logs to identify
        # niches where the corpus needs broader coverage.
        logger.warning(
            "[ref_source] niche=%s corpus_hit=false corpus_size=%d threshold=%d — "
            "falling back to live EnsembleData search (costs API units)",
            niche,
            len(corpus_pool),
            REF_N,
        )
        pool = await _niche_aweme_pool(niche, period=30)
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
        # Corpus-sourced picks already have analysis_json — skip re-analysis.
        if aweme.get("_from_corpus") and aweme.get("_corpus_analysis"):
            stats = aweme.get("statistics") or {}
            views = int(stats.get("play_count") or 0)
            handle = (aweme.get("author") or {}).get("unique_id") or ""
            corpus_analysis = aweme["_corpus_analysis"]
            raw_hook_type = (corpus_analysis.get("hook_analysis") or {}).get("hook_type") or ""
            return {
                "aweme_id": aweme["aweme_id"],
                "analysis": corpus_analysis,
                "metadata": {
                    "video_id": aweme["aweme_id"],
                    "author": {"username": handle},
                    "views": views,
                    "tiktok_url": aweme.get("_corpus_tiktok_url", ""),
                    "thumbnail_url": aweme.get("thumbnail_url"),
                    "days_ago": aweme.get("_corpus_days_ago", 0),
                    "breakout": aweme.get("_corpus_breakout", 0.0),
                    "hook_type": raw_hook_type,
                    "hook_type_vi": hook_type_vi(raw_hook_type),
                    # content_type from video_corpus table — not present in analysis_json.
                    # Required for carousel reference filtering in run_video_diagnosis().
                    "content_type": aweme.get("_corpus_content_type", "video"),
                },
            }
        async with sem:
            return await analyze_aweme(
                aweme, include_diagnosis=False, full_analyses=fa
            )

    user_task = asyncio.create_task(_user())
    ref_tasks = [asyncio.create_task(_ref(a)) for a in picks]
    user_res = await user_task
    ref_results = await asyncio.gather(*ref_tasks)
    references = [r for r in ref_results if "analysis" in r]

    niche_id = await resolve_niche_id_cached(session, niche)
    count, niche_name = await get_corpus_count_cached(
        session, niche_id=niche_id, days=30, niche_name=niche
    )
    citation = build_corpus_citation_block(count, niche_name, days=30)

    # Fetch niche norms from materialized view — fail-open, never raises
    niche_norms = await get_niche_intelligence(niche)
    # Inject an explicit no-data marker when niche_norms is empty so Gemini
    # cannot hallucinate niche benchmarks. The soft prompt instruction alone
    # ("bỏ qua so sánh") is insufficient — an explicit _note in the JSON is
    # harder for the model to ignore than prose guidance.
    if not niche_norms:
        niche_norms = {"_note": "Không có data niche — KHÔNG tạo số liệu niche, KHÔNG so sánh với chuẩn niche"}

    emit(step_queue, step_done(f"Đã phân tích {1 + len(references)} video — đang viết báo cáo..."))

    # Detect content format from user analysis — reuse corpus_ingest classifier.
    user_analysis_dict = user_res.get("analysis") or {}
    user_metadata_dict = user_res.get("metadata") or {}
    niche_id_for_format = 0  # format classifier uses niche_id for mukbang heuristic;
                              # 0 = unknown is safe (falls back to keyword matching only)
    content_format = classify_format(user_analysis_dict, niche_id_for_format)

    # Build user_stats from metadata for the synthesis prompt.
    user_stats: dict[str, Any] = {
        "views": user_metadata_dict.get("views") or 0,
        "likes": user_metadata_dict.get("likes") or 0,
        "comments": user_metadata_dict.get("comments") or 0,
        "shares": user_metadata_dict.get("shares") or 0,
        "breakout_multiplier": user_metadata_dict.get("breakout") or 0.0,
        "duration": user_metadata_dict.get("duration") or 0,
    }

    # Detect content type from user analysis result for routing
    user_content_type = user_res.get("content_type") or (
        "carousel" if user_res.get("metadata", {}).get("content_type") == "carousel" else "video"
    )
    include_carousel_directions = _wants_directions(user_message)

    # Detect carousel sub-format for FORMAT_ANALYSIS_WEIGHTS routing.
    # Inferred from content_arc when available (set by Gemini carousel extraction).
    def _carousel_subformat(analysis: dict[str, Any]) -> str:
        arc = (analysis.get("content_arc") or "").lower()
        if arc in ("list", "gallery"):
            return "carousel_product_roundup"
        if arc in ("tutorial_steps",):
            return "carousel_tutorial"
        if arc in ("story", "narrative"):
            return "carousel_story"
        return "carousel"

    diagnosis: str
    if include_diagnosis:
        if user_content_type == "carousel":
            carousel_format = _carousel_subformat(user_analysis_dict)
            # Filter references to carousel-only when the corpus has enough;
            # fall back to all references if fewer than REF_N carousels found.
            # Filter on metadata.content_type only — not analysis.content_type.
            # For corpus-sourced references, analysis contains the raw Gemini
            # extraction sub-dict (hook_analysis, content_arc, scenes…) which
            # never has content_type at its root. content_type comes from the
            # video_corpus table column and is surfaced via metadata.content_type
            # (set by _ref() above from _corpus_content_type).
            # For live-analyzed references, analyze_aweme() also places
            # content_type in the metadata dict, not in the analysis sub-dict.
            carousel_refs = [
                r for r in references
                if (r.get("metadata") or {}).get("content_type") == "carousel"
            ]
            if len(carousel_refs) < REF_N:
                # Not enough carousel references — use all references (mixed is better than empty)
                carousel_refs = references
            logger.info(
                "[carousel] routing to synthesize_diagnosis_carousel_v2 "
                "format=%s carousel_refs=%d wants_directions=%s",
                carousel_format,
                len(carousel_refs),
                include_carousel_directions,
            )
            diagnosis = await run_sync(
                synthesize_diagnosis_carousel_v2,
                carousel_format=carousel_format,
                niche_name=niche,
                corpus_size=count,
                niche_norms=niche_norms,
                reference_carousels=_truncate_transcripts(carousel_refs),
                user_analysis=_truncate_analysis(user_analysis_dict),
                user_stats=user_stats,
                wants_directions=include_carousel_directions,
                collapsed_questions=questions if questions and len(questions) > 1 else None,
            )
        else:
            diagnosis = await run_sync(
                synthesize_diagnosis_v2,
                content_format=content_format,
                niche_name=niche,
                corpus_size=count,
                niche_norms=niche_norms,
                reference_videos=_truncate_transcripts(references),
                user_analysis=_truncate_analysis(user_analysis_dict),
                user_stats=user_stats,
                collapsed_questions=questions if questions and len(questions) > 1 else None,
            )
        # Server-side guarantee: ensure all reference videos appear as video_ref
        # blocks regardless of whether Gemini emitted them. Appended only for refs
        # whose video_id is not already present in the synthesis text.
        already_emitted = set(re.findall(r'"video_id"\s*:\s*"([^"]+)"', diagnosis))

        injected_blocks: list[str] = []
        for ref in references:
            meta = ref.get("metadata") or {}
            vid = str(meta.get("video_id") or ref.get("aweme_id") or "")
            if not vid or vid in already_emitted:
                continue
            handle = ""
            author = meta.get("author") or {}
            handle = str(author.get("username") or "")
            views = int(meta.get("views") or 0)
            days_ago = int(meta.get("days_ago") or 0)
            breakout = float(meta.get("breakout") or 0.0)
            block: dict = {
                "type": "video_ref",
                "video_id": vid,
                "handle": f"@{handle}" if handle and not handle.startswith("@") else handle,
                "views": views,
                "days_ago": days_ago,
            }
            if breakout > 1.0:
                block["breakout"] = round(breakout, 1)
            injected_blocks.append(_json.dumps(block, ensure_ascii=False))
            already_emitted.add(vid)

        if injected_blocks:
            diagnosis = diagnosis.rstrip() + "\n\n" + "\n".join(injected_blocks)
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
