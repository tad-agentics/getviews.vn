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


def _resolve_niche_id(client: Any, niche_name: str) -> int | None:
    """Resolve a free-text niche string to a niche_taxonomy id.

    Resolution order (most → least precise):
    1. signal_hashtags array overlap — matches "#catwalk" against stored hashtags.
       Uses Postgres `cs` (contains) operator: signal_hashtags @> ARRAY['#<name>'].
    2. name_en substring — "Fashion" matches "Fashion & outfit".
    3. name_vn substring — fallback for Vietnamese niche names.

    Returns None when no match found — caller should fall back to live search.
    """
    # Normalise: strip leading # and lowercase; then try both "#term" and "term"
    term = niche_name.strip().lstrip("#").lower()
    hashtag_form = f"#{term}"

    # 1. signal_hashtags overlap (Supabase PostgREST: cs = @> array contains)
    try:
        r = (
            client.table("niche_taxonomy")
            .select("id")
            .contains("signal_hashtags", [hashtag_form])
            .limit(1)
            .execute()
        )
        if r.data:
            return r.data[0]["id"]
    except Exception:
        pass  # Fall through to name match

    # 2. name_en substring
    try:
        r2 = (
            client.table("niche_taxonomy")
            .select("id")
            .ilike("name_en", f"%{term}%")
            .limit(1)
            .execute()
        )
        if r2.data:
            return r2.data[0]["id"]
    except Exception:
        pass

    # 3. name_vn substring
    try:
        r3 = (
            client.table("niche_taxonomy")
            .select("id")
            .ilike("name_vn", f"%{term}%")
            .limit(1)
            .execute()
        )
        if r3.data:
            return r3.data[0]["id"]
    except Exception:
        pass

    return None


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


# ---------------------------------------------------------------------------
# Breakout + signal helpers — used by run_trend_spike to enrich payload
# ---------------------------------------------------------------------------

async def get_top_breakout_videos(
    niche_id: int | None,
    *,
    days: int = 7,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return corpus videos sorted by breakout_multiplier for a niche.

    Returns list of {video_id, creator_handle, views, breakout_multiplier, indexed_at}.
    Falls back to [] on any error.
    """
    try:
        client = _anon_client()
        query = (
            client.table("video_corpus")
            .select("video_id, creator_handle, views, breakout_multiplier, indexed_at")
            .gt("breakout_multiplier", 1.0)
            .gte("indexed_at", f"now() - interval '{days} days'")
            .order("breakout_multiplier", desc=True)
            .limit(limit)
        )
        if niche_id is not None:
            query = query.eq("niche_id", niche_id)
        result = query.execute()
        return result.data or []
    except Exception as exc:
        logger.warning("[corpus_context] get_top_breakout_videos failed: %s", exc)
        return []


async def get_niche_intelligence(niche_name: str) -> dict[str, Any]:
    """Fetch one row from niche_intelligence for a niche identified by name.

    Resolves niche_id via niche_taxonomy lookup, then returns the materialized
    niche stats row (avg_face_appears_at, pct_face_in_half_sec,
    avg_transitions_per_second, hook_distribution, format_distribution,
    avg_engagement_rate, avg_text_overlays, has_cta_pct, commerce_pct,
    median_duration, sample_size).

    Falls back to {} on any error so callers never raise.
    """
    try:
        client = _anon_client()
        niche_id = _resolve_niche_id(client, niche_name)

        if niche_id is None:
            logger.info("[corpus_context] niche '%s' not found in niche_taxonomy", niche_name)
            return {}

        ni_result = (
            client.table("niche_intelligence")
            .select("*")
            .eq("niche_id", niche_id)
            .single()
            .execute()
        )
        return ni_result.data or {}
    except Exception as exc:
        logger.warning("[corpus_context] get_niche_intelligence failed for '%s': %s", niche_name, exc)
        return {}


async def get_cached_analysis(video_id: str) -> dict[str, Any] | None:
    """Look up a previously-analyzed video in video_corpus by video_id.

    Returns the stored analysis_json dict if found and non-empty, else None.
    Used as a cross-user cache — if video was already analyzed (by batch ingest
    or a previous user), skip re-download and re-analysis entirely.

    Falls back to None on any error so callers always proceed to fresh analysis.
    """
    if not video_id:
        return None
    try:
        client = _anon_client()
        result = (
            client.table("video_corpus")
            .select("analysis_json, creator_handle, views, tiktok_url, thumbnail_url")
            .eq("video_id", video_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        row = rows[0]
        analysis = row.get("analysis_json") or {}
        if not analysis:
            return None
        logger.info("[corpus_context] cache hit for video_id=%s — skipping download", video_id)
        return {
            "analysis": analysis,
            "_from_corpus_cache": True,
            "_corpus_handle": row.get("creator_handle") or "",
            "_corpus_views": int(row.get("views") or 0),
            "_corpus_tiktok_url": row.get("tiktok_url") or "",
            "_corpus_thumbnail_url": row.get("thumbnail_url") or "",
        }
    except Exception as exc:
        logger.warning("[corpus_context] get_cached_analysis failed for %s: %s", video_id, exc)
        return None


async def fetch_corpus_reference_pool(
    niche_name: str,
    *,
    days: int = 30,
    limit: int = 20,
    exclude_video_id: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch video_corpus rows for a niche, shaped as aweme-compatible dicts.

    Used by run_video_diagnosis to source reference videos from the curated
    corpus (niche-tagged, ≥20k views) instead of raw live EnsembleData search,
    which can return off-niche content.

    Returns rows shaped with synthetic `aweme_id`, `statistics`, `author`
    fields so helpers.select_reference_videos() and analyze_aweme() can
    consume them. Falls back to [] on any error so callers can fall through
    to the live search pool.
    """
    try:
        client = _anon_client()
        niche_id = _resolve_niche_id(client, niche_name)

        if niche_id is None:
            logger.warning(
                "[corpus_context] fetch_corpus_reference_pool: niche '%s' not in taxonomy — "
                "falling back to live search. Add signal_hashtags entry to fix.",
                niche_name,
            )
            return []

        query = (
            client.table("video_corpus")
            .select(
                "video_id, creator_handle, views, likes, comments, shares, "
                "engagement_rate, tiktok_url, thumbnail_url, indexed_at, analysis_json"
            )
            .eq("niche_id", niche_id)
            .gte("indexed_at", f"now() - interval '{days} days'")
            .order("engagement_rate", desc=True)
            .limit(limit)
        )
        result = query.execute()
        rows = result.data or []

        awemes: list[dict[str, Any]] = []
        for row in rows:
            vid = row.get("video_id") or ""
            if not vid or vid == exclude_video_id:
                continue
            handle = row.get("creator_handle") or ""
            views = int(row.get("views") or 0)
            likes = int(row.get("likes") or 0)
            comments = int(row.get("comments") or 0)
            shares = int(row.get("shares") or 0)
            tiktok_url = row.get("tiktok_url") or f"https://www.tiktok.com/@{handle}/video/{vid}"
            corpus_analysis = row.get("analysis_json") or {}
            if not corpus_analysis:
                logger.warning(
                    "[corpus_context] corpus row %s has no analysis_json — skipping", vid
                )
                continue
            awemes.append({
                "aweme_id": vid,
                "author": {"unique_id": handle},
                "tiktok_url": tiktok_url,
                "thumbnail_url": row.get("thumbnail_url"),
                "statistics": {
                    "play_count": views,
                    "digg_count": likes,
                    "comment_count": comments,
                    "share_count": shares,
                },
                # Use pre-computed engagement_rate from corpus (more accurate than
                # recomputing from raw counts, which excludes shares in some APIs).
                "_corpus_er": float(row.get("engagement_rate") or 0.0),
                # create_time=0 intentional: we pre-filter by indexed_at above.
                "create_time": 0,
                # Pre-built analysis from corpus — skip re-analysis in pipeline.
                "_from_corpus": True,
                "_corpus_analysis": corpus_analysis,
                "_corpus_tiktok_url": tiktok_url,
            })
        return awemes
    except Exception as exc:
        logger.warning("[corpus_context] fetch_corpus_reference_pool failed: %s", exc)
        return []


async def get_signal_grades_for_niche(
    niche_id: int,
) -> dict[str, str]:
    """Return {hook_type: signal} for most recent week in a niche.

    Falls back to {} on any error (signal grades may not be computed yet).
    """
    try:
        client = _anon_client()
        result = (
            client.table("signal_grades")
            .select("hook_type, signal")
            .eq("niche_id", niche_id)
            .order("week_start", desc=True)
            .limit(20)
            .execute()
        )
        seen: dict[str, str] = {}
        for row in (result.data or []):
            ht = row.get("hook_type", "")
            sig = row.get("signal", "stable")
            if ht and ht not in seen:
                seen[ht] = sig
        return seen
    except Exception as exc:
        logger.warning("[corpus_context] get_signal_grades_for_niche failed: %s", exc)
        return {}
