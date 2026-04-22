"""Batch corpus ingest: fetch trending posts per niche → analyze → upsert to video_corpus.

Flow per niche:
  1. Fetch top posts via keyword + hashtag search (EnsembleData).
  2. Filter to posts not already in video_corpus (skip known video_ids).
  3. Analyze each post with Gemini (video or carousel path).
  4. Upsert rows to video_corpus via service-role Supabase client.
  5. After all niches complete, refresh niche_intelligence materialized view.
  6. On Sundays: run batch_analytics (creator_velocity + breakout_multiplier)
               + signal_classifier (signal_grades per niche × hook_type).

Designed to run as a Cloud Scheduler cron or via POST /batch/ingest.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import analyze_aweme, analyze_aweme_from_path
from getviews_pipeline.config import (
    ADAPTIVE_HASHTAG_MIN_FETCH,
    CORPUS_LEGACY_CAROUSEL_HASHTAG_FETCH,
    HASHTAG_YIELD_THRESHOLD,
)
from getviews_pipeline.ed_budget import theoretical_ed_pool_requests
from getviews_pipeline.hashtag_niche_map import learn_hashtag_mappings
from getviews_pipeline.helpers import (
    DISTRIBUTION_GENERIC_HASHTAGS,
    filter_recency,
    merge_aweme_lists,
)
from getviews_pipeline.r2 import (
    download_and_upload_thumbnail,
    download_and_upload_video,
    extract_and_upload,
    r2_configured,
)
from getviews_pipeline.runtime import get_analysis_semaphore

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

BATCH_VIDEOS_PER_NICHE = int(os.environ.get("BATCH_VIDEOS_PER_NICHE", "10"))
BATCH_RECENCY_DAYS = int(os.environ.get("BATCH_RECENCY_DAYS", "30"))
BATCH_MAX_FAILURES = int(os.environ.get("BATCH_MAX_FAILURES", "3"))
BATCH_CONCURRENCY = int(os.environ.get("BATCH_CONCURRENCY", "4"))

# Quality gates — tune via env vars without redeploying
# Minimum views a post must have to enter the corpus (filters low-reach content)
BATCH_MIN_VIEWS = int(os.environ.get("BATCH_MIN_VIEWS", "20000"))
# Minimum engagement rate % — (likes+comments+shares)/views*100 (filters dead content)
BATCH_MIN_ER = float(os.environ.get("BATCH_MIN_ER", "2.0"))
# Keyword search pages fetched per niche (each page ~20 posts, broadens candidate pool)
BATCH_KEYWORD_PAGES = int(os.environ.get("BATCH_KEYWORD_PAGES", "2"))
# Carousel ingest: carousels per niche per batch run
BATCH_CAROUSELS_PER_NICHE = int(os.environ.get("BATCH_CAROUSELS_PER_NICHE", "3"))
# Carousel quality gate: minimum likes (digg_count) — used instead of play_count
# because TikTok doesn't report play_count for carousels reliably in feed responses
BATCH_CAROUSEL_MIN_LIKES = int(os.environ.get("BATCH_CAROUSEL_MIN_LIKES", "500"))
# Max signal_hashtags used for EnsembleData fetch calls per niche.
# signal_hashtags array may grow to 25+ for better _resolve_niche_id() coverage,
# but we cap EnsembleData calls to avoid unit limit exhaustion.
# All hashtags are still used for in-DB matching (no API cost); only fetch is capped.
BATCH_HASHTAG_FETCH_LIMIT = int(os.environ.get("BATCH_HASHTAG_FETCH_LIMIT", "6"))

# Reingest multi-info chunk size (URL limits + ED billing — tune via REINGEST_MULTI_CHUNK).
REINGEST_MULTI_CHUNK = max(1, int(os.environ.get("REINGEST_MULTI_CHUNK", "12") or "12"))


def _norm_corpus_hashtag(ht: str) -> str:
    return ht.strip().lstrip("#").lower()


def _pick_hashtags_for_pool_fetch(
    signal_hashtags: list[str],
    yields_by_tag: dict[str, int],
    limit: int,
) -> list[str]:
    """Order hashtags by recent ingest yield; trim adaptive fetch list (see plan §10)."""
    if not signal_hashtags or limit <= 0:
        return []
    tags = list(signal_hashtags)
    tags.sort(
        key=lambda t: yields_by_tag.get(_norm_corpus_hashtag(t), 0),
        reverse=True,
    )
    high = [
        t
        for t in tags
        if yields_by_tag.get(_norm_corpus_hashtag(t), 0) >= HASHTAG_YIELD_THRESHOLD
    ]
    if len(high) >= ADAPTIVE_HASHTAG_MIN_FETCH:
        return high[:limit]
    if high:
        rest = [t for t in tags if t not in high]
        return (high + rest)[:limit]
    return tags[:limit]


# ── Result containers ───────────────────────────────────────────────────────────

@dataclass
class IngestResult:
    niche_id: int
    niche_name: str
    inserted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class BatchSummary:
    total_inserted: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    niches_processed: int = 0
    niche_results: list[dict[str, Any]] = field(default_factory=list)
    materialized_view_refreshed: bool = False


# ── Supabase service-role client ────────────────────────────────────────────────

def _service_client() -> Any:
    """Create a Supabase client with service_role key (bypasses RLS for batch writes)."""
    from getviews_pipeline.supabase_client import get_service_client

    return get_service_client()


def _load_hashtag_yields_all_sync(client: Any) -> dict[int, dict[str, int]]:
    """niche_id → { normalized_hashtag → ingest_count } for last 14d (RPC)."""
    try:
        result = client.rpc("corpus_hashtag_yields_14d", {}).execute()
    except Exception as exc:
        logger.warning(
            "[corpus] corpus_hashtag_yields_14d RPC failed (run migration 20260429180000?): %s",
            exc,
        )
        return {}
    out: dict[int, dict[str, int]] = {}
    for row in result.data or []:
        try:
            nid = int(row.get("niche_id"))
        except (TypeError, ValueError):
            continue
        ht = _norm_corpus_hashtag(str(row.get("hashtag") or ""))
        if not ht:
            continue
        try:
            cnt = int(row.get("ingest_count") or 0)
        except (TypeError, ValueError):
            cnt = 0
        out.setdefault(nid, {})[ht] = cnt
    return out


# ── Distribution annotations ────────────────────────────────────────────────────
# Alias for annotate_distribution() — the full distribution-generic set lives in
# helpers.DISTRIBUTION_GENERIC_HASHTAGS so both this module and hashtag_niche_map
# use the identical filter (no local copy → no divergence risk).
GENERIC_HASHTAGS: frozenset[str] = DISTRIBUTION_GENERIC_HASHTAGS


def annotate_distribution(hashtags: list[str], caption: str | None) -> dict[str, Any]:
    """Compute distribution annotations from ED metadata.

    These are NOT quality gates — all rows are still ingested regardless.
    They annotate each video so niche_intelligence can compute:
      - pct_has_specific_hashtags: % of top videos with ≥1 niche-specific hashtag
      - pct_has_caption_text: % of top videos with real text beyond hashtags
      - avg_hashtag_count: hashtag volume norms per niche
      - pct_original_sound: already exists in niche_intelligence (from is_original_sound)

    These feed into the synthesis prompt, enabling data-backed distribution claims:
      "92% top video trong ngách skincare có caption + hashtag cụ thể cho ngách.
       Video bạn chỉ có 4 hashtag tiếng Anh chung chung (#trending #ootd) —
       thuật toán không biết đẩy cho ai."
    """
    tags_lower = [t.lower() for t in (hashtags or [])]

    # True = at least 1 hashtag is niche-specific (not in the generic noise list)
    has_specific = any(t not in GENERIC_HASHTAGS for t in tags_lower)

    # True = caption contains ≥10 chars of non-hashtag text
    has_caption_text = False
    if caption:
        stripped = re.sub(r"#\w+\s*", "", caption).strip()
        has_caption_text = len(stripped) > 10

    return {
        "has_vietnamese_hashtags": has_specific,
        "has_caption_text": has_caption_text,
        "hashtag_count": len(tags_lower),
    }


# ── Niche fetching ──────────────────────────────────────────────────────────────

async def _fetch_niches(client: Any) -> list[dict[str, Any]]:
    """Return all rows from niche_taxonomy."""
    result = client.table("niche_taxonomy").select("id, name_en, name_vn, signal_hashtags").execute()
    return result.data or []


async def _existing_video_ids(client: Any, niche_id: int) -> set[str]:
    """Return set of video_ids already in video_corpus for this niche."""
    result = (
        client.table("video_corpus")
        .select("video_id")
        .eq("niche_id", niche_id)
        .execute()
    )
    return {row["video_id"] for row in (result.data or [])}


# ── Post pool fetch ─────────────────────────────────────────────────────────────

async def _fetch_keyword_pages(
    term: str,
    *,
    max_pages: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch keyword search results, following nextCursor.

    ``max_pages`` defaults to BATCH_KEYWORD_PAGES (deep-pool ingest can pass a larger cap).
    Stops early when a page contributes **no** new ``aweme_id`` values vs prior pages
    (adaptive keyword paging — saves ED units when the feed is exhausted / duplicate-heavy).
    """
    pages = max_pages if max_pages is not None else BATCH_KEYWORD_PAGES
    all_awemes: list[dict[str, Any]] = []
    cursor: int = 0
    seen_aweme_ids: set[str] = set()
    for page in range(pages):
        try:
            awemes, next_cursor = await ensemble.fetch_keyword_search(
                term, period=BATCH_RECENCY_DAYS, cursor=cursor
            )
            new_ids = 0
            for a in awemes:
                aid = str(a.get("aweme_id") or "")
                if aid and aid not in seen_aweme_ids:
                    seen_aweme_ids.add(aid)
                    new_ids += 1
            all_awemes.extend(awemes)
            logger.debug(
                "[corpus] keyword='%s' page=%d fetched=%d new_ids=%d next_cursor=%s",
                term, page, len(awemes), new_ids, next_cursor,
            )
            if next_cursor is None or not awemes:
                break
            # Only skip further pages when a non-first page repeats only IDs we already saw.
            if page > 0 and awemes and new_ids == 0:
                logger.info(
                    "[corpus] keyword='%s' early-exit after page=%d (0 new aweme_ids)",
                    term,
                    page,
                )
                break
            cursor = next_cursor
        except Exception as exc:
            logger.warning("[corpus] keyword search page %d failed for '%s': %s", page, term, exc)
            break
    return all_awemes


async def _fetch_niche_pool(
    niche: dict[str, Any],
    *,
    keyword_pages: int | None = None,
    hashtag_yields: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Fetch posts for a niche via keyword search (paginated) + all signal hashtags, merged + deduped."""
    term = (niche.get("name_en") or "").strip()
    hashtags: list[str] = niche.get("signal_hashtags") or []

    # Keyword search: paginated — broadens pool beyond a single page of ~20 posts
    keyword_task = _fetch_keyword_pages(term, max_pages=keyword_pages)
    # Cap hashtag fetch calls; order by recent ingest yield when RPC data exists.
    yields = hashtag_yields or {}
    fetch_hashtags = _pick_hashtags_for_pool_fetch(
        hashtags, yields, BATCH_HASHTAG_FETCH_LIMIT
    )
    hashtag_tasks = [
        ensemble.fetch_hashtag_posts(ht.lstrip("#"), cursor=0)
        for ht in fetch_hashtags
    ]

    all_results = await asyncio.gather(keyword_task, *hashtag_tasks, return_exceptions=True)

    all_awemes: list[dict[str, Any]] = []
    for res in all_results:
        if isinstance(res, Exception):
            logger.warning("[corpus] pool fetch error: %s", res)
            continue
        if isinstance(res, tuple):
            awemes, _ = res
        elif isinstance(res, list):
            awemes = res
        else:
            continue
        all_awemes.extend(awemes)

    merged = merge_aweme_lists(all_awemes, [])
    return filter_recency(merged, BATCH_RECENCY_DAYS)


async def _fetch_carousel_pool(niche: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch carousel posts (aweme_type=2) for a niche from signal hashtag feeds.

    ED's keyword search surfaces mostly videos. Carousels live in hashtag feeds
    but are mixed with videos. This function fetches the same hashtag feeds and
    filters to aweme_type=2 (photo carousel) only.

    Quality proxy: uses digg_count (likes) instead of play_count because TikTok
    does not report play_count reliably for carousels in feed API responses —
    the field is often 0 even for high-reach carousels.
    """
    hashtags: list[str] = niche.get("signal_hashtags") or []
    if not hashtags:
        return []

    # Cap carousel hashtag fetch to same limit as video pool fetch.
    fetch_hashtags = hashtags[:BATCH_HASHTAG_FETCH_LIMIT]
    hashtag_tasks = [
        ensemble.fetch_hashtag_posts(ht.lstrip("#"), cursor=0)
        for ht in fetch_hashtags
    ]
    results = await asyncio.gather(*hashtag_tasks, return_exceptions=True)

    all_awemes: list[dict[str, Any]] = []
    for res in results:
        if isinstance(res, Exception):
            logger.warning("[corpus] carousel hashtag fetch error: %s", res)
            continue
        awemes, _ = res if isinstance(res, tuple) else (res, None)
        all_awemes.extend(awemes or [])

    # Filter to carousels only — aweme_type=2 or image_post_info.images present
    carousels = [
        a for a in all_awemes
        if ensemble.detect_content_type(a) == "carousel"
    ]

    logger.info(
        "[corpus] carousel pool for niche '%s': %d carousels from %d total hashtag posts",
        niche.get("name_en", "?"), len(carousels), len(all_awemes),
    )
    return filter_recency(carousels, BATCH_RECENCY_DAYS)


def _carousel_pool_from_merged_video_pool(
    pool: list[dict[str, Any]],
    *,
    niche_name: str,
) -> list[dict[str, Any]]:
    """Derive carousel candidates from the same merged pool as videos (no 2nd hashtag pass)."""
    carousels = [
        a for a in pool if ensemble.detect_content_type(a) == "carousel"
    ]
    logger.info(
        "[corpus] carousel pool (merged) niche='%s': %d carousels from pool size %d",
        niche_name,
        len(carousels),
        len(pool),
    )
    return filter_recency(carousels, BATCH_RECENCY_DAYS)


# ── Single post ingest ──────────────────────────────────────────────────────────

_VIETNAMESE_PATTERN = re.compile(
    r"[\u00c0-\u024f\u1e00-\u1eff\u0300-\u036f]"  # diacritics common in Vietnamese
)


def _has_vietnamese_chars(text: str) -> bool:
    """Return True if the text contains Vietnamese diacritical characters.

    Vietnamese uses precomposed Unicode characters (e.g. ắ, ề, ượ) in the
    Latin Extended-A/B and Latin Extended Additional blocks. A single match is
    sufficient — any diacritic signals a high probability of Vietnamese content.
    English, Korean, and Japanese captions won't have these characters.
    """
    return bool(_VIETNAMESE_PATTERN.search(text))


def _safe_engagement_rate(
    *,
    er_from_analysis: float | None,
    views: int,
    likes: int,
    comments: int,
    shares: int,
) -> float:
    """Return engagement rate as a percentage. Never returns >100 or infinity.

    Priority:
      1. Use er_from_analysis when views > 0 (already correctly calculated in parse_metadata)
      2. Recalculate from raw counts when er_from_analysis is None but views > 0
      3. Return 0 when views = 0 (never divide by zero)
    """
    if views <= 0:
        return 0.0
    if er_from_analysis is not None:
        er = float(er_from_analysis)
        # Sanity cap: ER > 100% signals a calculation error
        return min(er, 100.0)
    return min((likes + comments + shares) / views * 100.0, 100.0)


# ── Corpus classifiers ─────────────────────────────────────────────────────────
# Python equivalents of src/lib/batch/classifiers.ts — keep in sync.

_VN_PATTERN = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)

_HOOK_TYPE_ALIASES: dict[str, str] = {
    # Canonical values from models.py HookType — must all pass through unchanged
    "question": "question", "bold_claim": "bold_claim", "shock_stat": "shock_stat",
    "story_open": "story_open", "controversy": "controversy", "challenge": "challenge",
    "how_to": "how_to", "social_proof": "social_proof", "curiosity_gap": "curiosity_gap",
    "pain_point": "pain_point", "trend_hijack": "trend_hijack", "none": "none", "other": "other",
    # Additional canonical values from knowledge-base HOOK_CATEGORIES
    "warning": "warning", "price_shock": "price_shock", "reaction": "reaction",
    "comparison": "comparison", "expose": "expose", "pov": "pov",
    # Vietnamese-language aliases
    "canh_bao": "warning", "gia_soc": "price_shock", "phan_ung": "reaction",
    "so_sanh": "comparison", "boc_phot": "expose", "huong_dan": "how_to",
    "ke_chuyen": "story_open", "bang_chung": "social_proof",
    # English synonyms Gemini might use
    "tutorial": "how_to", "story": "story_open", "storytelling": "story_open",
    "shock": "bold_claim", "tips": "how_to", "fomo": "warning", "fear": "warning",
    # New categories — map to closest canonical HookType for DB column compatibility
    "curiosity": "curiosity_gap", "curiosity_gap": "curiosity_gap",
    "insider": "social_proof", "secret": "social_proof",
}

_SOUTHERN = [
    r"\btui\b", r"\bmấy bà\b", r"\bnè\b", r"\bnha\b", r"\bhông\b",
    r"\bquá trời\b", r"\bdzậy\b", r"\bvầy\b", r"\bbiết hông\b",
    r"á(?=\s|[.,!?])", r"\btrời ơi\b", r"\bluôn á\b",
    r"\bnghen\b", r"\bhen\b", r"\bquá xá\b",
]
_NORTHERN = [
    r"\bmình\b", r"\bcác bạn\b", r"\bnhé\b", r"ạ(?=\s|[.,!?])",
    r"\bcực kỳ\b", r"\bthế\b", r"\bvậy à\b", r"\bbiết không\b",
    r"\bkhông ạ\b", r"\bấy\b", r"\bđấy\b", r"\bcơ\b",
]
_CENTRAL = [r"\bchi\b", r"\bmô\b(?=\s)", r"\bni\b", r"\brứa\b", r"\brăng\b"]


def _normalize_hook_type(raw: str) -> str:
    return _HOOK_TYPE_ALIASES.get(raw.lower(), "other")


def classify_format(analysis_json: dict[str, Any], niche_id: int) -> str:
    """Classify a video's content format from its Gemini analysis.

    ━━━ TAXONOMY LOCK — READ BEFORE CHANGING ━━━
    The 15 values this function can return are a hard contract shared across 7 layers:

        corpus_ingest.py     → writes content_format into video_corpus (DB column)
        output_redesign.py   → FORMAT_ANALYSIS_WEIGHTS keyed to these 15 values;
                               get_analysis_focus() switches on them; diagnosis prompt
                               injects format-specific signal priorities
        gemini.py            → reads content_format from corpus; passes to
                               build_diagnosis_narrative_prompt() and
                               build_carousel_diagnosis_narrative_prompt()
        layer0_niche.py      → queries content_format for formula detection
                               (top formula = best hook_type × content_format pair)
        layer0_migration.py  → groups migration signals by content_format per week
        niche_intelligence   → format_distribution JSONB aggregated from content_format;
                               used in diagnosis framing and Layer 0A synthesis
        prompts.py           → format_distribution injected into corpus citation blocks

    ANY taxonomy change (add / rename / remove a value) requires ALL of the above to
    change atomically in a single migration + deploy. Backfilling existing DB rows via
    SQL UPDATE is also required — old values will silently fall through to the "other"
    branch in FORMAT_ANALYSIS_WEIGHTS, degrading diagnosis quality.

    The plan §M.8 proposal (Gemini Flash-Lite reclassification into react/unbox/list/
    trending_hook) was evaluated and DEFERRED. Regex classification is intentional here:
    it is deterministic, zero-cost, and zero-latency. Switching to Gemini classification
    adds ~$0.002/video in extraction cost and a round-trip latency with no quality gain
    for the primary use-case (format_distribution benchmarking). If the taxonomy is
    expanded in the future, add new values to FORMAT_ANALYSIS_WEIGHTS FIRST, run the
    migration + backfill SECOND, then update this function THIRD.

    PRIORITY ORDER — intentional, highest specificity first:

    1. mukbang   — eating/ASMR signals are highly specific; checked before recipe/review.
    2. grwm      — "get ready with me" is a named ritual format; checked before tutorial.
    3. recipe    — cooking actions (nấu, chiên, ướp) are more specific than generic "cách làm".
                   NOTE: "hướng dẫn nấu ăn" matches recipe here, NOT tutorial (line below).
                   This is intentional — recipe is more semantically precise for food content.
    4. haul      — unboxing/haul signals are unambiguous; checked before review.
    5. review    — broad category. Intentionally catches "review + tutorial" combos because
                   the dominant intent of such videos is evaluation, not instruction.
                   NOTE: "so sánh + review" → review wins here. Comparison is checked below
                   only for videos without explicit review vocabulary.
    6. tutorial  — how-to instruction; falls here only if not caught by recipe/grwm above.
    7. comparison — "vs / so sánh" without review vocabulary.
    8. storytelling — narrative past-tense signals.
    9. before_after — transformation arc signals.
    10. pov       — anchored to the literal string "pov:" at transcript start.
    11. outfit_transition — fashion/transition signals.
    12. vlog      — lifestyle/daily signals; broad, checked late to avoid false positives.
    13. dance     — scene-only classification (no transcript, all action scenes).
    14. faceless  — product/demo scenes without face_to_camera and with spoken transcript.
    15. other     — fallback.

    These priorities affect format_distribution in niche_intelligence. If the observed
    distribution for a niche looks wrong, check whether the ranking above needs adjustment
    for that niche's vocabulary before adding niche-specific overrides.
    """
    transcript = (analysis_json.get("audio_transcript") or "").lower()
    topics = " ".join(t.lower() for t in (analysis_json.get("topics") or []))
    scenes = analysis_json.get("scenes") or []
    tone = analysis_json.get("tone") or ""
    combined = f"{transcript} {topics}"

    if re.search(r"mukbang|ăn.*cùng|mời.*ăn|eating|asmr", combined): return "mukbang"
    if niche_id == 4 and len(scenes) >= 10 and tone == "entertaining": return "mukbang"
    if re.search(r"grwm|get ready|makeup routine|morning routine|buổi sáng", combined): return "grwm"
    if re.search(r"công thức|recipe|nấu|cách làm|nguyên liệu|ướp|xào|chiên|nướng|hấp", combined): return "recipe"
    if re.search(r"haul|đập hộp|unbox|mở hộp|mua.*về|đặt.*gửi", combined): return "haul"
    if re.search(
        r"review|chấm điểm|đánh giá|dùng thử|trải nghiệm|"
        r"ăn đứt|đỉnh hơn|đẳng cấp|phần trình diễn|màn trình diễn",
        combined,
    ):
        return "review"
    if re.search(
        r"cách|hướng dẫn|tutorial|mẹo|bước|step|tips|"
        r"xác minh|đăng ký|thủ tục|quyết toán|bí quyết",
        combined,
    ):
        return "tutorial"
    if re.search(
        r"vs |so sánh|versus|cái nào|nào hơn|nào tốt|khác nhau|phân biệt|khác biệt",
        combined,
    ):
        return "comparison"
    if re.search(
        r"kể chuyện|story|hồi đó|hồi nhỏ|ngày xưa|mình từng|"
        r"câu chuyện|kể về|nàng dâu|chàng rể|đằng sau là|"
        r"sự thật|lời kể|chia sẻ câu chuyện",
        combined,
    ):
        return "storytelling"
    if re.search(r"trước.*sau|before.*after|biến đổi|thay đổi.*ngày|glow.?up", combined): return "before_after"
    if re.match(r"pov[: ]", combined.lstrip()): return "pov"
    if re.search(r"outfit|ootd|biến hình|transition|mix đồ|phối đồ", combined): return "outfit_transition"
    if re.search(r"vlog|daily|thường ngày|một ngày|hôm nay mình|ngày của", combined): return "vlog"
    if scenes and all(s.get("type") == "action" for s in scenes) and not transcript: return "dance"
    product_types = {"product_shot", "demo", "action"}
    if (scenes and all(s.get("type") in product_types for s in scenes)
            and len(transcript) > 50
            and not any(s.get("type") == "face_to_camera" for s in scenes)):
        return "faceless"
    return "other"


def _classify_cta(cta: str | None) -> str | None:
    if not cta:
        return None
    c = cta.lower()
    if re.search(r"lưu lại|lưu ngay|save|lưu về", c): return "save"
    if re.search(r"theo dõi|follow|đăng ký|subscribe", c): return "follow"
    if re.search(r"comment|bình luận|cho.*biết|chia sẻ.*bên dưới", c): return "comment"
    if re.search(r"giỏ hàng|mua ngay|chốt đơn|đặt hàng|shop|cart", c): return "shop_cart"
    if re.search(r"link.*bio|bio.*link|link.*comment|link.*mô tả", c): return "link_bio"
    if re.search(r"còn tiếp|phần 2|part 2|tiếp tục|tập sau", c): return "part2"
    if re.search(r"thử đi|thử.*xem|làm.*thử|ăn thử", c): return "try_it"
    return "other"


def _detect_commerce(analysis_json: dict[str, Any]) -> bool:
    transcript = (analysis_json.get("audio_transcript") or "").lower()
    overlays = " ".join(
        (t.get("text") or "").lower()
        for t in (analysis_json.get("text_overlays") or [])
    )
    combined = f"{transcript} {overlays}"
    if re.search(r"\d+k\b|\d+đ\b|\d+\.\d+đ|giá.*\d|giảm.*\d+%", combined): return True
    if re.search(r"shopee|tiktok shop|lazada|link.*bio|giỏ hàng|mã giảm|voucher|freeship|affiliate", combined): return True
    if re.search(r"mua ngay|chốt đơn|đặt hàng|mua.*ở đâu|link.*mua|bán hàng|ra đơn", combined): return True
    if re.search(r"flash sale|sale|giảm sốc|giảm giá|khuyến mãi|ưu đãi|hết.*là.*hết", combined): return True
    if re.search(r"giá gốc|giá sale|rẻ hơn|đáng tiền|tiết kiệm", combined): return True
    cta = (analysis_json.get("cta") or "").lower()
    if cta and re.search(r"mua|chốt|giỏ hàng|shop|link", cta): return True
    return False


def _detect_dialect(transcript: str) -> str | None:
    if not transcript or len(transcript) < 20:
        return None
    t = transcript.lower()
    south = sum(1 for p in _SOUTHERN if re.search(p, t))
    north = sum(1 for p in _NORTHERN if re.search(p, t))
    central = sum(1 for p in _CENTRAL if re.search(p, t))
    max_score = max(south, north, central)
    if max_score < 2:
        return None
    if central >= 3:
        return "central"
    if south > north * 1.5:
        return "southern"
    if north > south * 1.5:
        return "northern"
    if south >= 2 and north >= 2:
        return "mixed"
    return "southern" if south > north else "northern"


def _classify_creator_tier(followers: int | None) -> str | None:
    if not followers or followers < 0:
        return None
    if followers < 1_000: return "nano"
    if followers < 10_000: return "micro"
    if followers < 100_000: return "mid"
    if followers < 1_000_000: return "macro"
    return "mega"


def _vietnam_hour(create_time: int | None) -> int | None:
    if not create_time:
        return None
    dt = datetime.fromtimestamp(create_time, tz=UTC)
    return (dt.hour + 7) % 24


def _normalize_handle(handle: str) -> str:
    return handle.lstrip("@").lower().strip()


def _build_corpus_row(
    aweme: dict[str, Any],
    analysis: dict[str, Any],
    niche_id: int,
) -> dict[str, Any] | None:
    """Map aweme + analysis result to a video_corpus row dict. Returns None on error."""
    if "error" in analysis or "analysis" not in analysis:
        return None

    metadata = analysis.get("metadata") or {}
    # VideoMetadata serialises stats under "metrics" (not "stats")
    metrics = metadata.get("metrics") or {}
    # Fallback: read raw aweme statistics dict if metrics is empty
    raw_stats = aweme.get("statistics") or {}
    author = metadata.get("author") or {}
    content_type = analysis.get("content_type", "video")

    video_id = str(aweme.get("aweme_id", "") or "")
    if not video_id:
        return None

    handle = _normalize_handle(
        author.get("username")
        or str(aweme.get("author", {}).get("unique_id", "") or "")
        or "unknown"
    )

    tiktok_url = (
        metadata.get("tiktok_url")
        or f"https://www.tiktok.com/@{handle}/video/{video_id}"
    )

    # Thumbnail: first CDN URL from display cover if available
    video_obj = aweme.get("video") or {}
    cover = video_obj.get("origin_cover") or video_obj.get("cover") or {}
    cover_urls: list[str] = cover.get("url_list") or []
    thumbnail_url = cover_urls[0] if cover_urls else None

    # Video play URL (first H264 URL)
    video_urls = ensemble.extract_video_urls(aweme)
    video_url = video_urls[0] if video_urls else None

    views = int(metrics.get("views") or raw_stats.get("play_count") or raw_stats.get("playCount") or 0)
    likes = int(metrics.get("likes") or raw_stats.get("digg_count") or 0)
    comments = int(metrics.get("comments") or raw_stats.get("comment_count") or 0)
    shares = int(metrics.get("shares") or raw_stats.get("share_count") or 0)
    saves = int(raw_stats.get("collect_count") or raw_stats.get("collectCount") or 0)

    analysis_json: dict[str, Any] = analysis.get("analysis") or {}
    hook_info: dict[str, Any] = analysis_json.get("hook_analysis") or {}
    scenes: list[dict[str, Any]] = analysis_json.get("scenes") or []

    # ED metadata from aweme
    music: dict[str, Any] = aweme.get("music") or {}
    sound_id = str(music.get("id") or "") or None
    sound_name = music.get("title") or None
    # Detect original sounds via two signal paths (either is sufficient):
    # 1. Explicit API field — EnsembleData may expose music.is_original or music.is_original_sound.
    # 2. Title prefix match — covers EN ("original sound - @handle"), VI ("âm thanh gốc",
    #    "nhạc gốc"), and TikTok Studio uploads ("original audio").
    _music_title_lower = str(sound_name or "").lower()
    is_original_sound = bool(
        music.get("is_original") or music.get("is_original_sound")
        or (sound_name and (
            _music_title_lower.startswith("original sound")
            or _music_title_lower.startswith("original audio")
            or _music_title_lower.startswith("âm thanh gốc")
            or _music_title_lower.startswith("nhạc gốc")
        ))
    )
    create_time: int | None = aweme.get("createTime") or aweme.get("create_time")
    raw_author: dict[str, Any] = aweme.get("author") or {}
    creator_followers: int | None = (
        raw_author.get("follower_count")
        or raw_author.get("followerCount")
        or None
    )
    if creator_followers is not None:
        creator_followers = int(creator_followers)

    desc = aweme.get("desc") or ""
    hashtags: list[str] = [
        c.get("title") or ""
        for c in (aweme.get("challenges") or [])
        if c.get("title")
    ]

    stitch_setting: dict[str, Any] = aweme.get("stitch_setting") or aweme.get("stitchSetting") or {}
    duet_setting: dict[str, Any] = aweme.get("duet_setting") or aweme.get("duetSetting") or {}
    is_stitch = bool(stitch_setting.get("stitch_type") == 1 or stitch_setting.get("stitchType") == 1)
    is_duet = bool(duet_setting.get("duet_type") == 1 or duet_setting.get("duetType") == 1)

    posted_at = (
        datetime.fromtimestamp(create_time, tz=UTC).isoformat()
        if create_time else None
    )

    transcript: str = analysis_json.get("audio_transcript") or ""

    # ── Post-extraction quality checks (warnings only — row is still ingested) ──
    # These catch degraded Gemini extractions that pollute corpus and skew niche_norms.
    # They do NOT block ingest; use the warnings to decide whether to re-run or discard.
    _video_duration_approx = scenes[-1].get("end") if scenes else None
    if _video_duration_approx and _video_duration_approx > 10 and len(scenes) <= 1:
        logger.warning(
            "[corpus_quality] video_id=%s: only %d scene(s) for %.0fs video — "
            "likely coarse extraction; transitions_per_second will be wrong",
            video_id, len(scenes), _video_duration_approx,
        )
    _tps = analysis_json.get("transitions_per_second") or 0
    if len(scenes) > 1 and _tps == 0:
        logger.warning(
            "[corpus_quality] video_id=%s: %d scenes but transitions_per_second=0 — "
            "extraction inconsistency",
            video_id, len(scenes),
        )
    if transcript and len(transcript) > 20 and not _VN_PATTERN.search(transcript):
        logger.warning(
            "[corpus_quality] video_id=%s: transcript (%d chars) has no Vietnamese "
            "diacritics — possible English paraphrase or mis-transcription",
            video_id, len(transcript),
        )
    hook_phrase = hook_info.get("hook_phrase") or ""
    if hook_phrase and not _VN_PATTERN.search(hook_phrase) and transcript and _VN_PATTERN.search(transcript):
        logger.warning(
            "[corpus_quality] video_id=%s: hook_phrase %r has no Vietnamese diacritics "
            "but transcript does — likely English paraphrase",
            video_id, hook_phrase[:60],
        )

    return {
        # ── Core columns (existing 17) ──
        "video_id": video_id,
        "content_type": content_type,
        "niche_id": niche_id,
        "creator_handle": handle,
        "tiktok_url": tiktok_url,
        "thumbnail_url": thumbnail_url,
        "video_url": video_url,
        "frame_urls": [],
        "analysis_json": analysis_json,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "engagement_rate": _safe_engagement_rate(
            er_from_analysis=analysis.get("engagement_rate") or metadata.get("engagement_rate"),
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
        ),

        # ── Group A: Gemini analysis extraction (11 columns) ──
        "hook_type": _normalize_hook_type(hook_info.get("hook_type") or "other"),
        "hook_phrase": hook_info.get("hook_phrase"),
        "face_appears_at": hook_info.get("face_appears_at"),
        "first_frame_type": hook_info.get("first_frame_type") or "other",
        "video_duration": scenes[-1].get("end") if scenes else None,
        "transitions_per_second": analysis_json.get("transitions_per_second"),
        "tone": analysis_json.get("tone"),
        "text_overlay_count": len(analysis_json.get("text_overlays") or []),
        "scene_count": len(scenes),
        "language": "vi",  # guaranteed by Gate 3/4 in ingest_niche

        # ── Group B: Vietnamese/Asian TikTok-specific (4 columns) ──
        "content_format": classify_format(analysis_json, niche_id),
        "cta_type": _classify_cta(analysis_json.get("cta")),
        "is_commerce": _detect_commerce(analysis_json),
        "dialect": _detect_dialect(transcript),

        # ── Group C: ED metadata (13 columns) ──
        "saves": saves,
        "save_rate": saves / views if views > 0 else None,
        "posted_at": posted_at,
        "posting_hour": _vietnam_hour(create_time),
        "sound_id": sound_id,
        "sound_name": sound_name,
        "is_original_sound": is_original_sound,
        "creator_followers": creator_followers,
        "creator_tier": _classify_creator_tier(creator_followers),
        "caption": desc or None,
        "hashtags": hashtags if hashtags else None,
        "is_stitch": is_stitch,
        "is_duet": is_duet,

        # ── Group D: Searchable text (2 columns) ──
        "topics": analysis_json.get("topics") or [],
        "transcript_snippet": transcript[:500] if transcript else None,

        # ── Group E: Distribution annotations (3 columns) ──
        # Computed from ED metadata already in memory — zero incremental API cost.
        # NOT quality gates. Every row is annotated regardless.
        **annotate_distribution(hashtags, desc or None),
    }


def _video_pool_gate_diagnostics(
    pool: list[dict[str, Any]],
    existing_ids: set[str],
) -> dict[str, int]:
    """Count why video awemes from the keyword/hashtag pool are not selected (mirrors ingest gates)."""
    d: dict[str, int] = {
        "pool_awemes": len(pool),
        "already_in_corpus_this_niche": 0,
        "no_aweme_id": 0,
        "play_count_zero": 0,
        "below_min_views": 0,
        "failed_vn_gate": 0,
        "below_min_er": 0,
        "passed_video_gates": 0,
    }
    for a in pool:
        vid = str(a.get("aweme_id", "") or "")
        if not vid:
            d["no_aweme_id"] += 1
            continue
        if vid in existing_ids:
            d["already_in_corpus_this_niche"] += 1
            continue
        stats = a.get("statistics") or {}
        play_count = int(stats.get("play_count") or stats.get("playCount") or 0)
        if play_count == 0:
            d["play_count_zero"] += 1
            continue
        if play_count < BATCH_MIN_VIEWS:
            d["below_min_views"] += 1
            continue
        author = a.get("author") or {}
        region = str(author.get("region") or "").upper()
        if region and region not in ("VN", ""):
            d["failed_vn_gate"] += 1
            continue
        if not region:
            desc = str(a.get("desc") or "")
            if desc and not _has_vietnamese_chars(desc):
                d["failed_vn_gate"] += 1
                continue
        likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)
        comments = int(stats.get("comment_count") or stats.get("commentCount") or 0)
        shares = int(stats.get("share_count") or stats.get("shareCount") or 0)
        er = _safe_engagement_rate(
            er_from_analysis=None,
            views=play_count,
            likes=likes,
            comments=comments,
            shares=shares,
        )
        if er < BATCH_MIN_ER:
            d["below_min_er"] += 1
            continue
        d["passed_video_gates"] += 1
    return d


async def _ingest_candidate_awemes(
    client: Any,
    niche_id: int,
    niche_name: str,
    candidates: list[dict[str, Any]],
) -> IngestResult:
    """Analyze prepared aweme dicts and upsert rows (shared by pool ingest + explicit reingest)."""
    result = IngestResult(niche_id=niche_id, niche_name=niche_name)
    if not candidates:
        return result

    logger.info("[corpus] niche=%s — analyzing %d candidates", niche_name, len(candidates))

    sem = get_analysis_semaphore()

    async def _analyze_one(aweme: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """Return (analysis_dict, frame_urls). frame_urls is [] for carousels or on failure."""
        async with sem:
            ct = ensemble.detect_content_type(aweme)
            if ct == "carousel":
                analysis = await analyze_aweme(aweme, include_diagnosis=False)
                return analysis, []

            video_urls = ensemble.extract_video_urls(aweme)
            if not video_urls:
                return {
                    "error": "No video URLs in aweme",
                    "metadata": ensemble.parse_metadata(aweme).model_dump(),
                }, []

            video_path: Path | None = None
            try:
                try:
                    video_path = await ensemble.download_video(video_urls)
                except Exception as e:
                    return {
                        "error": str(e),
                        "metadata": ensemble.parse_metadata(aweme).model_dump(),
                    }, []

                vid = str(aweme.get("aweme_id", "") or "")
                async def _noop_frames() -> list[str]:
                    return []

                frame_coro = (
                    extract_and_upload(video_path, vid)
                    if r2_configured()
                    else _noop_frames()
                )
                analysis, frame_urls = await asyncio.gather(
                    analyze_aweme_from_path(aweme, video_path, include_diagnosis=False),
                    frame_coro,
                )
                return analysis, frame_urls if isinstance(frame_urls, list) else []
            finally:
                if video_path is not None:
                    video_path.unlink(missing_ok=True)

    gather_results = await asyncio.gather(
        *[_analyze_one(a) for a in candidates], return_exceptions=True
    )

    rows: list[dict[str, Any]] = []
    frame_urls_by_video_id: dict[str, list[str]] = {}

    for aweme, gather_result in zip(candidates, gather_results):
        if isinstance(gather_result, Exception):
            logger.warning("[corpus] analyze error: %s", gather_result)
            result.failed += 1
            result.errors.append(str(gather_result))
            continue
        analysis, frame_urls = gather_result
        row = _build_corpus_row(aweme, analysis, niche_id)
        vid = str(aweme.get("aweme_id", "") or "")
        if row is None:
            result.skipped += 1
            err = analysis.get("error")
            logger.warning(
                "[corpus] niche=%s skip video_id=%s (no corpus row) keys=%s err=%s",
                niche_name,
                vid,
                list(analysis.keys())[:14],
                (str(err)[:400] if err is not None else None),
            )
        else:
            try:
                from getviews_pipeline.pattern_fingerprint import (
                    compute_and_upsert_pattern,
                )

                pattern_id = await compute_and_upsert_pattern(
                    client, analysis.get("analysis") or {}, niche_id,
                )
                if pattern_id:
                    row["pattern_id"] = pattern_id
            except Exception as exc:
                logger.warning("[corpus] pattern fingerprint failed: %s", exc)
            rows.append(row)
            if frame_urls:
                frame_urls_by_video_id[row["video_id"]] = frame_urls

    if rows and r2_configured():
        video_rows = [r for r in rows if r.get("content_type", "video") == "video" and r.get("video_url")]

        for row in video_rows:
            pre_frames = frame_urls_by_video_id.get(row["video_id"], [])
            if pre_frames:
                row["frame_urls"] = pre_frames
                logger.info("[corpus] %s — %d frame(s) from shared download", row["video_id"], len(pre_frames))

        logger.info(
            "[corpus] niche=%s — R2 upload: %d video clips + %d thumbnails",
            niche_name,
            len(video_rows),
            len(rows),
        )

        video_upload_tasks = [
            download_and_upload_video(
                [row["video_url"]],
                row["video_id"],
            )
            for row in video_rows
        ]
        thumb_tasks = [
            download_and_upload_thumbnail(
                row.get("thumbnail_url") or "",
                row["video_id"],
            )
            for row in rows
        ]

        video_results, thumb_results = await asyncio.gather(
            asyncio.gather(*video_upload_tasks, return_exceptions=True),
            asyncio.gather(*thumb_tasks, return_exceptions=True),
        )

        for row, video_result in zip(video_rows, video_results):
            if isinstance(video_result, str) and video_result:
                row["video_url"] = video_result
                logger.info("[corpus] %s — video uploaded to R2: %s", row["video_id"], video_result)
            elif isinstance(video_result, Exception):
                logger.warning("[corpus] video upload error for %s: %s", row["video_id"], video_result)

        for row, thumb_result in zip(rows, thumb_results):
            if isinstance(thumb_result, str) and thumb_result:
                row["thumbnail_url"] = thumb_result
                logger.info("[corpus] %s — thumbnail uploaded to R2: %s", row["video_id"], thumb_result)
            elif isinstance(thumb_result, Exception):
                logger.warning("[corpus] thumbnail upload error for %s: %s", row["video_id"], thumb_result)

    if rows:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: _upsert_rows_sync(client, rows)
            )
            result.inserted += len(rows)
            logger.info("[corpus] niche=%s — upserted %d rows", niche_name, len(rows))

            for row in rows:
                row_hashtags: list[str] = row.get("hashtags") or []
                if row_hashtags:
                    await learn_hashtag_mappings(
                        video_hashtags=row_hashtags,
                        niche_id=niche_id,
                        niche_source="corpus_batch",
                        client=client,
                    )
        except Exception as exc:
            logger.error("[corpus] niche=%s upsert failed: %s", niche_name, exc)
            result.failed += len(rows)
            result.errors.append(f"upsert: {exc}")

    return result


# ── Per-niche ingest ─────────────────────────────────────────────────────────────

async def ingest_niche(
    niche: dict[str, Any],
    client: Any,
    *,
    keyword_pages_override: int | None = None,
    videos_per_niche_override: int | None = None,
    carousels_per_niche_override: int | None = None,
    hashtag_yields_for_niche: dict[str, int] | None = None,
) -> IngestResult:
    niche_id: int = niche["id"]
    niche_name: str = niche.get("name_en") or niche.get("name_vn") or str(niche_id)
    result = IngestResult(niche_id=niche_id, niche_name=niche_name)

    logger.info("[corpus] niche=%s id=%d — fetching pool", niche_name, niche_id)

    try:
        pool = await _fetch_niche_pool(
            niche,
            keyword_pages=keyword_pages_override,
            hashtag_yields=hashtag_yields_for_niche,
        )
    except Exception as exc:
        logger.error("[corpus] niche=%s pool fetch failed: %s", niche_name, exc)
        result.errors.append(f"pool_fetch: {exc}")
        result.failed += 1
        return result

    existing_ids = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _existing_video_ids_sync(client, niche_id)
    )

    if CORPUS_LEGACY_CAROUSEL_HASHTAG_FETCH:
        carousel_pool = await _fetch_carousel_pool(niche)
    else:
        carousel_pool = _carousel_pool_from_merged_video_pool(
            pool, niche_name=niche_name
        )

    # ── Quality gates ────────────────────────────────────────────────────────────
    # Shared helper — applies Gates 3+4 (Vietnamese creator/caption checks)
    def _passes_vn_gates(a: dict[str, Any], vid: str) -> bool:
        author = a.get("author") or {}
        region = str(author.get("region") or "").upper()
        if region and region not in ("VN", ""):
            logger.debug("[corpus] skip %s — region=%s (not VN)", vid, region)
            return False
        if not region:
            desc = str(a.get("desc") or "")
            if desc and not _has_vietnamese_chars(desc):
                logger.debug("[corpus] skip %s — no Vietnamese chars in caption and region unknown", vid)
                return False
        return True

    # ── Video candidates ─────────────────────────────────────────────────────────
    candidates = []
    for a in pool:
        vid = str(a.get("aweme_id", "") or "")
        if vid in existing_ids:
            continue

        stats = a.get("statistics") or {}
        play_count = int(stats.get("play_count") or stats.get("playCount") or 0)

        # Gate 1: views must be above zero (no engagement data at all)
        if play_count == 0:
            logger.debug("[corpus] skip %s — play_count=0 (no real stats)", vid)
            continue

        # Gate 2: minimum view floor — filters out low-reach content
        if play_count < BATCH_MIN_VIEWS:
            logger.debug("[corpus] skip %s — play_count=%d < min=%d", vid, play_count, BATCH_MIN_VIEWS)
            continue

        # Gate 3+4: Vietnamese creator
        if not _passes_vn_gates(a, vid):
            continue

        # Gate 5: minimum engagement rate — filters out dead content that got views but no engagement
        likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)
        comments = int(stats.get("comment_count") or stats.get("commentCount") or 0)
        shares = int(stats.get("share_count") or stats.get("shareCount") or 0)
        er = _safe_engagement_rate(
            er_from_analysis=None,
            views=play_count,
            likes=likes,
            comments=comments,
            shares=shares,
        )
        if er < BATCH_MIN_ER:
            logger.debug("[corpus] skip %s — ER=%.2f%% < min=%.2f%%", vid, er, BATCH_MIN_ER)
            continue

        candidates.append(a)

    # Sort by play_count desc (most-viewed first) for quality signal
    candidates.sort(
        key=lambda a: int((a.get("statistics") or {}).get("play_count", 0) or 0),
        reverse=True,
    )
    vpn = videos_per_niche_override if videos_per_niche_override is not None else BATCH_VIDEOS_PER_NICHE
    candidates = candidates[:vpn]

    # ── Carousel candidates ──────────────────────────────────────────────────────
    # Carousel quality gates differ from video:
    # - play_count is unreliable for carousels in feed responses (often 0) — use digg_count instead
    # - Gate 1 (play_count > 0) is skipped; Gate 2 replaced with min-likes floor
    # - ER gate is skipped because we have no reliable view denominator
    carousel_candidates = []
    for a in carousel_pool:
        vid = str(a.get("aweme_id", "") or "")
        if vid in existing_ids:
            continue
        # Skip carousels already picked as video candidates (de-dup)
        if any(str(c.get("aweme_id", "")) == vid for c in candidates):
            continue

        stats = a.get("statistics") or {}
        likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)

        # Carousel Gate: minimum likes floor — proxy for reach when play_count is missing
        if likes < BATCH_CAROUSEL_MIN_LIKES:
            logger.debug("[corpus] skip carousel %s — likes=%d < min=%d", vid, likes, BATCH_CAROUSEL_MIN_LIKES)
            continue

        # Gate 3+4: Vietnamese creator
        if not _passes_vn_gates(a, vid):
            continue

        carousel_candidates.append(a)

    # Sort carousels by likes desc
    carousel_candidates.sort(
        key=lambda a: int((a.get("statistics") or {}).get("digg_count", 0) or 0),
        reverse=True,
    )
    cpn = carousels_per_niche_override if carousels_per_niche_override is not None else BATCH_CAROUSELS_PER_NICHE
    carousel_candidates = carousel_candidates[:cpn]

    if carousel_candidates:
        logger.info(
            "[corpus] niche=%s — %d carousel candidates added (min_likes=%d)",
            niche_name, len(carousel_candidates), BATCH_CAROUSEL_MIN_LIKES,
        )

    # Merge video + carousel candidates
    candidates = candidates + carousel_candidates

    if not candidates:
        vdiag = _video_pool_gate_diagnostics(pool, existing_ids)
        logger.info(
            "[corpus] niche=%s — no ingestible candidates this run "
            "(misleading legacy label was 'all posts already indexed'). "
            "carousel_raw_pool=%d video_gate_diag=%s",
            niche_name,
            len(carousel_pool),
            vdiag,
        )
        return result

    id_strs = [str(c.get("aweme_id", "") or "") for c in candidates if c.get("aweme_id") is not None]
    preview = ",".join(id_strs[:60])
    if len(id_strs) > 60:
        preview = f"{preview},...(+{len(id_strs) - 60} more)"
    logger.info(
        "[corpus] niche=%s — candidate_aweme_ids n=%d: %s",
        niche_name,
        len(id_strs),
        preview,
    )

    sub = await _ingest_candidate_awemes(client, niche_id, niche_name, candidates)
    result.inserted = sub.inserted
    result.skipped = sub.skipped
    result.failed = sub.failed
    result.errors = sub.errors
    return result


def _existing_video_ids_sync(client: Any, niche_id: int) -> set[str]:
    result = (
        client.table("video_corpus")
        .select("video_id")
        .eq("niche_id", niche_id)
        .execute()
    )
    return {row["video_id"] for row in (result.data or [])}


def _upsert_rows_sync(client: Any, rows: list[dict[str, Any]]) -> None:
    client.table("video_corpus").upsert(rows, on_conflict="video_id").execute()


# ── Materialized view refresh ────────────────────────────────────────────────────

def _refresh_niche_intelligence_sync(client: Any) -> None:
    """Refresh niche_intelligence materialized view via RPC."""
    client.rpc("refresh_niche_intelligence", {}).execute()


async def _refresh_niche_intelligence(client: Any) -> bool:
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: _refresh_niche_intelligence_sync(client)
        )
        logger.info("[corpus] niche_intelligence materialized view refreshed")
        return True
    except Exception as exc:
        logger.error("[corpus] materialized view refresh failed: %s", exc)
        return False


async def run_reingest_video_items(
    items: list[dict[str, Any]],
    *,
    refresh_mv: bool = True,
) -> BatchSummary:
    """Re-fetch posts by TikTok ``video_id`` / ``aweme_id`` and run analyze+upsert.

    Each item is ``{"video_id": "<aweme_id>", "niche_id": <int>}`` (``aweme_id`` alias allowed).
    Does not run Sunday weekly analytics — only analyze/upsert + optional MV refresh.
    """
    from collections import defaultdict

    summary = BatchSummary()
    client = _service_client()

    seen: set[tuple[str, int]] = set()
    ordered: list[tuple[str, int]] = []
    for it in items:
        vid = str(it.get("video_id") or it.get("aweme_id") or "").strip()
        raw_nid = it.get("niche_id")
        if not vid or raw_nid is None:
            continue
        try:
            nid = int(raw_nid)
        except (TypeError, ValueError):
            continue
        key = (vid, nid)
        if key in seen:
            continue
        seen.add(key)
        ordered.append((vid, nid))

    if len(ordered) > 400:
        logger.warning("[corpus] reingest capped from %d to 400 items", len(ordered))
        ordered = ordered[:400]

    if not ordered:
        logger.warning("[corpus] reingest: no valid items")
        return summary

    niches: list[dict[str, Any]] = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _fetch_niches_sync(client)
    )
    niches_by_id = {int(n["id"]): n for n in niches}

    by_niche: dict[int, list[str]] = defaultdict(list)
    for vid, nid in ordered:
        by_niche[nid].append(vid)

    with ensemble.ed_batch_metering() as batch_id:
        for niche_id, ids in by_niche.items():
            niche = niches_by_id.get(niche_id)
            if not niche:
                logger.error("[corpus] reingest: unknown niche_id=%s", niche_id)
                summary.total_failed += len(ids)
                summary.niches_processed += 1
                summary.niche_results.append({
                    "niche_id": niche_id,
                    "niche_name": str(niche_id),
                    "inserted": 0,
                    "skipped": 0,
                    "failed": len(ids),
                    "errors": ["unknown niche_id"],
                })
                continue

            niche_name = niche.get("name_en") or niche.get("name_vn") or str(niche_id)
            candidates: list[dict[str, Any]] = []
            missing = 0
            for i in range(0, len(ids), REINGEST_MULTI_CHUNK):
                chunk = ids[i : i + REINGEST_MULTI_CHUNK]
                raw_posts = await ensemble.fetch_post_multi_info(chunk)
                fresh_by_id: dict[str, dict[str, Any]] = {}
                for post in raw_posts:
                    detail = post.get("aweme_detail") or post
                    vid_id = str(detail.get("aweme_id") or "")
                    if vid_id:
                        fresh_by_id[vid_id] = detail
                for vid in chunk:
                    detail = fresh_by_id.get(vid)
                    if not detail:
                        missing += 1
                        continue
                    candidates.append(detail)

            if missing:
                logger.warning(
                    "[corpus] reingest niche=%s — EnsembleData missing %d/%d aweme payloads",
                    niche_name,
                    missing,
                    len(ids),
                )

            sub = await _ingest_candidate_awemes(client, niche_id, niche_name, candidates)
            sub_failed = sub.failed + missing
            err_extra = ([f"multi_info_missing:{missing}"] if missing else [])
            summary.total_inserted += sub.inserted
            summary.total_skipped += sub.skipped
            summary.total_failed += sub_failed
            summary.niches_processed += 1
            summary.niche_results.append({
                "niche_id": niche_id,
                "niche_name": niche_name,
                "inserted": sub.inserted,
                "skipped": sub.skipped,
                "failed": sub_failed,
                "errors": sub.errors + err_extra,
            })

        if refresh_mv:
            summary.materialized_view_refreshed = await _refresh_niche_intelligence(client)
        else:
            summary.materialized_view_refreshed = False

        logger.info(
            ensemble.format_ed_meter_summary(
                batch_id=batch_id,
                niches=summary.niches_processed,
                inserted=summary.total_inserted,
                skipped=summary.total_skipped,
                failed=summary.total_failed,
                label="reingest_videos",
                theoretical_pool=None,
            )
        )

    return summary


# ── Main batch entry point ───────────────────────────────────────────────────────

async def run_batch_ingest(
    niche_ids: list[int] | None = None,
    *,
    deep_pool: bool = False,
) -> BatchSummary:
    """Run full batch ingest. Optionally restrict to specific niche_ids.

    Args:
        niche_ids: If provided, only ingest these niche IDs. Otherwise all niches.
        deep_pool: When True, widen keyword pagination and per-niche caps so a follow-up
            run can overlap more of a prior candidate set (e.g. after a model outage).

    Returns:
        BatchSummary with per-niche counts and materialized view status.
    """
    summary = BatchSummary()
    client = _service_client()

    niches: list[dict[str, Any]] = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _fetch_niches_sync(client)
    )

    if niche_ids:
        niches = [n for n in niches if n["id"] in niche_ids]

    if not niches:
        logger.warning("[corpus] No niches to process")
        return summary

    kw: int | None = None
    vpn: int | None = None
    cpn: int | None = None
    if deep_pool:
        kw = min(BATCH_KEYWORD_PAGES * 3, 8)
        vpn = min(BATCH_VIDEOS_PER_NICHE * 2, 40)
        cpn = min(BATCH_CAROUSELS_PER_NICHE * 2, 12)
        logger.info(
            "[corpus] deep_pool ingest: keyword_pages=%d videos_per_niche=%d carousels=%d",
            kw,
            vpn,
            cpn,
        )

    logger.info("[corpus] Starting batch ingest for %d niches", len(niches))

    eff_kw_pages = kw if kw is not None else BATCH_KEYWORD_PAGES
    theory_pool = theoretical_ed_pool_requests(
        len(niches),
        keyword_pages=eff_kw_pages,
        hashtag_limit=BATCH_HASHTAG_FETCH_LIMIT,
        legacy_carousel_second_hashtag_pass=CORPUS_LEGACY_CAROUSEL_HASHTAG_FETCH,
    )
    logger.info("[corpus] theoretical_ed_pool %s", theory_pool["formula"])

    hashtag_yields_all = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _load_hashtag_yields_all_sync(client)
    )

    with ensemble.ed_batch_metering() as batch_id, ensemble.ed_call_site("corpus_ingest.batch"):
        # Process niches in batches of BATCH_CONCURRENCY to avoid overwhelming APIs
        for i in range(0, len(niches), BATCH_CONCURRENCY):
            batch = niches[i : i + BATCH_CONCURRENCY]
            results = await asyncio.gather(
                *[
                    ingest_niche(
                        n,
                        client,
                        keyword_pages_override=kw,
                        videos_per_niche_override=vpn,
                        carousels_per_niche_override=cpn,
                        hashtag_yields_for_niche=hashtag_yields_all.get(int(n["id"]), {}),
                    )
                    for n in batch
                ],
                return_exceptions=True,
            )
            for res in results:
                if isinstance(res, Exception):
                    logger.error("[corpus] niche ingest raised: %s", res)
                    summary.total_failed += 1
                    continue
                summary.total_inserted += res.inserted
                summary.total_skipped += res.skipped
                summary.total_failed += res.failed
                summary.niches_processed += 1
                summary.niche_results.append({
                    "niche_id": res.niche_id,
                    "niche_name": res.niche_name,
                    "inserted": res.inserted,
                    "skipped": res.skipped,
                    "failed": res.failed,
                    "errors": res.errors,
                })

        # Refresh materialized view once all niches are done
        summary.materialized_view_refreshed = await _refresh_niche_intelligence(client)

        # Daily: refresh Video Đáng Học rankings
        try:
            from getviews_pipeline.video_dang_hoc import run_video_dang_hoc

            vdh_result = await run_video_dang_hoc(client)
            logger.info(
                "[video_dang_hoc] bung_no=%d dang_hot=%d errors=%s",
                vdh_result.bung_no_count,
                vdh_result.dang_hot_count,
                vdh_result.errors or "none",
            )
        except Exception as exc:
            logger.error("[video_dang_hoc] Video Đáng Học refresh failed (non-fatal): %s", exc)

        # Daily: Layer 0B — emerging sound insights
        try:
            from getviews_pipeline.layer0_sound import run_sound_insights

            l0b_result = await run_sound_insights(client)
            logger.info("[layer0b] sounds_analyzed=%d", l0b_result.get("analyzed", 0))
        except Exception as exc:
            logger.error("[layer0b] Sound insight failed (non-fatal): %s", exc)

        # Weekly analytics (Sunday only — day 6 in Python's weekday())
        today = date.today()
        is_sunday = today.weekday() == 6
        if is_sunday:
            logger.info(
                "[corpus] Sunday — running weekly analytics (trend_velocity + P1-7 + P1-8)..."
            )
            await _run_weekly_analytics(client)

        logger.info(
            "[corpus] Batch complete — inserted=%d skipped=%d failed=%d niches=%d mv_refreshed=%s",
            summary.total_inserted,
            summary.total_skipped,
            summary.total_failed,
            summary.niches_processed,
            summary.materialized_view_refreshed,
        )
        logger.info(
            ensemble.format_ed_meter_summary(
                batch_id=batch_id,
                niches=len(niches),
                inserted=summary.total_inserted,
                skipped=summary.total_skipped,
                failed=summary.total_failed,
                label="batch_ingest",
                theoretical_pool=theory_pool,
            )
        )
    return summary


async def _run_weekly_analytics(client: Any) -> None:
    """Run trend velocity + creator velocity + breakout multiplier + signal grading (Sunday only).

    Non-fatal: errors are logged but do not fail the batch ingest.
    """
    try:
        from getviews_pipeline.trend_velocity import run_trend_velocity
        tv_result = await run_trend_velocity(client)
        logger.info(
            "[tv] rows_upserted=%d niches=%d errors=%s",
            tv_result.rows_upserted,
            tv_result.niches_processed,
            tv_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[tv] Trend velocity computation failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.batch_analytics import run_analytics
        analytics_result = await run_analytics(client)
        logger.info(
            "[analytics] creators_updated=%d videos_updated=%d errors=%s",
            analytics_result.creators_updated,
            analytics_result.videos_updated,
            analytics_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[analytics] Weekly analytics failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.signal_classifier import run_signal_grading
        signal_result = await run_signal_grading(client)
        logger.info(
            "[signal] grades_written=%d niches=%d errors=%s",
            signal_result.grades_written,
            signal_result.niches_processed,
            signal_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[signal] Signal grading failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.trending_cards import run_trending_cards

        tc_result = await run_trending_cards(client)
        logger.info(
            "[trending_cards] cards_written=%d niches=%d errors=%s",
            tc_result.cards_written,
            tc_result.niches_processed,
            tc_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[trending_cards] Trending cards generation failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.cross_creator import run_cross_creator_detection

        cc_result = await run_cross_creator_detection(client)
        logger.info(
            "[cross_creator] patterns_written=%d niches_affected=%d errors=%s",
            cc_result.patterns_written,
            cc_result.niches_affected,
            cc_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[cross_creator] Cross-creator detection failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.sound_aggregator import run_sound_aggregation

        sa_result = await run_sound_aggregation(client)
        logger.info(
            "[sound_aggregation] upserted=%d",
            sa_result.get("upserted", 0),
        )
    except Exception as exc:
        logger.error("[sound_aggregation] Sound aggregation failed (non-fatal): %s", exc)

    # --- Layer 0: Intelligence Extraction (the brain) ---
    # Runs LAST — reads from video_corpus + signal_grades + trending_sounds
    # Non-fatal: if Layer 0 fails, dashboard still shows statistics (without mechanism)

    # Layer 0D — Trending Hashtag Discovery (runs first so new tags feed 0A)
    try:
        from getviews_pipeline.layer0_hashtag import run_hashtag_discovery
        l0d_result = await run_hashtag_discovery(client)
        logger.info(
            "[layer0d] candidates=%d added=%d map_written=%d candidates_saved=%d stale=%d skipped=%d errors=%s",
            l0d_result.get("candidates_found", 0),
            l0d_result.get("added", 0),
            l0d_result.get("map_written", 0),
            l0d_result.get("candidates_saved", 0),
            l0d_result.get("stale_signals", 0),
            l0d_result.get("skipped", 0),
            l0d_result.get("errors") or "none",
        )
    except Exception as exc:
        logger.error("[layer0d] Hashtag discovery failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.layer0_niche import run_niche_insights
        l0a_result = await run_niche_insights(client)
        logger.info(
            "[layer0a] insights=%d skipped=%d errors=%s",
            l0a_result.insights_written,
            l0a_result.niches_skipped,
            l0a_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[layer0a] Niche insight generation failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.layer0_migration import run_cross_niche_migration
        l0c_result = await run_cross_niche_migration(client)
        logger.info("[layer0c] migrations=%d", l0c_result.get("migrations_found", 0))
    except Exception as exc:
        logger.error("[layer0c] Cross-niche migration failed (non-fatal): %s", exc)


def _fetch_niches_sync(client: Any) -> list[dict[str, Any]]:
    result = (
        client.table("niche_taxonomy")
        .select("id, name_en, name_vn, signal_hashtags")
        .execute()
    )
    return result.data or []
