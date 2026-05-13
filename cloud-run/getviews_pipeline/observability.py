"""Phase 2.2 — Structured JSON log helpers for Cloud Logging.

All diagnosis events are emitted here with a consistent schema so Cloud
Logging dashboards can chart cache hit rates, Gemini cost savings, and
per-session latency without ad-hoc log parsing.

Usage::

    from getviews_pipeline.observability import log_diagnosis_event, log_cache_event

    # At the end of run_video_diagnosis:
    log_diagnosis_event(
        request_id=session_id,
        video_id=aweme_id,
        duration_ms=elapsed_ms,
        gemini_cost_usd=cost,
        cache_source="fresh",
        content_format=content_format,
        niche_id=niche_id,
    )

Cloud Logging query to chart cache savings::

    jsonPayload.event="diagnosis_completed"
    | sum(jsonPayload.gemini_cost_saved_usd) group by jsonPayload.cache_source
"""

from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

CacheSource = Literal["on_demand_cache", "corpus_diagnostics_cache", "fresh"]


def log_diagnosis_event(
    *,
    request_id: str | None,
    video_id: str | None,
    duration_ms: int,
    gemini_cost_usd: float = 0.0,
    gemini_cost_saved_usd: float = 0.0,
    cache_source: CacheSource = "fresh",
    content_format: str | None = None,
    niche_id: int | None = None,
    performance_tier: str | None = None,
    success: bool = True,
    error: str | None = None,
) -> None:
    """Structured log for a completed video diagnosis.

    Every diagnosis — cache hit or full pipeline — emits one of these so
    Cloud Logging can chart:
    - ``cache_hit_rate`` by ``cache_source``
    - ``sum(gemini_cost_saved_usd)`` to validate cache ROI
    - ``p50/p95 duration_ms`` by ``content_format``
    """
    logger.info(
        "diagnosis_completed",
        extra={
            "event": "diagnosis_completed",
            "request_id": request_id,
            "video_id": video_id,
            "duration_ms": duration_ms,
            "gemini_cost_usd": gemini_cost_usd,
            "gemini_cost_saved_usd": gemini_cost_saved_usd,
            "cache_source": cache_source,
            "content_format": content_format,
            "niche_id": niche_id,
            "performance_tier": performance_tier,
            "success": success,
            "error": error,
        },
    )


def log_cache_event(
    *,
    event: str,
    cache_source: CacheSource,
    video_id: str | None = None,
    request_id: str | None = None,
    ttl_remaining_sec: float | None = None,
    gemini_cost_saved_usd: float = 0.0,
) -> None:
    """Structured log for cache hits and misses.

    Events:
    - ``cache_hit``: cache was used, Gemini skipped
    - ``cache_miss``: cache miss, Gemini call required
    - ``cache_write``: new diagnosis written to cache
    """
    logger.info(
        event,
        extra={
            "event": event,
            "cache_source": cache_source,
            "video_id": video_id,
            "request_id": request_id,
            "ttl_remaining_sec": ttl_remaining_sec,
            "gemini_cost_saved_usd": gemini_cost_saved_usd,
        },
    )


def log_pipeline_step(
    *,
    step: str,
    request_id: str | None,
    video_id: str | None = None,
    duration_ms: int | None = None,
    extra: dict | None = None,
) -> None:
    """Structured log for pipeline steps (frame extraction, corpus lookup, etc.)."""
    payload: dict = {
        "event": "pipeline_step",
        "step": step,
        "request_id": request_id,
        "video_id": video_id,
    }
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    if extra:
        payload.update(extra)
    logger.info(step, extra=payload)


# ── Phase 5.8 — cache observability metrics ───────────────────────────────────
#
# Each function emits one structured log entry.  Cloud Logging dashboards
# can filter on `jsonPayload.metric` and chart trends without custom agents.
#
# Required metrics (plan §5.8):
#   cache_hit_rate         → use log_cache_event (already emitted on hit/write)
#   gemini_cost_saved_usd  → already in log_cache_event + log_diagnosis_event
#   corpus_growth_via_users→ log_corpus_growth_event
#   channel_dedup_hit_rate → log_channel_cache_event
#   sse_drop_rate          → log_sse_event (existing SSE error handling)
#   tiktok_url_normalize_collision_rate → log_url_normalize_event


def log_corpus_growth_event(
    *,
    video_id: str,
    ingest_source: str,
    quality_tier: str,
    views: int,
    niche_id: int | None = None,
    action: str = "promoted",
) -> None:
    """Phase 5.8 — corpus growth via user diagnoses.

    Emitted when ``promote_on_demand_to_corpus`` successfully writes a row.
    Cloud Logging query to chart corpus growth rate from users::

        jsonPayload.metric="corpus_growth"
        | count() group by jsonPayload.ingest_source, jsonPayload.quality_tier
    """
    logger.info(
        "corpus_growth",
        extra={
            "metric": "corpus_growth",
            "event": "corpus_growth",
            "video_id": video_id,
            "ingest_source": ingest_source,
            "quality_tier": quality_tier,
            "views": views,
            "niche_id": niche_id,
            "action": action,
        },
    )


def log_channel_cache_event(
    *,
    event: str,
    handle: str,
    cache_age_sec: float | None = None,
) -> None:
    """Phase 5.8 — channel snapshot cache hit/miss.

    Events:
    - ``channel_cache_hit``: channel context served from in-process cache.
    - ``channel_cache_miss``: Supabase query required.

    Cloud Logging query to chart channel dedup hit rate::

        jsonPayload.metric="channel_cache"
        | count() group by jsonPayload.event
    """
    logger.info(
        event,
        extra={
            "metric": "channel_cache",
            "event": event,
            "handle": handle,
            "cache_age_sec": cache_age_sec,
        },
    )


def log_url_normalize_event(
    *,
    raw_url: str,
    canonical_url: str,
    was_normalized: bool,
) -> None:
    """Phase 5.8 — URL normalization collision metric.

    Emitted when ``normalize_tiktok_url`` produces a canonical URL that
    differs from the raw input (collision = variant resolved to existing key).

    Cloud Logging query::

        jsonPayload.metric="url_normalize"
        | count() group by jsonPayload.was_normalized
    """
    logger.info(
        "url_normalize",
        extra={
            "metric": "url_normalize",
            "event": "url_normalize",
            "was_normalized": was_normalized,
            "raw_url": raw_url[:200],
            "canonical_url": canonical_url[:200],
        },
    )
