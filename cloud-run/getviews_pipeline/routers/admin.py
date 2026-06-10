"""Admin dashboard backend routes (/admin/*)."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.parse as _urlparse
import urllib.request as _urlrequest
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field

from getviews_pipeline.api_models import StrictBody
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
# Customer APIs (official): GET with query params only — no path prefix beyond /apis
#   get-used-units:  ?date=YYYY-MM-DD&token=...
#   get-history:     ?days=N&token=...
#   https://ensembledata.com/apis/customer/get-used-units
#   https://ensembledata.com/apis/customer/get-history

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


def _ed_used_units_from_payload(payload: dict[str, Any]) -> int:
    """EnsembleData ``/customer/get-used-units`` returns either a top-level
    ``units`` int, ``data.units``, or a per-platform map under ``data`` (e.g.
    ``data.tiktok``) per current docs. Summing only ``data.units`` produced
    all-zero admin panels when the map form was used.
    """
    u = payload.get("units")
    if u is not None:
        try:
            return int(u)
        except (TypeError, ValueError):
            pass
    data = payload.get("data")
    if not isinstance(data, dict):
        return 0
    u2 = data.get("units")
    if u2 is not None:
        try:
            return int(u2)
        except (TypeError, ValueError):
            pass
    total = 0
    for v in data.values():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            total += int(v)
    return total


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
            "delivered_at": datetime.now(UTC).isoformat() if delivered else None,
        }).execute()
    except Exception as exc:
        logger.exception("[alerts] _record_alert_fire(%s) failed: %s", rule_key, exc)


def _evaluate_ensemble_runway_low(rule: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    runway_days_max = int(rule.get("threshold_json", {}).get("runway_days_max", 7))
    if _ENSEMBLE_MONTHLY_BUDGET <= 0:
        return (False, "ED_MONTHLY_UNIT_BUDGET unset — rule skipped", {"reason": "no_budget"})
    now = datetime.now(UTC)
    total_used = last7_sum = last7_days = 0
    for i in range(30):
        day = (now - timedelta(days=i)).date().isoformat()
        try:
            payload = _ensemble_fetch_used_units(day)
            units = _ed_used_units_from_payload(payload)
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
    age_h = (datetime.now(UTC) - last).total_seconds() / 3600
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

    Rows auto-swept after Cloud Run timeout (``swept_stale_running``) are
    excluded — they are observability hygiene, not pipeline breakage.
    """
    from getviews_pipeline.batch_observability import is_swept_stale_batch_job_run
    from getviews_pipeline.supabase_client import get_service_client

    window_days = int(rule.get("threshold_json", {}).get("window_days", 7))
    failures_max = int(rule.get("threshold_json", {}).get("failures_max", 0))

    since_iso = (datetime.now(UTC) - timedelta(days=window_days)).isoformat()
    try:
        client = get_service_client()
        rows: list[dict[str, Any]] = []
        offset = 0
        page_size = 500
        while True:
            resp = (
                client.table("batch_job_runs")
                .select("job_name, error, started_at, summary")
                .eq("status", "failed")
                .gte("started_at", since_iso)
                .order("started_at", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            batch = resp.data or []
            if not batch:
                break
            for row in batch:
                if is_swept_stale_batch_job_run(row):
                    continue
                rows.append(row)
            if len(batch) < page_size:
                break
            offset += page_size
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


def _evaluate_pg_net_batch_http_4xx(rule: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    """Fire when pg_net logged HTTP 4xx for a ``/batch/*`` request (recent window).

    Complements ``cron_batch_failures``: Cloud Run may never run when pg_cron
    hits the wrong service (401/404) so ``batch_job_runs`` stays empty. This
    rule reads ``net._http_response`` × ``net.http_request_queue`` via RPC
    ``admin_pg_net_batch_http_4xx_events``.
    """
    t = rule.get("threshold_json") or {}
    hours = int(t.get("hours", 6))
    max_4xx = int(t.get("max_4xx", 0))
    from getviews_pipeline.supabase_client import get_service_client

    try:
        resp = (
            get_service_client()
            .rpc("admin_pg_net_batch_http_4xx_events", {"p_hours": hours})
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:
        return (False, f"query failed: {exc}", {"reason": "query_error"})

    n = len(rows)
    breached = n > max_4xx
    sample = rows[:5] if rows else []
    context = {
        "count_4xx": n,
        "max_4xx": max_4xx,
        "hours": hours,
        "sample": sample,
    }
    if breached:
        codes = ", ".join(str(r.get("status_code")) for r in sample if r.get("status_code") is not None)
        msg = f"pg_net: {n} HTTP 4xx tới /batch/* trong {hours}h (mã mẫu: {codes or 'n/a'})"
    else:
        msg = f"pg_net batch HTTP ok · 0 4xx trong {hours}h (ngưỡng {max_4xx})"
    return (breached, msg, context)


_EVALUATORS: dict[str, Any] = {
    "ensemble_runway_low": _evaluate_ensemble_runway_low,
    "corpus_stale": _evaluate_corpus_stale,
    "admin_trigger_error_spike": _evaluate_trigger_error_spike,
    "cron_batch_failures": _evaluate_cron_batch_failures,
    "pg_net_batch_http_4xx": _evaluate_pg_net_batch_http_4xx,
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

class AdminTriggerIngestBody(StrictBody):
    niche_ids: list[int] | None = None
    deep_pool: bool = False
    ingest_shift: str | None = None
    ingest_shift_count: int = Field(default=3, ge=1, le=6)


class AdminTriggerMorningRitualBody(StrictBody):
    """Same job as ``POST /batch/morning-ritual`` but JWT+is_admin instead of X-Batch-Secret."""

    user_ids: list[str] | None = Field(
        default=None,
        description=(
            "Profile UUIDs to process. Omit or null = every user with a niche "
            "set: one 3-script bundle per user (single-niche model since 2026-05-05)."
        ),
    )


class AdminTriggerEmptyBody(StrictBody):
    """Placeholder body for jobs that take no parameters."""


class AdminTriggerPostProcessingBody(StrictBody):
    """Manual kick of /batch/post-processing — heal MV / VĐH / sound after ingest."""

    weekly_if_sunday: bool = True


class AdminTriggerThumbnailBackfillBody(StrictBody):
    batch_size: int = 20
    limit: int | None = None
    dry_run: bool = False


class AdminBackfillClassificationBody(StrictBody):
    """ME-17 — text-only Gemini backfill for ``content_context`` + ``niche_classification``."""

    batch_size: int = Field(default=500, ge=1, le=10_000)
    max_runtime_s: int = Field(default=3300, ge=30, le=7200)
    dry_run: bool = False


class AdminCrossNicheRemapBackfillBody(StrictBody):
    """Deterministic cross-niche ``content_class_id`` realignment (HI-11 loop misfiles)."""

    batch_size: int = Field(default=500, ge=1, le=5000)
    max_runtime_s: int = Field(default=3300, ge=30, le=7200)
    dry_run: bool = False
    video_ids: list[str] | None = None


class AdminAssignmentTierBackfillBody(StrictBody):
    """ACQE — backfill ``class_assignment_tier`` on legacy rows + junction repair."""

    batch_size: int = Field(default=500, ge=50, le=2000)
    max_rows: int = Field(default=15_000, ge=100, le=50_000)
    repair_validated_junction: bool = True


class AdminTriggerRefreshBody(StrictBody):
    """Corpus freshness refresh — metadata-only re-pull from EnsembleData."""
    limit: int | None = None         # defaults to REFRESH_BATCH_LIMIT (200)
    stale_days: int | None = None    # defaults to REFRESH_STALE_DAYS (3)
    views_floor: int | None = None   # defaults to REFRESH_VIEWS_FLOOR (1000)


class AdminTriggerR2JanitorBody(StrictBody):
    """R2 storage janitor — defaults to dry-run for safety."""
    dry_run: bool = True


class AdminTriggerEnrichShotsBody(StrictBody):
    """Wave 2.5 Phase A PR #4c — top-N Gemini re-extract for video_shots.

    Re-runs the full ingest analyze+upload path (new enrichment prompt
    + per-scene frame extraction) on the highest-view video_corpus rows
    that still have NULL framing on all their shots. Budget: ~$0.003 per
    video Gemini + ~1 ED unit, so limit=500 ≈ $1.50 Gemini.
    """
    limit: int = 500
    dry_run: bool = False


class AdminTriggerViralScoreBacktestBody(StrictBody):
    """Wave 3 PR #4 — proposed viral-alignment score backtest over a
    sample of corpus rows with known breakout_multiplier.

    Returns score distribution + Spearman ρ so the design doc (PR #5)
    can commit to the formula with receipts. Reproducible via
    ``seed`` — default matches the doc's committed run.
    """
    sample_size: int = 200
    seed: int | None = 2026


async def _admin_run_ingest(body: AdminTriggerIngestBody) -> dict[str, Any]:
    from getviews_pipeline.corpus_ingest import run_batch_ingest
    from getviews_pipeline.ensemble import EnsembleDailyBudgetExceeded

    try:
        summary = await run_batch_ingest(
            niche_ids=body.niche_ids,
            deep_pool=body.deep_pool,
            ingest_shift=body.ingest_shift,
            ingest_shift_count=body.ingest_shift_count,
        )
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


async def _admin_run_backfill_classification(body: AdminBackfillClassificationBody) -> dict[str, Any]:
    from getviews_pipeline.classification_backfill import run_classification_backfill
    from getviews_pipeline.supabase_client import get_service_client

    return await run_sync(
        run_classification_backfill,
        client=get_service_client(),
        batch_size=body.batch_size,
        max_runtime_s=float(body.max_runtime_s),
        dry_run=body.dry_run,
    )


async def _admin_run_cross_niche_remap_backfill(
    body: AdminCrossNicheRemapBackfillBody,
) -> dict[str, Any]:
    from getviews_pipeline.classification_backfill import run_cross_niche_class_remap_backfill
    from getviews_pipeline.runtime import run_sync
    from getviews_pipeline.supabase_client import get_service_client

    return await run_sync(
        run_cross_niche_class_remap_backfill,
        client=get_service_client(),
        batch_size=body.batch_size,
        max_runtime_s=float(body.max_runtime_s),
        dry_run=body.dry_run,
        video_ids=body.video_ids,
    )


async def _admin_run_assignment_tier_backfill(
    body: AdminAssignmentTierBackfillBody,
) -> dict[str, Any]:
    from getviews_pipeline.class_quality_engine import run_assignment_tier_backfill
    from getviews_pipeline.supabase_client import get_service_client

    return await run_sync(
        run_assignment_tier_backfill,
        get_service_client(),
        batch_size=body.batch_size,
        max_rows=body.max_rows,
        repair_validated_junction=body.repair_validated_junction,
    )


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


async def _admin_run_viral_score_backtest(
    body: AdminTriggerViralScoreBacktestBody,
) -> dict[str, Any]:
    """Run the viral-alignment backtest harness and record the
    distribution / Spearman ρ to ``batch_job_runs``. See Wave 3 PR #4.

    Wrapped in ``record_job_run`` so the run shows up in the batch
    observability dashboard alongside cron jobs, and a failed run is
    auditable as ``status='failed'`` rather than vanishing.
    """
    from getviews_pipeline.batch_observability import record_job_run
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.viral_alignment_backtest import run_viral_score_backtest

    client = get_service_client()
    async with record_job_run(client, "viral_score_backtest") as summary_slot:
        result = await run_viral_score_backtest(
            client, sample_size=body.sample_size, seed=body.seed,
        )
        # Mutate in place — record_job_run stores the final contents.
        summary_slot.update(result)
        return {"ok": True, **result}


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


async def _admin_run_post_processing(body: AdminTriggerPostProcessingBody) -> dict[str, Any]:
    """Manual kick of /batch/post-processing — heal MV / Video Đáng Học /
    sound insights (+ Sunday weekly analytics) after an aborted ingest."""
    from getviews_pipeline.corpus_ingest import run_ingest_post_processing
    from getviews_pipeline.supabase_client import get_service_client

    return await run_ingest_post_processing(
        get_service_client(),
        run_weekly_analytics_if_sunday=body.weekly_if_sunday,
    )


async def _admin_run_reclassify_format() -> dict[str, Any]:
    """Manual kick of /batch/reclassify-format — regex-only catch-up on
    rows stuck in content_format='other'/NULL."""
    from getviews_pipeline.content_format_reclassify import (
        run_content_format_reclassify,
    )
    from getviews_pipeline.supabase_client import get_service_client

    return await run_sync(run_content_format_reclassify, client=get_service_client())


async def _admin_run_r2_janitor(*, dry_run: bool = True) -> dict[str, Any]:
    """Manual kick of /batch/r2-janitor — reconcile R2 storage against
    video_corpus and delete orphans. Defaults to dry-run for safety;
    pass dry_run=False to run the destructive pass."""
    from getviews_pipeline.r2_janitor import run_r2_janitor
    from getviews_pipeline.supabase_client import get_service_client

    return await run_sync(run_r2_janitor, dry_run=dry_run, client=get_service_client())


async def _admin_run_layer0() -> dict[str, Any]:
    """Manual kick of /batch/layer0 — niche insights + sound insights.
    Each layer is independent; per-layer exceptions are captured, not
    re-raised."""
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
    now = datetime.now(UTC)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    try:
        tax_res = client.table("niche_taxonomy").select("id, name_en, name_vn").execute()
        niches = tax_res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"niche_taxonomy: {exc}") from exc

    try:
        corpus_res = client.table("video_corpus").select("ingest_loop_niche_id, created_at").gte("created_at", cutoff_90d.isoformat()).execute()
        corpus_rows = corpus_res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"video_corpus: {exc}") from exc

    counts_7d: dict[int, int] = {}
    counts_30d: dict[int, int] = {}
    counts_90d: dict[int, int] = {}
    last_ingest: dict[int, str] = {}

    for row in corpus_rows:
        nid = row.get("ingest_loop_niche_id")
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


@router.get("/admin/corpus-class-health")
async def admin_corpus_class_health(
    _admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    """Per-content_class corpus snapshot — assignment tiers + junction alignment."""
    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    now = datetime.now(UTC)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    try:
        classes_res = (
            client.table("content_classifications")
            .select("id, slug, name_vn, format_axis, active")
            .eq("active", True)
            .execute()
        )
        classes = classes_res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"content_classifications: {exc}") from exc

    try:
        corpus_res = (
            client.table("video_corpus")
            .select(
                "content_class_id, indexed_at, class_assignment_tier, "
                "inferred_creator_niche_id"
            )
            .eq("language", "vi")
            .gte("indexed_at", cutoff_90d.isoformat())
            .not_.is_("content_class_id", "null")
            .execute()
        )
        corpus_rows = corpus_res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"video_corpus: {exc}") from exc

    try:
        junction_res = (
            client.table("creator_niche_content_classes")
            .select("creator_niche_id, content_class_id")
            .execute()
        )
        junction_pairs = {
            (int(r["creator_niche_id"]), int(r["content_class_id"]))
            for r in (junction_res.data or [])
            if r.get("creator_niche_id") is not None and r.get("content_class_id") is not None
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"junction: {exc}") from exc

    targets_by_cc: dict[int, dict[str, Any]] = {}
    try:
        targets_res = (
            client.table("content_class_ingest_targets")
            .select("content_class_id, viability_tier, daily_vpn, active")
            .execute()
        )
        for t in targets_res.data or []:
            cc = t.get("content_class_id")
            if cc is not None:
                targets_by_cc[int(cc)] = t
    except Exception as exc:
        logger.warning("[corpus-class-health] ingest targets fetch failed: %s", exc)

    counts_7d: dict[int, int] = {}
    counts_30d: dict[int, int] = {}
    counts_90d: dict[int, int] = {}
    tier_hist: dict[str, int] = {"validated": 0, "low_conf": 0, "flagged": 0, "null": 0}
    junction_miss_30d = 0
    corpus_30d_total = 0

    for row in corpus_rows:
        cc = row.get("content_class_id")
        indexed = row.get("indexed_at")
        if cc is None or not indexed:
            continue
        cc_id = int(cc)
        try:
            indexed_dt = datetime.fromisoformat(str(indexed).replace("Z", "+00:00"))
        except ValueError:
            continue
        counts_90d[cc_id] = counts_90d.get(cc_id, 0) + 1
        if indexed_dt >= cutoff_30d:
            counts_30d[cc_id] = counts_30d.get(cc_id, 0) + 1
            corpus_30d_total += 1
            tier = row.get("class_assignment_tier")
            tier_key = str(tier) if tier in ("validated", "low_conf", "flagged") else "null"
            tier_hist[tier_key] = tier_hist.get(tier_key, 0) + 1
            cn = row.get("inferred_creator_niche_id")
            stored_cc = row.get("content_class_id")
            if cn is not None and stored_cc is not None:
                pair = (int(cn), int(stored_cc))
                if pair not in junction_pairs:
                    junction_miss_30d += 1
        if indexed_dt >= cutoff_7d:
            counts_7d[cc_id] = counts_7d.get(cc_id, 0) + 1

    viability_hist: dict[str, int] = {"Healthy": 0, "Thin": 0, "Dormant": 0, "unknown": 0}
    per_class: list[dict[str, Any]] = []
    classes_with_corpus_30d = 0
    thin_under_20 = 0

    for c in classes:
        cc_id = c.get("id")
        if cc_id is None:
            continue
        cc_id = int(cc_id)
        v30 = counts_30d.get(cc_id, 0)
        if v30 > 0:
            classes_with_corpus_30d += 1
        if 0 < v30 < 20:
            thin_under_20 += 1
        target = targets_by_cc.get(cc_id, {})
        viability = str(target.get("viability_tier") or "unknown")
        viability_hist[viability] = viability_hist.get(viability, 0) + 1
        per_class.append({
            "content_class_id": cc_id,
            "slug": c.get("slug"),
            "name_vn": c.get("name_vn"),
            "format_axis": c.get("format_axis"),
            "videos_7d": counts_7d.get(cc_id, 0),
            "videos_30d": v30,
            "videos_90d": counts_90d.get(cc_id, 0),
            "viability_tier": target.get("viability_tier"),
            "daily_vpn": target.get("daily_vpn"),
            "ingest_active": target.get("active"),
        })

    per_class.sort(key=lambda r: (-r["videos_30d"], r["content_class_id"]))
    summary = {
        "classes_total": len(classes),
        "classes_with_corpus_30d": classes_with_corpus_30d,
        "classes_zero_corpus_30d": len(classes) - classes_with_corpus_30d,
        "classes_thin_under_20": thin_under_20,
        "videos_7d_total": sum(counts_7d.values()),
        "videos_30d_total": corpus_30d_total,
        "videos_90d_total": sum(counts_90d.values()),
        "assignment_tier_histogram_30d": tier_hist,
        "junction_miss_30d": junction_miss_30d,
        "junction_miss_rate_30d": round(junction_miss_30d / max(corpus_30d_total, 1), 4),
        "viability_histogram": viability_hist,
    }
    return JSONResponse({
        "ok": True,
        "as_of": now.isoformat(),
        "summary": summary,
        "content_classes": per_class,
    })


def _gemini_calls_site_stats(
    client: Any,
    since_iso: str,
    *,
    call_site: str,
    is_batch: bool | None = None,
) -> dict[str, Any]:
    """Paginated ``gemini_calls`` aggregate for one ingest call_site."""
    total_count = 0
    total_cost = 0.0
    offset = 0
    page_size = 1000
    while True:
        query = (
            client.table("gemini_calls")
            .select("cost_usd")
            .eq("call_site", call_site)
            .gte("created_at", since_iso)
        )
        if is_batch is not None:
            query = query.eq("is_batch", is_batch)
        resp = query.range(offset, offset + page_size - 1).execute()
        rows = resp.data or []
        if not rows:
            break
        total_count += len(rows)
        for row in rows:
            try:
                total_cost += float(row.get("cost_usd") or 0)
            except (TypeError, ValueError):
                continue
        if len(rows) < page_size:
            break
        offset += page_size
    return {
        "count": total_count,
        "cost_usd": round(total_cost, 4),
    }


def _gemini_batch_call_stats(client: Any, since_iso: str) -> dict[str, Any]:
    """Aggregate ``video_extraction_batch`` rows since ``since_iso``."""
    return _gemini_calls_site_stats(
        client, since_iso, call_site="video_extraction_batch", is_batch=True,
    )


def _hi13_gemini_tier_share(batch_stats: dict[str, Any], sync_stats: dict[str, Any]) -> float | None:
    batch_n = int(batch_stats.get("count") or 0)
    sync_n = int(sync_stats.get("count") or 0)
    total = batch_n + sync_n
    if total == 0:
        return None
    return round(batch_n / total, 4)


def _hi13_ingest_batch_path_share(totals: dict[str, int]) -> float | None:
    """Share of corpus videos that exited via Batch API vs sync fallback."""
    ok = int(totals.get("batch_line_ok") or 0)
    fallback = int(totals.get("sync_fallback") or 0)
    denom = ok + fallback
    if denom == 0:
        return None
    return round(ok / denom, 4)


def _aggregate_ingest_hi13_totals(client: Any, since_iso: str) -> dict[str, int]:
    """Sum HI-13 counters from all ``batch/ingest`` rows in the window (paginated)."""
    totals = {
        "batch_line_ok": 0,
        "batch_line_fail": 0,
        "sync_fallback": 0,
        "batch_jobs_ok": 0,
        "batch_jobs_failed": 0,
        "runs": 0,
    }
    offset = 0
    page_size = 500
    while True:
        resp = (
            client.table("batch_job_runs")
            .select("summary")
            .eq("job_name", "batch/ingest")
            .gte("started_at", since_iso)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            break
        for row in rows:
            hi13 = _hi13_from_job_summary(row.get("summary") or {})
            totals["runs"] += 1
            for key in (
                "batch_line_ok",
                "batch_line_fail",
                "sync_fallback",
                "batch_jobs_ok",
                "batch_jobs_failed",
            ):
                totals[key] += hi13.get(key, 0)
        if len(rows) < page_size:
            break
        offset += page_size
    return totals


def _hi13_from_job_summary(summary: Any) -> dict[str, int]:
    if not isinstance(summary, dict):
        return {}
    hi13 = summary.get("hi13")
    if isinstance(hi13, dict):
        return {
            "batch_line_ok": int(hi13.get("batch_line_ok") or 0),
            "batch_line_fail": int(hi13.get("batch_line_fail") or 0),
            "sync_fallback": int(hi13.get("sync_fallback") or 0),
            "batch_jobs_ok": int(hi13.get("batch_jobs_ok") or 0),
            "batch_jobs_failed": int(hi13.get("batch_jobs_failed") or 0),
        }
    return {
        "batch_line_ok": int(summary.get("batch_line_hits") or 0),
        "batch_line_fail": len(summary.get("batch_line_errors") or []),
        "sync_fallback": int(summary.get("sync_fallback_count") or 0),
        "batch_jobs_ok": 1 if summary.get("batch_job_ok") else 0,
        "batch_jobs_failed": 0 if summary.get("batch_job_ok") else 1,
    }


@router.get("/admin/hi13-batch-health")
async def admin_hi13_batch_health(
    _admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    """HI-13 Gemini Batch API — ingest flag, gemini_calls, and recent job runs."""
    from getviews_pipeline.config import (
        CORPUS_BATCH_POLL_INTERVAL_SEC,
        CORPUS_BATCH_POLL_MAX_SEC,
        CORPUS_INGEST_USE_GEMINI_BATCH,
    )
    from getviews_pipeline.supabase_client import get_service_client

    client = get_service_client()
    now = datetime.now(UTC)
    since_7d = (now - timedelta(days=7)).isoformat()
    since_30d = (now - timedelta(days=30)).isoformat()

    batch_7d = _gemini_batch_call_stats(client, since_7d)
    batch_30d = _gemini_batch_call_stats(client, since_30d)
    sync_7d = _gemini_calls_site_stats(
        client, since_7d, call_site="video_extraction", is_batch=False,
    )
    sync_30d = _gemini_calls_site_stats(
        client, since_30d, call_site="video_extraction", is_batch=False,
    )

    from getviews_pipeline.batch_observability import is_swept_stale_batch_job_run

    recent_runs: list[dict[str, Any]] = []
    try:
        ingest_totals = _aggregate_ingest_hi13_totals(client, since_30d)
        runs_res = (
            client.table("batch_job_runs")
            .select("job_name, started_at, finished_at, status, duration_ms, summary, error")
            .in_("job_name", ["batch/ingest", "batch/hi13-pilot"])
            .gte("started_at", since_30d)
            .order("started_at", desc=True)
            .limit(50)
            .execute()
        )
        for row in runs_res.data or []:
            if is_swept_stale_batch_job_run(row):
                continue
            summary = row.get("summary") or {}
            hi13 = _hi13_from_job_summary(summary)
            recent_runs.append({
                "job_name": row.get("job_name"),
                "started_at": row.get("started_at"),
                "finished_at": row.get("finished_at"),
                "status": row.get("status"),
                "duration_ms": row.get("duration_ms"),
                "error": row.get("error"),
                "hi13": hi13,
                "batch_line_hits": hi13.get("batch_line_ok", 0),
                "sync_fallback": hi13.get("sync_fallback", 0),
                "skipped_duplicate_run": bool(summary.get("skipped_duplicate_run")),
            })
        recent_runs = recent_runs[:25]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"batch_job_runs: {exc}") from exc

    success_rate_30d = (
        round(
            ingest_totals["batch_line_ok"]
            / max(ingest_totals["batch_line_ok"] + ingest_totals["batch_line_fail"], 1),
            4,
        )
    )
    batch_path_share_30d = _hi13_ingest_batch_path_share(ingest_totals)
    gemini_tier_share_7d = _hi13_gemini_tier_share(batch_7d, sync_7d)
    gemini_tier_share_30d = _hi13_gemini_tier_share(batch_30d, sync_30d)

    return JSONResponse({
        "ok": True,
        "as_of": now.isoformat(),
        "config": {
            "enabled": CORPUS_INGEST_USE_GEMINI_BATCH,
            "poll_interval_s": CORPUS_BATCH_POLL_INTERVAL_SEC,
            "poll_max_s": CORPUS_BATCH_POLL_MAX_SEC,
        },
        "gemini_calls": {
            "batch_7d": batch_7d,
            "batch_30d": batch_30d,
            "sync_extraction_7d": sync_7d,
            "sync_extraction_30d": sync_30d,
            "batch_tier_share_7d": gemini_tier_share_7d,
            "batch_tier_share_30d": gemini_tier_share_30d,
        },
        "ingest_30d": {
            **ingest_totals,
            "batch_line_success_rate": success_rate_30d,
            "batch_path_share": batch_path_share_30d,
            "batch_path_share_target": 0.5,
        },
        "recent_runs": recent_runs,
    })


@router.get("/admin/ensemble-credits")
async def admin_ensemble_credits(
    _admin: dict[str, Any] = Depends(require_admin),
    days: int = Query(14, ge=1, le=60),
) -> JSONResponse:
    now = datetime.now(UTC)
    results: list[dict[str, Any]] = []
    for i in range(days):
        day = (now - timedelta(days=i)).date().isoformat()
        try:
            payload = _ensemble_fetch_used_units(day)
            units = _ed_used_units_from_payload(payload)
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

    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
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

    return JSONResponse({"ok": True, "as_of": datetime.now(UTC).isoformat(), "total": total, "days": days, "by_call_site": _group("call_site"), "by_endpoint": _group("endpoint"), "by_request_class": _group("request_class")})


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
    return JSONResponse({"ok": True, "as_of": datetime.now(UTC).isoformat(), "days": days, "entries": entries, "raw": raw})


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

    return JSONResponse({"ok": True, "as_of": datetime.now(UTC).isoformat(), "slack_configured": bool(_SLACK_ADMIN_WEBHOOK_URL), "evaluations": evaluations})


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
    since = datetime.now(UTC) - timedelta(minutes=minutes)
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
            {"id": "ingest", "label": "Corpus ingest (/batch/ingest)", "body_schema": {"niche_ids": "int[] | null", "deep_pool": "bool", "ingest_shift": "a–f | null", "ingest_shift_count": "int 1–6"}, "heavy": True},
            {
                "id": "post_processing",
                "label": "Post-ingest aggregates (/batch/post-processing) — MV, VĐH, Layer0B, Sunday weekly",
                "body_schema": {"weekly_if_sunday": "bool — default true"},
                "heavy": True,
            },
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
            {"id": "layer0", "label": "Layer 0 insights (/batch/layer0)", "body_schema": {}, "heavy": True},
            {
                "id": "assignment_tier_backfill",
                "label": "ACQE assignment tier backfill — legacy NULL tiers + junction repair",
                "body_schema": {
                    "batch_size": "int — default 500",
                    "max_rows": "int — default 15000",
                    "repair_validated_junction": "bool — downgrade validated when junction miss",
                },
                "heavy": True,
            },
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


@router.post(
    "/admin/trigger/morning_ritual",
    summary="Regenerate daily ritual (manual)",
    description=(
        "Same workload as POST /batch/morning-ritual. Omit user_ids to process "
        "every profile: one 3-script bundle per user (single-niche model since 2026-05-05)."
    ),
)
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


@router.post(
    "/admin/backfill-classification",
    summary="ME-17 — Backfill legacy content_context + niche_classification",
    description=(
        "Rows where ``niche_resolution_source`` IS NULL: text-only Gemini over "
        "stored ``analysis_json``. Idempotent — sets ``niche_resolution_source`` "
        "to ``gemini_two_axis``. Same job as POST /admin/trigger/backfill_classification."
    ),
)
async def admin_backfill_classification(
    body: AdminBackfillClassificationBody = AdminBackfillClassificationBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"],
        action="backfill.classification",
        params={
            "batch_size": body.batch_size,
            "max_runtime_s": body.max_runtime_s,
            "dry_run": body.dry_run,
        },
        runner=lambda: _admin_run_backfill_classification(body),
    )


@router.post("/admin/trigger/backfill_classification")
async def admin_trigger_backfill_classification(
    body: AdminBackfillClassificationBody = AdminBackfillClassificationBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    """Alias for ``POST /admin/backfill-classification`` (admin UI trigger id)."""
    return await _run_trigger_with_audit(
        user_id=admin["user_id"],
        action="backfill.classification",
        params={
            "batch_size": body.batch_size,
            "max_runtime_s": body.max_runtime_s,
            "dry_run": body.dry_run,
        },
        runner=lambda: _admin_run_backfill_classification(body),
    )


@router.post("/admin/trigger/cross_niche_remap_backfill")
async def admin_trigger_cross_niche_remap_backfill(
    body: AdminCrossNicheRemapBackfillBody = AdminCrossNicheRemapBackfillBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"],
        action="backfill.cross_niche_remap",
        params={
            "batch_size": body.batch_size,
            "max_runtime_s": body.max_runtime_s,
            "dry_run": body.dry_run,
            "video_ids": body.video_ids,
        },
        runner=lambda: _admin_run_cross_niche_remap_backfill(body),
    )


@router.post("/admin/trigger/assignment_tier_backfill")
async def admin_trigger_assignment_tier_backfill(
    body: AdminAssignmentTierBackfillBody = AdminAssignmentTierBackfillBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"],
        action="backfill.assignment_tier",
        params={
            "batch_size": body.batch_size,
            "max_rows": body.max_rows,
            "repair_validated_junction": body.repair_validated_junction,
        },
        runner=lambda: _admin_run_assignment_tier_backfill(body),
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


@router.post("/admin/trigger/post_processing")
async def admin_trigger_post_processing(
    body: AdminTriggerPostProcessingBody = AdminTriggerPostProcessingBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.post_processing",
        params={"weekly_if_sunday": body.weekly_if_sunday},
        runner=lambda: _admin_run_post_processing(body),
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


@router.post("/admin/trigger/r2_janitor")
async def admin_trigger_r2_janitor(
    body: AdminTriggerR2JanitorBody = AdminTriggerR2JanitorBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    async def runner() -> dict[str, Any]:
        return await _admin_run_r2_janitor(dry_run=body.dry_run)

    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.r2_janitor",
        params={"dry_run": body.dry_run}, runner=runner,
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


@router.post("/admin/trigger/viral_score_backtest")
async def admin_trigger_viral_score_backtest(
    body: AdminTriggerViralScoreBacktestBody = AdminTriggerViralScoreBacktestBody(),
    admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    return await _run_trigger_with_audit(
        user_id=admin["user_id"], action="trigger.viral_score_backtest",
        params={"sample_size": body.sample_size, "seed": body.seed},
        runner=lambda: _admin_run_viral_score_backtest(body),
    )
