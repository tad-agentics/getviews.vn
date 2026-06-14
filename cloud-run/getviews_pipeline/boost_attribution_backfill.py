"""One-shot boost_attribution backfill for legacy ``unknown`` corpus rows."""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.corpus_boost_suspect import BoostPercentiles, classify_boost_suspect
from getviews_pipeline.corpus_windows import corpus_benchmark_window_days
from getviews_pipeline.postgrest_time import indexed_at_cutoff_iso

logger = logging.getLogger(__name__)

_BACKFILL_SELECT = (
    "video_id, views, engagement_rate, comments, boost_attribution, reference_eligible"
)


def _percentiles_from_rows(rows: list[dict[str, Any]]) -> BoostPercentiles:
    views: list[float] = []
    comment_rates: list[float] = []
    ers: list[float] = []
    for row in rows:
        v = float(row.get("views") or 0)
        if v <= 0:
            continue
        views.append(v)
        ers.append(float(row.get("engagement_rate") or 0))
        comment_rates.append(float(row.get("comments") or 0) / v)

    if not views:
        return BoostPercentiles(thin=True)

    def _pct(vals: list[float], p: float) -> float:
        s = sorted(vals)
        idx = int((len(s) - 1) * p)
        return s[idx]

    return BoostPercentiles(
        sample_size=len(rows),
        p10_comment_rate=_pct(comment_rates, 0.10) or 0.001,
        p25_er=_pct(ers, 0.25) or 2.0,
        p75_views=_pct(views, 0.75) or 10_000.0,
        p90_views=_pct(views, 0.90) or 50_000.0,
        thin=len(rows) < 50,
    )


def run_boost_attribution_backfill_sync(
    client: Any,
    *,
    limit: int = 0,
    dry_run: bool = False,
) -> dict[str, int]:
    """Reclassify ``unknown`` rows using global trailing-corpus percentiles.

    Mirrors ``classify_boost_suspect`` from batch ingest (§4.7 M1). Idempotent
    for rows already ``organic_confident`` / ``suspect_*``.
    """
    days = corpus_benchmark_window_days()
    cutoff = indexed_at_cutoff_iso(days)

    pct_res = (
        client.table("video_corpus")
        .select("views, engagement_rate, comments")
        .eq("content_type", "video")
        .gt("views", 0)
        .gte("indexed_at", cutoff)
        .execute()
    )
    percentiles = _percentiles_from_rows(list(pct_res.data or []))

    q = (
        client.table("video_corpus")
        .select(_BACKFILL_SELECT)
        .eq("content_type", "video")
        .gt("views", 0)
        .gte("indexed_at", cutoff)
        .in_("boost_attribution", ["unknown", ""])
    )
    if limit > 0:
        q = q.limit(limit)
    rows = list(q.execute().data or [])

    stats = {
        "scanned": len(rows),
        "updated": 0,
        "organic_confident": 0,
        "suspect_low": 0,
        "suspect_medium": 0,
        "dry_run": int(dry_run),
    }
    if not rows:
        return stats

    updates: list[dict[str, Any]] = []
    for row in rows:
        views = int(row.get("views") or 0)
        comments = int(row.get("comments") or 0)
        er = float(row.get("engagement_rate") or 0)
        result = classify_boost_suspect(
            views=views,
            er=er,
            comments=comments,
            percentiles=percentiles,
            hard_reject_enabled=False,
        )
        stats[result.attribution] = stats.get(result.attribution, 0) + 1
        updates.append(
            {
                "video_id": row["video_id"],
                "boost_attribution": result.attribution,
                "reference_eligible": result.reference_eligible,
            }
        )

    if dry_run:
        logger.info("[boost_backfill] dry_run — would update %d rows", len(updates))
        return stats

    chunk = 200
    for start in range(0, len(updates), chunk):
        batch = updates[start : start + chunk]
        client.table("video_corpus").upsert(batch, on_conflict="video_id").execute()
        stats["updated"] += len(batch)

    logger.info(
        "[boost_backfill] updated %d rows (organic=%d suspect_low=%d suspect_medium=%d)",
        stats["updated"],
        stats.get("organic_confident", 0),
        stats.get("suspect_low", 0),
        stats.get("suspect_medium", 0),
    )
    return stats
