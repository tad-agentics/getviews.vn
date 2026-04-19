"""Phase B · B.1.2 — niche benchmark row for /video (niche_intelligence + modeled curve).

`niche_intelligence` is a materialized view (see migrations). This module maps
columns to the `VideoNicheMeta` contract and builds the dashed benchmark curve
using the B.0.1 modeled path (`video_structural.model_niche_benchmark_curve`).

The JSON field ``retention_source`` (``"real"`` | ``"modeled"``) is mirrored into
``POST /video/analyze`` → ``meta.retention_source`` so the SPA can pick the
retention block kicker per ``artifacts/plans/retention-curve-decision.md``.
"""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.video_structural import model_niche_benchmark_curve

logger = logging.getLogger(__name__)

# Default video length for curve shape when caller omits `duration_sec` (UI ref ~58s).
DEFAULT_CURVE_DURATION_SEC = 58.0


def _to_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def count_winners_sample_in_niche_sync(sb: Any, niche_id: int, median_er: float) -> int | None:
    """Corpus rows in ``niche_id`` with ``breakout_multiplier >= 1.5`` OR ``engagement_rate > median_er``."""
    if not niche_id or sb is None:
        return None
    er = float(median_er)
    er_s = f"{er:.10f}".rstrip("0").rstrip(".")
    if er_s == "" or er_s == "-":
        er_s = "0"
    try:
        res = (
            sb.table("video_corpus")
            .select("video_id", count="exact")
            .eq("niche_id", niche_id)
            .or_(f"breakout_multiplier.gte.1.5,engagement_rate.gt.{er_s}")
            .execute()
        )
        return int(res.count or 0)
    except Exception as exc:
        logger.warning("[niche_benchmark] winners_sample count niche=%s: %s", niche_id, exc)
        return None


def niche_row_to_video_meta(row: dict[str, Any]) -> dict[str, Any]:
    """Map `niche_intelligence` MV row → `VideoNicheMeta` shape (api-types.ts)."""
    organic = _to_float(row.get("organic_avg_views"))
    commerce = _to_float(row.get("commerce_avg_views"))
    if organic > 0 and commerce > 0:
        avg_views = int(round((organic + commerce) / 2.0))
    else:
        avg_views = int(round(organic or commerce))

    median_er = _to_float(row.get("median_er"), 0.04)
    # Heuristic until per-video retention telemetry exists: tighter ER → higher
    # assumed watch-through (bounded for UI).
    avg_retention = min(0.92, max(0.28, 0.40 + min(median_er, 0.14) * 3.2))
    # `avg_ctr` in the plan is a compact scalar for cross-niche compare; reuse ER scale.
    avg_ctr = min(0.14, max(0.006, median_er))
    sample_size = _to_int(row.get("sample_size"), 0)

    return {
        "avg_views": avg_views,
        "avg_retention": round(avg_retention, 4),
        "avg_ctr": round(avg_ctr, 5),
        "sample_size": sample_size,
    }


def build_niche_benchmark_payload(
    row: dict[str, Any] | None,
    *,
    niche_id: int,
    duration_sec: float = DEFAULT_CURVE_DURATION_SEC,
    user_sb: Any | None = None,
) -> dict[str, Any]:
    """JSON body for ``GET /video/niche-benchmark``.

    When ``user_sb`` is set, ``niche_meta.winners_sample_size`` counts corpus
    winners in the niche (``breakout_multiplier >= 1.5`` or ``engagement_rate``
    above MV ``median_er``). Otherwise the field is ``None``.
    """
    dur = max(float(duration_sec), 1.0)
    if not row:
        return {
            "niche_id": niche_id,
            "niche_meta": None,
            "niche_benchmark_curve": [],
            "retention_source": "modeled",
            "computed_at": None,
            "reference_duration_sec": dur,
        }

    meta = niche_row_to_video_meta(row)
    median_er = _to_float(row.get("median_er"), 0.04)
    meta["winners_sample_size"] = count_winners_sample_in_niche_sync(user_sb, niche_id, median_er)
    curve = model_niche_benchmark_curve(
        dur,
        niche_median_retention=float(meta["avg_retention"]),
        n_points=20,
    )
    return {
        "niche_id": niche_id,
        "niche_meta": meta,
        "niche_benchmark_curve": curve,
        "retention_source": "modeled",
        "computed_at": row.get("computed_at"),
        "reference_duration_sec": dur,
    }


def fetch_niche_intelligence_sync(sb: Any, niche_id: int) -> dict[str, Any] | None:
    """Blocking fetch of one MV row (call from thread pool or sync context)."""
    try:
        res = (
            sb.table("niche_intelligence")
            .select(
                "niche_id,sample_size,organic_avg_views,commerce_avg_views,"
                "median_er,avg_engagement_rate,computed_at"
            )
            .eq("niche_id", niche_id)
            .execute()
        )
    except Exception as exc:
        logger.warning("[niche_benchmark] select niche=%s failed: %s", niche_id, exc)
        return None
    rows = res.data or []
    return rows[0] if rows and isinstance(rows[0], dict) else None
