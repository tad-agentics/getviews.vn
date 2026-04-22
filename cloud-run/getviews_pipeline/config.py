"""Environment variables, constants, and CDN headers for the GetViews pipeline."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Supabase auth — ES256 JWKS (stateless JWT validation, no shared secret)
SUPABASE_JWKS_URL = os.environ.get(
    "SUPABASE_JWKS_URL",
    "https://lzhiqnxfveqttsujebiv.supabase.co/auth/v1/.well-known/jwks.json",
)
# Legacy fallback: if SUPABASE_JWT_SECRET is set (HS256), use it instead of JWKS ES256
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")

ENSEMBLEDATA_API_TOKEN = os.environ.get("ENSEMBLE_DATA_API_KEY") or os.environ.get("ENSEMBLEDATA_API_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Default matches cloud-run/.env.example — gemini-2.0-flash-001 is no longer served (404).
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
# §11 hybrid: extraction (Flash-Lite) vs synthesis (Flash) vs knowledge (Flash-Lite).
GEMINI_EXTRACTION_MODEL = os.environ.get("GEMINI_EXTRACTION_MODEL", "").strip() or GEMINI_MODEL
GEMINI_SYNTHESIS_MODEL = os.environ.get("GEMINI_SYNTHESIS_MODEL", "").strip() or GEMINI_MODEL
GEMINI_KNOWLEDGE_MODEL = (
    os.environ.get("GEMINI_KNOWLEDGE_MODEL", "").strip() or GEMINI_EXTRACTION_MODEL
)
# Text-only second step; defaults to GEMINI_SYNTHESIS_MODEL.
GEMINI_DIAGNOSIS_MODEL = os.environ.get("GEMINI_DIAGNOSIS_MODEL", "").strip() or None
# Intent classification — text-only, JSON output, must be fast (<300ms).
# Defaults to GEMINI_KNOWLEDGE_MODEL (Flash-Lite) for low latency.
GEMINI_INTENT_MODEL = os.environ.get("GEMINI_INTENT_MODEL", "").strip() or GEMINI_KNOWLEDGE_MODEL
# Comma-separated fallback model names (optional), tried in order after primary fails.
GEMINI_EXTRACTION_FALLBACKS = [
    s.strip()
    for s in os.environ.get("GEMINI_EXTRACTION_FALLBACKS", "").split(",")
    if s.strip()
]
GEMINI_SYNTHESIS_FALLBACKS = [
    s.strip()
    for s in os.environ.get("GEMINI_SYNTHESIS_FALLBACKS", "").split(",")
    if s.strip()
]
GEMINI_KNOWLEDGE_FALLBACKS = [
    s.strip()
    for s in os.environ.get("GEMINI_KNOWLEDGE_FALLBACKS", "").split(",")
    if s.strip()
]
# Extraction: low temperature for deterministic transcription + scene detection.
# Synthesis: higher temperature for natural Vietnamese creative writing.
# GEMINI_TEMPERATURE is kept as a legacy override — if set, it overrides both.
_GEMINI_TEMPERATURE_LEGACY = os.environ.get("GEMINI_TEMPERATURE")
GEMINI_EXTRACTION_TEMPERATURE = float(
    _GEMINI_TEMPERATURE_LEGACY or os.environ.get("GEMINI_EXTRACTION_TEMPERATURE", "0.2")
)
GEMINI_SYNTHESIS_TEMPERATURE = float(
    _GEMINI_TEMPERATURE_LEGACY or os.environ.get("GEMINI_SYNTHESIS_TEMPERATURE", "0.8")
)
# Legacy alias — kept so existing code that imports GEMINI_TEMPERATURE still compiles.
# New code should use the split constants above.
GEMINI_TEMPERATURE = GEMINI_SYNTHESIS_TEMPERATURE
# Opt-in: low | medium | high | unspecified (empty = API default). Lower = faster video.
GEMINI_VIDEO_MEDIA_RESOLUTION = (
    os.environ.get("GEMINI_VIDEO_MEDIA_RESOLUTION", "").strip().lower()
)

ENSEMBLEDATA_BASE = "https://ensembledata.com/apis"
ENSEMBLEDATA_POST_INFO_URL = f"{ENSEMBLEDATA_BASE}/tt/post/info"
ENSEMBLEDATA_POST_MULTI_INFO_URL = f"{ENSEMBLEDATA_BASE}/tt/post/multi-info"
ENSEMBLEDATA_KEYWORD_SEARCH_URL = f"{ENSEMBLEDATA_BASE}/tt/keyword/search"
ENSEMBLEDATA_HASHTAG_POSTS_URL = f"{ENSEMBLEDATA_BASE}/tt/hashtag/posts"
ENSEMBLEDATA_USER_POSTS_URL = f"{ENSEMBLEDATA_BASE}/tt/user/posts"
ENSEMBLEDATA_USER_SEARCH_URL = f"{ENSEMBLEDATA_BASE}/tt/user/search"
# /tt/post/comments returns up to ~50 comments per aweme_id at cursor=0.
# Used on-demand only (paid intents) — cached for 7 days in
# video_corpus.comment_radar. See comment_radar.fetch_comments_for_video.
ENSEMBLEDATA_POST_COMMENTS_URL = f"{ENSEMBLEDATA_BASE}/tt/post/comments"


def _float_env(name: str, default: str) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


# ── EnsembleData metering & unit estimates ([ed-meter] logs) ─────────────────
# Override per endpoint after calibrating vs ED dashboard
# (artifacts/docs/ed-pricing-map.md).
ED_UNIT_KEYWORD_SEARCH = _float_env("ED_UNIT_KEYWORD_SEARCH", "1")
ED_UNIT_HASHTAG_POSTS = _float_env("ED_UNIT_HASHTAG_POSTS", "1")
ED_UNIT_POST_INFO = _float_env("ED_UNIT_POST_INFO", "1")
ED_UNIT_POST_MULTI_INFO = _float_env("ED_UNIT_POST_MULTI_INFO", "1")
ED_UNIT_USER_POSTS = _float_env("ED_UNIT_USER_POSTS", "1")
ED_UNIT_USER_SEARCH = _float_env("ED_UNIT_USER_SEARCH", "1")
ED_UNIT_POST_COMMENTS = _float_env("ED_UNIT_POST_COMMENTS", "1")

# Keyword search: extra author payload. Default false — set
# KEYWORD_SEARCH_AUTHOR_STATS=true if play_count is missing.
KEYWORD_SEARCH_AUTHOR_STATS = _bool_env("KEYWORD_SEARCH_AUTHOR_STATS", False)

# Carousel pool: legacy mode runs a second hashtag pass (2× hashtag cost per niche).
CORPUS_LEGACY_CAROUSEL_HASHTAG_FETCH = _bool_env("CORPUS_LEGACY_CAROUSEL_HASHTAG_FETCH", False)

# Batch-only daily request ceiling (UTC day). 0 = disabled. Prefer log-only first.
ED_BATCH_DAILY_REQUEST_MAX = int(os.environ.get("ED_BATCH_DAILY_REQUEST_MAX", "0") or "0")
ED_BATCH_BUDGET_ENFORCE = _bool_env("ED_BATCH_BUDGET_ENFORCE", False)

# Tier-3 `classify_intent_gemini` calls per UTC day. 0 = unlimited.
CLASSIFIER_GEMINI_DAILY_MAX = int(os.environ.get("CLASSIFIER_GEMINI_DAILY_MAX", "0") or "0")

# TTL cache for hot user-path ED calls (seconds). 0 = disabled.
ENSEMBLE_USER_PATH_CACHE_TTL_SEC = int(
    os.environ.get("ENSEMBLE_USER_PATH_CACHE_TTL_SEC", "300") or "300"
)
ENSEMBLE_USER_PATH_CACHE_MAX = int(
    os.environ.get("ENSEMBLE_USER_PATH_CACHE_MAX", "2000") or "2000"
)

# Adaptive hashtag fetch: minimum tags to fetch when DB yields exist (safety floor).
ADAPTIVE_HASHTAG_MIN_FETCH = int(os.environ.get("ADAPTIVE_HASHTAG_MIN_FETCH", "2") or "2")
HASHTAG_YIELD_THRESHOLD = int(os.environ.get("HASHTAG_YIELD_THRESHOLD", "1") or "1")

TIKTOK_ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "tiktok.com",
        "www.tiktok.com",
        "vm.tiktok.com",
        "m.tiktok.com",
    }
)

BATCH_MIN_URLS = 1
BATCH_MAX_URLS = 5

MAX_INLINE_SIZE_BYTES = 75 * 1024 * 1024

# Carousel: max slide positions scanned from image_post_info for CDN URLs.
CAROUSEL_EXTRACT_MAX_SLIDES = int(os.environ.get("CAROUSEL_EXTRACT_MAX_SLIDES", "35"))
# Max slides after extraction to actually download + send to Gemini (tighter cap).
CAROUSEL_MAX_SLIDES = int(os.environ.get("CAROUSEL_MAX_SLIDES", "10"))
# Skip individual slides larger than this after download (bytes).
CAROUSEL_MAX_IMAGE_BYTES = int(
    os.environ.get("CAROUSEL_MAX_IMAGE_BYTES", str(15 * 1024 * 1024))
)

CDN_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.tiktok.com/",
    "Accept": "*/*",
}

# Residential proxy for TikTok CDN downloads (video + carousel images).
# Without this, Cloud Run datacenter IPs will be blocked by TikTok.
# Format: http://user:pass@host:port
# Providers: Smartproxy, Bright Data, Oxylabs, IPRoyal
RESIDENTIAL_PROXY_URL = os.environ.get("RESIDENTIAL_PROXY_URL")

# ── Cloudflare R2 (frame + video storage) ─────────────────────────────────────
# Frames are extracted from videos at fixed timestamps and uploaded to R2.
# frame_urls in video_corpus stores the resulting public CDN URLs.
# Videos (720p/30s .mp4) are also uploaded to R2 for permanent Explore playback.
#
# Required env vars (shared for both frames and videos):
#   R2_ACCOUNT_ID        — Cloudflare account ID
#   R2_ACCESS_KEY_ID     — R2 API token access key (Object Read & Write)
#   R2_SECRET_ACCESS_KEY — R2 API token secret key
#   R2_BUCKET_NAME       — R2 bucket name (e.g. "getviews-media")
#   R2_PUBLIC_URL        — Public URL prefix for frames (e.g. "https://media.getviews.vn")
#
# Optional — separate public URL for videos (defaults to R2_PUBLIC_URL if unset):
#   R2_VIDEO_PUBLIC_URL  — Public URL prefix for videos (e.g. "https://media.getviews.vn")
#                          Videos are stored at: videos/{video_id}.mp4
#                          Frames are stored at: frames/{video_id}/{i}.png
#
# When any of the required vars is absent, R2 upload is skipped silently.
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "getviews-media")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")
# If R2_VIDEO_PUBLIC_URL is not set, falls back to R2_PUBLIC_URL.
R2_VIDEO_PUBLIC_URL = os.environ.get("R2_VIDEO_PUBLIC_URL", "").rstrip("/")

# Frame timestamps to extract (seconds from start of video).
# 0s = hook frame, 1s = after hook, 3s = body start.
FRAME_TIMESTAMPS_SEC: list[float] = [0.0, 1.0, 3.0]

FILES_API_POLL_INITIAL_SEC = 1.0
FILES_API_POLL_MAX_SEC = 8.0
FILES_API_POLL_TIMEOUT_SEC = 90.0  # upper bound; creators uploading dense 60s
                                    # videos occasionally need 40-60s to reach
                                    # ACTIVE. Was 30s, raised after "Gemini silently
                                    # times out on large videos" audit finding.

# Backward-compat aliases — keep older callers working.
FILES_API_POLL_INTERVAL_SEC = FILES_API_POLL_INITIAL_SEC
FILES_API_POLL_MAX_ATTEMPTS = int(FILES_API_POLL_TIMEOUT_SEC / FILES_API_POLL_INITIAL_SEC)

logger.info(
    "Resolved GEMINI_MODEL=%s extraction=%s synthesis=%s knowledge=%s diagnosis=%s "
    "temp_extraction=%.1f temp_synthesis=%.1f",
    GEMINI_MODEL,
    GEMINI_EXTRACTION_MODEL,
    GEMINI_SYNTHESIS_MODEL,
    GEMINI_KNOWLEDGE_MODEL,
    GEMINI_DIAGNOSIS_MODEL or GEMINI_SYNTHESIS_MODEL,
    GEMINI_EXTRACTION_TEMPERATURE,
    GEMINI_SYNTHESIS_TEMPERATURE,
)


def require_ensembledata_token() -> str:
    if not ENSEMBLEDATA_API_TOKEN:
        raise ValueError("ENSEMBLEDATA_API_TOKEN is not set")
    return ENSEMBLEDATA_API_TOKEN


def require_gemini_api_key() -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")
    return GEMINI_API_KEY
