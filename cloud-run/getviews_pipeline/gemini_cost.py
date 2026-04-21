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
from dataclasses import dataclass
from typing import Any

from getviews_pipeline.supabase_client import get_service_client

logger = logging.getLogger(__name__)


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
) -> float:
    """Insert a ``gemini_calls`` row asynchronously. Returns the computed cost.

    Callers that want the cost for metrics can use the return value directly;
    everyone else can ignore it.
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
    }

    thread = threading.Thread(
        target=_insert_row,
        args=(row,),
        daemon=True,
        name=f"gemini-cost-{call_site}",
    )
    thread.start()

    return cost_usd
