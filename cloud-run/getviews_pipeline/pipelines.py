"""Intent pipelines: Ensemble search + parallel Gemini analysis + synthesis."""

from __future__ import annotations

import asyncio
import json as _json
import logging
import re
import statistics as stats_module
import time
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import analyze_aweme, detect_language_market_mismatch
from getviews_pipeline.claim_tiers import PATTERN_SPREAD_MIN_INSTANCES
from getviews_pipeline.corpus_context import (
    build_corpus_citation_block,
    fetch_corpus_reference_pool,
    fetch_creator_format_history,
    get_corpus_count_cached,
    get_niche_intelligence,
    get_signal_grades_for_niche,
    get_top_breakout_videos,
    resolve_niche_id_cached,
)
from getviews_pipeline.corpus_ingest import classify_format
from getviews_pipeline.creator_enrich import (
    default_actions,
    derive_red_flags,
    detect_commerce,
    extract_contact,
    needs_product_context,
    rate_ballpark_for_tier,
    tier_from_followers,
)
from getviews_pipeline.enum_labels_vi import carousel_subformat_vi
from getviews_pipeline.gemini import (
    synthesize_diagnosis_carousel_v2,
    synthesize_diagnosis_v2,
    synthesize_intent_markdown,
)
from getviews_pipeline.hashtag_niche_map import (
    _refresh_cache as _refresh_hashtag_cache,
)
from getviews_pipeline.hashtag_niche_map import (
    classify_from_hashtags,
    score_niche_match,
)
from getviews_pipeline.helpers import (
    filter_recency,
    infer_niche_from_hashtags,
    merge_aweme_lists,
    select_reference_videos,
)
from getviews_pipeline.intents import QueryIntent
from getviews_pipeline.output_redesign import hook_type_vi
from getviews_pipeline.pattern_fingerprint import (
    annotate_with_pattern_names,
    get_top_delta_patterns,
)
from getviews_pipeline.persona import build_persona_block, extract_persona_slots
from getviews_pipeline.runtime import get_analysis_semaphore, run_sync
from getviews_pipeline.step_events import (
    emit,
    emit_pipeline_error,
    emit_sentinel,
    label_for_corpus_query,
    step_count,
    step_creator,
    step_done,
    step_error,
    step_process,
    step_search,
    step_start,
)
from getviews_pipeline.supabase_client import get_service_client

logger = logging.getLogger(__name__)

REF_N = 5

SILENT_FORMAT_EXCEPTIONS = frozenset(
    {
        "product_display_silent",
        "ambient_lifestyle",
        "macro_closeup_product",
        "aesthetic_broll",
        "text_overlay_only",
        "faceless",
        "highlight",
    }
)


def _slim_reference_video(r: dict[str, Any], source: str = "corpus") -> dict[str, Any]:
    """Project only fields needed for frontend evidence embeds."""
    aweme_id = r.get("aweme_id") or ""
    author = r.get("author") if isinstance(r.get("author"), dict) else {}
    author_handle = r.get("author_unique_id") or author.get("unique_id")
    thumb = r.get("thumbnail_url") or (r.get("metadata") or {}).get("thumbnail_url")
    stats = r.get("statistics") or {}
    hook_type = r.get("hook_type") or (r.get("analysis") or {}).get("hook_analysis", {}).get(
        "hook_type"
    )
    content_format_val = r.get("content_format") or (r.get("analysis") or {}).get(
        "content_format"
    )
    views_raw = (
        r.get("statistics_play_count")
        or stats.get("play_count")
        or r.get("views")
        or (r.get("metadata") or {}).get("views")
    )
    engagement_rate = r.get("engagement_rate")
    tiktok_url = None
    if author_handle and aweme_id:
        tiktok_url = f"https://tiktok.com/@{author_handle}/video/{aweme_id}"
    return {
        "aweme_id": aweme_id,
        "desc": ((r.get("desc") or "")[:120]) or None,
        "hook_type": hook_type,
        "content_format": content_format_val,
        "views": int(views_raw) if views_raw is not None else None,
        "engagement_rate": float(engagement_rate) if engagement_rate is not None else None,
        "author_handle": author_handle,
        "thumbnail_url": thumb,
        "tiktok_url": tiktok_url,
        "source": source,
    }


def compute_bright_spot_signal(
    er_percentile_rank: float | None,
    views_vs_avg_ratio: float | None,
) -> dict[str, Any] | None:
    """er_percentile_rank is an engagement-rate proxy (50 = at niche avg); not raw retention."""
    if er_percentile_rank is None or views_vs_avg_ratio is None:
        return None

    high_er = er_percentile_rank >= 70
    high_views = views_vs_avg_ratio >= 1.0

    if high_er and not high_views:
        return {
            "signal_type": "hook_only_problem",
            "message_vi": (
                "Engagement rate cao hơn trung bình niche — nội dung tạo được tương tác tốt. "
                "Vấn đề là lượt xem vẫn thấp, nghĩa là hook chưa đủ mạnh để kéo đủ người vào xem."
            ),
        }
    elif high_er and high_views:
        return {
            "signal_type": "performing_well",
            "message_vi": (
                "Video đang hoạt động tốt — cả engagement rate lẫn lượt xem đều vượt mức trung bình format."
            ),
        }
    elif not high_er and not high_views:
        if er_percentile_rank < 30:
            return {
                "signal_type": "content_and_hook",
                "message_vi": (
                    "Cả engagement rate lẫn lượt xem đều dưới mức format trung bình — "
                    "cần xem lại cả hook lẫn nội dung chính."
                ),
            }
        return {
            "signal_type": "hook_and_distribution",
            "message_vi": (
                "Lượt xem và engagement rate đều dưới mức format trung bình — "
                "cần cải thiện cả hook lẫn khả năng phân phối."
            ),
        }
    return None


def classify_performance_tier_corpus(views: int, format_avg: float | None) -> str:
    if not format_avg or format_avg == 0:
        return "unknown"
    ratio = views / format_avg
    if ratio >= 2.0:
        return "hit"
    if ratio < 0.5:
        return "flop"
    return "average"


def refine_performance_tier(corpus_tier: str, views: int, channel_context: dict[str, Any]) -> str:
    if not channel_context.get("available"):
        return corpus_tier
    median_views = channel_context.get("median_views")
    if not median_views or median_views == 0:
        return corpus_tier
    account_ratio = views / float(median_views)
    account_tier = (
        "hit" if account_ratio >= 2.0 else "flop" if account_ratio < 0.5 else "average"
    )
    if corpus_tier == account_tier:
        return corpus_tier
    if {corpus_tier, account_tier} == {"hit", "flop"}:
        return "average"
    return account_tier


def fetch_channel_context_sync(creator_handle: str, current_video_id: str) -> dict[str, Any]:
    handle = creator_handle.lstrip("@").strip()
    vid = str(current_video_id or "").strip()
    if not handle or not vid:
        return {"available": False, "reason": "Thiếu handle hoặc video id để tra kênh"}

    try:
        client = get_service_client()
        res = (
            client.table("video_corpus")
            .select("video_id, caption, views, content_format, posted_at, indexed_at")
            .eq("creator_handle", handle)
            .neq("video_id", vid)
            .order("posted_at", desc=True)
            .limit(10)
            .execute()
        )
        videos = list(res.data or [])
        if len(videos) < 2:
            return {
                "available": False,
                "reason": f"Chỉ có {len(videos)} video khác trong kho — chưa đủ để so sánh",
            }

        view_counts = [int(v.get("views") or 0) for v in videos]
        median_views = float(stats_module.median(view_counts)) if view_counts else 0.0

        sorted_by_views = sorted(
            videos,
            key=lambda v: int(v.get("views") or 0),
            reverse=True,
        )
        top_videos = sorted_by_views[:2]
        bottom_videos = sorted_by_views[-2:]
        fmt_counts = Counter(v.get("content_format") for v in top_videos if v.get("content_format"))
        best_fmt = fmt_counts.most_common(1)[0][0] if fmt_counts else None

        return {
            "available": True,
            "top_videos": [
                {
                    "aweme_id": v.get("video_id"),
                    "desc": v.get("caption"),
                    "views": int(v.get("views") or 0),
                    "content_format": v.get("content_format"),
                }
                for v in top_videos
            ],
            "bottom_videos": [
                {
                    "aweme_id": v.get("video_id"),
                    "desc": v.get("caption"),
                    "views": int(v.get("views") or 0),
                    "content_format": v.get("content_format"),
                }
                for v in bottom_videos
            ],
            "best_performing_format": best_fmt,
            "sample_size": len(videos),
            "median_views": median_views,
        }
    except Exception as exc:
        msg = str(exc)[:80]
        return {"available": False, "reason": f"Lỗi truy vấn kênh: {msg}"}


async def _run_channel_context(creator_handle: str, current_video_id: str) -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        fetch_channel_context_sync,
        creator_handle,
        current_video_id,
    )


def _format_avg_views_for_diagnosis(niche_id: int, content_format: str) -> float | None:
    if not niche_id or not content_format:
        return None
    try:
        from getviews_pipeline.corpus_ingest import _content_class_for
        from getviews_pipeline.video_niche_benchmark import fetch_content_class_intelligence_sync

        cc = _content_class_for(niche_id, content_format)
        if cc:
            row = fetch_content_class_intelligence_sync(get_service_client(), cc)
            if row:
                v = row.get("median_views") or row.get("avg_views")
                if v:
                    return float(v)
        since_dt = datetime.now(UTC) - timedelta(days=30)
        since_iso = since_dt.isoformat()
        client = get_service_client()
        res = (
            client.table("video_corpus")
            .select("views")
            .eq("niche_id", niche_id)
            .eq("content_format", content_format)
            .gte("indexed_at", since_iso)
            .limit(150)
            .execute()
        )
        vals = sorted(int(r.get("views") or 0) for r in (res.data or []))
        if len(vals) < 5:
            return None
        return float(vals[len(vals) // 2])
    except Exception as exc:
        logger.warning("[video_diagnosis] format_avg lookup failed: %s", exc)
        return None


def _estimate_er_percentile_rank(user_er: float, niche_avg_er: float | None) -> float | None:
    """Estimate where user's engagement rate sits relative to niche avg (50 = at average).

    This is an ER-based proxy, not raw TikTok retention data. Callers should not label
    the output as "retention" in user-visible copy.
    """
    if niche_avg_er is None or niche_avg_er <= 0:
        return None
    ratio = float(user_er) / float(niche_avg_er)
    # Map ratio≈1.0 → rank 50; clamp 5–95 to avoid saturate messaging.
    ranked = 50.0 + (ratio - 1.0) * 40.0
    return max(5.0, min(95.0, ranked))


def _reference_evidence_lines(
    refs: list[dict[str, Any]],
    corpus_source: str,
) -> str:
    lines: list[str] = []
    for ref in refs:
        aid = ref.get("aweme_id") or ""
        stats = ref.get("statistics") or {}
        vc = int(stats.get("play_count") or 0)
        dsc = (ref.get("desc") or "")[:60]
        src = corpus_source if ref.get("_from_corpus") else "live_search"
        lines.append(f"- aweme_id: {aid} | desc: {dsc} | views: {vc} | source: {src}")
    return "\n".join(lines)

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
    from google.genai import types as _types  # type: ignore

    from getviews_pipeline.gemini import (
        GEMINI_KNOWLEDGE_FALLBACKS,
        GEMINI_KNOWLEDGE_MODEL,
        _generate_content_models,
        _response_text,
    )

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


def _inject_creator_card_blocks(synthesis: str, analyzed: list[dict[str, Any]]) -> str:
    """Append creator_card JSON blocks for each unique creator in analyzed KOL videos.

    One block per creator handle — uses the creator's best video_id as avatar source.
    The R2 frame URL for that video_id gives a stable thumbnail (not expiring TikTok CDN).
    """
    seen_handles: set[str] = set()
    blocks: list[str] = []

    for ref in analyzed:
        meta = ref.get("metadata") or {}
        author = meta.get("author") or {}
        handle = str(author.get("username") or "")
        if not handle or handle in seen_handles:
            continue
        seen_handles.add(handle)

        video_id = str(meta.get("video_id") or ref.get("aweme_id") or "")
        followers_raw = int(author.get("follower_count") or 0)
        if followers_raw >= 1_000_000:
            followers_str = f"{followers_raw / 1_000_000:.1f}M"
        elif followers_raw >= 1_000:
            followers_str = f"{followers_raw / 1_000:.0f}K"
        else:
            followers_str = str(followers_raw) if followers_raw > 0 else "?"

        views = int(meta.get("views") or 0)
        likes = int(meta.get("likes") or meta.get("digg_count") or 0)
        comments = int(meta.get("comments") or meta.get("comment_count") or 0)
        shares = int(meta.get("shares") or meta.get("share_count") or 0)
        er = round((likes + comments + shares) / views * 100, 1) if views > 0 else 0.0

        analysis = ref.get("analysis") or {}
        hook_type = str(analysis.get("hook_type") or "")

        block: dict = {
            "type": "creator_card",
            "handle": f"@{handle}" if not handle.startswith("@") else handle,
            "avatar_video_id": video_id,
            "followers": followers_str,
            "er": f"{er}%",
        }
        if hook_type:
            block["hook_style"] = hook_type

        blocks.append(_json.dumps(block, ensure_ascii=False))

    if blocks:
        synthesis = synthesis.rstrip() + "\n\n" + "\n".join(blocks)
    return synthesis


def _first_handle(analyzed: list[dict[str, Any]]) -> str:
    for a in analyzed:
        meta = a.get("metadata") or {}
        author = meta.get("author") or {}
        h = str(author.get("username") or "").lstrip("@")
        if h:
            return h
    return ""


def _build_follow_ups(
    intent: str,
    niche_label: str,
    analyzed: list[dict[str, Any]] | None = None,
    *,
    handle: str | None = None,
    topic: str = "",
) -> list[str]:
    """Rule-based Vietnamese follow-up suggestions shown as chips after each response.

    Kept rule-based (not another Gemini call) so the chips are free to render and
    ship instantly. Clicks route to the free `follow_up` intent on the client.
    Capped at 3 chips per response to keep the UI tight.
    """
    n = niche_label or "ngách này"
    picked_handle = handle or _first_handle(analyzed or [])

    chips: list[str] = []
    if intent == "content_directions":
        # Progressive disclosure — Phase 2 chips unlock prioritisation + cadence
        # + metrics the core response intentionally defers.
        chips.append("Hướng nào nên thử trước?")
        chips.append(f"Lên kế hoạch 30 ngày trộn 3 hướng cho {n}")
        chips.append("Metric target tuần đầu cho mỗi hướng")
    elif intent == "trend_spike":
        # Progressive disclosure — deferred saturation, urgency, adaptation,
        # and production-cost details each get a dedicated chip.
        chips.append("Trend nào ít cạnh tranh nhất (low saturation)?")
        chips.append("Trend này bao giờ hết hot?")
        chips.append(f"Adapt trend top 1 cho ngách {n} thế nào?")
    elif intent == "video_diagnosis":
        # Progressive disclosure — each chip maps to a deferred section the
        # synthesis prompt intentionally didn't elaborate. See
        # artifacts/docs/features/output-discipline.md.
        chips.append("Cho mình 3 hook thay thế chi tiết")
        chips.append("Gợi ý 3 thay đổi cụ thể cho video tiếp theo")
        chips.append("Thumbnail nên chỉnh thế nào?")
    elif intent == "competitor_profile":
        # Deferred depths: hook library, posting pattern, monetization, style-clone brief.
        chips.append("3 công thức hook hay nhất của họ")
        chips.append("Họ đăng vào khung giờ nào, tuần mấy post?")
        if picked_handle:
            chips.append(f"Tạo brief nhái phong cách của @{picked_handle}")
        else:
            chips.append("Họ đang kiếm tiền thế nào?")
    elif intent == "shot_list":
        # Progressive disclosure — each chip unlocks a deferred artifact
        # (caption bundle / cover / prep checklist / length variants).
        chips.append("Viết caption + 5 hashtag cho video này")
        chips.append("Gợi ý cover/thumbnail")
        chips.append("Checklist chuẩn bị quay (dụng cụ, ánh sáng)")
    elif intent == "brief_generation":
        # Progressive disclosure — commercial / legal / KPI layers each
        # get a dedicated chip so the creative core stays readable.
        chips.append("Thêm budget + KPI target cho brief này")
        chips.append("Viết disclosure (#hợp tác) + usage rights clause")
        chips.append("Tạo checklist deliverables (video + story + caption)")
    elif intent == "own_channel":
        # Progressive disclosure — each chip unlocks a deferred audit layer.
        chips.append("Phân tích content mix của tôi (% review/GRWM/trend)")
        chips.append("Cho mình 3 hook thí nghiệm cho tuần sau")
        chips.append("Metric target 4 tuần tới — views + ER cần tăng bao nhiêu?")
    elif intent == "creator_search":
        chips.append("Gợi ý brief cho KOL đầu danh sách")
        chips.append(f"Xu hướng {n} tuần này")
        chips.append(f"Hướng content đang chạy cho {n}")
    # Dedupe while preserving order, cap at 3.
    seen: set[str] = set()
    unique: list[str] = []
    for c in chips:
        if c and c not in seen:
            unique.append(c)
            seen.add(c)
    return unique[:3]


def _coverage_dict(
    niche_id: int | None,
    niche_name: str,
    count: int,
    ref_count: int,
    source: str,
    freshness_days: int,
) -> dict[str, Any]:
    return {
        "niche_id": niche_id,
        "niche_label": niche_name,
        "corpus_count": count,
        "reference_count": ref_count,
        "source": source,
        "freshness_days": freshness_days,
    }


async def run_content_directions(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    try:
        sem = get_analysis_semaphore()
        emit(step_queue, step_start(f"Đang tìm hướng nội dung cho '{niche}'..."))
        emit(step_queue, step_search("corpus", label_for_corpus_query(niche)))
        fa: dict[str, Any] = session.setdefault("full_analyses", {})
        cached_ids = set(fa.keys())

        corpus_pool = await fetch_corpus_reference_pool(niche, days=30, limit=20)
        corpus_source = "corpus"
        if len(corpus_pool) >= REF_N:
            corpus_pool.sort(key=lambda v: float(v.get("_corpus_er") or 0.0), reverse=True)
            picks = [v for v in corpus_pool if v.get("aweme_id") not in cached_ids][:REF_N]
            pool = corpus_pool
        else:
            # P0-2: tag the provenance so the synthesis prompt knows to disclaim.
            corpus_source = "live_search" if len(corpus_pool) == 0 else "sparse_fallback"
            logger.info(
                "[content_directions] corpus pool too small (%d) for niche '%s', using live search (source=%s)",
                len(corpus_pool), niche, corpus_source,
            )
            emit(step_queue, step_search("ensemble", label_for_corpus_query(niche)))
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

        # Annotate each analyzed reference with its pattern display_name so the
        # synthesis can group directions by pattern family. Fails open —
        # missing pattern_id leaves the field unset; the prompt tolerates it.
        try:
            from getviews_pipeline.corpus_context import _anon_client as _ac

            vid_ids = [str((r.get("metadata") or {}).get("video_id") or "") for r in analyzed]
            vid_ids = [v for v in vid_ids if v]
            name_by_vid = await annotate_with_pattern_names(_ac(), vid_ids)
            for r in analyzed:
                vid = str((r.get("metadata") or {}).get("video_id") or "")
                if vid and vid in name_by_vid:
                    r.setdefault("metadata", {})["pattern_display_name"] = name_by_vid[vid]
        except Exception as exc:
            logger.warning("[content_directions] pattern annotate failed: %s", exc)

        niche_id = await resolve_niche_id_cached(session, niche)
        count, niche_name = await get_corpus_count_cached(
            session, niche_id=niche_id, days=30, niche_name=niche
        )
        citation = build_corpus_citation_block(
            count,
            niche_name,
            days=30,
            reference_count=len(analyzed),
            source=corpus_source,
        )
        logger.info(
            "[content_directions] niche_input=%r resolved=%r niche_id=%s corpus_count=%d refs=%d source=%s",
            niche, niche_name, niche_id, count, len(analyzed), corpus_source,
        )
        emit(step_queue, step_done("Đã phân tích xong — đang tổng hợp hướng nội dung..."))

        persona = extract_persona_slots(" ".join(questions))
        persona_block = build_persona_block(persona)

        payload = {
            "niche": niche,
            "reference_count": len(analyzed),
            "analyzed_videos": analyzed,
            "persona": persona.asdict() if not persona.is_empty() else None,
        }
        synthesis = await run_sync(
            synthesize_intent_markdown,
            "content_directions",
            payload,
            collapsed_questions=questions if len(questions) > 1 else None,
            niche_key=niche,
            corpus_citation=citation,
            persona_block=persona_block,
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
        coverage = _coverage_dict(niche_id, niche_name, count, len(analyzed), corpus_source, 30)
        follow_ups = _build_follow_ups("content_directions", niche_name, analyzed)
        return {
            "intent": "content_directions",
            "niche": niche,
            "synthesis": synthesis,
            "analyzed_videos": analyzed,
            "directions": directions_struct,
            "coverage": coverage,
            "follow_ups": follow_ups,
        }
    except Exception as exc:
        emit_pipeline_error(step_queue, exc, code="content_directions_failed")
        raise
    finally:
        emit_sentinel(step_queue)


async def run_trend_spike(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
    step_queue: asyncio.Queue | None = None,
) -> dict[str, Any]:
    try:
        sem = get_analysis_semaphore()
        emit(step_queue, step_start(f"Đang tìm xu hướng '{niche}'..."))
        emit(step_queue, step_search("corpus", label_for_corpus_query(niche, window_days=7)))
        fa = session.setdefault("full_analyses", {})
        cached_ids = set(fa.keys())

        # Prefer corpus (7-day window) for niche-accurate trend videos.
        corpus_pool = await fetch_corpus_reference_pool(niche, days=7, limit=20)
        corpus_source = "corpus"
        if len(corpus_pool) >= REF_N:
            # Sort by breakout_multiplier for trend spike — highest breakout wins
            corpus_pool.sort(key=lambda v: float(v.get("_corpus_breakout") or 0.0), reverse=True)
            picks = [v for v in corpus_pool if v.get("aweme_id") not in cached_ids][:REF_N]
            pool = corpus_pool
        else:
            corpus_source = "live_search" if len(corpus_pool) == 0 else "sparse_fallback"
            logger.info(
                "[trend_spike] corpus pool too small (%d) for niche '%s' (7d), using live search (source=%s)",
                len(corpus_pool), niche, corpus_source,
            )
            emit(step_queue, step_search("ensemble", label_for_corpus_query(niche, window_days=7)))
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
        citation = build_corpus_citation_block(
            count, niche_name, days=7,
            reference_count=len(picks),
            source=corpus_source,
        )
        persona = extract_persona_slots(" ".join(questions))
        persona_block = build_persona_block(persona)
        logger.info(
            "[trend_spike] niche_input=%r resolved=%r niche_id=%s corpus_count=%d source=%s",
            niche, niche_name, niche_id, count, corpus_source,
        )

        # Enrich with real breakout + signal data (P1-7 + P1-8)
        emit(step_queue, step_search("corpus", label_for_corpus_query(niche, window_days=7)))

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

        # Pattern fingerprints — top 3 rising patterns for this niche. Empty
        # list on missing table / never-run clustering — prompt handles both.
        top_patterns: list[dict[str, Any]] = []
        try:
            from getviews_pipeline.corpus_context import _anon_client as _ac

            top_patterns = await get_top_delta_patterns(_ac(), niche_id, limit=3)
        except Exception as exc:
            logger.warning("[trend_spike] top_delta_patterns fetch failed: %s", exc)

        # Resolve niche_spread id[] → [{id, label}] so the frontend can render
        # spread chips without a second round-trip. Fails open to empty labels.
        from getviews_pipeline.corpus_context import get_niche_label_map

        try:
            niche_label_map = await get_niche_label_map()
        except Exception as exc:
            logger.warning("[trend_spike] niche label map failed: %s", exc)
            niche_label_map = {}

        def _spread_with_labels(raw_ids: list[int] | None) -> list[dict[str, Any]]:
            if not raw_ids:
                return []
            out: list[dict[str, Any]] = []
            seen: set[int] = set()
            for nid in raw_ids:
                try:
                    i = int(nid)
                except (TypeError, ValueError):
                    continue
                if i in seen:
                    continue
                seen.add(i)
                label = niche_label_map.get(i) or str(i)
                out.append({"id": i, "label": label})
            return out

        # Drop patterns too thin to cite — per claim_tiers.pattern_spread
        # threshold (10 weekly instances). A pattern with fewer instances is
        # coincidence, not signal, and "lan sang N ngách" fires misleadingly
        # on those. Cross-niche vs single-niche is still decided downstream
        # from niche_spread_count.
        patterns_payload = [
            {
                "display_name": p.get("display_name") or "Pattern",
                "instance_count_week": int(p.get("weekly_instance_count") or 0),
                "instance_count_prev_week": int(p.get("weekly_instance_count_prev") or 0),
                "weekly_delta": int(p.get("weekly_instance_count") or 0)
                - int(p.get("weekly_instance_count_prev") or 0),
                "niche_spread_count": len(p.get("niche_spread") or []),
                "niche_spread": _spread_with_labels(p.get("niche_spread")),
                "signature": p.get("signature") or {},
            }
            for p in top_patterns
            if int(p.get("weekly_instance_count") or 0) >= PATTERN_SPREAD_MIN_INSTANCES
        ]

        emit(step_queue, step_done("Đã tổng hợp dữ liệu — đang viết phân tích..."))
        payload = {
            "niche": niche,
            "window_days": 7,
            "analyzed_videos": analyzed,
            "breakout_videos": breakout_videos,
            "signal_grades": signal_grades,
            "trending_sounds": trending_sounds,
            "patterns": patterns_payload,
        }
        synthesis = await run_sync(
            synthesize_intent_markdown,
            "trend_spike",
            payload,
            collapsed_questions=questions if len(questions) > 1 else None,
            niche_key=niche,
            corpus_citation=citation,
            persona_block=persona_block,
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
            "coverage": _coverage_dict(niche_id, niche_name, count, len(analyzed), corpus_source, 7),
            "follow_ups": _build_follow_ups("trend_spike", niche_name, analyzed),
            "patterns": patterns_payload,
        }
    except Exception as exc:
        emit_pipeline_error(step_queue, exc, code="trend_spike_failed")
        raise
    finally:
        emit_sentinel(step_queue)


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
    emit_sentinel(step_queue)
    return {
        "intent": "competitor_profile",
        "handle": handle,
        "synthesis": synthesis,
        "analyzed_videos": analyzed,
        "follow_ups": _build_follow_ups(
            "competitor_profile",
            session.get("niche") or "ngách này",
            analyzed,
            handle=handle,
        ),
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
        emit(step_queue, step_search("corpus", label_for_corpus_query(niche or topic or "ngách")))
        niche_id = await resolve_niche_id_cached(session, niche)
        count, niche_name = await get_corpus_count_cached(
            session, niche_id=niche_id, days=30, niche_name=niche
        )
        source = "corpus" if count > 0 else "sparse_fallback"
        citation = build_corpus_citation_block(
            count, niche_name, days=30, reference_count=0, source=source,
        )
        persona = extract_persona_slots(" ".join(questions) + " " + (topic or ""))
        persona_block = build_persona_block(persona)
        logger.info(
            "[brief_generation] topic=%r niche_input=%r resolved=%r corpus_count=%d",
            topic, niche, niche_name, count,
        )
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
            persona_block=persona_block,
        )
        emit(step_queue, step_done("Brief xong — đang hiển thị..."))
        _append_completed(session, QueryIntent.BRIEF_GENERATION)
        _bump_analyses_summary(
            session,
            niche=niche or session.get("niche"),
            delta_videos=0,
            intent_label="brief_generation",
        )
        return {
            "intent": "brief_generation",
            "topic": topic,
            "niche": niche,
            "brief": brief,
            "coverage": _coverage_dict(niche_id, niche_name, count, 0, source, 30),
            "follow_ups": _build_follow_ups("brief_generation", niche_name, topic=topic),
        }
    except Exception as exc:
        emit_pipeline_error(step_queue, exc, code="brief_generation_failed")
        raise
    finally:
        emit_sentinel(step_queue)


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
        emit(step_queue, step_search("corpus", label_for_corpus_query(niche or topic or "ngách")))
        niche_id = await resolve_niche_id_cached(session, niche)
        count, niche_name = await get_corpus_count_cached(
            session, niche_id=niche_id, days=30, niche_name=niche
        )
        # shot_list doesn't fetch corpus videos itself — source is always implied
        # as "context" (pulled from prior session turns). If the niche has no
        # corpus rows at all, the citation builder will emit the zero-data
        # disclaimer so the shot list doesn't claim niche benchmarks it lacks.
        source = "corpus" if count > 0 else "sparse_fallback"
        citation = build_corpus_citation_block(
            count, niche_name, days=30, reference_count=0, source=source,
        )
        persona = extract_persona_slots(" ".join(questions) + " " + (topic or ""))
        persona_block = build_persona_block(persona)
        logger.info(
            "[shot_list] topic=%r niche_input=%r resolved=%r corpus_count=%d",
            topic, niche, niche_name, count,
        )
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
            persona_block=persona_block,
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
            "coverage": _coverage_dict(niche_id, niche_name, count, 0, source, 30),
            "follow_ups": _build_follow_ups("shot_list", niche_name, topic=topic),
        }
    except Exception as exc:
        emit_pipeline_error(step_queue, exc, code="shot_list_failed")
        raise
    finally:
        emit_sentinel(step_queue)


_DIRECTION_KEYWORDS = (
    "gợi ý", "định dạng", "ý tưởng", "hướng content",
    "kịch bản", "cho tôi", "cho mình", "ý kiến",
)


def _wants_directions(user_message: str) -> bool:
    """Return True if the user message requests content direction suggestions."""
    lower = user_message.lower()
    return any(kw in lower for kw in _DIRECTION_KEYWORDS)


async def _get_niche_insight(
    niche_name: str, session: dict[str, Any],
) -> tuple[str, str | None]:
    """Fetch current week's Layer 0 mechanism insight for this niche.

    Returns ``(prompt_block, execution_tip)``:
      * ``prompt_block`` — formatted string ready for injection into
        the synthesis voice_block; empty string when no insight.
      * ``execution_tip`` — the raw ``niche_insights.execution_tip``
        value (Wave 3), suitable for rendering as a distinct callout
        on the diagnosis payload. None when the niche has no tip yet.

    Both are derived from the same DB row, so one read fills both.
    Fails open: logs warning + returns ``("", None)``.
    """
    try:
        niche_id = await resolve_niche_id_cached(session, niche_name)
        if not niche_id:
            return "", None

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
            return "", None

        row = rows[0]
        insight_text = row.get("insight_text") or ""
        execution_tip = (row.get("execution_tip") or "").strip() or None
        staleness = row.get("staleness_risk") or "LOW"

        if not insight_text:
            # Tip may still exist even when insight_text is empty — the
            # callout is independent of the prompt block.
            return "", execution_tip

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
        return block, execution_tip
    except Exception as exc:
        logger.warning("[layer0_context] fetch failed (non-fatal): %s", exc)
        return "", None


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
    emit(step_queue, step_search("corpus", label_for_corpus_query(niche)))
    uid = str(user_aweme.get("aweme_id", "") or "")
    cached_ids = set(fa.keys())
    if uid:
        cached_ids.add(uid)
    channel_handle_norm = handle.strip().lstrip("@") if handle else ""
    ch_task: asyncio.Task | None = None
    if channel_handle_norm and uid:
        ch_task = asyncio.create_task(_run_channel_context(channel_handle_norm, uid))

    # Prefer curated corpus (niche-tagged, ≥20k views) over live search to
    # ensure reference videos are actually in the same niche as the user's video.
    corpus_pool = await fetch_corpus_reference_pool(
        niche, days=30, limit=40, exclude_video_id=uid or None
    )
    corpus_source = "corpus"
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
        corpus_source = "live_search" if len(corpus_pool) == 0 else "sparse_fallback"
        logger.warning(
            "[ref_source] niche=%s corpus_hit=false corpus_size=%d threshold=%d source=%s — "
            "falling back to live EnsembleData search (costs API units)",
            niche,
            len(corpus_pool),
            REF_N,
            corpus_source,
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
        except (TimeoutError, Exception) as e:
            logger.warning("[ref_timeout] aweme_id=%s — skipped: %s", aweme.get("aweme_id"), e)
            return {"_skipped": True}

    user_task = asyncio.create_task(_user())
    ref_tasks = [asyncio.create_task(_ref_with_timeout(a)) for a in picks]
    user_res = await user_task
    ref_results = await asyncio.gather(*ref_tasks)
    references = [r for r in ref_results if "analysis" in r and not r.get("_skipped")]

    # Graceful degradation — any carousel error dict from _analyze_carousel()
    # must be caught here before downstream code assumes "analysis" key exists.
    # carousel_no_images: EnsembleData returned no slide URLs (even after aweme_id re-query)
    # carousel_download_failed: CDN download of slides failed (blocked / expired URLs)
    _user_error = user_res.get("error") if isinstance(user_res, dict) else None
    if _user_error in ("carousel_no_images", "carousel_download_failed"):
        _msg = (
            "GetViews chưa tải được ảnh carousel này — CDN TikTok đang chặn tải xuống. "
            "Thử lại sau ít phút hoặc hỏi 'Carousel skincare đang trending?' để xem xu hướng."
            if _user_error == "carousel_download_failed"
            else (
                "Bài ảnh TikTok chưa hỗ trợ — EnsembleData không trả về ảnh slide. "
                "Thử hỏi 'Carousel skincare đang trending?' để xem xu hướng ngách này."
            )
        )
        emit(step_queue, step_error(code=_user_error, message_vi=_msg))
        emit_sentinel(step_queue)
        if ch_task is not None:
            ch_task.cancel()
        return

    niche_id = await resolve_niche_id_cached(session, niche)
    count, niche_name = await get_corpus_count_cached(
        session, niche_id=niche_id, days=30, niche_name=niche
    )
    citation = build_corpus_citation_block(
        count,
        niche_name,
        days=30,
        reference_count=len(references),
        source=corpus_source,
    )
    # P2-1: extract persona from user_message so audience age / pain points /
    # geography aren't silently dropped by the synthesis prompt.
    persona = extract_persona_slots(user_message or "")
    persona_block = build_persona_block(persona)
    logger.info(
        "[video_diagnosis] niche_input=%r resolved=%r niche_id=%s corpus_count=%d refs=%d source=%s",
        niche, niche_name, niche_id, count, len(references), corpus_source,
    )

    # Fetch niche norms from materialized view — fail-open, never raises
    niche_norms = await get_niche_intelligence(niche)
    # Inject an explicit no-data marker when niche_norms is empty so Gemini
    # cannot hallucinate niche benchmarks. The soft prompt instruction alone
    # ("bỏ qua so sánh") is insufficient — an explicit _note in the JSON is
    # harder for the model to ignore than prose guidance.
    if not niche_norms:
        niche_norms = {"_note": "Không có data niche — KHÔNG tạo số liệu niche, KHÔNG so sánh với chuẩn niche"}

    # Layer 0 context — pre-computed mechanism insight for this niche (fail-open).
    # Wave 3: also surface the raw execution_tip on the output so the FE can
    # render it as a distinguished callout (not just buried in prompt context).
    layer0_context, niche_execution_tip = await _get_niche_insight(niche, session)

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

    carousel_format: str | None = None
    diagnosis: str
    narrative_vi_out: dict[str, Any] | None = None
    format_cards_out: list[dict[str, Any]] | None = None
    bright_spot_out: dict[str, Any] | None = None
    channel_context_out: dict[str, Any] | None = None
    refined_performance_tier_out: str | None = None
    diagnosis_errors_out: list[dict[str, Any]] | None = None
    diagnosis_kpi_out: dict[str, Any] | None = None
    if include_diagnosis:
        if user_content_type == "carousel":
            # ch_task is not used by the carousel path — cancel immediately to avoid leak.
            if ch_task is not None:
                ch_task.cancel()
                ch_task = None
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
            # OQ-1 + OQ-2: fetch creator's own format history from corpus for
            # account-level format pattern diagnosis and baseline multiplier.
            # Fail-open: None = creator not in corpus → omit section entirely.
            _author_handle = (user_metadata_dict.get("author") or {}).get("username") or ""
            creator_history = await fetch_creator_format_history(_author_handle)
            creator_format_history_block = ""
            if creator_history and creator_history["carousel_count"] > 0:
                _cc = creator_history["carousel_count"]
                _vc = creator_history["video_count"]
                _total = creator_history["total_posts"]
                _cavg = creator_history.get("carousel_avg_views")
                _vavg = creator_history.get("video_recent_avg")
                _mult = creator_history.get("multiplier")
                _top_cv = creator_history.get("top_carousel_views")
                lines = [
                    "## LỊCH SỬ FORMAT KÊNH (từ kho phân tích)",
                    f"Trong {_total} bài top của @{_author_handle} trong kho dữ liệu: "
                    f"{_cc} carousel / {_vc} video.",
                ]
                if _cavg:
                    lines.append(f"Trung bình views carousel: {_cavg:,}.")
                if _vavg:
                    lines.append(f"Trung bình views video gần đây (5 bài): {_vavg:,}.")
                if _mult and _mult > 1.0:
                    lines.append(
                        f"Carousel của kênh này đạt trung bình {_mult}× so với video gần đây "
                        f"— dữ liệu thực, không ước lượng."
                    )
                if _top_cv:
                    lines.append(f"Carousel top nhất của kênh: {_top_cv:,} views.")
                lines.append(
                    "Dùng dữ liệu này để đưa ra nhận xét cụ thể về xu hướng format của kênh. "
                    "KHÔNG bịa đặt số liệu ngoài những con số trên."
                )
                creator_format_history_block = "\n".join(lines)
            logger.info(
                "[carousel] routing to synthesize_diagnosis_carousel_v2 "
                "format=%s carousel_refs=%d wants_directions=%s creator_history=%s",
                carousel_format,
                len(carousel_refs),
                include_carousel_directions,
                bool(creator_format_history_block),
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
                corpus_citation=citation,
                persona_block=persona_block,
                creator_format_history_block=creator_format_history_block,
            )
        else:
            loop_fmt = asyncio.get_event_loop()
            format_avg = await loop_fmt.run_in_executor(
                None,
                lambda: _format_avg_views_for_diagnosis(int(niche_id or 0), content_format),
            )
            raw_avg_er = niche_norms.get("avg_engagement_rate")
            niche_avg_er = float(raw_avg_er) if raw_avg_er is not None else None
            user_er = float(user_stats.get("engagement_rate") or 0.0)
            er_percentile_rank = _estimate_er_percentile_rank(user_er, niche_avg_er)
            curr_views = int(user_stats.get("views") or 0)
            views_vs_avg_ratio = (
                curr_views / float(format_avg) if format_avg else None
            )
            bright_spot_signal = compute_bright_spot_signal(er_percentile_rank, views_vs_avg_ratio)
            corpus_tier = classify_performance_tier_corpus(curr_views, format_avg)

            errors: list[dict[str, Any]] = []
            ha0 = user_analysis_dict.get("hook_analysis")
            hook_phrase = (ha0 or {}).get("hook_phrase") if isinstance(ha0, dict) else ""
            hook_text = f"{meta.description or ''} {hook_phrase or ''}".strip()
            lang_error = detect_language_market_mismatch(hook_text)
            if lang_error:
                errors.insert(0, lang_error)
            has_human = bool(user_analysis_dict.get("has_human_speaking_to_camera"))
            has_opinion = bool(user_analysis_dict.get("has_expressed_opinion_or_question"))
            if (
                not has_human
                and not has_opinion
                and content_format not in SILENT_FORMAT_EXCEPTIONS
            ):
                errors.append(
                    {
                        "error_id": "no_human_presence",
                        "title": "Không có người nói chuyện với camera",
                        "detail": (
                            "Video không có mặt người hoặc giọng nói trực tiếp. "
                            "Format này hoạt động tốt hơn khi có người dẫn dắt, "
                            "tạo kết nối cảm xúc với người xem."
                        ),
                        "fix": (
                            "Thêm ít nhất 2-3 giây mặt người nói chuyện thẳng với camera "
                            "tại hook hoặc giữa video."
                        ),
                        "sev": "mid",
                        "t": 0.0,
                        "end": None,
                    }
                )

            kpi_dict: dict[str, Any] = {
                "views": curr_views,
                "likes": int(user_stats.get("likes") or 0),
                "comments": int(user_stats.get("comments") or 0),
                "shares": int(user_stats.get("shares") or 0),
                "bookmarks": int(user_stats.get("bookmarks") or 0),
                "engagement_rate": user_er,
                "er_percentile_rank": er_percentile_rank,
                "format_avg_views": format_avg,
            }
            diagnosis_errors_out = errors
            diagnosis_kpi_out = kpi_dict
            bright_spot_out = bright_spot_signal

            ref_pairs: list[tuple[dict[str, Any], str]] = []
            for ref in references:
                src = (
                    "corpus"
                    if corpus_source in ("corpus", "sparse_fallback")
                    else "live_search"
                )
                ref_pairs.append((ref, src))

            emit(
                step_queue,
                {
                    "type": "pre_synthesis",
                    "errors": errors,
                    "kpi": kpi_dict,
                    "bright_spot_signal": bright_spot_signal,
                    "performance_tier": corpus_tier,
                    "reference_videos": [_slim_reference_video(r, s) for r, s in ref_pairs],
                },
            )

            if ch_task is not None:
                try:
                    channel_context = await ch_task
                except Exception as exc:
                    logger.warning("[video_diagnosis] channel_context task failed: %s", exc)
                    channel_context = {"available": False, "reason": str(exc)[:80]}
            else:
                channel_context = {"available": False, "reason": "Không có handle TikTok"}

            refined_tier = refine_performance_tier(corpus_tier, curr_views, channel_context)
            channel_context_payload = {**channel_context, "performance_tier": refined_tier}
            channel_context_out = channel_context_payload
            refined_performance_tier_out = refined_tier
            emit(step_queue, {"type": "channel_context", **channel_context_payload})

            errors_prompt = list(errors)
            if refined_tier == "hit":
                filtered_sev = [
                    e for e in errors if e.get("sev") == "high"
                ]
                if filtered_sev:
                    errors_prompt = filtered_sev

            evidence_block = _reference_evidence_lines(references, corpus_source)

            diagnosis_md, narrative_vi_out, format_cards_out = await run_sync(
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
                corpus_citation=citation,
                persona_block=persona_block,
                performance_tier=refined_tier,
                channel_context=channel_context_payload,
                errors=errors_prompt,
                reference_evidence_block=evidence_block,
            )
            emit(
                step_queue,
                {
                    "type": "narrative_ready",
                    "narrative_vi": narrative_vi_out,
                    "format_cards": format_cards_out,
                },
            )
            diagnosis = diagnosis_md
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
    emit_sentinel(step_queue)

    # Parallel side-queries — each fails open so a miss never blocks the
    # primary diagnosis path. Share the resolved video_id so both reads hit
    # the same row.
    user_video_id = str((user_res.get("metadata") or {}).get("video_id") or "")

    # Comment radar — sentiment + purchase intent from the video's comment
    # section. Fails open: any fetch / parse error leaves the field unset.
    comment_radar: dict[str, Any] | None = None
    try:
        from getviews_pipeline.comment_radar_cache import resolve_comment_radar

        comment_count_hint = int(
            ((user_res.get("metadata") or {}).get("metrics") or {}).get("comments") or 0
        )
        if user_video_id:
            comment_radar = await resolve_comment_radar(
                user_video_id, comment_count_hint=comment_count_hint,
            )
    except Exception as exc:
        logger.warning("[video_diagnosis] comment_radar resolve failed: %s", exc)

    # Thumbnail tile — one Gemini image call on the t=0 frame URL stored in
    # video_corpus.frame_urls. Resolves to None for user-submitted videos not
    # yet in the corpus (no frame extracted) or on any Gemini / Supabase
    # failure; the frontend tile hides gracefully in that case.
    thumbnail_analysis: dict[str, Any] | None = None
    try:
        from getviews_pipeline.thumbnail_analysis_cache import (
            resolve_thumbnail_analysis,
        )

        if user_video_id:
            thumbnail_analysis = await resolve_thumbnail_analysis(user_video_id)
    except Exception as exc:
        logger.warning("[video_diagnosis] thumbnail resolve failed: %s", exc)

    # Flatten user result for backward compatibility with VideoAnalyzeResult consumers
    out: dict[str, Any] = {
        "intent": "video_diagnosis",
        "niche": niche,
        "user_video": user_res,
        "reference_videos": references,
        "diagnosis": diagnosis,
        "coverage": _coverage_dict(niche_id, niche_name, count, len(references), corpus_source, 30),
        "follow_ups": _build_follow_ups(
            "video_diagnosis",
            niche_name,
            references,
            handle=(user_res.get("metadata") or {}).get("author", {}).get("username"),
        ),
    }
    if niche_execution_tip:
        out["niche_execution_tip"] = niche_execution_tip
    if comment_radar is not None:
        out["comment_radar"] = comment_radar
    if thumbnail_analysis is not None:
        out["thumbnail_analysis"] = thumbnail_analysis
    if "metadata" in user_res:
        out["metadata"] = user_res["metadata"]
    if "analysis" in user_res:
        out["analysis"] = user_res["analysis"]
    if "content_type" in user_res:
        out["content_type"] = user_res["content_type"]
    if carousel_format is not None:
        out["carousel_subformat"] = carousel_format
        out["carousel_subformat_label"] = carousel_subformat_vi(carousel_format, default=carousel_format)
        # slide count from metadata (populated by _analyze_carousel via CarouselAnalysis)
        _slide_count = (user_res.get("metadata") or {}).get("slide_count")
        if _slide_count:
            out["carousel_slide_count"] = int(_slide_count)
    if include_diagnosis and user_content_type == "video":
        if diagnosis_errors_out is not None:
            out["errors"] = diagnosis_errors_out
        if diagnosis_kpi_out is not None:
            out["kpi"] = diagnosis_kpi_out
        if bright_spot_out is not None:
            out["bright_spot_signal"] = bright_spot_out
        if channel_context_out is not None:
            out["channel_context"] = channel_context_out
        if refined_performance_tier_out is not None:
            out["performance_tier"] = refined_performance_tier_out
        if narrative_vi_out is not None:
            out["narrative_vi"] = narrative_vi_out
        if format_cards_out is not None:
            out["format_cards"] = format_cards_out
    return out


async def _enrich_creator_card(
    handle: str,
    pool_stats: dict[str, Any],
    target_niche_id: int | None,
    search_niche: str,
    persona_empty: bool,
    question_text: str,
) -> dict[str, Any]:
    """Build one CreatorCard for a picked handle.

    Lives in one place so the outer run_* stays readable. Fails open — every
    external call is wrapped and falls back to whatever signals we already
    have in `pool_stats`.
    """
    from google.genai import types as _types  # type: ignore

    from getviews_pipeline.corpus_context import (
        _anon_client as _ac,
    )
    from getviews_pipeline.corpus_context import (
        get_cached_analysis,
    )
    from getviews_pipeline.gemini import (
        GEMINI_KNOWLEDGE_FALLBACKS,
        GEMINI_KNOWLEDGE_MODEL,
        _generate_content_models,
        _response_text,
    )

    h = handle.lstrip("@")

    # 1. Last-30 posts from the creator (1 EnsembleData unit).
    last_posts: list[dict[str, Any]] = []
    try:
        last_posts = await ensemble.fetch_user_posts(h, depth=1)
    except Exception as exc:
        logger.warning("[creator_search] fetch_user_posts failed for @%s: %s", h, exc)

    # Normalise to "most recent first" the API already does this but defensive.
    last_posts = last_posts[:20]

    # 2. Real author metadata from the first post (followers, bio, verified).
    author0 = (last_posts[0].get("author") or {}) if last_posts else {}
    followers = int(author0.get("follower_count") or 0)
    display_name = str(author0.get("nickname") or "")
    verified = bool(author0.get("verification_type") and int(author0.get("verification_type") or 0) > 0)
    bio = str(author0.get("signature") or "")
    avatar_url: str | None = None
    ag = author0.get("avatar_thumb") or author0.get("avatar_medium") or author0.get("avatar_larger")
    if isinstance(ag, dict):
        urls = ag.get("url_list") or []
        if urls:
            avatar_url = str(urls[0])

    # 3. Per-post stats — real ER = engagements / (followers × post_count).
    post_captions: list[str] = []
    post_hashtags: list[list[str]] = []
    views_list: list[int] = []
    engagements_sum = 0
    comments_sum = 0
    views_sum = 0
    latest_ts: int = 0
    for p in last_posts:
        desc = str(p.get("desc") or "")
        post_captions.append(desc)
        # EnsembleData text_extra is a list of {hashtag_name, type=1, ...}
        tags_raw = p.get("text_extra") or []
        tags = [t.get("hashtag_name") for t in tags_raw if isinstance(t, dict) and t.get("hashtag_name")]
        post_hashtags.append(tags)
        stats = p.get("statistics") or {}
        v = int(stats.get("play_count") or 0)
        views_list.append(v)
        views_sum += v
        engagements_sum += int(stats.get("digg_count") or 0)
        engagements_sum += int(stats.get("comment_count") or 0)
        engagements_sum += int(stats.get("share_count") or 0)
        comments_sum += int(stats.get("comment_count") or 0)
        ct = int(p.get("create_time") or 0)
        if ct > latest_ts:
            latest_ts = ct

    er_followers_pct: float | None = None
    if followers > 0 and last_posts:
        er_followers_pct = round(engagements_sum / (followers * len(last_posts)) * 100, 2)
    comment_rate_pct = round((comments_sum / views_sum) * 100, 2) if views_sum > 0 else None
    median_views_30d = int(sorted(views_list)[len(views_list) // 2]) if views_list else None
    days_since_last_post: int | None = None
    if latest_ts > 0:
        import time as _t
        days_since_last_post = max(0, int((_t.time() - latest_ts) / 86400))

    # 4. creator_velocity — engagement_trend + posting_frequency, + a 60-day median
    #    proxy (we don't have 60-day posts — use avg_views as a soft check).
    engagement_trend: str | None = None
    posting_frequency_per_week: float | None = None
    median_views_60d: int | None = None
    try:
        client = _ac()
        cv_res = (
            client.table("creator_velocity")
            .select("engagement_trend, posting_frequency_per_week, velocity_score")
            .ilike("creator_handle", h)
            .limit(1)
            .execute()
        )
        cv_rows = cv_res.data or []
        if cv_rows:
            cv = cv_rows[0]
            engagement_trend = cv.get("engagement_trend")
            pf = cv.get("posting_frequency_per_week")
            if pf is not None:
                posting_frequency_per_week = float(pf)
    except Exception as exc:
        logger.warning("[creator_search] creator_velocity lookup failed for @%s: %s", h, exc)

    # 5. Niche match confidence from last-20 hashtags.
    niche_match_conf = 0.0
    if target_niche_id is not None:
        try:
            client = _ac()
            await _refresh_hashtag_cache(client)
            niche_match_conf = round(
                score_niche_match(post_hashtags, target_niche_id), 2,
            )
        except Exception as exc:
            logger.warning("[creator_search] niche_match score failed for @%s: %s", h, exc)

    # 6. Best video — top-ER post from last-20, pull cached analysis for why_it_worked.
    best_video_payload: dict[str, Any] | None = None
    if last_posts:
        def _er(post: dict[str, Any]) -> float:
            s = post.get("statistics") or {}
            v = int(s.get("play_count") or 0)
            if v <= 0:
                return 0.0
            eng = (
                int(s.get("digg_count") or 0)
                + int(s.get("comment_count") or 0)
                + int(s.get("share_count") or 0)
            )
            return eng / v
        best = max(last_posts, key=_er)
        bvid = str(best.get("aweme_id") or "")
        bstats = best.get("statistics") or {}
        cached = await get_cached_analysis(bvid) if bvid else None
        why = ""
        if cached and isinstance(cached.get("analysis"), dict):
            hook_type = str(cached["analysis"].get("hook_analysis", {}).get("hook_type", "") or "")
            content_arc = str(cached["analysis"].get("content_arc") or "")
            why = ", ".join([x for x in [hook_type_vi(hook_type) if hook_type else "", content_arc] if x])
        best_video_payload = {
            "video_id": bvid,
            "thumbnail_url": cached.get("_corpus_thumbnail_url") if cached else None,
            "tiktok_url": f"https://www.tiktok.com/@{h}/video/{bvid}" if bvid else "",
            "views": int(bstats.get("play_count") or 0),
            "why_it_worked": why or "Hook hiệu quả + CTA rõ trong nhịp đầu (suy luận từ ER).",
        }

    # 7. Commerce + contact + red flags (all pure).
    commerce = detect_commerce(bio, post_captions)
    contact = extract_contact(bio)
    tier = tier_from_followers(followers)
    red_flags = derive_red_flags(
        days_since_last_post=days_since_last_post,
        engagement_trend=engagement_trend,
        median_views_30d=median_views_30d,
        median_views_60d=median_views_60d,
        er_followers_pct=er_followers_pct,
        tier=tier,
        commerce=commerce,
    )

    # 8. Persona-aware reason via Gemini.
    facts = (
        f"@{h} — {display_name or h} · {followers:,} followers ({tier})\n"
        f"ER thật {er_followers_pct or '-'}% · median views {median_views_30d or '-'}\n"
        f"Niche match confidence: {niche_match_conf:.0%}\n"
        f"Sponsored posts gần đây: {commerce.recent_sponsored_count}\n"
        f"Shop link: {'có' if commerce.shop_linked else 'không'}\n"
        f"Red flags: {', '.join(red_flags) if red_flags else 'không'}\n"
    )
    reason_prompt = (
        f'Nhu cầu seller: "{question_text}"\n\n'
        f"Creator:\n{facts}\n"
        "Viết 2-3 câu tiếng Việt giải thích TẠI SAO creator này hợp với nhu cầu seller. "
        "Tham chiếu cụ thể đến đặc điểm đối tượng (tuổi, pain point, xuất xứ) nếu seller đã nêu. "
        "Không lặp lại số liệu — chỉ giải thích lý do fit. Không xã giao."
    )
    try:
        cfg = _types.GenerateContentConfig(temperature=0.6, max_output_tokens=180)
        resp = _generate_content_models(
            [reason_prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        reason_text = _response_text(resp).strip()
    except Exception as exc:
        logger.warning("[creator_search] reason gen failed for @%s: %s", h, exc)
        reason_text = (
            f"@{h} post đều trong ngách {search_niche} với ER thật "
            f"{er_followers_pct or '-'}%. Phù hợp làm điểm khởi đầu để brief."
        )

    # 9. Rate + actions.
    rate = rate_ballpark_for_tier(tier).asdict()
    actions = [a.__dict__ for a in default_actions(h, search_niche)]

    return {
        "handle": f"@{h}",
        "display_name": display_name or None,
        "verified": verified,
        "avatar_url": avatar_url,
        "bio_excerpt": bio[:140] if bio else None,
        "followers": followers or pool_stats.get("total_views", 0),
        "tier": tier,
        "posting_frequency_per_week": posting_frequency_per_week,
        "days_since_last_post": days_since_last_post,
        "niche_match": {
            "primary_niche": search_niche,
            "confidence": niche_match_conf,
            "secondary_niches": [],
        },
        "audience": {
            "top_age_bucket": None,   # Phase 2 — hide row in frontend when null
            "gender_skew": None,
            "top_region": None,
        },
        "engagement_rate_followers": er_followers_pct or 0.0,
        "comment_rate": comment_rate_pct or 0.0,
        "median_views": median_views_30d or 0,
        "engagement_trend": engagement_trend,
        "best_video": best_video_payload,
        "commerce": commerce.asdict(),
        "red_flags": red_flags,
        "contact": contact.asdict(),
        "reason": reason_text,
        "rate_ballpark": rate,
        "actions": actions,
    }


async def run_creator_search(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    """Seller-first KOL finder — returns the CreatorCard[] shape documented at
    `artifacts/docs/features/kol-finder.md`.

    Pipeline:
    1. Resolve target niche via niche_match (covers Vietnamese prose inputs).
    2. Pull a keyword+hashtag video pool for that niche (30-day window).
    3. Aggregate by handle → pick top 3 by total views (cheap, deduped).
    4. For each of the 3 handles, fetch their last-30 posts from EnsembleData
       (1 unit each) and build a CreatorCard in parallel.
    5. Append a conversational product-context follow-up chip when the seller
       hasn't given price/competitor info yet.

    Fails open throughout — every external call is wrapped so one creator's
    missing follower data never blocks the other two cards.
    """

    # ── Step 1: resolve niche ────────────────────────────────────────────────
    search_niche = await run_sync(_extract_kol_target_niche, questions, session.get("niche"))
    niche_id = await resolve_niche_id_cached(session, search_niche)
    count, niche_name = await get_corpus_count_cached(
        session, niche_id=niche_id, days=30, niche_name=search_niche,
    )
    logger.info("[creator_search] search_niche=%r resolved=%r niche_id=%s", search_niche, niche_name, niche_id)

    # ── Step 2: pool ─────────────────────────────────────────────────────────
    pool = await _niche_aweme_pool(search_niche, period=30)
    logger.info("[creator_search] pool size=%d", len(pool))

    # ── Step 3: aggregate + pick top 3 ───────────────────────────────────────
    handle_stats: dict[str, dict[str, Any]] = {}
    for aweme in pool:
        author = aweme.get("author") or {}
        handle = str(author.get("unique_id") or author.get("uniqueId") or "").strip()
        if not handle:
            continue
        stats = aweme.get("statistics") or {}
        views = int(stats.get("play_count") or 0)
        engagements = (
            int(stats.get("digg_count") or 0)
            + int(stats.get("comment_count") or 0)
            + int(stats.get("share_count") or 0)
        )
        s = handle_stats.setdefault(handle, {"total_views": 0, "total_engage": 0, "video_count": 0})
        s["total_views"] += views
        s["total_engage"] += engagements
        s["video_count"] += 1

    MIN_VIDEOS = 2
    candidates = [
        (h, s) for h, s in handle_stats.items()
        if s["video_count"] >= MIN_VIDEOS and s["total_views"] > 0
    ]
    candidates.sort(key=lambda x: x[1]["total_views"], reverse=True)
    top_handles = candidates[:3]

    # ── Step 4: enrich each in parallel ──────────────────────────────────────
    question_text = " | ".join(questions)
    # Persona-empty check gates the product-context follow-up.
    from getviews_pipeline.persona import extract_persona_slots
    persona = extract_persona_slots(question_text)

    cards = []
    if top_handles:
        cards = await asyncio.gather(
            *[
                _enrich_creator_card(
                    handle, stats, niche_id, search_niche, persona.is_empty(), question_text,
                )
                for handle, stats in top_handles
            ]
        )

    # ── Step 5: synthesis text + follow-ups ──────────────────────────────────
    if not cards:
        synthesis = (
            f"Mình chưa tìm được creator phù hợp với **{search_niche}**.\n\n"
            "Thử mô tả cụ thể hơn — ví dụ: 'creator làm đẹp ở Hà Nội', "
            "'KOC skincare dưới 50K followers'."
        )
    else:
        synthesis = (
            f"Mình tìm được **{len(cards)} creator** đang hoạt động tốt cho "
            f"**{search_niche}**. Các card dưới đây kèm theo lý do fit cụ thể, "
            "điểm mạnh và cách liên hệ."
        )

    follow_ups = _build_follow_ups(
        "creator_search",
        niche_name,
        handle=(cards[0]["handle"].lstrip("@") if cards else None),
    )
    # Inject the conversational product-context chip when we'd learn something new.
    if cards and needs_product_context(question_text, persona.is_empty()):
        follow_ups.insert(
            0,
            "Sản phẩm + giá + đối thủ của bạn là gì? Mình sẽ lọc lại cho đúng hơn.",
        )
        follow_ups = follow_ups[:3]

    session.setdefault("completed_intents", []).append("creator_search")
    _bump_analyses_summary(
        session, niche=search_niche, delta_videos=0, intent_label="creator_search",
    )

    return {
        "intent": "creator_search",
        "niche": search_niche,
        "synthesis": synthesis,
        "creators": cards,
        "coverage": _coverage_dict(
            niche_id, niche_name, count, len(cards),
            "live_aggregate" if cards else "live_search", 30,
        ),
        "follow_ups": follow_ups,
    }


async def run_own_channel(
    niche: str,
    session: dict[str, Any],
    questions: list[str],
) -> dict[str, Any]:
    """Soi kênh — prefer curated corpus for niche-accurate references; fall back to
    live search only when the corpus is too sparse. Mirrors run_content_directions
    so the same transparency/citation/persona guarantees apply."""
    sem = get_analysis_semaphore()
    fa: dict[str, Any] = session.setdefault("full_analyses", {})
    cached_ids = set(fa.keys())

    corpus_pool = await fetch_corpus_reference_pool(niche, days=30, limit=20)
    corpus_source = "corpus"
    if len(corpus_pool) >= REF_N:
        corpus_pool.sort(key=lambda v: float(v.get("_corpus_er") or 0.0), reverse=True)
        picks = [v for v in corpus_pool if v.get("aweme_id") not in cached_ids][:REF_N]
        pool = corpus_pool
    else:
        corpus_source = "live_search" if len(corpus_pool) == 0 else "sparse_fallback"
        logger.info(
            "[own_channel] corpus too small (%d) for niche '%s', live search (source=%s)",
            len(corpus_pool), niche, corpus_source,
        )
        pool = await _niche_aweme_pool(niche, period=30)
        picks = select_reference_videos(
            pool, recency_days=30, n=REF_N, cached_ids=cached_ids, rank_by="er"
        )

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

    tasks = [_one(a) for a in picks]
    results = await asyncio.gather(*tasks)
    for r in results:
        if "analysis" in r:
            analyzed.append(r)

    niche_id = await resolve_niche_id_cached(session, niche)
    count, niche_name = await get_corpus_count_cached(
        session, niche_id=niche_id, days=30, niche_name=niche
    )
    citation = build_corpus_citation_block(
        count, niche_name, days=30,
        reference_count=len(analyzed),
        source=corpus_source,
    )
    persona = extract_persona_slots(" ".join(questions))
    persona_block = build_persona_block(persona)
    logger.info(
        "[own_channel] niche_input=%r resolved=%r niche_id=%s corpus_count=%d source=%s",
        niche, niche_name, niche_id, count, corpus_source,
    )

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
        niche_key=niche,
        corpus_citation=citation,
        persona_block=persona_block,
    )
    synthesis = _inject_video_ref_blocks(synthesis, analyzed)
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
        "coverage": _coverage_dict(niche_id, niche_name, count, len(analyzed), corpus_source, 30),
        "follow_ups": _build_follow_ups("own_channel", niche_name, analyzed),
    }
