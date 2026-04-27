"""Batch corpus ingest, analytics, and maintenance routes."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from getviews_pipeline.deps import require_batch_caller
from getviews_pipeline.runtime import run_sync

logger = logging.getLogger(__name__)

router = APIRouter()


class BatchIngestRequest(BaseModel):
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


class BatchReingestVideosRequest(BaseModel):
    items: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description='Each item: {"video_id": "<aweme_id>", "niche_id": <int>} (aweme_id alias allowed).',
    )
    refresh_mv: bool = Field(default=True, description="Refresh niche_intelligence after upserts.")


class RitualBatchRequest(BaseModel):
    user_ids: list[str] | None = Field(
        default=None,
        description="Restrict to specific user ids. Omit for all users.",
    )


class PatternDecksBatchRequest(BaseModel):
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
        "POST /batch/ingest triggered — niche_ids=%s deep_pool=%s",
        body.niche_ids,
        body.deep_pool,
    )
    async with record_job_run(get_service_client(), "batch/ingest") as obs_summary:
        obs_summary["niche_ids"] = body.niche_ids
        obs_summary["deep_pool"] = body.deep_pool
        try:
            summary = await run_batch_ingest(niche_ids=body.niche_ids, deep_pool=body.deep_pool)
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
        })

    return JSONResponse({
        "ok": True,
        "total_inserted": summary.total_inserted,
        "total_skipped": summary.total_skipped,
        "total_failed": summary.total_failed,
        "niches_processed": summary.niches_processed,
        "materialized_view_refreshed": summary.materialized_view_refreshed,
        "niche_results": summary.niche_results,
    })


class BatchDouyinIngestRequest(BaseModel):
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


@router.post("/batch/reclassify-format")
async def batch_reclassify_format(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """One-shot: re-run classify_format on rows stuck in ``other``/NULL.

    Axis 2 catch-up (state-of-corpus.md). Zero Gemini cost — pure regex
    pass on cached analysis_json. Safe to re-run; idempotent.
    Protected by require_batch_caller.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.content_format_reclassify import (
        run_content_format_reclassify,
    )
    from getviews_pipeline.runtime import run_sync
    from getviews_pipeline.supabase_client import get_service_client

    logger.info("POST /batch/reclassify-format triggered")
    client = get_service_client()

    async with record_job_run(client, "batch/reclassify-format") as obs_summary:
        try:
            result = await run_sync(run_content_format_reclassify, client=client)
        except Exception as exc:
            logger.exception("Batch reclassify-format failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        obs_summary.update(result)

    return JSONResponse({"ok": True, **result})


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


@router.post("/batch/backfill-thumbnails")
async def batch_backfill_thumbnails(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """One-time backfill: copy TikTok CDN thumbnail URLs → permanent R2 URLs.

    Protected by require_batch_caller. Safe to re-run — skips rows already on R2.
    """
    from getviews_pipeline.r2 import download_and_upload_thumbnail, r2_configured
    from getviews_pipeline.config import R2_PUBLIC_URL
    from getviews_pipeline.supabase_client import get_service_client

    if not r2_configured():
        raise HTTPException(status_code=500, detail="R2 not configured")

    sb = get_service_client()
    logger.info("POST /batch/backfill-thumbnails — starting")

    r2_prefix = R2_PUBLIC_URL.rstrip("/") if R2_PUBLIC_URL else "NONE"
    result = sb.table("video_corpus").select("video_id, thumbnail_url").execute()
    rows = result.data or []
    to_backfill = [
        r for r in rows
        if r.get("thumbnail_url") and not r["thumbnail_url"].startswith(r2_prefix)
    ]
    logger.info("[backfill-thumbnails] %d/%d rows need backfill", len(to_backfill), len(rows))

    updated = failed = skipped = 0
    CHUNK = 10
    for i in range(0, len(to_backfill), CHUNK):
        chunk = to_backfill[i:i + CHUNK]
        tasks = [download_and_upload_thumbnail(r["thumbnail_url"], r["video_id"]) for r in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for row, res in zip(chunk, results):
            if isinstance(res, Exception):
                logger.warning("[backfill-thumbnails] error for %s: %s", row["video_id"], res)
                failed += 1
            elif isinstance(res, str) and res:
                try:
                    sb.table("video_corpus").update({"thumbnail_url": res}).eq("video_id", row["video_id"]).execute()
                    updated += 1
                except Exception as exc:
                    logger.warning("[backfill-thumbnails] DB patch failed for %s: %s", row["video_id"], exc)
                    failed += 1
            else:
                skipped += 1

    logger.info("[backfill-thumbnails] done — updated=%d failed=%d skipped=%d", updated, failed, skipped)
    return JSONResponse({"ok": True, "updated": updated, "failed": failed, "skipped": skipped, "total": len(to_backfill)})


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
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.layer0_niche import run_niche_insights
    from getviews_pipeline.layer0_sound import run_sound_insights
    from getviews_pipeline.layer0_migration import run_cross_niche_migration

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

        try:
            l0c = await run_cross_niche_migration(client)
            result["layer0c_migration"] = {"migrations_found": l0c.get("migrations_found", 0)}
        except Exception as exc:
            logger.exception("[layer0c] failed: %s", exc)
            result["layer0c_migration"] = {"error": str(exc)}

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
    """Nightly cron: generate 3 scripts for every creator with a niche set.

    Protected by require_batch_caller. Called by Cloud Scheduler at ~07:00 Asia/
    Ho_Chi_Minh so the ritual is ready when the creator opens the app.
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
        DEFAULT_BATCH_CAP, run_pattern_decks_batch,
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
