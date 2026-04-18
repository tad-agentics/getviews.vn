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

import asyncio
import logging
import os
import threading
from typing import Any

from getviews_pipeline.claim_tiers import (
    CLAIM_TIERS,
    HOOK_EFFECTIVENESS_MIN_PER_BUCKET,
    should_cite_hook_effectiveness,
)
from getviews_pipeline.formatters import citation_vi, timeframe_vi

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supabase anon client (read-only — corpus_count uses RLS-allowed SELECT)
# ---------------------------------------------------------------------------

_anon: Any = None
_anon_lock = threading.Lock()


def _anon_client() -> Any:
    """Supabase client with anon key — sufficient for reading video_corpus counts.

    Cached at module level behind a threading.Lock() so the supabase-py client
    is only instantiated once per Cloud Run instance even under concurrent requests.
    Mirrors the pattern used by gemini.py:_get_client().
    """
    global _anon
    with _anon_lock:
        if _anon is None:
            from supabase import create_client  # type: ignore[import-untyped]

            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_ANON_KEY", "")
            if not url or not key:
                raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
            _anon = create_client(url, key)
    return _anon


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

def build_corpus_citation_block(
    count: int,
    niche_name: str,
    days: int,
    *,
    reference_count: int | None = None,
    source: str = "corpus",
) -> str:
    """Return a Vietnamese citation instruction block for synthesis prompt injection.

    The first sentence of the model's output is REQUIRED to echo the citation
    verbatim so the user always sees which corpus slice the answer came from.

    Args:
        count:            Total corpus rows matching (niche_id, days).
        niche_name:       Vietnamese niche label (e.g. "skincare").
        days:             Recency window (used for timeframe phrasing).
        reference_count:  How many were actually pulled into this synthesis
                          (len(analyzed_videos)). Defaults to `count` when None.
        source:           "corpus" — filtered query hit the corpus pool.
                          "live_search" — corpus was too sparse, fell back to
                          keyword/hashtag search; model must disclaim freshness.
                          "sparse_fallback" — no corpus rows at all in niche.

    Modes:
      • count > 0 & source == "corpus"  → canonical citation. Opening sentence required.
      • 0 < count < THRESHOLD           → sparsity disclaimer included.
      • count == 0                       → transparency disclaimer about missing data.
    """
    SPARSE_THRESHOLD = CLAIM_TIERS["basic_citation"]
    cite = citation_vi(count, niche_name, days) if count > 0 else ""
    ref = reference_count if reference_count is not None else count

    # Required opening sentence template — the model MUST echo this verbatim.
    if count >= SPARSE_THRESHOLD and source == "corpus":
        required_opening = (
            f"Dựa trên phân tích {ref} video TikTok về {niche_name} {timeframe_vi(days)}, "
            f"đây là {min(max(ref, 3), 5)} hướng content hiệu quả"
        )
        return (
            f"NGỮ CẢNH DỮ LIỆU: {cite}.\n"
            "BẮT BUỘC: Câu đầu tiên của phản hồi phải bắt đầu bằng: "
            f'"{required_opening}..."\n'
            "Luôn trích dẫn số lượng video và khung thời gian trong mọi nhận định.\n"
            'Dùng cách nói tự nhiên: "tháng này", "tuần này" — không nói "30 ngày gần nhất".\n'
            f'Mọi nhận định xu hướng phải chứa cụm: "{cite}"'
        )

    if 0 < count < SPARSE_THRESHOLD:
        example = (
            f'Chỉ có {count} video {niche_name} trong corpus {timeframe_vi(days)} '
            "— đây là insight sơ bộ, cần kiểm chứng thêm."
        )
        return (
            f"NGỮ CẢNH DỮ LIỆU (DỮ LIỆU THƯA): {cite}.\n"
            "BẮT BUỘC: Câu đầu tiên của phản hồi phải nói rõ số lượng video tham chiếu "
            f'có hạn, VD: "{example}"\n'
            "Không đưa ra tuyên bố mạnh về xu hướng khi dữ liệu thưa."
        )

    if source == "live_search":
        return (
            "NGỮ CẢNH DỮ LIỆU: Corpus không đủ video cho ngách này. "
            "Video tham chiếu lấy từ live search theo từ khóa, không đảm bảo cùng ngách.\n"
            'BẮT BUỘC: Câu đầu tiên phản hồi phải nói: "Chưa có đủ dữ liệu về '
            f'{niche_name} trong corpus — đây là insight từ các video tương tự theo '
            'từ khóa, nên kiểm chứng bằng dữ liệu chuyên ngành."\n'
            "Ghi rõ khi một nhận định suy đoán từ các ngách lân cận."
        )

    # count == 0 and not live_search
    return (
        f"NGỮ CẢNH DỮ LIỆU: Chưa có video nào về {niche_name} trong corpus "
        f"{timeframe_vi(days)}.\n"
        f'BẮT BUỘC: Câu đầu tiên phản hồi phải nói: "Chưa có đủ dữ liệu về '
        f'{niche_name} trong corpus — đây là insight từ các ngách tương tự, cần '
        'kiểm chứng bằng dữ liệu gần đây."\n'
        "Không trích dẫn số lượng cụ thể khi không có dữ liệu."
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


# ---------------------------------------------------------------------------
# Niche label map — resolve niche_id → human label for UI rendering.
# ---------------------------------------------------------------------------

_niche_label_cache: dict[int, str] | None = None
_niche_label_cache_lock = threading.Lock()


def _niche_label_map_sync(client: Any) -> dict[int, str]:
    """Build {niche_id: label} from niche_taxonomy. Prefers Vietnamese name."""
    global _niche_label_cache
    with _niche_label_cache_lock:
        if _niche_label_cache is not None:
            return _niche_label_cache
        try:
            r = (
                client.table("niche_taxonomy")
                .select("id, name_en, name_vn")
                .execute()
            )
            mapping: dict[int, str] = {}
            for row in r.data or []:
                nid = row.get("id")
                if not isinstance(nid, int):
                    continue
                label = row.get("name_vn") or row.get("name_en") or str(nid)
                mapping[nid] = str(label)
            _niche_label_cache = mapping
        except Exception as exc:
            logger.warning("[corpus_context] niche label map fetch failed: %s", exc)
            _niche_label_cache = {}
        return _niche_label_cache


async def get_niche_label_map() -> dict[int, str]:
    """Return {niche_id: label} — cached in-process.

    Used to turn pattern_fingerprint.niche_spread (int array) into display
    chips in the frontend without sending raw integers over the wire.
    """
    from getviews_pipeline.runtime import run_sync

    try:
        return await run_sync(_niche_label_map_sync, _anon_client())
    except Exception as exc:
        logger.warning("[corpus_context] get_niche_label_map failed: %s", exc)
        return {}


def _invalidate_niche_label_cache() -> None:
    """Test hook — clear the in-process niche label map cache."""
    global _niche_label_cache
    with _niche_label_cache_lock:
        _niche_label_cache = None


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


async def resolve_niche_id_cached(
    session: dict[str, Any],
    niche_name: str,
) -> int | None:
    """Resolve a niche name to its niche_taxonomy PK, with in-session caching.

    Cache key is the normalized niche_name, stored in ``session["_niche_ids"]``.
    This supports sessions where the user switches niches across intents — each
    distinct niche_name gets its own cached id, so a "làm đẹp" lookup never
    returns the cached id from a prior "review đồ gia dụng" call.

    On first call for a given niche_name: queries niche_taxonomy via
    name_en / name_vn / signal_hashtags.
    On follow-up calls with the same name: returns the cached integer (no DB hit).

    Returns None when the niche name cannot be matched — callers should pass
    None to get_corpus_count_cached, which counts across all niches as a safe
    fallback.
    """
    key = niche_name.strip().lower()
    cache: dict[str, int | None] = session.setdefault("_niche_ids", {})

    if key in cache:
        return cache[key]

    from getviews_pipeline.runtime import run_sync  # local import avoids circular dep

    try:
        client = _anon_client()
        niche_id = await run_sync(_resolve_niche_id, client, niche_name)
    except Exception as exc:
        logger.warning("[corpus_context] niche_id resolution failed for '%s': %s", niche_name, exc)
        niche_id = None

    cache[key] = niche_id
    return niche_id


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
        from getviews_pipeline.analysis_guards import is_cached_analysis_fresh

        client = _anon_client()
        result = (
            client.table("video_corpus")
            .select("analysis_json, creator_handle, views, tiktok_url, thumbnail_url, indexed_at")
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
        indexed_at = row.get("indexed_at")
        fresh = is_cached_analysis_fresh(indexed_at)
        if fresh:
            logger.info("[corpus_context] cache hit (fresh) for video_id=%s", video_id)
        else:
            logger.info(
                "[corpus_context] cache hit (stale, indexed_at=%s) for video_id=%s — "
                "serving with _stale flag so the synthesis can disclaim",
                indexed_at, video_id,
            )
        return {
            "analysis": analysis,
            "_from_corpus_cache": True,
            "_stale": not fresh,
            "_indexed_at": indexed_at,
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
                "engagement_rate, breakout_multiplier, tiktok_url, thumbnail_url, "
                "indexed_at, content_format, content_type, analysis_json"
            )
            .eq("niche_id", niche_id)
            .gte("indexed_at", f"now() - interval '{days} days'")
            .order("engagement_rate", desc=True)
            .limit(limit)
        )
        result = query.execute()
        rows = result.data or []

        import math
        from datetime import datetime, timezone as _tz

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

            # Compute real days_ago from indexed_at so Gemini emits accurate recency.
            indexed_at_str = row.get("indexed_at") or ""
            try:
                indexed_dt = datetime.fromisoformat(indexed_at_str.replace("Z", "+00:00"))
                days_ago = max(0, math.floor(
                    (datetime.now(_tz.utc) - indexed_dt).total_seconds() / 86400
                ))
                # create_time epoch so helpers can sort; we pre-filter by indexed_at
                create_time = int(indexed_dt.timestamp())
            except Exception:
                days_ago = 0
                create_time = 0

            breakout = float(row.get("breakout_multiplier") or 0.0)

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
                "_corpus_days_ago": days_ago,
                "_corpus_breakout": breakout,
                "create_time": create_time,
                # Pre-built analysis from corpus — skip re-analysis in pipeline.
                "_from_corpus": True,
                "_corpus_analysis": corpus_analysis,
                "_corpus_tiktok_url": tiktok_url,
                # Scene-level pattern data for narrative synthesis.
                "_corpus_scenes": corpus_analysis.get("scenes") or [],
                "_corpus_hook_analysis": corpus_analysis.get("hook_analysis") or {},
                "_corpus_content_format": row.get("content_format") or "",
                "_corpus_content_type": row.get("content_type") or "video",
            })

        # Repair stale (expired TikTok CDN) thumbnails in-place — fire-and-forget,
        # updates DB so subsequent requests get R2 URLs from the start.
        stale_count = sum(1 for a in awemes if not _is_r2_url(a.get("thumbnail_url")))
        if stale_count:
            logger.info(
                "[corpus_context] %d/%d reference videos have stale thumbnails — repairing",
                stale_count, len(awemes),
            )
            await refresh_stale_thumbnails(awemes)

        return awemes
    except Exception as exc:
        logger.warning("[corpus_context] fetch_corpus_reference_pool failed: %s", exc)
        return []


async def get_signal_grades_for_niche(
    niche_id: int,
) -> dict[str, str]:
    """Return {hook_type: signal} for most recent week in a niche.

    Gated by the hook_effectiveness claim tier (claim_tiers.py):
      - Total samples across all hook types must clear CLAIM_TIERS[
        "hook_effectiveness"] (50) — otherwise returns {}. A niche with
        <50 samples is too thin to cite per-hook ER claims honestly.
      - Per-hook rows below HOOK_EFFECTIVENESS_MIN_PER_BUCKET (5) are
        dropped — an individual bucket needs ≥5 instances before its
        reading is anything other than noise.

    Falls back to {} on any error (signal grades may not be computed yet).
    """
    try:
        client = _anon_client()
        result = (
            client.table("signal_grades")
            .select("hook_type, signal, sample_size")
            .eq("niche_id", niche_id)
            .order("week_start", desc=True)
            .limit(50)
            .execute()
        )
        seen: dict[str, str] = {}
        sample_by_hook: dict[str, int] = {}
        for row in (result.data or []):
            ht = row.get("hook_type", "")
            sig = row.get("signal", "stable")
            ss = int(row.get("sample_size") or 0)
            if ht and ht not in seen:
                seen[ht] = sig
                sample_by_hook[ht] = ss
        total_samples = sum(sample_by_hook.values())
        if not should_cite_hook_effectiveness(total_samples):
            logger.info(
                "[corpus_context] niche_id=%s: hook_effectiveness gated — "
                "total_samples=%d < %d",
                niche_id, total_samples, CLAIM_TIERS["hook_effectiveness"],
            )
            return {}
        return {
            ht: sig for ht, sig in seen.items()
            if sample_by_hook.get(ht, 0) >= HOOK_EFFECTIVENESS_MIN_PER_BUCKET
        }
    except Exception as exc:
        logger.warning("[corpus_context] get_signal_grades_for_niche failed: %s", exc)
        return {}


def _is_r2_url(url: str | None) -> bool:
    """Return True if the URL points to R2 (permanent) rather than TikTok CDN (signed/expiring)."""
    return bool(url and url.startswith("https://pub-"))


async def _refresh_thumbnail_async(video_id: str, fresh_cdn_url: str) -> str | None:
    """Download *fresh_cdn_url* and upload to R2; update video_corpus row in the background.

    Returns the R2 URL on success, None on any failure.
    This is fire-and-forget safe — callers should not await the result blocking the main flow.
    """
    try:
        from getviews_pipeline.r2 import download_and_upload_thumbnail, r2_configured
        if not r2_configured():
            return None
        r2_url = await download_and_upload_thumbnail(fresh_cdn_url, video_id)
        if r2_url:
            try:
                from getviews_pipeline.supabase_client import get_service_client
                sb = get_service_client()
                sb.table("video_corpus").update({"thumbnail_url": r2_url}).eq("video_id", video_id).execute()
                logger.info("[corpus_context] repaired thumbnail %s → %s", video_id, r2_url)
            except Exception as db_exc:
                logger.warning("[corpus_context] DB update after thumb repair failed for %s: %s", video_id, db_exc)
        return r2_url
    except Exception as exc:
        logger.debug("[corpus_context] thumbnail refresh failed for %s: %s", video_id, exc)
        return None


async def refresh_stale_thumbnails(awemes: list[dict[str, Any]]) -> None:
    """For corpus aweme dicts with non-R2 thumbnail_url, fire off background R2 upload tasks.

    Fetches fresh CDN URLs via EnsembleData multi-info, uploads to R2, updates DB.
    Results are applied to the aweme dicts in-place so the current request
    benefits immediately if the upload finishes quickly enough.
    """
    stale = [a for a in awemes if not _is_r2_url(a.get("thumbnail_url"))]
    if not stale:
        return

    try:
        from getviews_pipeline.ensemble import fetch_post_multi_info
        stale_ids = [str(a["aweme_id"]) for a in stale if a.get("aweme_id")]
        if not stale_ids:
            return

        fresh_posts = await fetch_post_multi_info(stale_ids)
        fresh_by_id: dict[str, dict] = {}
        for post in fresh_posts:
            detail = post.get("aweme_detail") or post
            vid_id = str(detail.get("aweme_id") or "")
            if vid_id:
                fresh_by_id[vid_id] = detail

        repair_tasks = []
        repair_awemes = []
        for aweme in stale:
            vid_id = str(aweme.get("aweme_id") or "")
            detail = fresh_by_id.get(vid_id)
            if not detail:
                continue
            cover = detail.get("video", {}).get("cover") or {}
            cover_urls = cover.get("url_list") or []
            fresh_url = cover_urls[0] if cover_urls else ""
            if not fresh_url:
                continue
            repair_tasks.append(_refresh_thumbnail_async(vid_id, fresh_url))
            repair_awemes.append(aweme)

        if not repair_tasks:
            return

        results = await asyncio.gather(*repair_tasks, return_exceptions=True)
        for aweme, result in zip(repair_awemes, results):
            if isinstance(result, str) and result:
                aweme["thumbnail_url"] = result

        refreshed = sum(1 for r in results if isinstance(r, str) and r)
        logger.info("[corpus_context] thumbnail refresh: %d/%d repaired", refreshed, len(stale))

    except Exception as exc:
        logger.warning("[corpus_context] refresh_stale_thumbnails failed: %s", exc)
