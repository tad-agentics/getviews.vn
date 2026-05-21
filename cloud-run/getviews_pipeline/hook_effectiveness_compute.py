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
from datetime import UTC, datetime, timedelta
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
        .select(
            "ingest_loop_niche_id, content_class_id, hook_type, views, engagement_rate, "
            "save_rate, breakout_multiplier, indexed_at"
        )
        .not_.is_("hook_type", None)
        .gte("indexed_at", since.isoformat())
    )
    if until is not None:
        q = q.lt("indexed_at", until.isoformat())
    rows = (q.execute()).data or []
    return [
        r for r in rows
        if isinstance(r, dict)
        and r.get("ingest_loop_niche_id") is not None
        and r.get("hook_type")
    ]


def _bucket_metrics(bucket_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Compute avg_views / avg_engagement_rate / avg_completion_rate for one bucket.

    Returns None when the bucket has zero usable views (every row had
    views=0 — no point storing the row).
    """
    views = []
    for r in bucket_rows:
        v = float(r.get("views") or 0)
        if v <= 0:
            continue
        bm = float(r.get("breakout_multiplier") or 1.0)
        views.append(v * min(max(bm, 1.0), 5.0))
    er = [float(r["engagement_rate"]) for r in bucket_rows if r.get("engagement_rate") is not None]
    sr = [float(r["save_rate"]) for r in bucket_rows if r.get("save_rate") is not None]

    avg_views_val = _mean(views)
    if avg_views_val is None:
        return None

    return {
        "avg_views": int(round(avg_views_val)),
        "avg_engagement_rate": round(_mean(er), 6) if er else None,
        "avg_completion_rate": round(_mean(sr), 6) if sr else None,
        "sample_size": len(bucket_rows),
    }


def _compute_buckets(rows: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    """Group rows by ``(niche_id, hook_type)`` and compute averages.

    Returns one entry per bucket with ``sample_size >= SAMPLE_FLOOR``.
    """
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = (int(r["ingest_loop_niche_id"]), str(r["hook_type"]))
        groups[key].append(r)

    buckets: dict[tuple[int, str], dict[str, Any]] = {}
    for (niche_id, hook_type), bucket_rows in groups.items():
        if len(bucket_rows) < SAMPLE_FLOOR:
            continue
        metrics = _bucket_metrics(bucket_rows)
        if metrics is None:
            continue
        buckets[(niche_id, hook_type)] = {
            "niche_id": niche_id,
            "hook_type": hook_type,
            **metrics,
        }
    return buckets


def _compute_content_class_buckets(
    rows: list[dict[str, Any]],
) -> dict[tuple[int, str], dict[str, Any]]:
    """Group rows by ``(content_class_id, hook_type)``.

    Two-axis A.2.2 (2026-05-15): parallel to ``_compute_buckets`` but
    keyed on ``content_class_id`` so pattern thesis / video diagnosis
    can rank hooks at the (topic × format) granularity. Rows with
    ``content_class_id IS NULL`` are skipped (pre-PR2 corpus); they'll
    fill in once PR2 backfill + ingest classifier catches up.
    """
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        cci = r.get("content_class_id")
        if cci is None:
            continue
        key = (int(cci), str(r["hook_type"]))
        groups[key].append(r)

    buckets: dict[tuple[int, str], dict[str, Any]] = {}
    for (content_class_id, hook_type), bucket_rows in groups.items():
        if len(bucket_rows) < SAMPLE_FLOOR:
            continue
        metrics = _bucket_metrics(bucket_rows)
        if metrics is None:
            continue
        buckets[(content_class_id, hook_type)] = {
            "content_class_id": content_class_id,
            "hook_type": hook_type,
            **metrics,
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
    """Recompute + upsert ``hook_effectiveness`` AND ``content_class_hook_effectiveness``.

    Returns counts for both tables — the two-axis A.2.2 pivot writes
    parallel niche-scoped + content_class-scoped aggregates from a
    single corpus pass so the read layer (A.2.3) can pick the right
    grouping axis based on caller context (e.g. pattern thesis for a
    pasted video uses content_class; pattern thesis for a niche-wide
    query uses niche).
    """
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    now = datetime.now(UTC)
    current_since = now - timedelta(days=WINDOW_DAYS)
    prior_since = now - timedelta(days=WINDOW_DAYS * 2)
    prior_until = current_since

    current_rows = _fetch_corpus_window(client, since=current_since)
    prior_rows = _fetch_corpus_window(client, since=prior_since, until=prior_until)

    # ── Niche-scoped (legacy) ─────────────────────────────────────────
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

    written = 0
    if upsert_rows:
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
    else:
        logger.warning(
            "[hook_effectiveness] 0 niche buckets cleared the sample floor (n_rows=%d)",
            len(current_rows),
        )

    # ── Content-class-scoped (A.2.2 — 2026-05-15) ─────────────────────
    current_cc_buckets = _compute_content_class_buckets(current_rows)
    prior_cc_buckets = _compute_content_class_buckets(prior_rows)

    cc_upsert_rows: list[dict[str, Any]] = []
    for key, bucket in current_cc_buckets.items():
        prior_avg = float((prior_cc_buckets.get(key) or {}).get("avg_views") or 0)
        cc_upsert_rows.append({
            **bucket,
            "trend_direction": _trend_direction(float(bucket["avg_views"]), prior_avg),
            "computed_at": now.isoformat(),
        })

    cc_written = 0
    if cc_upsert_rows:
        try:
            for i in range(0, len(cc_upsert_rows), 200):
                chunk = cc_upsert_rows[i:i + 200]
                client.table("content_class_hook_effectiveness").upsert(
                    chunk,
                    on_conflict="content_class_id,hook_type",
                ).execute()
                cc_written += len(chunk)
            logger.info(
                "[hook_effectiveness] content_class upserted %d rows (current=%d prior=%d)",
                cc_written, len(current_cc_buckets), len(prior_cc_buckets),
            )
        except Exception as exc:
            # Migration 20260515000000 may not yet be applied on this DB
            # (deploy gap window). Log + continue — niche-scoped path
            # already succeeded so the cron isn't a total wash.
            logger.warning(
                "[hook_effectiveness] content_class upsert failed (acceptable "
                "if migration 20260515000000 not yet applied): %s",
                exc,
            )
    else:
        logger.info(
            "[hook_effectiveness] 0 content_class buckets cleared the sample floor "
            "(n_rows=%d, content_class_id null on most rows pre-PR2 backfill?)",
            len(current_rows),
        )

    return {
        "upserted": written,
        "current_buckets": len(current_buckets),
        "prior_buckets": len(prior_buckets),
        "content_class_upserted": cc_written,
        "content_class_current_buckets": len(current_cc_buckets),
        "content_class_prior_buckets": len(prior_cc_buckets),
    }
