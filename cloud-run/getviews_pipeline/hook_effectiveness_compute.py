"""Weekly batch — aggregate ``hook_effectiveness`` from ``video_corpus``.

Unblocks Pattern + Ideas reports. Before this module, the
``hook_effectiveness`` table had **0 rows in production** — see
``artifacts/docs/state-of-corpus.md`` Appendix B Gap 1. Pattern's
``load_pattern_inputs`` + Ideas' ``load_ideas_inputs`` both query this
table and, on empty result, ``rank_hooks_for_pattern([])`` returns an
empty list → Pattern / Ideas reports render with zero hook findings.

What this computes, per ``(niche_id, hook_type)``:

  - ``avg_views``              — mean of ``video_corpus.views``
  - ``avg_engagement_rate``    — mean of ``video_corpus.engagement_rate``
  - ``avg_completion_rate``    — mean of ``video_corpus.save_rate``
    (schema column is misnamed: "completion" but we use save rate as
    the retention proxy since per-video retention isn't stored. The
    Pattern reader's ``_score_row`` weights this field, so keeping it
    populated matters for ranking.)
  - ``sample_size``            — videos in the bucket
  - ``trend_direction``        — ``rising | stable | declining`` by
    comparing current 30d ``avg_views`` to prior 30d ``avg_views``.

Upserts on ``(niche_id, hook_type)``. Buckets with fewer than
``SAMPLE_FLOOR = 3`` videos in the current window are skipped — too
few samples to support downstream "bold_claim is #1 hook in Skincare"
claims.

The raw per-video rates (``engagement_rate``, ``save_rate``) are
already computed at ingest time in ``corpus_ingest.py``. We average
those instead of recomputing from ``likes / views``, so any ingest-
time normalisation stays authoritative.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Minimum videos per (niche, hook) bucket before we surface the aggregate.
# 3 is permissive — the downstream claim-tier gate in ``claim_tiers.py``
# applies a stricter 50-sample requirement before the hook_effectiveness
# tier is citable. This floor just drops the noisiest buckets so we don't
# store rows that'd immediately be filtered out downstream.
SAMPLE_FLOOR = 3

# Rolling window for the current aggregate. 30 days matches the
# ``niche_intelligence`` materialised view window so the two aggregates
# stay comparable.
WINDOW_DAYS = 30

# Trend-direction thresholds: how much does ``avg_views`` need to move
# week-over-week to count as a direction change?
TREND_RISING_PCT = 0.10      # +10% → rising
TREND_DECLINING_PCT = -0.10  # -10% → declining


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _fetch_corpus_window(
    client: Any,
    since: datetime,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    """Pull the rows needed for aggregation — narrow column list."""
    q = (
        client.table("video_corpus")
        .select("niche_id, hook_type, views, engagement_rate, save_rate, indexed_at")
        .not_.is_("hook_type", None)
        .gte("indexed_at", since.isoformat())
    )
    if until is not None:
        q = q.lt("indexed_at", until.isoformat())
    rows = (q.execute()).data or []
    return [
        r for r in rows
        if isinstance(r, dict)
        and r.get("niche_id") is not None
        and r.get("hook_type")
    ]


def _compute_buckets(rows: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    """Group rows by ``(niche_id, hook_type)`` and compute averages.

    Returns one entry per bucket with ``sample_size >= SAMPLE_FLOOR``.
    ``views`` → ``avg_views`` (int); ``engagement_rate`` + ``save_rate``
    are averaged and stored under ``avg_engagement_rate`` +
    ``avg_completion_rate`` respectively.
    """
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = (int(r["niche_id"]), str(r["hook_type"]))
        groups[key].append(r)

    buckets: dict[tuple[int, str], dict[str, Any]] = {}
    for (niche_id, hook_type), bucket_rows in groups.items():
        if len(bucket_rows) < SAMPLE_FLOOR:
            continue

        views = [float(r.get("views") or 0) for r in bucket_rows if (r.get("views") or 0) > 0]
        er = [float(r["engagement_rate"]) for r in bucket_rows if r.get("engagement_rate") is not None]
        sr = [float(r["save_rate"]) for r in bucket_rows if r.get("save_rate") is not None]

        avg_views_val = _mean(views)
        if avg_views_val is None:
            # Every row had 0 views — don't store the bucket.
            continue

        buckets[(niche_id, hook_type)] = {
            "niche_id": niche_id,
            "hook_type": hook_type,
            "avg_views": int(round(avg_views_val)),
            "avg_engagement_rate": round(_mean(er), 6) if er else None,
            "avg_completion_rate": round(_mean(sr), 6) if sr else None,
            "sample_size": len(bucket_rows),
        }
    return buckets


def _trend_direction(current_avg: float, prior_avg: float) -> str:
    """Classify week-over-week ``avg_views`` change.

    Returns ``"stable"`` when prior is zero / missing so a brand-new
    bucket doesn't claim a direction it can't justify.
    """
    if prior_avg <= 0:
        return "stable"
    delta = (current_avg - prior_avg) / prior_avg
    if delta > TREND_RISING_PCT:
        return "rising"
    if delta < TREND_DECLINING_PCT:
        return "declining"
    return "stable"


def run_hook_effectiveness(client: Any | None = None) -> dict[str, Any]:
    """Recompute + upsert the ``hook_effectiveness`` table.

    Returns ``{"upserted": int, "current_buckets": int, "prior_buckets": int}``
    — the two counts diverging signals which buckets newly crossed the
    sample floor (or fell off it) this week.
    """
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    now = datetime.now(timezone.utc)
    current_since = now - timedelta(days=WINDOW_DAYS)
    prior_since = now - timedelta(days=WINDOW_DAYS * 2)
    prior_until = current_since

    current_rows = _fetch_corpus_window(client, since=current_since)
    prior_rows = _fetch_corpus_window(client, since=prior_since, until=prior_until)

    current_buckets = _compute_buckets(current_rows)
    prior_buckets = _compute_buckets(prior_rows)

    upsert_rows: list[dict[str, Any]] = []
    for key, bucket in current_buckets.items():
        prior_avg = float((prior_buckets.get(key) or {}).get("avg_views") or 0)
        upsert_rows.append({
            **bucket,
            "trend_direction": _trend_direction(float(bucket["avg_views"]), prior_avg),
            "computed_at": now.isoformat(),
        })

    if not upsert_rows:
        logger.warning(
            "[hook_effectiveness] 0 buckets cleared the sample floor (n_rows=%d)",
            len(current_rows),
        )
        return {
            "upserted": 0,
            "current_buckets": 0,
            "prior_buckets": len(prior_buckets),
        }

    # Chunk the upserts — 200/request is well under Supabase PostgREST
    # defaults and matches the existing batch-job patterns.
    written = 0
    for i in range(0, len(upsert_rows), 200):
        chunk = upsert_rows[i:i + 200]
        client.table("hook_effectiveness").upsert(
            chunk,
            on_conflict="niche_id,hook_type",
        ).execute()
        written += len(chunk)

    logger.info(
        "[hook_effectiveness] upserted %d rows (current=%d prior=%d)",
        written, len(current_buckets), len(prior_buckets),
    )
    return {
        "upserted": written,
        "current_buckets": len(current_buckets),
        "prior_buckets": len(prior_buckets),
    }
