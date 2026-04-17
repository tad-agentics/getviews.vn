"""Intent pipelines: Ensemble search + parallel Gemini analysis + synthesis."""

from __future__ import annotations

import asyncio
import json as _json
import logging
import re
import time
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
from getviews_pipeline.hashtag_niche_map import classify_from_hashtags
from getviews_pipeline.output_redesign import hook_type_vi
from getviews_pipeline.gemini import (
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


# Niche taxonomy labels the pipeline knows about — used to ground Gemini's
# product→niche mapping so it doesn't hallucinate an unlisted niche.
_NICHE_TAXONOMY_LABELS: list[str] = [
    "review đồ gia dụng",
    "làm đẹp",
    "skincare",
    "thời trang",
    "ẩm thực",
    "du lịch",
    "công nghệ",
    "tài chính",
    "giáo dục",
    "giải trí",
    "thể thao",
    "sức khỏe",
    "mẹ và bé",
    "thú cưng",
    "hài",
    "Shopee affiliate",
    "lifestyle",
]


def _extract_kol_target_niche(questions: list[str], session_niche: str | None) -> str:
    """Extract the target product/niche from a KOL-search question using Gemini.

    When the user asks "tìm KOC cho thương hiệu đồng hồ", the session niche
    may be unset or set to a previous unrelated niche. infer_niche_from_hashtags
    just slices raw query text — it is not a classifier. This function uses a
    cheap Gemini call to map the product description to the closest niche label
    from _NICHE_TAXONOMY_LABELS, giving run_kol_search a meaningful search term.

    Falls back to session_niche if extraction fails.
    """
    from getviews_pipeline.gemini import _generate_content_models, _response_text, GEMINI_KNOWLEDGE_MODEL, GEMINI_KNOWLEDGE_FALLBACKS
    from google.genai import types as _types  # type: ignore

    combined = " | ".join(questions)
    labels_str = ", ".join(_NICHE_TAXONOMY_LABELS)
    prompt = (
        f"Câu hỏi của người dùng: \"{combined}\"\n\n"
        f"Danh sách niche: {labels_str}\n\n"
        "Người dùng muốn tìm KOC/KOL để quay UGC cho sản phẩm/thương hiệu nào? "
        "Chọn niche GẦN NHẤT từ danh sách trên. "
        "Nếu không có niche phù hợp, trả về niche gần nhất với sản phẩm đó. "
        "Chỉ trả về TÊN NICHE, không giải thích. Ví dụ: 'thời trang' hoặc 'review đồ gia dụng'."
    )
    try:
        cfg = _types.GenerateContentConfig(temperature=0.0, max_output_tokens=32)
        response = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        extracted = _response_text(response).strip().strip('"').strip("'")
        if extracted:
            logger.info("[kol_search] extracted target niche from question: %r → %r", combined[:80], extracted)
            return extracted
    except Exception as exc:
        logger.warning("[kol_search] niche extraction failed: %s — falling back to session niche", exc)
    return session_niche or "tiktok vietnam"


_NICHE_SEARCH_STOPWORDS: frozenset[str] = frozenset({
    "trendingtiktok", "trending", "viral", "tiktok", "foryou", "fyp",
    "xuhuong", "thinhhanh", "hot", "xinh", "dep",
})


def _niche_query_terms(niche: str) -> str:
    """Return a clean search term for EnsembleData keyword/hashtag search.

    Strips leading # and rejects pure noise strings (generic hashtags that
    carry no niche signal) — falls back to "tiktok vietnam" so live search
    at least returns Vietnamese content rather than garbage.
    """
    term = niche.strip().lstrip("#")
    if not term or term.lower() in _NICHE_SEARCH_STOPWORDS:
        return "tiktok vietnam"
    return term


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


def _inject_video_ref_blocks(synthesis: str, analyzed: list[dict[str, Any]]) -> str:
    """Append video_ref JSON blocks for any analyzed video not already in synthesis.

    Works for pipelines that use the metadata-wrapper structure:
      {"aweme_id": id, "metadata": {"video_id": ..., "author": {"username": ...}, ...}}
    """
    already_emitted = set(re.findall(r'"video_id"\s*:\s*"([^"]+)"', synthesis))
    now_ts = time.time()
    injected: list[str] = []
    for ref in analyzed:
        meta = ref.get("metadata") or {}
        vid = str(meta.get("video_id") or ref.get("aweme_id") or "")
        if not vid or vid in already_emitted:
            continue
        author = meta.get("author") or {}
        handle = str(author.get("username") or "")
        views = int(meta.get("views") or 0)
        create_time = int(ref.get("create_time") or 0)
        days_ago = int(meta.get("days_ago") or (
            int((now_ts - create_time) / 86400) if create_time > 0 else 0
        ))
        breakout = float(meta.get("breakout") or 0.0)
        thumb = str(meta.get("thumbnail_url") or "")
        block: dict = {
            "type": "video_ref",
            "video_id": vid,
            "handle": f"@{handle}" if handle and not handle.startswith("@") else handle,
            "views": views,
            "days_ago": days_ago,
        }
        if breakout > 1.0:
            block["breakout"] = round(breakout, 1)
        if thumb:
            block["thumbnail_url"] = thumb
        injected.append(_json.dumps(block, ensure_ascii=False))
        already_emitted.add(vid)
    if injected:
        synthesis = synthesis.rstrip() + "\n\n" + "\n".join(injected)
    return synthesis


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
        synthesis = _inject_video_ref_blocks(synthesis, analyzed)
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
        synthesis = _inject_video_ref_blocks(synthesis, analyzed)
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
        _append_completed(session, QueryIntent.SHOT_LIST)
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


async def _get_niche_insight(niche_name: str, session: dict[str, Any]) -> str:
    """Fetch current week's Layer 0 mechanism insight for this niche.

    Returns a formatted string ready for injection into the synthesis voice_block.
    Returns "" if no insight is available (Layer 0 hasn't run yet, or sparse niche).
    """
    try:
        niche_id = await resolve_niche_id_cached(session, niche_name)
        if not niche_id:
            return ""

        from getviews_pipeline.supabase_client import get_service_client
        client = get_service_client()
        loop = asyncio.get_event_loop()

        def _query() -> list[dict]:
            return (
                client.table("niche_insights")
                .select("insight_text,execution_tip,staleness_risk,quality_flag")
                .eq("niche_id", niche_id)
                .is_("quality_flag", None)  # only surface non-flagged insights
                .order("week_of", desc=True)
                .limit(1)
                .execute()
            ).data or []

        rows = await loop.run_in_executor(None, _query)
        if not rows:
            return ""

        row = rows[0]
        insight_text = row.get("insight_text") or ""
        execution_tip = row.get("execution_tip") or ""
        staleness = row.get("staleness_risk") or "LOW"

        if not insight_text:
            return ""

        block = (
            f"PHÂN TÍCH NGÁCH TUẦN NÀY (Layer 0 — pre-computed, staleness={staleness}):\n"
            f"{insight_text}\n"
        )
        if execution_tip:
            block += f"Tip áp dụng ngay: {execution_tip}\n"
        block += (
            "\nSử dụng dữ liệu trên để INFORM nhận định — "
            "so sánh video user với common_visual/common_timing của top formula. "
            "KHÔNG dump raw JSON. KHÔNG bịa cơ chế ngoài dữ liệu trên."
        )
        return block
    except Exception as exc:
        logger.warning("[layer0_context] fetch failed (non-fatal): %s", exc)
        return ""


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

    # ── Niche resolution (3-tier, best-signal-first) ──────────────────────────
    # Tier 1: explicit override or session niche (most reliable — set by onboarding
    #         or a prior content_directions intent in the same session).
    # Tier 2: DB-backed hashtag→niche map (classify_from_hashtags). Knows that
    #         e.g. #xinh maps to "thoi_trang" from learned corpus associations.
    # Tier 3: Raw first-non-generic hashtag or description snippet (last resort,
    #         often produces poor niche strings like "trendingtiktok").
    if niche_override:
        niche = niche_override
    elif session.get("niche"):
        niche = session["niche"]
    else:
        _sb = get_service_client()
        _db_niche_id = await classify_from_hashtags(meta.hashtags, _sb)
        if _db_niche_id is not None:
            # Resolve niche_id → display name from niche_taxonomy
            try:
                _row = _sb.table("niche_taxonomy").select("name_vn, name_en").eq("id", _db_niche_id).single().execute()
                _tax = _row.data or {}
                niche = _tax.get("name_vn") or _tax.get("name_en") or infer_niche_from_hashtags(meta.hashtags, meta.description)
            except Exception:
                niche = infer_niche_from_hashtags(meta.hashtags, meta.description)
        else:
            niche = infer_niche_from_hashtags(meta.hashtags, meta.description)

    logger.info("[video_diagnosis] niche resolved=%s hashtags=%s", niche, meta.hashtags[:5])
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

    async def _ref_with_timeout(aweme: dict[str, Any]) -> dict[str, Any]:
        try:
            return await asyncio.wait_for(_ref(aweme), timeout=60.0)
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning("[ref_timeout] aweme_id=%s — skipped: %s", aweme.get("aweme_id"), e)
            return {"_skipped": True}

    user_task = asyncio.create_task(_user())
    ref_tasks = [asyncio.create_task(_ref_with_timeout(a)) for a in picks]
    user_res = await user_task
    ref_results = await asyncio.gather(*ref_tasks)
    references = [r for r in ref_results if "analysis" in r and not r.get("_skipped")]

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

    # Layer 0 context — pre-computed mechanism insight for this niche (fail-open)
    layer0_context = await _get_niche_insight(niche, session)

    emit(step_queue, step_done(f"Đã phân tích {1 + len(references)} video — đang viết báo cáo..."))

    # Detect content format from user analysis — reuse corpus_ingest classifier.
    user_analysis_dict = user_res.get("analysis") or {}
    user_metadata_dict = user_res.get("metadata") or {}
    niche_id_for_format = 0  # format classifier uses niche_id for mukbang heuristic;
                              # 0 = unknown is safe (falls back to keyword matching only)
    content_format = classify_format(user_analysis_dict, niche_id_for_format)

    # Build user_stats from metadata for the synthesis prompt.
    # VideoMetadata.model_dump() nests engagement metrics under "metrics" sub-dict.
    _metrics = user_metadata_dict.get("metrics") or {}
    user_stats: dict[str, Any] = {
        "views": _metrics.get("views") or 0,
        "likes": _metrics.get("likes") or 0,
        "comments": _metrics.get("comments") or 0,
        "shares": _metrics.get("shares") or 0,
        "bookmarks": _metrics.get("bookmarks") or 0,
        "engagement_rate": user_metadata_dict.get("engagement_rate") or 0.0,
        "breakout_multiplier": user_metadata_dict.get("breakout") or None,
        "duration": user_metadata_dict.get("duration_sec") or 0,
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
                layer0_context=layer0_context,
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
                wants_directions=_wants_directions(user_message),
                layer0_context=layer0_context,
            )
        # Server-side guarantee: ensure all reference videos appear as video_ref
        # blocks regardless of whether Gemini emitted them. Appended only for refs
        # whose video_id is not already present in the synthesis text.
        already_emitted = set(re.findall(r'"video_id"\s*:\s*"([^"]+)"', diagnosis))

        injected_blocks: list[str] = []
        now_ts = time.time()
        for ref in references:
            # refs are raw aweme dicts — read fields directly from aweme structure
            vid = str(ref.get("aweme_id") or "")
            if not vid or vid in already_emitted:
                continue
            author = ref.get("author") or {}
            handle = str(author.get("unique_id") or author.get("sec_uid") or "")
            stats = ref.get("statistics") or {}
            views = int(stats.get("play_count") or 0)
            create_time = int(ref.get("create_time") or 0)
            days_ago = int((now_ts - create_time) / 86400) if create_time > 0 else 0
            breakout = float(ref.get("breakout_multiplier") or 0.0)
            thumb = str(ref.get("thumbnail_url") or "")
            block: dict = {
                "type": "video_ref",
                "video_id": vid,
                "handle": f"@{handle}" if handle and not handle.startswith("@") else handle,
                "views": views,
                "days_ago": days_ago,
            }
            if breakout > 1.0:
                block["breakout"] = round(breakout, 1)
            if thumb:
                block["thumbnail_url"] = thumb
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
    """KOL / creator discovery — reference posts + synthesis (free intent on product).

    niche passed from main.py is the session niche, which may be unset or set to
    an unrelated niche from a previous question (e.g. the user asked about skincare
    before now asking for watch-brand KOCs). We always re-derive the target niche
    from the current questions so the video pool matches what the user actually asked.
    """
    sem = get_analysis_semaphore()
    # Re-derive search niche from the current question — session niche is often
    # stale or unrelated when the user asks about a specific product/brand.
    search_niche = await run_sync(_extract_kol_target_niche, questions, session.get("niche"))
    pool = await _niche_aweme_pool(search_niche, period=30)
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
        "niche": search_niche,
        "reference_count": len(analyzed),
        "analyzed_videos": analyzed,
    }
    synthesis = await run_sync(
        synthesize_intent_markdown,
        "find_creators",
        payload,
        collapsed_questions=questions if len(questions) > 1 else None,
        niche_key=search_niche,
    )
    session["kol_search"] = synthesis
    completed = session.setdefault("completed_intents", [])
    if "find_creators" not in completed:
        completed.append("find_creators")
    _bump_analyses_summary(
        session,
        niche=search_niche,
        delta_videos=len(analyzed),
        intent_label="find_creators",
    )
    return {
        "intent": "find_creators",
        "niche": search_niche,
        "synthesis": synthesis,
        "analyzed_videos": analyzed,
    }


async def run_creator_search(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    """KOL/KOC finder — EnsembleData user search + corpus lookup + Gemini per-creator reason.

    Flow:
    1. Extract product/niche keywords from questions via Gemini (cheap call).
    2. Search EnsembleData /tt/user/search for creators in that niche.
    3. Filter: min_followers=5 000, compute ER = heartCount / followerCount * 100, min_er=5.
    4. Pick top 3 by ER.
    5. For each, look up 1 representative video from video_corpus (by creator_handle).
    6. Call Gemini to write a 2-sentence "why this creator fits" reason per creator.
    7. Return synthesis with inline creator_card JSON blocks.
    """
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _response_text,
        GEMINI_KNOWLEDGE_MODEL,
        GEMINI_KNOWLEDGE_FALLBACKS,
        GEMINI_SYNTHESIS_MODEL,
        GEMINI_SYNTHESIS_FALLBACKS,
    )
    from google.genai import types as _types  # type: ignore

    # ── Step 1: extract search keyword ────────────────────────────────────────
    search_niche = await run_sync(_extract_kol_target_niche, questions, session.get("niche"))
    logger.info("[creator_search] search_niche=%r", search_niche)

    # ── Step 2: EnsembleData user search ──────────────────────────────────────
    MIN_FOLLOWERS = 5_000
    MIN_ER = 5.0

    try:
        raw_users, _ = await ensemble.fetch_user_search(search_niche)
    except Exception as exc:
        logger.warning("[creator_search] EnsembleData user search failed: %s", exc)
        raw_users = []

    # ── Step 3: filter and score ───────────────────────────────────────────────
    def _parse_user(u: dict[str, Any]) -> dict[str, Any] | None:
        """Normalise one EnsembleData userInfo dict to our schema."""
        # EnsembleData may nest under .user / .stats or at top level
        user_obj = u.get("user") or u
        stats_obj = u.get("stats") or u

        handle = str(
            user_obj.get("uniqueId") or user_obj.get("unique_id") or ""
        ).strip().lstrip("@")
        if not handle:
            return None

        followers = int(stats_obj.get("followerCount") or stats_obj.get("follower_count") or 0)
        hearts = int(stats_obj.get("heartCount") or stats_obj.get("heart_count") or 0)

        if followers < MIN_FOLLOWERS:
            return None

        er = round(hearts / followers * 100, 1) if followers > 0 else 0.0
        if er < MIN_ER:
            return None

        return {
            "handle": f"@{handle}",
            "followers": followers,
            "er": er,
            "hearts": hearts,
            "nickname": str(user_obj.get("nickname") or handle),
        }

    candidates: list[dict[str, Any]] = []
    for raw in raw_users:
        parsed = _parse_user(raw)
        if parsed:
            candidates.append(parsed)

    # Sort by ER desc, take top 3
    top3 = sorted(candidates, key=lambda c: c["er"], reverse=True)[:3]

    if not top3:
        logger.warning("[creator_search] no qualifying creators for niche=%r", search_niche)

    # ── Step 4: corpus lookup — 1 representative video per creator ─────────────
    def _get_anon() -> Any:
        from getviews_pipeline.corpus_context import _anon_client as _ac
        return _ac()

    def _fetch_avatar_video(handle_raw: str) -> str | None:
        """Return video_id of highest-view video for this creator in video_corpus."""
        try:
            client = _get_anon()
            h = handle_raw.lstrip("@")
            result = (
                client.table("video_corpus")
                .select("video_id")
                .ilike("creator_handle", h)
                .order("views", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                return str(rows[0]["video_id"])
        except Exception as exc:
            logger.warning("[creator_search] corpus lookup failed for %s: %s", handle_raw, exc)
        return None

    # Run corpus lookups concurrently
    avatar_video_ids = await asyncio.gather(
        *[run_sync(_fetch_avatar_video, c["handle"]) for c in top3]
    )

    for creator, vid in zip(top3, avatar_video_ids):
        creator["avatar_video_id"] = vid or ""

    # ── Step 5: Gemini per-creator reason ─────────────────────────────────────
    question_text = " | ".join(questions)

    async def _reason_for(creator: dict[str, Any]) -> str:
        prompt = (
            f"Người dùng cần tìm creator cho: \"{question_text}\"\n\n"
            f"Creator: {creator['handle']} — {creator['followers']:,} followers, "
            f"ER {creator['er']}%\n\n"
            "Viết ĐÚNG 2 câu tiếng Việt ngắn gọn giải thích tại sao creator này phù hợp "
            "cho chiến dịch trên. Câu 1: mô tả phong cách/content của họ. "
            "Câu 2: tại sao phù hợp với thương hiệu/sản phẩm này. "
            "Chỉ trả về 2 câu, không thêm gì khác."
        )
        try:
            cfg = _types.GenerateContentConfig(temperature=0.7, max_output_tokens=128)
            resp = _generate_content_models(
                [prompt],
                primary_model=GEMINI_KNOWLEDGE_MODEL,
                fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
                config=cfg,
            )
            return _response_text(resp).strip()
        except Exception as exc:
            logger.warning("[creator_search] reason generation failed for %s: %s", creator["handle"], exc)
            return f"Creator với {creator['followers']:,} followers và ER {creator['er']}%."

    reasons = await asyncio.gather(*[_reason_for(c) for c in top3])
    for creator, reason in zip(top3, reasons):
        creator["reason"] = reason

    # ── Step 6: build output with creator_card JSON blocks ────────────────────
    if not top3:
        synthesis = (
            f"Mình chưa tìm được creator phù hợp với **{search_niche}** trong kết quả hiện tại.\n\n"
            "Thử mô tả cụ thể hơn về sản phẩm hoặc phong cách nội dung bạn cần — "
            "ví dụ: 'creator nấu ăn ở Hà Nội', 'KOC skincare dưới 50K followers'."
        )
    else:
        intro = (
            f"Mình tìm được **{len(top3)} creator** phù hợp với **{search_niche}** "
            f"— lọc theo tối thiểu 5.000 followers và engagement rate ≥ 5%:\n\n"
        )
        cards: list[str] = []
        for c in top3:
            card_data = {
                "type": "creator_card",
                "handle": c["handle"],
                "avatar_video_id": c["avatar_video_id"],
                "followers": c["followers"],
                "er": c["er"],
                "reason": c["reason"],
            }
            cards.append(_json.dumps(card_data, ensure_ascii=False))

        synthesis = intro + "\n\n".join(cards) + "\n\n"
        synthesis += (
            "---\n"
            "_Dán @handle vào đây để mình phân tích chi tiết kênh đó — "
            "hook pattern, top video, và chiến lược content._"
        )

    session.setdefault("completed_intents", []).append("creator_search")
    _bump_analyses_summary(
        session,
        niche=search_niche,
        delta_videos=0,
        intent_label="creator_search",
    )

    return {
        "intent": "creator_search",
        "niche": search_niche,
        "synthesis": synthesis,
        "creators": top3,
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
