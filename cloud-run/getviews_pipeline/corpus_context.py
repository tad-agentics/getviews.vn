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
import threading
from datetime import UTC
from typing import Any, Literal

from getviews_pipeline.claim_tiers import (
    CLAIM_TIERS,
    HOOK_EFFECTIVENESS_MIN_PER_BUCKET,
    should_cite_hook_effectiveness,
)
from getviews_pipeline.formatters import citation_vi, timeframe_vi
from getviews_pipeline.postgrest_time import indexed_at_cutoff_iso
from getviews_pipeline.settings import settings as _settings

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

            url = _settings.supabase_url
            key = _settings.supabase_anon_key
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
            .gte("indexed_at", indexed_at_cutoff_iso(days))
        )
        if niche_id is not None:
            query = query.eq("ingest_loop_niche_id", niche_id)
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
            .gte("indexed_at", indexed_at_cutoff_iso(days))
            .order("breakout_multiplier", desc=True)
            .limit(limit)
        )
        if niche_id is not None:
            query = query.eq("ingest_loop_niche_id", niche_id)
        result = query.execute()
        return result.data or []
    except Exception as exc:
        logger.warning("[corpus_context] get_top_breakout_videos failed: %s", exc)
        return []


def _fetch_creator_format_history_sync(
    client: Any,
    handle: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Sync inner — called via run_sync."""
    # Strip leading @ if present
    h = handle.lstrip("@").lower()
    result = (
        client.table("video_corpus")
        .select("video_id, views, content_type, indexed_at, breakout_multiplier")
        .ilike("creator_handle", h)
        .order("views", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def aggregate_creator_format_history_from_rows(
    rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Build format-split stats from ``video_corpus`` rows (top-by-views slice)."""
    if not rows:
        return None
    carousels = [r for r in rows if (r.get("content_type") or "video") == "carousel"]
    videos = [r for r in rows if (r.get("content_type") or "video") != "carousel"]

    carousel_views = [int(r.get("views") or 0) for r in carousels if r.get("views")]

    carousel_avg = int(sum(carousel_views) / len(carousel_views)) if carousel_views else None
    recent_video_rows = sorted(
        videos, key=lambda r: r.get("indexed_at") or "", reverse=True,
    )[:5]
    recent_video_views = [
        int(r.get("views") or 0) for r in recent_video_rows if r.get("views")
    ]
    video_recent_avg = (
        int(sum(recent_video_views) / len(recent_video_views))
        if recent_video_views
        else None
    )

    multiplier: float | None = None
    if carousel_avg and video_recent_avg and video_recent_avg > 0:
        multiplier = round(carousel_avg / video_recent_avg, 1)

    return {
        "total_posts": len(rows),
        "carousel_count": len(carousels),
        "video_count": len(videos),
        "carousel_avg_views": carousel_avg,
        "video_recent_avg": video_recent_avg,
        "top_carousel_views": max(carousel_views) if carousel_views else None,
        "multiplier": multiplier,
    }


def format_creator_format_history_for_diagnosis(
    handle: str,
    creator_history: dict[str, Any] | None,
) -> str:
    """ME-20 — markdown block for video/carousel diagnosis prompts (corpus-backed only).

    Surfaces carousel vs recent-video view ratio only when signal is clear:
    ``multiplier`` ≥ 1.5 (carousel stronger) or ≤ 0.7 (video stronger). Between
    those, keeps baseline stats without a verdict line (reduces noisy copy).
    """
    _h = (handle or "").strip().lstrip("@")
    if not _h or not creator_history:
        return ""
    cc = int(creator_history.get("carousel_count") or 0)
    if cc <= 0:
        return ""

    vc = int(creator_history.get("video_count") or 0)
    total = int(creator_history.get("total_posts") or 0)
    cavg = creator_history.get("carousel_avg_views")
    vavg = creator_history.get("video_recent_avg")
    mult_raw = creator_history.get("multiplier")
    top_cv = creator_history.get("top_carousel_views")

    lines = [
        "## LỊCH SỬ FORMAT KÊNH (từ kho phân tích)",
        f"Trong {total} bài top của @{_h} trong kho dữ liệu: "
        f"{cc} carousel / {vc} video.",
    ]
    if cavg is not None:
        lines.append(f"Trung bình views carousel: {int(cavg):,}.")
    if vavg is not None:
        lines.append(f"Trung bình views video gần đây (5 bài): {int(vavg):,}.")

    if mult_raw is not None and cavg is not None and vavg is not None:
        try:
            m = float(mult_raw)
        except (TypeError, ValueError):
            m = 0.0
        if m >= 1.5:
            lines.append(
                f"Carousel của kênh đạt trung bình {m:.1f}× view so với video gần đây "
                f"— ưu tiên carousel khi chiến lược hợp ngách."
            )
        elif m <= 0.7 and m > 0:
            inv = round(1.0 / m, 1)
            lines.append(
                f"Video gần đây đạt khoảng {inv:.1f}× view so với carousel trung bình "
                f"— carousel chưa phải thế mạnh; cân nhắc nâng carousel hoặc tập trung video."
            )

    if top_cv is not None:
        lines.append(f"Carousel top nhất của kênh: {int(top_cv):,} views.")
    lines.append(
        "Dùng dữ liệu này để đưa ra nhận xét cụ thể về xu hướng format của kênh. "
        "KHÔNG bịa đặt số liệu ngoài những con số trên."
    )
    return "\n".join(lines)


def get_creator_format_history_sync(
    handle: str,
    limit: int = 10,
) -> dict[str, Any] | None:
    """Sync variant for non-async callers (e.g. video narrative finalize)."""
    if not handle:
        return None
    try:
        client = _anon_client()
        rows = _fetch_creator_format_history_sync(client, handle, limit)
        return aggregate_creator_format_history_from_rows(rows)
    except Exception as exc:
        logger.warning(
            "[corpus_context] get_creator_format_history_sync @%s failed: %s", handle, exc,
        )
        return None


async def fetch_creator_format_history(
    handle: str,
    limit: int = 10,
) -> dict[str, Any] | None:
    """Fetch creator's top corpus posts and compute format split + baseline views.

    Returns:
        None        — creator not in corpus (omit the section; never fabricate)
        dict        — {
            total_posts:        int,
            carousel_count:     int,
            video_count:        int,
            carousel_avg_views: int | None,
            video_recent_avg:   int | None,   # avg of last 5 non-carousel posts
            top_carousel_views: int | None,
            multiplier:         float | None,  # carousel_avg / video_recent_avg
        }
    """
    if not handle:
        return None
    try:
        client = _anon_client()
        from getviews_pipeline.runtime import run_sync  # avoid circular at module level
        rows = await run_sync(_fetch_creator_format_history_sync, client, handle, limit)
        return aggregate_creator_format_history_from_rows(rows)
    except Exception as exc:
        logger.warning("[corpus_context] fetch_creator_format_history @%s failed: %s", handle, exc)
        return None


async def get_niche_intelligence(niche_name: str) -> dict[str, Any]:
    """DEPRECATED shim — aggregates ``content_class_intelligence`` for a niche name.

    Resolves legacy ``niche_taxonomy`` id → creator niche → junction classes.
    Prefer ``content_class_intelligence`` directly when ``content_class_id`` known.
    """
    try:
        client = _anon_client()
        niche_id = _resolve_niche_id(client, niche_name)

        if niche_id is None:
            logger.info("[corpus_context] niche '%s' not found in niche_taxonomy", niche_name)
            return {}

        from getviews_pipeline.profile_niches import creator_niche_id_for_legacy_niche
        from getviews_pipeline.video_niche_benchmark import (
            fetch_creator_niche_aggregate_intelligence_sync,
        )

        cn_id = creator_niche_id_for_legacy_niche(niche_id)
        if cn_id is None:
            return {}
        row = fetch_creator_niche_aggregate_intelligence_sync(client, cn_id)
        return row or {}
    except Exception as exc:
        logger.warning("[corpus_context] get_niche_intelligence failed for '%s': %s", niche_name, exc)
        return {}


def fetch_latest_sound_radar(client: Any, niche_id: int) -> dict[str, Any]:
    """Latest trend_velocity.sound_trends JSON for Sound Radar (accelerating/peaking/cooling)."""
    if niche_id <= 0:
        return {}
    try:
        res = (
            client.table("trend_velocity")
            .select("sound_trends,week_start")
            .eq("niche_id", niche_id)
            .order("week_start", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return {}
        st = rows[0].get("sound_trends") or {}
        return st if isinstance(st, dict) else {}
    except Exception as exc:
        logger.warning("[corpus_context] sound_radar niche_id=%s failed: %s", niche_id, exc)
        return {}


def fetch_latest_trending_sound_profile(
    client: Any,
    niche_id: int,
    sound_id: str,
) -> dict[str, Any] | None:
    """Trending_sounds row for this niche+sound (latest week_of)."""
    sid = str(sound_id or "").strip()
    if niche_id <= 0 or not sid:
        return None
    try:
        res = (
            client.table("trending_sounds")
            .select(
                "lifecycle_phase,commercial_music_library_eligible,dialect_audio,"
                "usage_count,week_of,sound_name"
            )
            .eq("niche_id", niche_id)
            .eq("sound_id", sid)
            .order("week_of", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        return rows[0] if isinstance(rows[0], dict) else None
    except Exception as exc:
        logger.warning(
            "[corpus_context] trending_sound profile niche=%s sound=%s failed: %s",
            niche_id, sid[:16], exc,
        )
        return None


def enrich_niche_meta_with_sound_radar(
    niche_id: int,
    niche_meta: dict[str, Any],
) -> dict[str, Any]:
    """Attach sound_radar snapshot for §6 signal extractors (read-only)."""
    if niche_id <= 0:
        return niche_meta
    client = _anon_client()
    radar = fetch_latest_sound_radar(client, niche_id)
    if radar:
        niche_meta = {**niche_meta, "sound_radar": radar}
    return niche_meta


def lookup_trending_sound_profile_for_diagnosis(
    niche_id: int,
    sound_id: str,
) -> dict[str, Any] | None:
    """Service-role-free lookup for live diagnosis path."""
    return fetch_latest_trending_sound_profile(_anon_client(), niche_id, sound_id)


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


def _build_reference_awemes_from_rows(
    rows: list[dict[str, Any]],
    *,
    exclude_video_id: str | None,
) -> list[dict[str, Any]]:
    """Map ``video_corpus`` PostgREST rows → aweme-shaped dicts for ref selection."""
    import math
    from datetime import datetime

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

        indexed_at_str = row.get("indexed_at") or ""
        try:
            indexed_dt = datetime.fromisoformat(indexed_at_str.replace("Z", "+00:00"))
            days_ago = max(
                0,
                math.floor((datetime.now(UTC) - indexed_dt).total_seconds() / 86400),
            )
            create_time = int(indexed_dt.timestamp())
        except Exception:
            days_ago = 0
            create_time = 0

        breakout = float(row.get("breakout_multiplier") or 0.0)

        desc_bits: list[str] = []
        at = str(corpus_analysis.get("audio_transcript") or "").strip()
        if at:
            desc_bits.append(at[:160])
        topics = corpus_analysis.get("topics") or []
        if isinstance(topics, list) and topics:
            desc_bits.append(" ".join(str(t) for t in topics[:6]))
        cc = corpus_analysis.get("content_context")
        if isinstance(cc, dict):
            sm = str(cc.get("subject_matter") or "").strip()
            if sm:
                desc_bits.append(sm[:160])
        ref_desc = " ".join(desc_bits).strip()

        awemes.append({
            "aweme_id": vid,
            "desc": ref_desc,
            "author": {"unique_id": handle},
            "tiktok_url": tiktok_url,
            "thumbnail_url": row.get("thumbnail_url"),
            "statistics": {
                "play_count": views,
                "digg_count": likes,
                "comment_count": comments,
                "share_count": shares,
            },
            "_corpus_er": float(row.get("engagement_rate") or 0.0),
            "_corpus_days_ago": days_ago,
            "_corpus_breakout": breakout,
            "create_time": create_time,
            "_from_corpus": True,
            "_corpus_analysis": corpus_analysis,
            "_corpus_tiktok_url": tiktok_url,
            "_corpus_scenes": corpus_analysis.get("scenes") or [],
            "_corpus_hook_analysis": corpus_analysis.get("hook_analysis") or {},
            "_corpus_content_format": row.get("content_format") or "",
            "_corpus_content_type": row.get("content_type") or "video",
            "_corpus_content_class_id": row.get("content_class_id"),
        })
    return awemes


def content_class_id_for_reference_pool(
    meta: dict[str, Any],
    *,
    content_format: str = "",
) -> int | None:
    """Resolve content_class for evidence pool (corpus row or niche × format heuristic)."""
    raw = meta.get("content_class_id")
    if raw is not None:
        try:
            cc = int(raw)
            return cc if cc > 0 else None
        except (TypeError, ValueError):
            pass
    niche_id = int(meta.get("niche_id") or 0)
    fmt = str(content_format or meta.get("content_format") or "").strip()
    if niche_id and fmt:
        from getviews_pipeline.corpus_ingest import _content_class_for

        cc = _content_class_for(niche_id, fmt)
        return int(cc) if cc else None
    return None


_REFERENCE_POOL_SELECT = (
    "video_id, creator_handle, views, likes, comments, shares, "
    "engagement_rate, breakout_multiplier, tiktok_url, thumbnail_url, "
    "indexed_at, content_format, content_type, content_class_id, analysis_json"
)
# Widen cohort when class-scoped pool is too thin (parity with REF_N / proximity pick).
_REFERENCE_POOL_MIN_SCOPE_ROWS = 5
ReferencePoolScope = Literal["content_class", "junction", "niche"]


def _reference_pool_query(
    client: Any,
    *,
    niche_id: int,
    days: int,
    limit: int,
    scope: ReferencePoolScope,
    content_class_id: int | None,
    junction_class_ids: list[int],
    eligible_only: bool,
) -> Any:
    q = (
        client.table("video_corpus")
        .select(_REFERENCE_POOL_SELECT)
        .gt("views", 0)
        .gte("indexed_at", indexed_at_cutoff_iso(days))
        .order("breakout_multiplier", desc=True, nullsfirst=False)
        .order("engagement_rate", desc=True)
        .limit(limit)
    )
    if scope == "content_class" and content_class_id:
        q = q.eq("content_class_id", content_class_id)
    elif scope == "junction" and junction_class_ids:
        q = q.in_("content_class_id", junction_class_ids)
    else:
        q = q.eq("ingest_loop_niche_id", niche_id)
    if eligible_only:
        q = q.eq("reference_eligible", True)
    return q


def _merge_eligible_reference_rows(
    client: Any,
    *,
    niche_id: int,
    days: int,
    limit: int,
    scope: ReferencePoolScope,
    content_class_id: int | None,
    junction_class_ids: list[int],
) -> list[dict[str, Any]]:
    """Eligible-first ref rows for one cohort scope (§4.7 M2 + class-first browse)."""
    eligible = (
        _reference_pool_query(
            client,
            niche_id=niche_id,
            days=days,
            limit=limit,
            scope=scope,
            content_class_id=content_class_id,
            junction_class_ids=junction_class_ids,
            eligible_only=True,
        )
        .execute()
        .data
        or []
    )
    if len(eligible) >= limit:
        return eligible
    if _settings.corpus_boost_hard_reject:
        return eligible
    seen = {str(r.get("video_id")) for r in eligible if r.get("video_id")}
    merged = list(eligible)
    fallback = (
        _reference_pool_query(
            client,
            niche_id=niche_id,
            days=days,
            limit=limit,
            scope=scope,
            content_class_id=content_class_id,
            junction_class_ids=junction_class_ids,
            eligible_only=False,
        )
        .execute()
        .data
        or []
    )
    for row in fallback:
        vid = str(row.get("video_id") or "")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        merged.append(row)
        if len(merged) >= limit:
            break
    return merged


def _fetch_corpus_reference_rows(
    client: Any,
    *,
    niche_id: int,
    days: int,
    limit: int,
    content_class_id: int | None = None,
) -> tuple[list[dict[str, Any]], ReferencePoolScope]:
    """Class → junction → legacy niche ladder (parity with Home breakouts)."""
    from getviews_pipeline.profile_niches import content_class_ids_for_legacy_niche

    junction_ids = content_class_ids_for_legacy_niche(client, niche_id)
    scopes: list[ReferencePoolScope] = []
    if content_class_id:
        scopes.append("content_class")
    if junction_ids:
        scopes.append("junction")
    scopes.append("niche")

    chosen: list[dict[str, Any]] = []
    chosen_scope: ReferencePoolScope = "niche"
    for scope in scopes:
        rows = _merge_eligible_reference_rows(
            client,
            niche_id=niche_id,
            days=days,
            limit=limit,
            scope=scope,
            content_class_id=content_class_id,
            junction_class_ids=junction_ids,
        )
        if rows:
            chosen = rows
            chosen_scope = scope
        if len(rows) >= _REFERENCE_POOL_MIN_SCOPE_ROWS:
            break
    return chosen, chosen_scope


def fetch_corpus_reference_pool_sync(
    niche_name: str,
    *,
    days: int = 30,
    limit: int = 40,
    exclude_video_id: str | None = None,
    content_class_id: int | None = None,
    legacy_niche_id: int | None = None,
) -> list[dict[str, Any]]:
    """Sync corpus ref pool (no thumbnail repair) for ``finalize_video_narrative_layer``."""
    try:
        client = _anon_client()
        niche_id = int(legacy_niche_id) if legacy_niche_id else _resolve_niche_id(client, niche_name)
        if niche_id is None or niche_id <= 0:
            logger.warning(
                "[corpus_context] fetch_corpus_reference_pool_sync: niche %r not resolved",
                niche_name,
            )
            return []
        rows, scope = _fetch_corpus_reference_rows(
            client,
            niche_id=niche_id,
            days=days,
            limit=limit,
            content_class_id=content_class_id,
        )
        if scope != "niche":
            logger.debug(
                "[corpus_context] reference pool scope=%s niche=%s class=%s rows=%d",
                scope,
                niche_id,
                content_class_id,
                len(rows),
            )
        return _build_reference_awemes_from_rows(rows, exclude_video_id=exclude_video_id)
    except Exception as exc:
        logger.warning("[corpus_context] fetch_corpus_reference_pool_sync failed: %s", exc)
        return []


async def fetch_corpus_reference_pool(
    niche_name: str,
    *,
    days: int = 30,
    limit: int = 20,
    exclude_video_id: str | None = None,
    content_class_id: int | None = None,
    legacy_niche_id: int | None = None,
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
        niche_id = int(legacy_niche_id) if legacy_niche_id else _resolve_niche_id(client, niche_name)

        if niche_id is None or niche_id <= 0:
            logger.warning(
                "[corpus_context] fetch_corpus_reference_pool: niche '%s' not in taxonomy — "
                "falling back to live search. Add signal_hashtags entry to fix.",
                niche_name,
            )
            return []

        rows, scope = _fetch_corpus_reference_rows(
            client,
            niche_id=niche_id,
            days=days,
            limit=limit,
            content_class_id=content_class_id,
        )
        if scope != "niche":
            logger.debug(
                "[corpus_context] reference pool scope=%s niche=%s class=%s rows=%d",
                scope,
                niche_id,
                content_class_id,
                len(rows),
            )

        awemes = _build_reference_awemes_from_rows(rows, exclude_video_id=exclude_video_id)

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
    """Return True if the URL points to R2 (permanent) rather than TikTok CDN (signed/expiring).

    Checks against R2_PUBLIC_URL only — intentionally excludes R2_VIDEO_PUBLIC_URL.

    Rationale: this function is called exclusively on ``thumbnail_url`` values from
    ``video_corpus``. All three thumbnail write helpers (``copy_first_frame_to_thumbnail``,
    ``upload_thumbnail_bytes``, ``download_and_upload_thumbnail``) construct the public
    URL using ``R2_PUBLIC_URL``. Video clips are the only assets written via
    ``R2_VIDEO_PUBLIC_URL``, and video clip URLs never appear in ``thumbnail_url``.

    Including R2_VIDEO_PUBLIC_URL in this check would cause ``refresh_stale_thumbnails``
    to skip repair for any thumbnail_url that happens to start with the video CDN domain
    (e.g. due to data corruption or future code path mistakes), silently leaving those
    rows with a broken thumbnail URL.

    Falls back to the default Cloudflare ``pub-*.r2.dev`` URL pattern for deployments
    that use the raw r2.dev URL (R2_PUBLIC_URL is unset or unchanged from default).
    """
    if not url:
        return False
    from getviews_pipeline.config import R2_PUBLIC_URL
    if R2_PUBLIC_URL:
        base = R2_PUBLIC_URL.rstrip("/")
        if url.startswith(base + "/") or url == base:
            return True
    # Fallback: default Cloudflare R2 public URL pattern
    return url.startswith("https://pub-")


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
        from getviews_pipeline.ensemble import cover_url_from_aweme_detail, fetch_post_multi_info
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
            fresh_url = cover_url_from_aweme_detail(detail)
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
