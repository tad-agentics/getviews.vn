"""Corpus context helpers — count queries and citation building for synthesis prompts.

These functions are called in pipelines.py before each synthesis call to inject
real corpus counts into the Gemini prompt. The count is cached in-session so
follow-up questions don't re-query Supabase.

Usage pattern (P0-1):
    count, niche_name = await get_corpus_count(niche_id=3, days=30)
    citation = citation_vi(count, niche_name, days=30)
    # → "Dựa trên 412 video review đồ gia dụng tháng này"
    # Inject into synthesis prompt context block.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from getviews_pipeline.formatters import citation_vi

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supabase anon client (read-only — corpus_count uses RLS-allowed SELECT)
# ---------------------------------------------------------------------------

def _anon_client() -> Any:
    """Supabase client with anon key — sufficient for reading video_corpus counts."""
    from supabase import create_client  # type: ignore[import-untyped]

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Corpus count query
# ---------------------------------------------------------------------------

async def get_corpus_count(
    niche_id: int | None,
    *,
    days: int = 30,
    niche_name: str = "",
) -> tuple[int, str]:
    """Query video_corpus count for a niche within the given recency window.

    Returns (count, resolved_niche_name).

    Falls back to (0, niche_name) on any error — never raises, so a Supabase
    outage doesn't break synthesis. The prompt will gracefully omit the count
    when it's 0 (see build_corpus_citation_block).

    Args:
        niche_id:   Niche PK from niche_taxonomy. None = count across all niches.
        days:       Recency window in days (default 30).
        niche_name: Human-readable Vietnamese niche label (e.g. "review đồ gia dụng").
                    Used as the name in the citation string.
    """
    try:
        client = _anon_client()
        query = (
            client.table("video_corpus")
            .select("id", count="exact")
            .gte("indexed_at", f"now() - interval '{days} days'")
        )
        if niche_id is not None:
            query = query.eq("niche_id", niche_id)
        result = query.execute()
        count = result.count or 0
        return count, niche_name
    except Exception as exc:
        logger.warning("[corpus_context] count query failed: %s", exc)
        return 0, niche_name


# ---------------------------------------------------------------------------
# Citation block builder — returns a string ready for prompt injection
# ---------------------------------------------------------------------------

def build_corpus_citation_block(count: int, niche_name: str, days: int) -> str:
    """Return a Vietnamese citation instruction block for synthesis prompt injection.

    When count > 0:
        Bạn đang phân tích dựa trên 412 video review đồ gia dụng tháng này.
        Luôn trích dẫn số lượng video và khung thời gian trong mọi nhận định.
        Dùng cách nói tự nhiên: "tháng này", "tuần này" — không nói "30 ngày gần nhất".
        Mọi phản hồi có nhận định về xu hướng phải bắt đầu bằng hoặc chứa:
        "Dựa trên {count} video {niche} {timeframe}"

    When count == 0 (failed query or empty corpus):
        Returns an empty string — no citation injected.
    """
    if count <= 0:
        return ""

    cite = citation_vi(count, niche_name, days)
    return (
        f"NGỮ CẢNH DỮ LIỆU: {cite}.\n"
        "Luôn trích dẫn số lượng video và khung thời gian trong mọi nhận định có dữ liệu.\n"
        'Dùng cách nói tự nhiên: "tháng này", "tuần này" — không nói "30 ngày gần nhất".\n'
        f'Mọi nhận định xu hướng phải chứa cụm: "{cite}"'
    )


# ---------------------------------------------------------------------------
# Session cache helpers — avoid re-querying on follow-up messages
# ---------------------------------------------------------------------------

def get_cached_count(session: dict[str, Any], niche_id: int | None) -> tuple[int, str] | None:
    """Return cached (count, niche_name) if already fetched this session."""
    cache: dict = session.get("_corpus_counts", {})
    key = str(niche_id)
    entry = cache.get(key)
    if entry:
        return entry["count"], entry["niche_name"]
    return None


def set_cached_count(
    session: dict[str, Any], niche_id: int | None, count: int, niche_name: str
) -> None:
    """Store (count, niche_name) in session so follow-ups skip the Supabase call."""
    cache = session.setdefault("_corpus_counts", {})
    cache[str(niche_id)] = {"count": count, "niche_name": niche_name}


async def get_corpus_count_cached(
    session: dict[str, Any],
    niche_id: int | None,
    *,
    days: int = 30,
    niche_name: str = "",
) -> tuple[int, str]:
    """get_corpus_count with in-session caching.

    On first call: queries Supabase, caches result in session dict.
    On follow-up calls in the same session: returns cached value immediately.
    """
    cached = get_cached_count(session, niche_id)
    if cached is not None:
        return cached
    count, resolved_name = await get_corpus_count(
        niche_id, days=days, niche_name=niche_name
    )
    set_cached_count(session, niche_id, count, resolved_name)
    return count, resolved_name
