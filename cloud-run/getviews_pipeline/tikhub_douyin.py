"""TikHub Douyin client wrapper (replaces ensemble_douyin.py).

EnsembleData's ``/douyin/*`` mirror routes turned out to silently
return empty payloads (verified live, 2026-04-27) — every call
landed zero awemes in the corpus. We migrated the Douyin pipeline
provider to TikHub (api.tikhub.io) which proxies the Douyin web
internal API directly.

Public surface: this module exports the same five async functions
``ensemble_douyin`` did, with identical signatures and return
shapes, so ``douyin_ingest`` / ``douyin_metadata`` / ``douyin_data``
need zero changes:

  • ``fetch_douyin_post_info(url_or_id)`` → ``aweme_detail`` dict
  • ``fetch_douyin_post_multi_info(aweme_ids)`` → list of awemes
  • ``fetch_douyin_keyword_search(keyword, *, cursor)``
        → ``(awemes, next_cursor)`` tuple
  • ``fetch_douyin_hashtag_posts(hashtag, *, cursor)``
        → ``(awemes, next_cursor)`` tuple
  • ``fetch_douyin_user_posts(handle, *, depth, start_cursor)``
        → list of awemes

Why the response shape doesn't change: both EnsembleData and TikHub
scrape the same Douyin web API, so they emit the canonical Douyin
``aweme_detail`` envelope (``aweme_id``, ``desc``, ``video.{...}``,
``statistics.{...}``, ``author.{unique_id, nickname, ...}``,
``text_extra[].hashtag_name``, ``create_time``). The translation
work in this module is purely on the *request* side — TikHub
needs ``challenge_id`` / ``sec_user_id`` where ED accepted handles
and hashtag names. We resolve those once per unique input and
cache via in-process dicts.

What this module owns:
  • TikHub envelope unwrapping (``{"code": 200, "data": {...}}``).
  • ``handle → sec_user_id`` resolution via ``fetch_query_user``.
  • ``hashtag_name → challenge_id`` resolution via
    ``fetch_challenge_search_v2``.
  • Daily budget gate via ``consume_tikhub_douyin_budget_or_raise``.

What it deliberately re-uses:
  • ``aweme_from_feed_item`` from ``ensemble`` — flattens the
    optional ``{"aweme_info": {...}}`` wrapping that some TikHub
    endpoints emit, into the canonical aweme dict downstream code
    consumes.
  • ``parse_metadata`` (downstream) — Douyin awemes share the
    schema, so the existing parser produces a ``VideoMetadata``
    for ingest unchanged.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from getviews_pipeline.config import (
    TIKHUB_API_KEY,
    TIKHUB_BASE_URL,
    TIKHUB_REQUEST_TIMEOUT_SEC,
)
from getviews_pipeline.ensemble import (
    aweme_from_feed_item,
    consume_tikhub_douyin_budget_or_raise,
)

logger = logging.getLogger(__name__)


# ── Resolution caches ─────────────────────────────────────────────────
# In-process per-instance caches with a hard size cap. Each cache key
# is a single string (handle / hashtag-name) and each value is the
# resolved ID. Misses (None) are also cached so we don't re-attempt
# resolution for the same input within a run.
_SEC_USER_ID_CACHE: dict[str, str | None] = {}
_CHALLENGE_ID_CACHE: dict[str, str | None] = {}
_RESOLVE_CACHE_MAX = 512


def _cache_set(cache: dict[str, str | None], key: str, value: str | None) -> None:
    """Bounded dict cache — evicts the oldest entry once over the cap.

    Python 3.7+ dicts iterate in insertion order, so ``next(iter(cache))``
    yields the oldest key.
    """
    if key in cache:
        cache[key] = value
        return
    if len(cache) >= _RESOLVE_CACHE_MAX:
        oldest = next(iter(cache))
        cache.pop(oldest, None)
    cache[key] = value


def reset_resolution_caches_for_tests() -> None:
    """Clear the handle / hashtag resolution caches (tests only)."""
    _SEC_USER_ID_CACHE.clear()
    _CHALLENGE_ID_CACHE.clear()


# ── HTTP client ───────────────────────────────────────────────────────


async def _tikhub_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any = None,
) -> dict[str, Any]:
    """Single TikHub HTTP call with auth + budget gate + envelope unwrap.

    Returns the inner ``data`` payload (the part of the response
    callers actually care about). Raises ``ValueError`` on:
      • Non-200 HTTP status (mapped to a clean error message).
      • TikHub envelope ``code != 200``.
      • Missing ``data`` key in a successful response.

    The budget guard fires *before* the network call so a saturated
    daily counter never burns a real request.
    """
    if not TIKHUB_API_KEY:
        raise ValueError("tikhub: TIKHUB_API_KEY not configured")

    consume_tikhub_douyin_budget_or_raise()

    url = f"{TIKHUB_BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {TIKHUB_API_KEY}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=TIKHUB_REQUEST_TIMEOUT_SEC) as client:
            if method == "GET":
                resp = await client.get(url, params=params, headers=headers)
            elif method == "POST":
                resp = await client.post(url, params=params, json=json, headers=headers)
            else:
                raise ValueError(f"tikhub: unsupported method {method}")
    except httpx.HTTPError as exc:
        raise ValueError(f"tikhub: network error {exc.__class__.__name__}: {exc}") from exc

    if resp.status_code == 401:
        raise ValueError("tikhub: 401 unauthorized — check TIKHUB_API_KEY")
    if resp.status_code == 429:
        raise ValueError("tikhub: 429 rate-limited — slow down or upgrade plan")
    if resp.status_code >= 400:
        raise ValueError(f"tikhub: HTTP {resp.status_code} — {resp.text[:200]}")

    try:
        body = resp.json()
    except ValueError as exc:
        raise ValueError(f"tikhub: malformed JSON response: {exc}") from exc

    code = body.get("code")
    if code is not None and code != 200:
        raise ValueError(
            f"tikhub: envelope error code={code} message={body.get('message') or body.get('msg') or '?'}"
        )

    data = body.get("data")
    if data is None:
        # Some endpoints embed ``data`` directly; treat that as success
        # with the whole body as data so we don't false-positive a
        # missing field.
        return body
    return data if isinstance(data, dict) else {"data": data}


# ── Resolution helpers ────────────────────────────────────────────────


async def _resolve_sec_user_id(handle: str) -> str | None:
    """Translate a Douyin handle (``unique_id``) to the ``sec_user_id``
    that ``fetch_user_post_videos`` requires.

    Cached in-process so a niche with N creators only resolves each
    handle once per pod lifetime. Cache misses also cache None so we
    don't re-fire the lookup for handles that just don't exist.
    """
    cleaned = (handle or "").strip().lstrip("@")
    if not cleaned:
        return None
    if cleaned in _SEC_USER_ID_CACHE:
        return _SEC_USER_ID_CACHE[cleaned]

    try:
        data = await _tikhub_request(
            "POST",
            "/api/v1/douyin/web/fetch_query_user",
            json={"unique_id": cleaned},
        )
    except ValueError as exc:
        logger.warning("[tikhub] handle resolve failed handle=%s: %s", cleaned, exc)
        _cache_set(_SEC_USER_ID_CACHE, cleaned, None)
        return None

    sec_id = (
        (data.get("user_info") or {}).get("sec_uid")
        or data.get("sec_uid")
        or data.get("sec_user_id")
    )
    sec_id = sec_id if isinstance(sec_id, str) and sec_id else None
    _cache_set(_SEC_USER_ID_CACHE, cleaned, sec_id)
    return sec_id


async def _resolve_challenge_id(hashtag: str) -> str | None:
    """Translate a hashtag name to the ``challenge_id`` that
    ``fetch_challenge_posts`` requires.

    Same caching strategy as ``_resolve_sec_user_id``.
    """
    cleaned = (hashtag or "").strip().lstrip("#")
    if not cleaned:
        return None
    if cleaned in _CHALLENGE_ID_CACHE:
        return _CHALLENGE_ID_CACHE[cleaned]

    try:
        data = await _tikhub_request(
            "POST",
            "/api/v1/douyin/search/fetch_challenge_search_v2",
            json={"keyword": cleaned, "cursor": 0},
        )
    except ValueError as exc:
        logger.warning("[tikhub] challenge resolve failed tag=%s: %s", cleaned, exc)
        _cache_set(_CHALLENGE_ID_CACHE, cleaned, None)
        return None

    # Pick the first challenge whose name matches the input (case
    # insensitive). TikHub's search returns a ranked list under
    # ``data.challenge_list`` per their SDK. Defensive: also check
    # bare ``challenge_list`` and the ``data`` array-shaped variant.
    challenges = (
        data.get("challenge_list")
        or (data.get("data") if isinstance(data.get("data"), list) else None)
        or []
    )
    cid: str | None = None
    for ch in challenges:
        if not isinstance(ch, dict):
            continue
        name = (ch.get("cha_name") or ch.get("challenge_name") or ch.get("name") or "").strip()
        cid_candidate = ch.get("cid") or ch.get("challenge_id") or ch.get("cha_id")
        if name.lower() == cleaned.lower() and isinstance(cid_candidate, str) and cid_candidate:
            cid = cid_candidate
            break
    # Fallback: if no exact match, take the top result — TikHub's
    # ranking already does prefix/fuzzy on hashtag search.
    if cid is None and challenges:
        first = challenges[0] if isinstance(challenges[0], dict) else {}
        cand = first.get("cid") or first.get("challenge_id") or first.get("cha_id")
        if isinstance(cand, str) and cand:
            cid = cand
    _cache_set(_CHALLENGE_ID_CACHE, cleaned, cid)
    return cid


_AWEME_ID_RE = re.compile(r"/video/(\d+)")


def _extract_aweme_id(url_or_id: str) -> str:
    """Extract the bare numeric aweme_id from a URL or pass through.

    Douyin URLs come in two shapes:
      • ``https://www.douyin.com/video/<aweme_id>``
      • ``https://v.douyin.com/<short>/`` (short-link, redirects to canonical)
    For short links we'd need an extra HEAD request to resolve; the
    caller hierarchy in ``corpus_ingest`` only ever passes canonical
    URLs or bare aweme_ids, so we only handle those two cases.
    """
    val = (url_or_id or "").strip()
    if not val:
        return ""
    if val.isdigit():
        return val
    m = _AWEME_ID_RE.search(val)
    return m.group(1) if m else val


# ── Public API (mirrors ensemble_douyin signatures) ───────────────────


async def fetch_douyin_post_info(url_or_id: str) -> dict[str, Any]:
    """Single Douyin video metadata. Returns the bare ``aweme_detail`` dict."""
    aweme_id = _extract_aweme_id(url_or_id)
    if not aweme_id:
        raise ValueError("douyin post info requires a non-empty url or id")
    data = await _tikhub_request(
        "GET",
        "/api/v1/douyin/web/fetch_one_video_v2",
        params={"aweme_id": aweme_id},
    )
    inner = data.get("aweme_detail")
    if isinstance(inner, dict):
        return inner
    if data.get("aweme_id") is not None or data.get("video") is not None:
        return data
    raise ValueError("tikhub post info: no aweme_detail in payload")


async def fetch_douyin_post_multi_info(aweme_ids: list[str]) -> list[dict[str, Any]]:
    """Batch metadata fetch. Returns ``[]`` on empty input rather than calling TikHub."""
    cleaned = [a.strip() for a in (aweme_ids or []) if a and a.strip()]
    if not cleaned:
        return []
    # TikHub expects a list of dicts ``[{"aweme_id": "..."}, ...]`` per
    # the SDK ``fetch_multi_video(body=...)`` signature.
    body = [{"aweme_id": a} for a in cleaned]
    data = await _tikhub_request(
        "POST",
        "/api/v1/douyin/web/fetch_multi_video",
        json=body,
    )
    raw = data.get("aweme_details") or data.get("data") or data.get("aweme_list")
    if isinstance(raw, list):
        return [a for a in raw if isinstance(a, dict)]
    return []


async def fetch_douyin_keyword_search(
    keyword: str,
    *,
    period: int = 30,
    sorting: int = 1,
    cursor: int = 0,
) -> tuple[list[dict[str, Any]], int | None]:
    """Douyin keyword search.

    ``period`` and ``sorting`` are accepted for compatibility with the
    old ED signature; TikHub uses different conventions:
      • ``sort_type``: "0" 综合 / "1" 最多点赞 / "2" 最新发布 — we map
        ``sorting=1`` → "1" (most likes) and any other value → "0".
      • ``publish_time``: "0" 不限 / "1" 1d / "7" 7d / "180" 180d —
        we map ``period<=1`` → "1", ``period<=7`` → "7",
        ``period<=180`` → "180", else "0".
    """
    kw = (keyword or "").strip().lstrip("#")
    if not kw:
        raise ValueError("douyin keyword search requires a non-empty keyword")

    sort_type = "1" if sorting == 1 else "0"
    if period <= 1:
        publish_time = "1"
    elif period <= 7:
        publish_time = "7"
    elif period <= 180:
        publish_time = "180"
    else:
        publish_time = "0"

    data = await _tikhub_request(
        "POST",
        "/api/v1/douyin/search/fetch_video_search_v2",
        json={
            "keyword": kw,
            "cursor": cursor,
            "sort_type": sort_type,
            "publish_time": publish_time,
            "filter_duration": "0",
            "content_type": "0",
            "search_id": "",
            "backtrace": "",
        },
    )
    awemes = _extract_awemes(data)
    next_cursor = _next_cursor(data)
    return awemes, next_cursor


async def fetch_douyin_hashtag_posts(
    hashtag: str,
    *,
    cursor: int = 0,
) -> tuple[list[dict[str, Any]], int | None]:
    """Douyin hashtag feed chunk. Resolves name → challenge_id internally."""
    tag = (hashtag or "").strip().lstrip("#")
    if not tag:
        raise ValueError("douyin hashtag posts requires a non-empty name")

    challenge_id = await _resolve_challenge_id(tag)
    if not challenge_id:
        # Treat unresolved hashtag as an empty page rather than
        # bubbling a ValueError — same shape the orchestrator expects
        # on a thin/missing pool, so it just continues to the next tag.
        logger.info("[tikhub] hashtag %s — no challenge_id; treating as empty page", tag)
        return [], None

    data = await _tikhub_request(
        "POST",
        "/api/v1/douyin/web/fetch_challenge_posts",
        json={
            "challenge_id": challenge_id,
            "sort_type": 0,
            "cursor": cursor,
            "count": 20,
        },
    )
    awemes = _extract_awemes(data)
    next_cursor = _next_cursor(data)
    return awemes, next_cursor


async def fetch_douyin_user_posts(
    user_id_or_handle: str,
    *,
    depth: int = 1,
    start_cursor: int = 0,
) -> list[dict[str, Any]]:
    """Recent posts for a Douyin creator. Resolves handle → sec_user_id internally."""
    u = (user_id_or_handle or "").strip().lstrip("@")
    if not u:
        raise ValueError("douyin user posts requires a username or sec_uid")

    # If the input already looks like a sec_user_id (contains
    # underscores / hyphens / is non-numeric and longer than typical
    # handles), pass it through; otherwise resolve via fetch_query_user.
    if _looks_like_sec_uid(u):
        sec_user_id: str | None = u
    else:
        sec_user_id = await _resolve_sec_user_id(u)
    if not sec_user_id:
        logger.info("[tikhub] user posts: handle %s did not resolve — empty pool", u)
        return []

    out: list[dict[str, Any]] = []
    cursor = str(start_cursor or 0)
    for _ in range(max(1, int(depth))):
        data = await _tikhub_request(
            "GET",
            "/api/v1/douyin/web/fetch_user_post_videos",
            params={
                "sec_user_id": sec_user_id,
                "max_cursor": cursor,
                "count": 20,
                "filter_type": "0",
            },
        )
        page = _extract_awemes(data)
        out.extend(page)
        next_cursor = _next_cursor(data)
        if not next_cursor:
            break
        cursor = str(next_cursor)
        await asyncio.sleep(0)  # cooperative yield between pages
    return out


# ── Helpers ──────────────────────────────────────────────────────────


def _extract_awemes(data: Any) -> list[dict[str, Any]]:
    """Walk a TikHub Douyin payload to the list of aweme dicts.

    TikHub surfaces the awemes under a few different keys depending
    on the endpoint:
      • ``aweme_list``      — fetch_user_post_videos, fetch_challenge_posts
      • ``aweme_details``   — fetch_multi_video
      • ``data`` (list)     — fetch_video_search_v2 + general/multi search
      • ``data.data``       — older ED-shaped variant some endpoints use
    Each candidate item passes through ``aweme_from_feed_item`` (the
    same normaliser ED uses) so wrapped ``{"aweme_info": {...}}`` rows
    surface as a flat aweme dict.
    """
    if data is None:
        return []
    raw: Any = None
    if isinstance(data, dict):
        for key in ("aweme_list", "aweme_details", "aweme_detail_list", "videos"):
            v = data.get(key)
            if isinstance(v, list):
                raw = v
                break
        if raw is None:
            inner = data.get("data")
            if isinstance(inner, list):
                raw = inner
    elif isinstance(data, list):
        raw = data
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        normalised = aweme_from_feed_item(item)
        if normalised:
            out.append(normalised)
    return out


def _next_cursor(data: dict[str, Any]) -> int | None:
    """Pluck ``next_cursor`` / ``max_cursor`` / ``cursor`` from a TikHub payload.

    Different Douyin endpoints surface cursor under different keys.
    Returns ``None`` if no usable cursor is present (signals end-of-pool
    to callers).
    """
    if not isinstance(data, dict):
        return None
    for key in ("next_cursor", "max_cursor", "cursor", "nextCursor"):
        val = data.get(key)
        if val is None or val == 0 or val == "0":
            continue
        try:
            return int(val)
        except (TypeError, ValueError):
            continue
    return None


def _looks_like_sec_uid(value: str) -> bool:
    """Heuristic: Douyin sec_user_ids are long base64-ish strings.

    Real sec_user_ids look like ``MS4wLjABAAAA...``. Handles are short
    user-chosen strings (e.g. ``elon_musk_yt``). We treat anything ≥ 30
    chars and starting with ``MS4`` as already-resolved.
    """
    return len(value) >= 30 and value.startswith("MS4")
