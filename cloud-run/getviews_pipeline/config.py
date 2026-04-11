"""Environment, constants, and CDN headers for the MCP server."""

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
