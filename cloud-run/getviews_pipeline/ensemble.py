"""EnsembleData client: post info, metadata parsing, video download."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Any

import aiofiles
import httpx

from getviews_pipeline.config import (
    CAROUSEL_EXTRACT_MAX_SLIDES,
    CAROUSEL_MAX_IMAGE_BYTES,
    CDN_HEADERS,
    ENSEMBLEDATA_HASHTAG_POSTS_URL,
    ENSEMBLEDATA_KEYWORD_SEARCH_URL,
    ENSEMBLEDATA_POST_INFO_URL,
    ENSEMBLEDATA_POST_MULTI_INFO_URL,
    ENSEMBLEDATA_USER_POSTS_URL,
    require_ensembledata_token,
)
from getviews_pipeline.models import Author, ContentType, Metrics, Music, VideoMetadata

# EnsembleData echoes TikTok's mobile API. Photo carousels use aweme_type == 2; slide
# URLs live under image_post_info.images[].display_image.url_list[].
AWEME_TYPE_PHOTO_CAROUSEL = 2

logger = logging.getLogger(__name__)

_api_client: httpx.AsyncClient | None = None
_cdn_client: httpx.AsyncClient | None = None
_api_lock = asyncio.Lock()
_cdn_lock = asyncio.Lock()


async def get_api_client() -> httpx.AsyncClient:
    """Direct client for EnsembleData API calls. No proxy — not needed."""
    global _api_client
    async with _api_lock:
        if _api_client is None or _api_client.is_closed:
            _api_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0, read=120.0)
            )
        return _api_client


async def get_cdn_client() -> httpx.AsyncClient:
    """Client for TikTok CDN downloads. Uses residential proxy when configured.

    Set RESIDENTIAL_PROXY_URL in env to route through proxy, e.g.:
      http://user:pass@gate.smartproxy.com:7777
      http://user:pass@brd.superproxy.io:22225

    Without the env var, falls back to direct (works in dev, will get blocked in prod).
    """
    global _cdn_client
    async with _cdn_lock:
        if _cdn_client is None or _cdn_client.is_closed:
            proxy_url = os.environ.get("RESIDENTIAL_PROXY_URL")
            if proxy_url and not proxy_url.strip():
                proxy_url = None
            if proxy_url:
                logger.info("CDN client using residential proxy: %s", proxy_url.split("@")[-1])
            _cdn_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0, read=120.0),
                proxy=proxy_url,
            )
        return _cdn_client


def _aweme_payload_from_mapping(obj: dict[str, Any]) -> dict[str, Any]:
    """Resolve one EnsembleData post object to the aweme dict `parse_metadata` expects."""
    detail = obj.get("aweme_detail")
    if isinstance(detail, dict):
        return detail
    if obj.get("aweme_id") is not None or obj.get("video") is not None:
        return obj
    raise ValueError(
        "Unexpected EnsembleData response: post object has no aweme_detail "
        "and no aweme_id or video fields"
    )


def _extract_aweme_detail(data: Any) -> dict[str, Any]:
    """Normalize `payload['data']`.

    Supports a dict (with or without `aweme_detail`) or a list whose first
    element is the aweme object (EnsembleData list form).
    """
    if data is None:
        raise ValueError("Unexpected EnsembleData response: missing data")

    if isinstance(data, dict):
        return _aweme_payload_from_mapping(data)

    if isinstance(data, list):
        if not data:
            raise ValueError("Unexpected EnsembleData response: empty data list")
        first = data[0]
        if not isinstance(first, dict):
            raise ValueError(
                "Unexpected EnsembleData response: data[0] must be an object"
            )
        return _aweme_payload_from_mapping(first)

    raise ValueError(
        f"Unexpected EnsembleData response: data must be dict or list, got {type(data).__name__}"
    )


def _ensembledata_error_message(code: int) -> str | None:
    match code:
        case 491:
            return "Invalid or missing API token — check ENSEMBLEDATA_API_TOKEN"
        case 492:
            return "Account email not verified — verify the EnsembleData account"
        case 493:
            return "Subscription expired — renew EnsembleData plan"
        case 495:
            return "Daily unit limit exhausted — upgrade plan or wait until midnight UTC"
        case _:
            return None


async def fetch_post_info(url: str) -> dict[str, Any]:
    """Fetch TikTok post info; return aweme_detail dict."""
    is_photo_url = "/photo/" in url
    if is_photo_url:
        logger.info("[carousel] /photo/ URL detected — expecting aweme_type=2: %s", url)

    token = require_ensembledata_token()
    client = await get_api_client()
    r = await client.get(
        ENSEMBLEDATA_POST_INFO_URL,
        params={"url": url, "token": token},
    )
    msg = _ensembledata_error_message(r.status_code)
    if msg:
        raise ValueError(msg)

    try:
        payload = r.json()
    except Exception as e:
        raise ValueError(
            f"EnsembleData returned non-JSON response (status {r.status_code})"
        ) from e

    if isinstance(payload, dict):
        raw_code = payload.get("code", payload.get("error_code"))
        if raw_code is not None:
            try:
                code = int(raw_code)
            except (TypeError, ValueError):
                code = -1
            msg = _ensembledata_error_message(code)
            if msg:
                raise ValueError(msg)

    if r.status_code != 200:
        r.raise_for_status()

    if not isinstance(payload, dict):
        raise ValueError("Unexpected EnsembleData response: not a JSON object")

    aweme_detail = _extract_aweme_detail(payload.get("data"))

    if is_photo_url:
        aweme_type = aweme_detail.get("aweme_type")
        has_ipi = bool(
            isinstance(aweme_detail.get("image_post_info"), dict)
            and aweme_detail["image_post_info"].get("images")
        )
        logger.info(
            "[carousel] ED response for /photo/ URL — aweme_type=%s image_post_info.images=%s",
            aweme_type,
            has_ipi,
        )
        # URL-based type override: if ED did not set aweme_type=2 but the URL path is
        # /photo/, treat it as a carousel. Carousel detection normally relies on
        # aweme_type or image_post_info.images; some ED responses omit aweme_type
        # for photo posts while still including image_post_info.images.
        if aweme_type != AWEME_TYPE_PHOTO_CAROUSEL and not has_ipi:
            logger.warning(
                "[carousel] /photo/ URL but aweme_type=%s and no image_post_info — "
                "ED may not recognize /photo/ path format; setting _photo_url_hint=True",
                aweme_type,
            )
        # Always tag with hint so detect_content_type can use URL as tiebreaker.
        aweme_detail["_photo_url_hint"] = True

    return aweme_detail


async def _ensemble_get(path_url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET EnsembleData API; return parsed JSON object."""
    token = require_ensembledata_token()
    client = await get_api_client()
    q = {**params, "token": token}
    r = await client.get(path_url, params=q)
    msg = _ensembledata_error_message(r.status_code)
    if msg:
        raise ValueError(msg)
    try:
        payload = r.json()
    except Exception as e:
        raise ValueError(
            f"EnsembleData returned non-JSON response (status {r.status_code})"
        ) from e
    if isinstance(payload, dict):
        raw_code = payload.get("code", payload.get("error_code"))
        if raw_code is not None:
            try:
                code = int(raw_code)
            except (TypeError, ValueError):
                code = -1
            msg = _ensembledata_error_message(code)
            if msg:
                raise ValueError(msg)
    if r.status_code != 200:
        r.raise_for_status()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected EnsembleData response: not a JSON object")
    return payload


def aweme_from_feed_item(item: Any) -> dict[str, Any] | None:
    """Normalize keyword/hashtag/user feed item to aweme_detail-shaped dict."""
    if not isinstance(item, dict):
        return None
    ai = item.get("aweme_info")
    if isinstance(ai, dict) and (ai.get("aweme_id") is not None or ai.get("video") is not None):
        return ai
    if item.get("aweme_id") is not None or item.get("video") is not None:
        return item
    return None


def iter_awemes_from_search_payload(data: Any) -> list[dict[str, Any]]:
    """Extract list of aweme dicts from keyword/hashtag ``data`` field."""
    if data is None:
        return []
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, list):
            raw_items = inner
        else:
            return []
    else:
        return []
    out: list[dict[str, Any]] = []
    for item in raw_items:
        a = aweme_from_feed_item(item)
        if a:
            out.append(a)
    return out


async def fetch_keyword_search(
    keyword: str,
    *,
    period: int = 30,
    sorting: int = 1,
    cursor: int = 0,
    country: str = "vn",
) -> tuple[list[dict[str, Any]], int | None]:
    """TikTok keyword search; ``sorting`` 1 ≈ likes/engagement. Returns (awemes, next_cursor).

    Defaults to country="vn" so corpus stays Vietnamese-creator focused.
    get_author_stats=True ensures aweme.statistics includes play_count.
    """
    kw = keyword.strip().lstrip("#")
    if not kw:
        raise ValueError("keyword search requires a non-empty keyword")
    payload = await _ensemble_get(
        ENSEMBLEDATA_KEYWORD_SEARCH_URL,
        {
            "name": kw,
            "period": period,
            "sorting": sorting,
            "cursor": cursor,
            "country": country.lower(),
            "match_exactly": "False",
            "get_author_stats": "True",
        },
    )
    data = payload.get("data")
    awemes = iter_awemes_from_search_payload(data)
    next_cursor = None
    if isinstance(data, dict) and data.get("nextCursor") is not None:
        try:
            next_cursor = int(data["nextCursor"])
        except (TypeError, ValueError):
            next_cursor = None
    return awemes, next_cursor


async def fetch_hashtag_posts(
    hashtag: str,
    *,
    cursor: int = 0,
) -> tuple[list[dict[str, Any]], int | None]:
    """Hashtag feed chunk (~20 posts). ``name`` without #."""
    tag = hashtag.strip().lstrip("#")
    if not tag:
        raise ValueError("hashtag posts requires a non-empty name")
    payload = await _ensemble_get(
        ENSEMBLEDATA_HASHTAG_POSTS_URL,
        {"name": tag, "cursor": cursor},
    )
    data = payload.get("data")
    awemes = iter_awemes_from_search_payload(data)
    next_cursor = None
    if isinstance(data, dict) and data.get("nextCursor") is not None:
        try:
            next_cursor = int(data["nextCursor"])
        except (TypeError, ValueError):
            next_cursor = None
    return awemes, next_cursor


async def fetch_user_posts(
    username: str,
    *,
    depth: int = 1,
    start_cursor: int = 0,
) -> list[dict[str, Any]]:
    """Recent posts for ``username`` (no @)."""
    u = username.strip().lstrip("@")
    if not u:
        raise ValueError("user posts requires a username")
    payload = await _ensemble_get(
        ENSEMBLEDATA_USER_POSTS_URL,
        {
            "username": u,
            "depth": depth,
            "start_cursor": start_cursor,
            "new_version": "False",
            "download_video": "False",
        },
    )
    data = payload.get("data")
    return iter_awemes_from_search_payload(data)


async def fetch_post_multi_info(aweme_ids: list[str]) -> list[dict[str, Any]]:
    """Batch post info by aweme id (semicolon-separated)."""
    ids = [str(x).strip() for x in aweme_ids if str(x).strip()]
    if not ids:
        return []
    payload = await _ensemble_get(
        ENSEMBLEDATA_POST_MULTI_INFO_URL,
        {
            "ids": ";".join(ids),
            "new_version": "False",
            "download_video": "False",
        },
    )
    data = payload.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        inner = data.get("data") or data.get("posts") or data.get("aweme_details")
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
    return []


def _int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _float_sec_from_ms(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        return float(val) / 1000.0
    except (TypeError, ValueError):
        return 0.0


def detect_content_type(aweme_detail: dict[str, Any]) -> ContentType:
    """§2: carousel when aweme_type=2 or when ``image_post_info.images`` is non-empty.

    Priority order:
    1. aweme_type == 2 with image_post_info.images → carousel (strongest signal)
    2. image_post_info.images present (any aweme_type) → carousel
    3. _photo_url_hint == True (URL path contained /photo/) → carousel as fallback
       when ED response lacks both aweme_type=2 and image_post_info (rare, but observed
       when ED doesn't recognize the /photo/ URL format)
    4. Anything else → video
    """
    if _int(aweme_detail.get("aweme_type")) == AWEME_TYPE_PHOTO_CAROUSEL:
        ipi = aweme_detail.get("image_post_info")
        if isinstance(ipi, dict):
            images = ipi.get("images")
            if isinstance(images, list) and len(images) > 0:
                return "carousel"
        # aweme_type=2 but no images — treat as carousel anyway; _analyze_carousel
        # will return an informative error if CDN URLs are missing.
        return "carousel"
    ipi = aweme_detail.get("image_post_info")
    if isinstance(ipi, dict):
        images = ipi.get("images")
        if isinstance(images, list) and len(images) > 0:
            return "carousel"
    # URL-based hint set by fetch_post_info for /photo/ paths
    if aweme_detail.get("_photo_url_hint"):
        return "carousel"
    return "video"


def parse_metadata(aweme_detail: dict[str, Any]) -> VideoMetadata:
    video_id = str(aweme_detail.get("aweme_id", "") or "")
    desc = str(aweme_detail.get("desc", "") or "")

    hashtags: list[str] = []
    for item in aweme_detail.get("text_extra") or []:
        if isinstance(item, dict) and item.get("hashtag_name"):
            hashtags.append(str(item["hashtag_name"]))

    video = aweme_detail.get("video") or {}
    duration_sec = _float_sec_from_ms(video.get("duration"))

    stats = aweme_detail.get("statistics") or {}
    views = _int(stats.get("play_count"))
    likes = _int(stats.get("digg_count"))
    comments = _int(stats.get("comment_count"))
    shares = _int(stats.get("share_count"))
    bookmarks = _int(stats.get("collect_count"))

    engagement_rate: float | None = None
    if views is not None and views > 0:
        if likes is not None and comments is not None and shares is not None:
            engagement_rate = (likes + comments + shares) / views * 100.0

    author = aweme_detail.get("author") or {}
    verification_type = author.get("verification_type", 0)
    try:
        verified = int(verification_type) > 0
    except (TypeError, ValueError):
        verified = False

    music = aweme_detail.get("music") or {}

    ct_detected = detect_content_type(aweme_detail)
    if ct_detected == "carousel":
        content_type: ContentType = "carousel"
        ipi = aweme_detail.get("image_post_info")
        images_raw = ipi.get("images") if isinstance(ipi, dict) else None
        slide_count = len(images_raw) if isinstance(images_raw, list) else None
    else:
        content_type = "video"
        slide_count = None

    return VideoMetadata(
        video_id=video_id,
        description=desc,
        hashtags=hashtags,
        content_type=content_type,
        slide_count=slide_count,
        duration_sec=duration_sec,
        create_time=_int(aweme_detail.get("create_time")),
        metrics=Metrics(
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            bookmarks=bookmarks,
        ),
        engagement_rate=engagement_rate,
        author=Author(
            username=str(author.get("unique_id", "") or ""),
            display_name=str(author.get("nickname", "") or ""),
            followers=_int(author.get("follower_count")),
            verified=verified,
        ),
        music=Music(
            title=music.get("title"),
            artist=music.get("author"),
            is_original=music.get("is_original"),
        ),
    )


def _urls_from_play_addr(play_addr: Any) -> list[str]:
    if not isinstance(play_addr, dict):
        return []
    raw = play_addr.get("url_list") or []
    if not isinstance(raw, list):
        return []
    return [str(u) for u in raw if isinstance(u, str) and u]


def extract_video_urls(aweme_detail: dict[str, Any]) -> list[str]:
    video = aweme_detail.get("video") or {}
    if not isinstance(video, dict):
        return []

    candidates: list[str] = []
    candidates.extend(_urls_from_play_addr(video.get("play_addr_h264")))
    candidates.extend(_urls_from_play_addr(video.get("play_addr")))

    bit_rate = video.get("bit_rate") or []
    if isinstance(bit_rate, list):
        for tier in bit_rate:
            if isinstance(tier, dict):
                candidates.extend(_urls_from_play_addr(tier.get("play_addr")))

    seen: set[str] = set()
    out: list[str] = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_image_url_lists(aweme_detail: dict[str, Any]) -> list[list[str]]:
    """Per-slide CDN URL lists (``display_image`` or slide ``url_list``), order preserved.

    Capped at :data:`src.config.CAROUSEL_EXTRACT_MAX_SLIDES` slides. Empty outer list
    if not a carousel payload.
    """
    ipi = aweme_detail.get("image_post_info")
    if not isinstance(ipi, dict):
        return []
    images_raw = ipi.get("images")
    if not isinstance(images_raw, list) or not images_raw:
        return []

    out: list[list[str]] = []
    for item in images_raw[:CAROUSEL_EXTRACT_MAX_SLIDES]:
        if not isinstance(item, dict):
            continue
        display = item.get("display_image")
        # Usually display_image.url_list; some payloads use slide-level url_list.
        raw_urls = (
            _urls_from_play_addr(display) if isinstance(display, dict) else []
        )
        if not raw_urls:
            raw_urls = _urls_from_play_addr(item)
        if not raw_urls:
            continue
        slide_urls: list[str] = []
        seen_u: set[str] = set()
        for u in raw_urls:
            if u and u not in seen_u:
                seen_u.add(u)
                slide_urls.append(u)
        if slide_urls:
            out.append(slide_urls)
    return out


def _mime_from_stream_headers(url: str, content_type: str | None) -> str:
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct.startswith("image/"):
            return ct
    base = url.lower().split("?")[0]
    if base.endswith(".webp"):
        return "image/webp"
    if base.endswith(".png"):
        return "image/png"
    return "image/jpeg"


async def _download_one_slide_image(
    client: httpx.AsyncClient,
    slide_index: int,
    url_candidates: list[str],
) -> tuple[Path, str] | None:
    """Try CDN mirrors for one slide; write to ``/tmp`` or return None if all fail."""
    for url in url_candidates:
        path = Path("/tmp") / f"{uuid.uuid4().hex}.img"
        try:
            async with client.stream(
                "GET", url, headers=CDN_HEADERS, follow_redirects=True
            ) as r:
                r.raise_for_status()
                ctype = r.headers.get("content-type")
                mime = _mime_from_stream_headers(url, ctype)
                total = 0
                try:
                    async with aiofiles.open(path, "wb") as f:
                        async for chunk in r.aiter_bytes():
                            total += len(chunk)
                            if total > CAROUSEL_MAX_IMAGE_BYTES:
                                raise ValueError("slide too large")
                            await f.write(chunk)
                except Exception:
                    if path.exists():
                        try:
                            path.unlink()
                        except OSError:
                            pass
                    raise
            if total == 0:
                if path.exists():
                    try:
                        path.unlink()
                    except OSError:
                        pass
                continue
            logger.debug(
                "Slide %s downloaded: %d bytes via %s",
                slide_index,
                total,
                "proxy" if os.environ.get("RESIDENTIAL_PROXY_URL") else "direct",
            )
            return path, mime
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError, ValueError) as e:
            logger.debug(
                "Carousel slide %s CDN URL failed: %s — %s",
                slide_index,
                url[:80],
                e,
            )
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
            continue

    logger.warning(
        "All CDN URLs failed for carousel slide index %s (%d mirrors)",
        slide_index,
        len(url_candidates),
    )
    return None


async def download_images(
    url_lists: list[list[str]],
) -> tuple[list[tuple[int, Path, str]], list[int]]:
    """Download each slide's image to ``/tmp``; skip slides that fail entirely.

    Returns ``(successful rows, failed indices)`` where each successful row is
    ``(source_index, path, mime)``. ``source_index`` is the slide's 0-based position
    in ``url_lists`` (stable carousel batch index when Gemini maps ``slides[].index``).
    """
    if not url_lists:
        return [], []

    client = await get_cdn_client()
    success: list[tuple[int, Path, str]] = []
    failed_indices: list[int] = []

    for i, candidates in enumerate(url_lists):
        if not candidates:
            failed_indices.append(i)
            logger.warning("Carousel slide %s has no CDN URLs", i)
            continue
        got = await _download_one_slide_image(client, i, candidates)
        if got is None:
            failed_indices.append(i)
        else:
            path, mime = got
            success.append((i, path, mime))

    return success, failed_indices


async def download_video(url_list: list[str]) -> Path:
    """Stream-download first working URL to a temp mp4 path (403: retry same URL up to 3×)."""
    if not url_list:
        raise ValueError("No video download URLs available")

    client = await get_cdn_client()  # proxied when RESIDENTIAL_PROXY_URL is set
    last_err: Exception | None = None
    for url in url_list:
        for attempt in range(3):
            path = Path("/tmp") / f"{uuid.uuid4().hex}.mp4"
            try:
                async with client.stream(
                    "GET", url, headers=CDN_HEADERS, follow_redirects=True
                ) as r:
                    if r.status_code == 403:
                        if attempt < 2:
                            await asyncio.sleep(0.25 * (attempt + 1))
                            continue
                        r.raise_for_status()
                    r.raise_for_status()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        async with aiofiles.open(path, "wb") as f:
                            async for chunk in r.aiter_bytes():
                                await f.write(chunk)
                    except Exception:
                        if path.exists():
                            try:
                                path.unlink()
                            except OSError:
                                pass
                        raise
                size_mb = path.stat().st_size / (1024 * 1024)
                logger.info(
                    "Video downloaded: %.1fMB via %s",
                    size_mb,
                    "proxy" if os.environ.get("RESIDENTIAL_PROXY_URL") else "direct",
                )
                return path
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
                last_err = e
                if path.exists():
                    try:
                        path.unlink()
                    except OSError:
                        pass
                if (
                    attempt < 2
                    and isinstance(e, httpx.HTTPStatusError)
                    and e.response is not None
                    and e.response.status_code == 403
                ):
                    await asyncio.sleep(0.25 * (attempt + 1))
                    continue
                break

    raise RuntimeError(f"Video download failed for all CDN mirrors: {last_err!s}") from last_err
