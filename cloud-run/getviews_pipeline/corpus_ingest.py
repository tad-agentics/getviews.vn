"""Batch corpus ingest: fetch trending posts per niche → analyze → upsert to video_corpus.

Flow per niche:
  1. Fetch top posts via keyword + hashtag search (EnsembleData).
  2. Filter to posts not already in video_corpus (skip known video_ids).
  3. Analyze each post with Gemini (video or carousel path).
  4. Upsert rows to video_corpus via service-role Supabase client.
  5. After all niches complete, refresh niche_intelligence materialized view.
  6. On Sundays: run batch_analytics (creator_velocity + breakout_multiplier)
               + signal_classifier (signal_grades per niche × hook_type).

Designed to run as a Cloud Scheduler cron or via POST /batch/ingest.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import (
    _finish_analysis,
    analyze_aweme,
)
from getviews_pipeline.config import (
    ADAPTIVE_HASHTAG_MIN_FETCH,
    CORPUS_BATCH_POLL_INTERVAL_SEC,
    CORPUS_BATCH_POLL_MAX_SEC,
    CORPUS_INGEST_USE_GEMINI_BATCH,
    CORPUS_LEGACY_CAROUSEL_HASHTAG_FETCH,
    GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
    HASHTAG_YIELD_THRESHOLD,
)
from getviews_pipeline.corpus_boost_suspect import classify_boost_suspect
from getviews_pipeline.corpus_instructiveness import (
    IngestBatchContext,
    _classify_creator_tier,
    corpus_ingest_mode,
    corpus_score_cohort,
    effective_videos_per_niche,
    post_extract_should_reject,
    pre_pool_min_views,
    predict_content_class_pre_score,
    prefetch_ingest_batch_context,
    select_purity_candidates,
    use_class_score_cohort,
)
from getviews_pipeline.creator_blocklist import is_blocklisted_handle, niche_override_for_handle
from getviews_pipeline.ed_budget import theoretical_ed_pool_requests
from getviews_pipeline.extraction_quality import classify_extraction_quality
from getviews_pipeline.gemini import (
    analyze_video,
    build_video_corpus_batch_jsonl_record,
    run_corpus_extraction_batch_file_job,
    upload_local_video_file_active,
)
from getviews_pipeline.hashtag_niche_map import learn_hashtag_mappings
from getviews_pipeline.helpers import (
    DISTRIBUTION_GENERIC_HASHTAGS,
    filter_recency,
    merge_aweme_lists,
)
from getviews_pipeline.hook_type_normalize import normalize_hook_type
from getviews_pipeline.r2 import (
    download_and_upload_video,
    extract_and_upload,
    extract_and_upload_scene_frames,
    r2_configured,
    resolve_ingest_thumbnail_url,
)
from getviews_pipeline.runtime import get_analysis_semaphore
from getviews_pipeline.settings import settings as _ingest_settings
from getviews_pipeline.stats_history_m4 import make_stats_snapshot
from getviews_pipeline.video_shots_writer import (
    build_video_shot_rows,
    upsert_video_shots_sync,
)
from getviews_pipeline.vietnamese_slang import merge_lexicon_slang_into_video_analysis_dict

logger = logging.getLogger(__name__)


def _parse_csv_niche_ids(raw: str) -> frozenset[int]:
    """Comma-separated ``niche_taxonomy.id`` for priority ingest (star niches)."""
    out: set[int] = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part, 10)
        except ValueError:
            logger.warning(
                "[corpus] invalid BATCH_PRIORITY_NICHE_IDS segment, skipping: %r", part
            )
            continue
        if n > 0:
            out.add(n)
    return frozenset(out)


def _parse_hashtag_fetch_by_niche(raw: str) -> dict[int, int]:
    """``BATCH_HASHTAG_FETCH_BY_NICHE`` — ``3:31,5:20`` = niche 3 fetches up to 31 tags."""
    out: dict[int, int] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        left, _, right = part.partition(":")
        try:
            nid, lim = int(left.strip(), 10), int(right.strip(), 10)
        except ValueError:
            logger.warning(
                "[corpus] invalid BATCH_HASHTAG_FETCH_BY_NICHE segment, skipping: %r", part
            )
            continue
        if nid > 0 and lim > 0:
            out[nid] = lim
    return out


def _parse_carousels_by_niche(raw: str) -> dict[int, int]:
    """``BATCH_CAROUSELS_BY_NICHE`` — ``2:8,15:1`` = legacy niche 2 takes 8 carousels/night."""
    out: dict[int, int] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        left, _, right = part.partition(":")
        try:
            nid, lim = int(left.strip(), 10), int(right.strip(), 10)
        except ValueError:
            logger.warning(
                "[corpus] invalid BATCH_CAROUSELS_BY_NICHE segment, skipping: %r", part
            )
            continue
        if nid > 0 and lim >= 0:
            out[nid] = lim
    return out


# ── Config — sourced from settings.py (pydantic-validated at startup) ──────────

from getviews_pipeline.settings import settings as _settings  # noqa: E402

# Default 30 videos/niche/batch; override via env on small ED budgets.
BATCH_VIDEOS_PER_NICHE = _settings.batch_videos_per_niche
BATCH_RECENCY_DAYS = _settings.batch_recency_days

# Wave 5+ Phase 2 — thin-niche prioritization.
CORPUS_TARGET_PER_NICHE = _settings.corpus_target_per_niche
THIN_NICHE_MAX_MULTIPLIER = _settings.thin_niche_max_multiplier

# Star niches — priority ingest.
BATCH_PRIORITY_NICHE_IDS = _parse_csv_niche_ids(_settings.batch_priority_niche_ids)
BATCH_PRIORITY_NICHE_VPN_FLOOR = _settings.batch_priority_niche_vpn_floor
BATCH_PRIORITY_NICHE_MAX_VPN = max(1, _settings.batch_priority_niche_max_vpn)
BATCH_MAX_FAILURES = _settings.batch_max_failures
BATCH_CONCURRENCY = _settings.batch_concurrency

# Quality gates — tune via env vars without redeploying.
BATCH_MIN_VIEWS = _settings.batch_min_views
BATCH_MIN_ER = _settings.batch_min_er
BATCH_KEYWORD_PAGES = _settings.batch_keyword_pages
BATCH_CAROUSELS_PER_NICHE = _settings.batch_carousels_per_niche
BATCH_CAROUSELS_BY_NICHE = _parse_carousels_by_niche(_settings.batch_carousels_by_niche)
BATCH_CAROUSEL_MIN_LIKES = _settings.batch_carousel_min_likes
BATCH_HASHTAG_FETCH_LIMIT = _settings.batch_hashtag_fetch_limit
BATCH_HASHTAG_FETCH_BY_NICHE = _parse_hashtag_fetch_by_niche(_settings.batch_hashtag_fetch_by_niche)


def _carousels_per_night_for_ingest_loop(ingest_loop_niche_id: int) -> int:
    """Carousel slots per batch night — ME-18 per ingest-loop map or uniform default."""
    return BATCH_CAROUSELS_BY_NICHE.get(ingest_loop_niche_id, BATCH_CAROUSELS_PER_NICHE)


def _hashtag_fetch_limit_for_ingest_loop(ingest_loop_niche_id: int) -> int:
    return BATCH_HASHTAG_FETCH_BY_NICHE.get(ingest_loop_niche_id, BATCH_HASHTAG_FETCH_LIMIT)


# Reingest multi-info chunk size.
REINGEST_MULTI_CHUNK = max(1, _settings.reingest_multi_chunk)


def _norm_corpus_hashtag(ht: str) -> str:
    return ht.strip().lstrip("#").lower()


def _pick_hashtags_for_pool_fetch(
    signal_hashtags: list[str],
    yields_by_tag: dict[str, int],
    limit: int,
) -> list[str]:
    """Order hashtags by recent ingest yield; trim adaptive fetch list (see plan §10)."""
    if not signal_hashtags or limit <= 0:
        return []
    tags = list(signal_hashtags)
    tags.sort(
        key=lambda t: yields_by_tag.get(_norm_corpus_hashtag(t), 0),
        reverse=True,
    )
    high = [
        t
        for t in tags
        if yields_by_tag.get(_norm_corpus_hashtag(t), 0) >= HASHTAG_YIELD_THRESHOLD
    ]
    if len(high) >= ADAPTIVE_HASHTAG_MIN_FETCH:
        return high[:limit]
    if high:
        rest = [t for t in tags if t not in high]
        return (high + rest)[:limit]
    return tags[:limit]


def _discovery_relax_effective(niche: dict[str, Any]) -> bool:
    """Env flag OR ACQE Thin/Dormant tier on the ingest target."""
    if _ingest_settings.corpus_discovery_relax:
        return True
    return niche.get("_viability_tier") in ("Thin", "Dormant")


def _resolve_pool_hashtags(
    niche: dict[str, Any],
    yields: dict[str, int],
    ht_limit: int,
    client: Any | None,
) -> list[str]:
    """Class map v2 first, then yield-ranked trim (Thin → top 25 tags)."""
    loop_cc = niche.get("_loop_content_class_id")
    thin = _discovery_relax_effective(niche)
    signal = niche.get("signal_hashtags") or []
    if loop_cc is not None and client is not None:
        from getviews_pipeline.hashtag_class_map import (
            fetch_map_hashtags_for_class_sync,
            pick_hashtags_for_class,
        )

        extra = fetch_map_hashtags_for_class_sync(
            client, int(loop_cc), limit=25 if thin else 15,
        )
        merged = pick_hashtags_for_class(signal, thin=thin, extra_from_map=extra)
        effective_limit = 25 if thin else min(ht_limit, 15)
        if thin and effective_limit < ADAPTIVE_HASHTAG_MIN_FETCH:
            effective_limit = ADAPTIVE_HASHTAG_MIN_FETCH
        return _pick_hashtags_for_pool_fetch(merged, yields, effective_limit)
    return _pick_hashtags_for_pool_fetch(signal, yields, ht_limit)


# ── Result containers ───────────────────────────────────────────────────────────

@dataclass
class IngestResult:
    ingest_loop_niche_id: int
    niche_name: str
    inserted: int = 0
    skipped: int = 0
    failed: int = 0
    subject_matter_inserted: int = 0
    errors: list[str] = field(default_factory=list)
    hi13_batch_line_ok: int = 0
    hi13_batch_line_fail: int = 0
    hi13_sync_fallback: int = 0
    hi13_batch_jobs_ok: int = 0
    hi13_batch_jobs_failed: int = 0
    content_class_id: int | None = None
    pool_raw: int = 0
    candidates_found: int = 0
    hashtags_queried: int = 0


def _merge_sub_ingest_result(dst: IngestResult, src: IngestResult) -> None:
    """Copy counters from ``_ingest_candidate_awemes`` sub-result into ``ingest_niche`` result."""
    dst.inserted = src.inserted
    dst.skipped = src.skipped
    dst.failed = src.failed
    dst.subject_matter_inserted = src.subject_matter_inserted
    dst.errors = src.errors
    dst.hi13_batch_line_ok = src.hi13_batch_line_ok
    dst.hi13_batch_line_fail = src.hi13_batch_line_fail
    dst.hi13_sync_fallback = src.hi13_sync_fallback
    dst.hi13_batch_jobs_ok = src.hi13_batch_jobs_ok
    dst.hi13_batch_jobs_failed = src.hi13_batch_jobs_failed


@dataclass
class BatchSummary:
    total_inserted: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    niches_processed: int = 0
    niche_results: list[dict[str, Any]] = field(default_factory=list)
    materialized_view_refreshed: bool = False
    # Wave 5+ Phase 2 — per-niche quota allocation snapshot. Empty list
    # when deep_pool overrode vpn (no per-niche calc) or when the niche-
    # count fetch failed (the prioritization fail-opens to the uniform
    # default). One entry per niche: ingest_loop_niche_id, niche_name,
    # current_count, multiplier, allocated_vpn.
    thin_niche_allocations: list[dict[str, Any]] = field(default_factory=list)
    # Wall-clock budget guard — set to True when the run stopped early to
    # avoid the Cloud Run request timeout. niches_remaining is the number
    # of niches that were not processed before the budget expired.
    aborted_early: bool = False
    niches_remaining: int = 0
    # H-3 run-marker guard: True when this (utc_day, shift) was already
    # claimed by an earlier run today — the duplicate exits without spending.
    skipped_duplicate_run: bool = False
    ingest_shift: str | None = None
    ingest_shift_count: int = 1
    content_class_ids_planned: list[int] = field(default_factory=list)
    remaining_content_class_ids: list[int] = field(default_factory=list)
    ingest_mode: str = "legacy"
    score_cohort: str = "legacy"
    ingest_loop: str = "niche"
    shadow_metrics: dict[str, Any] = field(default_factory=dict)
    # Wave 2 W2-4 — rows upserted with HI-9 content_context.subject_matter present.
    subject_matter_inserted: int = 0
    hi13_batch_line_ok: int = 0
    hi13_batch_line_fail: int = 0
    hi13_sync_fallback: int = 0
    hi13_batch_jobs_ok: int = 0
    hi13_batch_jobs_failed: int = 0


# ── Thin-niche prioritization (Wave 5+ Phase 2) ────────────────────────────────


def compute_thin_niche_multiplier(
    current_count: int,
    *,
    target: int = CORPUS_TARGET_PER_NICHE,
    max_multiplier: float = THIN_NICHE_MAX_MULTIPLIER,
) -> float:
    """Per-niche quota multiplier in the closed range ``[1.0, max_multiplier]``.

    * ``current_count >= target`` → ``1.0`` (at/above target, no boost)
    * ``current_count == 0``      → ``max_multiplier``
    * linear in the gap fraction between them.

    Pure function; unit-tested in isolation. Behaviour tuned so a ``200``
    target with 3× cap gives a rich 184-row niche ~1.08× (negligible
    extra) and a near-empty 14-row niche ~2.86× (catches up fast).
    """
    if target <= 0 or max_multiplier <= 1.0:
        return 1.0
    gap = max(0, target - max(0, int(current_count)))
    gap_fraction = gap / target  # 0.0 at target, 1.0 when empty
    return 1.0 + (max_multiplier - 1.0) * gap_fraction


def _apply_hi13_batch_metrics(
    result: IngestResult,
    vres: list[Any],
    batch_meta: dict[str, Any],
) -> None:
    """Accumulate HI-13 Batch API line stats from one niche shard job."""
    if not batch_meta:
        return
    if batch_meta.get("ok"):
        result.hi13_batch_jobs_ok += 1
    else:
        result.hi13_batch_jobs_failed += 1
    batch_map = batch_meta.get("by_video_id")
    if not isinstance(batch_map, dict):
        batch_map = {}
    hits = sum(
        1 for entry in batch_map.values()
        if isinstance(entry, dict) and entry.get("ok")
    )
    fails = sum(
        1 for entry in batch_map.values()
        if isinstance(entry, dict) and not entry.get("ok")
    )
    result.hi13_batch_line_ok += hits
    result.hi13_batch_line_fail += fails
    ok_count = sum(1 for r in vres if isinstance(r, tuple))
    result.hi13_sync_fallback += max(0, ok_count - hits)


def apply_thin_niche_multiplier(
    base_vpn: int,
    multiplier: float,
    *,
    hard_cap: int | None = None,
) -> int:
    """Apply the multiplier to ``base_vpn`` and round up to at least 1.

    ``hard_cap`` caps the result so a future misconfig (5× multiplier
    with 50 base) doesn't blow the ED budget. Caller typically passes
    ``base_vpn * max_multiplier`` rounded up.
    """
    raw = max(1, int(round(base_vpn * max(1.0, multiplier))))
    if hard_cap is not None:
        raw = min(raw, hard_cap)
    return raw


def _fetch_niche_counts_sync(client: Any) -> dict[int, int]:
    """Return ``{ingest_loop_niche_id: row_count}`` for every ingest loop in video_corpus.

    Used by ``run_batch_ingest`` to compute per-niche quota multipliers
    before dispatching. Fails open to an empty dict on any DB error —
    the batch then runs with the default (uniform) quota, which is the
    pre-Phase-2 behaviour.
    """
    try:
        resp = (
            client.table("video_corpus")
            .select("ingest_loop_niche_id")
            .not_.is_("ingest_loop_niche_id", "null")
            .limit(50_000)  # well over any realistic corpus size
            .execute()
        )
    except Exception as exc:
        logger.warning("[corpus] niche-count fetch failed (non-fatal): %s", exc)
        return {}
    counts: dict[int, int] = {}
    for row in resp.data or []:
        nid = row.get("ingest_loop_niche_id")
        if nid is None:
            continue
        counts[int(nid)] = counts.get(int(nid), 0) + 1
    return counts


# ── Supabase service-role client ────────────────────────────────────────────────

def _service_client() -> Any:
    """Create a Supabase client with service_role key (bypasses RLS for batch writes)."""
    from getviews_pipeline.supabase_client import get_service_client

    return get_service_client()


def _load_hashtag_yields_all_sync(client: Any) -> dict[int, dict[str, int]]:
    """ingest_loop_niche_id → { normalized_hashtag → ingest_count } for last 14d (RPC)."""
    try:
        result = client.rpc("corpus_hashtag_yields_14d", {}).execute()
    except Exception as exc:
        logger.warning(
            "[corpus] corpus_hashtag_yields_14d RPC failed (run migration 20260429180000?): %s",
            exc,
        )
        return {}
    out: dict[int, dict[str, int]] = {}
    for row in result.data or []:
        try:
            nid = int(row.get("niche_id"))  # RPC column alias → ingest_loop_niche_id
        except (TypeError, ValueError):
            continue
        ht = _norm_corpus_hashtag(str(row.get("hashtag") or ""))
        if not ht:
            continue
        try:
            cnt = int(row.get("ingest_count") or 0)
        except (TypeError, ValueError):
            cnt = 0
        out.setdefault(nid, {})[ht] = cnt
    return out


# ── Distribution annotations ────────────────────────────────────────────────────
# Alias for annotate_distribution() — the full distribution-generic set lives in
# helpers.DISTRIBUTION_GENERIC_HASHTAGS so both this module and hashtag_niche_map
# use the identical filter (no local copy → no divergence risk).
GENERIC_HASHTAGS: frozenset[str] = DISTRIBUTION_GENERIC_HASHTAGS


def annotate_distribution(hashtags: list[str], caption: str | None) -> dict[str, Any]:
    """Compute distribution annotations from ED metadata.

    These are NOT quality gates — all rows are still ingested regardless.
    They annotate each video so niche_intelligence can compute:
      - pct_has_specific_hashtags: % of top videos with ≥1 niche-specific hashtag
      - pct_has_caption_text: % of top videos with real text beyond hashtags
      - avg_hashtag_count: hashtag volume norms per niche
      - pct_original_sound: already exists in niche_intelligence (from is_original_sound)

    These feed into the synthesis prompt, enabling data-backed distribution claims:
      "92% top video trong ngách skincare có caption + hashtag cụ thể cho ngách.
       Video bạn chỉ có 4 hashtag tiếng Anh chung chung (#trending #ootd) —
       thuật toán không biết đẩy cho ai."
    """
    tags_lower = [t.lower() for t in (hashtags or [])]

    # True = at least 1 hashtag is niche-specific (not in the generic noise list)
    has_specific = any(t not in GENERIC_HASHTAGS for t in tags_lower)

    # True = caption contains ≥10 chars of non-hashtag text
    has_caption_text = False
    if caption:
        stripped = re.sub(r"#\w+\s*", "", caption).strip()
        has_caption_text = len(stripped) > 10

    return {
        "has_vietnamese_hashtags": has_specific,
        "has_caption_text": has_caption_text,
        "hashtag_count": len(tags_lower),
    }


# ── Niche fetching ──────────────────────────────────────────────────────────────

async def _fetch_niches(client: Any) -> list[dict[str, Any]]:
    """Return all rows from niche_taxonomy."""
    result = client.table("niche_taxonomy").select("id, name_en, name_vn, signal_hashtags").execute()
    return result.data or []


async def _existing_video_ids(client: Any, niche_id: int) -> set[str]:
    """Return set of all video_ids already in video_corpus (global, not per-niche).

    Phase 6.3 audit: the ``niche_id`` parameter is kept for backward
    compatibility but the query is intentionally global. A video can migrate
    between niches during re-indexing; a per-niche check would miss it and
    trigger a redundant Gemini analysis. Global dedup is the correct scope.
    See ``_existing_video_ids_sync`` and ``_load_all_existing_video_ids_sync``.
    """
    _ = niche_id  # intentionally global — see docstring
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _load_all_existing_video_ids_sync(client))


# ── Post pool fetch ─────────────────────────────────────────────────────────────

async def _fetch_keyword_pages(
    term: str,
    *,
    max_pages: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch keyword search results, following nextCursor.

    ``max_pages`` defaults to BATCH_KEYWORD_PAGES (deep-pool ingest can pass a larger cap).
    Stops early when a page contributes **no** new ``aweme_id`` values vs prior pages
    (adaptive keyword paging — saves ED units when the feed is exhausted / duplicate-heavy).
    """
    pages = max_pages if max_pages is not None else BATCH_KEYWORD_PAGES
    all_awemes: list[dict[str, Any]] = []
    cursor: int = 0
    seen_aweme_ids: set[str] = set()
    for page in range(pages):
        try:
            awemes, next_cursor = await ensemble.fetch_keyword_search(
                term, period=BATCH_RECENCY_DAYS, cursor=cursor
            )
            new_ids = 0
            for a in awemes:
                aid = str(a.get("aweme_id") or "")
                if aid and aid not in seen_aweme_ids:
                    seen_aweme_ids.add(aid)
                    new_ids += 1
            all_awemes.extend(awemes)
            logger.debug(
                "[corpus] keyword='%s' page=%d fetched=%d new_ids=%d next_cursor=%s",
                term, page, len(awemes), new_ids, next_cursor,
            )
            if next_cursor is None or not awemes:
                break
            # Only skip further pages when a non-first page repeats only IDs we already saw.
            if page > 0 and awemes and new_ids == 0:
                logger.info(
                    "[corpus] keyword='%s' early-exit after page=%d (0 new aweme_ids)",
                    term,
                    page,
                )
                break
            cursor = next_cursor
        except Exception as exc:
            logger.warning("[corpus] keyword search page %d failed for '%s': %s", page, term, exc)
            break
    return all_awemes


async def _fetch_niche_pool(
    niche: dict[str, Any],
    *,
    keyword_pages: int | None = None,
    hashtag_yields: dict[str, int] | None = None,
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """Fetch posts for a niche via keyword search (paginated) + all signal hashtags, merged + deduped."""
    term = (niche.get("name_en") or "").strip()

    # Keyword search: paginated — broadens pool beyond a single page of ~20 posts
    keyword_task = _fetch_keyword_pages(term, max_pages=keyword_pages)
    # Cap hashtag fetch calls; class map v2 first, then yield-ranked trim.
    yields = hashtag_yields or {}
    ht_limit = _hashtag_fetch_limit_for_ingest_loop(int(niche["id"]))
    fetch_hashtags = _resolve_pool_hashtags(niche, yields, ht_limit, client)
    hashtag_tasks = [
        ensemble.fetch_hashtag_posts(ht.lstrip("#"), cursor=0)
        for ht in fetch_hashtags
    ]

    all_results = await asyncio.gather(keyword_task, *hashtag_tasks, return_exceptions=True)

    all_awemes: list[dict[str, Any]] = []
    for res in all_results:
        if isinstance(res, Exception):
            logger.warning("[corpus] pool fetch error: %s", res)
            continue
        if isinstance(res, tuple):
            awemes, _ = res
        elif isinstance(res, list):
            awemes = res
        else:
            continue
        all_awemes.extend(awemes)

    merged = merge_aweme_lists(all_awemes, [])
    return filter_recency(merged, BATCH_RECENCY_DAYS)


_CAROUSEL_MULTI_INFO_CHUNK = 50  # max IDs per tt/post/multi-info call


async def _fetch_carousel_pool(
    niche: dict[str, Any],
    *,
    hashtag_yields: dict[str, int] | None = None,
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """Fetch carousel posts (aweme_type=2) for a niche from signal hashtag feeds.

    ED's keyword search surfaces mostly videos. Carousels live in hashtag feeds
    but are mixed with videos. This function fetches the same hashtag feeds and
    filters to aweme_type=2 (photo carousel) only.

    Quality proxy: uses digg_count (likes) instead of play_count because TikTok
    does not report play_count reliably for carousels in feed API responses —
    the field is often 0 even for high-reach carousels.

    Root-cause fix: TikTok's mobile API omits ``image_post_info.images`` from
    feed/list responses (hashtag, keyword). ``detect_content_type`` therefore
    always returns "video" on raw feed objects. When the first-pass filter finds
    0 carousels we call ``fetch_post_multi_info`` on the pool IDs (in chunks) to
    get full detail objects that include ``image_post_info``, then re-filter.
    """
    yields = hashtag_yields or {}
    ht_limit = _hashtag_fetch_limit_for_ingest_loop(int(niche["id"]))
    fetch_hashtags = _resolve_pool_hashtags(niche, yields, ht_limit, client)
    if not fetch_hashtags:
        return []
    hashtag_tasks = [
        ensemble.fetch_hashtag_posts(ht.lstrip("#"), cursor=0)
        for ht in fetch_hashtags
    ]
    results = await asyncio.gather(*hashtag_tasks, return_exceptions=True)

    all_awemes: list[dict[str, Any]] = []
    for res in results:
        if isinstance(res, Exception):
            logger.warning("[corpus] carousel hashtag fetch error: %s", res)
            continue
        awemes, _ = res if isinstance(res, tuple) else (res, None)
        all_awemes.extend(awemes or [])

    # First-pass filter using lightweight feed objects
    carousels = [a for a in all_awemes if ensemble.detect_content_type(a) == "carousel"]

    if not carousels and all_awemes:
        # Feed objects lack image_post_info — enrich via multi-info to get full detail.
        aweme_ids = [str(a.get("aweme_id", "") or "") for a in all_awemes]
        aweme_ids = [aid for aid in aweme_ids if aid]
        chunks = [
            aweme_ids[i : i + _CAROUSEL_MULTI_INFO_CHUNK]
            for i in range(0, len(aweme_ids), _CAROUSEL_MULTI_INFO_CHUNK)
        ]
        enriched: list[dict[str, Any]] = []
        for chunk in chunks:
            try:
                enriched.extend(await ensemble.fetch_post_multi_info(chunk))
            except Exception as exc:
                logger.warning("[corpus] carousel multi-info enrichment error: %s", exc)
        if enriched:
            carousels = [a for a in enriched if ensemble.detect_content_type(a) == "carousel"]
            logger.info(
                "[corpus] carousel pool for niche '%s': %d carousels from %d enriched posts"
                " (multi-info pass)",
                niche.get("name_en", "?"), len(carousels), len(enriched),
            )
        else:
            logger.info(
                "[corpus] carousel pool for niche '%s': 0 carousels — multi-info enrichment"
                " returned no data for %d feed posts",
                niche.get("name_en", "?"), len(all_awemes),
            )
    else:
        logger.info(
            "[corpus] carousel pool for niche '%s': %d carousels from %d total hashtag posts",
            niche.get("name_en", "?"), len(carousels), len(all_awemes),
        )

    return filter_recency(carousels, BATCH_RECENCY_DAYS)


def _carousel_pool_from_merged_video_pool(
    pool: list[dict[str, Any]],
    *,
    niche_name: str,
) -> list[dict[str, Any]]:
    """Derive carousel candidates from the same merged pool as videos (no 2nd hashtag pass)."""
    carousels = [
        a for a in pool if ensemble.detect_content_type(a) == "carousel"
    ]
    logger.info(
        "[corpus] carousel pool (merged) niche='%s': %d carousels from pool size %d",
        niche_name,
        len(carousels),
        len(pool),
    )
    return filter_recency(carousels, BATCH_RECENCY_DAYS)


# ── Single post ingest ──────────────────────────────────────────────────────────

_VIETNAMESE_PATTERN = re.compile(
    r"[\u00c0-\u024f\u1e00-\u1eff\u0300-\u036f]"  # diacritics common in Vietnamese
)


def _has_vietnamese_chars(text: str) -> bool:
    """Return True if the text contains Vietnamese diacritical characters.

    Vietnamese uses precomposed Unicode characters (e.g. ắ, ề, ượ) in the
    Latin Extended-A/B and Latin Extended Additional blocks. A single match is
    sufficient — any diacritic signals a high probability of Vietnamese content.
    English, Korean, and Japanese captions won't have these characters.
    """
    return bool(_VIETNAMESE_PATTERN.search(text))


def _safe_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _safe_engagement_rate(
    *,
    er_from_analysis: float | None,
    views: int,
    likes: int,
    comments: int,
    shares: int,
) -> float:
    """Return engagement rate as a percentage. Never returns >100 or infinity.

    Priority:
      1. Use er_from_analysis when views > 0 (already correctly calculated in parse_metadata)
      2. Recalculate from raw counts when er_from_analysis is None but views > 0
      3. Return 0 when views = 0 (never divide by zero)
    """
    if views <= 0:
        return 0.0
    if er_from_analysis is not None:
        er = float(er_from_analysis)
        # Sanity cap: ER > 100% signals a calculation error
        return min(er, 100.0)
    return min((likes + comments + shares) / views * 100.0, 100.0)


# ── Corpus classifiers ─────────────────────────────────────────────────────────
# Python equivalents of src/lib/batch/classifiers.ts — keep in sync.

_VN_PATTERN = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)

_SOUTHERN = [
    r"\btui\b", r"\bmấy bà\b", r"\bnè\b", r"\bnha\b", r"\bhông\b",
    r"\bquá trời\b", r"\bdzậy\b", r"\bvầy\b", r"\bbiết hông\b",
    r"á(?=\s|[.,!?])", r"\btrời ơi\b", r"\bluôn á\b",
    r"\bnghen\b", r"\bhen\b", r"\bquá xá\b",
]
_NORTHERN = [
    r"\bmình\b", r"\bcác bạn\b", r"\bnhé\b", r"ạ(?=\s|[.,!?])",
    r"\bcực kỳ\b", r"\bthế\b", r"\bvậy à\b", r"\bbiết không\b",
    r"\bkhông ạ\b", r"\bấy\b", r"\bđấy\b", r"\bcơ\b",
]
_CENTRAL = [r"\bchi\b", r"\bmô\b(?=\s)", r"\bni\b", r"\brứa\b", r"\brăng\b"]


def _normalize_promotion_type(raw: Any) -> str:
    s = str(raw or "organic").strip().lower()
    if s in ("organic", "brand_deal", "affiliate", "self_promotion"):
        return s
    return "organic"


def _normalize_str_list(raw: Any, *, max_items: int, max_len: int) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw[:max_items]:
        if x is None:
            continue
        t = str(x).strip()[:max_len]
        if t:
            out.append(t)
    return out


def classify_format(analysis_json: dict[str, Any], legacy_niche_id: int) -> str:
    from getviews_pipeline.content_format_guards import guard_content_format

    return guard_content_format(
        _classify_format_core(analysis_json, legacy_niche_id),
        analysis_json,
    )


def _classify_format_core(analysis_json: dict[str, Any], legacy_niche_id: int) -> str:
    """Classify a video's content format from its Gemini analysis.

    ━━━ TAXONOMY LOCK — READ BEFORE CHANGING ━━━
    The 19 values this function can return are a hard contract shared across 7 layers:

        corpus_ingest.py     → writes content_format into video_corpus (DB column)
        output_redesign.py   → FORMAT_ANALYSIS_WEIGHTS keyed to these 15 values;
                               get_analysis_focus() switches on them; diagnosis prompt
                               injects format-specific signal priorities
        gemini.py            → reads content_format from corpus; passes to
                               build_diagnosis_narrative_prompt() and
                               build_carousel_diagnosis_narrative_prompt()
        layer0_niche.py      → queries content_format for formula detection
                               (top formula = best hook_type × content_format pair)
        niche_intelligence   → format_distribution JSONB aggregated from content_format;
                               used in diagnosis framing and Layer 0A synthesis
        prompts.py           → format_distribution injected into corpus citation blocks

    ANY taxonomy change (add / rename / remove a value) requires ALL of the above to
    change atomically in a single migration + deploy. Backfilling existing DB rows via
    SQL UPDATE is also required — old values will silently fall through to the "other"
    branch in FORMAT_ANALYSIS_WEIGHTS, degrading diagnosis quality.

    The plan §M.8 proposal (Gemini Flash-Lite reclassification into react/unbox/list/
    trending_hook) was evaluated and DEFERRED. Regex classification is intentional here:
    it is deterministic, zero-cost, and zero-latency. Switching to Gemini classification
    adds ~$0.002/video in extraction cost and a round-trip latency with no quality gain
    for the primary use-case (format_distribution benchmarking). If the taxonomy is
    expanded in the future, add new values to FORMAT_ANALYSIS_WEIGHTS FIRST, run the
    migration + backfill SECOND, then update this function THIRD.

    PRIORITY ORDER — intentional, highest specificity first:

    1. mukbang   — eating/ASMR signals are highly specific; checked before recipe/review.
    2. grwm      — "get ready with me" is a named ritual format; checked before tutorial.
    3. gameplay  — Wave 5+ taxonomy expansion. niche=17 OR game-title topics.
                   Checked early so gaming entertainment doesn't get captured by
                   mukbang/storytelling/dance via its entertaining tone + action scenes.
                   See ``artifacts/docs/taxonomy-expansion.md`` §6.1.
    4. recipe    — cooking actions (nấu, chiên, ướp) are more specific than generic "cách làm".
                   NOTE: "hướng dẫn nấu ăn" matches recipe here, NOT tutorial (line below).
                   This is intentional — recipe is more semantically precise for food content.
    5. haul      — unboxing/haul signals are unambiguous; checked before review.
    6. review    — broad category. Intentionally catches "review + tutorial" combos because
                   the dominant intent of such videos is evaluation, not instruction.
                   NOTE: "so sánh + review" → review wins here. Comparison is checked below
                   only for videos without explicit review vocabulary.
    7. tutorial  — how-to instruction; falls here only if not caught by recipe/grwm above.
    8. comparison — "vs / so sánh" without review vocabulary.
    9. lesson    — Wave 5+ taxonomy expansion. Educational content WITHOUT procedural how-to
                   verbs (vocab drills, parenting advice, "word of the day"). Lands AFTER
                   comparison so career-vs-career content with 'kinh nghiệm' stays
                   comparison. See §6.3 (doc §7 puts this at 8; dogfood moved it to 9).
    10. comedy_skit — Wave 5+ taxonomy expansion. (niche=13 AND humorous) OR comedy-topic
                   match. Placed BEFORE storytelling so scripted dialogue comedy doesn't
                   leak into narrative-recall storytelling. See §6.2.
    11. storytelling — narrative past-tense signals.
    12. before_after — transformation arc signals.
    13. pov       — anchored to the literal string "pov:" at transcript start.
    14. outfit_transition — fashion/transition signals.
    15. vlog      — lifestyle/daily signals; broad, checked late to avoid false positives.
    16. dance     — scene-only classification (no transcript, all action scenes).
    17. faceless  — product/demo scenes without face_to_camera and with spoken transcript.
    18. highlight — Wave 5+ taxonomy expansion. LAST positive match: niche IN
                   (14,16,17,21,22) + entertaining/humorous/inspirational tone +
                   scenes≥4 + short transcript. Heuristic is intentionally loose;
                   must run last so tighter buckets claim their rows first. See §6.4.
    19. other     — fallback.

    These priorities affect format_distribution in niche_intelligence. If the observed
    distribution for a niche looks wrong, check whether the ranking above needs adjustment
    for that niche's vocabulary before adding niche-specific overrides.
    """
    transcript = (analysis_json.get("audio_transcript") or "").lower()
    topics = " ".join(t.lower() for t in (analysis_json.get("topics") or []))
    scenes = analysis_json.get("scenes") or []
    tone = analysis_json.get("tone") or ""
    combined = f"{transcript} {topics}"

    from getviews_pipeline.content_format_guards import (
        detect_foreign_reup,
        haul_regex_matches,
    )

    is_reup = detect_foreign_reup(analysis_json)

    # Wave 5+ taxonomy expansion — topic-keyword sets for the 3 new
    # non-trivial buckets (highlight uses niche + tone + scene only, no
    # topic keywords). See artifacts/docs/taxonomy-expansion.md §6.
    gameplay_topic_re = re.compile(
        r"gaming|esports|liên quân|arena of valor|honor of kings|"
        r"roblox|attack on titan|minecraft|pubg|valorant|league of legends|"
        r"mobile legends|free fire|fortnite|genshin",
    )
    # Strict-comedy markers — fire comedy_skit regardless of niche. Kept
    # tight so generic topic tokens like "couple humor" / "funny kids"
    # (which appear on vlog / outfit rows) don't leak into comedy_skit.
    # ``comedy`` as a bare token is INTENTIONALLY not here — Gemini tags
    # many niches' content with "comedy" as a mood descriptor (fashion
    # videos, vlogs), and the leak rate wasn't worth the coverage.
    comedy_strict_re = re.compile(
        r"\bskit\b|\bprank\b|"
        r"family chaos|relatable memes|hài kịch|tiểu phẩm",
    )
    # Niche-13 gated humor markers — secondary signal, only meaningful
    # when paired with niche=13 (Comedy & Entertainment). Matches the
    # loose "humor"/"funny"/"hài hước" tokens that leak otherwise.
    comedy_n13_markers_re = re.compile(r"\bhumor\b|\bfunny\b|hài hước")
    lesson_topic_re = re.compile(
        r"vocabulary|grammar|language learning|tenses|linguistics|"
        r"từ vựng|ngữ pháp|học tiếng|bài học|kinh nghiệm|"
        r"parenting tip|child development|finance education|tài chính cá nhân",
    )

    # Verbal-first formats (recipe, tutorial) require actual speech in the
    # transcript. Without this gate, a silent-music video with "nấu ăn" in
    # topics trips the recipe rule — caught by the eval harness as the
    # "cat video → recipe" false positive.
    has_speech = bool(transcript.strip()) and not re.search(
        r"không có (lời|tiếng|dialogue)|no speech|no dialogue|"
        r"^\[music|^\[âm nhạc|^\[tiếng|^\[không ",
        transcript.strip()[:100],
    )

    # 2026-06-13 false-positive fix: the old greedy `ăn.*cùng` / `mời.*ăn`
    # matched the bigram "ăn" (inside lăn/chăn/khăn… — no word boundary) spanning
    # the ENTIRE transcript to a far-away "cùng" (almost always "cuối cùng" =
    # "finally"). A cushion-review video (`7647501335624961298`, niche=làm đẹp)
    # was tagged mukbang this way. Anchor "ăn" on a word boundary and bound the
    # gap so only the genuine phrases "ăn cùng" / "mời … ăn" fire.
    if re.search(r"mukbang|eating|asmr|\băn\b[^.]{0,10}\bcùng\b|\bmời\b[^.]{0,15}\băn\b", combined):
        return "mukbang"
    if legacy_niche_id == 4 and len(scenes) >= 10 and tone == "entertaining":
        return "mukbang"
    if re.search(r"grwm|get ready|makeup routine|morning routine|buổi sáng", combined):
        return "grwm"
    # Wave 5+ taxonomy expansion — gameplay (position 3). Niche 17 is a
    # strong prior; the topic regex catches gaming content in other
    # niches (e.g. phone-review niche 9 covering a game launch). Lands
    # BEFORE recipe/review to prevent niche-17 entertainment content
    # from being mis-captured by those regexes via action scenes or
    # "review" vocabulary inside gaming commentary.
    if legacy_niche_id == 17 or gameplay_topic_re.search(combined):
        return "gameplay"
    # 2026-06-13 FP audit: bare ``hấp`` matched the substring inside
    # ``thấp`` (low) and ``hấp thu`` (absorb) — ~320 skincare/finance
    # rows mis-tagged recipe. Anchor cooking verbs; only allow steaming
    # ``hấp`` in explicit dish phrases (hấp cá, hấp gà, …).
    if has_speech and re.search(
        r"công thức|\brecipe\b|\bcách làm\b|nguyên liệu|"
        r"\bnấu\b|\bướp\b|\bxào\b|\bchiên\b|\bnướng\b|"
        r"\bhấp cá\b|\bhấp gà\b|\bhấp tôm\b|\bhấp bí\b|\bhấp rau\b|\bhấp xôi\b|"
        r"\bhấp luôn\b|\bhấp chín\b",
        combined,
    ):
        return "recipe"
    # 2026-06-13 FP audit: greedy ``mua.*về`` bounded; 2026-06-13 reup guard:
    # foreign-reup VN subtitles often contain ``mua về`` / ``review`` without
    # native commerce intent — weak haul requires commerce evidence.
    if haul_regex_matches(combined, analysis_json, is_reup=is_reup):
        return "haul"
    if re.search(
        r"shopee|lazada|tiktok shop",
        combined,
    ) and re.search(
        r"săn được|mua mấy món|trên sàn|shopee mall",
        combined,
    ):
        return "haul"
    if re.search(
        r"\bmua\b[^.]{0,120}(?:\d{1,3}[.,]\d{3}|\d+\s000|\blà\s+\d[\d.,]*)",
        combined,
    ):
        return "haul"
    if re.search(
        r"review|chấm điểm|đánh giá|dùng thử|trải nghiệm|"
        r"ăn đứt|đỉnh hơn|đẳng cấp|phần trình diễn|màn trình diễn",
        combined,
    ):
        return "review"
    # 2026-06-13 FP audit: bare ``cách`` (~45% of tutorial bucket) matched
    # conversational filler (``cách đây``, ``cách ly``). Require how-to
    # phrases ``cách làm`` / ``cách để`` instead of the bare token.
    if has_speech and re.search(
        r"cách làm|cách để|hướng dẫn|tutorial|mẹo|bước|step|tips|"
        r"xác minh|đăng ký|thủ tục|quyết toán|bí quyết",
        combined,
    ):
        return "tutorial"
    if re.search(
        r"vs |so sánh|versus|cái nào|nào hơn|nào tốt|khác nhau|phân biệt|khác biệt|"
        r"nghề .{0,50} và nghề",
        combined,
    ):
        return "comparison"
    # Wave 5+ taxonomy expansion — lesson (position 9, after comparison).
    # Educational content WITHOUT procedural how-to verbs. The Wave 5+
    # design doc placed this at position 8 (before comparison), but
    # dogfood surfaced a priority conflict: career-vs-career comparisons
    # that mention "kinh nghiệm" (lesson trigger) should stay
    # comparison, not flip to lesson. Moving lesson after comparison
    # lets the more-specific "vs"/"so sánh" signal win on that edge.
    # Niche set: EduTok VN (11) — education + language learning merged
    # from former niche 23; lesson-format-natural alongside topic-regex.
    if (
        tone in ("educational", "authoritative")
        and (legacy_niche_id == 11 or lesson_topic_re.search(combined))
    ):
        return "lesson"
    # Wave 5+ taxonomy expansion — comedy_skit (position 10). BEFORE
    # storytelling so scripted dialogue comedy doesn't leak into
    # narrative-recall. Two paths:
    #   (a) strict-comedy topic match (comedy / skit / prank / etc.) —
    #       fires regardless of niche, because these tokens are
    #       specific enough to be unambiguous across niches.
    #   (b) niche=27 gate (legacy 13 pre-20260728) — tone=humorous OR generic humor marker.
    #       Generic markers ("humor", "funny", "hài hước") appear on
    #       vlog / outfit rows too; gating by lifestyle ingest bucket prevents leaks.
    if comedy_strict_re.search(combined) or (
        legacy_niche_id in (13, 27)
        and (tone == "humorous" or comedy_n13_markers_re.search(combined))
    ):
        return "comedy_skit"
    if re.search(
        # Wave 5+ fix (2026-05-13): bare-substring tokens (`story`,
        # `drama`, `skit`) wrapped with ``\b`` word boundaries so
        # ``history`` no longer false-fires storytelling. Multi-word
        # VN phrases (``kể chuyện``, ``đằng sau là``, …) already have
        # implicit boundaries via the space; only the single-token
        # English loanwords needed pinning.
        r"kể chuyện|\bstory\b|hồi đó|hồi nhỏ|ngày xưa|mình từng|"
        r"câu chuyện|kể về|nàng dâu|chàng rể|đằng sau là|"
        r"sự thật|lời kể|chia sẻ câu chuyện|"
        r"hoàn cảnh|kiếp nạn|\bdrama\b|\bskit\b",
        combined,
    ):
        return "storytelling"
    if re.search(r"trước.*sau|before.*after|biến đổi|thay đổi.*ngày|glow.?up", combined):
        return "before_after"
    if re.match(r"pov[: ]", combined.lstrip()):
        return "pov"
    if re.search(r"outfit|ootd|biến hình|transition|mix đồ|phối đồ", combined):
        return "outfit_transition"
    parenting_vlog_re = re.compile(
        r"baby care|parenting|infant care|bath time",
    )
    if (
        parenting_vlog_re.search(topics)
        and tone in ("entertaining", "conversational")
        and any(s.get("type") == "face_to_camera" for s in scenes)
    ):
        return "vlog"
    if re.search(
        r"\bvlog\b|thường ngày|một ngày|hôm nay mình|ngày của|"
        r"sau khi tốt nghiệp|sau khi đi làm|dựng sạp|mở quán|khởi nghiệp",
        combined,
    ):
        return "vlog"
    if scenes and all(s.get("type") == "action" for s in scenes) and not transcript:
        return "dance"
    product_types = {"product_shot", "demo", "action"}
    if (scenes and all(s.get("type") in product_types for s in scenes)
            and len(transcript) > 50
            and not any(s.get("type") == "face_to_camera" for s in scenes)):
        return "faceless"
    # Wave 5+ taxonomy expansion — highlight (position 18, last
    # positive match). Short music-driven reaction/moment clips.
    # Intentionally loose heuristic: runs AFTER dance + faceless so
    # tighter buckets claim their rows first. Niche set: Chị đẹp (6) /
    # Ô tô / Xe máy (14, includes former moto culture 25) / travel (16) /
    # gaming (17) / sports (21). Niche 22 (K-pop / Âm nhạc) was removed
    # when that niche was retired (2026-05-07).
    # Scene count ≥ 4 filters out single-shot videos. Short-transcript
    # gate (≤ 80 chars OR music-only marker) distinguishes from vlog
    # / storytelling (transcript-heavy).
    if (
        legacy_niche_id in (6, 14, 16, 17, 21)
        and tone in ("entertaining", "humorous", "inspirational")
        and len(scenes) >= 4
        and (
            len(transcript.strip()) <= 80
            or re.search(r"\[âm nhạc|\[music", transcript[:40])
        )
    ):
        return "highlight"
    return "other"


# Two-axis niche refactor PR2 — Python mirror of
# ``map_legacy_corpus_to_content_class`` SQL function. Both must stay in
# sync; the SQL handles backfill of existing rows, this handles new
# ingest. Keys: legacy ``niche_taxonomy.id`` (some retired ids preserved
# for cold-clone DBs that still have history). Values: ``content_classifications.id``
# (seeded in 20260510000000_two_axis_niche_pr1_schema). Tightened
# format-specific rules listed first; per-niche fallback last.
def _content_class_for(legacy_niche_id: int, content_format: str | None) -> int | None:
    if legacy_niche_id is None:
        return None
    cf = content_format or ""

    # ── Beauty (legacy 2)
    if legacy_niche_id == 2:
        if cf in ("review", "comparison"):
            return 3
        if cf == "haul":
            return 4
        if cf == "tutorial":
            return 1
        if cf == "grwm":
            return 2
        if cf in ("before_after", "storytelling", "pov"):
            return 5
        return 1
    # ── Fashion (legacy 3)
    if legacy_niche_id == 3:
        if cf == "haul":
            return 7
        if cf in ("review", "comparison"):
            return 8
        if cf in ("outfit_transition", "highlight", "dance"):
            return 9
        if cf in ("vlog", "storytelling", "pov"):
            return 10
        return 6
    # ── Food (legacy 4)
    if legacy_niche_id == 4:
        if cf == "recipe":
            return 13
        if cf == "mukbang":
            return 14
        if cf in ("review", "comparison"):
            return 11
        if cf in ("vlog", "storytelling", "pov"):
            return 12
        return 11
    # ── Business / Finance / Real estate
    if legacy_niche_id == 5:
        if cf in ("haul", "review", "comparison"):
            return 49
        if cf == "tutorial":
            return 48
        if cf == "storytelling":
            return 47
        return 48
    if legacy_niche_id == 10:
        return 51
    if legacy_niche_id == 15:
        if cf == "storytelling":
            return 47
        if cf == "comparison":
            return 46
        return 45
    # ── Family / Parenting (legacy 7)
    if legacy_niche_id == 7:
        if cf == "comedy_skit":
            return 31
        if cf in ("vlog", "storytelling", "pov"):
            return 30
        if cf in ("lesson", "tutorial"):
            return 33
        return 33
    # ── Education (legacy 11, 23)
    if legacy_niche_id in (11, 23):
        if cf == "lesson":
            return 36
        if cf in ("tutorial", "comparison"):
            return 37
        if cf == "storytelling":
            return 38
        return 35
    # ── Tech (legacy 9)
    if legacy_niche_id == 9:
        if cf in ("haul", "review", "comparison"):
            return 40
        if cf == "tutorial":
            return 41
        return 40
    # ── Gaming (legacy 17)
    if legacy_niche_id == 17:
        if cf == "gameplay":
            return 42
        if cf in ("review", "comparison"):
            return 43
        return 42
    # ── Music & Dance (legacy 28)
    if legacy_niche_id == 28:
        if cf == "dance":
            return 29
        if cf in ("highlight", "outfit_transition"):
            return 28
        return 28
    # ── Lifestyle ingest (legacy 13 → 27; 19/20 merged into 27 at ingest)
    if legacy_niche_id in (13, 27):
        if cf == "comedy_skit":
            return 24
        if cf == "dance":
            return 29  # music_dance_choreography — parity with SQL map_legacy_corpus_to_content_class
        if cf in ("storytelling", "pov"):
            return 26
        return 24
    # ── Pets (legacy 19 — cold DB only)
    if legacy_niche_id == 19:
        if cf == "tutorial":
            return 71
        if cf == "lesson":
            return 70
        if cf in ("storytelling", "pov", "comedy_skit"):
            return 72
        return 72
    # ── Home (legacy 20 — cold DB only)
    if legacy_niche_id == 20:
        if cf == "tutorial":
            return 74
        if cf in ("haul", "review"):
            return 73
        return 73
    # ── Music (legacy 22 retired, kept for backfill)
    if legacy_niche_id == 22:
        if cf == "dance":
            return 29
        return 28
    # ── Auto (legacy 14, 25)
    if legacy_niche_id in (14, 25):
        if cf in ("review", "comparison"):
            return 65
        if cf == "tutorial":
            return 67
        if cf in ("vlog", "storytelling"):
            return 66
        return 65
    # ── Travel & Sports (legacy 16, 21)
    if legacy_niche_id == 16:
        if cf == "lesson":
            return 62
        if cf in ("highlight", "outfit_transition"):
            return 63
        return 60
    if legacy_niche_id == 21:
        if cf == "highlight":
            return 64
        if cf == "vlog":
            return 63
        return 64
    # ── Gym / Fitness (legacy 8)
    if legacy_niche_id == 8:
        if cf in ("vlog", "storytelling"):
            return 59
        return 56
    # ── Wellness (legacy 26)
    if legacy_niche_id == 26:
        if cf in ("vlog", "storytelling"):
            return 55
        if cf == "lesson":
            return 53
        return 52
    # ── Retired niches with no special format mapping
    if legacy_niche_id == 1:
        return 49   # Shopee review
    if legacy_niche_id == 6:
        return 23   # Chị đẹp → lifestyle_aesthetic
    if legacy_niche_id == 12:
        return 50   # Livestream
    if legacy_niche_id == 18:
        return 13   # Nấu ăn
    if legacy_niche_id == 24:
        return 46   # Crypto
    return None


def _classify_cta(cta: str | None) -> str | None:
    """Map a raw CTA phrase to one of 7 taxonomy buckets or ``None`` / ``"other"``.

    Regex patterns expanded 2026-05-10 based on the cta-face-detect audit
    (see ``artifacts/docs/cta-face-detect-audit.md``). The audit sampled
    20 "other"-bucketed rows + found that ~70% could route to existing
    buckets given better VN-specific patterns. Additions below cover
    shop-pressure shorthand ("chốt ngay/nhẹ", "săn deal"), try-it
    variations ("áp dụng", "tham khảo", "làm liền", "ghé"),
    external-channel follows ("lên kênh|kênh YT"), DM CTAs
    ("inbox|nhắn mình|nhắn tin"), and part-2 announcements ("video sau").
    """
    if not cta:
        return None
    c = cta.lower()
    if re.search(r"lưu lại|lưu ngay|save|lưu về", c):
        return "save"
    if re.search(
        r"theo dõi|follow|đăng ký|subscribe|"
        r"lên kênh|kênh yt|channel",
        c,
    ):
        return "follow"
    if re.search(
        r"comment|bình luận|cho.*biết|chia sẻ.*bên dưới|"
        r"inbox|nhắn mình|nhắn tin|dm mình",
        c,
    ):
        return "comment"
    if re.search(
        r"giỏ hàng|mua ngay|chốt đơn|đặt hàng|shop|cart|"
        r"chốt ngay|chốt đi|chốt nhẹ|chốt luôn|săn deal|săn sale|săn hàng",
        c,
    ):
        return "shop_cart"
    if re.search(r"link.*bio|bio.*link|link.*comment|link.*mô tả", c):
        return "link_bio"
    if re.search(
        r"còn tiếp|phần 2|part 2|tiếp tục|tập sau|"
        r"video sau|clip sau|kỳ sau|phần tiếp",
        c,
    ):
        return "part2"
    if re.search(
        r"thử đi|thử.*xem|làm.*thử|ăn thử|"
        r"áp dụng|tham khảo|làm liền|ghé|thử áp dụng|nên xem",
        c,
    ):
        return "try_it"
    return "other"


def _detect_commerce(analysis_json: dict[str, Any]) -> bool:
    transcript = (analysis_json.get("audio_transcript") or "").lower()
    overlays = " ".join(
        (t.get("text") or "").lower()
        for t in (analysis_json.get("text_overlays") or [])
    )
    combined = f"{transcript} {overlays}"
    if re.search(r"\d+k\b|\d+đ\b|\d+\.\d+đ|giá.*\d|giảm.*\d+%", combined):
        return True
    if re.search(r"shopee|tiktok shop|lazada|link.*bio|giỏ hàng|mã giảm|voucher|freeship|affiliate", combined):
        return True
    if re.search(r"mua ngay|chốt đơn|đặt hàng|mua.*ở đâu|link.*mua|bán hàng|ra đơn", combined):
        return True
    if re.search(r"flash sale|sale|giảm sốc|giảm giá|khuyến mãi|ưu đãi|hết.*là.*hết", combined):
        return True
    if re.search(r"giá gốc|giá sale|rẻ hơn|đáng tiền|tiết kiệm", combined):
        return True
    cta = (analysis_json.get("cta") or "").lower()
    if cta and re.search(r"mua|chốt|giỏ hàng|shop|link", cta):
        return True
    return False


def _detect_dialect(transcript: str) -> str | None:
    if not transcript or len(transcript) < 20:
        return None
    t = transcript.lower()
    south = sum(1 for p in _SOUTHERN if re.search(p, t))
    north = sum(1 for p in _NORTHERN if re.search(p, t))
    central = sum(1 for p in _CENTRAL if re.search(p, t))
    max_score = max(south, north, central)
    if max_score < 2:
        return None
    if central >= 3:
        return "central"
    if south > north * 1.5:
        return "southern"
    if north > south * 1.5:
        return "northern"
    if south >= 2 and north >= 2:
        return "mixed"
    return "southern" if south > north else "northern"


def _vietnam_hour(create_time: int | None) -> int | None:
    if not create_time:
        return None
    dt = datetime.fromtimestamp(create_time, tz=UTC)
    return (dt.hour + 7) % 24


def _normalize_handle(handle: str) -> str:
    return handle.lstrip("@").lower().strip()


def _niche_signal_hashtags_by_id_from_niches(
    niches: list[dict[str, Any]],
) -> dict[int, list[str]]:
    """All ``niche_taxonomy.id → signal_hashtags`` for batch niche validation."""
    out: dict[int, list[str]] = {}
    for row in niches:
        nid = int(row["id"])
        raw = row.get("signal_hashtags")
        if isinstance(raw, list):
            out[nid] = [str(x) for x in raw]
        else:
            out[nid] = []
    return out


def _normalize_signal_tag_fragment(raw: str) -> str:
    """Lowercase substring needle; strip leading ``#`` (DB tags may include it)."""
    return (raw or "").strip().lstrip("#").lower()


def _haystack_for_niche_resolution(
    analysis: dict[str, Any] | None,
    caption: str | None,
) -> str:
    """Flatten caption + hook phrase + topics into one lowercase search blob."""
    # Audit Pass-2 fix #5 — haystack is intentionally limited to
    # ``caption + hook_phrase`` to stay aligned with the SQL backfill in
    # ``20260708120000_reclassify_misclassified_corpus_niche.sql`` (which
    # uses the same two fields). Including Gemini-extracted ``topics``
    # here would let ingest reassign rows the migration would have left
    # alone, creating drift between historical and incoming data.
    cap = caption or ""
    inner: dict[str, Any] = {}
    if analysis and isinstance(analysis, dict):
        raw_inner = analysis.get("analysis")
        if isinstance(raw_inner, dict):
            inner = raw_inner
    hook = ""
    hook_obj = inner.get("hook_analysis")
    if isinstance(hook_obj, dict):
        hook = str(hook_obj.get("hook_phrase") or "")
    return f"{cap} {hook}".strip().lower()


def _signal_hit_counts_per_niche(
    haystack_lower: str,
    niche_signal_hashtags_by_id: dict[int, list[str]],
) -> dict[int, int]:
    """Per-niche counts: each matching signal tag adds one (substring, case-insensitive)."""
    if not haystack_lower:
        return {nid: 0 for nid in niche_signal_hashtags_by_id}
    counts: dict[int, int] = {}
    for nid, tags in niche_signal_hashtags_by_id.items():
        n = 0
        for t in tags:
            frag = _normalize_signal_tag_fragment(t)
            if frag and frag in haystack_lower:
                n += 1
        counts[nid] = n
    return counts


def _resolve_actual_niche_from_content(
    analysis: dict[str, Any] | None,
    caption: str | None,
    niche_signal_hashtags_by_id: dict[int, list[str]],
    default_niche_id: int,
) -> tuple[int, dict[int, int]]:
    """Pick a niche from signal_hashtag hits when another niche leads by ≥2 hits.

    Mirrors the Sprint 8 SQL backfill: substring match on caption +
    hook_phrase only (intentionally excluding Gemini ``topics``; see
    ``_haystack_for_niche_resolution``).

    Audit Pass-2 fix #7 — returns ``(resolved_nid, per_niche_hits)`` so
    callers logging the decision don't have to recompute the haystack +
    hit map. Empty hits dict when haystack is empty / no signal map.
    """
    if not niche_signal_hashtags_by_id:
        return default_niche_id, {}
    haystack = _haystack_for_niche_resolution(analysis, caption)
    if not haystack:
        return default_niche_id, {}
    counts = _signal_hit_counts_per_niche(haystack, niche_signal_hashtags_by_id)
    if not counts:
        return default_niche_id, {}
    max_hits = max(counts.values())
    if max_hits <= 0:
        return default_niche_id, counts
    best_nid = min(nid for nid, c in counts.items() if c == max_hits)
    default_hits = counts.get(default_niche_id, 0)
    if best_nid != default_niche_id and max_hits >= default_hits + 2:
        return best_nid, counts
    return default_niche_id, counts


_GEMINI_NICHE_CONFIDENCE_FLOOR = 0.6

# TD-6 Wave 1b — per-batch counter for junction rejections (route mode).
_hi11_junction_reject_count = 0


def reset_hi11_junction_reject_count() -> None:
    global _hi11_junction_reject_count
    _hi11_junction_reject_count = 0


def get_hi11_junction_reject_count() -> int:
    return _hi11_junction_reject_count


def _record_hi11_junction_reject(
    *,
    video_id: str,
    creator_niche_id: int | None,
    content_class_id: int | None,
    reason: str,
) -> None:
    global _hi11_junction_reject_count
    _hi11_junction_reject_count += 1
    logger.warning(
        "[corpus] hi11_junction_reject video_id=%s creator_niche_id=%s "
        "content_class_id=%s reason=%s",
        video_id or "?",
        creator_niche_id,
        content_class_id,
        reason,
    )


def _niche_resolution_shadow_fields(
    analysis_json: dict[str, Any],
    resolver_niche_id: int,
    *,
    video_id: str = "",
    content_type: str = "video",
) -> dict[str, Any]:
    """HI-11 shadow telemetry — does not affect ``niche_id`` (hashtag resolver stays canonical).

    Junction-miss logging uses the same format axis as ``_route_niche_and_class_override``:
    carousels prefer ``carousel_format_axis`` (fallback ``format_axis``); videos use
    ``format_axis`` only so stray carousel keys do not skew shadow telemetry.
    """
    from getviews_pipeline.profile_niches import (
        CREATOR_NICHE_SLUG_TO_ID,
        legacy_niche_id_for_creator_niche,
    )
    from getviews_pipeline.two_axis_taxonomy import junction_has_pair

    nc = analysis_json.get("niche_classification")
    if not isinstance(nc, dict):
        return {
            "niche_resolution_source": "hashtag",
            "niche_resolution_confidence": None,
            "inferred_creator_niche_id": None,
        }

    try:
        conf = float(nc.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0

    slug_raw = nc.get("creator_niche_slug")
    slug = str(slug_raw).strip() if slug_raw is not None else ""
    inferred: int | None = CREATOR_NICHE_SLUG_TO_ID.get(slug)

    # HI-9 acceptance: explicit warning when Gemini emits a (niche × format_axis)
    # pair not seeded in ``creator_niche_content_classes``. HI-11 routing will
    # downgrade rather than write NULL content_class_id; the WARN is the signal
    # to grow the junction via migration.
    is_carousel = content_type == "carousel"
    if is_carousel:
        fmt_raw = nc.get("carousel_format_axis") or nc.get("format_axis")
    else:
        fmt_raw = nc.get("format_axis")
    fmt_axis = str(fmt_raw).strip() if fmt_raw is not None else ""
    if slug and fmt_axis and not junction_has_pair(slug, fmt_axis):
        logger.warning(
            "[corpus] junction miss video_id=%s niche=%s format_axis=%s conf=%.2f "
            "— HI-11 will downgrade until junction row added",
            video_id or "?",
            slug,
            fmt_axis,
            conf,
        )

    if conf >= _GEMINI_NICHE_CONFIDENCE_FLOOR and inferred is not None:
        gem_legacy = legacy_niche_id_for_creator_niche(inferred)
        if gem_legacy is not None and gem_legacy != resolver_niche_id:
            logger.info(
                "[corpus] niche shadow disagree video_id=%s gemini_legacy=%s resolver_niche=%s conf=%.2f",
                video_id or "?",
                gem_legacy,
                resolver_niche_id,
                conf,
            )
        return {
            "niche_resolution_source": "gemini_two_axis",
            "niche_resolution_confidence": conf,
            "inferred_creator_niche_id": inferred,
        }

    return {
        "niche_resolution_source": "hashtag",
        "niche_resolution_confidence": conf if conf > 0 else None,
        "inferred_creator_niche_id": None,
    }


def _route_niche_and_class_override(
    analysis: dict[str, Any],
    hashtag_resolved_nid: int,
    *,
    video_id: str,
    loop_content_class_id: int | None = None,
    loop_legacy_niche_id: int | None = None,
) -> tuple[int, int | None]:
    """HI-11 routing — in-niche ``content_class_id`` only (no cross-niche legacy move).

    When ``NICHE_RESOLVER_MODE=route`` and Gemini clears confidence, map
    ``format_axis`` onto the ingest loop's primary ``creator_niche`` junction.
    Legacy ``niche_id`` stays ``hashtag_resolved_nid``; only ``content_class_id``
    may override. Cross-niche Gemini slugs are ignored for routing.
    """
    from getviews_pipeline.config import NICHE_RESOLVER_MODE
    from getviews_pipeline.junction_content_class import (
        content_class_id_for_creator_niche_format,
        creator_niche_has_content_class,
        primary_creator_niche_id_for_content_class,
    )
    from getviews_pipeline.profile_niches import (
        CREATOR_NICHE_ID_TO_SLUG,
        CREATOR_NICHE_SLUG_TO_ID,
        creator_niche_id_for_legacy_niche,
    )
    from getviews_pipeline.two_axis_taxonomy import junction_has_pair

    if NICHE_RESOLVER_MODE != "route":
        return hashtag_resolved_nid, None

    loop_cn = primary_creator_niche_id_for_content_class(loop_content_class_id)
    if loop_cn is None and loop_legacy_niche_id is not None:
        loop_cn = creator_niche_id_for_legacy_niche(int(loop_legacy_niche_id))
    if loop_cn is None:
        return hashtag_resolved_nid, None

    loop_slug = CREATOR_NICHE_ID_TO_SLUG.get(loop_cn)
    if not loop_slug:
        return hashtag_resolved_nid, None

    analysis_json = analysis.get("analysis") or {}
    content_type = analysis.get("content_type", "video")
    is_carousel = content_type == "carousel"
    nc = analysis_json.get("niche_classification")
    if not isinstance(nc, dict):
        return hashtag_resolved_nid, None

    try:
        conf = float(nc.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0

    if conf < _GEMINI_NICHE_CONFIDENCE_FLOOR:
        return hashtag_resolved_nid, None

    gem_slug_raw = nc.get("creator_niche_slug")
    gem_slug = str(gem_slug_raw).strip() if gem_slug_raw is not None else ""
    inferred: int | None = CREATOR_NICHE_SLUG_TO_ID.get(gem_slug) if gem_slug else None
    if inferred is not None and inferred != loop_cn:
        logger.info(
            "[corpus] hi11 in_niche_only ignore_gemini_niche video_id=%s "
            "loop_creator_niche_id=%s gemini_slug=%s",
            video_id or "?",
            loop_cn,
            gem_slug,
        )

    if is_carousel:
        fmt_raw = nc.get("carousel_format_axis") or nc.get("format_axis")
    else:
        fmt_raw = nc.get("format_axis")
    fmt_axis = str(fmt_raw).strip() if fmt_raw is not None else ""
    if not fmt_axis or not junction_has_pair(loop_slug, fmt_axis):
        _record_hi11_junction_reject(
            video_id=video_id,
            creator_niche_id=loop_cn,
            content_class_id=None,
            reason="junction_pair_miss",
        )
        logger.warning(
            "[corpus] hi11 route skip video_id=%s junction_miss_or_empty "
            "loop_slug=%s format_axis=%s",
            video_id or "?",
            loop_slug,
            fmt_axis,
        )
        return hashtag_resolved_nid, None

    cc_id = content_class_id_for_creator_niche_format(loop_cn, fmt_axis)
    if cc_id is None:
        _record_hi11_junction_reject(
            video_id=video_id,
            creator_niche_id=loop_cn,
            content_class_id=None,
            reason="no_cc_row",
        )
        logger.warning(
            "[corpus] hi11 route skip video_id=%s no_cc_row loop_creator_niche_id=%s "
            "format_axis=%s",
            video_id or "?",
            loop_cn,
            fmt_axis,
        )
        return hashtag_resolved_nid, None

    if not creator_niche_has_content_class(loop_cn, cc_id):
        _record_hi11_junction_reject(
            video_id=video_id,
            creator_niche_id=loop_cn,
            content_class_id=cc_id,
            reason="td6_junction_miss",
        )
        logger.warning(
            "[corpus] hi11 route skip video_id=%s td6_junction_miss "
            "loop_creator_niche_id=%s content_class_id=%s format_axis=%s",
            video_id or "?",
            loop_cn,
            cc_id,
            fmt_axis,
        )
        return hashtag_resolved_nid, None

    logger.info(
        "[corpus] hi11 route in_niche_class video_id=%s loop_creator_niche_id=%s "
        "content_class_id=%s hashtag_baseline=%s",
        video_id or "?",
        loop_cn,
        cc_id,
        hashtag_resolved_nid,
    )
    return hashtag_resolved_nid, cc_id


def _build_corpus_row(
    aweme: dict[str, Any],
    analysis: dict[str, Any],
    legacy_niche_id: int,
    *,
    content_class_id_override: int | None = None,
    shadow_resolver_niche_id: int | None = None,
) -> dict[str, Any] | None:
    """Map aweme + analysis result to a video_corpus row dict. Returns None on error."""
    if "error" in analysis or "analysis" not in analysis:
        return None

    metadata = analysis.get("metadata") or {}
    # VideoMetadata serialises stats under "metrics" (not "stats")
    metrics = metadata.get("metrics") or {}
    # Fallback: read raw aweme statistics dict if metrics is empty
    raw_stats = aweme.get("statistics") or {}
    author = metadata.get("author") or {}
    content_type = analysis.get("content_type", "video")

    video_id = str(aweme.get("aweme_id", "") or "")
    if not video_id:
        # An aweme without aweme_id means EnsembleData broke contract — if
        # this ever spikes, the keys are the debugging entry point
        # (audit 2026-06-10 M-9: silent skips were untraceable).
        logger.warning(
            "[corpus] aweme missing aweme_id — skipped. keys=%s", sorted(aweme.keys())
        )
        return None

    handle = _normalize_handle(
        author.get("username")
        or str(aweme.get("author", {}).get("unique_id", "") or "")
        or "unknown"
    )

    tiktok_url = (
        metadata.get("tiktok_url")
        or f"https://www.tiktok.com/@{handle}/video/{video_id}"
    )

    # Thumbnail: first CDN URL from display cover if available.
    # For carousels, aweme.video is absent — fall back to the first slide CDN URL
    # from image_post_info (signed, expiring, but better than NULL). This is then
    # overwritten with a permanent R2 URL by _analyze_carousel (analysis["r2_thumbnail_url"])
    # if R2 is configured, so the expiring URL never reaches the DB in practice.
    video_obj = aweme.get("video") or {}
    cover = video_obj.get("origin_cover") or video_obj.get("cover") or {}
    cover_urls: list[str] = cover.get("url_list") or []
    if not cover_urls and content_type == "carousel":
        image_lists = ensemble.extract_image_url_lists(aweme)
        if image_lists and image_lists[0]:
            cover_urls = [image_lists[0][0]]
    thumbnail_url = cover_urls[0] if cover_urls else None
    # Prefer the permanent R2 URL set by _analyze_carousel, if available.
    r2_thumb = analysis.get("r2_thumbnail_url")
    if r2_thumb:
        thumbnail_url = r2_thumb

    # Video play URL — prefer the permanent R2 clip banked during live
    # analysis (2026-06-11) over the expiring platform H264 URL.
    video_urls = ensemble.extract_video_urls(aweme)
    video_url = analysis.get("r2_video_url") or (video_urls[0] if video_urls else None)

    views = int(metrics.get("views") or raw_stats.get("play_count") or raw_stats.get("playCount") or 0)
    likes = int(metrics.get("likes") or raw_stats.get("digg_count") or 0)
    comments = int(metrics.get("comments") or raw_stats.get("comment_count") or 0)
    shares = int(metrics.get("shares") or raw_stats.get("share_count") or 0)
    saves = int(raw_stats.get("collect_count") or raw_stats.get("collectCount") or 0)

    analysis_json: dict[str, Any] = analysis.get("analysis") or {}
    hook_info: dict[str, Any] = analysis_json.get("hook_analysis") or {}
    scenes: list[dict[str, Any]] = analysis_json.get("scenes") or []

    # ED metadata from aweme
    music: dict[str, Any] = aweme.get("music") or {}
    sound_id = str(music.get("id") or "") or None
    sound_name = music.get("title") or None
    # Detect original sounds via two signal paths (either is sufficient):
    # 1. Explicit API field — EnsembleData may expose music.is_original or music.is_original_sound.
    # 2. Title prefix match — covers EN ("original sound - @handle"), VI ("âm thanh gốc",
    #    "nhạc gốc"), and TikTok Studio uploads ("original audio").
    _music_title_lower = str(sound_name or "").lower()
    is_original_sound = bool(
        music.get("is_original") or music.get("is_original_sound")
        or (sound_name and (
            _music_title_lower.startswith("original sound")
            or _music_title_lower.startswith("original audio")
            or _music_title_lower.startswith("âm thanh gốc")
            or _music_title_lower.startswith("nhạc gốc")
        ))
    )
    create_time: int | None = aweme.get("createTime") or aweme.get("create_time")
    raw_author: dict[str, Any] = aweme.get("author") or {}
    creator_followers: int | None = (
        raw_author.get("follower_count")
        or raw_author.get("followerCount")
        or None
    )
    if creator_followers is not None:
        creator_followers = int(creator_followers)

    # Breakout at ingest: views / creator median play (EnsembleData author stats when enabled).
    author_stats: dict[str, Any] = (
        aweme.get("authorStats")
        or aweme.get("author_stats")
        or {}
    )
    if not author_stats and isinstance(raw_author, dict):
        author_stats = (
            raw_author.get("authorStats")
            or raw_author.get("author_stats")
            or {}
        )
    median_views: int | None = _safe_int(
        author_stats.get("medianPlayCount") or author_stats.get("median_play_count")
    )
    breakout_ratio_ingest: float | None = None
    if median_views and median_views > 0:
        breakout_ratio_ingest = round(float(views) / float(median_views), 2)

    desc = aweme.get("desc") or ""
    hashtags: list[str] = [
        c.get("title") or ""
        for c in (aweme.get("challenges") or [])
        if c.get("title")
    ]

    stitch_setting: dict[str, Any] = aweme.get("stitch_setting") or aweme.get("stitchSetting") or {}
    duet_setting: dict[str, Any] = aweme.get("duet_setting") or aweme.get("duetSetting") or {}
    is_stitch = bool(stitch_setting.get("stitch_type") == 1 or stitch_setting.get("stitchType") == 1)
    is_duet = bool(duet_setting.get("duet_type") == 1 or duet_setting.get("duetType") == 1)

    posted_at = (
        datetime.fromtimestamp(create_time, tz=UTC).isoformat()
        if create_time else None
    )

    transcript: str = analysis_json.get("audio_transcript") or ""

    extraction_quality = classify_extraction_quality(
        analysis_json,
        content_type=content_type,
    )

    # ── Post-extraction quality checks (persist flag; row is still ingested) ──
    _video_duration_approx = scenes[-1].get("end") if scenes else None
    if extraction_quality == "degraded_scenes":
        logger.warning(
            "[corpus_quality] video_id=%s: only %d scene(s) for %.0fs video — "
            "likely coarse extraction; transitions_per_second will be wrong",
            video_id, len(scenes), float(_video_duration_approx or 0),
        )
    elif extraction_quality == "degraded":
        logger.warning(
            "[corpus_quality] video_id=%s: %d scenes but transitions_per_second=0 — "
            "extraction inconsistency",
            video_id, len(scenes),
        )
    if transcript and len(transcript) > 20 and not _VN_PATTERN.search(transcript):
        logger.warning(
            "[corpus_quality] video_id=%s: transcript (%d chars) has no Vietnamese "
            "diacritics — possible English paraphrase or mis-transcription",
            video_id, len(transcript),
        )
    hook_phrase = hook_info.get("hook_phrase") or ""
    if hook_phrase and not _VN_PATTERN.search(hook_phrase) and transcript and _VN_PATTERN.search(transcript):
        logger.warning(
            "[corpus_quality] video_id=%s: hook_phrase %r has no Vietnamese diacritics "
            "but transcript does — likely English paraphrase",
            video_id, hook_phrase[:60],
        )

    _format = classify_format(analysis_json, legacy_niche_id)
    _shadow_nid = (
        shadow_resolver_niche_id if shadow_resolver_niche_id is not None else legacy_niche_id
    )
    _final_cc = (
        content_class_id_override
        if content_class_id_override is not None
        else _content_class_for(legacy_niche_id, _format)
    )
    _loop_cc = aweme.get("_ingest_loop_content_class_id")
    _cohort_mismatch = bool(
        use_class_score_cohort()
        and _loop_cc is not None
        and _final_cc is not None
        and int(_loop_cc) != int(_final_cc)
    )

    return {
        # ── Core columns (existing 17) ──
        "video_id": video_id,
        "content_type": content_type,
        **_niche_resolution_shadow_fields(
            analysis_json,
            _shadow_nid,
            video_id=video_id,
            content_type=content_type,
        ),
        "creator_handle": handle,
        "tiktok_url": tiktok_url,
        "thumbnail_url": thumbnail_url,
        "video_url": video_url,
        "frame_urls": [],
        "analysis_json": analysis_json,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "engagement_rate": _safe_engagement_rate(
            er_from_analysis=analysis.get("engagement_rate") or metadata.get("engagement_rate"),
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
        ),
        "stats_history": [
            make_stats_snapshot(
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                phase="t0",
            )
        ],

        # ── Group A: Gemini analysis extraction (11 columns) ──
        "hook_type": normalize_hook_type(hook_info.get("hook_type") or "other"),
        "hook_phrase": hook_info.get("hook_phrase"),
        "face_appears_at": hook_info.get("face_appears_at"),
        "first_frame_type": hook_info.get("first_frame_type") or "other",
        "video_duration": scenes[-1].get("end") if scenes else None,
        "transitions_per_second": analysis_json.get("transitions_per_second"),
        "tone": analysis_json.get("tone"),
        "text_overlay_count": len(analysis_json.get("text_overlays") or []),
        "scene_count": len(scenes),
        "language": "vi",  # guaranteed by Gate 3/4 in ingest_niche
        "target_audience": str(analysis_json.get("target_audience") or "")[:200],
        "pain_points": _normalize_str_list(analysis_json.get("pain_points"), max_items=3, max_len=160),
        "promotion_type": _normalize_promotion_type(analysis_json.get("promotion_type")),
        "style_tags": _normalize_str_list(analysis_json.get("style_tags"), max_items=8, max_len=64),

        # ── Group B: Vietnamese/Asian TikTok-specific (4 columns) ──
        "content_format": _format,
        # Two-axis niche refactor PR2 — sharp (topic × format) classification
        # for analysis. Mirrors map_legacy_corpus_to_content_class() in
        # supabase/migrations/20260511000000_two_axis_niche_pr2_corpus.sql.
        # HI-11 route mode: junction-derived id bypasses legacy ladder.
        "content_class_id": _final_cc,
        "cta_type": _classify_cta(analysis_json.get("cta")),
        "is_commerce": _detect_commerce(analysis_json),
        "dialect": _detect_dialect(transcript),

        # ── Group C: ED metadata (13 columns) ──
        "saves": saves,
        "save_rate": saves / views if views > 0 else None,
        "breakout_ratio": breakout_ratio_ingest,
        "creator_median_views": median_views,
        "posted_at": posted_at,
        "posting_hour": _vietnam_hour(create_time),
        "sound_id": sound_id,
        "sound_name": sound_name,
        "is_original_sound": is_original_sound,
        "creator_followers": creator_followers,
        "creator_tier": _classify_creator_tier(creator_followers),
        "caption": desc or None,
        "hashtags": hashtags if hashtags else None,
        "is_stitch": is_stitch,
        "is_duet": is_duet,

        # ── Group D: Searchable text (2 columns) ──
        "topics": analysis_json.get("topics") or [],
        "transcript_snippet": transcript[:500] if transcript else None,

        # ── Group E: Distribution annotations (3 columns) ──
        # Computed from ED metadata already in memory — zero incremental API cost.
        # NOT quality gates. Every row is annotated regardless.
        **annotate_distribution(hashtags, desc or None),

        # Phase 0 provenance (ingest loop vs stored cohort)
        "ingest_loop_niche_id": aweme.get("_ingest_loop_niche_id"),
        "ingest_loop_content_class_id": _loop_cc,
        "score_cohort_mismatch": _cohort_mismatch,
        "extraction_quality": extraction_quality,
    }


def _video_pool_gate_diagnostics(
    pool: list[dict[str, Any]],
    existing_ids: set[str],
) -> dict[str, int]:
    """Count why video awemes from the keyword/hashtag pool are not selected (mirrors ingest gates)."""
    d: dict[str, int] = {
        "pool_awemes": len(pool),
        "already_in_corpus_this_niche": 0,
        "no_aweme_id": 0,
        "play_count_zero": 0,
        "below_min_views": 0,
        "failed_vn_gate": 0,
        "below_min_er": 0,
        "passed_video_gates": 0,
    }
    for a in pool:
        vid = str(a.get("aweme_id", "") or "")
        if not vid:
            d["no_aweme_id"] += 1
            continue
        if vid in existing_ids:
            d["already_in_corpus_this_niche"] += 1
            continue
        stats = a.get("statistics") or {}
        play_count = int(stats.get("play_count") or stats.get("playCount") or 0)
        if play_count == 0:
            d["play_count_zero"] += 1
            continue
        if play_count < pre_pool_min_views():
            d["below_min_views"] += 1
            continue
        author = a.get("author") or {}
        region = str(author.get("region") or "").upper()
        if region and region not in ("VN", ""):
            d["failed_vn_gate"] += 1
            continue
        if not region:
            desc = str(a.get("desc") or "")
            if desc and not _has_vietnamese_chars(desc):
                d["failed_vn_gate"] += 1
                continue
        likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)
        comments = int(stats.get("comment_count") or stats.get("commentCount") or 0)
        shares = int(stats.get("share_count") or stats.get("shareCount") or 0)
        er = _safe_engagement_rate(
            er_from_analysis=None,
            views=play_count,
            likes=likes,
            comments=comments,
            shares=shares,
        )
        if er < BATCH_MIN_ER:
            d["below_min_er"] += 1
            continue
        d["passed_video_gates"] += 1
    return d


async def _analyze_videos_gemini_batch_for_corpus(
    niche_name: str,
    video_awemes: list[dict[str, Any]],
) -> tuple[list[Any], dict[str, Any]]:
    """HI-13: one JSONL Batch job (file source) per niche shard, sync fallback.

    Returns ``(results, batch_out)`` where ``results`` has one entry per
    ``video_awemes`` (tuple result, or Exception) matching ``_analyze_one`` video
    success shape: ``(analysis_dict, hook_frame_urls, scene_frame_pairs)``.
    """
    from getviews_pipeline.models import VideoAnalysis
    from getviews_pipeline.services.asr_vietnamese import (
        sync_prepare_vietnamese_asr_supplement,
    )

    n = len(video_awemes)
    if n == 0:
        return [], {}

    sem = get_analysis_semaphore()
    loop = asyncio.get_event_loop()

    @dataclass
    class _P:
        idx: int
        aweme: dict[str, Any]
        video_path: Path
        video_id: str
        file_resource: Any
        gemini_upload_name: str
        frame_urls: list[str]
        asr_prefix: str
        stt_usd: float | None

    async def prep_one(i: int, aweme: dict[str, Any]) -> tuple[int, Any]:
        async with sem:
            try:
                vid = str(aweme.get("aweme_id", "") or "")
                video_urls = ensemble.extract_video_urls(aweme)
                if not video_urls:
                    return i, RuntimeError("No video URLs in aweme")
                try:
                    video_path = await ensemble.download_video(video_urls)
                except Exception as e:
                    return i, e
                metadata = ensemble.parse_metadata(aweme)
                try:
                    asr_prefix, stt_usd = await loop.run_in_executor(
                        None,
                        sync_prepare_vietnamese_asr_supplement,
                        video_path,
                        metadata.video_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[hi14] batch path asr prep failed: %s", exc)
                    asr_prefix, stt_usd = "", None

                from getviews_pipeline.prompts import (
                    build_tiktok_caption_extraction_prefix,
                    merge_extraction_supplemental_prefixes,
                )

                caption_prefix = build_tiktok_caption_extraction_prefix(
                    metadata.description,
                    metadata.hashtags,
                )
                asr_prefix = merge_extraction_supplemental_prefixes(
                    asr_prefix,
                    caption_prefix,
                ) or ""

                async def _noop_frames() -> list[str]:
                    return []

                frame_coro = (
                    extract_and_upload(video_path, vid)
                    if r2_configured()
                    else _noop_frames()
                )
                file_resource, frame_urls = await asyncio.gather(
                    loop.run_in_executor(
                        None,
                        upload_local_video_file_active,
                        video_path,
                    ),
                    frame_coro,
                )
                gname = getattr(file_resource, "name", None) or ""
                return i, _P(
                    idx=i,
                    aweme=aweme,
                    video_path=video_path,
                    video_id=vid,
                    file_resource=file_resource,
                    gemini_upload_name=gname,
                    frame_urls=frame_urls if isinstance(frame_urls, list) else [],
                    asr_prefix=asr_prefix or "",
                    stt_usd=stt_usd,
                )
            except Exception as e:  # noqa: BLE001
                return i, e

    prep_pairs = await asyncio.gather(
        *[prep_one(k, video_awemes[k]) for k in range(n)]
    )
    preps: list[Any] = [None] * n
    for idx, item in prep_pairs:
        preps[idx] = item

    records: list[dict[str, Any]] = []
    gemini_names: list[str] = []
    stt_map: dict[str, float | None] = {}
    for i in range(n):
        entry = preps[i]
        if not isinstance(entry, _P):
            continue
        stt_map[entry.video_id] = entry.stt_usd
        records.append(
            build_video_corpus_batch_jsonl_record(
                entry.video_id,
                entry.file_resource,
                supplemental_user_prefix=entry.asr_prefix or None,
            )
        )
        gemini_names.append(entry.gemini_upload_name)

    batch_map: dict[str, dict[str, Any]] = {}
    batch_out: dict[str, Any] = {}
    if records:
        safe = re.sub(r"[^\w\-]+", "_", niche_name)[:40]
        display_name = f"corpus-{safe}-{int(time.time())}"
        batch_out = await loop.run_in_executor(
            None,
            lambda: run_corpus_extraction_batch_file_job(
                records=records,
                display_name=display_name,
                poll_interval_s=CORPUS_BATCH_POLL_INTERVAL_SEC,
                poll_max_s=CORPUS_BATCH_POLL_MAX_SEC,
                gemini_file_names=gemini_names,
                gcp_stt_cost_by_video_id=stt_map,
            ),
        )
        if batch_out.get("ok") and isinstance(batch_out.get("by_video_id"), dict):
            batch_map = batch_out["by_video_id"]
        else:
            logger.warning(
                "[corpus] batch job failed niche=%s state=%s err=%s",
                niche_name,
                batch_out.get("state"),
                batch_out.get("job_error"),
            )

    results: list[Any] = []
    for i in range(n):
        entry = preps[i]
        if isinstance(entry, Exception):
            results.append(entry)
            continue
        if not isinstance(entry, _P):
            results.append(
                TypeError(f"batch prep unexpected {type(entry).__name__}")
            )
            continue
        p = entry
        vid = p.video_id
        aweme = p.aweme
        video_path = p.video_path
        frame_urls = p.frame_urls

        br = batch_map.get(vid)
        analysis_obj: VideoAnalysis | None = None
        if br and br.get("ok") and br.get("text"):
            try:
                from getviews_pipeline.gemini import parse_batch_extraction_analysis_json

                raw = parse_batch_extraction_analysis_json(str(br["text"]))
                merge_lexicon_slang_into_video_analysis_dict(raw)
                analysis_obj = VideoAnalysis.model_validate(raw)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[corpus] batch JSON validate failed video_id=%s: %s",
                    vid,
                    exc,
                )
                analysis_obj = None

        if analysis_obj is None:
            try:
                analysis_obj = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda path=video_path, pre=p.asr_prefix, usd=p.stt_usd: analyze_video(
                            path,
                            supplemental_user_prefix=(pre or None),
                            gcp_stt_cost_usd=usd,
                        ),
                    ),
                    timeout=GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
                )
            except Exception as exc:  # noqa: BLE001
                results.append(exc)
                try:
                    video_path.unlink(missing_ok=True)
                except OSError:
                    pass
                continue

        metadata = ensemble.parse_metadata(aweme)
        try:
            finished = await _finish_analysis(
                metadata=metadata,
                analysis_obj=analysis_obj,
                metadata_for_diagnosis=metadata.model_dump(),
                include_diagnosis=False,
            )
        except Exception as exc:  # noqa: BLE001
            results.append(exc)
            try:
                video_path.unlink(missing_ok=True)
            except OSError:
                pass
            continue

        scene_frame_pairs: list[tuple[int, str]] = []
        if r2_configured():
            scenes = (finished.get("analysis") or {}).get("scenes") or []
            if scenes:
                try:
                    scene_frame_pairs = await extract_and_upload_scene_frames(
                        video_path,
                        vid,
                        scenes,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[corpus] scene frame extraction (batch path) %s: %s",
                        vid,
                        exc,
                    )

        try:
            video_path.unlink(missing_ok=True)
        except OSError:
            pass

        results.append(
            (
                finished,
                frame_urls if isinstance(frame_urls, list) else [],
                scene_frame_pairs,
            )
        )

    return results, batch_out


async def run_hi13_batch_pilot(
    *,
    limit: int = 10,
    niche_id: int | None = None,
) -> dict[str, Any]:
    """HI-13 pilot — Batch JSONL extraction for ``limit`` videos; no corpus upsert."""
    from getviews_pipeline.config import GEMINI_EXTRACTION_MODEL

    limit = max(1, min(int(limit), 20))
    client = _service_client()
    niches = await asyncio.get_event_loop().run_in_executor(
        None, lambda: fetch_ingest_targets_sync(client),
    )
    if not niches:
        niches = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _fetch_niches_sync(client),
        )
    if niche_id is not None:
        niches = [n for n in niches if int(n["id"]) == int(niche_id)]
    if not niches:
        return {"ok": False, "error": "no_niche", "niche_id": niche_id}

    niche = niches[0]
    nid = int(niche["id"])
    niche_name = niche.get("name_en") or niche.get("name_vn") or str(nid)

    pool = await _fetch_niche_pool(niche, keyword_pages=1, client=client)
    video_awemes: list[dict[str, Any]] = []
    for aweme in pool:
        if ensemble.detect_content_type(aweme) == "carousel":
            continue
        video_awemes.append(aweme)
        if len(video_awemes) >= limit:
            break

    if not video_awemes:
        return {
            "ok": False,
            "error": "no_video_candidates",
            "niche_id": nid,
            "niche_name": niche_name,
            "pool_size": len(pool),
        }

    logger.info(
        "[hi13-pilot] niche=%s id=%d — Batch API for %d videos (no upsert)",
        niche_name,
        nid,
        len(video_awemes),
    )
    results, batch_out = await _analyze_videos_gemini_batch_for_corpus(
        niche_name, video_awemes,
    )

    ok_count = sum(1 for r in results if isinstance(r, tuple))
    err_count = sum(1 for r in results if isinstance(r, Exception))

    batch_ok = bool(batch_out.get("ok"))
    batch_map = batch_out.get("by_video_id") if isinstance(batch_out.get("by_video_id"), dict) else {}
    batch_hits = sum(
        1 for entry in batch_map.values()
        if isinstance(entry, dict) and entry.get("ok")
    )
    batch_line_errors = [
        {"video_id": vid, "error": entry.get("error")}
        for vid, entry in batch_map.items()
        if isinstance(entry, dict) and not entry.get("ok")
    ][:5]

    return {
        "ok": batch_ok and ok_count > 0,
        "niche_id": nid,
        "niche_name": niche_name,
        "model": GEMINI_EXTRACTION_MODEL,
        "requested": limit,
        "candidates": len(video_awemes),
        "batch_job_ok": batch_ok,
        "batch_state": batch_out.get("state"),
        "batch_error": batch_out.get("job_error"),
        "batch_stats": batch_out.get("batch_stats"),
        "batch_line_hits": batch_hits,
        "batch_line_errors": batch_line_errors,
        "analysis_ok": ok_count,
        "analysis_errors": err_count,
        "sync_fallback_count": max(0, ok_count - batch_hits),
        "dry_run": True,
    }


async def _ingest_candidate_awemes(
    client: Any,
    ingest_loop_niche_id: int,
    niche_name: str,
    candidates: list[dict[str, Any]],
    *,
    niche_signal_hashtags_by_id: dict[int, list[str]] | None = None,
    ingest_batch_ctx: IngestBatchContext | None = None,
) -> IngestResult:
    """Analyze prepared aweme dicts and upsert rows (shared by pool ingest + explicit reingest)."""
    from getviews_pipeline.two_axis_taxonomy import extract_subject_matter_from_analysis_json

    result = IngestResult(
        ingest_loop_niche_id=ingest_loop_niche_id, niche_name=niche_name,
    )
    if not candidates:
        return result

    hook_type_counts: dict[str, int] = {}
    # Per-aweme niche (CR-3): ingest_niche stashes creator overrides on each
    # dict; pop here so Ensemble/Gemini paths never see the internal key.
    per_aweme_niche_ids: list[int] = []
    for a in candidates:
        stashed = a.pop("_ingest_niche_id", None)
        per_aweme_niche_ids.append(
            int(stashed) if stashed is not None else ingest_loop_niche_id
        )

    logger.info("[corpus] niche=%s — analyzing %d candidates", niche_name, len(candidates))

    sem = get_analysis_semaphore()

    async def _analyze_one(
        aweme: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], list[tuple[int, str]]]:
        """Return ``(analysis_dict, hook_frame_urls, scene_frame_pairs)``.

        ``hook_frame_urls`` is the existing fixed-timestamp list used for
        diagnosis; ``scene_frame_pairs`` is ``[(scene_index, url), …]``
        for the per-scene ``video_shots.frame_url`` column (Wave 2.5
        Phase A PR #3). Both are ``[]`` for carousels, failed downloads,
        or when R2 is not configured. Scene frames need the Gemini
        analysis to know the scene boundaries, so we run analysis first
        and scene-frame extraction second while the download is still
        on disk.
        """
        async with sem:
            ct = ensemble.detect_content_type(aweme)
            if ct == "carousel":
                analysis = await analyze_aweme(aweme, include_diagnosis=False)
                return analysis, [], []

            video_urls = ensemble.extract_video_urls(aweme)
            if not video_urls:
                return {
                    "error": "No video URLs in aweme",
                    "metadata": ensemble.parse_metadata(aweme).model_dump(),
                }, [], []

            video_path: Path | None = None
            try:
                try:
                    video_path = await ensemble.download_video(video_urls)
                except Exception as e:
                    return {
                        "error": str(e),
                        "metadata": ensemble.parse_metadata(aweme).model_dump(),
                    }, [], []

                vid = str(aweme.get("aweme_id", "") or "")
                async def _noop_frames() -> list[str]:
                    return []

                frame_coro = (
                    extract_and_upload(video_path, vid)
                    if r2_configured()
                    else _noop_frames()
                )
                # Phase 3.3 — route through async_run_extraction_core so all
                # batch ingest flows through the canonical extraction boundary.
                # The result is an ExtractionResult; we unwrap it back to a
                # dict for the downstream upsert helpers (backward compatible).
                from getviews_pipeline.services.extraction import async_run_extraction_core
                extraction_result, frame_urls = await asyncio.gather(
                    async_run_extraction_core(aweme, video_path),
                    frame_coro,
                )
                # Unwrap ExtractionResult → legacy dict shape so downstream
                # helpers (upsert_corpus_extraction, etc.) stay unchanged.
                if extraction_result.error:
                    analysis: dict = {
                        "error": extraction_result.error,
                        "metadata": extraction_result.metadata.model_dump(),
                    }
                else:
                    analysis = {
                        "metadata": extraction_result.metadata.model_dump(),
                        "analysis": extraction_result.analysis.model_dump() if extraction_result.analysis else {},
                        "content_type": extraction_result.content_type,
                        "transcript_quality": extraction_result.transcript_quality,
                        "entry_cost": extraction_result.entry_cost,
                    }

                # Scene-frame extraction (Wave 2.5 Phase A PR #3/#4) —
                # runs AFTER analysis because it needs scene boundaries.
                # Video is still on disk inside this try-block.
                scene_frame_pairs: list[tuple[int, str]] = []
                if r2_configured():
                    scenes = (
                        (analysis.get("analysis") or {}).get("scenes") or []
                    )
                    if scenes:
                        try:
                            scene_frame_pairs = await extract_and_upload_scene_frames(
                                video_path, vid, scenes,
                            )
                        except Exception as exc:  # defensive — the helper
                            # already swallows its own errors, but the
                            # broader ingest must never fail on per-scene
                            # extraction.
                            logger.warning(
                                "[corpus] scene frame extraction raised for %s: %s",
                                vid, exc,
                            )

                return (
                    analysis,
                    frame_urls if isinstance(frame_urls, list) else [],
                    scene_frame_pairs,
                )
            finally:
                if video_path is not None:
                    video_path.unlink(missing_ok=True)

    carousel_indices = [
        i
        for i, a in enumerate(candidates)
        if ensemble.detect_content_type(a) == "carousel"
    ]
    video_indices = [
        i
        for i, a in enumerate(candidates)
        if ensemble.detect_content_type(a) != "carousel"
    ]

    gather_results: list[Any] = [None] * len(candidates)

    if carousel_indices:
        cres = await asyncio.gather(
            *[_analyze_one(candidates[i]) for i in carousel_indices],
            return_exceptions=True,
        )
        for idx, r in zip(carousel_indices, cres, strict=True):
            gather_results[idx] = r

    if video_indices:
        vlist = [candidates[i] for i in video_indices]
        if CORPUS_INGEST_USE_GEMINI_BATCH:
            logger.info(
                "[corpus] niche=%s — HI-13 Batch API for %d videos",
                niche_name,
                len(vlist),
            )
            vres, batch_meta = await _analyze_videos_gemini_batch_for_corpus(niche_name, vlist)
            _apply_hi13_batch_metrics(result, vres, batch_meta)
        else:
            vres = await asyncio.gather(
                *[_analyze_one(candidates[i]) for i in video_indices],
                return_exceptions=True,
            )
        for idx, r in zip(video_indices, vres, strict=True):
            gather_results[idx] = r

    rows: list[dict[str, Any]] = []
    frame_urls_by_video_id: dict[str, list[str]] = {}
    scene_frame_urls_by_video_id: dict[str, dict[int, str]] = {}

    for aweme, gather_result, loop_nid in zip(
        candidates, gather_results, per_aweme_niche_ids
    ):
        if isinstance(gather_result, Exception):
            logger.warning("[corpus] analyze error: %s", gather_result)
            result.failed += 1
            result.errors.append(str(gather_result))
            continue
        analysis, frame_urls, scene_frame_pairs = gather_result
        desc_raw = str(aweme.get("desc") or "")
        challenge_titles = [
            str(c.get("title") or "")
            for c in (aweme.get("challenges") or [])
            if c.get("title")
        ]
        caption_for_resolution = (
            f"{desc_raw} {' '.join(challenge_titles)}".strip()
        )
        signal_map = niche_signal_hashtags_by_id
        if signal_map:
            # Audit Pass-2 fix #7 — resolver now returns the per-niche
            # hits map it computed internally so the call site doesn't
            # rebuild the haystack a second time per candidate.
            resolved_nid, per_niche_hits = _resolve_actual_niche_from_content(
                analysis,
                caption_for_resolution or None,
                signal_map,
                loop_nid,
            )
        else:
            resolved_nid = loop_nid
            per_niche_hits = {}
        vid = str(aweme.get("aweme_id", "") or "")
        if resolved_nid != loop_nid:
            logger.info(
                "[corpus] niche reassigned video_id=%s loop_niche=%s → actual=%s "
                "(caption_hits %s=%s, %s=%s)",
                vid,
                loop_nid,
                resolved_nid,
                loop_nid,
                per_niche_hits.get(loop_nid, 0),
                resolved_nid,
                per_niche_hits.get(resolved_nid, 0),
            )
        from getviews_pipeline.cross_niche_class_remap import resolve_post_route_content_class_id
        from getviews_pipeline.profile_niches import creator_niche_id_for_legacy_niche

        loop_creator_cn = creator_niche_id_for_legacy_niche(loop_nid)
        route_nid, cc_override = _route_niche_and_class_override(
            analysis,
            resolved_nid,
            video_id=vid,
            loop_content_class_id=aweme.get("_ingest_loop_content_class_id"),
            loop_legacy_niche_id=loop_nid,
        )
        cc_override = resolve_post_route_content_class_id(
            analysis.get("analysis") or {},
            route_content_class_id=cc_override,
            video_id=vid,
            loop_creator_niche_id=loop_creator_cn,
        )
        row = _build_corpus_row(
            aweme,
            analysis,
            route_nid,
            content_class_id_override=cc_override,
            shadow_resolver_niche_id=resolved_nid,
        )
        if row is None:
            result.skipped += 1
            err = analysis.get("error")
            logger.warning(
                "[corpus] niche=%s skip video_id=%s (no corpus row) keys=%s err=%s",
                niche_name,
                vid,
                list(analysis.keys())[:14],
                (str(err)[:400] if err is not None else None),
            )
        else:
            _enrich_breakout_ratio_for_row(
                row,
                aweme,
                niche_id=route_nid,
                ingest_batch_ctx=ingest_batch_ctx,
                content_class_id=cc_override
                or aweme.get("_ingest_loop_content_class_id"),
            )
            br = row.get("breakout_ratio")
            reject, reason = post_extract_should_reject(
                row,
                analysis,
                hook_type_counts=hook_type_counts,
                breakout_ratio=float(br) if br is not None else None,
            )
            if reject:
                result.skipped += 1
                logger.info(
                    "[corpus] niche=%s post_extract_reject video_id=%s reason=%s",
                    niche_name,
                    vid,
                    reason,
                )
                continue
            ht = str(row.get("hook_type") or "none")
            hook_type_counts[ht] = hook_type_counts.get(ht, 0) + 1
            stats = aweme.get("statistics") or {}
            v = int(stats.get("play_count") or stats.get("playCount") or 0)
            c = int(stats.get("comment_count") or stats.get("commentCount") or 0)
            likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)
            shares = int(stats.get("share_count") or stats.get("shareCount") or 0)
            er = _safe_engagement_rate(
                er_from_analysis=None,
                views=v,
                likes=likes,
                comments=c,
                shares=shares,
            )
            from getviews_pipeline.corpus_boost_suspect import boost_percentiles_from_niche_intel

            pct = boost_percentiles_from_niche_intel(None)
            if ingest_batch_ctx is not None:
                pct = ingest_batch_ctx.niche_boost.get(route_nid) or ingest_batch_ctx.global_boost
            boost = classify_boost_suspect(
                views=v,
                er=er,
                comments=c,
                percentiles=pct,
                hard_reject_enabled=_ingest_settings.corpus_boost_hard_reject,
            )
            row["boost_attribution"] = boost.attribution
            row["reference_eligible"] = boost.reference_eligible
            row["ingest_relaxation_tier"] = int(
                aweme.get("_ingest_relaxation_tier") or 0
            )
            if _ingest_settings.ed_batch_comment_fetch_enabled:
                try:
                    from getviews_pipeline.comment_radar_cache import resolve_comment_radar

                    radar = await resolve_comment_radar(vid, comment_count_hint=c)
                    if radar:
                        row["comment_radar"] = radar
                except Exception as exc:
                    logger.warning("[corpus] batch comment_radar %s: %s", vid, exc)
            try:
                from getviews_pipeline.pattern_fingerprint import (
                    compute_and_upsert_pattern,
                )

                pattern_id = await compute_and_upsert_pattern(
                    client, analysis.get("analysis") or {}, route_nid,
                )
                if pattern_id:
                    row["pattern_id"] = pattern_id
            except Exception as exc:
                logger.warning("[corpus] pattern fingerprint failed: %s", exc)
            rows.append(row)
            if extract_subject_matter_from_analysis_json(row.get("analysis_json")):
                result.subject_matter_inserted += 1
            if frame_urls:
                frame_urls_by_video_id[row["video_id"]] = frame_urls
            if scene_frame_pairs:
                scene_frame_urls_by_video_id[row["video_id"]] = dict(scene_frame_pairs)

    if rows and r2_configured():
        video_rows = [
            r for r in rows
            if r.get("content_type", "video") == "video"
            and r.get("video_url")
            # Already R2-hosted (live analysis banked the clip) — skip re-upload.
            and "/videos/" not in str(r.get("video_url") or "")
        ]

        for row in video_rows:
            pre_frames = frame_urls_by_video_id.get(row["video_id"], [])
            if pre_frames:
                row["frame_urls"] = pre_frames
                logger.info("[corpus] %s — %d frame(s) from shared download", row["video_id"], len(pre_frames))

        logger.info(
            "[corpus] niche=%s — R2 upload: %d video clips + %d thumbnails",
            niche_name,
            len(video_rows),
            len(rows),
        )

        video_upload_tasks = [
            download_and_upload_video(
                [row["video_url"]],
                row["video_id"],
            )
            for row in video_rows
        ]
        # Derive user-facing ``thumbnails/{video_id}.webp`` (360w). Re-upserts
        # with legacy R2 ``.png`` DB URLs are promoted when WebP is missing on
        # R2 — see ``resolve_ingest_thumbnail_url``.
        async def _row_thumbnail(row: dict[str, Any]) -> str | None:
            return await resolve_ingest_thumbnail_url(
                str(row["video_id"]),
                row.get("thumbnail_url"),
                # Frame-first (2026-06-11): rows whose frames were just
                # extracted from the actual video overwrite any webp that
                # was previously mirrored from a TikTok CDN cover.
                prefer_frame=bool(row.get("frame_urls")),
            )

        thumb_tasks = [_row_thumbnail(row) for row in rows]

        video_results, thumb_results = await asyncio.gather(
            asyncio.gather(*video_upload_tasks, return_exceptions=True),
            asyncio.gather(*thumb_tasks, return_exceptions=True),
        )

        for row, video_result in zip(video_rows, video_results):
            if isinstance(video_result, str) and video_result:
                row["video_url"] = video_result
                logger.info("[corpus] %s — video uploaded to R2: %s", row["video_id"], video_result)
            else:
                # Upload failed (None) or raised — never persist the ephemeral ED
                # CDN link. Drop it; _merge_existing_provenance_sync restores a
                # prior permanent R2 URL when one exists (re-ingest case).
                if isinstance(video_result, Exception):
                    logger.warning(
                        "[corpus] video upload error for %s: %s", row["video_id"], video_result
                    )
                row.pop("video_url", None)

        for row, thumb_result in zip(rows, thumb_results):
            if isinstance(thumb_result, str) and thumb_result:
                row["thumbnail_url"] = thumb_result
                logger.info("[corpus] %s — thumbnail uploaded to R2: %s", row["video_id"], thumb_result)
            elif isinstance(thumb_result, Exception):
                logger.warning("[corpus] thumbnail upload error for %s: %s", row["video_id"], thumb_result)

    if rows:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: _upsert_rows_sync(client, rows)
            )
            result.inserted += len(rows)
            logger.info("[corpus] niche=%s — upserted %d rows", niche_name, len(rows))

            # video_shots dual-write (Wave 2.5 Phase A PR #4). The
            # matcher queries this table directly — see the migration
            # comment in 20260510000003_video_shots_table.sql. Runs
            # after video_corpus because the video_id FK points there;
            # isolated in its own try so a shot-writer failure never
            # rolls back a successful corpus ingest.
            try:
                shot_rows: list[dict[str, Any]] = []
                for row in rows:
                    vid = row["video_id"]
                    shot_rows.extend(
                        build_video_shot_rows(
                            row, scene_frame_urls_by_video_id.get(vid),
                        )
                    )
                if shot_rows:
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: upsert_video_shots_sync(client, shot_rows),
                    )
                    logger.info(
                        "[corpus] niche=%s — upserted %d video_shots rows",
                        niche_name, len(shot_rows),
                    )
            except Exception as exc:
                logger.error(
                    "[corpus] niche=%s video_shots upsert failed: %s",
                    niche_name, exc,
                )

            for row in rows:
                row_hashtags: list[str] = row.get("hashtags") or []
                if row_hashtags:
                    loop_nid = row.get("ingest_loop_niche_id")
                    if loop_nid is not None:
                        await learn_hashtag_mappings(
                            video_hashtags=row_hashtags,
                            niche_id=int(loop_nid),
                            niche_source="corpus_batch",
                            client=client,
                        )
                    cc_learn = row.get("content_class_id")
                    if cc_learn is not None:
                        try:
                            from getviews_pipeline.hashtag_class_map import learn_from_corpus_row

                            await learn_from_corpus_row(
                                client,
                                hashtags=row_hashtags,
                                content_class_id=int(cc_learn),
                            )
                        except Exception as exc:
                            logger.debug("[hashtag_class_map] learn skip: %s", exc)
        except Exception as exc:
            logger.error("[corpus] niche=%s upsert failed: %s", niche_name, exc)
            result.failed += len(rows)
            result.errors.append(f"upsert: {exc}")

    return result


# ── Per-niche ingest ─────────────────────────────────────────────────────────────

async def ingest_niche(
    niche: dict[str, Any],
    client: Any,
    *,
    keyword_pages_override: int | None = None,
    videos_per_niche_override: int | None = None,
    carousels_per_niche_override: int | None = None,
    hashtag_yields_for_niche: dict[str, int] | None = None,
    niche_signal_hashtags_by_id: dict[int, list[str]] | None = None,
    existing_video_ids: set[str] | None = None,
    ingest_batch_ctx: IngestBatchContext | None = None,
) -> IngestResult:
    ingest_loop_niche_id: int = niche["id"]
    niche_name: str = (
        niche.get("name_en") or niche.get("name_vn") or str(ingest_loop_niche_id)
    )
    result = IngestResult(
        ingest_loop_niche_id=ingest_loop_niche_id, niche_name=niche_name,
    )
    loop_cc = niche.get("_loop_content_class_id")
    if loop_cc is not None:
        result.content_class_id = int(loop_cc)

    logger.info(
        "[corpus] niche=%s id=%d — fetching pool",
        niche_name,
        ingest_loop_niche_id,
    )

    try:
        pool = await _fetch_niche_pool(
            niche,
            keyword_pages=keyword_pages_override,
            hashtag_yields=hashtag_yields_for_niche,
            client=client,
        )
    except Exception as exc:
        logger.error("[corpus] niche=%s pool fetch failed: %s", niche_name, exc)
        result.errors.append(f"pool_fetch: {exc}")
        result.failed += 1
        return result

    result.pool_raw = len(pool)
    ht_limit = _hashtag_fetch_limit_for_ingest_loop(int(niche["id"]))
    fetch_hashtags = _resolve_pool_hashtags(
        niche, hashtag_yields_for_niche or {}, ht_limit, client,
    )
    result.hashtags_queried = len(fetch_hashtags)

    if existing_video_ids is not None:
        existing_ids = existing_video_ids
    else:
        existing_ids = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _existing_video_ids_sync(client, ingest_loop_niche_id)
        )

    if CORPUS_LEGACY_CAROUSEL_HASHTAG_FETCH:
        carousel_pool = await _fetch_carousel_pool(
            niche, hashtag_yields=hashtag_yields_for_niche, client=client,
        )
    else:
        carousel_pool = _carousel_pool_from_merged_video_pool(
            pool, niche_name=niche_name
        )

    # ── Quality gates ────────────────────────────────────────────────────────────
    # Shared helper — applies Gates 3+4 (Vietnamese creator/caption checks)
    def _passes_vn_gates(a: dict[str, Any], vid: str) -> bool:
        author = a.get("author") or {}
        region = str(author.get("region") or "").upper()
        if region and region not in ("VN", ""):
            logger.debug("[corpus] skip %s — region=%s (not VN)", vid, region)
            return False
        if not region:
            desc = str(a.get("desc") or "")
            if desc and not _has_vietnamese_chars(desc):
                logger.debug("[corpus] skip %s — no Vietnamese chars in caption and region unknown", vid)
                return False
        return True

    # ── Video candidates ─────────────────────────────────────────────────────────
    mode = corpus_ingest_mode()
    pool_min_views = pre_pool_min_views(mode)
    if _discovery_relax_effective(niche):
        pool_min_views = max(1_000, pool_min_views - 2_000)
    existing_class_map = niche.get("_existing_class_by_video") or {}
    loop_cc_target = niche.get("_loop_content_class_id")
    candidates = []
    blocklist_skipped = 0
    for a in pool:
        vid = str(a.get("aweme_id", "") or "")
        if _should_skip_existing_for_dedup(
            vid,
            existing_ids,
            loop_content_class_id=loop_cc_target,
            existing_class_by_video=existing_class_map,
        ):
            continue

        # Gate 0: news/aggregator blocklist — skip before any expensive
        # check. Vietnamese media outlets (theanh28, vtvcab, kenh14, 24h
        # family, sports/esports news) are NOT creators in our target
        # audience; their videos pollute niche signal and produce fake
        # patterns. Sprint 8.5.
        author_handle = str((a.get("author") or {}).get("unique_id") or "")
        if is_blocklisted_handle(author_handle):
            blocklist_skipped += 1
            logger.debug(
                "[corpus] skip %s — blocklisted handle @%s", vid, author_handle,
            )
            continue

        # Creator-level niche override: some creators are consistently
        # mislabeled by the visual classifier (e.g., business coaches whose
        # talking-head format matches Skincare). Override before row build.
        _niche_override = niche_override_for_handle(author_handle)
        effective_niche_id = (
            _niche_override if _niche_override is not None else ingest_loop_niche_id
        )
        if _niche_override is not None and _niche_override != ingest_loop_niche_id:
            logger.info(
                "[corpus] niche override @%s: %d → %d",
                author_handle, ingest_loop_niche_id, _niche_override,
            )
        a["_ingest_niche_id"] = effective_niche_id
        a["_ingest_loop_niche_id"] = ingest_loop_niche_id
        pre_cc = predict_content_class_pre_score(
            a, loop_niche_id=ingest_loop_niche_id,
        )
        if pre_cc is not None:
            a["_ingest_loop_content_class_id"] = pre_cc
        loop_cc = niche.get("_loop_content_class_id")
        if loop_cc is not None:
            a["_ingest_loop_content_class_id"] = int(loop_cc)

        stats = a.get("statistics") or {}
        play_count = int(stats.get("play_count") or stats.get("playCount") or 0)

        # Gate 1: views must be above zero (no engagement data at all)
        if play_count == 0:
            logger.debug("[corpus] skip %s — play_count=0 (no real stats)", vid)
            continue

        # Gate 2: view floor — legacy flat 20k; shadow/purity defer to Tier 1 tiers
        if play_count < pool_min_views:
            logger.debug(
                "[corpus] skip %s — play_count=%d < pre_pool_min=%d mode=%s",
                vid,
                play_count,
                pool_min_views,
                mode,
            )
            continue

        # Gate 3+4: Vietnamese creator
        if not _passes_vn_gates(a, vid):
            continue

        # Gate 5: minimum engagement rate — filters out dead content that got views but no engagement
        likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)
        comments = int(stats.get("comment_count") or stats.get("commentCount") or 0)
        shares = int(stats.get("share_count") or stats.get("shareCount") or 0)
        er = _safe_engagement_rate(
            er_from_analysis=None,
            views=play_count,
            likes=likes,
            comments=comments,
            shares=shares,
        )
        if er < BATCH_MIN_ER:
            logger.debug("[corpus] skip %s — ER=%.2f%% < min=%.2f%%", vid, er, BATCH_MIN_ER)
            continue

        candidates.append(a)

    signal_tags = (
        (niche_signal_hashtags_by_id or {}).get(ingest_loop_niche_id, [])
    )
    vpn = videos_per_niche_override if videos_per_niche_override is not None else BATCH_VIDEOS_PER_NICHE
    if mode == "purity":
        vpn = effective_videos_per_niche(vpn)

    legacy_sorted = sorted(
        candidates,
        key=lambda a: int((a.get("statistics") or {}).get("play_count", 0) or 0),
        reverse=True,
    )
    legacy_top = legacy_sorted[:vpn]

    if mode in ("shadow", "purity") and ingest_batch_ctx is not None:
        ctx = ingest_batch_ctx
        purity_selected, sel_meta = select_purity_candidates(
            candidates,
            niche_id=ingest_loop_niche_id,
            signal_hashtags=signal_tags,
            k=vpn,
            ctx=ctx,
            er_fn=_safe_engagement_rate,
        )
        if mode == "shadow":
            candidates = legacy_top
            logger.info(
                "[corpus_shadow] niche=%s purity_would_select=%d legacy_select=%d meta=%s",
                niche_name,
                len(purity_selected),
                len(legacy_top),
                sel_meta,
            )
        else:
            candidates = purity_selected
            relax_tier = int(sel_meta.get("relaxation_tier") or 0)
            for c in candidates:
                c["_ingest_relaxation_tier"] = relax_tier
            logger.info(
                "[corpus] niche=%s purity selected=%d relaxation_tier=%s",
                niche_name,
                len(candidates),
                relax_tier,
            )
    else:
        candidates = legacy_top
        if mode == "shadow" and ingest_batch_ctx is None:
            logger.warning(
                "[corpus] shadow mode without batch context — falling back to legacy sort",
            )

    video_candidate_aweme_ids = {
        str(c.get("aweme_id", "") or "") for c in candidates
    }
    video_candidate_aweme_ids.discard("")

    # ── Carousel candidates ──────────────────────────────────────────────────────
    # Carousel quality gates differ from video:
    # - play_count is unreliable for carousels in feed responses (often 0) — use digg_count instead
    # - Gate 1 (play_count > 0) is skipped; Gate 2 replaced with min-likes floor
    # - ER gate is skipped because we have no reliable view denominator
    carousel_candidates = []
    for a in carousel_pool:
        vid = str(a.get("aweme_id", "") or "")
        if _should_skip_existing_for_dedup(
            vid,
            existing_ids,
            loop_content_class_id=loop_cc_target,
            existing_class_by_video=existing_class_map,
        ):
            continue
        # Skip carousels already picked as video candidates (de-dup) — O(1) set lookup
        if vid in video_candidate_aweme_ids:
            continue

        # Gate 0: news/aggregator blocklist — same rule as videos. Sprint 8.5.
        author_handle = str((a.get("author") or {}).get("unique_id") or "")
        if is_blocklisted_handle(author_handle):
            blocklist_skipped += 1
            logger.debug(
                "[corpus] skip carousel %s — blocklisted handle @%s", vid, author_handle,
            )
            continue

        _niche_override = niche_override_for_handle(author_handle)
        effective_niche_id = (
            _niche_override if _niche_override is not None else ingest_loop_niche_id
        )
        if _niche_override is not None and _niche_override != ingest_loop_niche_id:
            logger.info(
                "[corpus] niche override (carousel) @%s: %d → %d",
                author_handle, ingest_loop_niche_id, _niche_override,
            )
        a["_ingest_niche_id"] = effective_niche_id
        a["_ingest_loop_niche_id"] = ingest_loop_niche_id

        stats = a.get("statistics") or {}
        likes = int(stats.get("digg_count") or stats.get("diggCount") or 0)

        # Carousel Gate: minimum likes floor — proxy for reach when play_count is missing
        if likes < BATCH_CAROUSEL_MIN_LIKES:
            logger.debug("[corpus] skip carousel %s — likes=%d < min=%d", vid, likes, BATCH_CAROUSEL_MIN_LIKES)
            continue

        # Gate 3+4: Vietnamese creator
        if not _passes_vn_gates(a, vid):
            continue

        carousel_candidates.append(a)

    # Sort carousels by likes desc
    carousel_candidates.sort(
        key=lambda a: int((a.get("statistics") or {}).get("digg_count", 0) or 0),
        reverse=True,
    )
    if carousels_per_niche_override is not None:
        cpn = carousels_per_niche_override
    else:
        cpn = _carousels_per_night_for_ingest_loop(ingest_loop_niche_id)
    carousel_candidates = carousel_candidates[: max(0, cpn)]

    if carousel_candidates:
        logger.info(
            "[corpus] niche=%s — %d carousel candidates added (min_likes=%d)",
            niche_name, len(carousel_candidates), BATCH_CAROUSEL_MIN_LIKES,
        )

    # Merge video + carousel candidates
    candidates = candidates + carousel_candidates
    result.candidates_found = len(candidates)

    # Sprint 8.5 — surface how many awemes the news/aggregator
    # blocklist filtered this pass. Visible in cron logs so ops can
    # spot when a noisy media account starts dominating an EnsembleData
    # hashtag fetch.
    if blocklist_skipped > 0:
        logger.info(
            "[corpus] niche=%s — blocklist filtered %d aweme(s) (news/aggregator handles)",
            niche_name, blocklist_skipped,
        )

    if not candidates:
        vdiag = _video_pool_gate_diagnostics(pool, existing_ids)
        logger.info(
            "[corpus] niche=%s — no ingestible candidates this run "
            "(misleading legacy label was 'all posts already indexed'). "
            "carousel_raw_pool=%d video_gate_diag=%s",
            niche_name,
            len(carousel_pool),
            vdiag,
        )
        return result

    id_strs = [str(c.get("aweme_id", "") or "") for c in candidates if c.get("aweme_id") is not None]
    preview = ",".join(id_strs[:60])
    if len(id_strs) > 60:
        preview = f"{preview},...(+{len(id_strs) - 60} more)"
    logger.info(
        "[corpus] niche=%s — candidate_aweme_ids n=%d: %s",
        niche_name,
        len(id_strs),
        preview,
    )

    sub = await _ingest_candidate_awemes(
        client,
        ingest_loop_niche_id,
        niche_name,
        candidates,
        niche_signal_hashtags_by_id=niche_signal_hashtags_by_id,
        ingest_batch_ctx=ingest_batch_ctx,
    )
    _merge_sub_ingest_result(result, sub)
    return result


def _load_all_existing_video_ids_sync(
    client: Any,
    *,
    page_size: int = 1000,
) -> set[str]:
    """Return every ``video_id`` in ``video_corpus`` via paginated ``.range()`` queries.

    PostgREST / Supabase caps ``select`` responses (default 1000 rows). A bare
    ``.execute()`` without pagination silently truncated dedup (CR-1) so rows
    beyond the first page were invisible and re-ingested nightly.
    """
    out: set[str] = set()
    offset = 0
    while True:
        result = (
            client.table("video_corpus")
            .select("video_id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = result.data or []
        for row in rows:
            vid = row.get("video_id")
            if vid:
                out.add(str(vid))
        if len(rows) < page_size:
            break
        offset += page_size
    return out


def _existing_video_ids_sync(client: Any, niche_id: int) -> set[str]:
    """Return every ``video_id`` already in ``video_corpus`` (any niche).

    Audit Pass-2 fix #4 — was previously filtered by ``niche_id``, but
    Sprint 9's content-aware resolver reassigns rows from the loop niche
    to a different one. After reassignment, the loop niche's existing-id
    check no longer sees the row, so the next cron pass re-pulls + re-
    analyzes it (expensive Gemini call) before reassigning to the same
    target niche again. Global dedup avoids the wasted analysis.

    The ``niche_id`` argument is kept (logging breadcrumb) but no longer
    influences the query — so callers that previously relied on per-niche
    isolation must understand the wider scope.
    """
    _ = niche_id  # kept on the signature; rows are deduped globally now
    return _load_all_existing_video_ids_sync(client)


def _enrich_breakout_ratio_for_row(
    row: dict[str, Any],
    aweme: dict[str, Any],
    *,
    niche_id: int,
    ingest_batch_ctx: Any | None,
    content_class_id: int | None,
) -> None:
    """§corpus-ingest R3 — persist breakout_ratio via cohort p50 when author median missing."""
    if row.get("breakout_ratio") is not None or ingest_batch_ctx is None:
        return
    views = int(row.get("views") or 0)
    if views <= 0:
        return
    from getviews_pipeline.corpus_instructiveness import _breakout_for_aweme

    br, _src = _breakout_for_aweme(
        aweme,
        views,
        niche_id,
        ingest_batch_ctx,
        content_class_id=content_class_id,
    )
    if br > 0:
        row["breakout_ratio"] = br


def _is_permanent_r2_media_url(url: str | None, *, kind: Literal["video", "thumbnail"]) -> bool:
    if not url:
        return False
    path_marker = "/videos/" if kind == "video" else "/thumbnails/"
    from getviews_pipeline.config import R2_PUBLIC_URL, R2_VIDEO_PUBLIC_URL

    bases = [R2_VIDEO_PUBLIC_URL, R2_PUBLIC_URL] if kind == "video" else [R2_PUBLIC_URL]
    for base in bases:
        if not base:
            continue
        b = base.rstrip("/")
        if (url.startswith(b + "/") or url == b) and path_marker in url:
            return True
    return url.startswith("https://pub-") and path_marker in url


def _merge_existing_provenance_sync(
    client: Any,
    rows: list[dict[str, Any]],
) -> None:
    """COALESCE ingest provenance + stats_history + permanent media URLs."""
    ids = [str(r.get("video_id") or "") for r in rows if r.get("video_id")]
    if not ids:
        return
    existing: dict[str, dict[str, Any]] = {}
    chunk_size = 200
    for start in range(0, len(ids), chunk_size):
        chunk = ids[start : start + chunk_size]
        res = (
            client.table("video_corpus")
            .select(
                "video_id, ingest_source, first_seen_at, quality_tier, stats_history, "
                "video_url, thumbnail_url"
            )
            .in_("video_id", chunk)
            .execute()
        )
        for item in res.data or []:
            existing[str(item["video_id"])] = item

    for row in rows:
        vid = str(row.get("video_id") or "")
        prior = existing.get(vid)
        if not prior:
            continue
        if prior.get("ingest_source"):
            row["ingest_source"] = prior["ingest_source"]
        if prior.get("first_seen_at"):
            row["first_seen_at"] = prior["first_seen_at"]
        if prior.get("quality_tier"):
            row["quality_tier"] = prior["quality_tier"]
        prior_sh = prior.get("stats_history")
        if isinstance(prior_sh, list) and len(prior_sh) > 0:
            row["stats_history"] = prior_sh

        prior_video = prior.get("video_url")
        new_video = row.get("video_url")
        if prior_video and _is_permanent_r2_media_url(str(prior_video), kind="video"):
            if not new_video or not _is_permanent_r2_media_url(str(new_video), kind="video"):
                row["video_url"] = prior_video

        prior_thumb = prior.get("thumbnail_url")
        new_thumb = row.get("thumbnail_url")
        if prior_thumb and _is_permanent_r2_media_url(str(prior_thumb), kind="thumbnail"):
            if not new_thumb or not _is_permanent_r2_media_url(str(new_thumb), kind="thumbnail"):
                row["thumbnail_url"] = prior_thumb


def _upsert_rows_sync(client: Any, rows: list[dict[str, Any]]) -> None:
    """Provenance-safe batch upsert — full row dict via PostgREST.

    M4 migration regressed ``upsert_video_corpus_batch`` (subset columns only).
    Canonical path: merge existing provenance in Python, then upsert all fields
    Python sends (boost, relax tier, stats_history t0, breakout_ratio, …).
    """
    from datetime import UTC
    from datetime import datetime as _dt

    now_iso = _dt.now(UTC).isoformat()
    enriched = []
    for row in rows:
        r = dict(row)
        r.pop("niche_id", None)
        r.setdefault("ingest_source", "batch_nightly")
        r.setdefault("quality_tier", "high")
        r.setdefault("first_seen_at", now_iso)
        r["last_refreshed_at"] = now_iso
        enriched.append(r)

    _merge_existing_provenance_sync(client, enriched)
    client.table("video_corpus").upsert(enriched, on_conflict="video_id").execute()


# ── Materialized view refresh ────────────────────────────────────────────────────

def _refresh_content_class_intelligence_sync(client: Any) -> None:
    """Refresh content_class_intelligence MV via RPC.

    Two-axis A.2.1 (2026-05-14): parallel MV keyed on
    content_classifications.id. Refreshed after every corpus update so
    pattern thesis / video diagnosis can pivot to the (topic × format)
    granularity once A.2.3 lands.
    """
    client.rpc("refresh_content_class_intelligence", {}).execute()


def _refresh_content_class_tier_intelligence_sync(client: Any) -> None:
    """Refresh peer-band MV (Phase 2). Fails open if migration not applied."""
    client.rpc("refresh_content_class_tier_intelligence", {}).execute()


def _refresh_creator_niche_content_class_stats_sync(client: Any) -> None:
    """Wave 3c — refresh junction × class stats MV for morning ritual anchor."""
    client.rpc("refresh_creator_niche_content_class_stats", {}).execute()


async def _refresh_corpus_intelligence_mvs(client: Any) -> bool:
    """Refresh content_class intelligence MVs after corpus updates."""
    cc_ok = False
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: _refresh_content_class_intelligence_sync(client)
        )
        logger.info("[corpus] content_class_intelligence materialized view refreshed")
        cc_ok = True
    except Exception as exc:
        logger.warning(
            "[corpus] content_class_intelligence refresh failed (acceptable "
            "if migration 20260514000000 not yet applied): %s",
            exc,
        )
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: _refresh_content_class_tier_intelligence_sync(client)
        )
        logger.info("[corpus] content_class_tier_intelligence MV refreshed")
    except Exception as exc:
        logger.warning(
            "[corpus] content_class_tier_intelligence refresh failed (non-fatal): %s",
            exc,
        )
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: _refresh_creator_niche_content_class_stats_sync(client)
        )
        logger.info("[corpus] creator_niche_content_class_stats MV refreshed")
    except Exception as exc:
        logger.warning(
            "[corpus] creator_niche_content_class_stats refresh failed (non-fatal): %s",
            exc,
        )
    return cc_ok


def _pick_top_videos_for_enrichment_sync(
    client: Any,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Return top ``limit`` ``{video_id, niche_id}`` dicts from
    video_corpus, filtered to rows that still need enrichment.

    "Needs enrichment" = the corresponding ``video_shots`` rows have
    NULL ``framing`` for every scene (i.e. the SQL-copy backfill ran
    but the enriched fields never got populated because Gemini
    analyzed the video before PR #2 shipped). Once this trigger
    re-analyzes the video, the dual-write upsert lands the new
    enriched dimensions.

    Ordered by ``views DESC`` — high-engagement rows land first
    because the matcher prioritizes them when surfacing references.
    """
    # Small-limit query: all "enriched" video_ids (have any row with
    # non-null framing). Even at 10K+ corpus this is a single index
    # scan. Used as the exclude-set for the main ranked query.
    enriched = (
        client.table("video_shots")
        .select("video_id")
        .not_.is_("framing", "null")
        .execute()
    )
    enriched_ids: set[str] = {row["video_id"] for row in (enriched.data or [])}

    # Pull an over-fetch so we can subtract the enriched set and still
    # hit `limit` candidates. Doubled + 50 handles the likely overlap
    # ratio after the dual-write has been running for a bit.
    target = max(1, int(limit))
    result = (
        client.table("video_corpus")
        .select("video_id,ingest_loop_niche_id")
        .not_.is_("ingest_loop_niche_id", "null")
        .eq("content_type", "video")
        .order("views", desc=True)
        .limit(target * 2 + 50)
        .execute()
    )
    rows = result.data or []
    out: list[dict[str, Any]] = []
    for r in rows:
        vid = r.get("video_id")
        nid = r.get("ingest_loop_niche_id")
        if not vid or nid is None:
            continue
        if vid in enriched_ids:
            continue
        out.append({"video_id": str(vid), "niche_id": int(nid)})
        if len(out) >= target:
            break
    return out


async def pick_top_videos_for_enrichment(
    client: Any,
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: _pick_top_videos_for_enrichment_sync(client, limit=limit),
    )


async def run_reingest_video_items(
    items: list[dict[str, Any]],
    *,
    refresh_mv: bool = True,
) -> BatchSummary:
    """Re-fetch posts by TikTok ``video_id`` / ``aweme_id`` and run analyze+upsert.

    Each item is ``{"video_id": "<aweme_id>", "niche_id": <int>}`` (``aweme_id``
    alias allowed) where ``niche_id`` is the ingest-loop bucket
    (``niche_taxonomy.id``).
    Does not run Sunday weekly analytics — only analyze/upsert + optional MV refresh.
    """
    from collections import defaultdict

    summary = BatchSummary()
    client = _service_client()

    seen: set[tuple[str, int]] = set()
    ordered: list[tuple[str, int]] = []
    for it in items:
        vid = str(it.get("video_id") or it.get("aweme_id") or "").strip()
        raw_nid = it.get("niche_id")
        if not vid or raw_nid is None:
            continue
        try:
            nid = int(raw_nid)
        except (TypeError, ValueError):
            continue
        key = (vid, nid)
        if key in seen:
            continue
        seen.add(key)
        ordered.append((vid, nid))

    # Wave 2.5 Phase A PR #4c raised this from 400 → 500 so the
    # "enrich top-500 shots" backfill trigger can run in a single batch.
    # Each reingest item = 1 Gemini video call (~$0.003) + 1 ED multi_info
    # unit (~0.02 from the 5000/day plan), so 500 items ≈ $1.50 Gemini +
    # ~10 ED units — well inside budget.
    if len(ordered) > 500:
        logger.warning("[corpus] reingest capped from %d to 500 items", len(ordered))
        ordered = ordered[:500]

    if not ordered:
        logger.warning("[corpus] reingest: no valid items")
        return summary

    niches: list[dict[str, Any]] = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _fetch_niches_sync(client)
    )
    niches_by_id = {int(n["id"]): n for n in niches}
    niche_signal_map = _niche_signal_hashtags_by_id_from_niches(niches)

    by_niche: dict[int, list[str]] = defaultdict(list)
    for vid, nid in ordered:
        by_niche[nid].append(vid)

    with ensemble.ed_batch_metering() as batch_id:
        for ingest_loop_niche_id, ids in by_niche.items():
            niche = niches_by_id.get(ingest_loop_niche_id)
            if not niche:
                logger.error(
                    "[corpus] reingest: unknown ingest_loop_niche_id=%s",
                    ingest_loop_niche_id,
                )
                summary.total_failed += len(ids)
                summary.niches_processed += 1
                summary.niche_results.append({
                    "ingest_loop_niche_id": ingest_loop_niche_id,
                    "niche_name": str(ingest_loop_niche_id),
                    "inserted": 0,
                    "skipped": 0,
                    "failed": len(ids),
                    "errors": ["unknown ingest_loop_niche_id"],
                })
                continue

            niche_name = (
                niche.get("name_en")
                or niche.get("name_vn")
                or str(ingest_loop_niche_id)
            )
            candidates: list[dict[str, Any]] = []
            missing = 0
            for i in range(0, len(ids), REINGEST_MULTI_CHUNK):
                chunk = ids[i : i + REINGEST_MULTI_CHUNK]
                raw_posts = await ensemble.fetch_post_multi_info(chunk)
                fresh_by_id: dict[str, dict[str, Any]] = {}
                for post in raw_posts:
                    detail = post.get("aweme_detail") or post
                    vid_id = str(detail.get("aweme_id") or "")
                    if vid_id:
                        fresh_by_id[vid_id] = detail
                for vid in chunk:
                    detail = fresh_by_id.get(vid)
                    if not detail:
                        missing += 1
                        continue
                    candidates.append(detail)

            if missing:
                logger.warning(
                    "[corpus] reingest niche=%s — EnsembleData missing %d/%d aweme payloads",
                    niche_name,
                    missing,
                    len(ids),
                )

            sub = await _ingest_candidate_awemes(
                client,
                ingest_loop_niche_id,
                niche_name,
                candidates,
                niche_signal_hashtags_by_id=niche_signal_map,
            )
            sub_failed = sub.failed + missing
            err_extra = ([f"multi_info_missing:{missing}"] if missing else [])
            summary.total_inserted += sub.inserted
            summary.total_skipped += sub.skipped
            summary.total_failed += sub_failed
            summary.subject_matter_inserted += sub.subject_matter_inserted
            summary.niches_processed += 1
            summary.niche_results.append({
                "ingest_loop_niche_id": ingest_loop_niche_id,
                "niche_name": niche_name,
                "inserted": sub.inserted,
                "skipped": sub.skipped,
                "failed": sub_failed,
                "errors": sub.errors + err_extra,
            })

        if refresh_mv:
            summary.materialized_view_refreshed = await _refresh_corpus_intelligence_mvs(client)
        else:
            summary.materialized_view_refreshed = False

        logger.info(
            ensemble.format_ed_meter_summary(
                batch_id=batch_id,
                niches=summary.niches_processed,
                inserted=summary.total_inserted,
                skipped=summary.total_skipped,
                failed=summary.total_failed,
                label="reingest_videos",
                theoretical_pool=None,
            )
        )

    return summary


async def run_ingest_post_processing(
    client: Any,
    *,
    run_weekly_analytics_if_sunday: bool = True,
) -> dict[str, Any]:
    """ME-16 — MV refresh, Video Đáng Học, Layer 0B sound, Layer 0D hashtag
    discovery, plus optional Sunday weekly analytics.

    Callable from a successful ``/batch/ingest`` or standalone ``/batch/post-processing``
    (e.g. after a wall-clock-aborted ingest).
    """
    out: dict[str, Any] = {
        "materialized_view_refreshed": False,
        "video_dang_hoc_error": None,
        "layer0b_error": None,
        "layer0d_error": None,
        "weekly_analytics_run": False,
        "acqe_error": None,
        "hi11_rolling_error": None,
    }

    out["materialized_view_refreshed"] = await _refresh_corpus_intelligence_mvs(client)

    try:
        from getviews_pipeline.class_quality_engine import run_acqe_nightly

        out["acqe_summary"] = await asyncio.get_event_loop().run_in_executor(
            None, lambda: run_acqe_nightly(client),
        )
    except Exception as exc:
        out["acqe_error"] = str(exc)
        logger.error("[acqe] nightly failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.hi11_rolling_eval import run_hi11_rolling_eval

        out["hi11_rolling"] = await asyncio.get_event_loop().run_in_executor(
            None, lambda: run_hi11_rolling_eval(client),
        )
    except Exception as exc:
        out["hi11_rolling_error"] = str(exc)
        logger.error("[hi11_rolling] failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.hashtag_class_map import run_hashtag_map_maintenance_sync

        out["hashtag_map_maintenance"] = await asyncio.get_event_loop().run_in_executor(
            None, lambda: run_hashtag_map_maintenance_sync(client),
        )
    except Exception as exc:
        out["hashtag_map_error"] = str(exc)
        logger.error("[hashtag_class_map] maintenance failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.video_dang_hoc import run_video_dang_hoc

        vdh_result = await run_video_dang_hoc(client)
        logger.info(
            "[video_dang_hoc] bung_no=%d dang_hot=%d errors=%s",
            vdh_result.bung_no_count,
            vdh_result.dang_hot_count,
            vdh_result.errors or "none",
        )
    except Exception as exc:
        out["video_dang_hoc_error"] = str(exc)
        logger.error("[video_dang_hoc] Video Đáng Học refresh failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.layer0_sound import run_sound_insights

        l0b_result = await run_sound_insights(client)
        logger.info("[layer0b] sounds_analyzed=%d", l0b_result.get("analyzed", 0))
    except Exception as exc:
        out["layer0b_error"] = str(exc)
        logger.error("[layer0b] Sound insight failed (non-fatal): %s", exc)

    # Layer 0D — Trending Hashtag Discovery. Was Sunday-only inside
    # _run_weekly_analytics; promoted to daily on 2026-05-17 so new
    # high-performing hashtags surfacing in the corpus flow into
    # niche_taxonomy.signal_hashtags within ≤24h instead of ≤7 days.
    # Cost is bounded by layer0_hashtag.MAX_CANDIDATES_PER_RUN=60 — most
    # days the candidate scan returns 0 (steady-state corpus), so the
    # Gemini classifier doesn't fire. Worst-case ~7× weekly cost = ~$0.70/wk.
    try:
        from getviews_pipeline.layer0_hashtag import run_hashtag_discovery
        l0d_result = await run_hashtag_discovery(client)
        logger.info(
            "[layer0d] candidates=%d added=%d map_written=%d candidates_saved=%d stale=%d skipped=%d errors=%s",
            l0d_result.get("candidates_found", 0),
            l0d_result.get("added", 0),
            l0d_result.get("map_written", 0),
            l0d_result.get("candidates_saved", 0),
            l0d_result.get("stale_signals", 0),
            l0d_result.get("skipped", 0),
            l0d_result.get("errors") or "none",
        )
    except Exception as exc:
        out["layer0d_error"] = str(exc)
        logger.error("[layer0d] Hashtag discovery failed (non-fatal): %s", exc)

    today = date.today()
    is_sunday = today.weekday() == 6
    if is_sunday and run_weekly_analytics_if_sunday:
        logger.info(
            "[corpus] Sunday — running weekly analytics (trend_velocity + P1-7 + P1-8)..."
        )
        await _run_weekly_analytics(client)
        out["weekly_analytics_run"] = True

    return out


async def _run_weekly_analytics(client: Any) -> None:
    """Run trend velocity + creator velocity + breakout multiplier + signal grading (Sunday only).

    Non-fatal: errors are logged but do not fail the batch ingest.
    """
    try:
        from getviews_pipeline.trend_velocity import run_trend_velocity
        tv_result = await run_trend_velocity(client)
        logger.info(
            "[tv] rows_upserted=%d niches=%d errors=%s",
            tv_result.rows_upserted,
            tv_result.niches_processed,
            tv_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[tv] Trend velocity computation failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.batch_analytics import run_analytics
        analytics_result = await run_analytics(client)
        logger.info(
            "[analytics] creators_updated=%d videos_updated=%d errors=%s",
            analytics_result.creators_updated,
            analytics_result.videos_updated,
            analytics_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[analytics] Weekly analytics failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.signal_classifier import run_signal_grading
        signal_result = await run_signal_grading(client)
        logger.info(
            "[signal] grades_written=%d niches=%d errors=%s",
            signal_result.grades_written,
            signal_result.niches_processed,
            signal_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[signal] Signal grading failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.cross_creator import run_cross_creator_detection

        cc_result = await run_cross_creator_detection(client)
        logger.info(
            "[cross_creator] patterns_written=%d niches_affected=%d errors=%s",
            cc_result.patterns_written,
            cc_result.niches_affected,
            cc_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[cross_creator] Cross-creator detection failed (non-fatal): %s", exc)

    try:
        from getviews_pipeline.sound_aggregator import run_sound_aggregation

        sa_result = await run_sound_aggregation(client)
        logger.info(
            "[sound_aggregation] upserted=%d",
            sa_result.get("upserted", 0),
        )
    except Exception as exc:
        logger.error("[sound_aggregation] Sound aggregation failed (non-fatal): %s", exc)

    # --- Layer 0: Intelligence Extraction (the brain) ---
    # Runs LAST — reads from video_corpus + signal_grades + trending_sounds
    # Non-fatal: if Layer 0 fails, dashboard still shows statistics (without mechanism)
    #
    # Layer 0D (hashtag discovery) ran here Sundays-only until 2026-05-17;
    # promoted to daily inside run_ingest_post_processing for ≤24h discovery
    # latency on new high-performing hashtags.

    try:
        from getviews_pipeline.layer0_niche import run_niche_insights
        l0a_result = await run_niche_insights(client)
        logger.info(
            "[layer0a] insights=%d skipped=%d errors=%s",
            l0a_result.insights_written,
            l0a_result.niches_skipped,
            l0a_result.errors or "none",
        )
    except Exception as exc:
        logger.error("[layer0a] Niche insight generation failed (non-fatal): %s", exc)


# ── Main batch entry point ───────────────────────────────────────────────────────

async def run_batch_ingest(
    niche_ids: list[int] | None = None,
    *,
    deep_pool: bool = False,
    wall_clock_budget_s: int = 3400,
    ingest_shift: str | None = None,
    ingest_shift_count: int = 3,
) -> BatchSummary:
    """Run full batch ingest. Optionally restrict to specific niche_ids.

    Args:
        niche_ids: If provided, only ingest these niche IDs. Otherwise all niches.
        deep_pool: When True, widen keyword pagination and per-niche caps so a follow-up
            run can overlap more of a prior candidate set (e.g. after a model outage).
        wall_clock_budget_s: Stop processing niches after this many seconds (default 3400s
            ≈57 min). A 2-minute safety buffer is applied so the function returns before
            the Cloud Run request timeout (3600s). Set to 0 to disable the guard.
        ingest_shift: When set (``a``–``f``), process only that slice of active class
            targets after splitting by ``ingest_shift_count`` (default 3 nightly shifts).
        ingest_shift_count: Number of shifts to divide active class targets into.

    Returns:
        BatchSummary with per-niche counts and materialized view status.
        summary.aborted_early=True when the budget was exhausted mid-run.
    """
    reset_hi11_junction_reject_count()
    summary = BatchSummary()
    summary.ingest_mode = corpus_ingest_mode()
    summary.score_cohort = corpus_score_cohort()
    client = _service_client()

    # H-3 run marker: claim the (utc_day, shift) slot before any paid work.
    # A cron double-fire / overlapping manual trigger of the SAME shift
    # otherwise re-runs the full Gemini extraction (doubled spend).
    if ingest_shift is not None:
        claimed = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _claim_ingest_shift_sync(client, ingest_shift),
        )
        if not claimed:
            logger.error(
                "[corpus] shift %s already claimed today (corpus_ingest_runs) — "
                "skipping duplicate run. Delete the row to force a re-run.",
                ingest_shift,
            )
            summary.skipped_duplicate_run = True
            summary.ingest_shift = ingest_shift
            summary.ingest_shift_count = ingest_shift_count
            return summary

    loop_mode = _corpus_ingest_loop_mode()
    summary.ingest_loop = loop_mode
    if loop_mode == "class":
        niches = await asyncio.get_event_loop().run_in_executor(
            None, lambda: fetch_ingest_targets_sync(client),
        )
        logger.info("[corpus] ingest loop=class — %d active targets", len(niches))
    else:
        niches = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _fetch_niches_sync(client),
        )
    niche_signal_map = _niche_signal_hashtags_by_id_from_niches(niches)

    if niche_ids:
        niches = [n for n in niches if n["id"] in niche_ids]

    if loop_mode == "class" and ingest_shift is not None:
        try:
            niches, shift_meta = split_ingest_targets_for_shift(
                niches,
                shift=ingest_shift,
                shift_count=ingest_shift_count,
            )
        except ValueError as exc:
            logger.error("[corpus] Invalid ingest shift: %s", exc)
            raise
        summary.ingest_shift = shift_meta.get("ingest_shift")
        summary.ingest_shift_count = int(shift_meta.get("ingest_shift_count") or ingest_shift_count)
        summary.content_class_ids_planned = list(shift_meta.get("content_class_ids_planned") or [])
        logger.info(
            "[corpus] ingest shift=%s count=%d — %d class targets planned (cc_ids=%s)",
            summary.ingest_shift,
            summary.ingest_shift_count,
            len(niches),
            summary.content_class_ids_planned[:8],
        )
    elif loop_mode == "class":
        summary.content_class_ids_planned = [
            int(n["_loop_content_class_id"])
            for n in niches
            if n.get("_loop_content_class_id") is not None
        ]

    if not niches:
        logger.warning("[corpus] No niches to process")
        return summary

    kw: int | None = None
    vpn: int | None = None
    if deep_pool:
        kw = min(BATCH_KEYWORD_PAGES * 3, 8)
        vpn = min(BATCH_VIDEOS_PER_NICHE * 2, 100)
        logger.info(
            "[corpus] deep_pool ingest: keyword_pages=%d videos_per_niche=%d "
            "carousels=min(per_niche_base*2,12)",
            kw,
            vpn,
        )

    # Wave 5+ Phase 2 — per-niche quota prioritization. When ``vpn`` is
    # not pinned by ``deep_pool``, compute a per-niche video quota from
    # each niche's current corpus count: thin niches get up to
    # ``THIN_NICHE_MAX_MULTIPLIER`` × the base BATCH_VIDEOS_PER_NICHE,
    # rich niches stay at 1×. The hard cap prevents a future misconfig
    # from blowing the ED budget.
    per_niche_vpn: dict[int, int] = {}
    niche_allocation_log: list[dict[str, Any]] = []
    if vpn is None and summary.ingest_mode == "purity":
        purity_vpn = effective_videos_per_niche(BATCH_VIDEOS_PER_NICHE)
        for n in niches:
            nid = int(n["id"])
            per_niche_vpn[nid] = purity_vpn
            niche_allocation_log.append({
                "ingest_loop_niche_id": nid,
                "niche_name": n.get("name_en") or n.get("name_vn") or str(nid),
                "current_count": 0,
                "multiplier": 1.0,
                "allocated_vpn": purity_vpn,
                "priority_floor": False,
                "purity_allocator": True,
            })
        logger.info(
            "[corpus] purity allocator — uniform VPN=%d per niche (mode=%s)",
            purity_vpn,
            summary.ingest_mode,
        )
    elif vpn is None:
        niche_counts = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _fetch_niche_counts_sync(client),
        )
        hard_cap = int(BATCH_VIDEOS_PER_NICHE * THIN_NICHE_MAX_MULTIPLIER)
        for n in niches:
            nid = int(n["id"])
            current = niche_counts.get(nid, 0)
            mult = compute_thin_niche_multiplier(current)
            allocated = apply_thin_niche_multiplier(
                BATCH_VIDEOS_PER_NICHE, mult, hard_cap=hard_cap,
            )
            per_niche_vpn[nid] = allocated
            niche_allocation_log.append({
                "ingest_loop_niche_id": nid,
                "niche_name": n.get("name_en") or n.get("name_vn") or str(nid),
                "current_count": current,
                "multiplier": round(mult, 2),
                "allocated_vpn": allocated,
                "priority_floor": False,
            })
        # Star niches (e.g. Thời trang) — floor so main verticals keep ingesting
        # after thin-niche math drops them to 1×.
        if BATCH_PRIORITY_NICHE_IDS and BATCH_PRIORITY_NICHE_VPN_FLOOR > 0:
            by_id: dict[int, dict[str, Any]] = {
                int(r["ingest_loop_niche_id"]): r for r in niche_allocation_log
            }
            for n in niches:
                nid = int(n["id"])
                if nid not in BATCH_PRIORITY_NICHE_IDS:
                    continue
                prev = per_niche_vpn.get(nid, BATCH_VIDEOS_PER_NICHE)
                new = min(
                    max(prev, BATCH_PRIORITY_NICHE_VPN_FLOOR), BATCH_PRIORITY_NICHE_MAX_VPN,
                )
                if new != prev:
                    per_niche_vpn[nid] = new
                row = by_id.get(nid)
                if row is not None:
                    row["allocated_vpn"] = new
                    row["priority_floor"] = True
        # Log the allocation so dogfood + batch_observability can see
        # which niches got prioritized this run.
        top5 = sorted(
            niche_allocation_log,
            key=lambda a: a["allocated_vpn"],
            reverse=True,
        )[:5]
        allocation_summary = ", ".join(
            f"{a['niche_name']}:{a['current_count']}→{a['allocated_vpn']}"
            for a in top5
        )
        star_note = ""
        if BATCH_PRIORITY_NICHE_IDS and BATCH_PRIORITY_NICHE_VPN_FLOOR > 0:
            star_note = (
                f" | priority_niches={','.join(str(x) for x in sorted(BATCH_PRIORITY_NICHE_IDS))} "
                f"floor>={BATCH_PRIORITY_NICHE_VPN_FLOOR} cap<={BATCH_PRIORITY_NICHE_MAX_VPN}"
            )
        logger.info(
            "[corpus] thin-niche prioritization — target=%d, max_mult=%.1f. "
            "Top-5 allocations: %s%s",
            CORPUS_TARGET_PER_NICHE, THIN_NICHE_MAX_MULTIPLIER, allocation_summary, star_note,
        )
        summary.thin_niche_allocations = niche_allocation_log

    logger.info(
        "[corpus] Starting batch ingest for %d niches (wall_clock_budget=%ds)",
        len(niches),
        wall_clock_budget_s,
    )

    eff_kw_pages = kw if kw is not None else BATCH_KEYWORD_PAGES
    ht_for_theory = BATCH_HASHTAG_FETCH_LIMIT
    if BATCH_HASHTAG_FETCH_BY_NICHE:
        ht_for_theory = max(
            ht_for_theory, max(BATCH_HASHTAG_FETCH_BY_NICHE.values())
        )
    theory_pool = theoretical_ed_pool_requests(
        len(niches),
        keyword_pages=eff_kw_pages,
        hashtag_limit=ht_for_theory,
        legacy_carousel_second_hashtag_pass=CORPUS_LEGACY_CAROUSEL_HASHTAG_FETCH,
    )
    logger.info("[corpus] theoretical_ed_pool %s", theory_pool["formula"])

    hashtag_yields_all = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _load_hashtag_yields_all_sync(client)
    )

    # CR-1 — single paginated snapshot for the whole run (avoids N parallel
    # fetches per niche and fixes the silent 1000-row PostgREST cap).
    existing_snapshot = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _load_all_existing_video_ids_sync(client),
    )
    existing_class_map: dict[str, int] = {}
    if loop_mode == "class":
        existing_class_map = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _load_existing_video_class_map_sync(client),
        )
        for n in niches:
            n["_existing_class_by_video"] = existing_class_map
    logger.info(
        "[corpus] dedup snapshot: %d existing video_ids (paginated global load)",
        len(existing_snapshot),
    )

    ingest_batch_ctx: IngestBatchContext | None = None
    if summary.ingest_mode in ("shadow", "purity"):
        niche_id_list = [int(n["id"]) for n in niches]
        ingest_batch_ctx = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: prefetch_ingest_batch_context(client, niche_id_list),
        )
        if ingest_batch_ctx.missing_median_total > 0:
            rate = ingest_batch_ctx.missing_median_count / max(
                1, ingest_batch_ctx.missing_median_total
            )
            logger.info(
                "[corpus] author median missing rate=%.1f%% (%d/%d)",
                rate * 100,
                ingest_batch_ctx.missing_median_count,
                ingest_batch_ctx.missing_median_total,
            )
        summary.shadow_metrics["missing_median_rate"] = (
            ingest_batch_ctx.missing_median_count
            / max(1, ingest_batch_ctx.missing_median_total)
        )

    # Wall-clock deadline: stop between niche batches, never mid-niche.
    # A 2-minute safety buffer ensures we return before Cloud Run kills the container.
    _BUDGET_SAFETY_BUFFER_S = 120
    t0 = time.monotonic()

    with ensemble.ed_batch_metering() as batch_id, ensemble.ed_call_site("corpus_ingest.batch"):
        # Process niches in batches of BATCH_CONCURRENCY to avoid overwhelming APIs
        for i in range(0, len(niches), BATCH_CONCURRENCY):
            # Wall-clock guard — stop between batches so record_job_run can write
            if wall_clock_budget_s > 0:
                elapsed = time.monotonic() - t0
                remaining = wall_clock_budget_s - _BUDGET_SAFETY_BUFFER_S - elapsed
                if remaining <= 0:
                    niches_left = len(niches) - i
                    summary.aborted_early = True
                    summary.niches_remaining = niches_left
                    summary.remaining_content_class_ids = [
                        int(n["_loop_content_class_id"])
                        for n in niches[i:]
                        if n.get("_loop_content_class_id") is not None
                    ]
                    logger.warning(
                        "[corpus] Wall-clock budget exhausted after %.0fs — stopping before "
                        "niche batch %d/%d (%d niches remaining, cc_ids=%s). "
                        "Increase wall_clock_budget_s, add ingest shifts, or reduce per-class VPN.",
                        elapsed,
                        i // BATCH_CONCURRENCY + 1,
                        -(-len(niches) // BATCH_CONCURRENCY),
                        niches_left,
                        summary.remaining_content_class_ids[:8],
                    )
                    break
            batch = niches[i : i + BATCH_CONCURRENCY]
            results = await asyncio.gather(
                *[
                    ingest_niche(
                        n,
                        client,
                        keyword_pages_override=kw,
                        # Per-niche vpn when thin-niche prioritization is
                        # active (``vpn is None``); falls back to the
                        # uniform ``vpn`` from deep_pool mode otherwise.
                        videos_per_niche_override=(
                            int(n["_daily_vpn"])
                            if n.get("_daily_vpn") is not None
                            else (
                                vpn if vpn is not None
                                else per_niche_vpn.get(int(n["id"]))
                            )
                        ),
                        carousels_per_niche_override=(
                            min(_carousels_per_night_for_ingest_loop(int(n["id"])) * 2, 12)
                            if deep_pool
                            else None
                        ),
                        hashtag_yields_for_niche=hashtag_yields_all.get(int(n["id"]), {}),
                        niche_signal_hashtags_by_id=niche_signal_map,
                        existing_video_ids=existing_snapshot,
                        ingest_batch_ctx=ingest_batch_ctx,
                    )
                    for n in batch
                ],
                return_exceptions=True,
            )
            for res in results:
                if isinstance(res, Exception):
                    logger.error("[corpus] niche ingest raised: %s", res)
                    summary.total_failed += 1
                    continue
                summary.total_inserted += res.inserted
                summary.total_skipped += res.skipped
                summary.total_failed += res.failed
                summary.subject_matter_inserted += res.subject_matter_inserted
                summary.hi13_batch_line_ok += res.hi13_batch_line_ok
                summary.hi13_batch_line_fail += res.hi13_batch_line_fail
                summary.hi13_sync_fallback += res.hi13_sync_fallback
                summary.hi13_batch_jobs_ok += res.hi13_batch_jobs_ok
                summary.hi13_batch_jobs_failed += res.hi13_batch_jobs_failed
                summary.niches_processed += 1
                summary.niche_results.append({
                    "ingest_loop_niche_id": res.ingest_loop_niche_id,
                    "content_class_id": res.content_class_id,
                    "niche_name": res.niche_name,
                    "inserted": res.inserted,
                    "skipped": res.skipped,
                    "failed": res.failed,
                    "pool_raw": res.pool_raw,
                    "candidates_found": res.candidates_found,
                    "hashtags_queried": res.hashtags_queried,
                    "errors": res.errors,
                    "hi13_batch_line_ok": res.hi13_batch_line_ok,
                    "hi13_batch_line_fail": res.hi13_batch_line_fail,
                    "hi13_sync_fallback": res.hi13_sync_fallback,
                })

        if not should_run_inline_ingest_post_processing(
            aborted_early=summary.aborted_early,
            ingest_shift=ingest_shift,
        ):
            if summary.aborted_early:
                logger.warning(
                    "[corpus] Skipping inline post-processing (mv refresh, video_dang_hoc, "
                    "sound insights, weekly analytics) due to wall-clock budget."
                )
            else:
                logger.info(
                    "[corpus] Skipping inline post-processing — scheduled shift %s; "
                    "cron-batch-post-processing (23:30 UTC) heals MV overnight.",
                    ingest_shift,
                )
        else:
            pp = await run_ingest_post_processing(
                client, run_weekly_analytics_if_sunday=True,
            )
            summary.materialized_view_refreshed = bool(pp.get("materialized_view_refreshed"))

        logger.info(
            "[corpus] Batch complete — inserted=%d skipped=%d failed=%d niches=%d "
            "subject_matter_rows=%d mv_refreshed=%s hi11_junction_reject=%d aborted_early=%s "
            "niches_remaining=%d elapsed=%.0fs",
            summary.total_inserted,
            summary.total_skipped,
            summary.total_failed,
            summary.niches_processed,
            summary.subject_matter_inserted,
            summary.materialized_view_refreshed,
            get_hi11_junction_reject_count(),
            summary.aborted_early,
            summary.niches_remaining,
            time.monotonic() - t0,
        )
        logger.info(
            ensemble.format_ed_meter_summary(
                batch_id=batch_id,
                niches=len(niches),
                inserted=summary.total_inserted,
                skipped=summary.total_skipped,
                failed=summary.total_failed,
                label="batch_ingest",
                theoretical_pool=theory_pool,
            )
        )
    summary.shadow_metrics["hi11_junction_reject"] = get_hi11_junction_reject_count()
    if ingest_shift is not None:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: _complete_ingest_shift_sync(client, ingest_shift, summary),
        )
    return summary


def _corpus_ingest_loop_mode() -> str:
    mode = (_ingest_settings.corpus_ingest_loop or "niche").strip().lower()
    return mode if mode in ("niche", "class") else "niche"


def _claim_ingest_shift_sync(client: Any, shift: str) -> bool:
    """Claim (utc_day, shift) in corpus_ingest_runs; False = already claimed.

    A double-fired shift doesn't duplicate rows (video_corpus upserts on
    video_id) but re-runs the full Gemini extraction — doubled spend and
    last-writer clobber. Only scheduled shifts are guarded; manual runs
    (``ingest_shift=None``) stay unguarded so ops can always re-run.
    Fail-open: a claim-infra error must never block the nightly ingest.
    To force a same-day re-run of a shift, delete its corpus_ingest_runs row.
    """
    day = datetime.now(UTC).date().isoformat()
    try:
        res = (
            client.table("corpus_ingest_runs")
            .upsert(
                {"utc_day": day, "ingest_shift": shift},
                on_conflict="utc_day,ingest_shift",
                ignore_duplicates=True,
            )
            .execute()
        )
        return bool(res.data)
    except Exception as exc:
        logger.warning("[corpus] ingest-run claim failed (%s) — proceeding unguarded", exc)
        return True


def _complete_ingest_shift_sync(client: Any, shift: str, summary: BatchSummary) -> None:
    """Best-effort completion stamp on the run marker (audit trail)."""
    day = datetime.now(UTC).date().isoformat()
    try:
        client.table("corpus_ingest_runs").update({
            "completed_at": datetime.now(UTC).isoformat(),
            "aborted_early": summary.aborted_early,
            "inserted_count": summary.total_inserted,
        }).eq("utc_day", day).eq("ingest_shift", shift).execute()
    except Exception as exc:
        logger.warning("[corpus] ingest-run completion stamp failed: %s", exc)


_INGEST_SHIFT_LETTERS = "abcdef"


def _ingest_shift_index(shift: str) -> int | None:
    letter = (shift or "").strip().lower()
    if not letter or letter not in _INGEST_SHIFT_LETTERS:
        return None
    return _INGEST_SHIFT_LETTERS.index(letter)


def _is_final_ingest_shift(shift: str | None, shift_count: int) -> bool:
    """True when this run is the last scheduled shift slice (``a``–``f``)."""
    if shift is None:
        return True
    if shift_count < 1:
        return True
    final = _INGEST_SHIFT_LETTERS[min(shift_count, len(_INGEST_SHIFT_LETTERS)) - 1]
    return shift.strip().lower() == final


def should_run_inline_ingest_post_processing(
    *,
    aborted_early: bool,
    ingest_shift: str | None,
) -> bool:
    """Whether ``/batch/ingest`` should run MV refresh inline before returning.

    Scheduled shifts (``ingest_shift`` set) always defer to
    ``cron-batch-post-processing`` so shift C does not blow the 3600s cap.
    """
    if aborted_early:
        return False
    return ingest_shift is None


def split_ingest_targets_for_shift(
    targets: list[dict[str, Any]],
    *,
    shift: str | None,
    shift_count: int = 3,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Split active ingest targets into ``shift_count`` priority-ordered slices.

    Targets must already be sorted by priority (desc). When ``shift`` is None,
    returns the full list unchanged (manual / legacy cron body ``{}``).
    """
    meta: dict[str, Any] = {
        "ingest_shift": shift,
        "ingest_shift_count": shift_count,
        "content_class_ids_planned": [],
    }
    cc_ids = [
        int(t["_loop_content_class_id"])
        for t in targets
        if t.get("_loop_content_class_id") is not None
    ]
    if shift is None:
        meta["content_class_ids_planned"] = cc_ids
        return targets, meta

    idx = _ingest_shift_index(shift)
    if idx is None:
        raise ValueError(f"invalid ingest_shift={shift!r} — use a–f")
    if idx >= shift_count:
        raise ValueError(
            f"ingest_shift={shift!r} out of range for ingest_shift_count={shift_count}",
        )

    n = len(targets)
    if n == 0:
        return [], meta

    base = n // shift_count
    remainder = n % shift_count
    start = 0
    for i in range(shift_count):
        size = base + (1 if i < remainder else 0)
        if i == idx:
            chunk = targets[start : start + size]
            meta["content_class_ids_planned"] = [
                int(t["_loop_content_class_id"])
                for t in chunk
                if t.get("_loop_content_class_id") is not None
            ]
            return chunk, meta
        start += size
    return [], meta


def _load_existing_video_class_map_sync(client: Any) -> dict[str, int]:
    """video_id → content_class_id for Phase 3 class-change re-upsert."""
    out: dict[str, int] = {}
    offset = 0
    page_size = 1000
    while True:
        res = (
            client.table("video_corpus")
            .select("video_id, content_class_id")
            .not_.is_("content_class_id", "null")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = res.data or []
        for row in rows:
            vid = row.get("video_id")
            cc = row.get("content_class_id")
            if vid and cc is not None:
                out[str(vid)] = int(cc)
        if len(rows) < page_size:
            break
        offset += page_size
    return out


def _should_skip_existing_for_dedup(
    video_id: str,
    existing_ids: set[str],
    *,
    loop_content_class_id: int | None,
    existing_class_by_video: dict[str, int] | None,
) -> bool:
    """Global dedup unless class-loop mode allows re-upsert when class changed."""
    if not video_id or video_id not in existing_ids:
        return False
    if _corpus_ingest_loop_mode() != "class" or loop_content_class_id is None:
        return True
    prev = (existing_class_by_video or {}).get(video_id)
    if prev is None:
        return False
    return int(prev) == int(loop_content_class_id)


def _legacy_niche_id_for_class_sync(client: Any, content_class_id: int) -> int:
    """Representative ingest-loop niche_id for class-loop ingest (mode from corpus)."""
    try:
        res = (
            client.table("video_corpus")
            .select("ingest_loop_niche_id")
            .eq("content_class_id", content_class_id)
            .not_.is_("ingest_loop_niche_id", "null")
            .limit(200)
            .execute()
        )
        counts: dict[int, int] = {}
        for row in res.data or []:
            nid = row.get("ingest_loop_niche_id")
            if nid is not None:
                counts[int(nid)] = counts.get(int(nid), 0) + 1
        if counts:
            return max(counts.items(), key=lambda x: x[1])[0]
    except Exception as exc:
        logger.warning("[corpus] legacy niche for class=%s failed: %s", content_class_id, exc)
    return 1


def fetch_ingest_targets_sync(client: Any) -> list[dict[str, Any]]:
    """Active content_class_ingest_targets shaped like niche_taxonomy rows."""
    from getviews_pipeline.config import RETIRED_CONTENT_CLASS_IDS

    targets = (
        client.table("content_class_ingest_targets")
        .select("content_class_id, signal_hashtags, daily_vpn, active, priority, viability_tier")
        .eq("active", True)
        .order("priority", desc=True)
        .execute()
        .data
        or []
    )
    cc_meta: dict[int, dict[str, Any]] = {}
    try:
        cc_rows = (
            client.table("content_classifications")
            .select("id, name_vn, slug, active")
            .eq("active", True)
            .execute()
            .data
            or []
        )
        cc_meta = {
            int(r["id"]): r for r in cc_rows
            if int(r["id"]) not in RETIRED_CONTENT_CLASS_IDS
        }
    except Exception:
        pass
    out: list[dict[str, Any]] = []
    for t in targets:
        cc_id = int(t["content_class_id"])
        if cc_id in RETIRED_CONTENT_CLASS_IDS:
            continue
        meta = cc_meta.get(cc_id, {})
        if not meta:
            continue
        leg_nid = _legacy_niche_id_for_class_sync(client, cc_id)
        out.append({
            "id": leg_nid,
            "name_en": meta.get("slug") or f"class-{cc_id}",
            "name_vn": meta.get("name_vn") or f"Class {cc_id}",
            "signal_hashtags": t.get("signal_hashtags") or [],
            "_loop_content_class_id": cc_id,
            "_daily_vpn": int(t.get("daily_vpn") or 15),
            "_viability_tier": t.get("viability_tier"),
        })
    return out


def _fetch_niches_sync(client: Any) -> list[dict[str, Any]]:
    result = (
        client.table("niche_taxonomy")
        .select("id, name_en, name_vn, signal_hashtags")
        .execute()
    )
    return result.data or []
