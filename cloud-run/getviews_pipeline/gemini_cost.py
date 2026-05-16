"""Phase D.5.1 — Gemini token pricing + async cost logging.

Two responsibilities:

1. ``estimate_cost`` — convert a ``usage_metadata`` object from a
   ``generate_content`` response into a USD dollar amount, routing through
   ``MODEL_PRICING_USD_PER_MTOK`` keyed by model family. When a response
   arrives from a fallback model we still attribute it to the actual model
   that served the request, so the dashboard can spot prod/preview cost
   drift per model.

2. ``log_gemini_call`` — fire-and-forget insert into ``gemini_calls``
   (plus a summary row into ``usage_events`` so the analytics dashboard
   can join without reading the raw cost table). Inserted via
   ``service_role`` so Row-Level Security is bypassed; never surfaces on
   the client bundle.

Pricing data lives in-process because:
  a) every Gemini 3.x preview we bill at is published; there's no live
     price API to call.
  b) keeping it out of the DB means cost audits don't depend on a
     migration having landed first.
Update the table below whenever Google ships a new Gemini 3.x preview or
adjusts per-mtok pricing — the function signature never needs to change.
"""

from __future__ import annotations

import atexit
import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from getviews_pipeline.supabase_client import get_service_client

logger = logging.getLogger(__name__)


# ── Daily USD ceiling (B3) ────────────────────────────────────────────
# Global per-day spend guard backed by ``gemini_calls.cost_usd``. Pre-call
# check so a runaway batch can't exceed the documented ~$70/mo target.
# Configured by GEMINI_DAILY_USD_MAX (0 = unlimited) and
# GEMINI_DAILY_USD_ENFORCE (false = log-only).


class GeminiDailyBudgetExceeded(RuntimeError):
    """Raised when today's gemini_calls.cost_usd sum is at/over the ceiling."""


_DAILY_USD_LOCK = threading.Lock()
_DAILY_USD_CACHE: dict[str, float] = {}     # utc_date_iso → cost_usd
_DAILY_USD_FETCHED_AT: dict[str, float] = {}  # utc_date_iso → monotonic seconds


def _today_utc_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _fetch_today_cost_usd(today_iso: str) -> float:
    """Sum gemini_calls.cost_usd for today (UTC). Best-effort — returns 0
    on any failure so a transient DB blip doesn't block production."""
    try:
        # `gte` on created_at uses the UTC date boundary. cost_usd is a
        # `numeric`; Supabase REST returns strings, so coerce defensively.
        res = (
            get_service_client()
            .table("gemini_calls")
            .select("cost_usd")
            .gte("created_at", f"{today_iso}T00:00:00Z")
            .execute()
        )
        rows = res.data or []
        return float(sum(float(r.get("cost_usd") or 0) for r in rows))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[gemini_cost] daily-budget read failed: %s", exc)
        return 0.0


def get_today_cost_usd(*, force_refresh: bool = False) -> float:
    """Cached daily Gemini spend (USD). Refreshed every
    ``GEMINI_DAILY_USD_CACHE_SEC`` seconds per UTC day."""
    from getviews_pipeline.config import GEMINI_DAILY_USD_CACHE_SEC

    today_iso = _today_utc_iso()
    now = time.monotonic()
    with _DAILY_USD_LOCK:
        cached = _DAILY_USD_CACHE.get(today_iso)
        fetched_at = _DAILY_USD_FETCHED_AT.get(today_iso, 0.0)
        fresh = (
            cached is not None
            and not force_refresh
            and (now - fetched_at) < GEMINI_DAILY_USD_CACHE_SEC
        )
        if fresh:
            return cached  # type: ignore[return-value]
    # Fetch outside the lock so a slow DB call doesn't block other threads.
    fetched = _fetch_today_cost_usd(today_iso)
    with _DAILY_USD_LOCK:
        _DAILY_USD_CACHE[today_iso] = fetched
        _DAILY_USD_FETCHED_AT[today_iso] = now
        # Drop yesterday's cache entries — small hygiene so the dict
        # doesn't grow unbounded across day rollovers.
        for stale in list(_DAILY_USD_CACHE):
            if stale != today_iso:
                _DAILY_USD_CACHE.pop(stale, None)
                _DAILY_USD_FETCHED_AT.pop(stale, None)
    return fetched


def check_gemini_daily_budget(call_site: str) -> None:
    """Pre-call guard. Raises ``GeminiDailyBudgetExceeded`` when today's
    spend has hit ``GEMINI_DAILY_USD_MAX`` and enforcement is on; logs a
    warning otherwise. No-op when the cap is 0 (disabled)."""
    from getviews_pipeline.config import (
        GEMINI_DAILY_USD_ENFORCE,
        GEMINI_DAILY_USD_MAX,
    )

    if GEMINI_DAILY_USD_MAX <= 0:
        return
    today_usd = get_today_cost_usd()
    if today_usd < GEMINI_DAILY_USD_MAX:
        return
    msg = (
        f"[gemini_cost] daily Gemini spend ${today_usd:.4f} >= "
        f"cap ${GEMINI_DAILY_USD_MAX:.4f} (call_site={call_site!r})"
    )
    if GEMINI_DAILY_USD_ENFORCE:
        logger.error("%s — refusing call", msg)
        raise GeminiDailyBudgetExceeded(msg)
    logger.warning("%s — log-only (set GEMINI_DAILY_USD_ENFORCE=true to block)", msg)


@dataclass(frozen=True)
class ModelPrice:
    """Per-million-token pricing in USD. Gemini 3.x tiers as of 2026-04."""
    tokens_in_per_mtok: float
    tokens_out_per_mtok: float


# Prices align with artifacts/plans/phase-d-gemini-cost-audit.md. Anything
# not in this table falls through to UNKNOWN_MODEL_PRICE (zero cost, but
# still records the row — undercount is preferred over a noisy log).
MODEL_PRICING_USD_PER_MTOK: dict[str, ModelPrice] = {
    # Flash-Lite stable (GA 2026-05-07) — steady-state default for extraction,
    # classification, intent routing, and synthesis.
    # Official pricing: $0.25/M in, $1.50/M out (text/image/video).
    # Source: https://ai.google.dev/gemini-api/docs/pricing#gemini-3.1-flash-lite
    "gemini-3.1-flash-lite": ModelPrice(
        tokens_in_per_mtok=0.25,
        tokens_out_per_mtok=1.50,
    ),
    # Preview aliases kept for historical cost-attribution of rows logged
    # before the GA cutover — same price tier as stable.
    "gemini-3.1-flash-lite-preview": ModelPrice(
        tokens_in_per_mtok=0.25,
        tokens_out_per_mtok=1.50,
    ),
    "gemini-3-flash-lite-preview": ModelPrice(
        tokens_in_per_mtok=0.25,
        tokens_out_per_mtok=1.50,
    ),
    # Flash — kept for any residual synthesis calls during migration.
    # Official pricing: $0.50/M in, $3.00/M out.
    # Source: https://ai.google.dev/gemini-api/docs/pricing#gemini-3-flash-preview
    "gemini-3.1-flash": ModelPrice(
        tokens_in_per_mtok=0.50,
        tokens_out_per_mtok=3.00,
    ),
    "gemini-3.1-flash-preview": ModelPrice(
        tokens_in_per_mtok=0.50,
        tokens_out_per_mtok=3.00,
    ),
    "gemini-3-flash-preview": ModelPrice(
        tokens_in_per_mtok=0.50,
        tokens_out_per_mtok=3.00,
    ),
    # Pro — reserved for eval-only rungs (not used in steady-state prod).
    "gemini-3-pro-preview": ModelPrice(
        tokens_in_per_mtok=1.25,
        tokens_out_per_mtok=5.00,
    ),
}

UNKNOWN_MODEL_PRICE = ModelPrice(0.0, 0.0)

# Context-cached prompt tokens bill at a fraction of standard input price
# (Gemini 3.x developer pricing table — verify periodically).
# Billable input tokens equivalent: (tokens_in - cached) + cached * this fraction.
GEMINI_CACHED_PROMPT_COST_FRACTION = 0.25


def price_for_model(model_name: str, *, batch: bool = False) -> ModelPrice:
    """Strip version/date qualifiers and look up the base model price.

    ``gemini-3-flash-lite-preview-04-2026`` → ``gemini-3-flash-lite-preview``.
    Google occasionally pins dates; stripping them keeps the pricing table
    readable without chasing every minor alias.

    ``batch=True`` applies the published ~50% Batch API multiplier to the
    resolved tier (flash-lite standard $0.25/$1.50 → batch $0.125/$0.75).
    """
    if model_name in MODEL_PRICING_USD_PER_MTOK:
        p = MODEL_PRICING_USD_PER_MTOK[model_name]
    else:
        p = None
        parts = model_name.split("-")
        for cutoff in range(len(parts), 2, -1):
            base = "-".join(parts[:cutoff])
            if base in MODEL_PRICING_USD_PER_MTOK:
                p = MODEL_PRICING_USD_PER_MTOK[base]
                break
        if p is None:
            logger.info("[gemini_cost] unknown model %s — recording zero cost", model_name)
            p = UNKNOWN_MODEL_PRICE
    if not batch:
        return p
    return ModelPrice(
        tokens_in_per_mtok=p.tokens_in_per_mtok * 0.5,
        tokens_out_per_mtok=p.tokens_out_per_mtok * 0.5,
    )


def estimate_cost(
    *,
    model_name: str,
    tokens_in: int,
    tokens_out: int,
    batch: bool = False,
    cached_prompt_tokens: int = 0,
) -> float:
    """USD cost for a single ``generate_content`` or batch-line response.

    When ``cached_prompt_tokens > 0`` (subset of ``tokens`` billed at context-cache
    rate), input cost uses ``GEMINI_CACHED_PROMPT_COST_FRACTION`` for that slice.
    """
    price = price_for_model(model_name, batch=batch)
    c = max(0, min(int(cached_prompt_tokens), int(tokens_in)))
    frac = GEMINI_CACHED_PROMPT_COST_FRACTION
    billable_in_tokens = float(tokens_in - c) + float(c) * frac
    return (
        billable_in_tokens * price.tokens_in_per_mtok / 1_000_000
        + tokens_out * price.tokens_out_per_mtok / 1_000_000
    )


def extract_usage_detail(response: Any) -> tuple[int, int, int]:
    """``(tokens_in, tokens_out, cached_content_token_count)`` from a genai response.

    ``cached_content_token_count`` comes from ``cached_content_token_count`` on
    usage metadata (HI-8 explicit cache verification). Defaults to 0 when absent.

    ``thoughts_token_count`` is folded into ``tokens_out`` (output rate).
    """
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return (0, 0, 0)
    tokens_in = int(getattr(meta, "prompt_token_count", 0) or 0)
    tokens_out = int(getattr(meta, "candidates_token_count", 0) or 0)
    tokens_thoughts = int(getattr(meta, "thoughts_token_count", 0) or 0)
    tcached = int(getattr(meta, "cached_content_token_count", 0) or 0)
    return (tokens_in, tokens_out + tokens_thoughts, tcached)


def extract_usage(response: Any) -> tuple[int, int]:
    """Backward-compatible ``(tokens_in, tokens_out)`` — ignores cache token split."""
    tin, tout, _ = extract_usage_detail(response)
    return (tin, tout)


# ── Async log writer ─────────────────────────────────────────────────────────
# Fire-and-forget so a transient Supabase blip never blocks the Gemini call.
# Track daemon threads so atexit can join briefly under Cloud Run SIGTERM
# (10s grace) — CR-4.

_PENDING_GEMINI_CALL_THREADS: set[threading.Thread] = set()
_PENDING_GEMINI_CALL_THREADS_LOCK = threading.Lock()


def _drain_gemini_cost_log_threads() -> None:
    """Best-effort join of pending ``gemini_calls`` insert threads (~8s budget)."""
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        with _PENDING_GEMINI_CALL_THREADS_LOCK:
            alive = [t for t in _PENDING_GEMINI_CALL_THREADS if t.is_alive()]
        if not alive:
            return
        for t in alive:
            t.join(timeout=0.25)
    with _PENDING_GEMINI_CALL_THREADS_LOCK:
        still = sum(1 for t in _PENDING_GEMINI_CALL_THREADS if t.is_alive())
    if still:
        logger.warning(
            "[gemini_cost] atexit drain: %d insert thread(s) still alive after 8s",
            still,
        )


atexit.register(_drain_gemini_cost_log_threads)


def _insert_row(row: dict[str, Any]) -> None:
    try:
        get_service_client().table("gemini_calls").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[gemini_cost] gemini_calls insert failed: %s", exc)


def _gemini_cost_insert_task(row: dict[str, Any]) -> None:
    try:
        _insert_row(row)
    finally:
        with _PENDING_GEMINI_CALL_THREADS_LOCK:
            _PENDING_GEMINI_CALL_THREADS.discard(threading.current_thread())


def log_gemini_call(
    *,
    user_id: str | None,
    call_site: str,
    model_name: str,
    tokens_in: int,
    tokens_out: int,
    duration_ms: int,
    session_id: str | None = None,
    success: bool = True,
    error_code: str | None = None,
    used_context_cache: bool | None = None,
    cached_content_token_count: int = 0,
    gcp_stt_cost_usd: float | None = None,
    is_batch: bool = False,
) -> float:
    """Insert a ``gemini_calls`` row asynchronously. Returns the computed cost.

    Callers that want the cost for metrics can use the return value directly;
    everyone else can ignore it.

    Failure rows (``success=False``) carry ``error_code`` (exception type
    name) and typically have ``tokens_in=tokens_out=0, duration_ms=<retry
    time>, cost_usd=0``. See ``log_gemini_failure`` for the convenience
    wrapper used by ``gemini.py``'s exhausted-retry path.

    ``cached_content_token_count`` — subset of ``tokens_in`` billed at the
    context-cache rate (HI-8); forwarded to ``estimate_cost`` and
    ``gemini_calls.cached_content_token_count``.
    """
    c_cache = max(0, int(cached_content_token_count))
    if c_cache > 0:
        used_context_cache = True
    cost_usd = round(estimate_cost(
        model_name=model_name,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        batch=is_batch,
        cached_prompt_tokens=c_cache,
    ), 6)

    # Structured log — queryable in Cloud Logging.
    # Build a Cloud Logging dashboard with:
    #   jsonPayload.event="gemini_call" AND jsonPayload.success=true
    # to chart sum(jsonPayload.cost_usd) by jsonPayload.model_name.
    log_extra: dict[str, Any] = {
        "event": "gemini_call",
        "call_site": call_site,
        "model_name": model_name,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cached_content_token_count": c_cache,
        "cost_usd": cost_usd,
        "duration_ms": duration_ms,
        "session_id": session_id,
        "success": success,
        "error_code": error_code,
    }
    if used_context_cache is not None:
        log_extra["used_context_cache"] = used_context_cache
    if gcp_stt_cost_usd is not None:
        log_extra["gcp_stt_cost_usd"] = gcp_stt_cost_usd
    logger.info(
        "gemini_call",
        extra=log_extra,
    )

    row = {
        "user_id": user_id,
        "call_site": call_site,
        "model_name": model_name,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "duration_ms": duration_ms,
        "session_id": session_id,
        "success": success,
        "error_code": error_code,
        "is_batch": is_batch,
        "cached_content_token_count": c_cache,
    }
    if gcp_stt_cost_usd is not None:
        row["gcp_stt_cost_usd"] = gcp_stt_cost_usd

    thread = threading.Thread(
        target=_gemini_cost_insert_task,
        args=(row,),
        daemon=True,
        name=f"gemini-cost-{call_site}",
    )
    with _PENDING_GEMINI_CALL_THREADS_LOCK:
        _PENDING_GEMINI_CALL_THREADS.add(thread)
    thread.start()

    return cost_usd


def log_gemini_failure(
    *,
    user_id: str | None,
    call_site: str,
    model_name: str,
    exc: BaseException,
    duration_ms: int,
    session_id: str | None = None,
    gcp_stt_cost_usd: float | None = None,
    is_batch: bool = False,
) -> None:
    """Log a ``gemini_calls`` row for an exhausted-retry failure.

    Called from ``gemini.py`` when all retries + fallback models have been
    exhausted and the caller is about to re-raise. Transient errors that
    recover on a later attempt are logged separately (ME-15) as
    ``success=False`` rows with ``error_code`` like ``..._attempt_N`` and
    zero tokens — only the final exhaustion uses this helper.

    Writes ``tokens_in=tokens_out=cost_usd=0``, ``duration_ms`` = total
    elapsed time across retries for this model (caller-provided),
    ``error_code`` = exception class name.
    """
    log_gemini_call(
        user_id=user_id,
        call_site=call_site,
        model_name=model_name,
        tokens_in=0,
        tokens_out=0,
        duration_ms=duration_ms,
        session_id=session_id,
        success=False,
        error_code=type(exc).__name__,
        gcp_stt_cost_usd=gcp_stt_cost_usd,
        is_batch=is_batch,
    )
