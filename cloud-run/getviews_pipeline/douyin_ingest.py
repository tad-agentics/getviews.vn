"""D2c (2026-06-03) — Kho Douyin · ingest orchestrator.

Wires D2a (``douyin_translator``) + D2b (``douyin_metadata``) +
``ensemble_douyin`` (D1) into the daily ingest cron. Mirrors the
Vietnamese TikTok ``corpus_ingest.run_batch_ingest`` shape but:

  • Smaller surface area — no quota / hashtag-yield ranker / pattern
    fingerprinter / VN-classifier passes (those land in D5+ if needed).
  • Higher view threshold — Douyin's mainland-CN scale runs ~10×
    larger than VN TikTok, so the default ``BATCH_DOUYIN_MIN_VIEWS``
    is 100K (vs 20K on VN).
  • Engagement-rate threshold tuned for Douyin's save+share-heavy
    signals (``_safe_engagement_rate`` in ``douyin_metadata.py``
    includes ``saves`` in the numerator).
  • Concurrent translation + Gemini video analysis (gather both —
    analysis is much slower so translation is essentially free).

Per-niche flow:

  1. ``_fetch_douyin_pool(niche, deep)`` — fan-in of
     ``ensemble_douyin.fetch_douyin_keyword_search`` (1 page) +
     ``fetch_douyin_hashtag_posts`` (top-N tags from
     ``signal_hashtags_zh``).
  2. ``_existing_douyin_video_ids(client, niche_id)`` — dedupe set
     scoped to this niche so re-running a niche doesn't re-ingest its
     own rows.
  3. Quality gates — ``views ≥ BATCH_DOUYIN_MIN_VIEWS`` AND
     ``engagement_rate ≥ BATCH_DOUYIN_MIN_ER``.
  4. ``_ingest_candidate_awemes_douyin`` — analyze + translate +
     upsert (with R2 frame extraction when configured).

D2d (next PR) ships the ``/batch/douyin-ingest`` endpoint + pg_cron
schedule that drives this module on a daily timer.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_core import analyze_aweme, analyze_aweme_from_path
from getviews_pipeline.douyin_metadata import build_douyin_corpus_row
from getviews_pipeline.douyin_translator import translate_douyin_caption
from getviews_pipeline.ensemble_douyin import (
    fetch_douyin_hashtag_posts,
    fetch_douyin_keyword_search,
)
from getviews_pipeline.r2 import (
    extract_and_upload,
    extract_and_upload_scene_frames,
    r2_configured,
)
from getviews_pipeline.runtime import get_analysis_semaphore

logger = logging.getLogger(__name__)


# ── Tuning constants (env-overridable) ──────────────────────────────

BATCH_DOUYIN_CONCURRENCY = int(os.environ.get("BATCH_DOUYIN_CONCURRENCY", "2"))
BATCH_DOUYIN_MIN_VIEWS = int(os.environ.get("BATCH_DOUYIN_MIN_VIEWS", "100000"))
BATCH_DOUYIN_MIN_ER = float(os.environ.get("BATCH_DOUYIN_MIN_ER", "2.5"))
BATCH_DOUYIN_HASHTAG_FETCH_LIMIT = int(
    os.environ.get("BATCH_DOUYIN_HASHTAG_FETCH_LIMIT", "3")
)
# Per-niche cap on candidates we run through Gemini. Douyin scale is
# generous; a smaller cap keeps the daily ED+Gemini budget bounded.
BATCH_DOUYIN_VIDEOS_PER_NICHE = int(
    os.environ.get("BATCH_DOUYIN_VIDEOS_PER_NICHE", "5")
)


# ── Result types ────────────────────────────────────────────────────


@dataclass
class DouyinIngestResult:
    niche_id: int
    niche_name: str
    fetched: int = 0
    skipped_dedupe: int = 0
    skipped_quality: int = 0
    inserted: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class DouyinBatchSummary:
    total_inserted: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    niches_processed: int = 0
    niche_results: list[dict[str, Any]] = field(default_factory=list)


# ── DB helpers ──────────────────────────────────────────────────────


def _service_client() -> Any:
    from getviews_pipeline.supabase_client import get_service_client

    return get_service_client()


async def _fetch_active_douyin_niches(client: Any) -> list[dict[str, Any]]:
    """Read the seeded niche taxonomy. ``active=FALSE`` rows are paused
    from cron without being deleted (FK validity for already-ingested
    corpus rows)."""

    def _q() -> list[dict[str, Any]]:
        res = (
            client.table("douyin_niche_taxonomy")
            .select("id, slug, name_vn, name_zh, signal_hashtags_zh")
            .eq("active", True)
            .order("id")
            .execute()
        )
        return list(res.data or [])

    return await asyncio.get_event_loop().run_in_executor(None, _q)


async def _existing_douyin_video_ids(client: Any, niche_id: int) -> set[str]:
    """Dedupe set — scoped per niche so a re-run of one niche doesn't
    skip another niche's videos."""

    def _q() -> set[str]:
        res = (
            client.table("douyin_video_corpus")
            .select("video_id")
            .eq("niche_id", niche_id)
            .execute()
        )
        return {str(r["video_id"]) for r in (res.data or []) if r.get("video_id")}

    return await asyncio.get_event_loop().run_in_executor(None, _q)


# ── Pool fetcher ────────────────────────────────────────────────────


async def _fetch_douyin_pool(
    niche: dict[str, Any],
    *,
    deep: bool = False,
) -> list[dict[str, Any]]:
    """Fan-in keyword + hashtag candidates for one niche.

    Strategy:
      • One ``fetch_douyin_keyword_search`` call seeded with the niche's
        Vietnamese display name's Chinese mirror (``name_zh``) — gets
        the broad top-engagement pool.
      • Top-N hashtag pages from ``signal_hashtags_zh`` — narrows to
        the curated trend pool.

    Dedupe across pools is by ``aweme_id`` so a video that surfaces in
    both keyword + hashtag pools only goes through Gemini once.

    ``deep=True`` doubles the per-pool page count (manual ops only).
    """
    name_zh = (niche.get("name_zh") or "").strip()
    pages = 2 if deep else 1
    candidates: list[dict[str, Any]] = []

    # Keyword pool — ED `/douyin/keyword/search` accepts CN keywords
    # directly (no romanization needed).
    if name_zh:
        cursor: int | None = 0
        for _ in range(pages):
            try:
                awemes, cursor = await fetch_douyin_keyword_search(
                    name_zh, cursor=cursor or 0,
                )
                candidates.extend(awemes)
            except Exception as exc:
                logger.warning(
                    "[douyin-ingest] keyword fetch failed niche=%s: %s",
                    niche.get("slug"), exc,
                )
                break
            if not cursor:
                break

    # Hashtag pool — top-N tags per niche.
    raw_hashtags = niche.get("signal_hashtags_zh") or []
    fetch_hashtags = list(raw_hashtags)[: BATCH_DOUYIN_HASHTAG_FETCH_LIMIT]
    for tag in fetch_hashtags:
        try:
            awemes, _ = await fetch_douyin_hashtag_posts(tag, cursor=0)
            candidates.extend(awemes)
        except Exception as exc:
            logger.warning(
                "[douyin-ingest] hashtag fetch failed niche=%s tag=%s: %s",
                niche.get("slug"), tag, exc,
            )

    # Dedupe by aweme_id within the pool.
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for a in candidates:
        if not isinstance(a, dict):
            continue
        vid = str(a.get("aweme_id") or "")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        deduped.append(a)
    return deduped


# ── Quality gates ──────────────────────────────────────────────────


def _passes_quality_gates(aweme: dict[str, Any]) -> tuple[bool, str | None]:
    """Returns ``(passes, reason_if_skipped)``. Cheap pre-Gemini filter."""
    stats = aweme.get("statistics") or {}
    try:
        views = int(stats.get("play_count") or 0)
    except (TypeError, ValueError):
        views = 0
    if views < BATCH_DOUYIN_MIN_VIEWS:
        return False, f"views={views} < min={BATCH_DOUYIN_MIN_VIEWS}"

    likes = int(stats.get("digg_count") or 0)
    comments = int(stats.get("comment_count") or 0)
    shares = int(stats.get("share_count") or 0)
    saves = int(stats.get("collect_count") or 0)
    er = (
        (likes + comments + shares + saves) / max(views, 1) * 100.0
        if views > 0 else 0.0
    )
    if er < BATCH_DOUYIN_MIN_ER:
        return False, f"er={er:.2f}% < min={BATCH_DOUYIN_MIN_ER}%"

    return True, None


# ── Shot row builder (douyin_video_shots dual-write) ─────────────────


def build_douyin_shot_rows(
    corpus_row: dict[str, Any],
    scene_frame_urls: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """Project a ``douyin_video_corpus`` row + per-scene frame URLs into
    ``douyin_video_shots`` row dicts ready for upsert.

    Mirrors ``video_shots_writer.build_video_shot_rows`` but for the
    Douyin shot table — different denormalized fields (``douyin_url``
    not ``tiktok_url``, ``views`` denormalized for the FE chip).

    Scenes with invalid bounds (``end <= start``, missing values) are
    silently dropped to avoid the CHECK-constraint violation that would
    fail the whole upsert batch.
    """
    video_id = corpus_row.get("video_id")
    niche_id = corpus_row.get("niche_id")
    if not video_id or niche_id is None:
        return []

    analysis_json = corpus_row.get("analysis_json") or {}
    scenes = analysis_json.get("scenes") or []
    if not scenes:
        return []

    hook_type = corpus_row.get("hook_type")
    creator_handle = corpus_row.get("creator_handle")
    thumbnail_url = corpus_row.get("thumbnail_url")
    douyin_url = corpus_row.get("douyin_url")
    views_raw = corpus_row.get("views")
    try:
        views = int(views_raw) if views_raw is not None else None
    except (TypeError, ValueError):
        views = None

    frame_urls = scene_frame_urls or {}

    rows: list[dict[str, Any]] = []
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        start = scene.get("start")
        end = scene.get("end")
        try:
            start_f = float(start) if start is not None else None
            end_f = float(end) if end is not None else None
        except (TypeError, ValueError):
            continue
        if start_f is None or end_f is None or end_f <= start_f:
            continue

        rows.append({
            "video_id": str(video_id),
            "niche_id": int(niche_id),
            "scene_index": i,
            "start_s": start_f,
            "end_s": end_f,
            "scene_type": _coerce_optional_str(scene.get("type")),
            "framing": _coerce_optional_str(scene.get("framing")),
            "pace": _coerce_optional_str(scene.get("pace")),
            "overlay_style": _coerce_optional_str(scene.get("overlay_style")),
            "subject": _coerce_optional_str(scene.get("subject")),
            "motion": _coerce_optional_str(scene.get("motion")),
            "description": _coerce_optional_str(scene.get("description")),
            "hook_type": _coerce_optional_str(hook_type),
            "creator_handle": _coerce_optional_str(creator_handle),
            "thumbnail_url": _coerce_optional_str(thumbnail_url),
            "douyin_url": _coerce_optional_str(douyin_url),
            "frame_url": frame_urls.get(i),
            "views": views,
        })
    return rows


def _coerce_optional_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _upsert_douyin_corpus_rows_sync(
    client: Any,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    client.table("douyin_video_corpus").upsert(
        rows, on_conflict="video_id"
    ).execute()


def _upsert_douyin_shots_sync(
    client: Any,
    shot_rows: list[dict[str, Any]],
) -> None:
    if not shot_rows:
        return
    client.table("douyin_video_shots").upsert(
        shot_rows, on_conflict="video_id,scene_index"
    ).execute()


# D6e — bounded shot upsert retry. Audit M6: when the corpus row lands
# but the shot upsert fails, the dedupe set blocks next-day re-ingest
# from re-attempting (corpus row exists). Retry the shot upsert a few
# times with exponential backoff before giving up; the in-flight ingest
# is the only place we can self-heal without a schema migration.
_SHOT_UPSERT_MAX_ATTEMPTS = 3
_SHOT_UPSERT_BACKOFF_BASE_SEC = 0.5


def _upsert_douyin_shots_with_retry_sync(
    client: Any,
    shot_rows: list[dict[str, Any]],
) -> tuple[bool, Exception | None]:
    """Retry shot upsert up to ``_SHOT_UPSERT_MAX_ATTEMPTS`` times with
    a 0.5s / 1.0s / 2.0s backoff. Returns ``(success, last_exception)``.

    The retry is synchronous; callers wrap it in ``run_in_executor``.
    """
    import time

    last_exc: Exception | None = None
    for attempt in range(_SHOT_UPSERT_MAX_ATTEMPTS):
        try:
            _upsert_douyin_shots_sync(client, shot_rows)
            return True, None
        except Exception as exc:
            last_exc = exc
            if attempt < _SHOT_UPSERT_MAX_ATTEMPTS - 1:
                time.sleep(_SHOT_UPSERT_BACKOFF_BASE_SEC * (2 ** attempt))
                continue
    return False, last_exc


# ── Per-video analyze + translate + build ───────────────────────────


async def _analyze_translate_one(
    aweme: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[tuple[int, str]], Any]:
    """Returns ``(analysis, hook_frame_urls, scene_frame_pairs, translation_or_None)``.

    Concurrency: video analysis (Gemini multimodal, slow — ~10s) runs
    in parallel with the Chinese→VN translation (Gemini text-only,
    fast — ~1s) so the wall time is dominated by the analysis.

    On any single-step failure the function still returns — the caller
    builds the row with whatever pieces succeeded; translation failure
    surfaces as ``translation=None`` (D3 synth re-attempts later).
    """
    sem = get_analysis_semaphore()
    async with sem:
        ct = ensemble.detect_content_type(aweme)
        desc_zh = str(aweme.get("desc", "") or "")
        creator = str(((aweme.get("author") or {}).get("unique_id")) or "")

        # Carousels: skip download, analyze the slide payload.
        if ct == "carousel":
            translation_task = asyncio.get_event_loop().run_in_executor(
                None, lambda: translate_douyin_caption(desc_zh, creator_handle=creator)
            )
            analysis = await analyze_aweme(aweme, include_diagnosis=False)
            translation = await translation_task
            return analysis, [], [], translation

        video_urls = ensemble.extract_video_urls(aweme)
        if not video_urls:
            return (
                {"error": "No video URLs in aweme",
                 "metadata": ensemble.parse_metadata(aweme).model_dump()},
                [], [], None,
            )

        video_path: Path | None = None
        try:
            try:
                video_path = await ensemble.download_video(video_urls)
            except Exception as exc:
                return (
                    {"error": str(exc),
                     "metadata": ensemble.parse_metadata(aweme).model_dump()},
                    [], [], None,
                )

            vid = str(aweme.get("aweme_id", "") or "")

            async def _noop_frames() -> list[str]:
                return []

            translation_task = asyncio.get_event_loop().run_in_executor(
                None, lambda: translate_douyin_caption(desc_zh, creator_handle=creator)
            )
            frame_coro = (
                extract_and_upload(video_path, vid)
                if r2_configured()
                else _noop_frames()
            )
            analysis, hook_frames, translation = await asyncio.gather(
                analyze_aweme_from_path(aweme, video_path, include_diagnosis=False),
                frame_coro,
                translation_task,
            )

            # Scene-frame extraction (after analysis — needs scene boundaries).
            scene_frame_pairs: list[tuple[int, str]] = []
            if r2_configured():
                scenes = (analysis.get("analysis") or {}).get("scenes") or []
                if scenes:
                    try:
                        scene_frame_pairs = await extract_and_upload_scene_frames(
                            video_path, vid, scenes,
                        )
                    except Exception as exc:
                        logger.warning(
                            "[douyin-ingest] scene frame extraction raised for %s: %s",
                            vid, exc,
                        )

            return (
                analysis,
                hook_frames if isinstance(hook_frames, list) else [],
                scene_frame_pairs,
                translation,
            )
        finally:
            if video_path is not None:
                video_path.unlink(missing_ok=True)


async def _ingest_candidate_awemes_douyin(
    client: Any,
    niche: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> DouyinIngestResult:
    """Analyze + translate + upsert a list of pre-filtered awemes."""
    niche_id = int(niche["id"])
    niche_name = str(niche.get("slug") or niche.get("name_vn") or "?")
    result = DouyinIngestResult(niche_id=niche_id, niche_name=niche_name)
    if not candidates:
        return result

    logger.info(
        "[douyin-ingest] niche=%s — analyzing %d candidates",
        niche_name, len(candidates),
    )

    gathered = await asyncio.gather(
        *[_analyze_translate_one(a) for a in candidates],
        return_exceptions=True,
    )

    rows: list[dict[str, Any]] = []
    hook_frames_by_id: dict[str, list[str]] = {}
    scene_frames_by_id: dict[str, dict[int, str]] = {}

    for aweme, gather_result in zip(candidates, gathered):
        if isinstance(gather_result, Exception):
            logger.warning("[douyin-ingest] analyze error: %s", gather_result)
            result.failed += 1
            result.errors.append(str(gather_result))
            continue
        analysis, hook_frames, scene_frame_pairs, translation = gather_result
        row = build_douyin_corpus_row(
            aweme, analysis, niche_id, translation=translation,
        )
        if row is None:
            result.skipped_quality += 1
            continue
        if hook_frames:
            row["frame_urls"] = hook_frames
            hook_frames_by_id[row["video_id"]] = hook_frames
        if scene_frame_pairs:
            scene_frames_by_id[row["video_id"]] = dict(scene_frame_pairs)
        rows.append(row)

    if not rows:
        return result

    # Upsert corpus rows.
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: _upsert_douyin_corpus_rows_sync(client, rows),
        )
    except Exception as exc:
        logger.exception("[douyin-ingest] corpus upsert failed: %s", exc)
        result.failed += len(rows)
        result.errors.append(f"corpus upsert: {exc}")
        return result

    # Dual-write shot rows for the matcher (analog of video_shots).
    shot_rows: list[dict[str, Any]] = []
    for row in rows:
        shot_rows.extend(
            build_douyin_shot_rows(
                row, scene_frames_by_id.get(row["video_id"])
            )
        )
    if shot_rows:
        # D6e (audit M6) — wrap in a 3-attempt retry to self-heal
        # transient PostgREST blips. The dedupe set means next-day
        # ingest won't re-attempt for any rows whose shots fail
        # permanently; manual backfill is the escape hatch.
        ok, last_exc = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _upsert_douyin_shots_with_retry_sync(client, shot_rows),
        )
        if not ok:
            logger.warning(
                "[douyin-ingest] shot upsert failed after %d attempts "
                "(corpus rows still landed): %s",
                _SHOT_UPSERT_MAX_ATTEMPTS, last_exc,
            )

    result.inserted = len(rows)
    logger.info(
        "[douyin-ingest] niche=%s — upserted %d rows + %d shot rows",
        niche_name, len(rows), len(shot_rows),
    )
    return result


# ── Per-niche orchestrator ──────────────────────────────────────────


async def ingest_douyin_niche(
    niche: dict[str, Any],
    client: Any,
    *,
    deep: bool = False,
) -> DouyinIngestResult:
    """Fetch candidate pool → dedupe → quality-gate → analyze + upsert."""
    niche_id = int(niche["id"])
    niche_name = str(niche.get("slug") or niche.get("name_vn") or "?")
    result = DouyinIngestResult(niche_id=niche_id, niche_name=niche_name)

    pool = await _fetch_douyin_pool(niche, deep=deep)
    result.fetched = len(pool)
    if not pool:
        return result

    existing = await _existing_douyin_video_ids(client, niche_id)
    deduped: list[dict[str, Any]] = []
    for aweme in pool:
        vid = str(aweme.get("aweme_id") or "")
        if not vid or vid in existing:
            result.skipped_dedupe += 1
            continue
        deduped.append(aweme)

    qualified: list[dict[str, Any]] = []
    for aweme in deduped:
        ok, reason = _passes_quality_gates(aweme)
        if not ok:
            result.skipped_quality += 1
            logger.debug(
                "[douyin-ingest] skip %s — %s",
                aweme.get("aweme_id"), reason,
            )
            continue
        qualified.append(aweme)
        if len(qualified) >= BATCH_DOUYIN_VIDEOS_PER_NICHE:
            break

    if not qualified:
        return result

    sub = await _ingest_candidate_awemes_douyin(client, niche, qualified)
    result.inserted = sub.inserted
    result.failed = sub.failed
    result.errors.extend(sub.errors)
    # Don't double-count quality skips already counted by build_row None.
    result.skipped_quality += sub.skipped_quality
    return result


# ── Top-level entrypoint ────────────────────────────────────────────


async def run_douyin_batch_ingest(
    *,
    niche_ids: list[int] | None = None,
    deep: bool = False,
) -> DouyinBatchSummary:
    """Run the daily Douyin ingest. ``niche_ids=None`` runs all active
    niches; passing an explicit list scopes the run (admin reruns)."""
    summary = DouyinBatchSummary()
    client = _service_client()

    niches = await _fetch_active_douyin_niches(client)
    if niche_ids:
        wanted = set(niche_ids)
        niches = [n for n in niches if int(n["id"]) in wanted]

    if not niches:
        logger.info("[douyin-ingest] no active niches to process")
        return summary

    logger.info(
        "[douyin-ingest] starting — %d niches, concurrency=%d, deep=%s",
        len(niches), BATCH_DOUYIN_CONCURRENCY, deep,
    )

    sem = asyncio.Semaphore(max(1, BATCH_DOUYIN_CONCURRENCY))

    async def _one(n: dict[str, Any]) -> DouyinIngestResult:
        async with sem:
            try:
                return await ingest_douyin_niche(n, client, deep=deep)
            except Exception as exc:
                logger.exception(
                    "[douyin-ingest] niche %s failed: %s",
                    n.get("slug"), exc,
                )
                r = DouyinIngestResult(
                    niche_id=int(n["id"]),
                    niche_name=str(n.get("slug") or "?"),
                )
                r.failed += 1
                r.errors.append(str(exc))
                return r

    results = await asyncio.gather(*[_one(n) for n in niches])

    for r in results:
        summary.niches_processed += 1
        summary.total_inserted += r.inserted
        summary.total_skipped += r.skipped_dedupe + r.skipped_quality
        summary.total_failed += r.failed
        summary.niche_results.append({
            "niche_id": r.niche_id,
            "niche_name": r.niche_name,
            "fetched": r.fetched,
            "skipped_dedupe": r.skipped_dedupe,
            "skipped_quality": r.skipped_quality,
            "inserted": r.inserted,
            "failed": r.failed,
            "errors": r.errors[:5],
        })

    logger.info(
        "[douyin-ingest] done — inserted=%d skipped=%d failed=%d niches=%d",
        summary.total_inserted, summary.total_skipped,
        summary.total_failed, summary.niches_processed,
    )
    return summary
