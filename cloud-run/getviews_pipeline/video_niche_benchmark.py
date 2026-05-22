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
            .eq("ingest_loop_niche_id", niche_id)
            .or_(f"breakout_multiplier.gte.1.5,engagement_rate.gt.{er_s}")
            .execute()
        )
        return int(res.count or 0)
    except Exception as exc:
        logger.warning("[niche_benchmark] winners_sample count niche=%s: %s", niche_id, exc)
        return None


def niche_row_to_video_meta(row: dict[str, Any]) -> dict[str, Any]:
    """Map `niche_intelligence` or `content_class_intelligence` MV row →
    `VideoNicheMeta` shape (api-types.ts).

    The niche MV splits views into ``organic_avg_views`` /
    ``commerce_avg_views``; the content_class MV exposes a single
    ``avg_views`` (no organic/commerce split). Reading only the niche
    columns made every content_class cohort collapse to
    ``avg_views=None``, which cascaded into "—" KPI multiplier, null
    bright-spot ratio, and ``performance_tier="unknown"`` → narrative
    flop-tone for what should have been hit videos. Prefer the
    organic+commerce blend when present; otherwise fall back to the
    direct ``avg_views`` (or ``median_views`` as a final floor).
    """
    organic = _to_float(row.get("organic_avg_views"))
    commerce = _to_float(row.get("commerce_avg_views"))
    if organic > 0 and commerce > 0:
        avg_views = int(round((organic + commerce) / 2.0))
    else:
        blended = max(organic, commerce, 0.0)
        if blended > 0:
            avg_views = int(round(blended))
        else:
            direct = _to_float(row.get("avg_views"))
            if direct > 0:
                avg_views = int(round(direct))
            else:
                median = _to_float(row.get("median_views"))
                avg_views = int(round(median)) if median > 0 else None

    # ``median_er`` and ``avg_engagement_rate`` are stored in *percent*
    # space (e.g. 4.0 = 4%) per ``corpus_ingest._safe_engagement_rate``.
    # The avg_retention heuristic below was written assuming ratio
    # space (0.04 = 4%), so for any niche with ER ≥ 0.14% (effectively
    # all of them) `min(median_er, 0.14)` saturated at 0.14 and every
    # niche modeled to retention ≈ 0.848 — the modeled curve no longer
    # varied by niche and the "× ngách TB" delta became meaningless.
    # Convert to ratio for the heuristic only; keep the emitted
    # median_er in its native percent scale so cross-cohort consumers
    # (e.g. _estimate_er_percentile_rank, which also reads
    # ``meta.engagement_rate`` in percent) stay self-consistent.
    median_er_pct = _to_float(row.get("median_er"), 4.0)  # percent default ≈ 4%
    median_er_ratio = median_er_pct / 100.0
    # Heuristic until per-video retention telemetry exists: tighter ER → higher
    # assumed watch-through (bounded for UI).
    avg_retention = min(0.92, max(0.28, 0.40 + min(median_er_ratio, 0.14) * 3.2))
    # `avg_ctr` in the plan is a compact scalar for cross-niche compare; reuse ER scale.
    avg_ctr = min(0.14, max(0.006, median_er_ratio))
    sample_size = _to_int(row.get("sample_size"), 0)

    out_meta: dict[str, Any] = {
        "avg_views": avg_views,  # None when cohort has no positive view signal (FE shows "—")
        "avg_retention": round(avg_retention, 4),
        "avg_ctr": round(avg_ctr, 5),
        "sample_size": sample_size,
        # Emit median_er in its native percent scale (matches what
        # downstream code expects when comparing against meta.engagement_rate,
        # which is also stored in percent).
        "median_er": round(median_er_pct, 5),
    }
    _ae = row.get("avg_engagement_rate")
    if _ae is not None:
        out_meta["avg_engagement_rate"] = round(_to_float(_ae), 5)
    return out_meta


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
    # median_er is stored as percent (4.0 ≈ 4%); match
    # video_corpus.engagement_rate scale.
    median_er = _to_float(row.get("median_er"), 4.0)
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
    """DEPRECATED — use ``fetch_content_class_intelligence_sync`` or tier MV.

    Shim aggregates ``content_class_intelligence`` across junction classes
    for the legacy ``ingest_loop_niche_id`` bucket. Direct ``niche_intelligence``
    reads were removed in content-class pivot Round B.
    """
    from getviews_pipeline.profile_niches import creator_niche_id_for_legacy_niche

    cn_id = creator_niche_id_for_legacy_niche(niche_id)
    if cn_id is not None:
        agg = fetch_creator_niche_aggregate_intelligence_sync(sb, cn_id)
        if agg is not None:
            return agg
    logger.debug(
        "[niche_benchmark] deprecated niche_intelligence shim miss niche=%s",
        niche_id,
    )
    return None


def fetch_creator_niche_aggregate_intelligence_sync(
    sb: Any,
    creator_niche_id: int,
) -> dict[str, Any] | None:
    """Best-effort aggregate of junction ``content_class_intelligence`` rows."""
    if not creator_niche_id or sb is None:
        return None
    try:
        junction = (
            sb.table("creator_niche_content_classes")
            .select("content_class_id, is_primary")
            .eq("creator_niche_id", creator_niche_id)
            .execute()
            .data
            or []
        )
        cc_ids = [int(j["content_class_id"]) for j in junction if j.get("content_class_id")]
        if not cc_ids:
            return None
        rows = (
            sb.table("content_class_intelligence")
            .select(
                "content_class_id,sample_size,avg_views,median_views,"
                "median_er,avg_engagement_rate,computed_at"
            )
            .in_("content_class_id", cc_ids)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning(
            "[niche_benchmark] creator niche aggregate cn=%s failed: %s",
            creator_niche_id,
            exc,
        )
        return None
    if not rows:
        return None
    primaries = {int(j["content_class_id"]) for j in junction if j.get("is_primary")}
    pool = [r for r in rows if int(r.get("content_class_id") or 0) in primaries] or rows
    best = max(pool, key=lambda r: _to_int(r.get("sample_size"), 0))
    total_sample = sum(_to_int(r.get("sample_size"), 0) for r in pool)
    out = dict(best)
    out["sample_size"] = total_sample
    out["ingest_loop_niche_id"] = None
    return out


# ── Two-axis A.2.3 (2026-05-15) — content_class benchmark fetch ─────────────────


# Sample-size threshold for preferring content_class_intelligence over
# niche_intelligence. content_class buckets are narrower so we want at
# least N rows before switching axis. Below this floor, fall back to
# niche-wide for stable benchmarks.
CONTENT_CLASS_BENCHMARK_MIN_SAMPLE = 15


def fetch_content_class_intelligence_sync(sb: Any, content_class_id: int) -> dict[str, Any] | None:
    """Blocking fetch from ``content_class_intelligence`` MV.

    Two-axis A.2.3 (2026-05-15) — parallel to ``fetch_niche_intelligence_sync``
    but for the sharper (topic × format) axis introduced in A.2.1. Returns
    ``None`` when MV row missing OR sample_size below the stability floor;
    callers fall back to niche-scoped row.

    Column shape mirrors the niche MV columns the FE meta consumer needs
    (avg_views/median_er/sample_size/computed_at) plus median_views/
    median_scene_count which are A.2.1-only additions.
    """
    if not content_class_id:
        return None
    try:
        res = (
            sb.table("content_class_intelligence")
            .select(
                "content_class_id,sample_size,avg_views,median_views,"
                "median_er,avg_engagement_rate,median_scene_count,computed_at"
            )
            .eq("content_class_id", content_class_id)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "[niche_benchmark] select content_class=%s failed (acceptable "
            "if migration 20260514000000 not yet applied): %s",
            content_class_id, exc,
        )
        return None
    rows = res.data or []
    row = rows[0] if rows and isinstance(rows[0], dict) else None
    if row is None:
        return None
    sample = _to_int(row.get("sample_size"), 0)
    if sample < CONTENT_CLASS_BENCHMARK_MIN_SAMPLE:
        # Too thin to back claims — caller falls back to niche-wide.
        return None
    return row


def fetch_content_class_tier_intelligence_sync(
    sb: Any,
    content_class_id: int,
    creator_tier: str,
) -> dict[str, Any] | None:
    """Peer-band MV row for (content_class_id, creator_tier)."""
    if not content_class_id or not creator_tier or sb is None:
        return None
    try:
        res = (
            sb.table("content_class_tier_intelligence")
            .select(
                "content_class_id,creator_tier,sample_size,median_views,"
                "p75_views,median_er,avg_views,avg_engagement_rate,computed_at"
            )
            .eq("content_class_id", content_class_id)
            .eq("creator_tier", creator_tier)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "[niche_benchmark] tier MV class=%s tier=%s: %s",
            content_class_id,
            creator_tier,
            exc,
        )
        return None
    rows = res.data or []
    row = rows[0] if rows and isinstance(rows[0], dict) else None
    if row is None:
        return None
    if _to_int(row.get("sample_size"), 0) < CONTENT_CLASS_BENCHMARK_MIN_SAMPLE:
        return None
    return row


def fetch_video_benchmark_with_axis(
    sb: Any,
    *,
    niche_id: int,
    content_class_id: int | None,
    creator_tier: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Pick the sharper benchmark row available, with axis label.

    When ``live_cohort_class_first`` is on: tier MV → class MV → niche fallback.
    Legacy niche-first path removed (Round B).

    Returns ``(row, axis)`` where ``axis`` is ``"content_class"``,
    ``"content_class_tier"``, or ``"niche"`` (or ``"none"`` when all miss).
    """
    if content_class_id is not None and creator_tier:
        tier_row = fetch_content_class_tier_intelligence_sync(
            sb, content_class_id, creator_tier,
        )
        if tier_row is not None:
            return tier_row, "content_class_tier"
    if content_class_id is not None:
        cc_row = fetch_content_class_intelligence_sync(sb, content_class_id)
        if cc_row is not None:
            return cc_row, "content_class"
    if niche_id:
        n_row = fetch_niche_intelligence_sync(sb, niche_id)
        if n_row is not None:
            return n_row, "niche"
    return None, "none"


def peer_percentile(
    value: float,
    *,
    median: float,
    p75: float | None = None,
) -> float | None:
    """Estimate 0–100 peer percentile vs tier cohort (Phase 2 dynamic tier diagnosis)."""
    if value <= 0 or median <= 0:
        return None
    if p75 is not None and p75 > median and value >= p75:
        span = max(p75 - median, 1.0)
        extra = min(1.0, (value - p75) / span)
        return round(min(99.0, 75.0 + extra * 24.0), 1)
    ratio = value / median
    if ratio >= 2.0:
        return 95.0
    if ratio >= 1.5:
        return 85.0
    if ratio >= 1.0:
        return 65.0
    if ratio >= 0.5:
        return 35.0
    return 15.0


def carousel_diagnosis_thresholds() -> dict[str, Any]:
    """Carousel benchmark thresholds from ``carousel_knowledge`` (topic_axis=carousel)."""
    from getviews_pipeline.carousel_knowledge import ALGORITHM_SIGNALS, OPTIMAL_SPECS

    str_sig = ALGORITHM_SIGNALS.get("swipe_through_rate") or {}
    comp = ALGORITHM_SIGNALS.get("completion_rate") or {}
    save = ALGORITHM_SIGNALS.get("save_rate") or {}
    slides = OPTIMAL_SPECS.get("slide_count") or {}
    return {
        "topic_axis": "carousel",
        "swipe_through_rate_strong": str_sig.get("strong"),
        "swipe_through_rate_weak": str_sig.get("weak"),
        "completion_rate_strong": comp.get("strong"),
        "save_rate_strong": save.get("strong"),
        "slide_count_ideal": slides.get("ideal"),
        "slide_count_min": slides.get("min"),
        "slide_count_max": slides.get("max"),
    }


def enrich_niche_meta_with_peer_tier(
    meta: dict[str, Any],
    tier_row: dict[str, Any] | None,
    *,
    views: int | None = None,
    topic_axis: str = "video",
) -> dict[str, Any]:
    """Attach peer_percentile + carousel thresholds when tier MV or carousel path."""
    out = dict(meta)
    if topic_axis == "carousel":
        out["carousel_thresholds"] = carousel_diagnosis_thresholds()
    if tier_row and views is not None:
        med = _to_float(tier_row.get("median_views"))
        p75 = _to_float(tier_row.get("p75_views")) or None
        pct = peer_percentile(float(views), median=med, p75=p75 if p75 else None)
        if pct is not None:
            out["peer_percentile"] = pct
    return out


def attach_peer_percentile_label(meta: dict[str, Any]) -> dict[str, Any]:
    """Vietnamese humility-safe label for FlopDiagnosisStrip (Wave 1 W1-3)."""
    pct = meta.get("peer_percentile")
    if pct is None:
        return meta
    try:
        p = float(pct)
    except (TypeError, ValueError):
        return meta
    out = dict(meta)
    if p >= 75:
        out["peer_percentile_label"] = (
            f"View cao hơn ~{int(round(p))}% video cùng format × tier"
        )
    elif p >= 50:
        out["peer_percentile_label"] = (
            f"View ~top {max(1, int(round(100 - p)))}% trong cùng format × tier"
        )
    else:
        out["peer_percentile_label"] = (
            f"View thấp hơn ~{int(round(100 - p))}% video cùng format × tier"
        )
    return out


def finalize_niche_meta_peer_tier(
    niche_meta: dict[str, Any],
    *,
    benchmark_axis: str,
    benchmark_row: dict[str, Any] | None,
    views: int,
    topic_axis: str = "video",
) -> dict[str, Any]:
    """Apply tier MV peer percentile + label when axis is content_class_tier."""
    if benchmark_axis != "content_class_tier" or not benchmark_row or views <= 0:
        return niche_meta
    enriched = enrich_niche_meta_with_peer_tier(
        niche_meta,
        benchmark_row,
        views=views,
        topic_axis=topic_axis,
    )
    return attach_peer_percentile_label(enriched)
