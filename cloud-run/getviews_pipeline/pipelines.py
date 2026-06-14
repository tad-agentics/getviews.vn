"""Intent pipelines: Ensemble search + parallel Gemini analysis + synthesis."""

from __future__ import annotations

import asyncio
import json as _json
import logging
import re
import statistics as stats_module
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import analyze_aweme
from getviews_pipeline.corpus_context import (
    build_corpus_citation_block,
    content_class_id_for_reference_pool,
    enrich_niche_meta_with_sound_radar,
    fetch_corpus_reference_pool,
    fetch_creator_format_history,
    format_creator_format_history_for_diagnosis,
    get_corpus_count_cached,
    get_niche_intelligence,
    lookup_trending_sound_profile_for_diagnosis,
    resolve_niche_id_cached,
)
from getviews_pipeline.corpus_ingest import classify_format
from getviews_pipeline.corpus_windows import (
    corpus_benchmark_window_days,
    corpus_citation_window_days,
    corpus_reference_fetch_days,
    corpus_reference_pick_days,
)
from getviews_pipeline.diagnosis_synthesis_contract import diagnosis_synthesis_kwargs
from getviews_pipeline.enum_labels_vi import carousel_subformat_vi
from getviews_pipeline.extraction_quality import peer_recency_tiebreak, peer_row_days_ago
from getviews_pipeline.gemini import (
    synthesize_diagnosis_carousel_v2,
    synthesize_diagnosis_v2,
)
from getviews_pipeline.hashtag_niche_map import (
    classify_from_hashtags,
)
from getviews_pipeline.helpers import (
    _author_key,
    _aweme_id,
    _engagement_rate,
    filter_recency,
    infer_niche_from_hashtags,
    merge_aweme_lists,
)
from getviews_pipeline.intents import QueryIntent
from getviews_pipeline.output_redesign import FORMAT_ANALYSIS_WEIGHTS, hook_type_vi
from getviews_pipeline.persona import build_persona_block, extract_persona_slots
from getviews_pipeline.runtime import get_analysis_semaphore, run_sync
from getviews_pipeline.services.extraction import (
    apply_rule_based_video_errors,
    extract_video_errors,
)
from getviews_pipeline.settings import settings as pipeline_settings
from getviews_pipeline.step_events import (
    emit,
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
from getviews_pipeline.video_niche_benchmark import fetch_class_hook_effectiveness_sync

logger = logging.getLogger(__name__)

REF_N = 5

# Canonical video_corpus.content_format slugs (no carousel* keys).
_VIDEO_CORPUS_FORMAT_SLUGS: frozenset[str] = frozenset(
    k for k in FORMAT_ANALYSIS_WEIGHTS if not str(k).startswith("carousel")
)

# First regex match wins when Gemini omits ``content_format``.
_FORMAT_SLUG_INFERENCE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"mukbang|asmr.*ăn|ăn cùng"), "mukbang"),
    (re.compile(r"\bgrwm\b|get ready|makeup routine|morning routine"), "grwm"),
    (
        re.compile(
            r"gameplay|gaming|liên quân|valorant|minecraft|genshin|roblox|pubg|\blol\b"
        ),
        "gameplay",
    ),
    (re.compile(r"\brecipe\b|công thức|\bnấu\b|nguyên liệu|ướp\b|\bchiên\b"), "recipe"),
    (re.compile(r"\bhaul\b|unbox|đập hộp|mở hộp"), "haul"),
    (re.compile(r"\breview\b|đánh giá|chấm điểm|trải nghiệm sản phẩm"), "review"),
    (re.compile(r"so sánh|versus|\bvs\.?\b|đối đầu"), "comparison"),
    (re.compile(r"\btutorial\b|hướng dẫn|\btips\b|mẹo hay"), "tutorial"),
    (re.compile(r"\blesson\b|bài học|từ vựng|ngữ pháp|học tiếng"), "lesson"),
    (re.compile(r"comedy skit|\bskit\b|tiểu phẩm|hài kịch|\bprank\b"), "comedy_skit"),
    (
        re.compile(r"storytelling|kể chuyện|câu chuyện|chia sẻ câu chuyện"),
        "storytelling",
    ),
    (re.compile(r"before.?after|trước và sau|trước/sau|glow.?up|biến đổi"), "before_after"),
    (re.compile(r"(^|\s)pov[: ]|\bpov\b"), "pov"),
    (
        re.compile(r"\boutfit\b|ootd|phối đồ|mix đồ|\btransition\b"),
        "outfit_transition",
    ),
    (re.compile(r"\bvlog\b|một ngày|daily vlog|thường ngày"), "vlog"),
    (re.compile(r"\bdance\b|nhảy|choreo"), "dance"),
    (
        re.compile(
            r"faceless|\bb-?roll\b|trình diễn sản phẩm|lifestyle b-?roll|không lộ mặt"
        ),
        "faceless",
    ),
    (re.compile(r"\bhighlight\b|montage|khoảnh khắc"), "highlight"),
]


def _normalize_card_content_format_slug(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    s = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    if s in _VIDEO_CORPUS_FORMAT_SLUGS:
        return s
    return None


def _infer_format_slug_from_card_text(combined: str) -> str | None:
    if not combined or not str(combined).strip():
        return None
    text = str(combined).lower()
    for pat, slug in _FORMAT_SLUG_INFERENCE:
        if pat.search(text):
            return slug
    return None


def _format_card_corpus_slug(
    card: dict[str, Any],
    *,
    analyzed_content_format: str | None,
    multi_card: bool,
) -> str | None:
    slug = _normalize_card_content_format_slug(
        card.get("content_format") or card.get("format_content_key")
    )
    if slug:
        return slug
    name = str(card.get("format_name_vi") or "")
    mech = str(card.get("mechanism_vi") or "")
    slug = _infer_format_slug_from_card_text(f"{name} {mech}")
    if slug:
        return slug
    if not multi_card and analyzed_content_format:
        return _normalize_card_content_format_slug(analyzed_content_format)
    return None


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
    # Inline playback (2026-06-11): only ship the URL when it's an R2-hosted
    # clip from corpus ingest — never an expiring platform play URL. The FE
    # plays these in the existing VideoPlayerModal instead of bouncing the
    # creator out to TikTok.
    raw_video_url = str(r.get("_corpus_video_url") or r.get("video_url") or "")
    playback_url = (
        raw_video_url
        if "/videos/" in raw_video_url and "tiktokcdn" not in raw_video_url
        else None
    )
    prox = r.get("_proximity_score")
    out: dict[str, Any] = {
        "aweme_id": aweme_id,
        "desc": ((r.get("desc") or "")[:120]) or None,
        "hook_type": hook_type,
        "content_format": content_format_val,
        "views": int(views_raw) if views_raw is not None else None,
        "engagement_rate": float(engagement_rate) if engagement_rate is not None else None,
        "author_handle": author_handle,
        "thumbnail_url": thumb,
        "tiktok_url": tiktok_url,
        "playback_url": playback_url,
        "source": source,
    }
    if prox is not None:
        out["content_proximity_score"] = int(prox)
    if _peer_hook_timestamps_enabled():
        analysis = r.get("analysis") if isinstance(r.get("analysis"), dict) else {}
        shot_ref = r.get("_shot_reference") if isinstance(r.get("_shot_reference"), dict) else None
        start_s, _end_s = _peer_hook_window_s(analysis, shot_ref=shot_ref)
        if start_s is not None:
            out["peer_hook_start_sec"] = start_s
    return out


def compute_bright_spot_signal(
    er_percentile_rank: float | None,
    views_vs_avg_ratio: float | None,
    *,
    retention_end_pct: float | None = None,
    channel_views_ratio: float | None = None,
) -> dict[str, Any] | None:
    """Bright spot / contradiction framing.

    ``er_percentile_rank`` is an ER proxy (50 = format average), not TikTok retention.
    ``retention_end_pct`` is the modeled/numeric retention-at-end when available.
    """
    low_views_corpus = views_vs_avg_ratio is not None and views_vs_avg_ratio < 1.0
    low_views_channel = channel_views_ratio is not None and channel_views_ratio < 0.5
    low_distribution = low_views_corpus or low_views_channel

    strong_retention = retention_end_pct is not None and retention_end_pct >= 68.0
    strong_er = er_percentile_rank is not None and er_percentile_rank >= 70.0

    if low_distribution and (strong_retention or strong_er):
        clauses: list[str] = []
        if strong_retention and retention_end_pct is not None:
            clauses.append(
                f"Đường cong giữ chân cuối ~{retention_end_pct:.0f}% — bạn đang giữ người xem "
                "tốt hơn đa số clip cùng format."
            )
        if strong_er:
            clauses.append(
                "Engagement rate (tương tác/view) cũng nghiêng về nhóm trên trung bình format."
            )
        if low_views_corpus and views_vs_avg_ratio is not None:
            clauses.append(
                f"Lượt xem chỉ ~{views_vs_avg_ratio:.2f}× TB format — phần gap chính nằm ở hook "
                "và lượt vào đầu, không phải ở chỗ “giữ chân”."
            )
        elif low_views_channel and channel_views_ratio is not None:
            clauses.append(
                f"So với trung vị kênh, clip ~{channel_views_ratio:.2f}× — đa phần là bài toán "
                "phân phối / hook, không phải “video dở” theo nghĩa giữ người xem."
            )
        tail = (
            " Các ý “lỗi cấu trúc” bên dưới là **đòn bẩy để mở thêm view**, "
            "không phủ nhận tín hiệu giữ chân đang mạnh."
        )
        return {
            "signal_type": "hook_only_problem",
            "message_vi": (" ".join(clauses).strip() + tail).strip(),
        }

    if er_percentile_rank is None or views_vs_avg_ratio is None:
        return None

    high_er = er_percentile_rank >= 70
    high_views = views_vs_avg_ratio >= 1.0

    if high_er and not high_views:
        return {
            "signal_type": "hook_only_problem",
            "message_vi": (
                "Engagement rate cao hơn trung bình format — nội dung tạo được tương tác tốt. "
                "Vấn đề là lượt xem vẫn thấp, nghĩa là hook chưa đủ mạnh để kéo đủ người vào xem."
            ),
        }
    if high_er and high_views:
        return {
            "signal_type": "performing_well",
            "message_vi": (
                "Video đang hoạt động tốt — cả engagement rate lẫn lượt xem đều vượt mức trung bình format."
            ),
        }
    if not high_er and not high_views:
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


def compute_view_scenarios(
    *,
    performance_tier: str,
    views_vs_avg_ratio: float | None,
    channel_views_ratio: float | None,
) -> list[dict[str, str]] | None:
    """Qualitative ROI ladder for flop diagnoses — ranges only, no fabricated view counts."""
    if performance_tier != "flop":
        return None
    if views_vs_avg_ratio is None and channel_views_ratio is None:
        return None
    return [
        {
            "focus_vi": "Ưu tiên hook + CTA rõ trong ~3s đầu",
            "outcome_vi": (
                "Thực tế hay gặp: ~1,5–2,5× lượt xem so với clip hiện tại khi format vẫn hợp ngách."
            ),
        },
        {
            "focus_vi": "Hook + khung hình đầu clip (cắt, sản phẩm, text)",
            "outcome_vi": (
                "Biên độ thường ~3–5× khi bám benchmark format đang chạy trên kho."
            ),
        },
        {
            "focus_vi": "Viết lại cấu trúc theo benchmark kênh / format",
            "outcome_vi": (
                "Mục tiêu thực tế: tiến gần TB lượt xem kênh và TB format — không có shortcut đảm bảo viral."
            ),
        },
    ]


# Below this age, a low view count is not yet a verdict — views only
# accumulate, so "flop"/"average" on a fresh video would judge an
# unfinished outcome (a high ratio IS conclusive early, views never drop).
_TIER_MIN_AGE_DAYS = 3.0


def classify_performance_tier_corpus(
    views: int,
    format_avg: float | None,
    *,
    video_age_days: float | None = None,
) -> str:
    if not format_avg or format_avg == 0:
        return "unknown"
    ratio = views / format_avg
    if ratio >= 2.0:
        return "hit"
    if video_age_days is not None and video_age_days < _TIER_MIN_AGE_DAYS:
        return "early"
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
    if corpus_tier == "early":
        # Inconclusive by age — only a conclusive channel-relative breakout
        # upgrades it; a low account ratio is just as unfinished.
        return "hit" if account_ratio >= 2.0 else "early"
    account_tier = (
        "hit" if account_ratio >= 2.0 else "flop" if account_ratio < 0.5 else "average"
    )
    if corpus_tier == account_tier:
        return corpus_tier
    if {corpus_tier, account_tier} == {"hit", "flop"}:
        return "average"
    return account_tier


def _dominant_creator_persona_from_corpus(
    client: Any, handle: str, exclude_video_id: str
) -> str | None:
    """Mode of ``creator_persona`` from recent corpus rows; needs ≥2 agreeing rows."""
    try:
        res = (
            client.table("video_corpus")
            .select("analysis_json")
            .eq("creator_handle", handle)
            .neq("video_id", exclude_video_id)
            .limit(24)
            .execute()
        )
    except Exception:
        return None
    counts: Counter[str] = Counter()
    for row in res.data or []:
        aj = row.get("analysis_json")
        if not isinstance(aj, dict):
            continue
        cp = str(aj.get("creator_persona") or "").strip().lower().replace("-", "_")
        if cp and cp not in ("null", "none", "other", ""):
            counts[cp] += 1
    if not counts:
        return None
    top, n = counts.most_common(1)[0]
    if n < 2:
        return None
    return top


def _fetch_channel_context_from_live_posts(
    handle: str,
    current_video_id: str,
) -> dict[str, Any]:
    """Synchronous EnsembleData fallback for channel context when corpus < 2 videos.

    Called only when the corpus query returns 0–1 other videos (common for creators
    analyzed on-demand for the first time). Uses httpx.Client so it is safe to call
    from a thread-pool executor. Posts are not persisted to corpus here — that happens
    separately via promote_on_demand_to_corpus.
    """
    import httpx

    from getviews_pipeline.config import ENSEMBLEDATA_USER_POSTS_URL, require_ensembledata_token

    try:
        token = require_ensembledata_token()
    except ValueError:
        return {"available": False, "reason": "ED token missing — no live fallback"}

    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.get(
                ENSEMBLEDATA_USER_POSTS_URL,
                params={
                    "username": handle,
                    "depth": 1,
                    "start_cursor": 0,
                    "new_version": "False",
                    "download_video": "False",
                    "token": token,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.debug("[channel_context] ED live fallback failed handle=%r: %s", handle, exc)
        return {"available": False, "reason": f"ED live fallback failed: {str(exc)[:60]}"}

    data = payload.get("data") or {}
    awemes: list[dict[str, Any]] = []
    if isinstance(data, dict):
        awemes = data.get("aweme_list") or []
    elif isinstance(data, list):
        awemes = data

    # Filter out the current video and build minimal channel-context rows
    rows: list[dict[str, Any]] = []
    for aw in awemes:
        aid = str(aw.get("aweme_id") or aw.get("id") or "")
        if aid == current_video_id:
            continue
        views = int(aw.get("statistics", {}).get("play_count") or aw.get("views") or 0)
        desc = str(aw.get("desc") or aw.get("caption") or "")
        rows.append({"video_id": aid, "caption": desc, "views": views, "content_format": None})

    if len(rows) < 2:
        return {
            "available": False,
            "reason": f"ED returned {len(rows)} usable posts — chưa đủ để so sánh",
        }

    view_counts = [r["views"] for r in rows]
    median_views = float(stats_module.median(view_counts)) if view_counts else 0.0
    sorted_rows = sorted(rows, key=lambda r: r["views"], reverse=True)
    top_videos = sorted_rows[:2]
    bottom_videos = sorted_rows[-2:]

    return {
        "available": True,
        "source": "live",  # distinguish from corpus-backed context
        "top_videos": [
            {
                "aweme_id": v["video_id"],
                "desc": v["caption"],
                "views": v["views"],
                "content_format": None,
                "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{v['video_id']}",
            }
            for v in top_videos
        ],
        "bottom_videos": [
            {
                "aweme_id": v["video_id"],
                "desc": v["caption"],
                "views": v["views"],
                "content_format": None,
                "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{v['video_id']}",
            }
            for v in bottom_videos
        ],
        "best_performing_format": None,
        "sample_size": len(rows),
        "median_views": median_views,
        "per_format_views": None,
    }


def fetch_channel_context_sync(creator_handle: str, current_video_id: str) -> dict[str, Any]:
    handle = creator_handle.lstrip("@").strip()
    vid = str(current_video_id or "").strip()
    if not handle or not vid:
        return {"available": False, "reason": "Thiếu handle hoặc video id để tra kênh"}

    try:
        client = get_service_client()
        res = (
            client.table("video_corpus")
            .select("video_id, caption, views, content_format, posted_at, indexed_at, analysis_json")
            .eq("creator_handle", handle)
            .neq("video_id", vid)
            .order("posted_at", desc=True)
            .limit(10)
            .execute()
        )
        videos = list(res.data or [])
        if len(videos) < 2:
            logger.debug(
                "[channel_context] corpus sparse (n=%d) for handle=%r — trying ED live fallback",
                len(videos),
                handle,
            )
            return _fetch_channel_context_from_live_posts(handle, vid)

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

        # Phase 4.1 — per_format_views: group by content_format, compute avg + median views.
        # Drives channel_proof block. Returns dict keyed by format; null if <2 formats with n>=3.
        format_groups: dict[str, list[int]] = {}
        for v in videos:
            fmt = str(v.get("content_format") or "").strip()
            if fmt:
                format_groups.setdefault(fmt, []).append(int(v.get("views") or 0))

        per_format_views: dict[str, Any] | None = None
        qualifying = {
            fmt: vws for fmt, vws in format_groups.items() if len(vws) >= 3
        }
        if len(qualifying) >= 2:
            per_format_views = {}
            for fmt, vws in qualifying.items():
                sorted_vws = sorted(vws)
                n = len(sorted_vws)
                per_format_views[fmt] = {
                    "n": n,
                    "avg_views": int(sum(sorted_vws) / n),
                    "median_views": int(sorted_vws[n // 2]),
                    "min_views": sorted_vws[0],
                    "max_views": sorted_vws[-1],
                }

        out_ctx: dict[str, Any] = {
            "available": True,
            "top_videos": [
                {
                    "aweme_id": v.get("video_id"),
                    "desc": v.get("caption"),
                    "views": int(v.get("views") or 0),
                    "content_format": v.get("content_format"),
                    "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{v.get('video_id')}",
                }
                for v in top_videos
            ],
            "bottom_videos": [
                {
                    "aweme_id": v.get("video_id"),
                    "desc": v.get("caption"),
                    "views": int(v.get("views") or 0),
                    "content_format": v.get("content_format"),
                    "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{v.get('video_id')}",
                }
                for v in bottom_videos
            ],
            "best_performing_format": best_fmt,
            "sample_size": len(videos),
            "median_views": median_views,
            "per_format_views": per_format_views,
        }
        dom_p = _dominant_creator_persona_from_corpus(client, handle, vid)
        if dom_p:
            out_ctx["dominant_creator_persona"] = dom_p
        # P3 follow-up (2026-06-11) — per-feature audit over the same rows
        # (face/hook/overlay/audio-role counts) so the video report can say
        # "this video has no face — and neither do your last N". Zero extra
        # queries; absent when too few rows carry analysis_json.
        from getviews_pipeline.channel_diagnose import compute_recent_content_audit

        audit = compute_recent_content_audit(videos, recent_total=len(videos))
        if audit:
            out_ctx["recent_content_audit"] = audit
        return out_ctx
    except Exception as exc:
        msg = str(exc)[:80]
        return {"available": False, "reason": f"Lỗi truy vấn kênh: {msg}"}


async def _run_channel_context(creator_handle: str, current_video_id: str) -> dict[str, Any]:
    # Phase 5.5 — use cached wrapper (24h TTL) so repeat creator handles
    # within the same instance don't re-query Supabase.
    from getviews_pipeline.services.channel import (
        fetch_channel_context_sync as _cached_fetch,
    )
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _cached_fetch,
        creator_handle,
        current_video_id,
    )


def _format_avg_views_for_diagnosis(niche_id: int, content_format: str) -> float | None:
    """Median views for same niche × content_format — MV first, then 30d corpus, then all-time."""
    fmt = str(content_format or "").strip()
    if not niche_id or not fmt:
        return None
    try:
        from getviews_pipeline.corpus_ingest import _content_class_for
        from getviews_pipeline.video_niche_benchmark import fetch_content_class_intelligence_sync

        cc = _content_class_for(niche_id, fmt)
        if cc:
            mv_row = fetch_content_class_intelligence_sync(get_service_client(), cc)
            if mv_row:
                mv_med = mv_row.get("median_views")
                mv_avg = mv_row.get("avg_views")
                v_mv = mv_med if mv_med is not None else mv_avg
                if v_mv is not None and float(v_mv) > 0:
                    return float(v_mv)
        since_dt = datetime.now(UTC) - timedelta(days=corpus_benchmark_window_days())
        since_iso = since_dt.isoformat()
        client = get_service_client()

        def _median_from_corpus(*, since: str | None) -> float | None:
            q = (
                client.table("video_corpus")
                .select("views")
                .eq("ingest_loop_niche_id", niche_id)
                .eq("content_format", fmt)
                .limit(200)
            )
            if since:
                q = q.gte("indexed_at", since)
            res = q.execute()
            vals = sorted(int(r.get("views") or 0) for r in (res.data or []))
            if len(vals) < 5:
                return None
            return float(vals[len(vals) // 2])

        med = _median_from_corpus(since=since_iso)
        if med is not None:
            return med
        # Thin 30d window but corpus has older rows — broadens FORMAT-AVG-0b fallback.
        return _median_from_corpus(since=None)
    except Exception as exc:
        logger.warning("[video_diagnosis] format_avg lookup failed: %s", exc)
        return None


def _fmt_int_vi(n: int) -> str:
    """Integer with dot thousands separator (matches FE vi-VN style)."""
    return f"{int(n):,}".replace(",", ".")


def fetch_format_corpus_enrichment_sync(
    content_format: str,
    niche_id: int,
    *,
    example_limit: int = 3,
) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    """Corpus view-range + median ER for a format×niche; top videos as linkable examples."""
    if not content_format or not niche_id:
        return None, None, []
    try:
        since_dt = datetime.now(UTC) - timedelta(days=corpus_benchmark_window_days())
        since_iso = since_dt.isoformat()
        client = get_service_client()
        res = (
            client.table("video_corpus")
            .select("video_id, caption, views, creator_handle, likes, comments, shares")
            .eq("ingest_loop_niche_id", niche_id)
            .eq("content_format", content_format)
            .gte("indexed_at", since_iso)
            .limit(200)
            .execute()
        )
        rows = [r for r in (res.data or []) if r.get("video_id")]
    except Exception as exc:
        logger.warning("[format_enrich] corpus query failed: %s", exc)
        return None, None, []

    view_r: str | None = None
    er_r: str | None = None
    if len(rows) >= 5:
        views_sorted = sorted(
            int(r.get("views") or 0) for r in rows if int(r.get("views") or 0) > 0
        )
        if len(views_sorted) >= 5:
            n = len(views_sorted)
            p25 = views_sorted[max(0, (n * 25) // 100)]
            p75 = views_sorted[min(n - 1, (n * 75) // 100)]
            view_r = f"{_fmt_int_vi(p25)} – {_fmt_int_vi(p75)}"
            er_vals: list[float] = []
            for r in rows:
                v = int(r.get("views") or 0)
                if v <= 0:
                    continue
                eng = (
                    int(r.get("likes") or 0)
                    + int(r.get("comments") or 0)
                    + int(r.get("shares") or 0)
                )
                er_vals.append(eng / float(v))
            if er_vals:
                med_er = float(stats_module.median(er_vals))
                er_r = f"{med_er * 100:.2f}%".replace(".", ",")

    by_v = sorted(rows, key=lambda r: int(r.get("views") or 0), reverse=True)
    examples: list[dict[str, Any]] = []
    for r in by_v[:example_limit]:
        aid = str(r.get("video_id") or "")
        handle = str(r.get("creator_handle") or "").lstrip("@").strip()
        if not aid or not handle:
            continue
        examples.append(
            {
                "aweme_id": aid,
                "desc": (str(r.get("caption") or "").strip())[:80],
                "play_count": int(r.get("views") or 0),
                "creator_handle": handle,
                "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{aid}",
            }
        )
    if len(examples) < 1:
        examples = []
    return view_r, er_r, examples


def enrich_format_cards_from_corpus(
    format_cards: list[dict[str, Any]] | None,
    niche_id: int,
    *,
    analyzed_content_format: str | None = None,
) -> list[dict[str, Any]] | None:
    """Merge per-card corpus stats/examples using each card's ``content_format`` slug.

    Slug resolution: optional model ``content_format`` field, then Vietnamese
    inference from ``format_name_vi`` + ``mechanism_vi``, then (single-card only)
    the analyzed video's ``analyzed_content_format``.
    """
    if not format_cards or not niche_id:
        return format_cards
    dict_rows = [c for c in format_cards if isinstance(c, dict)]
    multi = len(dict_rows) > 1
    cache: dict[str, tuple[str | None, str | None, list[dict[str, Any]]]] = {}
    out: list[dict[str, Any]] = []
    for c in format_cards:
        if not isinstance(c, dict):
            continue
        cc = dict(c)
        slug = _format_card_corpus_slug(
            cc,
            analyzed_content_format=analyzed_content_format,
            multi_card=multi,
        )
        if not slug:
            out.append(cc)
            continue
        if slug not in cache:
            cache[slug] = fetch_format_corpus_enrichment_sync(slug, niche_id)
        view_r, er_r, examples = cache[slug]
        if view_r:
            cc["view_range"] = view_r
        else:
            cc["view_range"] = "Chưa chốt được dải view cho ngách này."
        if er_r:
            cc["engagement_rate"] = er_r
        else:
            cc["engagement_rate"] = "—"
        if examples:
            cc["format_examples"] = examples
        else:
            cc.pop("format_examples", None)
        out.append(cc)
    return out


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


def _augment_user_stats_for_sound_diagnosis(
    user_stats: dict[str, Any],
    user_metadata_dict: dict[str, Any],
    user_analysis_dict: dict[str, Any],
    niche_id: int,
) -> None:
    """§6 sound signals — attach music ids + optional trending_sounds profile (read-only)."""
    music = user_metadata_dict.get("music") or {}
    mid = music.get("music_id")
    if mid is None:
        mid = music.get("id")
    if mid is not None:
        s = str(mid).strip()
        user_stats["sound_id"] = s or None
    else:
        user_stats["sound_id"] = None
    user_stats["music_title"] = music.get("title")
    user_stats["music_is_original"] = music.get("is_original")
    promo = str(user_analysis_dict.get("promotion_type") or "organic").lower()
    ci = user_analysis_dict.get("commerce_intent") or {}
    if not isinstance(ci, dict):
        ci = {}
    obj = str(ci.get("conversion_objective") or "").lower()
    user_stats["account_commercial_heuristic"] = promo not in (
        "organic",
        "",
    ) or obj not in ("", "entertainment_first")
    user_stats["trending_sound_profile"] = None
    sid = user_stats.get("sound_id")
    if niche_id > 0 and sid:
        user_stats["trending_sound_profile"] = lookup_trending_sound_profile_for_diagnosis(
            niche_id,
            str(sid),
        )


def _content_proximity_score(
    ref: dict[str, Any],
    video_desc: str,
    video_hashtags: list[str],
    *,
    user_subject_matter: str | None = None,
) -> int:
    """Keyword/hashtag overlap between reference text and the user video."""
    ref_meta = ref.get("metadata") if isinstance(ref.get("metadata"), dict) else {}
    analysis = ref.get("analysis") if isinstance(ref.get("analysis"), dict) else {}
    ref_text = (
        str(ref.get("desc") or "")
        or str(ref_meta.get("description") or "")
        or str(analysis.get("audio_transcript") or "")[:200]
    ).lower()
    ref_cc = analysis.get("content_context")
    ref_subject_matter = ""
    if isinstance(ref_cc, dict):
        sm = str(ref_cc.get("subject_matter") or "").strip().lower()
        if sm:
            ref_subject_matter = sm
            ref_text = f"{ref_text} {sm}".strip()
        topics = ref_cc.get("topics")
        if isinstance(topics, list):
            ref_text = f"{ref_text} {' '.join(str(t) for t in topics if t)}".strip()
    score = 0
    user_sm = str(user_subject_matter or "").strip().lower()
    if user_sm:
        if user_sm in ref_text or (ref_subject_matter and ref_subject_matter in user_sm):
            score += 5
        for w in [w for w in user_sm.split() if len(w) > 3][:8]:
            if w in ref_text:
                score += 1
    for tag in video_hashtags:
        t = str(tag or "").lower().lstrip("#")
        if len(t) > 1 and t in ref_text:
            score += 2
    words = [w for w in str(video_desc or "").lower().split() if len(w) > 3]
    for w in words[:10]:
        if w in ref_text:
            score += 1
    return score


def _ref_rank_er(ref: dict[str, Any]) -> float:
    if ref.get("_from_corpus"):
        return float(ref.get("_corpus_er") or 0.0)
    return _engagement_rate(ref)


def _ref_has_visible_thumbnail(v: dict[str, Any]) -> bool:
    """True when the candidate can render a reference tile the creator can SEE.

    Reference-first product rule (2026-06-11): within the same proximity
    tier, a reference with a working thumbnail beats a marginally
    higher-ER one with none — a gray tile teaches nothing. Corpus rows
    carry ``thumbnail_url`` (NULL for the unhealed legacy cohort); live
    ED awemes always have a fresh cover under ``video.cover``/
    ``video.origin_cover``.
    """
    if v.get("thumbnail_url"):
        return True
    video = v.get("video") if isinstance(v.get("video"), dict) else {}
    for key in ("origin_cover", "cover"):
        cov = video.get(key)
        if isinstance(cov, dict) and (cov.get("url_list") or []):
            return True
    return False


def _select_by_proximity_then_er(
    search_results: list[dict[str, Any]],
    *,
    video_desc: str,
    video_hashtags: list[str],
    cached_ids: set[str],
    n: int,
    recency_days: int | None = None,
    user_subject_matter: str | None = None,
) -> list[dict[str, Any]]:
    """Like select_reference_videos but primary sort is content proximity."""
    if recency_days is None:
        recency_days = corpus_reference_pick_days()
    t = time.time()
    cutoff = t - (recency_days * 86400)
    skip = cached_ids
    candidates = [
        v
        for v in search_results
        if _aweme_id(v) and _aweme_id(v) not in skip
    ]
    candidates = [
        v
        for v in candidates
        if int(v.get("create_time") or 0) >= int(cutoff)
    ]
    candidates.sort(
        key=lambda v: (
            _content_proximity_score(
                v,
                video_desc,
                video_hashtags,
                user_subject_matter=user_subject_matter,
            ),
            # Visible tile beats invisible at equal proximity (2026-06-11).
            1 if _ref_has_visible_thumbnail(v) else 0,
            _ref_rank_er(v),
            peer_recency_tiebreak(peer_row_days_ago(v)),
        ),
        reverse=True,
    )
    seen_authors: set[str] = set()
    selected: list[dict[str, Any]] = []
    for v in candidates:
        ak = _author_key(v) or _aweme_id(v)
        if ak in seen_authors:
            continue
        seen_authors.add(ak)
        selected.append(v)
        if len(selected) >= n:
            break
    return selected


async def _maybe_merge_content_targeted_refs_async(
    pool: list[dict[str, Any]],
    picks: list[dict[str, Any]],
    *,
    video_desc: str,
    video_hashtags: list[str],
    niche: str,
    cached_ids: set[str],
    n: int,
    recency_days: int | None = None,
    user_subject_matter: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """If all top picks have zero proximity, supplement pool from ED (user-video keywords)."""
    if recency_days is None:
        recency_days = corpus_reference_pick_days()
    if not picks or not (video_desc.strip() or video_hashtags):
        return pool, picks
    topn = picks[: min(3, len(picks))]
    scores = [
        _content_proximity_score(
            p,
            video_desc,
            video_hashtags,
            user_subject_matter=user_subject_matter,
        )
        for p in topn
    ]
    if any(s > 0 for s in scores):
        return pool, picks
    from getviews_pipeline.live_search import fetch_content_targeted_refs

    extra = await fetch_content_targeted_refs(video_desc, video_hashtags, niche, n=8)
    if not extra:
        return pool, picks
    seen = {str(p.get("aweme_id")) for p in pool}
    for a in extra:
        aid = str(a.get("aweme_id") or "")
        if aid and aid not in seen and aid not in cached_ids:
            a.setdefault("niche_label", niche)
            pool.append(a)
            seen.add(aid)
    new_picks = _select_by_proximity_then_er(
        pool,
        video_desc=video_desc,
        video_hashtags=video_hashtags,
        cached_ids=cached_ids,
        n=n,
        recency_days=recency_days,
        user_subject_matter=user_subject_matter,
    )
    return pool, new_picks


def _get_ref_thumbnail_urls_from_aweme(ref: dict[str, Any]) -> list[str]:
    video = ref.get("video") if isinstance(ref.get("video"), dict) else {}
    cover = video.get("cover") if isinstance(video.get("cover"), dict) else {}
    urls = [u for u in (cover.get("url_list") or []) if isinstance(u, str) and u.strip()]
    if urls:
        return urls
    u = ref.get("thumbnail_url")
    return [str(u).strip()] if u else []


async def _mirror_queue_thumbnails_for_rows(
    *,
    client: Any,
    rows_payload: list[tuple[str, dict[str, Any]]],
) -> None:
    """Best-effort R2 mirror for queued reference thumbnails (CDN URLs expire)."""
    from getviews_pipeline.r2 import download_and_upload_thumbnail

    for aid, raw_ref in rows_payload:
        if not aid:
            continue
        r2_url: str | None = None
        for thumb_url in _get_ref_thumbnail_urls_from_aweme(raw_ref)[:3]:
            r2_url = await download_and_upload_thumbnail(thumb_url, aid)
            if r2_url:
                break
        if not r2_url:
            continue
        try:
            client.table("corpus_ingest_queue").update({
                "thumbnail_r2_url": r2_url,
                "thumbnail_url": r2_url,
            }).eq("aweme_id", aid).execute()
        except Exception as exc:
            logger.warning("[corpus_queue] thumbnail mirror update failed aweme_id=%s: %s", aid, exc)


async def _reference_ingest_enqueue_and_mirror(
    live_raw_refs: list[dict[str, Any]],
    *,
    niche_id: int,
    niche_label: str,
) -> None:
    """Upsert high-views live references to corpus_ingest_queue + optional R2 thumbnails."""
    min_views = int(pipeline_settings.reference_ingest_min_views)
    rows: list[dict[str, Any]] = []
    mirror_pairs: list[tuple[str, dict[str, Any]]] = []
    for ref in live_raw_refs:
        if ref.get("_from_corpus"):
            continue
        stats = ref.get("statistics") or {}
        vc = int(stats.get("play_count") or 0)
        if vc < min_views:
            continue
        aid = str(ref.get("aweme_id") or "")
        if not aid:
            continue
        thumb_cdn = _get_ref_thumbnail_urls_from_aweme(ref)[0:1]
        thumb0 = thumb_cdn[0] if thumb_cdn else str(ref.get("thumbnail_url") or "")
        rows.append({
            "aweme_id": aid,
            "aweme_url": f"https://www.tiktok.com/video/{aid}",
            "niche_id": niche_id,
            "niche_label": niche_label,
            "views": vc,
            "desc_snippet": str(ref.get("desc") or "")[:200],
            "thumbnail_url": thumb0,
            "ingest_reason": "reference_live_search",
        })
        mirror_pairs.append((aid, ref))
    if not rows:
        return
    client = get_service_client()
    try:
        client.table("corpus_ingest_queue").upsert(
            rows,
            on_conflict="aweme_id",
        ).execute()
        logger.info("[corpus_queue] enqueued %d reference videos", len(rows))
    except Exception as exc:
        # Mirror anyway — the early ``return`` here coupled R2 thumbnail
        # mirroring to queue health, so the 7-week missing-table outage
        # (P-1, fixed 2026-06-10) ALSO silently stopped every live-search
        # reference thumbnail from being mirrored. The two concerns are
        # independent: a broken queue must not produce gray reference tiles.
        logger.warning("[corpus_queue] enqueue failed (mirroring continues): %s", exc)
    await _mirror_queue_thumbnails_for_rows(client=client, rows_payload=mirror_pairs)


def _peer_hook_window_s(
    analysis: dict[str, Any],
    *,
    shot_ref: dict[str, Any] | None = None,
) -> tuple[float | None, float | None]:
    """Best-effort hook/opening window for peer contrast (mirrors shot_reference_matcher)."""
    hook_block = analysis.get("hook_analysis") if isinstance(analysis.get("hook_analysis"), dict) else {}
    timeline = hook_block.get("hook_timeline")
    if isinstance(timeline, list):
        for ev in timeline:
            if not isinstance(ev, dict):
                continue
            raw_t = ev.get("t") if ev.get("t") is not None else ev.get("at_s")
            try:
                t0 = float(raw_t)
                return t0, round(t0 + 3.0, 2)
            except (TypeError, ValueError):
                continue
    scenes = analysis.get("scenes")
    if isinstance(scenes, list):
        for sc in scenes:
            if not isinstance(sc, dict):
                continue
            try:
                t0 = float(sc.get("start_s") or 0)
                t1 = float(sc.get("end_s") or t0 + 2.0)
                return round(t0, 2), round(max(t1, t0 + 0.5), 2)
            except (TypeError, ValueError):
                continue
    if isinstance(shot_ref, dict):
        try:
            t0 = float(shot_ref.get("start_s") or 0)
            t1 = float(shot_ref.get("end_s") or t0 + 2.0)
            return round(t0, 2), round(t1, 2)
        except (TypeError, ValueError):
            pass
    return None, None


def _peer_hook_timestamps_enabled() -> bool:
    """BE gate aligned with presentation/wide-context synthesis (B2)."""
    from getviews_pipeline.settings import settings

    return bool(settings.diagnosis_wide_context)


def _format_hook_sec_label(sec: float) -> str:
    """Short label for prompt/FE cite (e.g. 0.4 -> '0.4s', 62 -> '1:02')."""
    if sec < 60:
        rounded = round(sec, 1)
        return f"{rounded:g}s"
    minutes = int(sec // 60)
    seconds = sec - minutes * 60
    return f"{minutes}:{seconds:04.1f}"


def _reference_evidence_project(ref: dict[str, Any]) -> dict[str, str | int | float | None]:
    meta = ref.get("metadata") if isinstance(ref.get("metadata"), dict) else {}
    analysis = ref.get("analysis") if isinstance(ref.get("analysis"), dict) else {}
    aid = str(ref.get("aweme_id") or meta.get("video_id") or "")
    stats = ref.get("statistics") or {}
    m_metrics = meta.get("metrics") if isinstance(meta.get("metrics"), dict) else {}
    vc = int(stats.get("play_count") or m_metrics.get("views") or 0)
    dsc = (
        ref.get("desc")
        or meta.get("description")
        or (analysis.get("audio_transcript") or "")[:120]
        or ""
    )
    dsc = str(dsc)[:80]
    fmt = (
        ref.get("content_format")
        or analysis.get("content_format")
        or ref.get("format_label")
        or ""
    )
    niche = str(ref.get("niche_label") or ref.get("niche") or meta.get("niche_label") or "")
    # Craft evidence (quality audit 2026-06-11): the synthesis prompt used
    # to see only desc+views per reference, so the diagnosis could never
    # say HOW a winner opens. hook_phrase + the spoken opening line are
    # what make "làm như @handle" advice concrete.
    handle = str(
        ref.get("creator_handle")
        or meta.get("creator_handle")
        or (ref.get("author") or {}).get("unique_id", "")
        or ""
    ).lstrip("@")
    hook_block = analysis.get("hook_analysis") if isinstance(analysis.get("hook_analysis"), dict) else {}
    hook_phrase = str(hook_block.get("hook_phrase") or "")[:110]
    hook_type = str(hook_block.get("hook_type") or "")
    opening_line = str(analysis.get("audio_transcript") or "").strip()[:90]
    shot_ref = ref.get("_shot_reference") if isinstance(ref.get("_shot_reference"), dict) else None
    hook_start_sec: float | None = None
    hook_end_sec: float | None = None
    if _peer_hook_timestamps_enabled():
        hook_start_sec, hook_end_sec = _peer_hook_window_s(analysis, shot_ref=shot_ref)
    return {
        "aid": aid, "vc": vc, "dsc": dsc, "fmt": str(fmt), "niche": niche,
        "handle": handle, "hook_phrase": hook_phrase, "hook_type": hook_type,
        "opening_line": opening_line,
        "hook_start_sec": hook_start_sec,
        "hook_end_sec": hook_end_sec,
    }


def _reference_evidence_lines(
    refs: list[dict[str, Any]],
    corpus_source: str,
) -> str:
    del corpus_source  # per-ref provenance only (flags on ref dict)
    lines: list[str] = []
    for ref in refs:
        p = _reference_evidence_project(ref)
        if not p["aid"]:
            continue
        src = (
            "corpus"
            if (ref.get("_from_corpus") or ref.get("_from_corpus_cache"))
            else "live_search"
        )
        line = (
            f"- aweme_id: {p['aid']} | @{p['handle'] or '?'} | views: {p['vc']} | "
            f"format: {p['fmt']} | desc: {p['dsc']} | source: {src}"
        )
        if p["hook_phrase"]:
            line += f"\n  hook ({p['hook_type'] or '?'}): \"{p['hook_phrase']}\""
        if p["opening_line"] and p["opening_line"][:40] != str(p["hook_phrase"])[:40]:
            line += f"\n  lời mở (transcript): \"{p['opening_line']}…\""
        hook_start = p.get("hook_start_sec")
        if hook_start is not None:
            handle = p["handle"] or "?"
            start_lbl = _format_hook_sec_label(float(hook_start))
            end_raw = p.get("hook_end_sec")
            end_lbl = (
                f"–{_format_hook_sec_label(float(end_raw))}"
                if end_raw is not None
                else ""
            )
            line += (
                f"\n  mốc hook peer: @{handle} mở hook ~{start_lbl}{end_lbl} "
                f"(cite: «@{handle} mở ở {start_lbl}»)"
            )
        lines.append(line)
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


# Generic hashtags that carry no niche signal — reject so keyword/hashtag
# search falls back to a sensible default. (Restored: the Phase C teardown
# dropped this definition but left _niche_query_terms using it → NameError.)
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
    # In-memory session dict — compare path only (no chat DB context).
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




def _build_follow_ups(
    intent: str,
    niche_label: str,
    analyzed: list[dict[str, Any]] | None = None,
    *,
    handle: str | None = None,
    topic: str = "",
) -> list[str]:
    """Rule-based follow-up chips for ``run_video_diagnosis`` (compare path)."""
    _ = niche_label, analyzed, handle, topic
    if intent != "video_diagnosis":
        return []
    return [
        "Cho mình 3 hook thay thế chi tiết",
        "Gợi ý 3 thay đổi cụ thể cho video tiếp theo",
        "Thumbnail nên chỉnh thế nào?",
    ]


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


# VN phrases that signal the user wants content-direction suggestions.
# (Restored: the Phase C teardown dropped this definition but left
# _wants_directions using it → NameError.)
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
                .eq("ingest_loop_niche_id", niche_id)
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


async def _reference_pool_class_ids(
    session: dict[str, Any],
    *,
    niche: str,
    video_id: str | None,
    legacy_niche_id_hint: int | None = None,
) -> tuple[int | None, int | None]:
    """Resolve ``(content_class_id, legacy_niche_id)`` for corpus reference pool."""

    legacy_niche_id = int(legacy_niche_id_hint) if legacy_niche_id_hint else None
    if legacy_niche_id is None or legacy_niche_id <= 0:
        resolved = await resolve_niche_id_cached(session, niche)
        legacy_niche_id = int(resolved) if resolved else None

    content_class_id: int | None = None
    content_format = ""
    if video_id:
        try:
            client = get_service_client()
            row = (
                client.table("video_corpus")
                .select("content_class_id,content_format,niche_id:ingest_loop_niche_id")
                .eq("video_id", video_id)
                .maybe_single()
                .execute()
            )
            data = row.data if row else None
            if isinstance(data, dict):
                raw_cc = data.get("content_class_id")
                if raw_cc is not None:
                    try:
                        content_class_id = int(raw_cc)
                    except (TypeError, ValueError):
                        content_class_id = None
                content_format = str(data.get("content_format") or "")
                row_nid = data.get("niche_id")
                if (legacy_niche_id is None or legacy_niche_id <= 0) and row_nid is not None:
                    legacy_niche_id = int(row_nid)
        except Exception as exc:
            logger.debug("[video_diagnosis] corpus class lookup failed: %s", exc)

    meta: dict[str, Any] = {
        "content_class_id": content_class_id,
        "niche_id": legacy_niche_id,
        "content_format": content_format,
    }
    cc = content_class_id_for_reference_pool(meta, content_format=content_format)
    return cc, legacy_niche_id


async def _derive_class_after_user_analysis(
    user_res: dict[str, Any],
    session: dict[str, Any],
    niche: str,
    legacy_niche_id: int | None,
) -> tuple[int | None, int | None]:
    """Post-extraction class for ref pool when corpus row lacked ``content_class_id``."""
    niche_id = int(legacy_niche_id or 0)
    if niche_id <= 0:
        resolved = await resolve_niche_id_cached(session, niche)
        niche_id = int(resolved) if resolved else 0
    if niche_id <= 0:
        return None, None
    analysis = user_res.get("analysis") or {}
    if not isinstance(analysis, dict):
        return None, None
    content_format = classify_format(analysis, niche_id)
    cc = content_class_id_for_reference_pool(
        {"niche_id": niche_id, "content_format": content_format},
        content_format=content_format,
    )
    return (cc, niche_id) if cc else (None, None)


async def _load_corpus_ref_pool_and_picks(
    *,
    niche: str,
    uid: str,
    video_desc: str,
    video_hashtags: list[str],
    cached_ids: set[str],
    content_class_id: int | None,
    legacy_niche_id: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str]:
    """Corpus ref pool + proximity picks (+ content-targeted merge)."""
    fetch_days = corpus_reference_fetch_days()
    pick_days = corpus_reference_pick_days()
    corpus_pool = await fetch_corpus_reference_pool(
        niche,
        days=fetch_days,
        limit=40,
        exclude_video_id=uid or None,
        content_class_id=content_class_id,
        legacy_niche_id=legacy_niche_id,
    )
    for v in corpus_pool:
        v["niche_label"] = niche
    corpus_source = "corpus"
    if len(corpus_pool) >= REF_N:
        pool = corpus_pool
        picks = _select_by_proximity_then_er(
            corpus_pool,
            video_desc=video_desc,
            video_hashtags=video_hashtags,
            cached_ids=cached_ids,
            n=REF_N,
            recency_days=pick_days,
        )
        logger.info(
            "[ref_source] niche=%s class=%s corpus_hit=true corpus_size=%d",
            niche,
            content_class_id,
            len(corpus_pool),
        )
    else:
        corpus_source = "live_search" if len(corpus_pool) == 0 else "sparse_fallback"
        logger.warning(
            "[ref_source] niche=%s class=%s corpus_hit=false corpus_size=%d threshold=%d source=%s — "
            "falling back to live EnsembleData search (costs API units)",
            niche,
            content_class_id,
            len(corpus_pool),
            REF_N,
            corpus_source,
        )
        pool = await _niche_aweme_pool(niche, period=fetch_days)
        for v in pool:
            v.setdefault("niche_label", niche)
        picks = _select_by_proximity_then_er(
            pool,
            video_desc=video_desc,
            video_hashtags=video_hashtags,
            cached_ids=cached_ids,
            n=REF_N,
            recency_days=pick_days,
        )

    pool, picks = await _maybe_merge_content_targeted_refs_async(
        pool,
        picks,
        video_desc=video_desc,
        video_hashtags=video_hashtags,
        niche=niche,
        cached_ids=cached_ids,
        n=REF_N,
        recency_days=pick_days,
    )
    return corpus_pool, pool, picks, corpus_source


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
    import time as _time
    _diag_started = _time.monotonic()
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
    _db_niche_id: int | None = None
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

    video_desc = str(user_aweme.get("desc") or "")
    video_hashtags = [
        str(t.get("hashtag_name") or t.get("title") or "").lstrip("#")
        for t in (user_aweme.get("text_extra") or [])
        if t.get("hashtag_name") or t.get("title")
    ]

    # Prefer curated corpus (class → junction → niche ladder) over live search.
    ref_content_class_id, ref_legacy_niche_id = await _reference_pool_class_ids(
        session,
        niche=niche,
        video_id=uid or None,
        legacy_niche_id_hint=_db_niche_id,
    )
    corpus_pool, pool, picks, corpus_source = await _load_corpus_ref_pool_and_picks(
        niche=niche,
        uid=uid,
        video_desc=video_desc,
        video_hashtags=video_hashtags,
        cached_ids=cached_ids,
        content_class_id=ref_content_class_id,
        legacy_niche_id=ref_legacy_niche_id,
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
                "_from_corpus": True,
                "niche_label": niche,
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
                    "niche_label": niche,
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

    user_res: dict[str, Any]
    if ref_content_class_id is None:
        # Compare / off-corpus URLs: derive class from extraction before ref analysis.
        user_res = await _user()
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

        derived_cc, derived_nid = await _derive_class_after_user_analysis(
            user_res, session, niche, ref_legacy_niche_id,
        )
        if derived_cc:
            logger.info(
                "[ref_source] post-analysis class=%s niche_id=%s — refetch pool",
                derived_cc,
                derived_nid,
            )
            ref_content_class_id = derived_cc
            ref_legacy_niche_id = derived_nid
            corpus_pool, pool, picks, corpus_source = await _load_corpus_ref_pool_and_picks(
                niche=niche,
                uid=uid,
                video_desc=video_desc,
                video_hashtags=video_hashtags,
                cached_ids=cached_ids,
                content_class_id=ref_content_class_id,
                legacy_niche_id=ref_legacy_niche_id,
            )
        ref_results = await asyncio.gather(
            *[asyncio.create_task(_ref_with_timeout(a)) for a in picks],
        )
    else:
        user_task = asyncio.create_task(_user())
        ref_tasks = [asyncio.create_task(_ref_with_timeout(a)) for a in picks]
        user_res = await user_task
        ref_results = await asyncio.gather(*ref_tasks)

    references = [r for r in ref_results if "analysis" in r and not r.get("_skipped")]
    for r in references:
        r.setdefault("niche_label", niche)
        if not r.get("aweme_id") and isinstance(r.get("metadata"), dict):
            vid_m = r["metadata"].get("video_id")
            if vid_m:
                r["aweme_id"] = vid_m

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
    try:
        _nid_q = int(niche_id) if niche_id is not None else 0
        if _nid_q > 0:
            asyncio.create_task(
                _reference_ingest_enqueue_and_mirror(
                    list(picks),
                    niche_id=_nid_q,
                    niche_label=niche,
                ),
            )
    except (TypeError, ValueError) as exc:
        logger.debug("[corpus_queue] skip enqueue niche_id=%r: %s", niche_id, exc)

    citation_days = corpus_citation_window_days()
    count, niche_name = await get_corpus_count_cached(
        session, niche_id=niche_id, days=citation_days, niche_name=niche
    )
    citation = build_corpus_citation_block(
        count,
        niche_name,
        days=citation_days,
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
    niche_meta = await get_niche_intelligence(niche)
    # Inject an explicit no-data marker when niche_meta is empty so Gemini
    # cannot hallucinate niche benchmarks. The soft prompt instruction alone
    # ("bỏ qua so sánh") is insufficient — an explicit _note in the JSON is
    # harder for the model to ignore than prose guidance.
    if not niche_meta:
        niche_meta = {"_note": "Không có data niche — KHÔNG tạo số liệu niche, KHÔNG so sánh với chuẩn niche"}
    if niche_id is not None and int(niche_id) > 0:
        niche_meta = enrich_niche_meta_with_sound_radar(int(niche_id), niche_meta)

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
    view_scenarios_out: list[dict[str, str]] | None = None
    channel_context_out: dict[str, Any] | None = None
    refined_performance_tier_out: str | None = None
    diagnosis_errors_out: list[dict[str, Any]] | None = None
    diagnosis_kpi_out: dict[str, Any] | None = None

    # Comment radar resolved up front (cache-backed, fail-open) so the video
    # synthesis path can ground diagnosis in real audience signal — parity with
    # the single-video finalize path. Also feeds the out payload below.
    user_video_id = str(user_metadata_dict.get("video_id") or "")
    comment_radar: dict[str, Any] | None = None
    try:
        from getviews_pipeline.comment_radar_cache import resolve_comment_radar

        comment_count_hint = int(
            (user_metadata_dict.get("metrics") or {}).get("comments") or 0
        )
        if user_video_id:
            comment_radar = await resolve_comment_radar(
                user_video_id, comment_count_hint=comment_count_hint,
            )
    except Exception as exc:
        logger.warning("[video_diagnosis] comment_radar resolve failed: %s", exc)

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
            creator_format_history_block = format_creator_format_history_for_diagnosis(
                _author_handle,
                creator_history,
            )
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
                niche_meta=niche_meta,
                reference_carousels=_truncate_transcripts(carousel_refs),
                user_analysis=_truncate_analysis(user_analysis_dict),
                user_stats=user_stats,
                wants_directions=include_carousel_directions,
                collapsed_questions=questions if questions and len(questions) > 1 else None,
                layer0_context=layer0_context,
                corpus_citation=citation,
                persona_block=persona_block,
                creator_format_history_block=creator_format_history_block,
                niche_posting_context_block="",
            )
        else:
            loop_fmt = asyncio.get_event_loop()
            format_avg = await loop_fmt.run_in_executor(
                None,
                lambda: _format_avg_views_for_diagnosis(int(niche_id or 0), content_format),
            )
            raw_avg_er = niche_meta.get("avg_engagement_rate")
            niche_avg_er = float(raw_avg_er) if raw_avg_er is not None else None
            user_er = float(user_stats.get("engagement_rate") or 0.0)
            er_percentile_rank = _estimate_er_percentile_rank(user_er, niche_avg_er)
            curr_views = int(user_stats.get("views") or 0)
            views_vs_avg_ratio = (
                curr_views / float(format_avg) if format_avg else None
            )
            bright_spot_pre = compute_bright_spot_signal(
                er_percentile_rank,
                views_vs_avg_ratio,
                retention_end_pct=None,
                channel_views_ratio=None,
            )
            corpus_tier = classify_performance_tier_corpus(curr_views, format_avg)

            # Soften to the balanced mode only when the benchmark actively
            # contradicts flop (tier average); unknown (no benchmark) keeps
            # the legacy flop prompt — no evidence either way.
            extraction_mode_stream = (
                "win" if corpus_tier == "hit"
                else "average" if corpus_tier in ("average", "early")
                else "flop"
            )
            video_stub = {
                "creator_handle": handle,
                "views": curr_views,
                "engagement_rate": user_er,
            }
            gemini_errs = await run_sync(
                extract_video_errors,
                extraction_mode=extraction_mode_stream,
                video=video_stub,
                analysis=user_analysis_dict,
                niche_label=niche,
                niche_row=niche_meta,
                retention_curve=None,
            )
            _post_desc = str(user_metadata_dict.get("description") or "").strip()
            errors = apply_rule_based_video_errors(
                gemini_errs,
                user_analysis_dict,
                content_format,
                caption_hint=_post_desc,
                duration_sec=float(user_stats.get("duration") or 0) or None,
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
                    "kpi": kpi_dict,
                    "bright_spot_signal": bright_spot_pre,
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

            ch_ratio: float | None = None
            if channel_context_payload.get("available"):
                med_v = channel_context_payload.get("median_views")
                try:
                    med_f = float(med_v) if med_v is not None else 0.0
                except (TypeError, ValueError):
                    med_f = 0.0
                if med_f > 0:
                    ch_ratio = curr_views / med_f
            bright_spot_signal = compute_bright_spot_signal(
                er_percentile_rank,
                views_vs_avg_ratio,
                retention_end_pct=None,
                channel_views_ratio=ch_ratio,
            )
            bright_spot_out = bright_spot_signal
            view_scenarios_out = compute_view_scenarios(
                performance_tier=refined_tier,
                views_vs_avg_ratio=views_vs_avg_ratio,
                channel_views_ratio=ch_ratio,
            )

            errors_prompt = list(errors)
            if refined_tier == "hit":
                filtered_sev = [
                    e for e in errors if e.get("sev") == "high"
                ]
                if filtered_sev:
                    errors_prompt = filtered_sev

            evidence_block = _reference_evidence_lines(references, corpus_source)

            _author_handle_v = (user_metadata_dict.get("author") or {}).get("username") or ""
            creator_format_history_block_v = ""
            if _author_handle_v:
                _ch_v = await fetch_creator_format_history(_author_handle_v)
                creator_format_history_block_v = format_creator_format_history_for_diagnosis(
                    _author_handle_v,
                    _ch_v,
                )

            _augment_user_stats_for_sound_diagnosis(
                user_stats,
                user_metadata_dict,
                user_analysis_dict,
                int(niche_id) if niche_id is not None else 0,
            )

            # Diagnosis grounding parity: measured hook lift for this class/niche.
            # Fail-open — feature-flag + claim-tier gating applied inside synthesis.
            hook_effectiveness_rows: list[dict[str, Any]] = []
            try:
                hook_effectiveness_rows, _he_axis = await run_sync(
                    fetch_class_hook_effectiveness_sync,
                    get_service_client(),
                    content_class_id=ref_content_class_id,
                    niche_id=int(niche_id) if niche_id is not None else None,
                )
            except Exception as exc:
                logger.warning(
                    "[video_diagnosis] hook_effectiveness fetch failed: %s", exc
                )

            diagnosis_md, narrative_vi_out, format_cards_out = await run_sync(
                synthesize_diagnosis_v2,
                **diagnosis_synthesis_kwargs(
                    content_format=content_format,
                    niche_name=niche,
                    corpus_size=count,
                    niche_meta=niche_meta,
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
                    creator_format_history_block=creator_format_history_block_v,
                    cross_format_signal=None,
                    niche_posting_context_block="",
                    comment_radar=comment_radar,
                    hook_effectiveness=hook_effectiveness_rows,
                    addressing_mode="third_party",
                    video_creator_handle=None,
                ),
            )
            if format_cards_out and niche_id:
                format_cards_out = enrich_format_cards_from_corpus(
                    format_cards_out,
                    int(niche_id),
                    analyzed_content_format=content_format or None,
                )
            _nr_ev: dict[str, Any] = {
                "type": "narrative_ready",
                "narrative_vi": narrative_vi_out,
                "format_cards": format_cards_out,
                "errors": diagnosis_errors_out,
            }
            if bright_spot_out is not None:
                _nr_ev["bright_spot_signal"] = bright_spot_out
            if view_scenarios_out is not None:
                _nr_ev["view_scenarios"] = view_scenarios_out
            emit(step_queue, _nr_ev)
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
    # primary diagnosis path. ``user_video_id`` + ``comment_radar`` were already
    # resolved before synthesis (grounding parity); reuse them here.

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
            out["structural_errors"] = diagnosis_errors_out
        if diagnosis_kpi_out is not None:
            out["kpi"] = diagnosis_kpi_out
        if bright_spot_out is not None:
            out["bright_spot_signal"] = bright_spot_out
        if view_scenarios_out is not None:
            out["view_scenarios"] = view_scenarios_out
        if channel_context_out is not None:
            out["channel_context"] = channel_context_out
        if refined_performance_tier_out is not None:
            out["performance_tier"] = refined_performance_tier_out
        if narrative_vi_out is not None:
            out["narrative_vi"] = narrative_vi_out
        if format_cards_out is not None:
            out["format_cards"] = format_cards_out
        # Phase 4.4.6 — stable BE marker so the FE can detect v5 responses
        # without brittle sentence-count heuristics on van_de_chinh.
        out["_schema_version"] = "v5"

    import time as _time_end

    from getviews_pipeline.observability import log_diagnosis_event
    log_diagnosis_event(
        request_id=session.get("session_id"),
        video_id=str((user_res.get("metadata") or {}).get("video_id") or ""),
        duration_ms=int((_time_end.monotonic() - _diag_started) * 1000),
        cache_source="fresh",
        content_format=content_format,
        niche_id=niche_id,
        performance_tier=str(refined_performance_tier_out or ""),
    )
    return out


