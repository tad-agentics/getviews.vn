"""Batch corpus ingest, analytics, and maintenance routes."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from getviews_pipeline.api_models import StrictBody
from getviews_pipeline.deps import require_batch_caller
from getviews_pipeline.runtime import run_sync

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/batch/ping")
async def batch_ping(
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Cheap auth probe for Vault + pg_cron wiring (URL + ``X-Batch-Secret``).

    Returns immediately — use to confirm ``cloud_run_api_url`` points at the
    service that mounts ``/batch/*`` (the batch pod), not the user-only pod.
    """
    return JSONResponse({"ok": True})


class BatchIngestRequest(StrictBody):
    niche_ids: list[int] | None = Field(
        default=None,
        description="Restrict to specific niche IDs. Omit to ingest all niches.",
    )
    deep_pool: bool = Field(
        default=False,
        description=(
            "Widen keyword pagination and per-niche video/carousel caps to re-overlap "
            "a prior candidate pool after outages (e.g. Gemini model 404s)."
        ),
    )
    wall_clock_budget_s: int = Field(
        default=3400,
        ge=0,
        description=(
            "Stop processing niches after this many seconds to avoid the Cloud Run "
            "request timeout (3600s). A 120s safety buffer is applied internally so "
            "the function always returns before the container is killed. "
            "Set to 0 to disable (manual ops only — never for scheduled cron)."
        ),
    )
    ingest_shift: str | None = Field(
        default=None,
        description=(
            "Nightly class-loop slice: a–f. Split active content_class_ingest_targets "
            "into ingest_shift_count priority-ordered chunks; this run processes one chunk."
        ),
    )
    ingest_shift_count: int = Field(
        default=3,
        ge=1,
        le=6,
        description="Number of nightly ingest shifts (default 3 cron jobs: a, b, c).",
    )

    @field_validator("ingest_shift")
    @classmethod
    def _normalize_ingest_shift(cls, v: str | None) -> str | None:
        if v is None:
            return None
        letter = v.strip().lower()
        if letter not in "abcdef":
            raise ValueError("ingest_shift must be a–f")
        return letter

    @field_validator("ingest_shift_count")
    @classmethod
    def _validate_shift_letter_in_range(cls, v: int, info) -> int:
        shift = info.data.get("ingest_shift")
        if shift is not None and "abcdef".index(shift) >= v:
            raise ValueError(
                f"ingest_shift={shift!r} requires ingest_shift_count > "
                f"{ 'abcdef'.index(shift) }",
            )
        return v


class BatchReingestVideosRequest(StrictBody):
    items: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description='Each item: {"video_id": "<aweme_id>", "niche_id": <int>} (aweme_id alias allowed).',
    )
    refresh_mv: bool = Field(default=True, description="Refresh niche_intelligence after upserts.")


class RitualBatchRequest(StrictBody):
    user_ids: list[str] | None = Field(
        default=None,
        description="Restrict to specific user ids. Omit for all users.",
    )


class PatternDecksBatchRequest(StrictBody):
    cap: int | None = Field(
        default=None,
        ge=1, le=500,
        description=(
            "Max patterns to synthesize this run. Omit to use the module "
            "default (DEFAULT_BATCH_CAP). Lower this when running mid-day "
            "smoke tests to keep Gemini cost bounded."
        ),
    )
    pattern_ids: list[str] | None = Field(
        default=None,
        description=(
            "Restrict the run to specific pattern IDs (UUID strings). "
            "Bypasses the staleness query — use for admin manual reruns "
            "after a pattern's grounding videos materially change."
        ),
    )


@router.post("/batch/ingest")
async def batch_ingest(
    request: Request,
    body: BatchIngestRequest = BatchIngestRequest(),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Trigger video corpus batch ingest.

    Protected by require_batch_caller (X-Batch-Secret legacy or admin JWT).
    Intended to be called by Cloud Scheduler — not exposed to end users.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.corpus_ingest import run_batch_ingest
    from getviews_pipeline.ensemble import EnsembleDailyBudgetExceeded
    from getviews_pipeline.supabase_client import get_service_client

    logger.info(
        "POST /batch/ingest triggered — niche_ids=%s deep_pool=%s wall_clock_budget_s=%d "
        "ingest_shift=%s ingest_shift_count=%d",
        body.niche_ids,
        body.deep_pool,
        body.wall_clock_budget_s,
        body.ingest_shift,
        body.ingest_shift_count,
    )
    async with record_job_run(get_service_client(), "batch/ingest") as obs_summary:
        obs_summary["niche_ids"] = body.niche_ids
        obs_summary["deep_pool"] = body.deep_pool
        obs_summary["wall_clock_budget_s"] = body.wall_clock_budget_s
        obs_summary["ingest_shift"] = body.ingest_shift
        obs_summary["ingest_shift_count"] = body.ingest_shift_count
        try:
            summary = await run_batch_ingest(
                niche_ids=body.niche_ids,
                deep_pool=body.deep_pool,
                wall_clock_budget_s=body.wall_clock_budget_s,
                ingest_shift=body.ingest_shift,
                ingest_shift_count=body.ingest_shift_count,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except EnsembleDailyBudgetExceeded as exc:
            logger.error("Batch ingest aborted (ED daily budget): %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("Batch ingest failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        obs_summary.update({
            "total_inserted": summary.total_inserted,
            "total_skipped": summary.total_skipped,
            "total_failed": summary.total_failed,
            "niches_processed": summary.niches_processed,
            "materialized_view_refreshed": summary.materialized_view_refreshed,
            "aborted_early": summary.aborted_early,
            "skipped_duplicate_run": summary.skipped_duplicate_run,
            "niches_remaining": summary.niches_remaining,
            "content_class_ids_planned": summary.content_class_ids_planned,
            "remaining_content_class_ids": summary.remaining_content_class_ids,
            "niche_results": summary.niche_results,
            "hi13": {
                "batch_line_ok": summary.hi13_batch_line_ok,
                "batch_line_fail": summary.hi13_batch_line_fail,
                "sync_fallback": summary.hi13_sync_fallback,
                "batch_jobs_ok": summary.hi13_batch_jobs_ok,
                "batch_jobs_failed": summary.hi13_batch_jobs_failed,
            },
        })

    return JSONResponse({
        "ok": True,
        "total_inserted": summary.total_inserted,
        "total_skipped": summary.total_skipped,
        "total_failed": summary.total_failed,
        "niches_processed": summary.niches_processed,
        "materialized_view_refreshed": summary.materialized_view_refreshed,
        "aborted_early": summary.aborted_early,
        "niches_remaining": summary.niches_remaining,
        "ingest_shift": summary.ingest_shift,
        "ingest_shift_count": summary.ingest_shift_count,
        "content_class_ids_planned": summary.content_class_ids_planned,
        "remaining_content_class_ids": summary.remaining_content_class_ids,
        "niche_results": summary.niche_results,
    })


@router.post("/batch/hi13-pilot")
async def batch_hi13_pilot(
    limit: int = Query(10, ge=1, le=20),
    niche_id: int | None = Query(None, description="Optional legacy ingest_loop niche id"),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """HI-13 pilot — Gemini Batch JSONL for ``limit`` videos; no corpus upsert."""
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.corpus_ingest import run_hi13_batch_pilot
    from getviews_pipeline.supabase_client import get_service_client

    logger.info("POST /batch/hi13-pilot limit=%d niche_id=%s", limit, niche_id)
    client = get_service_client()
    async with record_job_run(client, "batch/hi13-pilot") as obs_summary:
        obs_summary["limit"] = limit
        obs_summary["niche_id"] = niche_id
        try:
            result = await run_hi13_batch_pilot(limit=limit, niche_id=niche_id)
        except Exception as exc:
            logger.exception("HI-13 pilot failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": result.get("ok", False), **result})


@router.post("/batch/post-processing")
async def batch_post_processing(
    request: Request,
    weekly_if_sunday: bool = Query(
        default=True,
        description="When false, skip the Sunday-only weekly analytics block (MV + VDH + Layer0B still run).",
    ),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """ME-16 — heal MV / Video Đáng Học / sound insights after an aborted ingest or ops rerun.

    Daily pg_cron ``cron-batch-post-processing`` (23:30 UTC) complements
    ``/batch/ingest`` so wall-clock aborts do not leave aggregates stale overnight.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.corpus_ingest import run_ingest_post_processing
    from getviews_pipeline.supabase_client import get_service_client

    logger.info("POST /batch/post-processing — weekly_if_sunday=%s", weekly_if_sunday)
    client = get_service_client()
    async with record_job_run(client, "batch/post-processing") as obs_summary:
        try:
            result = await run_ingest_post_processing(
                client,
                run_weekly_analytics_if_sunday=weekly_if_sunday,
            )
        except Exception as exc:
            logger.exception("Batch post-processing failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": True, **result})


class BatchDouyinIngestRequest(StrictBody):
    """D2d (2026-06-03) — body for ``POST /batch/douyin-ingest``.

    Mirrors ``BatchIngestRequest`` shape but:
      • ``deep`` (not ``deep_pool``) — the Douyin pool fetcher's deep
        flag widens keyword pagination only; there's no separate
        carousel pool to override.
      • Fewer fields — no Gemini-cascade / hashtag-yield knobs because
        the v1 Douyin pipeline doesn't have those layers yet.
    """

    niche_ids: list[int] | None = Field(
        default=None,
        description="Restrict to specific douyin_niche_taxonomy IDs. Omit to ingest all active niches.",
    )
    deep: bool = Field(
        default=False,
        description="Widen keyword pagination per niche (manual ops only — daily cron leaves this false).",
    )


@router.post("/batch/douyin-ingest")
async def batch_douyin_ingest(
    request: Request,
    body: BatchDouyinIngestRequest = BatchDouyinIngestRequest(),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """D2d (2026-06-03) — daily Kho Douyin ingest entrypoint.

    Protected by ``require_batch_caller`` (X-Batch-Secret legacy or
    admin JWT). Driven by the doc-only pg_cron schedule
    ``cron-batch-douyin-ingest`` (see migration
    ``20260603000003_pg_cron_douyin_ingest.sql``) at 22:00 UTC daily
    (05:00 Asia/Ho_Chi_Minh — 2hr after VN ``cron-batch-ingest`` so
    the two pipelines never compete for the EnsembleData budget gate).

    Returns a summary mirroring the VN ``/batch/ingest`` response shape
    so existing batch_observability dashboards can render Douyin runs
    side-by-side with VN ones.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.douyin_ingest import run_douyin_batch_ingest
    from getviews_pipeline.ensemble import EnsembleDailyBudgetExceeded
    from getviews_pipeline.supabase_client import get_service_client

    logger.info(
        "POST /batch/douyin-ingest triggered — niche_ids=%s deep=%s",
        body.niche_ids, body.deep,
    )
    async with record_job_run(get_service_client(), "batch/douyin-ingest") as obs_summary:
        obs_summary["niche_ids"] = body.niche_ids
        obs_summary["deep"] = body.deep
        try:
            summary = await run_douyin_batch_ingest(
                niche_ids=body.niche_ids,
                deep=body.deep,
            )
        except EnsembleDailyBudgetExceeded as exc:
            logger.error("Douyin batch ingest aborted (ED daily budget): %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("Douyin batch ingest failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        obs_summary.update({
            "total_inserted": summary.total_inserted,
            "total_skipped": summary.total_skipped,
            "total_failed": summary.total_failed,
            "niches_processed": summary.niches_processed,
        })

    return JSONResponse({
        "ok": True,
        "total_inserted": summary.total_inserted,
        "total_skipped": summary.total_skipped,
        "total_failed": summary.total_failed,
        "niches_processed": summary.niches_processed,
        "niche_results": summary.niche_results,
    })


@router.post("/batch/backfill-boost-attribution")
async def batch_backfill_boost_attribution(
    request: Request,
    dry_run: bool = Query(False),
    limit: int = Query(0, ge=0),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Reclassify legacy ``unknown`` boost_attribution rows (metadata-only, no Gemini)."""
    from getviews_pipeline.boost_attribution_backfill import run_boost_attribution_backfill_sync
    from getviews_pipeline.runtime import run_sync
    from getviews_pipeline.supabase_client import get_service_client

    logger.info(
        "POST /batch/backfill-boost-attribution dry_run=%s limit=%d",
        dry_run,
        limit,
    )
    try:
        stats = await run_sync(
            run_boost_attribution_backfill_sync,
            get_service_client(),
            limit=limit,
            dry_run=dry_run,
        )
    except Exception as exc:
        logger.exception("boost attribution backfill failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({"ok": True, **stats})


@router.post("/batch/reingest-videos")
async def batch_reingest_videos(
    request: Request,
    body: BatchReingestVideosRequest,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Re-analyze explicit TikTok video IDs and upsert into video_corpus.

    Protected by require_batch_caller. Intended for recovery after a bad model
    rollout when logs did not retain the original hashtag-pool ordering.
    """
    from getviews_pipeline.corpus_ingest import run_reingest_video_items
    from getviews_pipeline.ensemble import EnsembleDailyBudgetExceeded

    logger.info("POST /batch/reingest-videos — %d items", len(body.items))
    try:
        summary = await run_reingest_video_items(body.items, refresh_mv=body.refresh_mv)
    except EnsembleDailyBudgetExceeded as exc:
        logger.error("Batch reingest aborted (ED daily budget): %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Batch reingest failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({
        "ok": True,
        "total_inserted": summary.total_inserted,
        "total_skipped": summary.total_skipped,
        "total_failed": summary.total_failed,
        "niches_processed": summary.niches_processed,
        "materialized_view_refreshed": summary.materialized_view_refreshed,
        "niche_results": summary.niche_results,
    })


@router.post("/batch/process-ingest-queue")
async def batch_process_ingest_queue(
    limit: int = Query(50, ge=1, le=200),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Drain corpus_ingest_queue into full corpus ingest (Gemini + video_corpus upsert)."""
    from getviews_pipeline.corpus_ingest import run_reingest_video_items
    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    res = (
        client.table("corpus_ingest_queue")
        .select("aweme_id, niche_id")
        .is_("processed_at", "null")
        .order("queued_at")
        .limit(limit)
        .execute()
    )
    rows: list[dict[str, Any]] = res.data or []
    items: list[dict[str, Any]] = []
    for r in rows:
        aid = r.get("aweme_id")
        nid = r.get("niche_id")
        if not aid or nid is None:
            continue
        try:
            items.append({"video_id": str(aid), "niche_id": int(nid)})
        except (TypeError, ValueError):
            continue
    if not items:
        return JSONResponse({"ok": True, "queue_rows": 0, "message": "queue empty"})

    try:
        summary = await run_reingest_video_items(items, refresh_mv=True)
    except Exception as exc:
        logger.exception("POST /batch/process-ingest-queue reingest failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    now_iso = datetime.now(UTC).isoformat()
    for r in rows:
        aid = r.get("aweme_id")
        if not aid:
            continue
        try:
            client.table("corpus_ingest_queue").update({"processed_at": now_iso}).eq(
                "aweme_id", str(aid)
            ).execute()
        except Exception as exc:
            logger.warning(
                "[corpus_ingest_queue] mark processed failed aweme_id=%s: %s",
                aid,
                exc,
            )

    return JSONResponse({
        "ok": True,
        "queue_rows": len(rows),
        "total_inserted": summary.total_inserted,
        "total_skipped": summary.total_skipped,
        "total_failed": summary.total_failed,
    })


@router.post("/batch/refresh")
async def batch_refresh(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Refresh ``video_corpus`` engagement stats for the top-priority rows.

    Metadata-only — no Gemini re-analyze, just re-pull views/likes/etc.
    from EnsembleData. Closes the Axis 3 freshness gap (state-of-corpus.md).
    Protected by require_batch_caller. Intended cadence: daily.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.corpus_refresh import run_corpus_refresh
    from getviews_pipeline.supabase_client import get_service_client

    logger.info("POST /batch/refresh triggered")
    client = get_service_client()

    async with record_job_run(client, "batch/refresh") as obs_summary:
        try:
            result = await run_corpus_refresh(client=client)
        except Exception as exc:
            logger.exception("Batch refresh failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": True, **result})


class BatchReclassifyFormatRequest(StrictBody):
    """Optional bucket to re-audit (default ``other``/NULL catch-up tail)."""
    source_format: str = "other"


@router.post("/batch/reclassify-format")
async def batch_reclassify_format(
    body: BatchReclassifyFormatRequest = BatchReclassifyFormatRequest(),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """One-shot: re-run classify_format on rows stuck in ``other``/NULL.

    Axis 2 catch-up (state-of-corpus.md). Zero Gemini cost — pure regex
    pass on cached analysis_json. Safe to re-run; idempotent.
    Pass ``source_format`` (e.g. ``mukbang``) to re-audit a specific bucket.
    Protected by require_batch_caller.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.content_format_reclassify import (
        run_content_format_reclassify,
    )
    from getviews_pipeline.runtime import run_sync
    from getviews_pipeline.supabase_client import get_service_client

    logger.info(
        "POST /batch/reclassify-format triggered source_format=%s",
        body.source_format,
    )
    client = get_service_client()

    async with record_job_run(client, "batch/reclassify-format") as obs_summary:
        try:
            result = await run_sync(
                run_content_format_reclassify,
                client=client,
                source_format=body.source_format,
            )
        except Exception as exc:
            logger.exception("Batch reclassify-format failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": True, **result})


class BatchClassificationBackfillRequest(StrictBody):
    """ME-17 — nightly (or manual) Gemini text backfill for legacy corpus rows."""

    batch_size: int = Field(default=3500, ge=1, le=10_000)
    max_runtime_s: int = Field(default=3300, ge=60, le=7200)
    dry_run: bool = Field(default=False)


@router.post("/batch/backfill-classification")
async def batch_backfill_classification(
    body: BatchClassificationBackfillRequest = BatchClassificationBackfillRequest(),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Protected by ``require_batch_caller`` — intended for pg_cron on the batch URL."""
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.classification_backfill import run_classification_backfill
    from getviews_pipeline.runtime import run_sync
    from getviews_pipeline.supabase_client import get_service_client

    logger.info(
        "POST /batch/backfill-classification batch_size=%d max_runtime_s=%d dry_run=%s",
        body.batch_size,
        body.max_runtime_s,
        body.dry_run,
    )
    client = get_service_client()

    async with record_job_run(client, "batch/backfill-classification") as obs_summary:
        try:
            result = await run_sync(
                run_classification_backfill,
                client=client,
                batch_size=body.batch_size,
                max_runtime_s=float(body.max_runtime_s),
                dry_run=body.dry_run,
            )
        except Exception as exc:
            logger.exception("Batch backfill-classification failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": True, **result})


class BatchCrossNicheRemapBackfillRequest(StrictBody):
    batch_size: int = Field(default=500, ge=1, le=5000)
    max_runtime_s: int = Field(default=3300, ge=60, le=7200)
    dry_run: bool = Field(default=False)
    video_ids: list[str] | None = None


@router.post("/batch/backfill-cross-niche-remap")
async def batch_backfill_cross_niche_remap(
    body: BatchCrossNicheRemapBackfillRequest = BatchCrossNicheRemapBackfillRequest(),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.classification_backfill import run_cross_niche_class_remap_backfill
    from getviews_pipeline.runtime import run_sync
    from getviews_pipeline.supabase_client import get_service_client

    logger.info(
        "POST /batch/backfill-cross-niche-remap batch_size=%d dry_run=%s",
        body.batch_size,
        body.dry_run,
    )
    client = get_service_client()

    async with record_job_run(client, "batch/backfill-cross-niche-remap") as obs_summary:
        try:
            result = await run_sync(
                run_cross_niche_class_remap_backfill,
                client=client,
                batch_size=body.batch_size,
                max_runtime_s=float(body.max_runtime_s),
                dry_run=body.dry_run,
                video_ids=body.video_ids,
            )
        except Exception as exc:
            logger.exception("Batch backfill-cross-niche-remap failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": True, **result})


@router.post("/batch/sound-aggregate")
async def batch_sound_aggregate(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Aggregate trending sounds per niche for the current week.

    Standalone counterpart to ``run_sound_aggregation`` which previously
    only fired at the *end* of ``/batch/ingest``. The full ingest pipeline
    occasionally exceeds the pg_cron 5-min HTTP timeout, killing the
    sound aggregator step before ``trending_sounds`` gets refreshed —
    leaving the L1.4 pattern report's ``top_sounds`` cell stuck on last
    week's data. This endpoint runs only the aggregator (~30s) so the
    weekly cron stays inside the timeout window.

    Idempotent: upserts on ``(niche_id, sound_id, week_of)``. Cost:
    zero Gemini, ~50 small Supabase reads + 1 batched upsert per niche.
    Protected by ``require_batch_caller``.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.sound_aggregator import run_sound_aggregation
    from getviews_pipeline.supabase_client import get_service_client

    logger.info("POST /batch/sound-aggregate triggered")
    client = get_service_client()

    async with record_job_run(client, "batch/sound-aggregate") as obs_summary:
        try:
            result = await run_sound_aggregation(client)
        except Exception as exc:
            logger.exception("Batch sound-aggregate failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": True, **result})


@router.post("/batch/trend-velocity")
async def batch_trend_velocity(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Compute weekly trend_velocity rows (hook shifts + Sound Radar) per niche.

    L2.2 Sprint 2 — Sound Radar. Standalone runner so the cron is
    independent of the heavier Sunday ``/batch/analytics`` job. Reads
    ``trending_sounds`` (refreshed by ``/batch/sound-aggregate`` at
    Monday 21:30 UTC) and ``video_corpus`` (continuously refreshed by
    ``/batch/ingest``); writes one row per niche to ``trend_velocity``
    keyed on ``(niche_id, week_start)``.

    Pre-launch corpus is small (~5k videos / 18 niches) so this runs
    in seconds — no risk of pg_cron timeout. Idempotent: upserts on
    ``(niche_id, week_start)``. Cost: zero Gemini, ~36 Supabase reads
    + 1 batched upsert.

    Schedule: Mondays 22:30 UTC (30 min after sound-aggregate so the
    Monday-aligned ``trending_sounds.week_of`` is fresh in time).
    Protected by ``require_batch_caller``.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.trend_velocity import run_trend_velocity

    logger.info("POST /batch/trend-velocity triggered")
    client = get_service_client()

    async with record_job_run(client, "batch/trend-velocity") as obs_summary:
        try:
            result = await run_trend_velocity(client)
        except Exception as exc:
            logger.exception("Batch trend-velocity failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update({
            "niches_processed": result.niches_processed,
            "rows_upserted":    result.rows_upserted,
            "errors":           result.errors,
        })

    return JSONResponse({
        "ok": not result.errors,
        "niches_processed": result.niches_processed,
        "rows_upserted":    result.rows_upserted,
        "errors":           result.errors,
    })


@router.post("/batch/stats-history-refetch")
async def batch_stats_history_refetch(
    limit: int = Query(80, ge=1, le=200),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """§4.7 M4 — append ``stats_history`` snapshots at T+6h / T+24h via EnsembleData.

    Metadata-only refetch; derives ``distribution_shape=spike_then_flat`` when
    criteria match. Intended cadence: hourly pg_cron on the batch pod.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.stats_history_m4 import run_stats_history_refetch
    from getviews_pipeline.supabase_client import get_service_client

    logger.info("POST /batch/stats-history-refetch triggered limit=%d", limit)
    client = get_service_client()

    async with record_job_run(client, "batch/stats-history-refetch") as obs_summary:
        try:
            result = await run_stats_history_refetch(client=client, limit=limit)
        except Exception as exc:
            logger.exception("Batch stats-history-refetch failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update({
            "candidates": result.candidates,
            "refreshed": result.refreshed,
            "missing": result.missing,
            "errors": result.errors,
            "shapes_set": result.shapes_set,
        })

    return JSONResponse({
        "ok": result.errors == 0 or result.refreshed > 0,
        "candidates": result.candidates,
        "refreshed": result.refreshed,
        "missing": result.missing,
        "errors": result.errors,
        "shapes_set": result.shapes_set,
    })


@router.post("/batch/r2-janitor")
async def batch_r2_janitor(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Reconcile R2 storage against video_corpus and delete orphans.

    Defaults to dry-run. Pass ``?dry_run=false`` (or POST body
    ``{"dry_run": false}``) to run the destructive pass. Idempotent
    in either mode — re-running just re-walks the same R2 prefixes.

    Cost: zero Gemini, zero ED. R2 LIST + DELETE class A operations
    are ~$0.20 per full sweep at current corpus size.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.r2_janitor import run_r2_janitor
    from getviews_pipeline.runtime import run_sync
    from getviews_pipeline.supabase_client import get_service_client

    # Accept dry_run from query string or JSON body; default True.
    dry_run = True
    qp = request.query_params.get("dry_run")
    if qp is not None:
        dry_run = qp.lower() not in ("0", "false", "no")
    else:
        try:
            body = await request.json()
            if isinstance(body, dict) and "dry_run" in body:
                dry_run = bool(body["dry_run"])
        except Exception:
            pass

    logger.info("POST /batch/r2-janitor triggered (dry_run=%s)", dry_run)
    client = get_service_client()

    async with record_job_run(client, "batch/r2-janitor") as obs_summary:
        try:
            result = await run_sync(run_r2_janitor, dry_run=dry_run, client=client)
        except Exception as exc:
            logger.exception("Batch r2-janitor failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": True, **result})


@router.post("/batch/seed-class-hashtags")
async def batch_seed_class_hashtags(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
    active_only: bool = Query(True, description="Only seed active content_class_ingest_targets"),
    backfill_signal: bool = Query(
        True,
        description="Write signal_hashtags on targets that have none",
    ),
) -> JSONResponse:
    """Seed hashtag_class_map + signal_hashtags for class-loop corpus discovery."""
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.hashtag_class_map import seed_class_discovery_sync
    from getviews_pipeline.supabase_client import get_service_client

    logger.info(
        "POST /batch/seed-class-hashtags active_only=%s backfill_signal=%s",
        active_only,
        backfill_signal,
    )
    client = get_service_client()
    async with record_job_run(client, "batch/seed-class-hashtags") as obs_summary:
        obs_summary["active_only"] = active_only
        obs_summary["backfill_signal_hashtags"] = backfill_signal
        try:
            from getviews_pipeline.runtime import run_sync

            result = await run_sync(
                seed_class_discovery_sync,
                client,
                active_only=active_only,
                backfill_signal_hashtags=backfill_signal,
            )
        except Exception as exc:
            logger.exception("Seed class hashtags failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": True, **result})


def _cover_url_from_ensemble_post(post: dict[str, Any] | None) -> str | None:
    """First TikTok cover URL from an EnsembleData post payload."""
    from getviews_pipeline.ensemble import cover_url_from_aweme_detail

    if not post or not isinstance(post, dict):
        return None
    detail = post.get("aweme_detail") or post
    if not isinstance(detail, dict):
        return None
    return cover_url_from_aweme_detail(detail)


@router.post("/batch/backfill-thumbnails")
async def batch_backfill_thumbnails(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
    ed_fallback: bool = Query(
        True,
        description=(
            "If true, after R2 frame copy and CDN mirror fail, batch-fetch "
            "EnsembleData multi_info and rehost a fresh cover to R2 (ED units + proxy)."
        ),
    ),
    limit: int | None = Query(
        None,
        ge=1,
        le=200_000,
        description="Max candidate rows to process; omit = all that need a stable R2 thumbnail.",
    ),
) -> JSONResponse:
    """Backfill ``video_corpus.thumbnail_url`` to a permanent R2 URL.

    Per-row strategy (in order):
      1. **R2 frame[0] transcode** — download ``frames/{vid}/0.png``, ffmpeg
         360w WebP → ``thumbnails/{vid}.webp``. Legacy ``.png`` thumbs are
         re-encoded the same way when frame[0] is missing.
      2. **CDN mirror fallback** — only when frame[0] is missing AND the
         row has a non-empty ``thumbnail_url``. Costs proxy bandwidth;
         the URL may already be expired (TikTok CDN tokens rotate every
         few weeks), in which case the download fails and we fall through.
      3. **EnsembleData fresh cover** (optional, ``ed_fallback``) — batch
         ``fetch_post_multi_info`` for rows still missing a thumbnail, then
         ``download_and_upload_thumbnail`` for each fresh cover URL.
         Use when the row never got frame[0] on R2 and CDN is dead/empty.
      4. **NULL the column** — when all steps miss, set ``thumbnail_url=NULL``
         so the FE uses ``<VideoThumbnail>`` placeholder.

    Rows whose ``thumbnail_url`` already points at a **live** R2 object
    (verified via ``head_object``) are skipped. Phantom DB URLs — R2 prefix
    in Postgres but object deleted/missing — are reprocessed. Reads are
    paginated to bypass the 1000-row Supabase default.

    Protected by ``require_batch_caller``. Idempotent — safe to re-run.
    """
    from getviews_pipeline import ensemble
    from getviews_pipeline.config import R2_PUBLIC_URL
    from getviews_pipeline.r2 import (
        copy_first_frame_to_thumbnail,
        download_and_upload_thumbnail,
        r2_configured,
        r2_public_thumbnail_exists,
    )
    from getviews_pipeline.supabase_client import get_service_client

    if not r2_configured():
        raise HTTPException(status_code=500, detail="R2 not configured")

    r2_prefix = R2_PUBLIC_URL.rstrip("/") if R2_PUBLIC_URL else None
    if not r2_prefix:
        raise HTTPException(status_code=500, detail="R2_PUBLIC_URL missing")

    sb = get_service_client()

    def _set_thumb(vid: str, url: str | None) -> None:
        sb.table("video_corpus").update({"thumbnail_url": url}).eq("video_id", vid).execute()

    logger.info(
        "POST /batch/backfill-thumbnails — starting (ed_fallback=%s limit=%s)", ed_fallback, limit,
    )

    # Paginate around supabase-py's 1000-row default — corpus is ~46K rows.
    rows: list[dict[str, Any]] = []
    PAGE = 1000
    page = 0
    while True:
        result = (
            sb.table("video_corpus")
            .select("video_id, thumbnail_url")
            .range(page * PAGE, (page + 1) * PAGE - 1)
            .execute()
        )
        batch = result.data or []
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        page += 1

    thumb_exists_cache: dict[str, bool] = {}

    def _row_needs_thumbnail_backfill(row: dict[str, Any]) -> bool:
        url = (row.get("thumbnail_url") or "").strip()
        if not url:
            return True
        if not url.startswith(r2_prefix):
            return True
        vid = str(row["video_id"])
        if vid not in thumb_exists_cache:
            thumb_exists_cache[vid] = r2_public_thumbnail_exists(vid)
        return not thumb_exists_cache[vid]

    to_backfill = [r for r in rows if _row_needs_thumbnail_backfill(r)]
    if limit is not None:
        to_backfill = to_backfill[:limit]

    logger.info(
        "[backfill-thumbnails] %d/%d rows need backfill (capped=%s)",
        len(to_backfill), len(rows), limit,
    )

    loop = asyncio.get_event_loop()

    async def _mirror_cdn(row: dict[str, Any]) -> str | None:
        cdn_url = row.get("thumbnail_url")
        if not cdn_url or not str(cdn_url).strip():
            return None
        # Do not treat a stale R2 URL as a TikTok CDN source.
        if str(cdn_url).startswith(r2_prefix):
            return None
        try:
            return await download_and_upload_thumbnail(str(cdn_url), str(row["video_id"]))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[backfill-thumbnails] CDN mirror error for %s: %s", row["video_id"], exc,
            )
            return None

    from_frame = from_cdn = from_ed = nulled = failed = 0
    ed_missing_post = ed_no_cover = ed_upload_failed = 0
    CHUNK = 10
    for i in range(0, len(to_backfill), CHUNK):
        chunk = to_backfill[i: i + CHUNK]
        frame_results = await asyncio.gather(
            *[
                loop.run_in_executor(None, copy_first_frame_to_thumbnail, str(r["video_id"]))
                for r in chunk
            ],
            return_exceptions=True,
        )

        need_cdn: list[dict[str, Any]] = []
        for row, fr in zip(chunk, frame_results):
            vid = str(row["video_id"])
            if isinstance(fr, Exception):
                logger.warning("[backfill-thumbnails] frame copy task error for %s: %s", vid, fr)
                need_cdn.append(row)
                continue
            if fr:
                try:
                    _set_thumb(vid, fr)
                    from_frame += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[backfill-thumbnails] DB patch failed (frame) for %s: %s", vid, exc,
                    )
                    failed += 1
            else:
                need_cdn.append(row)

        if not need_cdn:
            continue

        cdn_urls = await asyncio.gather(
            *[_mirror_cdn(r) for r in need_cdn], return_exceptions=True,
        )
        need_ed: list[dict[str, Any]] = []
        for row, cu in zip(need_cdn, cdn_urls):
            vid = str(row["video_id"])
            if isinstance(cu, Exception):
                logger.warning("[backfill-thumbnails] cdn path error for %s: %s", vid, cu)
                need_ed.append(row)
                continue
            if cu:
                try:
                    _set_thumb(vid, cu)
                    from_cdn += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[backfill-thumbnails] DB patch failed (cdn) for %s: %s", vid, exc,
                    )
                    failed += 1
            else:
                need_ed.append(row)

        if not need_ed:
            continue

        if not ed_fallback:
            for row in need_ed:
                vid = str(row["video_id"])
                try:
                    _set_thumb(vid, None)
                    nulled += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[backfill-thumbnails] DB patch failed (null) for %s: %s", vid, exc,
                    )
                    failed += 1
            continue

        vids = [str(r["video_id"]) for r in need_ed]
        try:
            fresh_posts = await ensemble.fetch_post_multi_info(vids)
        except Exception as exc:  # noqa: BLE001
            logger.error("[backfill-thumbnails] ED multi_info failed for batch: %s", exc)
            for row in need_ed:
                try:
                    _set_thumb(str(row["video_id"]), None)
                    nulled += 1
                except Exception as dbe:  # noqa: BLE001
                    logger.warning(
                        "[backfill-thumbnails] DB null after ED fail for %s: %s", row["video_id"], dbe,
                    )
                    failed += 1
            continue

        fresh_by_id: dict[str, dict[str, Any]] = {}
        for post in fresh_posts or []:
            if not isinstance(post, dict):
                continue
            detail = post.get("aweme_detail") or post
            if isinstance(detail, dict):
                aid = str(detail.get("aweme_id") or "")
                if aid:
                    fresh_by_id[aid] = post

        for row in need_ed:
            vid = str(row["video_id"])
            post = fresh_by_id.get(vid)
            if not post:
                ed_missing_post += 1
                try:
                    _set_thumb(vid, None)
                    nulled += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[backfill-thumbnails] DB patch failed (null) for %s: %s", vid, exc,
                    )
                    failed += 1
                continue
            cover = _cover_url_from_ensemble_post(post)
            if not cover:
                ed_no_cover += 1
                try:
                    _set_thumb(vid, None)
                    nulled += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[backfill-thumbnails] DB patch failed (null) for %s: %s", vid, exc,
                    )
                    failed += 1
                continue
            try:
                uploaded = await download_and_upload_thumbnail(cover, vid)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[backfill-thumbnails] ED cover upload error for %s: %s", vid, exc)
                uploaded = None
            if uploaded:
                try:
                    _set_thumb(vid, uploaded)
                    from_ed += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[backfill-thumbnails] DB patch failed (ed) for %s: %s", vid, exc,
                    )
                    failed += 1
            else:
                ed_upload_failed += 1
                try:
                    _set_thumb(vid, None)
                    nulled += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[backfill-thumbnails] DB patch failed (null) for %s: %s", vid, exc,
                    )
                    failed += 1

    logger.info(
        "[backfill-thumbnails] done — from_frame=%d from_cdn=%d from_ed=%d "
        "nulled=%d failed=%d ed_missing_post=%d ed_no_cover=%d ed_upload_failed=%d total=%d",
        from_frame, from_cdn, from_ed, nulled, failed,
        ed_missing_post, ed_no_cover, ed_upload_failed, len(to_backfill),
    )
    return JSONResponse({
        "ok": True,
        "from_frame": from_frame,
        "from_cdn": from_cdn,
        "from_ed": from_ed,
        "nulled": nulled,
        "failed": failed,
        "ed_missing_post": ed_missing_post,
        "ed_no_cover": ed_no_cover,
        "ed_upload_failed": ed_upload_failed,
        "total": len(to_backfill),
        "ed_fallback": ed_fallback,
        "limit": limit,
    })


@router.post("/batch/analytics")
async def batch_analytics(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Trigger weekly analytics: creator velocity + breakout multiplier + signal grading.

    Protected by require_batch_caller. Normally called by Cloud Scheduler on Sundays.
    """
    from getviews_pipeline.batch_analytics import run_analytics
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.corpus_context import _anon_client
    from getviews_pipeline.hook_effectiveness_compute import run_hook_effectiveness
    from getviews_pipeline.pattern_fingerprint import recompute_weekly_counts
    from getviews_pipeline.runtime import run_sync
    from getviews_pipeline.signal_classifier import run_signal_grading
    from getviews_pipeline.supabase_client import get_service_client

    logger.info("POST /batch/analytics triggered")
    client = get_service_client()

    async with record_job_run(client, "batch/analytics") as obs_summary:
        try:
            analytics = await run_analytics()
            signal = await run_signal_grading()
            patterns_touched = 0
            try:
                patterns_touched = await recompute_weekly_counts(_anon_client())
            except Exception as exc:
                logger.warning("pattern weekly recompute failed: %s", exc)

            # Pass 4 (2026-05-09): populate ``hook_effectiveness`` aggregate
            # table. Before this ran, the table was empty in production and
            # Pattern + Ideas reports rendered with zero hook findings. See
            # ``artifacts/docs/state-of-corpus.md`` Appendix B Gap 1.
            hook_eff: dict[str, Any] = {"upserted": 0, "current_buckets": 0, "prior_buckets": 0}
            try:
                hook_eff = await run_sync(run_hook_effectiveness)
            except Exception as exc:
                logger.warning("hook_effectiveness recompute failed: %s", exc)
        except Exception as exc:
            logger.exception("Batch analytics failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        # Piggyback idempotency janitor — clean stale rows while we have the cron window
        try:
            from getviews_pipeline.answer_session import clean_expired_idempotency_rows
            clean_expired_idempotency_rows(client)
        except Exception as exc:
            logger.warning("[batch/analytics] idempotency janitor failed (non-fatal): %s", exc)

        obs_summary.update({
            "analytics": {
                "creators_updated": analytics.creators_updated,
                "videos_updated": analytics.videos_updated,
                "errors": analytics.errors,
            },
            "signal": {
                "grades_written": signal.grades_written,
                "niches_processed": signal.niches_processed,
                "errors": signal.errors,
            },
            "patterns": {"rows_updated": patterns_touched},
            "hook_effectiveness": hook_eff,
        })

    return JSONResponse({
        "ok": True,
        "analytics": {
            "creators_updated": analytics.creators_updated,
            "videos_updated": analytics.videos_updated,
            "errors": analytics.errors,
        },
        "signal": {
            "grades_written": signal.grades_written,
            "niches_processed": signal.niches_processed,
            "errors": signal.errors,
        },
        "patterns": {"rows_updated": patterns_touched},
        "hook_effectiveness": hook_eff,
    })


@router.post("/batch/layer0")
async def batch_layer0(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Trigger Layer 0 intelligence extraction independently of corpus ingest.

    Protected by require_batch_caller. Safe to re-run — upserts on conflict.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.layer0_niche import run_niche_insights
    from getviews_pipeline.layer0_sound import run_sound_insights
    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    logger.info("POST /batch/layer0 triggered")

    result: dict = {"ok": True}

    async with record_job_run(client, "batch/layer0") as obs_summary:
        try:
            l0a = await run_niche_insights(client)
            result["layer0a_niche"] = {
                "insights_written": l0a.insights_written,
                "niches_skipped": l0a.niches_skipped,
                "errors": l0a.errors,
            }
            logger.info(
                "[layer0a] insights=%d skipped=%d",
                l0a.insights_written, l0a.niches_skipped,
            )
        except Exception as exc:
            logger.exception("[layer0a] failed: %s", exc)
            result["layer0a_niche"] = {"error": str(exc)}

        try:
            l0b = await run_sound_insights(client)
            result["layer0b_sound"] = {"analyzed": l0b.get("analyzed", 0)}
        except Exception as exc:
            logger.exception("[layer0b] failed: %s", exc)
            result["layer0b_sound"] = {"error": str(exc)}

        # ``batch/layer0`` swallows per-layer exceptions so the endpoint
        # always returns 200. That means ``record_job_run`` would always
        # mark the run as ``ok`` — which hides partial failures. Surface
        # them in the summary so ``any(status='ok' and summary has
        # '.*error')`` queries can flag half-working runs.
        obs_summary.update({k: v for k, v in result.items() if k != "ok"})

    return JSONResponse(result)


@router.post("/batch/morning-ritual")
async def batch_morning_ritual(
    request: Request,
    body: RitualBatchRequest = RitualBatchRequest(),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Nightly batch: generate 3 scripts per (creator, followed niche).

    Protected by require_batch_caller. Production schedule (see ``deploy.sh``):
    ``0 22 * * *`` in ``Asia/Ho_Chi_Minh`` (22:00 VN) so rows are warm before
    the next morning. Supabase pg_cron may use a different UTC slot — keep in sync.
    """
    from getviews_pipeline.morning_ritual import run_morning_ritual_batch
    from getviews_pipeline.supabase_client import get_service_client

    try:
        summary = await run_sync(run_morning_ritual_batch, get_service_client(), body.user_ids)
    except Exception as exc:
        logger.exception("[batch/morning-ritual] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({
        "ok": True,
        "generated":              summary.generated,
        "skipped_thin":           summary.skipped_thin,
        "failed_schema":          summary.failed_schema,
        "failed_gemini":          summary.failed_gemini,
        "failed_duplicate_hooks": summary.failed_duplicate_hooks,
        "failed_upsert":          summary.failed_upsert,
        "users_no_niche":         summary.users_no_niche,
    })


@router.post("/batch/pattern-decks")
async def batch_pattern_decks(
    request: Request,
    body: PatternDecksBatchRequest = PatternDecksBatchRequest(),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Nightly cron: synthesize PatternModal deck content for stale
    ``video_patterns`` rows.

    The deck = ``structure`` (4 timing-bucketed lines), ``why``
    (audience psychology), ``careful`` (pitfall warning), ``angles``
    (filled vs gap content angles). Drives the FE PatternModal on
    /app/trends. Walks active patterns whose ``deck_computed_at`` is
    null OR older than 7 days, ordered staleest-first; per-batch cap
    keeps the Gemini bill predictable.

    Protected by ``require_batch_caller``. Pair with the pg_cron
    schedule in ``20260530000001_pg_cron_pattern_decks.sql``.
    """
    from getviews_pipeline.pattern_deck_synth import (
        DEFAULT_BATCH_CAP,
        run_pattern_decks_batch,
    )
    from getviews_pipeline.supabase_client import get_service_client

    cap = body.cap or DEFAULT_BATCH_CAP

    try:
        summary = await run_sync(
            run_pattern_decks_batch,
            get_service_client(),
            cap=cap,
            pattern_ids=body.pattern_ids,
        )
    except Exception as exc:
        logger.exception("[batch/pattern-decks] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({
        "ok":            True,
        "considered":    summary.considered,
        "generated":     summary.generated,
        "skipped_thin":  summary.skipped_thin,
        "skipped_fresh": summary.skipped_fresh,
        "failed_schema": summary.failed_schema,
        "failed_gemini": summary.failed_gemini,
        "failed_upsert": summary.failed_upsert,
    })


class DouyinSynthBatchRequest(StrictBody):
    """D3b (2026-06-04) — body for ``POST /batch/douyin-synth``.

    Mirrors ``PatternDecksBatchRequest``: optional cap + optional
    explicit ``video_ids`` list to bypass the staleness query (admin
    manual reruns after a synth-prompt bump).
    """

    cap: int | None = Field(
        default=None,
        ge=1, le=500,
        description=(
            "Max ``douyin_video_corpus`` rows to grade this run. Omit to use "
            "``DEFAULT_BATCH_CAP`` (100). Lower this for mid-day smoke tests."
        ),
    )
    video_ids: list[str] | None = Field(
        default=None,
        description=(
            "Restrict the run to specific Douyin aweme_ids. Bypasses the "
            "synth_computed_at staleness query — admin manual reruns only."
        ),
    )


@router.post("/batch/douyin-synth")
async def batch_douyin_synth(
    request: Request,
    body: DouyinSynthBatchRequest = DouyinSynthBatchRequest(),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """D3b daily cron: grade ``douyin_video_corpus`` rows for adapt-level
    + ETA + translator notes.

    Walks rows whose ``synth_computed_at`` is null OR older than 7 days,
    ordered staleest-first; per-batch cap keeps the Gemini bill bounded
    (~$0.005/row × 100 = ~$0.50/day worst case).

    Protected by ``require_batch_caller``. Pair with the pg_cron
    schedule in ``20260604000000_pg_cron_douyin_synth.sql``.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.douyin_adapt_batch import (
        DEFAULT_BATCH_CAP,
        run_douyin_adapt_batch,
    )
    from getviews_pipeline.supabase_client import get_service_client

    cap = body.cap or DEFAULT_BATCH_CAP
    sb = get_service_client()
    logger.info(
        "POST /batch/douyin-synth triggered — cap=%d explicit_ids=%s",
        cap, len(body.video_ids) if body.video_ids else None,
    )
    async with record_job_run(sb, "batch/douyin-synth") as obs_summary:
        obs_summary["cap"] = cap
        obs_summary["explicit_ids"] = (
            len(body.video_ids) if body.video_ids else 0
        )
        try:
            summary = await run_sync(
                run_douyin_adapt_batch,
                sb,
                cap=cap,
                video_ids=body.video_ids,
            )
        except Exception as exc:
            logger.exception("[batch/douyin-synth] failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        obs_summary.update({
            "considered": summary.considered,
            "generated": summary.generated,
            "failed_synth": summary.failed_synth,
            "failed_upsert": summary.failed_upsert,
            "skipped_no_title": summary.skipped_no_title,
        })

    return JSONResponse({
        "ok": True,
        "considered": summary.considered,
        "generated": summary.generated,
        "failed_synth": summary.failed_synth,
        "failed_upsert": summary.failed_upsert,
        "skipped_no_title": summary.skipped_no_title,
    })


@router.post("/batch/scene-intelligence")
async def batch_scene_intelligence(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Nightly cron: rebuild ``scene_intelligence`` from ``video_corpus`` scenes.

    Protected by require_batch_caller. Requires ``SUPABASE_SERVICE_ROLE_KEY``.
    """
    from getviews_pipeline.scene_intelligence_refresh import refresh_scene_intelligence_sync
    from getviews_pipeline.supabase_client import get_service_client

    try:
        stats = await run_sync(refresh_scene_intelligence_sync, get_service_client())
    except Exception as exc:
        logger.exception("[batch/scene-intelligence] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({"ok": True, **stats})


class DouyinPatternsBatchRequest(StrictBody):
    """D5c (2026-06-05) — body for ``POST /batch/douyin-patterns``.

    Mirrors ``DouyinSynthBatchRequest``: optional ``niche_ids``
    restriction + optional ``force`` flag to bypass the
    ``SYNTH_FRESH_FOR`` short-circuit on admin reruns.
    """

    niche_ids: list[int] | None = Field(
        default=None,
        description=(
            "Restrict the run to specific Douyin niche IDs. Omit to "
            "synthesise patterns for all active niches."
        ),
    )
    pool_size: int | None = Field(
        default=None,
        ge=6, le=100,
        description=(
            "Per-niche corpus pool size sent to the synthesiser. Omit "
            "to use ``DEFAULT_POOL_PER_NICHE`` (30). Lower for smoke "
            "tests, higher for one-off deeper-cluster experiments."
        ),
    )
    force: bool = Field(
        default=False,
        description=(
            "Re-compute every niche even if a row exists for this "
            "(niche_id, week_of) and is within the freshness window. "
            "Cron uses force=False; admin manual reruns use True."
        ),
    )


@router.post("/batch/douyin-patterns")
async def batch_douyin_patterns(
    request: Request,
    body: DouyinPatternsBatchRequest = DouyinPatternsBatchRequest(),
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """D5c weekly cron: synthesize 3 pattern signals per active niche.

    Walks all active ``douyin_niche_taxonomy`` rows, queries each
    niche's last-7d corpus from ``douyin_video_corpus``, calls D5b
    ``synth_douyin_patterns``, and UPSERTs the 3 ranked rows into
    ``douyin_patterns`` keyed on (niche_id, week_of, rank).

    Idempotent: a re-run on the same Monday with ``force=False`` is a
    no-op for niches whose existing row is < 6 days old.

    Protected by ``require_batch_caller``. Pair with the pg_cron
    schedule in ``20260605000001_pg_cron_douyin_patterns.sql``.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.douyin_patterns_batch import (
        DEFAULT_POOL_PER_NICHE,
        run_douyin_patterns_batch,
    )
    from getviews_pipeline.supabase_client import get_service_client

    pool_size = body.pool_size or DEFAULT_POOL_PER_NICHE
    sb = get_service_client()
    logger.info(
        "POST /batch/douyin-patterns triggered — niche_ids=%s pool_size=%d force=%s",
        body.niche_ids, pool_size, body.force,
    )
    async with record_job_run(sb, "batch/douyin-patterns") as obs_summary:
        obs_summary["pool_size"] = pool_size
        obs_summary["force"] = body.force
        obs_summary["niche_ids"] = (
            len(body.niche_ids) if body.niche_ids else 0
        )
        try:
            summary = await run_sync(
                run_douyin_patterns_batch,
                sb,
                niche_ids=body.niche_ids,
                pool_size=pool_size,
                force=body.force,
            )
        except Exception as exc:
            logger.exception("[batch/douyin-patterns] failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        obs_summary.update({
            "considered_niches": summary.considered_niches,
            "written_rows": summary.written_rows,
            "skipped_fresh": summary.skipped_fresh,
            "skipped_thin_pool": summary.skipped_thin_pool,
            "failed_synth": summary.failed_synth,
            "failed_upsert": summary.failed_upsert,
            "week_of": summary.week_of,
        })

    return JSONResponse({
        "ok": True,
        "week_of": summary.week_of,
        "considered_niches": summary.considered_niches,
        "written_rows": summary.written_rows,
        "skipped_fresh": summary.skipped_fresh,
        "skipped_thin_pool": summary.skipped_thin_pool,
        "failed_synth": summary.failed_synth,
        "failed_upsert": summary.failed_upsert,
    })


@router.post("/batch/marketing-corpus-pick")
async def batch_marketing_corpus_pick(
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Marketing API — pick random corpus video (>100k views), run deep/win diagnosis.

    Proxied from Supabase Edge ``marketing-corpus-pick`` (service_role JWT).
    Records pick only after ``narrative_vi`` is present. Typical latency 20–40s.
    """
    from getviews_pipeline.marketing_corpus_pick import (
        ANALYSIS_FAILED,
        POOL_EXHAUSTED,
        run_marketing_corpus_pick,
    )

    logger.info("POST /batch/marketing-corpus-pick triggered")
    try:
        payload = await run_sync(run_marketing_corpus_pick)
    except RuntimeError as exc:
        code = str(exc)
        if code == POOL_EXHAUSTED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": POOL_EXHAUSTED},
            ) from exc
        if code == ANALYSIS_FAILED:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error": ANALYSIS_FAILED},
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[batch/marketing-corpus-pick] failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({"ok": True, **payload})
