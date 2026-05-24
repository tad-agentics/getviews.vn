"""Shared TikTok URL resolution + SSRF-guarded short-link following.

Lives in the pipeline layer (not ``routers/``) so both the ``/stream``
router and the ``/answer`` compare path can resolve short links without a
backwards router→pipeline import. The SSRF guard is exercised by
``tests/test_short_url_ssrf.py``.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from getviews_pipeline.config import TIKTOK_ALLOWED_HOSTS

logger = logging.getLogger(__name__)

SHORT_TIKTOK_HOSTS = {"vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com"}
# Hosts the resolved (post-redirect) URL must land on. Superset of
# ``TIKTOK_ALLOWED_HOSTS`` plus the short-link hosts, since some
# resolves stay on the short host (rare). Anything else = SSRF guard
# trips.
RESOLVED_TIKTOK_HOSTS = TIKTOK_ALLOWED_HOSTS | SHORT_TIKTOK_HOSTS


def is_short_tiktok_url(url: str) -> bool:
    try:
        return urlparse(url).netloc.lower() in SHORT_TIKTOK_HOSTS
    except Exception:
        return False


def resolve_short_url(url: str, timeout: float = 8.0) -> str:
    """Follow redirects on a short TikTok URL and return the final URL.

    SSRF guard: ``follow_redirects=True`` would otherwise let an
    attacker craft a short link whose final ``Location`` points at
    ``169.254.169.254`` (cloud metadata) or any internal hostname.
    Every hop in the chain — including the terminal one — must
    resolve to a host in ``RESOLVED_TIKTOK_HOSTS``; otherwise we
    abort and return the original short URL (downstream pipelines
    will surface a "không phải TikTok URL" error).
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            current = url
            for _ in range(5):
                resp = client.head(current, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location")
                    if not location:
                        break
                    nxt = str(httpx.URL(current).join(location))
                    nxt_host = urlparse(nxt).netloc.lower()
                    if nxt_host not in RESOLVED_TIKTOK_HOSTS:
                        logger.warning(
                            "[short_url] redirect target %s rejected (host=%s) — using original",
                            nxt,
                            nxt_host,
                        )
                        return url
                    current = nxt
                    continue
                break
            logger.info("[short_url] resolved %s → %s", url, current)
            return current
    except Exception as exc:
        logger.warning("[short_url] could not resolve %s: %s — using original", url, exc)
        return url


def pick_two_video_urls(urls: list[str]) -> tuple[str | None, str | None]:
    """Pick the first two video-style URLs, in source order, for the
    compare pipeline. Falls back to the first two of any ordering when
    fewer than two video-style matches are found — the caller surfaces a
    "missing_video_url"-style error if either side fails to resolve.
    Mirrors the single-URL "video > photo > short-link > anything"
    precedence per slot."""
    video_like = [
        u for u in urls
        if "/video/" in u.lower()
        or "/photo/" in u.lower()
        or is_short_tiktok_url(u)
    ]
    pool = video_like if len(video_like) >= 2 else urls
    a = pool[0] if len(pool) >= 1 else None
    b = pool[1] if len(pool) >= 2 else None
    return a, b
