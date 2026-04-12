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
from datetime import date, datetime, timezone
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import analyze_aweme
from getviews_pipeline.helpers import filter_recency, merge_aweme_lists
from getviews_pipeline.r2 import download_and_extract_frames, download_and_upload_thumbnail, download_and_upload_video, r2_configured
from getviews_pipeline.runtime import get_analysis_semaphore

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

BATCH_VIDEOS_PER_NICHE = int(os.environ.get("BATCH_VIDEOS_PER_NICHE", "10"))
BATCH_RECENCY_DAYS = int(os.environ.get("BATCH_RECENCY_DAYS", "30"))
BATCH_MAX_FAILURES = int(os.environ.get("BATCH_MAX_FAILURES", "3"))
BATCH_CONCURRENCY = int(os.environ.get("BATCH_CONCURRENCY", "4"))

# Quality gates — tune via env vars without redeploying
# Minimum views a post must have to enter the corpus (filters low-reach content)
BATCH_MIN_VIEWS = int(os.environ.get("BATCH_MIN_VIEWS", "10000"))
# Minimum engagement rate % — (likes+comments+shares)/views*100 (filters dead content)
BATCH_MIN_ER = float(os.environ.get("BATCH_MIN_ER", "0.5"))
# Keyword search pages fetched per niche (each page ~20 posts, broadens candidate pool)
BATCH_KEYWORD_PAGES = int(os.environ.get("BATCH_KEYWORD_PAGES", "2"))


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

async def _fetch_keyword_pages(term: str) -> list[dict[str, Any]]:
    """Fetch BATCH_KEYWORD_PAGES pages of keyword search results, following nextCursor."""
    all_awemes: list[dict[str, Any]] = []
    cursor: int = 0
    for page in range(BATCH_KEYWORD_PAGES):
        try:
            awemes, next_cursor = await ensemble.fetch_keyword_search(
                term, period=BATCH_RECENCY_DAYS, cursor=cursor
            )
            all_awemes.extend(awemes)
            logger.debug(
                "[corpus] keyword='%s' page=%d fetched=%d next_cursor=%s",
                term, page, len(awemes), next_cursor,
            )
            if next_cursor is None or not awemes:
                break
            cursor = next_cursor
        except Exception as exc:
            logger.warning("[corpus] keyword search page %d failed for '%s': %s", page, term, exc)
            break
    return all_awemes


async def _fetch_niche_pool(niche: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch posts for a niche via keyword search (paginated) + all signal hashtags, merged + deduped."""
    term = (niche.get("name_en") or "").strip()
    hashtags: list[str] = niche.get("signal_hashtags") or []

    # Keyword search: paginated — broadens pool beyond a single page of ~20 posts
    keyword_task = _fetch_keyword_pages(term)
    # All signal_hashtags (was [:3] — now all 4)
    hashtag_tasks = [
        ensemble.fetch_hashtag_posts(ht.lstrip("#"), cursor=0)
        for ht in hashtags  # use all hashtags, not just first 3
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


def _classify_format(analysis_json: dict[str, Any], niche_id: int) -> str:
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
    if re.search(r"review|chấm điểm|đánh giá|dùng thử|trải nghiệm", combined): return "review"
    if re.search(r"cách|hướng dẫn|tutorial|mẹo|bước|step|tips", combined): return "tutorial"
    if re.search(r"vs |so sánh|versus|cái nào|nào hơn|nào tốt", combined): return "comparison"
    if re.search(r"kể chuyện|story|hồi đó|hồi nhỏ|ngày xưa|mình từng", combined): return "storytelling"
    if re.search(r"trước.*sau|before.*after|biến đổi|thay đổi.*ngày|glow.?up", combined): return "before_after"
    if re.match(r"pov[: ]", combined.lstrip()): return "pov"
    if re.search(r"outfit|ootd|biến hình|transition|mix đồ|phối đồ", combined): return "outfit_transition"
    if re.search(r"vlog|daily|thường ngày|một ngày", combined): return "vlog"
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
    dt = datetime.fromtimestamp(create_time, tz=timezone.utc)
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
    is_original_sound = bool(sound_name and str(sound_name).lower().startswith("original sound"))
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
        datetime.fromtimestamp(create_time, tz=timezone.utc).isoformat()
        if create_time else None
    )

    transcript: str = analysis_json.get("audio_transcript") or ""

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
        "content_format": _classify_format(analysis_json, niche_id),
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
    }


# ── Per-niche ingest ─────────────────────────────────────────────────────────────

async def ingest_niche(
    niche: dict[str, Any],
    client: Any,
) -> IngestResult:
    niche_id: int = niche["id"]
    niche_name: str = niche.get("name_en") or niche.get("name_vn") or str(niche_id)
    result = IngestResult(niche_id=niche_id, niche_name=niche_name)

    logger.info("[corpus] niche=%s id=%d — fetching pool", niche_name, niche_id)

    try:
        pool = await _fetch_niche_pool(niche)
    except Exception as exc:
        logger.error("[corpus] niche=%s pool fetch failed: %s", niche_name, exc)
        result.errors.append(f"pool_fetch: {exc}")
        result.failed += 1
        return result

    existing_ids = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _existing_video_ids_sync(client, niche_id)
    )

    # Quality gates — filter out low-quality / non-Vietnamese posts before analysis
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

        # Gate 3: Vietnamese creator — hard check on region when present
        author = a.get("author") or {}
        region = str(author.get("region") or "").upper()
        if region and region not in ("VN", ""):
            logger.debug("[corpus] skip %s — region=%s (not VN)", vid, region)
            continue

        # Gate 4: Vietnamese caption detection when region is absent (cheap heuristic)
        # Vietnamese uses diacritics in the Unicode Latin Extended Additional block
        if not region:
            desc = str(a.get("desc") or "")
            if desc and not _has_vietnamese_chars(desc):
                logger.debug("[corpus] skip %s — no Vietnamese chars in caption and region unknown", vid)
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
    candidates = candidates[:BATCH_VIDEOS_PER_NICHE]

    if not candidates:
        logger.info("[corpus] niche=%s — all posts already indexed, skipping", niche_name)
        return result

    logger.info("[corpus] niche=%s — analyzing %d candidates", niche_name, len(candidates))

    sem = get_analysis_semaphore()
    fa: dict[str, Any] = {}

    async def _analyze_one(aweme: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await analyze_aweme(aweme, include_diagnosis=False, full_analyses=fa)

    analyses = await asyncio.gather(*[_analyze_one(a) for a in candidates], return_exceptions=True)

    rows: list[dict[str, Any]] = []
    for aweme, analysis in zip(candidates, analyses):
        if isinstance(analysis, Exception):
            logger.warning("[corpus] analyze error: %s", analysis)
            result.failed += 1
            result.errors.append(str(analysis))
            continue
        row = _build_corpus_row(aweme, analysis, niche_id)
        if row is None:
            result.skipped += 1
        else:
            rows.append(row)

    # R2 upload: for each video row, concurrently:
    #   a) Download short clip → extract frames → upload frame PNGs (frame_urls)
    #   b) Download 30s clip → upload full .mp4 → store permanent video_url
    #   c) Download thumbnail → upload JPEG → store permanent thumbnail_url
    #      (TikTok CDN signed URLs expire within hours; R2 copy is permanent and free)
    # Failures are non-fatal — frame_urls stays [] and video/thumbnail_url stay as CDN URLs.
    if rows and r2_configured():
        video_rows = [r for r in rows if r.get("content_type", "video") == "video" and r.get("video_url")]
        logger.info(
            "[corpus] niche=%s — R2 upload: %d frames + %d video clips + %d thumbnails",
            niche_name,
            len(video_rows),
            len(video_rows),
            len(rows),
        )

        frame_tasks = [
            download_and_extract_frames(
                [row["video_url"]],
                row["video_id"],
            )
            for row in video_rows
        ]
        video_upload_tasks = [
            download_and_upload_video(
                [row["video_url"]],
                row["video_id"],
            )
            for row in video_rows
        ]
        # Thumbnail upload for ALL rows (including carousels that may not have video_url)
        thumb_tasks = [
            download_and_upload_thumbnail(
                row.get("thumbnail_url") or "",
                row["video_id"],
            )
            for row in rows
        ]

        frame_results, video_results, thumb_results = await asyncio.gather(
            asyncio.gather(*frame_tasks, return_exceptions=True),
            asyncio.gather(*video_upload_tasks, return_exceptions=True),
            asyncio.gather(*thumb_tasks, return_exceptions=True),
        )

        for row, frame_result, video_result in zip(video_rows, frame_results, video_results):
            if isinstance(frame_result, list) and frame_result:
                row["frame_urls"] = frame_result
                logger.info("[corpus] %s — %d frame(s) uploaded", row["video_id"], len(frame_result))
            elif isinstance(frame_result, Exception):
                logger.warning("[corpus] frame extraction error for %s: %s", row["video_id"], frame_result)

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
        except Exception as exc:
            logger.error("[corpus] niche=%s upsert failed: %s", niche_name, exc)
            result.failed += len(rows)
            result.errors.append(f"upsert: {exc}")

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


# ── Main batch entry point ───────────────────────────────────────────────────────

async def run_batch_ingest(
    niche_ids: list[int] | None = None,
) -> BatchSummary:
    """Run full batch ingest. Optionally restrict to specific niche_ids.

    Args:
        niche_ids: If provided, only ingest these niche IDs. Otherwise all niches.

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

    logger.info("[corpus] Starting batch ingest for %d niches", len(niches))

    # Process niches in batches of BATCH_CONCURRENCY to avoid overwhelming APIs
    for i in range(0, len(niches), BATCH_CONCURRENCY):
        batch = niches[i : i + BATCH_CONCURRENCY]
        results = await asyncio.gather(
            *[ingest_niche(n, client) for n in batch],
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

    # Weekly analytics (Sunday only — day 6 in Python's weekday())
    today = date.today()
    is_sunday = today.weekday() == 6
    if is_sunday:
        logger.info("[corpus] Sunday — running weekly analytics (trend_velocity + P1-7 + P1-8)...")
        await _run_weekly_analytics(client)

    logger.info(
        "[corpus] Batch complete — inserted=%d skipped=%d failed=%d niches=%d mv_refreshed=%s",
        summary.total_inserted,
        summary.total_skipped,
        summary.total_failed,
        summary.niches_processed,
        summary.materialized_view_refreshed,
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


def _fetch_niches_sync(client: Any) -> list[dict[str, Any]]:
    result = (
        client.table("niche_taxonomy")
        .select("id, name_en, name_vn, signal_hashtags")
        .execute()
    )
    return result.data or []
