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

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
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
    return datetime.now(timezone.utc).date().isoformat()


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
    # Flash-lite — extraction / classification / intent routing.
    "gemini-3-flash-lite-preview": ModelPrice(
        tokens_in_per_mtok=0.075,
        tokens_out_per_mtok=0.30,
    ),
    # Flash — Vietnamese synthesis / diagnosis / creative writing.
    "gemini-3-flash-preview": ModelPrice(
        tokens_in_per_mtok=0.30,
        tokens_out_per_mtok=1.20,
    ),
    # Pro — reserved for eval-only rungs (not used in steady-state prod).
    "gemini-3-pro-preview": ModelPrice(
        tokens_in_per_mtok=1.25,
        tokens_out_per_mtok=5.00,
    ),
}

UNKNOWN_MODEL_PRICE = ModelPrice(0.0, 0.0)


def price_for_model(model_name: str) -> ModelPrice:
    """Strip version/date qualifiers and look up the base model price.

    ``gemini-3-flash-lite-preview-04-2026`` → ``gemini-3-flash-lite-preview``.
    Google occasionally pins dates; stripping them keeps the pricing table
    readable without chasing every minor alias.
    """
    if model_name in MODEL_PRICING_USD_PER_MTOK:
        return MODEL_PRICING_USD_PER_MTOK[model_name]
    # Strip trailing date/version suffix after a fourth hyphen.
    parts = model_name.split("-")
    for cutoff in range(len(parts), 2, -1):
        base = "-".join(parts[:cutoff])
        if base in MODEL_PRICING_USD_PER_MTOK:
            return MODEL_PRICING_USD_PER_MTOK[base]
    logger.info("[gemini_cost] unknown model %s — recording zero cost", model_name)
    return UNKNOWN_MODEL_PRICE


def estimate_cost(
    *,
    model_name: str,
    tokens_in: int,
    tokens_out: int,
) -> float:
    """USD cost for a single ``generate_content`` response."""
    price = price_for_model(model_name)
    return (
        tokens_in * price.tokens_in_per_mtok / 1_000_000
        + tokens_out * price.tokens_out_per_mtok / 1_000_000
    )


def extract_usage(response: Any) -> tuple[int, int]:
    """Pull ``(tokens_in, tokens_out)`` from a genai response.

    The shape is ``response.usage_metadata.prompt_token_count`` and
    ``candidates_token_count``. Either can be missing on error responses
    or fallback models that don't populate usage — defaults to zero.
    """
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return (0, 0)
    tokens_in = int(getattr(meta, "prompt_token_count", 0) or 0)
    tokens_out = int(getattr(meta, "candidates_token_count", 0) or 0)
    return (tokens_in, tokens_out)


# ── Async log writer ─────────────────────────────────────────────────────────
# Fire-and-forget so a transient Supabase blip never blocks the Gemini call.
# Thread-per-insert is pragmatic (no asyncio loop on every caller); the
# writer lives longer than the HTTP response but the Cloud Run container
# drains in-flight threads on shutdown.

def _insert_row(row: dict[str, Any]) -> None:
    try:
        get_service_client().table("gemini_calls").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[gemini_cost] gemini_calls insert failed: %s", exc)


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
) -> float:
    """Insert a ``gemini_calls`` row asynchronously. Returns the computed cost.

    Callers that want the cost for metrics can use the return value directly;
    everyone else can ignore it.

    Failure rows (``success=False``) carry ``error_code`` (exception type
    name) and typically have ``tokens_in=tokens_out=0, duration_ms=<retry
    time>, cost_usd=0``. See ``log_gemini_failure`` for the convenience
    wrapper used by ``gemini.py``'s exhausted-retry path.
    """
    cost_usd = round(estimate_cost(
        model_name=model_name,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    ), 6)

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
    }

    thread = threading.Thread(
        target=_insert_row,
        args=(row,),
        daemon=True,
        name=f"gemini-cost-{call_site}",
    )
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
) -> None:
    """Log a ``gemini_calls`` row for an exhausted-retry failure.

    Called from ``gemini.py`` *only* when all retries + fallback models
    have been exhausted and the caller is about to re-raise. Transient
    hiccups that recover on retry are NOT logged here — they'd make
    the failure-rate panel noisy.

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
    )
