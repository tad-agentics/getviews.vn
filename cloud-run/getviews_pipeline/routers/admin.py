"""Admin dashboard backend routes (/admin/*)."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.parse as _urlparse
import urllib.request as _urlrequest
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from getviews_pipeline.config import ENSEMBLEDATA_API_TOKEN
from getviews_pipeline.deps import require_admin, require_batch_caller
from getviews_pipeline.runtime import run_sync

logger = logging.getLogger(__name__)

router = APIRouter()

# ── EnsembleData usage caches ─────────────────────────────────────────────────

_ENSEMBLE_USAGE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_ENSEMBLE_USAGE_TTL_SEC = 300.0

_ENSEMBLE_HISTORY_CACHE: dict[int, tuple[float, dict[str, Any]]] = {}
_ENSEMBLE_HISTORY_TTL_SEC = 300.0

_ENSEMBLE_MONTHLY_BUDGET = int(os.environ.get("ED_MONTHLY_UNIT_BUDGET", "0"))

# ── Slack admin webhook ───────────────────────────────────────────────────────

_SLACK_ADMIN_WEBHOOK_URL = os.environ.get("SLACK_ADMIN_WEBHOOK_URL", "").strip()

# ── Cloud Logging feature flag ────────────────────────────────────────────────

_ADMIN_LOGS_ENABLED = os.environ.get("ADMIN_LOGS_ENABLED", "").lower() in ("1", "true", "yes")
_GCP_PROJECT_ID_FOR_LOGS = os.environ.get("GCP_PROJECT_ID", "").strip()
_CLOUD_RUN_SERVICE_NAME = os.environ.get("K_SERVICE", "").strip()


# ── EnsembleData helper functions ─────────────────────────────────────────────

def _ensemble_fetch_used_units(date_iso: str) -> dict[str, Any]:
    if not ENSEMBLEDATA_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ensemble_token_unset")
    now = time.monotonic()
    cached = _ENSEMBLE_USAGE_CACHE.get(date_iso)
    if cached and now - cached[0] < _ENSEMBLE_USAGE_TTL_SEC:
        return cached[1]
    qs = _urlparse.urlencode({"date": date_iso, "token": ENSEMBLEDATA_API_TOKEN})
    url = f"https://ensembledata.com/apis/customer/get-used-units?{qs}"
    req = _urlrequest.Request(url, headers={"User-Agent": "getviews-admin/1.0"})
    try:
        with _urlrequest.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"ensemble_fetch_failed: {exc}") from exc
    _ENSEMBLE_USAGE_CACHE[date_iso] = (now, payload)
    return payload


def _ensemble_fetch_history(days: int) -> dict[str, Any]:
    if not ENSEMBLEDATA_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ensemble_token_unset")
    now = time.monotonic()
    cached = _ENSEMBLE_HISTORY_CACHE.get(days)
    if cached and now - cached[0] < _ENSEMBLE_HISTORY_TTL_SEC:
        return cached[1]
    qs = _urlparse.urlencode({"days": days, "token": ENSEMBLEDATA_API_TOKEN})
    url = f"https://ensembledata.com/apis/customer/get-history?{qs}"
    req = _urlrequest.Request(url, headers={"User-Agent": "getviews-admin/1.0"})
    try:
        with _urlrequest.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"ensemble_fetch_failed: {exc}") from exc
    _ENSEMBLE_HISTORY_CACHE[days] = (now, payload)
    return payload


# ── Alert evaluators ──────────────────────────────────────────────────────────

def _post_slack_admin_alert(message: str, severity: str) -> None:
    if not _SLACK_ADMIN_WEBHOOK_URL:
        return
    icon = {"info": "ℹ️", "warn": "⚠️", "crit": "🚨"}.get(severity, "⚠️")

    def _do() -> None:
        try:
            body = json.dumps({"text": f"{icon} *[GetViews admin]* {message}", "username": "getviews-admin"}).encode("utf-8")
            req = _urlrequest.Request(_SLACK_ADMIN_WEBHOOK_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with _urlrequest.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as exc:
            logger.warning("[alerts] slack webhook post failed: %s", exc)

    threading.Thread(target=_do, daemon=True, name="slack-admin-alert").start()


def _last_alert_phase(rule_key: str) -> str | None:
    from getviews_pipeline.supabase_client import get_service_client

    try:
        resp = (
            get_service_client()
            .table("admin_alert_fires")
            .select("phase")
            .eq("rule_key", rule_key)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0]["phase"] if rows else None
    except Exception as exc:
        logger.warning("[alerts] _last_alert_phase(%s) failed: %s", rule_key, exc)
        return None


def _record_alert_fire(*, rule_key: str, severity: str, message: str, context: dict, phase: str, delivered: bool) -> None:
    from getviews_pipeline.supabase_client import get_service_client

    try:
        get_service_client().table("admin_alert_fires").insert({
            "rule_key": rule_key, "severity": severity, "message": message,
            "context_json": context, "phase": phase,
            "delivered_at": datetime.now(timezone.utc).isoformat() if delivered else None,
        }).execute()
    except Exception as exc:
        logger.exception("[alerts] _record_alert_fire(%s) failed: %s", rule_key, exc)


def _evaluate_ensemble_runway_low(rule: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    runway_days_max = int(rule.get("threshold_json", {}).get("runway_days_max", 7))
    if _ENSEMBLE_MONTHLY_BUDGET <= 0:
        return (False, "ED_MONTHLY_UNIT_BUDGET unset — rule skipped", {"reason": "no_budget"})
    now = datetime.now(timezone.utc)
    total_used = last7_sum = last7_days = 0
    for i in range(30):
        day = (now - timedelta(days=i)).date().isoformat()
        try:
            payload = _ensemble_fetch_used_units(day)
            units_raw = payload.get("units")
            if units_raw is None and isinstance(payload.get("data"), dict):
                units_raw = payload["data"].get("units")
            units = int(units_raw or 0)
        except Exception:
            continue
        total_used += units
        if i < 7:
            last7_sum += units
            last7_days += 1
    if last7_days == 0:
        return (False, "no ED data — rule skipped", {"reason": "no_data"})
    avg_daily = last7_sum / last7_days
    remaining = max(0, _ENSEMBLE_MONTHLY_BUDGET - total_used)
    runway = int(remaining / avg_daily) if avg_daily > 0 else 999
    context = {
        "runway_days": runway, "runway_days_max": runway_days_max,
        "monthly_budget": _ENSEMBLE_MONTHLY_BUDGET, "total_used_30d": total_used,
        "avg_daily_7d": round(avg_daily, 1),
    }
    breached = runway < runway_days_max
    msg = (
        f"EnsembleData runway {runway}d (< {runway_days_max}d threshold) · "
        f"used {total_used:,}/{_ENSEMBLE_MONTHLY_BUDGET:,} units · avg {avg_daily:,.0f}/day"
        if breached else f"runway {runway}d — ok"
    )
    return (breached, msg, context)


def _evaluate_corpus_stale(rule: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    hours = int(rule.get("threshold_json", {}).get("hours_since_last_ingest", 48))
    from getviews_pipeline.supabase_client import get_service_client

    try:
        resp = get_service_client().table("video_corpus").select("created_at").order("created_at", desc=True).limit(1).execute()
        rows = resp.data or []
    except Exception as exc:
        return (False, f"query failed: {exc}", {"reason": "query_error"})
    if not rows:
        return (True, "video_corpus empty", {"reason": "empty"})
    last_iso = rows[0].get("created_at")
    if not last_iso:
        return (True, "created_at null on latest row", {"reason": "null_ts"})
    try:
        last = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
    except ValueError:
        return (False, "created_at parse failed", {"reason": "parse_error"})
    age_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    context = {"hours_since_last_ingest": round(age_h, 1), "threshold_hours": hours}
    breached = age_h >= hours
    msg = (
        f"Corpus stale · {age_h:.1f}h since last ingest (≥ {hours}h)"
        if breached else f"corpus fresh · {age_h:.1f}h old"
    )
    return (breached, msg, context)


def _evaluate_trigger_error_spike(rule: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    window = int(rule.get("threshold_json", {}).get("window_runs", 10))
    error_pct_max = float(rule.get("threshold_json", {}).get("error_pct_max", 50))
    from getviews_pipeline.supabase_client import get_service_client

    try:
        resp = (
            get_service_client()
            .table("admin_action_log")
            .select("result_status")
            .in_("result_status", ["ok", "error"])
            .order("created_at", desc=True)
            .limit(window)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:
        return (False, f"query failed: {exc}", {"reason": "query_error"})
    if len(rows) < 3:
        return (False, "not enough samples yet", {"n": len(rows)})
    errors = sum(1 for r in rows if r.get("result_status") == "error")
    pct = (errors / len(rows)) * 100
    context = {"window_runs": len(rows), "errors": errors, "error_pct": round(pct, 1), "error_pct_max": error_pct_max}
    breached = pct > error_pct_max
    msg = (
        f"Trigger error rate {pct:.0f}% ({errors}/{len(rows)}) · threshold {error_pct_max:.0f}%"
        if breached else f"trigger errors {pct:.0f}% — ok"
    )
    return (breached, msg, context)


def _evaluate_cron_batch_failures(rule: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Fire on any ``batch_job_runs.status='failed'`` in the window.

    We write failures on every /batch/* cron via record_job_run; without
    this rule, nothing reads them. One failure in 7 days should page —
    silent pipeline breakage is exactly what this table exists to
    surface.
    """
    window_days = int(rule.get("threshold_json", {}).get("window_days", 7))
    failures_max = int(rule.get("threshold_json", {}).get("failures_max", 0))
    from getviews_pipeline.supabase_client import get_service_client

    since_iso = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    try:
        resp = (
            get_service_client()
            .table("batch_job_runs")
            .select("job_name, error, started_at")
            .eq("status", "failed")
            .gte("started_at", since_iso)
            .order("started_at", desc=True)
            .limit(25)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:
        return (False, f"query failed: {exc}", {"reason": "query_error"})

    by_job: dict[str, int] = {}
    for row in rows:
        jn = row.get("job_name") or "unknown"
        by_job[jn] = by_job.get(jn, 0) + 1

    n = len(rows)
    breached = n > failures_max
    context = {
        "failures": n,
        "failures_max": failures_max,
        "window_days": window_days,
        "by_job": by_job,
        "latest_error": (rows[0].get("error") or "")[:200] if rows else None,
    }
    if breached:
        jobs_summary = ", ".join(f"{k}×{v}" for k, v in sorted(by_job.items()))
        msg = f"Pipeline có {n} cron fail trong {window_days}d · {jobs_summary}"
    else:
        msg = f"pipeline healthy · {n} failures trong {window_days}d"
    return (breached, msg, context)


_EVALUATORS: dict[str, Any] = {
    "ensemble_runway_low": _evaluate_ensemble_runway_low,
    "corpus_stale": _evaluate_corpus_stale,
    "admin_trigger_error_spike": _evaluate_trigger_error_spike,
    "cron_batch_failures": _evaluate_cron_batch_failures,
}


# ── Admin action log helpers ──────────────────────────────────────────────────

def _insert_admin_job_row(*, user_id: str, action: str, params: dict[str, Any]) -> str | None:
    try:
        from getviews_pipeline.supabase_client import get_service_client

        resp = (
            get_service_client()
            .table("admin_action_log")
            .insert({"user_id": user_id, "action": action, "params_json": params or {}, "result_status": "queued"})
            .execute()
        )
        rows = resp.data or []
        return rows[0].get("id") if rows else None
    except Exception as exc:
        logger.warning("[admin_action_log] insert queued-row failed: %s", exc)
        return None


def _update_admin_job_row(
    *, job_id: str, result_status: str,
    error_message: str | None = None,
    duration_ms: int | None = None,
    result_json: dict[str, Any] | None = None,
) -> None:
    def _do() -> None:
        try:
            from getviews_pipeline.supabase_client import get_service_client

            payload: dict[str, Any] = {"result_status": result_status}
            if error_message is not None:
                payload["error_message"] = error_message[:500]
            if duration_ms is not None:
                payload["duration_ms"] = duration_ms
            if result_json is not None:
                payload["result_json"] = result_json
            get_service_client().table("admin_action_log").update(payload).eq("id", job_id).execute()
        except Exception as exc:
            logger.warning("[admin_action_log] update row %s failed: %s", job_id, exc)

    threading.Thread(target=_do, daemon=True, name=f"admin-audit-{job_id[:8]}").start()


def _record_admin_action(
    *, user_id: str, action: str, params: dict[str, Any] | None,
    result_status: str, error_message: str | None = None, duration_ms: int | None = None,
) -> None:
    def _do() -> None:
        try:
            from getviews_pipeline.supabase_client import get_service_client

            get_service_client().table("admin_action_log").insert({
                "user_id": user_id, "action": action, "params_json": params or {},
                "result_status": result_status, "error_message": error_message, "duration_ms": duration_ms,
            }).execute()
        except Exception as exc:
            logger.warning("[admin_action_log] insert failed: %s", exc)

    threading.Thread(target=_do, daemon=True, name=f"admin-audit-{action}").start()


# ── Trigger runner helpers ────────────────────────────────────────────────────

class AdminTriggerIngestBody(BaseModel):
    niche_ids: list[int] | None = None
    deep_pool: bool = False


class AdminTriggerMorningRitualBody(BaseModel):
    user_ids: list[str] | None = None


class AdminTriggerEmptyBody(BaseModel):
    """Placeholder body for jobs that take no parameters."""


class AdminTriggerThumbnailBackfillBody(BaseModel):
    batch_size: int = 20
    limit: int | None = None
    dry_run: bool = False


class AdminTriggerRefreshBody(BaseModel):
    """Corpus freshness refresh — metadata-only re-pull from EnsembleData."""
    limit: int | None = None         # defaults to REFRESH_BATCH_LIMIT (200)
    stale_days: int | None = None    # defaults to REFRESH_STALE_DAYS (3)
    views_floor: int | None = None   # defaults to REFRESH_VIEWS_FLOOR (1000)


class AdminTriggerEnrichShotsBody(BaseModel):
    """Wave 2.5 Phase A PR #4c — top-N Gemini re-extract for video_shots.

    Re-runs the full ingest analyze+upload path (new enrichment prompt
    + per-scene frame extraction) on the highest-view video_corpus rows
    that still have NULL framing on all their shots. Budget: ~$0.003 per
    video Gemini + ~1 ED unit, so limit=500 ≈ $1.50 Gemini.
    """
    limit: int = 500
    dry_run: bool = False


async def _admin_run_ingest(body: AdminTriggerIngestBody) -> dict[str, Any]:
    from getviews_pipeline.corpus_ingest import run_batch_ingest
    from getviews_pipeline.ensemble import EnsembleDailyBudgetExceeded

    try:
        summary = await run_batch_ingest(niche_ids=body.niche_ids, deep_pool=body.deep_pool)
    except EnsembleDailyBudgetExceeded as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"ensemble_daily_budget_exceeded: {exc}") from exc
    return {
        "ok": True,
        "total_inserted": summary.total_inserted,
        "total_skipped": summary.total_skipped,
        "total_failed": summary.total_failed,
        "niches_processed": summary.niches_processed,
        "materialized_view_refreshed": summary.materialized_view_refreshed,
    }


async def _admin_run_morning_ritual(body: AdminTriggerMorningRitualBody) -> dict[str, Any]:
    from getviews_pipeline.morning_ritual import run_morning_ritual_batch
    from getviews_pipeline.supabase_client import get_service_client

    summary = await run_sync(run_morning_ritual_batch, get_service_client(), body.user_ids)
    return {
        "ok": True,
        "generated": summary.generated,
        "skipped_thin": summary.skipped_thin,
        "failed_schema": summary.failed_schema,
        "failed_gemini": summary.failed_gemini,
        "failed_duplicate_hooks": summary.failed_duplicate_hooks,
        "failed_upsert": summary.failed_upsert,
        "users_no_niche": summary.users_no_niche,
    }


async def _admin_run_analytics() -> dict[str, Any]:
    from getviews_pipeline.batch_analytics import run_analytics
    from getviews_pipeline.corpus_context import _anon_client
    from getviews_pipeline.pattern_fingerprint import recompute_weekly_counts
    from getviews_pipeline.signal_classifier import run_signal_grading

    analytics = await run_analytics()
    signal = await run_signal_grading()
    patterns_touched = 0
    try:
        patterns_touched = await recompute_weekly_counts(_anon_client())
    except Exception as exc:
        logger.warning("[admin/trigger/analytics] pattern weekly recompute failed: %s", exc)
    return {
        "ok": True,
        "analytics": {"creators_updated": analytics.creators_updated, "videos_updated": analytics.videos_updated, "errors": analytics.errors},
        "signal": {"grades_written": signal.grades_written, "niches_processed": signal.niches_processed, "errors": signal.errors},
        "patterns": {"rows_updated": patterns_touched},
    }


async def _admin_run_scene_intelligence() -> dict[str, Any]:
    from getviews_pipeline.scene_intelligence_refresh import refresh_scene_intelligence_sync
    from getviews_pipeline.supabase_client import get_service_client

    stats = await run_sync(refresh_scene_intelligence_sync, get_service_client())
    return {"ok": True, **stats}


async def _admin_run_thumbnail_backfill(body: AdminTriggerThumbnailBackfillBody) -> dict[str, Any]:
    import sys
    from pathlib import Path

    scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from backfill_thumbnails import run_thumbnail_backfill  # type: ignore[import-not-found]

    return await run_thumbnail_backfill(batch_size=body.batch_size, limit=body.limit, dry_run=body.dry_run)


async def _admin_run_enrich_shots_top500(
    body: AdminTriggerEnrichShotsBody,
) -> dict[str, Any]:
    """Re-extract top-N video_corpus rows to populate the enrichment
    fields (framing/pace/overlay_style/subject/motion/description) +
    per-scene frame_url on video_shots. See Wave 2.5 Phase A PR #4c.
    """
    from getviews_pipeline.corpus_ingest import (
        pick_top_videos_for_enrichment,
        run_reingest_video_items,
    )
    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    picked = await pick_top_videos_for_enrichment(client, limit=body.limit)

    if body.dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "picked": len(picked),
            "preview": [p["video_id"] for p in picked[:20]],
        }

    if not picked:
        return {"ok": True, "picked": 0, "inserted": 0, "skipped": 0, "failed": 0}

    summary = await run_reingest_video_items(picked, refresh_mv=False)
    return {
        "ok": True,
        "picked": len(picked),
        "inserted": summary.total_inserted,
        "skipped": summary.total_skipped,
        "failed": summary.total_failed,
        "niches_processed": summary.niches_processed,
    }


async def _admin_run_refresh(body: AdminTriggerRefreshBody) -> dict[str, Any]:
    """Manual kick of /batch/refresh — re-pull views/likes/etc for the
    top-priority video_corpus rows. Closes the Axis 3 freshness gap.
    """
    from getviews_pipeline.corpus_refresh import (
        REFRESH_BATCH_LIMIT,
        REFRESH_STALE_DAYS,
        REFRESH_VIEWS_FLOOR,
        run_corpus_refresh,
    )

    return await run_corpus_refresh(
        limit=body.limit if body.limit is not None else REFRESH_BATCH_LIMIT,
        stale_days=body.stale_days if body.stale_days is not None else REFRESH_STALE_DAYS,
        views_floor=body.views_floor if body.views_floor is not None else REFRESH_VIEWS_FLOOR,
    )


async def _admin_run_reclassify_format() -> dict[str, Any]:
    """Manual kick of /batch/reclassify-format — regex-only catch-up on
    rows stuck in content_format='other'/NULL."""
    from getviews_pipeline.content_format_reclassify import (
        run_content_format_reclassify,
    )
    from getviews_pipeline.supabase_client import get_service_client

    return await run_sync(run_content_format_reclassify, client=get_service_client())


async def _admin_run_layer0() -> dict[str, Any]:
    """Manual kick of /batch/layer0 — niche insights + sound insights +
    cross-niche migration. Each layer is independent; per-layer
    exceptions are captured, not re-raised."""
    from getviews_pipeline.layer0_migration import run_cross_niche_migration
    from getviews_pipeline.layer0_niche import run_niche_insights
    from getviews_pipeline.layer0_sound import run_sound_insights
    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    result: dict[str, Any] = {"ok": True}

    try:
        l0a = await run_niche_insights(client)
        result["layer0a_niche"] = {
            "insights_written": l0a.insights_written,
            "niches_skipped": l0a.niches_skipped,
            "errors": l0a.errors,
        }
    except Exception as exc:
        logger.exception("[admin/trigger/layer0] niche insights failed: %s", exc)
        result["layer0a_niche"] = {"error": str(exc)}

    try:
        l0b = await run_sound_insights(client)
        result["layer0b_sound"] = {"analyzed": l0b.get("analyzed", 0)}
    except Exception as exc:
        logger.exception("[admin/trigger/layer0] sound insights failed: %s", exc)
        result["layer0b_sound"] = {"error": str(exc)}

    try:
        l0c = await run_cross_niche_migration(client)
        result["layer0c_migration"] = {"migrations_found": l0c.get("migrations_found", 0)}
    except Exception as exc:
        logger.exception("[admin/trigger/layer0] migration failed: %s", exc)
        result["layer0c_migration"] = {"error": str(exc)}

    return result


async def _execute_trigger_task(*, job_id: str, action: str, runner: Any) -> None:
    logger.info("[admin/trigger] %s job=%s started", action, job_id)
    started = time.monotonic()
    _update_admin_job_row(job_id=job_id, result_status="running")
    try:
        result = await runner()
        duration_ms = int((time.monotonic() - started) * 1000)
        _update_admin_job_row(
            job_id=job_id, result_status="ok", duration_ms=duration_ms,
            result_json=result if isinstance(result, dict) else {"result": str(result)[:2000]},
        )
        logger.info("[admin/trigger] %s job=%s done in %dms", action, job_id, duration_ms)
    except HTTPException as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        _update_admin_job_row(job_id=job_id, result_status="error", error_message=str(exc.detail), duration_ms=duration_ms)
        logger.warning("[admin/trigger] %s job=%s failed in %dms: %s", action, job_id, duration_ms, exc.detail)
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        _update_admin_job_row(job_id=job_id, result_status="error", error_message=str(exc), duration_ms=duration_ms)
        logger.exception("[admin/trigger] %s job=%s crashed in %dms", action, job_id, duration_ms)


async def _run_trigger_with_audit(*, user_id: str, action: str, params: dict[str, Any], runner: Any) -> JSONResponse:
    import asyncio

    logger.info("[admin/trigger] %s queued params=%s invoked_by=%s", action, params, user_id)
    job_id = _insert_admin_job_row(user_id=user_id, action=action, params=params)

    if job_id is None:
        logger.warning("[admin/trigger] %s running sync (no job_id)", action)
        started = time.monotonic()
        try:
            result = await runner()
            _record_admin_action(user_id=user_id, action=action, params=params, result_status="ok", duration_ms=int((time.monotonic() - started) * 1000))
            return JSONResponse({"ok": True, "job_id": None, "status": "ok", "result": result})
        except Exception as exc:
            _record_admin_action(user_id=user_id, action=action, params=params, result_status="error", error_message=str(getattr(exc, "detail", exc))[:500], duration_ms=int((time.monotonic() - started) * 1000))
            raise

    asyncio.create_task(_execute_trigger_task(job_id=job_id, action=action, runner=runner), name=f"admin-trigger-{action}-{job_id[:8]}")
    return JSONResponse({"ok": True, "job_id": job_id, "status": "queued"}, status_code=status.HTTP_202_ACCEPTED)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/admin/corpus-health")
async def admin_corpus_health(
    _admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    """Per-niche corpus-adequacy snapshot for claim tiers."""
    from getviews_pipeline.claim_tiers import flags_for_count
    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    try:
        tax_res = client.table("niche_taxonomy").select("id, name_en, name_vn").execute()
        niches = tax_res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"niche_taxonomy: {exc}") from exc

    try:
        corpus_res = client.table("video_corpus").select("niche_id, created_at").gte("created_at", cutoff_90d.isoformat()).execute()
        corpus_rows = corpus_res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"video_corpus: {exc}") from exc

    counts_7d: dict[int, int] = {}
    counts_30d: dict[int, int] = {}
    counts_90d: dict[int, int] = {}
    last_ingest: dict[int, str] = {}

    for row in corpus_rows:
        nid = row.get("niche_id")
        created = row.get("created_at")
        if nid is None or not created:
            continue
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue
        counts_90d[nid] = counts_90d.get(nid, 0) + 1
        if created_dt >= cutoff_30d:
            counts_30d[nid] = counts_30d.get(nid, 0) + 1
        if created_dt >= cutoff_7d:
            counts_7d[nid] = counts_7d.get(nid, 0) + 1
        prev = last_ingest.get(nid)
        if prev is None or created > prev:
            last_ingest[nid] = created

    last_pattern: dict[int, str] = {}
    try:
        pat_res = client.table("video_patterns").select("niche_spread, last_seen_at, is_active").eq("is_active", True).execute()
        for row in pat_res.data or []:
            seen = row.get("last_seen_at")
            if not seen:
                continue
            for nid in row.get("niche_spread") or []:
                prev = last_pattern.get(nid)
                if prev is None or seen > prev:
                    last_pattern[nid] = seen
    except Exception as exc:
        logger.warning("[corpus-health] video_patterns fetch failed: %s", exc)

    per_niche: list[dict[str, Any]] = []
    tier_histogram = {"none": 0, "reference_pool": 0, "basic_citation": 0, "niche_norms": 0, "hook_effectiveness": 0, "trend_delta": 0}
    for n in niches:
        nid = n.get("id")
        if nid is None:
            continue
        v30 = counts_30d.get(nid, 0)
        flags = flags_for_count(v30)
        tier_histogram[flags.highest_passing_tier] = tier_histogram.get(flags.highest_passing_tier, 0) + 1
        per_niche.append({
            "niche_id": nid, "name_en": n.get("name_en"), "name_vn": n.get("name_vn"),
            "videos_7d": counts_7d.get(nid, 0), "videos_30d": v30, "videos_90d": counts_90d.get(nid, 0),
            "last_ingest_at": last_ingest.get(nid), "last_pattern_at": last_pattern.get(nid),
            "claim_tiers": flags.asdict(), "highest_passing_tier": flags.highest_passing_tier,
        })

    per_niche.sort(key=lambda r: (-r["videos_30d"], r["niche_id"]))
    summary = {
        "niches_total": len(per_niche),
        "videos_7d_total": sum(counts_7d.values()),
        "videos_30d_total": sum(counts_30d.values()),
        "videos_90d_total": sum(counts_90d.values()),
        "tier_histogram": tier_histogram,
    }
    return JSONResponse({"ok": True, "as_of": now.isoformat(), "summary": summary, "niches": per_niche})


@router.get("/admin/ensemble-credits")
async def admin_ensemble_credits(
    _admin: dict[str, Any] = Depends(require_admin),
    days: int = Query(14, ge=1, le=60),
) -> JSONResponse:
    now = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    for i in range(days):
        day = (now - timedelta(days=i)).date().isoformat()
        try:
            payload = _ensemble_fetch_used_units(day)
            units_raw = payload.get("units")
            if units_raw is None and isinstance(payload.get("data"), dict):
                units_raw = payload["data"].get("units")
            units = int(units_raw or 0)
            results.append({"date": day, "units": units, "ok": True})
        except HTTPException as exc:
            results.append({"date": day, "units": 0, "ok": False, "error": str(exc.detail)})
    results.reverse()
    return JSONResponse({"ok": True, "as_of": now.isoformat(), "monthly_budget": _ENSEMBLE_MONTHLY_BUDGET or None, "days": results})


@router.get("/admin/ensemble-call-sites")
async def admin_ensemble_call_sites(
    _admin: dict[str, Any] = Depends(require_admin),
    days: int = Query(7, ge=1, le=30),
) -> JSONResponse:
    from getviews_pipeline.supabase_client import get_service_client

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        resp = get_service_client().table("ensemble_calls").select("endpoint, call_site, request_class").gte("created_at", since).execute()
        rows = resp.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    total = len(rows)

    def _group(key: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for row in rows:
            v = row.get(key) or "unknown"
            counts[v] = counts.get(v, 0) + 1
        out = [{"key": k, "count": c, "pct": round(c / total * 100, 1) if total > 0 else 0.0} for k, c in counts.items()]
        out.sort(key=lambda r: (-r["count"], r["key"]))
        return out

    return JSONResponse({"ok": True, "as_of": datetime.now(timezone.utc).isoformat(), "total": total, "days": days, "by_call_site": _group("call_site"), "by_endpoint": _group("endpoint"), "by_request_class": _group("request_class")})


@router.get("/admin/ensemble-history")
async def admin_ensemble_history(
    _admin: dict[str, Any] = Depends(require_admin),
    days: int = Query(10, ge=1, le=90),
) -> JSONResponse:
    raw = _ensemble_fetch_history(days)
    entries: list[dict[str, Any]] = []
    candidates: list[Any] = []
    if isinstance(raw, list):
        candidates = raw
    elif isinstance(raw, dict):
        for key in ("history", "entries", "data", "results"):
            val = raw.get(key)
            if isinstance(val, list):
                candidates = val
                break
            if isinstance(val, dict):
                inner = val.get("history") or val.get("entries") or val.get("results")
                if isinstance(inner, list):
                    candidates = inner
                    break
    for item in candidates:
        if not isinstance(item, dict):
            continue
        entries.append({
            "date": item.get("date") or item.get("day") or item.get("timestamp"),
            "endpoint": item.get("endpoint") or item.get("path") or item.get("name"),
            "units": item.get("units") or item.get("units_used") or item.get("cost") or 0,
            "count": item.get("count") or item.get("calls") or item.get("requests"),
        })
    return JSONResponse({"ok": True, "as_of": datetime.now(timezone.utc).isoformat(), "days": days, "entries": entries, "raw": raw})


@router.post("/admin/evaluate-alerts")
async def admin_evaluate_alerts(
    request: Request,
    _caller: dict | None = Depends(require_batch_caller),
) -> JSONResponse:
    """Run the admin alert evaluator. require_batch_caller gated (cron target)."""
    from getviews_pipeline.supabase_client import get_service_client

    try:
        rules_resp = get_service_client().table("admin_alert_rules").select("rule_key, label, severity, threshold_json, enabled").eq("enabled", True).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    rules = rules_resp.data or []
    evaluations: list[dict[str, Any]] = []

    for rule in rules:
        rule_key = rule["rule_key"]
        evaluator = _EVALUATORS.get(rule_key)
        if evaluator is None:
            evaluations.append({"rule_key": rule_key, "action": "no_evaluator"})
            continue
        try:
            breached, message, context = evaluator(rule)
        except Exception as exc:
            logger.exception("[alerts] evaluator %s crashed: %s", rule_key, exc)
            evaluations.append({"rule_key": rule_key, "action": "evaluator_crashed", "error": str(exc)[:300]})
            continue
        prev_phase = _last_alert_phase(rule_key)
        if breached and prev_phase != "firing":
            _post_slack_admin_alert(f"[{rule['label']}] {message}", rule["severity"])
            _record_alert_fire(rule_key=rule_key, severity=rule["severity"], message=message, context=context, phase="firing", delivered=bool(_SLACK_ADMIN_WEBHOOK_URL))
            evaluations.append({"rule_key": rule_key, "breached": True, "action": "fired", "message": message})
        elif not breached and prev_phase == "firing":
            _record_alert_fire(rule_key=rule_key, severity=rule["severity"], message=message, context=context, phase="cleared", delivered=False)
            evaluations.append({"rule_key": rule_key, "breached": False, "action": "cleared", "message": message})
        else:
            evaluations.append({"rule_key": rule_key, "breached": breached, "action": "no_change", "message": message})

    return JSONResponse({"ok": True, "as_of": datetime.now(timezone.utc).isoformat(), "slack_configured": bool(_SLACK_ADMIN_WEBHOOK_URL), "evaluations": evaluations})


@router.get("/admin/alert-fires")
async def admin_alert_fires(
    _admin: dict[str, Any] = Depends(require_admin),
    limit: int = Query(50, ge=1, le=200),
) -> JSONResponse:
    from getviews_pipeline.supabase_client import get_service_client

    try:
        resp = get_service_client().table("admin_alert_fires").select("id, rule_key, severity, message, context_json, phase, delivered_at, created_at").order("created_at", desc=True).limit(limit).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"ok": True, "fires": resp.data or []})


@router.get("/admin/logs")
async def admin_logs(
    _admin: dict[str, Any] = Depends(require_admin),
    limit: int = Query(100, ge=1, le=500),
    severity: str = Query("INFO", pattern="^(DEFAULT|DEBUG|INFO|NOTICE|WARNING|ERROR|CRITICAL|ALERT|EMERGENCY)$"),
    minutes: int = Query(60, ge=1, le=1440),
) -> JSONResponse:
    """Tail recent Cloud Run logs (feature-flagged via ADMIN_LOGS_ENABLED)."""
    if not _ADMIN_LOGS_ENABLED:
        return JSONResponse({"ok": True, "enabled": False, "reason": "disabled", "hint": "Set ADMIN_LOGS_ENABLED=true on Cloud Run to enable this panel."})
    if not _GCP_PROJECT_ID_FOR_LOGS:
        return JSONResponse({"ok": True, "enabled": False, "reason": "project_missing", "hint": "Set GCP_PROJECT_ID env var on Cloud Run."})
    try:
        from google.cloud import logging as gcloud_logging
    except ImportError:
        return JSONResponse({"ok": True, "enabled": False, "reason": "sdk_missing", "hint": "Install the `[logs]` extra and redeploy."})
    try:
        client = gcloud_logging.Client(project=_GCP_PROJECT_ID_FOR_LOGS)
    except Exception as exc:
        return JSONResponse({"ok": True, "enabled": False, "reason": "credentials_error", "hint": f"google-cloud-logging Client init failed: {exc}."})
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    filters = ['resource.type = "cloud_run_revision"', f'timestamp >= "{since.isoformat()}"', f'severity >= {severity}']
    if _CLOUD_RUN_SERVICE_NAME:
        filters.append(f'resource.labels.service_name = "{_CLOUD_RUN_SERVICE_NAME}"')
    filter_str = " AND ".join(filters)
    try:
        entries_iter = client.list_entries(filter_=filter_str, order_by=gcloud_logging.DESCENDING, max_results=limit)
        entries: list[dict[str, Any]] = []
        for entry in entries_iter:
            payload = entry.payload
            if isinstance(payload, (dict, list)):
                message = json.dumps(payload, ensure_ascii=False)[:2000]
            else:
                message = str(payload)[:2000] if payload is not None else ""
            ts = entry.timestamp.isoformat() if entry.timestamp else None
            entries.append({"timestamp": ts, "severity": str(entry.severity) if entry.severity else "DEFAULT", "message": message, "logger": entry.resource.labels.get("service_name", "") if entry.resource else ""})
    except Exception as exc:
        return JSONResponse({"ok": True, "enabled": False, "reason": "credentials_error", "hint": f"list_entries failed: {exc}"})
    return JSONResponse({"ok": True, "enabled": True, "filter": filter_str, "entries": entries})


@router.get("/admin/action-log")
async def admin_action_log(
    _admin: dict[str, Any] = Depends(require_admin),
    limit: int = Query(50, ge=1, le=200),
) -> JSONResponse:
    from getviews_pipeline.supabase_client import get_service_client

    try:
        resp = get_service_client().table("admin_action_log").select("id, user_id, action, params_json, result_status, error_message, duration_ms, result_json, created_at").order("created_at", desc=True).limit(limit).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"ok": True, "entries": resp.data or []})


@router.get("/admin/jobs/{job_id}")
async def admin_job_status(
    job_id: str,
    _admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    from getviews_pipeline.supabase_client import get_service_client

    try:
        resp = get_service_client().table("admin_action_log").select("id, user_id, action, params_json, result_status, error_message, duration_ms, result_json, created_at").eq("id", job_id).limit(1).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    rows = resp.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="job_not_found")
    return JSONResponse({"ok": True, "job": rows[0]})


@router.get("/admin/triggers")
async def admin_list_triggers(
    _admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return JSONResponse({
        "ok": True,
        "jobs": [
            {"id": "ingest", "label": "Corpus ingest (/batch/ingest)", "body_schema": {"niche_ids": "int[] | null", "deep_pool": "bool"}, "heavy": True},
            {
                "id": "refresh",
                "label": "Corpus freshness refresh (/batch/refresh)",
                "body_schema": {
                    "limit": "int | null",
                    "stale_days": "int | null",
                    "views_floor": "int | null",
                },
                "heavy": True,
            },
            {
                "id": "reclassify_format",
                "label": "Content-format reclass (/batch/reclassify-format)",
                "body_schema": {},
                "heavy": True,
            },
            {"id": "morning_ritual", "label": "Morning ritual scripts (/batch/morning-ritual)", "body_schema": {"user_ids": "uuid[] | null"}, "heavy": True},
            {"id": "analytics", "label": "Weekly analytics + signal grading (/batch/analytics)", "body_schema": {}, "heavy": True},
            {"id": "layer0", "label": "Layer 0 insights", "body_schema": {}, "heavy": True},
            {"id": "scene_intelligence", "label": "Scene intelligence refresh (/batch/scene-intelligence)", "body_schema": {}, "heavy": True},
            {"id": "thumbnail_backfill", "label": "Thumbnail backfill — rehost TikTok CDN → R2", "body_schema": {}, "heavy": True},
        ],
    })


@router.post("/admin/trigger/ingest")
async def admin_trigger_ingest(
    body: AdminTriggerIngestBody = AdminTriggerIngestBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.ingest",
        params={"niche_ids": body.niche_ids, "deep_pool": body.deep_pool},
        runner=lambda: _admin_run_ingest(body),
    )


@router.post("/admin/trigger/morning_ritual")
async def admin_trigger_morning_ritual(
    body: AdminTriggerMorningRitualBody = AdminTriggerMorningRitualBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.morning_ritual",
        params={"user_ids": body.user_ids},
        runner=lambda: _admin_run_morning_ritual(body),
    )


@router.post("/admin/trigger/analytics")
async def admin_trigger_analytics(
    _body: AdminTriggerEmptyBody = AdminTriggerEmptyBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(user_id=admin["user_id"], action="trigger.analytics", params={}, runner=_admin_run_analytics)


@router.post("/admin/trigger/scene_intelligence")
async def admin_trigger_scene_intelligence(
    _body: AdminTriggerEmptyBody = AdminTriggerEmptyBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(user_id=admin["user_id"], action="trigger.scene_intelligence", params={}, runner=_admin_run_scene_intelligence)


@router.post("/admin/trigger/thumbnail_backfill")
async def admin_trigger_thumbnail_backfill(
    body: AdminTriggerThumbnailBackfillBody = AdminTriggerThumbnailBackfillBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.thumbnail_backfill",
        params={"batch_size": body.batch_size, "limit": body.limit, "dry_run": body.dry_run},
        runner=lambda: _admin_run_thumbnail_backfill(body),
    )


@router.post("/admin/trigger/refresh")
async def admin_trigger_refresh(
    body: AdminTriggerRefreshBody = AdminTriggerRefreshBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.refresh",
        params={
            "limit": body.limit,
            "stale_days": body.stale_days,
            "views_floor": body.views_floor,
        },
        runner=lambda: _admin_run_refresh(body),
    )


@router.post("/admin/trigger/reclassify_format")
async def admin_trigger_reclassify_format(
    _body: AdminTriggerEmptyBody = AdminTriggerEmptyBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.reclassify_format",
        params={}, runner=_admin_run_reclassify_format,
    )


@router.post("/admin/trigger/layer0")
async def admin_trigger_layer0(
    _body: AdminTriggerEmptyBody = AdminTriggerEmptyBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.layer0",
        params={}, runner=_admin_run_layer0,
    )


@router.post("/admin/trigger/enrich_shots_top500")
async def admin_trigger_enrich_shots_top500(
    body: AdminTriggerEnrichShotsBody = AdminTriggerEnrichShotsBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.enrich_shots_top500",
        params={"limit": body.limit, "dry_run": body.dry_run},
        runner=lambda: _admin_run_enrich_shots_top500(body),
    )


# ── Phase 3.4 — /admin/diagnostics ────────────────────────────────────────────

@router.get("/admin/diagnostics")
async def admin_diagnostics(
    _admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    """Operational diagnostics snapshot for on-call and deploy verification.

    Returns:
      - instance_id: K_REVISION env (Cloud Run revision) or "local"
      - batch_secret_configured: bool (whether X-Batch-Secret is still in use)
      - idempotency_table_row_count: int (rows in answer_session_idempotency)
      - models: active Gemini model names from config
      - as_of: ISO timestamp
    """
    from getviews_pipeline.config import GEMINI_MODEL_PRIMARY, GEMINI_MODEL_FALLBACK
    from getviews_pipeline.deps import _BATCH_SECRET
    from getviews_pipeline.supabase_client import get_service_client

    instance_id = os.environ.get("K_REVISION", "local")

    idem_row_count: int | None = None
    try:
        resp = get_service_client().table("answer_session_idempotency").select("user_id", count="exact").limit(0).execute()
        idem_row_count = resp.count if hasattr(resp, "count") else None
    except Exception as exc:
        logger.warning("[admin/diagnostics] idempotency count failed: %s", exc)

    return JSONResponse({
        "ok": True,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "instance_id": instance_id,
        "batch_secret_configured": bool(_BATCH_SECRET),
        "batch_secret_migration_status": (
            "legacy_active — migrate Scheduler jobs to admin JWT" if _BATCH_SECRET
            else "migrated — BATCH_SECRET can be removed"
        ),
        "idempotency_table_row_count": idem_row_count,
        "models": {
            "primary": GEMINI_MODEL_PRIMARY if hasattr(__import__("getviews_pipeline.config", fromlist=["GEMINI_MODEL_PRIMARY"]), "GEMINI_MODEL_PRIMARY") else "see config.py",
            "fallback": GEMINI_MODEL_FALLBACK if hasattr(__import__("getviews_pipeline.config", fromlist=["GEMINI_MODEL_FALLBACK"]), "GEMINI_MODEL_FALLBACK") else "see config.py",
        },
    })
