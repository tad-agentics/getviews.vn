"""D1 (2026-06-03) — EnsembleData Douyin client wrapper.

Mirrors ``ensemble.fetch_post_info`` / ``fetch_keyword_search`` /
``fetch_hashtag_posts`` for the Kho Douyin ingest pipeline (D2 lands the
ingest orchestration). EnsembleData routes Douyin endpoints under
``/douyin/*`` with the same response envelope as ``/tt/*``:

  payload = {
    "data": <list[aweme] | dict[..., {"data": list[aweme], "nextCursor": int}]>,
    "code": <int>,            # ED error code, 0 / unset on success
    ... ED metering metadata
  }

Each aweme dict has the same shape as TikTok aweme_detail
(``aweme_id``, ``video.{play_addr_h264, bit_rate}``, ``statistics``,
``author.{unique_id, ...}``, ``desc``, ``text_extra``, etc.) — Gemini
analysis (``analysis_core.analyze_aweme``) and the metadata extractor
work on Douyin awemes unchanged.

What this module owns:
  • URL routing (``/douyin/*`` vs ``/tt/*``).
  • Country defaults (Douyin = mainland CN, no per-region split).
  • Cleaner kwargs surface for the D2 ingest orchestrator —
    ``fetch_douyin_keyword_search`` doesn't expose TikTok-specific
    ``country`` since EnsembleData's Douyin endpoints don't accept it.

What it REUSES (deliberately not duplicated):
  • ``_ensemble_get`` — the rate-limited HTTP client + budget gate
    (one ED token, single daily counter).
  • ``aweme_from_feed_item`` / ``iter_awemes_from_search_payload`` —
    the response normaliser (works on /douyin/* responses unchanged
    per ED docs).
  • ``parse_metadata`` (from ``ensemble.py``) — Douyin awemes share the
    schema, so the existing parser produces a ``VideoMetadata`` for
    ingest just fine. ``language`` falls out of the analysis_json
    (Gemini detects 'zh' on Douyin captions).

This file does NOT do any Chinese→Vietnamese translation — that lands
in D2 alongside the ingest orchestrator (one Gemini call per video
right after analyze_aweme).
"""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.config import (
    ENSEMBLEDATA_DOUYIN_HASHTAG_POSTS_URL,
    ENSEMBLEDATA_DOUYIN_KEYWORD_SEARCH_URL,
    ENSEMBLEDATA_DOUYIN_POST_INFO_URL,
    ENSEMBLEDATA_DOUYIN_POST_MULTI_INFO_URL,
    ENSEMBLEDATA_DOUYIN_USER_POSTS_URL,
)
from getviews_pipeline.ensemble import (
    _ensemble_get,
    iter_awemes_from_search_payload,
)

logger = logging.getLogger(__name__)


async def fetch_douyin_post_info(url_or_id: str) -> dict[str, Any]:
    """Single Douyin video metadata.

    Accepts either the full Douyin URL
    (``https://www.douyin.com/video/<aweme_id>``) or just the bare
    aweme_id — ED resolves both. Returns the inner ``aweme_detail``
    dict (matching the TikTok ``aweme_detail`` shape so downstream
    analyzers don't branch).

    Raises ``ValueError`` on ED error codes (auth / rate-limit /
    not-found) — caller catches + skips the video.
    """
    val = (url_or_id or "").strip()
    if not val:
        raise ValueError("douyin post info requires a non-empty url or id")
    payload = await _ensemble_get(
        ENSEMBLEDATA_DOUYIN_POST_INFO_URL,
        {"url": val},
    )
    return _extract_aweme_detail(payload)


async def fetch_douyin_post_multi_info(aweme_ids: list[str]) -> list[dict[str, Any]]:
    """Batch metadata fetch for many ``aweme_ids`` (semicolon-joined).

    EnsembleData's ``/douyin/post/multi-info`` mirrors ``/tt/post/multi-info``;
    the response payload has ``data: list[aweme_detail]``. Caller
    de-dupes against ``douyin_video_corpus.video_id`` upstream so we
    don't waste ED units re-fetching cached ones.

    Returns ``[]`` on empty input rather than calling ED.
    """
    cleaned = [a.strip() for a in (aweme_ids or []) if a and a.strip()]
    if not cleaned:
        return []
    payload = await _ensemble_get(
        ENSEMBLEDATA_DOUYIN_POST_MULTI_INFO_URL,
        {"aweme_ids": ";".join(cleaned)},
    )
    data = payload.get("data")
    if isinstance(data, list):
        return [a for a in data if isinstance(a, dict)]
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, list):
            return [a for a in inner if isinstance(a, dict)]
    return []


async def fetch_douyin_keyword_search(
    keyword: str,
    *,
    period: int = 30,
    sorting: int = 1,
    cursor: int = 0,
) -> tuple[list[dict[str, Any]], int | None]:
    """Douyin keyword search — ``sorting`` 1 ≈ likes/engagement.

    Note: unlike ``fetch_keyword_search`` (TikTok) this does NOT accept a
    ``country`` param — EnsembleData's Douyin endpoints surface mainland-CN
    results only. Returns ``(awemes, next_cursor_or_None)`` matching the
    TikTok wrapper's tuple shape so the D2 ingest can fan-in both pools
    with the same iterator pattern.
    """
    kw = (keyword or "").strip().lstrip("#")
    if not kw:
        raise ValueError("douyin keyword search requires a non-empty keyword")
    payload = await _ensemble_get(
        ENSEMBLEDATA_DOUYIN_KEYWORD_SEARCH_URL,
        {
            "keyword": kw,
            "period": period,
            "sorting": sorting,
            "cursor": cursor,
        },
    )
    data = payload.get("data")
    awemes = iter_awemes_from_search_payload(data)
    next_cursor: int | None = None
    if isinstance(data, dict) and data.get("nextCursor") is not None:
        try:
            next_cursor = int(data["nextCursor"])
        except (TypeError, ValueError):
            next_cursor = None
    return awemes, next_cursor


async def fetch_douyin_hashtag_posts(
    hashtag: str,
    *,
    cursor: int = 0,
) -> tuple[list[dict[str, Any]], int | None]:
    """Douyin hashtag feed chunk (~20 posts/page).

    The hashtag string may include or omit the leading ``#`` — both are
    accepted. The Chinese hashtags seeded in
    ``douyin_niche_taxonomy.signal_hashtags_zh`` carry the ``#`` prefix
    by convention; this strips it to match ED's ``name=`` query format.
    """
    tag = (hashtag or "").strip().lstrip("#")
    if not tag:
        raise ValueError("douyin hashtag posts requires a non-empty name")
    payload = await _ensemble_get(
        ENSEMBLEDATA_DOUYIN_HASHTAG_POSTS_URL,
        {"name": tag, "cursor": cursor},
    )
    data = payload.get("data")
    awemes = iter_awemes_from_search_payload(data)
    next_cursor: int | None = None
    if isinstance(data, dict) and data.get("nextCursor") is not None:
        try:
            next_cursor = int(data["nextCursor"])
        except (TypeError, ValueError):
            next_cursor = None
    return awemes, next_cursor


async def fetch_douyin_user_posts(
    user_id_or_handle: str,
    *,
    depth: int = 1,
    start_cursor: int = 0,
) -> list[dict[str, Any]]:
    """Recent posts for a Douyin creator (handle or sec_uid).

    Used on-demand by the D5 pattern-aggregation step (when we want to
    find more videos from a creator that already showed up in the
    hashtag/keyword pool). Not in the daily ingest hot path.
    """
    u = (user_id_or_handle or "").strip().lstrip("@")
    if not u:
        raise ValueError("douyin user posts requires a username or sec_uid")
    payload = await _ensemble_get(
        ENSEMBLEDATA_DOUYIN_USER_POSTS_URL,
        {
            "user_id": u,
            "depth": depth,
            "start_cursor": start_cursor,
        },
    )
    data = payload.get("data")
    return iter_awemes_from_search_payload(data)


def _extract_aweme_detail(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize ``/douyin/post/info`` payload → bare ``aweme_detail``.

    EnsembleData's response is one of:
      • ``{"data": {"aweme_detail": {...}}}``
      • ``{"data": {...aweme...}}``
      • ``{"data": [{...aweme...}]}``  (rare)

    Returns the bare aweme dict; raises ``ValueError`` if nothing usable.
    """
    if not isinstance(payload, dict):
        raise ValueError("douyin post info: payload is not a dict")
    data = payload.get("data")
    if isinstance(data, dict):
        inner = data.get("aweme_detail")
        if isinstance(inner, dict):
            return inner
        if data.get("aweme_id") is not None or data.get("video") is not None:
            return data
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return first
    raise ValueError("douyin post info: no aweme_detail in payload")
