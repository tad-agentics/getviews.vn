"""Environment, constants, and CDN headers for the MCP server."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

ENSEMBLEDATA_API_TOKEN = os.environ.get("ENSEMBLE_DATA_API_KEY") or os.environ.get("ENSEMBLEDATA_API_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
# §11 hybrid: extraction (Flash-Lite) vs synthesis (Flash) vs knowledge (Flash-Lite).
GEMINI_EXTRACTION_MODEL = os.environ.get("GEMINI_EXTRACTION_MODEL", "").strip() or GEMINI_MODEL
GEMINI_SYNTHESIS_MODEL = os.environ.get("GEMINI_SYNTHESIS_MODEL", "").strip() or GEMINI_MODEL
GEMINI_KNOWLEDGE_MODEL = (
    os.environ.get("GEMINI_KNOWLEDGE_MODEL", "").strip() or GEMINI_EXTRACTION_MODEL
)
# Text-only second step; defaults to GEMINI_SYNTHESIS_MODEL.
GEMINI_DIAGNOSIS_MODEL = os.environ.get("GEMINI_DIAGNOSIS_MODEL", "").strip() or None
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
# Google Gemini 3 guidance: default 1.0
GEMINI_TEMPERATURE = float(os.environ.get("GEMINI_TEMPERATURE", "1.0"))
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

FILES_API_POLL_INTERVAL_SEC = 2
FILES_API_POLL_MAX_ATTEMPTS = 30

logger.info(
    "Resolved GEMINI_MODEL=%s extraction=%s synthesis=%s knowledge=%s diagnosis=%s temp=%s",
    GEMINI_MODEL,
    GEMINI_EXTRACTION_MODEL,
    GEMINI_SYNTHESIS_MODEL,
    GEMINI_KNOWLEDGE_MODEL,
    GEMINI_DIAGNOSIS_MODEL or GEMINI_SYNTHESIS_MODEL,
    GEMINI_TEMPERATURE,
)


def require_ensembledata_token() -> str:
    if not ENSEMBLEDATA_API_TOKEN:
        raise ValueError("ENSEMBLEDATA_API_TOKEN is not set")
    return ENSEMBLEDATA_API_TOKEN


def require_gemini_api_key() -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")
    return GEMINI_API_KEY
