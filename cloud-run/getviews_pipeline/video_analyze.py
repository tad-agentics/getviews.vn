"""Phase B · B.1.3 — /video/analyze: cache, structural slots, Gemini LLM, diagnostics upsert.

Deterministic pieces reuse ``video_structural`` + ``video_niche_benchmark``.
Writes go through **service_role** (see migration: no authenticated INSERT).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

AnalysisDepth = Literal["basic", "deep"]


def _normalize_analysis_depth(depth: str | None) -> AnalysisDepth:
    return "deep"


from getviews_pipeline.corpus_context import (
    content_class_id_for_reference_pool,
    format_creator_format_history_for_diagnosis,
    get_creator_format_history_sync,
)
from getviews_pipeline.corpus_windows import (
    corpus_benchmark_window_days,
    corpus_reference_fetch_days,
    corpus_reference_pick_days,
)
from getviews_pipeline.video_niche_benchmark import (
    build_niche_benchmark_payload,
    fetch_video_benchmark_with_axis,
    finalize_niche_meta_peer_tier,
)
from getviews_pipeline.video_structural import (
    decompose_segments,
    extract_hook_phases,
    model_retention_curve,
    model_retention_curve_from_structure,
    video_duration_sec,
)

logger = logging.getLogger(__name__)

RetentionSource = Literal["real", "modeled", "modeled_structural"]

DIAGNOSTICS_STALE_AFTER = timedelta(hours=1)


def _apply_peer_tier_to_niche_meta(
    niche_meta: dict[str, Any],
    *,
    benchmark_axis: str,
    benchmark_row: dict[str, Any] | None,
    views: int,
    content_format: str,
) -> dict[str, Any]:
    topic = "carousel" if str(content_format or "").strip().lower() == "carousel" else "video"
    return finalize_niche_meta_peer_tier(
        niche_meta,
        benchmark_axis=benchmark_axis,
        benchmark_row=benchmark_row,
        views=views,
        topic_axis=topic,
    )


# Bump when ``VideoAnalyzeResponse.meta`` shape changes (invalidates on-demand cache).
# v3 — embed_contract_version + finalize-lite repair for poisoned cached_response blobs.
ON_DEMAND_RESPONSE_SCHEMA_VERSION = 3
# Minimum on-demand blob version we still attempt embed repair on (v2 blobs may lack tiles).
ON_DEMAND_RESPONSE_SCHEMA_VERSION_MIN = 2
EXTRACT_JSON_SCHEMA_VERSION = 1
# Server-only fields persisted in ``cached_response`` — never ship to the FE.
_ON_DEMAND_CLIENT_STRIP_KEYS = frozenset({"extract_json", "extract_schema_version"})


def _strip_on_demand_client_cache_fields(out: dict[str, Any]) -> None:
    for key in _ON_DEMAND_CLIENT_STRIP_KEYS:
        out.pop(key, None)


def _truncate_tiktok_caption(text: str, *, max_len: int = 2000) -> str:
    return (text or "").strip()[:max_len]


def _legacy_meta_title(caption: str, hook_phrase: str) -> str | None:
    """First line of TikTok desc for backward-compat ``meta.title``."""
    cap = (caption or "").strip()
    if cap:
        first = cap.split("\n")[0].strip()
        return first[:200] if first else None
    hp = (hook_phrase or "").strip()
    return hp[:200] if hp else None


def _fetch_sidecars_sync(
    video_id: str,
    comment_count_hint: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Run async thumbnail + comment-radar resolvers from the sync pipeline (thread pool)."""
    from getviews_pipeline.comment_radar_cache import resolve_comment_radar
    from getviews_pipeline.thumbnail_analysis_cache import resolve_thumbnail_analysis

    async def _both() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        return await asyncio.gather(
            resolve_thumbnail_analysis(video_id),
            resolve_comment_radar(video_id, comment_count_hint=comment_count_hint),
        )

    return asyncio.run(_both())


def _merge_sidecars_into_response(
    out: dict[str, Any],
    *,
    video_id: str,
    comment_count_hint: int,
) -> dict[str, Any]:
    """Attach corpus sidecars; failures are logged and omitted from the payload."""
    try:
        thumb, radar = _fetch_sidecars_sync(video_id, comment_count_hint)
    except Exception as exc:
        logger.warning(
            "[video_analyze] sidecar resolve failed video_id=%s: %s",
            video_id,
            exc,
        )
        return out
    if thumb is not None:
        out["thumbnail_analysis"] = thumb
    if radar is not None:
        out["comment_radar"] = radar
    return out


def _ensure_comment_radar_on_out(out: dict[str, Any]) -> None:
    """Best-effort comment_radar for on-demand / missing sidecar (§4.7 M5)."""
    if out.get("comment_radar"):
        return
    video_id = str(out.get("video_id") or "")
    if not video_id:
        return
    meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    comment_count = int(meta.get("comments") or 0)
    if str(out.get("source") or "") != "on_demand" and comment_count < 5:
        return
    try:
        import asyncio

        from getviews_pipeline.comment_radar_cache import resolve_comment_radar

        radar = asyncio.run(
            resolve_comment_radar(video_id, comment_count_hint=comment_count),
        )
        if radar:
            out["comment_radar"] = radar
    except Exception as exc:
        logger.warning(
            "[video_narrative] comment_radar resolve failed video_id=%s: %s",
            video_id,
            exc,
        )


def _attach_hook_effectiveness_for_diagnosis(
    out: dict[str, Any],
    *,
    user_sb: Any | None,
) -> None:
    """Load measured hook lift for diagnosis grounding (always — shadow telemetry)."""
    if user_sb is None:
        out["hook_effectiveness"] = []
        out["hook_effectiveness_axis"] = "none"
        return
    meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    niche_meta = out.get("niche_meta") if isinstance(out.get("niche_meta"), dict) else {}
    content_class_id: int | None = None
    for raw_cc in (
        niche_meta.get("content_class_id"),
        meta.get("content_class_id"),
    ):
        if raw_cc is None:
            continue
        try:
            content_class_id = int(raw_cc)
            break
        except (TypeError, ValueError):
            continue
    niche_id: int | None = None
    for raw_n in (
        niche_meta.get("niche_id"),
        meta.get("niche_id"),
        meta.get("ingest_loop_niche_id"),
    ):
        if raw_n is None:
            continue
        try:
            niche_id = int(raw_n)
            break
        except (TypeError, ValueError):
            continue
    try:
        from getviews_pipeline.video_niche_benchmark import fetch_class_hook_effectiveness_sync

        rows, axis = fetch_class_hook_effectiveness_sync(
            user_sb,
            content_class_id=content_class_id,
            niche_id=niche_id,
        )
        out["hook_effectiveness"] = rows
        out["hook_effectiveness_axis"] = axis
    except Exception as exc:
        logger.warning("[video_analyze] hook_effectiveness fetch failed: %s", exc)
        out["hook_effectiveness"] = []
        out["hook_effectiveness_axis"] = "none"


def _resolve_user_retention_curve(
    *,
    duration_sec: float,
    analysis: dict[str, Any],
    niche_median_retention: float,
    breakout_multiplier: float,
    video_id: str,
    content_format: str,
) -> tuple[list[dict[str, float]], RetentionSource | None, list[dict[str, Any]]]:
    """Build user retention curve; optional structural override + risk_events."""
    from getviews_pipeline.services.asr_vietnamese import fetch_asr_segments
    from getviews_pipeline.settings import settings as pipeline_settings

    dur = max(float(duration_sec), 5.0)
    fmt = str(content_format or "").strip().lower()
    scenes_raw = analysis.get("scenes") if isinstance(analysis.get("scenes"), list) else []
    scenes = [s for s in scenes_raw if isinstance(s, dict)]
    hook = analysis.get("hook_analysis") if isinstance(analysis.get("hook_analysis"), dict) else {}

    synthetic = model_retention_curve(
        dur,
        niche_median_retention=float(niche_median_retention),
        breakout_multiplier=breakout_multiplier,
        n_points=20,
    )
    if fmt == "carousel" or not scenes:
        return synthetic, None, []

    asr_segments = fetch_asr_segments(video_id) if video_id else []
    hook_tl = hook.get("hook_timeline") if isinstance(hook.get("hook_timeline"), list) else []
    structural_curve, risk_events = model_retention_curve_from_structure(
        dur,
        scenes,
        niche_median_retention=float(niche_median_retention),
        breakout_multiplier=breakout_multiplier,
        asr_segments=asr_segments or None,
        hook_timeline=hook_tl,
        hook_analysis=hook,
        audio_track_role=(
            str(analysis.get("audio_track_role") or "").strip() or None
        ),
        n_points=20,
    )

    if not pipeline_settings.diagnosis_retention_structural:
        try:
            syn_end = float(synthetic[-1]["pct"]) if synthetic else 0.0
            struct_end = float(structural_curve[-1]["pct"]) if structural_curve else 0.0
            logger.info(
                "[retention_shadow] video_id=%s syn_end=%.1f struct_end=%.1f "
                "risk_count=%d top=%s",
                video_id or "",
                syn_end,
                struct_end,
                len(risk_events),
                [str(e.get("reason_vi") or "")[:60] for e in risk_events[:3]],
            )
        except Exception:
            logger.debug("[retention_shadow] log failed", exc_info=True)
        return synthetic, None, []

    return structural_curve, "modeled_structural", risk_events


# ── Gemini output schemas (Call 1 — structured errors only) ─────────────

# Moved to services/extraction.py — re-exported here for backward compatibility.
from getviews_pipeline.services.extraction import (  # noqa: E402
    _FORBIDDEN_PHRASES_VI,  # noqa: F401 — public re-export for tests
    _dedupe_lang_market_hook_errors,  # noqa: F401 — public re-export for tests / callers
    _summarise_niche_row,  # noqa: F401 — public re-export for tests
    _summarise_retention_curve,  # noqa: F401 — public re-export for tests
    apply_rule_based_video_errors,
    extract_video_errors,
)

# ── Mode + KPI helpers ─────────────────────────────────────────────────────


def _normalise_save_rate(video: dict[str, Any]) -> float:
    """Return save_rate as a *ratio* (0–1).

    Preferred source: corpus ``save_rate`` column (already stored as
    ratio). Falls back to ``saves/views`` when the column is missing.
    Defensive: if a legacy row leaked a percent value (>1.0), divide
    by 100 to bring it back into ratio space.
    """
    sr = video.get("save_rate")
    if sr is not None:
        v = float(sr or 0.0)
        return v / 100.0 if v > 1.0 else v
    saves = int(video.get("saves") or 0)
    views = max(int(video.get("views") or 1), 1)
    return saves / views


def _median_views_proxy(niche_row: dict[str, Any] | None) -> float:
    """Best view proxy from a benchmark row (niche or content_class MV).

    The niche MV has organic/commerce split; the content_class MV
    exposes ``avg_views``/``median_views`` directly. Reading only the
    niche columns made content_class rows fall through to the 5000
    floor and is_flop_mode silently classified every video against the
    wrong baseline.
    """
    if not niche_row:
        return 10_000.0
    o = float(niche_row.get("organic_avg_views") or 0)
    c = float(niche_row.get("commerce_avg_views") or 0)
    if o > 0 and c > 0:
        return (o + c) / 2.0
    blended = max(o, c, 0.0)
    if blended > 0:
        return blended
    direct = float(niche_row.get("avg_views") or 0)
    if direct > 0:
        return direct
    median = float(niche_row.get("median_views") or 0)
    if median > 0:
        return median
    return 5_000.0


# Niche-less flop thresholds — tunable via env vars (see settings.py).
from getviews_pipeline.settings import settings as _settings  # noqa: E402

NICHELESS_FLOP_VIEWS_FLOOR = _settings.nicheless_flop_views_floor
NICHELESS_FLOP_VIEWS_LOOSE = _settings.nicheless_flop_views_loose
NICHELESS_FLOP_ER_FLOOR = _settings.nicheless_flop_er_floor


def is_flop_mode(video: dict[str, Any], niche_row: dict[str, Any] | None) -> bool:
    """Decide whether to render the flop UI for this video.

    Two-tier decision:

      1. **Niche cohort present** — compare against niche medians. Flop
         when views < 50% of niche median OR ER < 60% of niche median.
         This is the corpus-grounded signal — most accurate when we
         have a meaningful cohort.

      2. **No niche cohort** (``niche_row`` is None) — fall back to
         absolute thresholds. Pre-migration this branch silently
         defaulted to win, which mis-rendered every URL paste whose
         hashtags didn't classify (a high-frequency case for new niches
         + generic-tag videos). The absolute thresholds are
         conservative — they only flag clear underperformance, so a
         creator-relative comparison would be more accurate. Acceptable
         trade-off until we can derive a creator-cohort signal.
    """
    views = int(video.get("views") or 0)
    er = float(video.get("engagement_rate") or 0.0)

    if not niche_row:
        # Niche-less fallback. AND on the loose tier so a high-views
        # video with weak ER doesn't trigger flop unless ER is
        # genuinely poor — protects against false-positive flop on
        # passive-consumption niches (asmr, sleep content, etc.).
        if NICHELESS_FLOP_VIEWS_FLOOR > 0 and 0 < views < NICHELESS_FLOP_VIEWS_FLOOR:
            return True
        if (
            NICHELESS_FLOP_VIEWS_LOOSE > 0
            and 0 < views < NICHELESS_FLOP_VIEWS_LOOSE
            and 0 < er < NICHELESS_FLOP_ER_FLOOR
        ):
            return True
        return False

    niche_views = _median_views_proxy(niche_row)
    median_er = float(niche_row.get("median_er") or 0.04)
    if niche_views > 0 and views < niche_views * 0.5:
        return True
    if median_er > 0 and er < median_er * 0.6:
        return True
    return False


def _fmt_int_short(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    return str(n)


_KPI_QUANT_CACHE_TTL_S = 300.0
_KPI_QUANT_CACHE: dict[
    int,
    tuple[float, tuple[tuple[float | None, float | None], tuple[float | None, float | None]]],
] = {}


def fetch_niche_save_share_pct_quantiles_sync(
    sb: Any,
    niche_id: int,
    *,
    min_samples: int = 5,
    limit: int = 200,
) -> tuple[tuple[float | None, float | None], tuple[float | None, float | None]]:
    """``((save_p25, save_p75), (share_p25, share_p75))`` on 0–100% scale for KPI labels.

    Save cohort uses ``100*saves/views`` per row (same definition as the KPI value), not
    ``save_rate``, so tertiles stay comparable when ``save_rate`` is sparsely populated.
    Results are cached per process (~5 min) to avoid hammering PostgREST on repeat reads.
    """
    if not niche_id or sb is None:
        return (None, None), (None, None)

    now = time.monotonic()
    cached = _KPI_QUANT_CACHE.get(niche_id)
    if cached is not None and now - cached[0] < _KPI_QUANT_CACHE_TTL_S:
        return cached[1]

    try:
        since = (datetime.now(UTC) - timedelta(days=corpus_benchmark_window_days())).isoformat()
        res = (
            sb.table("video_corpus")
            .select("views, shares, saves")
            .eq("ingest_loop_niche_id", niche_id)
            .gt("views", 0)
            .gte("indexed_at", since)
            .limit(limit)
            .execute()
        )
        rows = list(res.data or [])
    except Exception as exc:
        logger.debug("[video_analyze] kpi cohort quantiles failed niche=%s: %s", niche_id, exc)
        return (None, None), (None, None)

    save_pcts: list[float] = []
    share_pcts: list[float] = []
    for r in rows:
        v = int(r.get("views") or 0)
        if v <= 0:
            continue
        sv = int(r.get("saves") or 0)
        save_pcts.append(100.0 * sv / float(v))
        sh = int(r.get("shares") or 0)
        share_pcts.append(100.0 * sh / float(v))

    def _qpct(vals: list[float]) -> tuple[float | None, float | None]:
        if len(vals) < min_samples:
            return None, None
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        p25 = vals_sorted[max(0, (n * 25) // 100)]
        p75 = vals_sorted[min(n - 1, (n * 75) // 100)]
        if p75 <= p25:
            return None, None
        return float(p25), float(p75)

    out = _qpct(save_pcts), _qpct(share_pcts)
    _KPI_QUANT_CACHE[niche_id] = (now, out)
    return out


def classify_kpi_tertile_label(
    value: float,
    p25: float | None,
    p75: float | None,
    *,
    metric: str = "",
) -> str:
    """``thấp`` / ``TB`` / ``cao`` / ``''`` when cohort band missing (audit SAVE-LABEL v4)."""
    if p25 is None or p75 is None or p75 <= p25:
        return ""
    if value < p25:
        label = "thấp"
    elif value > p75:
        label = "cao"
    else:
        label = "TB"
    if metric:
        logger.debug(
            "[metric_label] metric=%s value=%s p25=%s p75=%s → label=%s",
            metric,
            value,
            p25,
            p75,
            label,
        )
    return label


def build_kpis(
    video: dict[str, Any],
    niche_meta: dict[str, Any],
    *,
    mode: Literal["win", "flop"],
    retention_end_pct: float,
    cohort_save_p25_pct: float | None = None,
    cohort_save_p75_pct: float | None = None,
    cohort_share_p25_pct: float | None = None,
    cohort_share_p75_pct: float | None = None,
) -> list[dict[str, str]]:
    views = int(video.get("views") or 0)
    shares = int(video.get("shares") or 0)
    saves = int(video.get("saves") or 0)
    # Niche-relative multiplier — historically labelled "× kênh" which
    # reads as "× channel" in Vietnamese but actually compares against
    # the niche cohort average. Two fixes (2026-05-08):
    #   1. Honest label: "× ngách" so it doesn't conflict with the
    #      true channel-relative ratio in ContextStrip.
    #   2. Hide the multiplier when the niche cohort is too thin
    #      (avg_views < 1_000) — otherwise the ``max(..., 1)`` floor
    #      produces nonsense like "126192.0× ngách" for sparse niches.
    niche_avg_raw = int(niche_meta.get("avg_views") or 0)
    if niche_avg_raw >= 1_000:
        mult = views / niche_avg_raw
        delta_views = f"{mult:.1f}× ngách" if mult >= 0.1 else "—"
    else:
        delta_views = "—"
    ret_pct = f"{retention_end_pct:.0f}%"
    ret_delta = "top 5%" if retention_end_pct >= 70 else "ngách TB"
    save_rate = (saves / views * 100.0) if views else 0.0
    sr_l = classify_kpi_tertile_label(
        save_rate,
        cohort_save_p25_pct,
        cohort_save_p75_pct,
        metric="save_rate",
    )
    band_ok = (
        cohort_save_p25_pct is not None
        and cohort_save_p75_pct is not None
        and cohort_save_p75_pct > cohort_save_p25_pct
    )
    if save_rate > 2.0 and (not band_ok or save_rate > cohort_save_p75_pct):
        sr_delta = "rất cao"
    elif sr_l:
        sr_delta = sr_l
    else:
        sr_delta = ""

    share_rate = (shares / views * 100.0) if views else 0.0
    sh_l = classify_kpi_tertile_label(
        share_rate,
        cohort_share_p25_pct,
        cohort_share_p75_pct,
        metric="share_rate",
    )
    if sh_l:
        share_delta = sh_l
    else:
        share_delta = "lan toả" if shares > 0 else "—"

    return [
        {"label": "VIEW", "value": _fmt_int_short(views), "delta": delta_views},
        {"label": "GIỮ CHÂN", "value": ret_pct, "delta": ret_delta},
        {"label": "SAVE RATE", "value": f"{save_rate:.1f}%", "delta": sr_delta},
        {"label": "SHARE", "value": _fmt_int_short(shares), "delta": share_delta},
    ]


def _parse_ts(ts: Any) -> datetime | None:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    try:
        s = str(ts).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _diagnostics_fresh(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    ct = _parse_ts(row.get("computed_at"))
    if not ct:
        return False
    return datetime.now(UTC) - ct < DIAGNOSTICS_STALE_AFTER


def _cache_age_minutes(row: dict[str, Any]) -> int:
    ct = _parse_ts(row.get("computed_at"))
    if not ct:
        return 0
    delta = datetime.now(UTC) - ct
    return max(0, int(delta.total_seconds() // 60))


def _fetch_corpus_row(user_sb: Any, vid: str) -> dict[str, Any]:
    """Load one ``video_corpus`` row; never surfaces PostgREST 0-row as a 500."""
    from postgrest.exceptions import APIError

    # video_corpus.niche_id was dropped (Phase C); alias the surviving legacy-niche
    # surrogate ingest_loop_niche_id back to the "niche_id" key so callers are unchanged.
    cols = (
        "video_id,creator_handle,views,likes,comments,shares,saves,save_rate,"
        "engagement_rate,thumbnail_url,created_at,niche_id:ingest_loop_niche_id,content_class_id,"
        "content_format,analysis_json,breakout_multiplier,tiktok_url,"
        "creator_median_views,caption,stats_history,distribution_shape,"
        "boost_attribution,reference_eligible"
    )
    try:
        vres = user_sb.table("video_corpus").select(cols).eq("video_id", vid).maybe_single().execute()
    except APIError as exc:
        code = getattr(exc, "code", None)
        details = str(getattr(exc, "details", "") or "")
        if code == "PGRST116" or "0 rows" in details:
            raise ValueError("video not in corpus") from exc
        raise
    if vres is None:
        raise ValueError("video not in corpus")
    data = getattr(vres, "data", None)
    if not isinstance(data, dict) or not data.get("video_id"):
        raise ValueError("video not in corpus")
    return data


def _diagnostics_legacy(diag: dict[str, Any]) -> bool:
    """True if ``video_diagnostics`` row predates unified errors + narrative schema."""

    if diag.get("analysis_headline"):
        return True
    les = diag.get("lessons") or []
    if isinstance(les, list) and len(les) > 0:
        return True
    for fi in diag.get("flop_issues") or []:
        if isinstance(fi, dict) and not str(fi.get("error_id") or "").strip():
            return True
    return False


# ── Niche-label resolver + UUID guard ────────────────────────────────


def _resolve_niche_label(user_sb: Any, niche_id: int) -> str:
    """``niche_taxonomy.name_vn`` preferred; empty string if missing or lookup fails."""
    if not niche_id:
        return ""
    try:
        tres = (
            user_sb.table("niche_taxonomy")
            .select("name_vn,name_en")
            .eq("id", niche_id)
            .limit(1)
            .execute()
        )
        tr = (tres.data or [{}])[0]
        return str(tr.get("name_vn") or tr.get("name_en") or "")
    except Exception:
        return ""


def _apply_studio_session_niche_cohort(
    out: dict[str, Any],
    session_niche_id: int | None,
    *,
    user_sb: Any | None,
) -> None:
    """Pin benchmarks + meta labels to the Studio session niche (legacy taxonomy id)."""
    pin = int(session_niche_id or 0)
    if pin <= 0 or user_sb is None:
        return
    meta = out.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        out["meta"] = meta
    prior = int(meta.get("niche_id") or 0)
    label = _resolve_niche_label(user_sb, pin)
    meta["niche_id"] = pin
    if label:
        meta["niche_label"] = label

    content_format = str(meta.get("content_format") or "").strip()
    content_class_id: int | None = None
    if content_format:
        try:
            from getviews_pipeline.corpus_ingest import _content_class_for

            content_class_id = _content_class_for(pin, content_format)
            if content_class_id is not None:
                meta["content_class_id"] = content_class_id
        except Exception:
            content_class_id = meta.get("content_class_id")
            if content_class_id is not None:
                try:
                    content_class_id = int(content_class_id)
                except (TypeError, ValueError):
                    content_class_id = None
    elif meta.get("content_class_id") is not None:
        try:
            content_class_id = int(meta["content_class_id"])
        except (TypeError, ValueError):
            content_class_id = None

    dur = float(meta.get("duration_sec") or 30.0)
    try:
        niche_intel, benchmark_axis = fetch_video_benchmark_with_axis(
            user_sb,
            niche_id=pin,
            content_class_id=content_class_id,
            creator_tier=None,
        )
        bench = build_niche_benchmark_payload(
            niche_intel,
            niche_id=pin,
            duration_sec=max(dur, 5.0),
            user_sb=user_sb,
            benchmark_axis=benchmark_axis,
            content_class_id=content_class_id,
        )
        if bench.get("niche_meta"):
            nm = bench["niche_meta"]
            nm["benchmark_axis"] = benchmark_axis
            out["niche_meta"] = nm
        if bench.get("niche_benchmark_curve"):
            out["niche_benchmark_curve"] = bench["niche_benchmark_curve"]
    except Exception as exc:
        logger.warning("[video_analyze] session niche cohort refresh failed: %s", exc)

    if prior != pin:
        logger.info(
            "[video_analyze] studio session niche pin %s -> %s video_id=%s",
            prior or "none",
            pin,
            out.get("video_id"),
        )


def _normalise_hook_timeline(raw: Any) -> list[dict[str, Any]]:
    """Expose Gemini hook_timeline for FE ``HookTimelineStrip`` (0–3s window)."""
    if not isinstance(raw, list):
        return []
    allowed = {
        "face_enter",
        "first_word",
        "text_overlay",
        "sound_drop",
        "cut",
        "product_enter",
        "reveal",
    }
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            t = float(item.get("t"))
        except (TypeError, ValueError):
            continue
        if t < 0 or t > 3.0:
            continue
        ev = str(item.get("event") or "").strip()
        if ev not in allowed:
            continue
        row: dict[str, Any] = {"t": round(t, 1), "event": ev}
        note = str(item.get("note") or "").strip()
        if note:
            row["note"] = note[:120]
        out.append(row)
    out.sort(key=lambda x: x["t"])
    return out


# Gemini ``VideoAnalysis.tone`` — mirrors ``ToneType`` in models.py.
VIDEO_TONE_VALUES = frozenset({
    "educational",
    "entertaining",
    "emotional",
    "humorous",
    "inspirational",
    "urgent",
    "conversational",
    "authoritative",
})


def _normalize_video_tone(raw: Any) -> str | None:
    tone = str(raw or "").strip().lower().replace("-", "_")
    if tone in ("none", "unknown", "other", ""):
        return None
    return tone if tone in VIDEO_TONE_VALUES else None


def _is_carousel_analysis(video: dict[str, Any], analysis: dict[str, Any]) -> bool:
    fmt = str(video.get("content_format") or "").lower()
    if "carousel" in fmt:
        return True
    slides = analysis.get("slides")
    return isinstance(slides, list) and len(slides) > 0


def _carousel_subformat_from_analysis(analysis: dict[str, Any]) -> str:
    arc = str(analysis.get("content_arc") or "").lower()
    if arc in ("list", "gallery"):
        return "carousel_product_roundup"
    if arc in ("tutorial_steps",):
        return "carousel_tutorial"
    if arc in ("story", "narrative"):
        return "carousel_story"
    return "carousel"


def _normalise_carousel_slides(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        texts = item.get("text_on_slide")
        preview = ""
        if isinstance(texts, list):
            preview = " ".join(str(t).strip() for t in texts if str(t).strip())[:160]
        row: dict[str, Any] = {"index": idx, "text_preview": preview or None}
        for key in (
            "has_face",
            "has_product",
            "word_count",
            "text_density",
            "swipe_anchor",
            "layout",
        ):
            if item.get(key) is not None:
                row[key] = item.get(key)
        out.append(row)
    out.sort(key=lambda x: x["index"])
    return out


def _attach_carousel_payload(
    payload: dict[str, Any],
    video: dict[str, Any],
    analysis: dict[str, Any],
) -> None:
    if not _is_carousel_analysis(video, analysis):
        return
    from getviews_pipeline.enum_labels_vi import carousel_subformat_vi

    sub = _carousel_subformat_from_analysis(analysis)
    slides = _normalise_carousel_slides(analysis.get("slides"))
    payload["carousel_subformat"] = sub
    payload["carousel_subformat_label"] = carousel_subformat_vi(sub, default=sub)
    if slides:
        payload["carousel_slide_count"] = len(slides)
    payload["carousel_intel"] = {
        "swipe_trigger_type": analysis.get("swipe_trigger_type"),
        "has_numbered_hook": analysis.get("has_numbered_hook"),
        "content_arc": analysis.get("content_arc"),
        "visual_consistency": analysis.get("visual_consistency"),
        "estimated_read_time_seconds": analysis.get("estimated_read_time_seconds"),
        "slide_pacing_score": analysis.get("slide_pacing_score"),
        "slides": slides,
    }


def _response_from_diagnostics_row(
    video: dict[str, Any],
    diag: dict[str, Any],
    *,
    mode: Literal["win", "flop"],
    niche_meta: dict[str, Any],
    niche_benchmark: list[dict[str, float]],
    retention_user: list[dict[str, float]],
    niche_label: str,
    retention_source: RetentionSource = "modeled",
    cross_format_signal: dict[str, Any] | None = None,
    retention_risk_events: list[dict[str, Any]] | None = None,
    user_sb: Any | None = None,
) -> dict[str, Any]:
    analysis = video.get("analysis_json") or {}
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError:
            analysis = {}
    if not isinstance(analysis, dict):
        analysis = {}
    dur = video_duration_sec(analysis)
    hook = (analysis.get("hook_analysis") or {}) if isinstance(analysis.get("hook_analysis"), dict) else {}
    hook_phrase = str(hook.get("hook_phrase") or "").strip()
    tiktok_caption = _truncate_tiktok_caption(str(video.get("caption") or ""))
    title_hint = _legacy_meta_title(tiktok_caption, hook_phrase)
    ret_curve = diag.get("retention_curve") or retention_user
    bench_curve = diag.get("niche_benchmark_curve") or niche_benchmark
    ret_end = float(ret_curve[-1]["pct"]) if ret_curve else 0.0

    # Channel-relative breakout: views vs the creator's own median.
    # Corpus path: read denormalized creator_median_views (from corpus_ingest).
    # On-demand path: column missing → skip; FE renders only when present.
    cm_views_raw = video.get("creator_median_views")
    creator_median_views = int(cm_views_raw) if cm_views_raw else None
    target_vs_creator_median = (
        round(int(video.get("views") or 0) / float(creator_median_views), 2)
        if creator_median_views and creator_median_views > 0
        else None
    )

    # Enrichment fields extracted by Gemini (VideoAnalysis schema, 2026-05-08).
    # Available on both corpus rows (analysis_json) and on-demand
    # (fresh extraction). Render only when populated to avoid empty chips.
    pain_points_raw = analysis.get("pain_points") or []
    style_tags_raw = analysis.get("style_tags") or []
    target_audience = str(analysis.get("target_audience") or "").strip()
    promotion_type = str(analysis.get("promotion_type") or "organic").strip().lower()
    pain_points = [str(p).strip() for p in pain_points_raw if isinstance(p, str) and p.strip()]
    style_tags = [str(s).strip() for s in style_tags_raw if isinstance(s, str) and s.strip()]
    tone = _normalize_video_tone(analysis.get("tone"))
    enrichment: dict[str, Any] | None = None
    if target_audience or pain_points or style_tags or promotion_type != "organic" or tone:
        enrichment = {
            "target_audience": target_audience or None,
            "pain_points": pain_points,
            "promotion_type": promotion_type if promotion_type in (
                "organic", "brand_deal", "affiliate", "self_promotion",
            ) else "organic",
            "style_tags": style_tags,
            "tone": tone,
        }

    nid_kpi = int(video.get("niche_id") or 0)
    (save_p25, save_p75), (share_p25, share_p75) = (
        fetch_niche_save_share_pct_quantiles_sync(user_sb, nid_kpi)
        if user_sb is not None and nid_kpi
        else ((None, None), (None, None))
    )

    from getviews_pipeline.content_format_guards import (
        detect_foreign_reup,
        refresh_video_content_format,
    )

    if nid_kpi and analysis:
        refresh_video_content_format(video, analysis, nid_kpi)
    foreign_reup = detect_foreign_reup(analysis)
    content_format_emit: str | None = str(video.get("content_format") or "").strip() or None
    content_class_id_emit: int | None = None
    if video.get("content_class_id") is not None:
        try:
            content_class_id_emit = int(video["content_class_id"])
        except (TypeError, ValueError):
            content_class_id_emit = None

    out = {
        "video_id": video["video_id"],
        "mode": mode,
        "meta": {
            "creator": video.get("creator_handle") or "",
            "views": int(video.get("views") or 0),
            "likes": int(video.get("likes") or 0),
            "comments": int(video.get("comments") or 0),
            "shares": int(video.get("shares") or 0),
            # save_rate is a *ratio* (0–1) — matches video_corpus.save_rate
            # storage and the FE contract (api-types.ts VideoAnalyzeMeta).
            # Some legacy corpus rows may have leaked percent values
            # (>1.0); normalise before emitting so downstream consumers
            # don't have to special-case.
            "save_rate": _normalise_save_rate(video),
            "duration_sec": dur,
            # Frame-first (2026-06-11): the permanent R2 frame capture from
            # the live analysis beats the platform cover — without this, the
            # stored turn payload carried an expiring tiktokcdn URL and the
            # user's own tile went gray when revisiting history weeks later.
            "thumbnail_url": analysis.get("r2_thumbnail_url")
            or video.get("thumbnail_url"),
            "date_posted": (video.get("created_at") or "")[:10]
            if video.get("created_at")
            else None,
            "created_at": video.get("created_at") or None,
            "title": title_hint or None,
            "caption": tiktok_caption or None,
            "hook_phrase": hook_phrase or None,
            "engagement_rate": float(video.get("engagement_rate") or 0.0),
            "niche_label": niche_label or None,
            "niche_id": int(video.get("niche_id") or 0),
            "retention_source": retention_source,
            "creator_median_views": creator_median_views,
            "target_vs_creator_median": target_vs_creator_median,
            # Declared on VideoMeta (report_types.py:469) but previously
            # never set — typed FE consumers always read None. Populate
            # from the corpus row's raw counts / classifiers.
            "saves": int(video.get("saves") or 0) if video.get("saves") is not None else None,
            "is_breakout": float(video.get("breakout_multiplier") or 0.0) >= 1.5,
            "stats_history": video.get("stats_history"),
            "distribution_shape": video.get("distribution_shape"),
            "content_format": content_format_emit,
            "foreign_reup": foreign_reup,
            "content_class_id": content_class_id_emit,
            "boost_attribution": video.get("boost_attribution"),
            "reference_eligible": video.get("reference_eligible"),
        },
        "enrichment": enrichment,
        "kpis": build_kpis(
            video,
            niche_meta,
            mode=mode,
            retention_end_pct=ret_end,
            cohort_save_p25_pct=save_p25,
            cohort_save_p75_pct=save_p75,
            cohort_share_p25_pct=share_p25,
            cohort_share_p75_pct=share_p75,
        ),
        # Corpus-sourced diagnostics rows (written by the batch indexer) don't
        # persist the display-only segment breakdown — recompute from the stored
        # analysis so the structure block never replays empty. decompose_segments
        # always yields a fallback timeline, so this is never empty for a video.
        "segments": diag.get("segments") or decompose_segments(analysis),
        "hook_phases": diag.get("hook_phases") or [],
        "hook_timeline": _normalise_hook_timeline(hook.get("hook_timeline")),
        "errors": diag.get("flop_issues") or [],
        "retention_curve": ret_curve,
        "niche_benchmark_curve": bench_curve,
        "niche_meta": niche_meta,
        "cross_format_signal": cross_format_signal,
        # Cached narrative-layer fields from video_diagnostics
        # (migration 20260513000003). When present, finalize_video_narrative_layer
        # early-returns and skips the Gemini synthesis call.
        "narrative_vi": diag.get("narrative_vi"),
        "format_cards": diag.get("format_cards"),
        "diagnosis": diag.get("diagnosis"),
        "performance_tier": diag.get("performance_tier"),
        "bright_spot_signal": diag.get("bright_spot_signal"),
        "view_scenarios": diag.get("view_scenarios"),
        "channel_context": diag.get("channel_context"),
        "reference_videos": diag.get("reference_videos"),
        "niche_posting_context": diag.get("niche_posting_context"),
    }
    if retention_risk_events:
        out["retention_risk_events"] = retention_risk_events
    _attach_carousel_payload(out, video, analysis)
    return out


# ── Corpus row helpers (UUID guard for video_id collisions) ──────────


_CORPUS_ROW_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def resolve_video_id(sb: Any, *, video_id: str | None, tiktok_url: str | None) -> str:
    """Resolve whatever the caller passed into the canonical TikTok aweme_id.

    Accepts three shapes for `video_id`:
      - TikTok aweme_id (a numeric string like "7630766288574369045") —
        the canonical shape, returned as-is.
      - video_corpus.id (UUID) — some frontend callers (notably the
        Explore grid at src/routes/_app/trends/ExploreScreen.tsx) pass
        the corpus row PK instead of the aweme_id because the
        ExploreGridVideo type only exposes the row id. Tolerate it by
        looking the row up and returning its aweme_id.
      - empty → fall through to tiktok_url lookup.

    The UUID path exists because the shared URL vocab `?video_id=` is
    semantically ambiguous; fixing every call site would touch more
    code than fixing the resolver once. A surface-level frontend fix
    would also make sense for future cleanliness but doesn't change
    the server-side guarantee.
    """
    if video_id and str(video_id).strip():
        vid = str(video_id).strip()
        # UUID shape → treat as corpus row id, not aweme_id.
        if _CORPUS_ROW_UUID_RE.match(vid):
            res = (
                sb.table("video_corpus")
                .select("video_id")
                .eq("id", vid)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if not rows:
                raise ValueError("Không tìm thấy video này trong kho dữ liệu")
            return str(rows[0]["video_id"])
        return vid
    if not tiktok_url or not str(tiktok_url).strip():
        raise ValueError("Cần video_id hoặc tiktok_url")
    url = str(tiktok_url).strip()
    res = (
        sb.table("video_corpus")
        .select("video_id")
        .eq("tiktok_url", url)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise ValueError("Không tìm thấy video này trong kho dữ liệu")
    return str(rows[0]["video_id"])


def _live_analyzed_to_slim_input(result: dict[str, Any]) -> dict[str, Any]:
    """Shape ``analyze_aweme`` output like an aweme dict for ``_slim_reference_video``."""
    meta = result.get("metadata") or {}
    vid = str(meta.get("video_id") or "")
    author = meta.get("author") if isinstance(meta.get("author"), dict) else {}
    handle = str(author.get("username") or "").lstrip("@")
    metrics = meta.get("metrics") if isinstance(meta.get("metrics"), dict) else {}
    desc = str(meta.get("description") or "")[:120]
    return {
        "aweme_id": vid,
        "author": {"unique_id": handle},
        # Frame capture + 30s clip banked during the live analysis — the
        # slim card ships these so live-search references render AND play
        # inline immediately (2026-06-11).
        "thumbnail_url": result.get("r2_thumbnail_url") or meta.get("thumbnail_url"),
        "video_url": result.get("r2_video_url"),
        "statistics": {"play_count": metrics.get("views")},
        "desc": desc or None,
        "engagement_rate": meta.get("engagement_rate"),
        "analysis": result.get("analysis"),
    }


async def _live_search_references_for_finalize(
    niche_name: str,
    target_video_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """EnsembleData niche pool + ``analyze_aweme`` — mirrors sparse path in ``run_video_diagnosis``."""
    from getviews_pipeline.analysis_core import analyze_aweme
    from getviews_pipeline.helpers import select_reference_videos
    from getviews_pipeline.pipelines import REF_N, _niche_aweme_pool, _slim_reference_video
    from getviews_pipeline.runtime import get_analysis_semaphore

    pool = await _niche_aweme_pool(niche_name, period=corpus_reference_fetch_days())
    skip = {target_video_id} if target_video_id else set()
    picks = select_reference_videos(
        pool, recency_days=corpus_reference_pick_days(), n=REF_N, cached_ids=skip, rank_by="er"
    )
    if not picks:
        return [], []

    sem = get_analysis_semaphore()

    async def _one(aweme: dict[str, Any]) -> dict[str, Any]:
        try:
            async with sem:
                # skip_corpus_cache=True avoids get_cached_analysis() which
                # pulls a module-level Supabase httpx transport pinned to
                # whichever event loop first created it. This function runs
                # inside ``asyncio.run(...)`` at video_analyze.py:789 — a
                # fresh loop each invocation — so reusing the prior loop's
                # client raises RuntimeError("Event loop is closed") on
                # the second on-demand request. d4ce4da fixed this for
                # _fetch_and_analyze_async; this analogous site was missed.
                return await asyncio.wait_for(
                    analyze_aweme(
                        aweme,
                        include_diagnosis=False,
                        full_analyses=None,
                        skip_corpus_cache=True,
                    ),
                    timeout=120.0,
                )
        except (TimeoutError, Exception) as exc:
            logger.warning(
                "[finalize_narrative] live ref analyze failed aweme_id=%s: %s",
                aweme.get("aweme_id"),
                exc,
            )
            return {"_skipped": True}

    results = await asyncio.gather(*[_one(a) for a in picks])
    synthesis_refs: list[dict[str, Any]] = []
    slim_refs: list[dict[str, Any]] = []
    for res in results:
        if not isinstance(res, dict) or res.get("_skipped") or "analysis" not in res:
            continue
        meta = res.get("metadata") or {}
        vid = str(meta.get("video_id") or "")
        if not vid:
            continue
        synthesis_refs.append({**res, "aweme_id": vid})
        slim_refs.append(
            _slim_reference_video(_live_analyzed_to_slim_input(res), "live_search")
        )

    if not synthesis_refs:
        return [], []
    return synthesis_refs, slim_refs


def _video_age_days_from_meta(meta: dict[str, Any]) -> float | None:
    """Days since the video was posted — feeds the tier age guard.

    ``meta`` timestamps arrive as epoch ints (EnsembleData ``create_time``)
    or ISO strings (corpus rows). None on anything unparseable so the tier
    falls back to age-blind classification.
    """
    raw = meta.get("created_at") or meta.get("posted_at") or meta.get("create_time")
    if raw is None:
        return None
    try:
        if isinstance(raw, (int, float)) or (isinstance(raw, str) and raw.strip().isdigit()):
            dt = datetime.fromtimestamp(float(raw), tz=UTC)
        else:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
    except (TypeError, ValueError, OSError):
        return None
    age = (datetime.now(tz=UTC) - dt).total_seconds() / 86400.0
    return age if age >= 0 else None


def _build_narrative_cache_update(
    *,
    narrative_vi: dict[str, Any],
    format_cards: list[dict[str, Any]] | None,
    diagnosis_md: str | None,
    performance_tier: str | None,
    bright_spot: dict[str, Any] | None,
    view_scenarios: list[dict[str, Any]] | None,
    channel_context: dict[str, Any] | None,
    reference_videos: list[dict[str, Any]] | None,
    niche_posting_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the conditional UPDATE payload for the narrative cache row.

    Only includes keys whose synth output is actually present. Otherwise a
    partial-success synth (Gemini returned narrative_vi but, say,
    format_cards came back None) would blank a previously-valid cached
    value via UPDATE … SET col = NULL. The next request would
    short-circuit on van_de_chinh and serve the degraded payload with no
    error surface.

    Same family as c69d0cd's narrative_vi gate, generalised to every
    cached field.
    """
    payload: dict[str, Any] = {"narrative_vi": narrative_vi}
    if format_cards is not None:
        payload["format_cards"] = format_cards
    if diagnosis_md:
        payload["diagnosis"] = diagnosis_md
    if performance_tier is not None:
        payload["performance_tier"] = performance_tier
    if bright_spot is not None:
        payload["bright_spot_signal"] = bright_spot
    if view_scenarios is not None:
        payload["view_scenarios"] = view_scenarios
    if channel_context:
        payload["channel_context"] = channel_context
    if reference_videos:
        payload["reference_videos"] = reference_videos
    if niche_posting_context:
        payload["niche_posting_context"] = niche_posting_context
    return payload


def _response_needs_embed_tile_repair(out: dict[str, Any]) -> bool:
    """True when synthesis pool exists but v6 sections lack gap-aligned embedded tiles."""
    from getviews_pipeline.gemini import (
        EMBED_CONTRACT_VERSION,
        count_valid_embedded_tiles,
        gap_sections_missing_peer_tiles,
    )

    if int(out.get("embed_contract_version") or 0) >= EMBED_CONTRACT_VERSION:
        return False
    refs = out.get("reference_videos")
    if not isinstance(refs, list) or len(refs) == 0:
        return False
    narrative = out.get("narrative_vi")
    if not isinstance(narrative, dict):
        return False
    diag = narrative.get("diagnosis_vi")
    if not isinstance(diag, dict):
        return False
    if count_valid_embedded_tiles(diag) == 0:
        return True
    return gap_sections_missing_peer_tiles(diag)


async def _refetch_synthesis_reference_videos(
    out: dict[str, Any],
    *,
    fallback_niche_id: int | None = None,
    user_id: str | None = None,
    service_sb: Any | None = None,
    user_sb: Any | None = None,
) -> list[dict[str, Any]]:
    """Best-effort pool refresh when cached rows lack ``reference_videos``."""
    from getviews_pipeline.services.references import select_synthesis_references_for_video

    meta: dict[str, Any] = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    video_id = str(out.get("video_id") or "")
    video_desc = str(meta.get("caption") or meta.get("title") or "")
    video_hashtags: list[str] = []
    niche_name = str(meta.get("niche_label") or "")
    content_format = str(meta.get("content_format") or "")
    if (not niche_name or int(meta.get("niche_id") or 0) <= 0) and service_sb:
        try:
            from getviews_pipeline.live_niche import resolve_live_niche_id

            aweme_for_niche = {
                "desc": video_desc,
                "challenges": [],
                "author": {"unique_id": str(meta.get("creator") or "").lstrip("@")},
                "text_extra": [],
            }
            resolved_nid = await resolve_live_niche_id(
                service_sb,
                aweme_for_niche,
                fallback_session_niche_id=int(fallback_niche_id or 0) or None,
                user_id=user_id,
            )
            if resolved_nid > 0:
                meta["niche_id"] = resolved_nid
                label_sb = user_sb if user_sb is not None else service_sb
                niche_name = _resolve_niche_label(label_sb, resolved_nid) or niche_name
                out["meta"] = meta
        except Exception as exc:
            logger.warning("[embed_repair] niche resolve failed: %s", exc)

    _, slim_refs, _ = await select_synthesis_references_for_video(
        niche_name=niche_name,
        video_id=video_id,
        video_desc=video_desc,
        video_hashtags=video_hashtags,
        preferred_content_format=content_format or None,
        content_class_id=content_class_id_for_reference_pool(
            meta,
            content_format=content_format,
        ),
        legacy_niche_id=int(meta.get("niche_id") or 0) or None,
        live_search_fn=_live_search_references_for_finalize,
    )
    return slim_refs


def _apply_embed_tile_repair_to_out(
    out: dict[str, Any],
    *,
    fallback_niche_id: int | None = None,
    user_sb: Any | None = None,
    service_sb: Any | None = None,
    user_id: str | None = None,
) -> bool:
    """Mutate *out* with sanitize/inject on cached or fresh v6 diagnosis. Returns True if repaired."""
    from getviews_pipeline.gemini import (
        EMBED_CONTRACT_VERSION,
        repair_diagnosis_vi_embedded_tiles,
    )

    narrative = out.get("narrative_vi")
    if not isinstance(narrative, dict):
        return False
    diag = narrative.get("diagnosis_vi")
    if not isinstance(diag, dict):
        return False

    refs = out.get("reference_videos")
    if not isinstance(refs, list) or len(refs) == 0:
        try:
            slim = asyncio.run(
                _refetch_synthesis_reference_videos(
                    out,
                    fallback_niche_id=fallback_niche_id,
                    user_id=user_id,
                    service_sb=service_sb,
                    user_sb=user_sb,
                )
            )
        except Exception as exc:
            logger.warning("[embed_repair] refetch failed video_id=%s: %s", out.get("video_id"), exc)
            slim = []
        if slim:
            out["reference_videos"] = slim
            refs = slim

    if not refs:
        return False

    before = int(out.get("embed_contract_version") or 0)
    addr = str(out.get("addressing_mode") or "third_party")
    meta_views = (out.get("meta") or {}).get("views") if isinstance(out.get("meta"), dict) else None
    tile_n = repair_diagnosis_vi_embedded_tiles(
        diag,
        refs,
        addressing_mode=addr,
        target_views=int(meta_views or 0) or None,
    )
    out["embed_contract_version"] = EMBED_CONTRACT_VERSION
    out["response_schema_version"] = ON_DEMAND_RESPONSE_SCHEMA_VERSION
    logger.info(
        "[embed_repair] video_id=%s tiles=%d refs=%d prior_contract=%s",
        out.get("video_id"),
        tile_n,
        len(refs),
        before,
    )
    return tile_n > 0


def _persist_embed_repair_to_diagnostics(out: dict[str, Any]) -> None:
    """Write repaired narrative/refs back to ``video_diagnostics`` (non-fatal)."""
    narrative = out.get("narrative_vi")
    if not isinstance(narrative, dict):
        return
    try:
        from getviews_pipeline.supabase_client import get_service_client

        sb = get_service_client()
        cache_vid = str(out.get("video_id") or "")
        if not cache_vid:
            return

        update_payload = _build_narrative_cache_update(
            narrative_vi=narrative,
            format_cards=out.get("format_cards") if isinstance(out.get("format_cards"), list) else None,
            diagnosis_md=str(out.get("diagnosis") or "") or None,
            performance_tier=str(out.get("performance_tier") or "") or None,
            bright_spot=out.get("bright_spot_signal")
            if isinstance(out.get("bright_spot_signal"), dict)
            else None,
            view_scenarios=out.get("view_scenarios")
            if isinstance(out.get("view_scenarios"), list)
            else None,
            channel_context=out.get("channel_context")
            if isinstance(out.get("channel_context"), dict)
            else None,
            reference_videos=out.get("reference_videos")
            if isinstance(out.get("reference_videos"), list)
            else None,
            niche_posting_context=out.get("niche_posting_context")
            if isinstance(out.get("niche_posting_context"), dict)
            else None,
        )
        if update_payload:
            depth = _normalize_analysis_depth(
                out.get("__analysis_depth") or out.get("__cache_analysis_depth"),
            )
            sb.table("video_diagnostics").update(update_payload).eq(
                "video_id", cache_vid,
            ).eq("analysis_depth", depth).execute()

        on_demand_url = out.get("__cache_on_demand_url") or out.get("tiktok_url")
        if str(out.get("source") or "") == "on_demand" and on_demand_url:
            cacheable = {k: v for k, v in out.items() if not str(k).startswith("__")}
            _persist_on_demand_cache(
                sb,
                tiktok_url=str(on_demand_url),
                video_id=cache_vid,
                response=cacheable,
                analysis_depth=_normalize_analysis_depth(out.get("__analysis_depth")),
            )
    except Exception as exc:
        logger.warning(
            "[embed_repair] diagnostics persist failed video_id=%s: %s",
            out.get("video_id"),
            exc,
        )


def _finalize_report_depth_fields(out: dict[str, Any]) -> None:
    """User-facing analysis is always deep; strip legacy upsell metadata."""
    out["analysis_depth"] = "deep"
    out.pop("locked_sections", None)


def finalize_video_narrative_layer(
    out: dict[str, Any],
    *,
    step_queue: Any | None = None,
    fallback_niche_id: int | None = None,
    user_sb: Any | None = None,
    service_sb: Any | None = None,
    user_id: str | None = None,
    analysis_depth: str | None = None,
) -> None:
    """Call 2 — narrative synthesis + SSE; mutates *out* in place.

    Expects ``out`` to contain private keys ``__narrative_analysis`` and
    ``__narrative_content_format`` (stripped before return to clients) set by
    ``run_video_analyze_pipeline`` / ``run_video_analyze_on_demand``.

    Idempotent: when ``out`` already carries cached narrative fields
    (set by ``_response_from_diagnostics_row`` on a video_diagnostics
    cache hit), this function returns without re-firing the Gemini
    synthesis call. The cache is populated below on the cache-miss path.
    """
    depth = _normalize_analysis_depth(
        out.pop("__analysis_depth", None) or analysis_depth,
    )

    # Cache hit short-circuit. narrative_vi is the anchor — when it
    # exists, every dependent field (format_cards, performance_tier,
    # bright_spot_signal, view_scenarios, channel_context,
    # reference_videos, diagnosis) was written in the same upsert.
    #
    # v5 gate: also require narrative_vi.van_de_chinh (v5-specific field
    # introduced in Phase 4.3). Old corpus rows have narrative_vi but lack
    # van_de_chinh — they must go through v5 synthesis to produce the v5
    # output shape. This ensures corpus cache hits always return v5 responses.
    _narrative = out.get("narrative_vi")
    if (
        _narrative
        and isinstance(_narrative, dict)
        and _narrative.get("van_de_chinh")
    ):
        if _response_needs_embed_tile_repair(out):
            _apply_embed_tile_repair_to_out(
                out,
                fallback_niche_id=fallback_niche_id,
                user_sb=user_sb,
                service_sb=service_sb,
                user_id=user_id,
            )
            _persist_embed_repair_to_diagnostics(out)
        else:
            from getviews_pipeline.gemini import EMBED_CONTRACT_VERSION

            if int(out.get("embed_contract_version") or 0) < EMBED_CONTRACT_VERSION:
                out["embed_contract_version"] = EMBED_CONTRACT_VERSION
        _finalize_report_depth_fields(out)
        from getviews_pipeline.voice_copy import humanize_video_report_out

        humanize_video_report_out(out)
        # Strip pipeline-private keys so the response shape stays clean
        # for the caller (matches the post-synthesis branch below).
        out.pop("__narrative_analysis", None)
        out.pop("__narrative_content_format", None)
        _strip_on_demand_client_cache_fields(out)
        return

    from getviews_pipeline.diagnosis_synthesis_contract import diagnosis_synthesis_kwargs
    from getviews_pipeline.gemini import synthesize_diagnosis_v2
    from getviews_pipeline.pipelines import (
        _estimate_er_percentile_rank,
        _truncate_transcripts,
        classify_performance_tier_corpus,
        compute_bright_spot_signal,
        compute_view_scenarios,
        enrich_format_cards_from_corpus,
        refine_performance_tier,
    )

    # Phase 5.5 — use the cached wrapper; same API as pipelines version.
    from getviews_pipeline.services.channel import fetch_channel_context_sync
    from getviews_pipeline.step_events import emit

    analysis: dict[str, Any] = out.pop("__narrative_analysis", None) or {}
    content_format: str = str(out.pop("__narrative_content_format", "") or "")
    from getviews_pipeline.two_axis_taxonomy import extract_subject_matter_from_analysis_json

    user_subject_matter = extract_subject_matter_from_analysis_json(analysis)
    meta: dict[str, Any] = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    niche_meta: dict[str, Any] = (
        out.get("niche_meta") if isinstance(out.get("niche_meta"), dict) else {}
    )

    video_id = str(out.get("video_id") or "")
    video_desc = str(
        out.pop("__tiktok_desc", None)
        or meta.get("caption")
        or meta.get("title")
        or ""
    )
    video_hashtags = list(out.pop("__tiktok_hashtags", None) or [])

    session_fallback = int(
        fallback_niche_id
        or out.pop("__fallback_niche_id", 0)
        or 0
    )
    if session_fallback > 0 and user_sb is not None:
        _apply_studio_session_niche_cohort(
            out, session_fallback, user_sb=user_sb,
        )
        meta = out.get("meta") if isinstance(out.get("meta"), dict) else meta
        niche_meta = (
            out.get("niche_meta") if isinstance(out.get("niche_meta"), dict) else niche_meta
        )
    elif (
        (not str(meta.get("niche_label") or "").strip() or int(meta.get("niche_id") or 0) <= 0)
        and service_sb
    ):
        try:
            from getviews_pipeline.live_niche import resolve_live_niche_id

            aweme_for_niche = out.pop("__aweme_for_niche", None)
            if not isinstance(aweme_for_niche, dict):
                aweme_for_niche = {
                    "desc": video_desc,
                    "challenges": [],
                    "author": {"unique_id": str(meta.get("creator") or "").lstrip("@")},
                    "text_extra": [{"hashtag_name": h} for h in video_hashtags if h],
                }
            resolved_nid = asyncio.run(
                resolve_live_niche_id(
                    service_sb,
                    aweme_for_niche,
                    fallback_session_niche_id=session_fallback or None,
                    user_id=user_id,
                )
            )
            if resolved_nid > 0:
                meta["niche_id"] = resolved_nid
                label_sb = user_sb if user_sb is not None else service_sb
                niche_label_fixed = _resolve_niche_label(label_sb, resolved_nid)
                if niche_label_fixed:
                    meta["niche_label"] = niche_label_fixed
                    out["meta"] = meta
                if user_sb is not None:
                    niche_intel_fix, bench_axis = fetch_video_benchmark_with_axis(
                        user_sb,
                        niche_id=resolved_nid,
                        content_class_id=None,
                    )
                    bench_fix = build_niche_benchmark_payload(
                        niche_intel_fix,
                        niche_id=resolved_nid,
                        duration_sec=float(meta.get("duration_sec") or 30.0),
                        user_sb=user_sb,
                        benchmark_axis=bench_axis,
                    )
                    if bench_fix.get("niche_meta"):
                        niche_meta = bench_fix["niche_meta"]
                        niche_meta["benchmark_axis"] = bench_axis
                        out["niche_meta"] = niche_meta
                        if bench_fix.get("niche_benchmark_curve"):
                            out["niche_benchmark_curve"] = bench_fix["niche_benchmark_curve"]
        except Exception as exc:
            logger.warning("[video_narrative] live niche resolve failed: %s", exc)

    niche_name = str(meta.get("niche_label") or "")
    from getviews_pipeline.services.references import select_synthesis_references_for_video
    from getviews_pipeline.video_report_coherence import effective_depth_tier, ref_n_for_tier

    _ref_views = int(meta.get("views") or 0)
    _ref_corpus_avg = float(niche_meta.get("avg_views") or 0.0)
    _ref_tier_pre = classify_performance_tier_corpus(
        _ref_views,
        _ref_corpus_avg or None,
        video_age_days=_video_age_days_from_meta(meta),
    )
    # Cohort-less flop guard — a thin-niche flop (tier=unknown but stored
    # mode=flop) still pulls the wider flop reference set so the creator has
    # more concrete examples to fix against.
    _ref_depth_tier = effective_depth_tier(_ref_tier_pre, out.get("mode"))

    synthesis_refs, slim_refs, evidence_block = asyncio.run(
        select_synthesis_references_for_video(
            niche_name=niche_name,
            video_id=video_id,
            video_desc=video_desc,
            video_hashtags=video_hashtags,
            preferred_content_format=content_format or None,
            user_subject_matter=user_subject_matter,
            content_class_id=content_class_id_for_reference_pool(
                meta,
                content_format=content_format,
            ),
            legacy_niche_id=int(meta.get("niche_id") or 0) or None,
            live_search_fn=_live_search_references_for_finalize,
            ref_n=ref_n_for_tier(_ref_depth_tier),
        )
    )
    out["reference_videos"] = slim_refs

    _ensure_comment_radar_on_out(out)
    _attach_hook_effectiveness_for_diagnosis(out, user_sb=user_sb)

    views = int(meta.get("views") or 0)
    corpus_avg_views = float(niche_meta.get("avg_views") or 0.0)
    performance_tier: str = classify_performance_tier_corpus(
        views,
        corpus_avg_views or None,
        video_age_days=_video_age_days_from_meta(meta),
    )

    channel_context_payload: dict[str, Any] | None = None
    creator_handle = str(meta.get("creator") or "").strip()
    if creator_handle and video_id:
        try:
            raw_ctx = fetch_channel_context_sync(creator_handle, video_id)
            if raw_ctx and raw_ctx.get("available"):
                channel_context_payload = raw_ctx
                performance_tier = refine_performance_tier(performance_tier, views, raw_ctx)
        except Exception:
            logger.debug("[video_narrative] channel context fetch failed")

    from getviews_pipeline.video_report_coherence import (
        build_video_related_questions,
        filter_structural_errors_for_tier,
        reconcile_video_mode,
        resolve_stored_video_mode,
        should_fill_related_questions,
    )

    cmv_raw = meta.get("creator_median_views")
    try:
        cmv_finalize = int(cmv_raw) if cmv_raw is not None else None
    except (TypeError, ValueError):
        cmv_finalize = None
    tvr_raw = meta.get("target_vs_creator_median")
    try:
        tvr_finalize = float(tvr_raw) if tvr_raw is not None else None
    except (TypeError, ValueError):
        tvr_finalize = None
    if channel_context_payload and channel_context_payload.get("median_views"):
        try:
            live_median = int(channel_context_payload["median_views"])
            if live_median > 0 and views > 0:
                cmv_finalize = live_median
                tvr_finalize = round(views / live_median, 2)
        except (TypeError, ValueError):
            pass

    _tier_lc = str(performance_tier or "unknown").lower()
    if _tier_lc in ("hit", "flop", "average", "early"):
        mode_reconciled = resolve_stored_video_mode(
            performance_tier,
            views=views,
            creator_median_views=cmv_finalize,
            target_vs_creator_median=tvr_finalize,
        )
    else:
        mode_reconciled = reconcile_video_mode(
            str(out.get("mode") or "win"),
            performance_tier,
            views=views,
            creator_median_views=cmv_finalize,
            target_vs_creator_median=tvr_finalize,
        )
    if mode_reconciled != str(out.get("mode") or ""):
        logger.info(
            "[video_narrative] report mode reconciled %s -> %s (tier=%s video_id=%s)",
            out.get("mode"),
            mode_reconciled,
            performance_tier,
            video_id,
        )
    out["mode"] = mode_reconciled

    errors: list[dict[str, Any]] = filter_structural_errors_for_tier(
        list(out.get("errors") or out.get("structural_errors") or []),
        performance_tier,
        views=views,
        creator_median_views=cmv_finalize,
        target_vs_creator_median=tvr_finalize,
    )
    out["errors"] = errors
    out["structural_errors"] = errors

    if should_fill_related_questions(out):
        out["related_questions"] = build_video_related_questions(
            performance_tier=performance_tier,
            mode=mode_reconciled,
            creator_handle=creator_handle or None,
            niche_label=niche_name or None,
            content_format=str(meta.get("content_format") or content_format or "") or None,
            views=views,
            creator_median_views=cmv_finalize,
            target_vs_creator_median=tvr_finalize,
        )

    if step_queue is not None:
        # views_vs_avg_ratio / corpus_size are computed further down — derive
        # the same numbers from what's in scope here for the streamed chip.
        pre_ratio = round(float(views) / corpus_avg_views, 2) if corpus_avg_views else None
        pre_bench_n = int(niche_meta.get("sample_size") or niche_meta.get("corpus_size") or 0)
        emit(
            step_queue,
            {
                "type": "pre_synthesis",
                "performance_tier": performance_tier,
                **({"tier_ratio": pre_ratio} if pre_ratio is not None else {}),
                **({"tier_benchmark_n": pre_bench_n} if pre_bench_n else {}),
                "reference_videos": out.get("reference_videos") or [],
            },
        )
        if channel_context_payload:
            emit(
                step_queue,
                {"type": "channel_context", "channel_context": channel_context_payload},
            )

    corpus_size = int(niche_meta.get("sample_size") or niche_meta.get("corpus_size") or 0)
    user_stats: dict[str, Any] = {
        "views": views,
        "likes": int(meta.get("likes") or 0),
        "comments": int(meta.get("comments") or 0),
        "shares": int(meta.get("shares") or 0),
        "duration_sec": float(meta.get("duration_sec") or 0.0),
        "save_rate": float(meta.get("save_rate") or 0.0),
        "caption": str(meta.get("caption") or video_desc or ""),
    }

    user_er = float(meta.get("engagement_rate") or 0.0)
    raw_ae = niche_meta.get("avg_engagement_rate")
    raw_me = niche_meta.get("median_er")
    try:
        niche_avg_er = float(raw_ae) if raw_ae is not None else None
    except (TypeError, ValueError):
        niche_avg_er = None
    if niche_avg_er is None or niche_avg_er <= 0:
        try:
            niche_avg_er = float(raw_me) if raw_me is not None else None
        except (TypeError, ValueError):
            niche_avg_er = None
    if niche_avg_er is not None and niche_avg_er <= 0:
        niche_avg_er = None
    er_percentile_rank = _estimate_er_percentile_rank(user_er, niche_avg_er)
    try:
        cohort_avg_views = float(niche_meta.get("avg_views") or 0) or None
    except (TypeError, ValueError):
        cohort_avg_views = None
    if cohort_avg_views is not None and cohort_avg_views <= 0:
        cohort_avg_views = None
    views_vs_avg_ratio = (
        float(views) / cohort_avg_views if cohort_avg_views and views >= 0 else None
    )
    curve_raw = out.get("retention_curve")
    retention_end_pct: float | None = None
    if isinstance(curve_raw, list) and curve_raw:
        last_pt = curve_raw[-1]
        if isinstance(last_pt, dict) and last_pt.get("pct") is not None:
            try:
                retention_end_pct = float(last_pt["pct"])
            except (TypeError, ValueError):
                retention_end_pct = None
    user_stats["engagement_rate"] = float(user_er)
    if retention_end_pct is not None:
        user_stats["retention_end_pct"] = retention_end_pct
    meta_ret_src = meta.get("retention_source")
    if meta_ret_src:
        user_stats["retention_source"] = str(meta_ret_src)
    risk_ev = out.get("retention_risk_events")
    if isinstance(risk_ev, list) and risk_ev:
        user_stats["retention_risk_events"] = risk_ev
    cmv_raw = meta.get("creator_median_views")
    if cmv_raw is not None:
        try:
            user_stats["creator_median_views"] = int(cmv_raw)
        except (TypeError, ValueError):
            pass
    tvr_raw = meta.get("target_vs_creator_median")
    if tvr_raw is not None:
        try:
            user_stats["target_vs_creator_median"] = float(tvr_raw)
        except (TypeError, ValueError):
            pass
    if views_vs_avg_ratio is not None:
        user_stats["views_vs_avg_ratio"] = float(views_vs_avg_ratio)
    ts_posted = meta.get("created_at") or meta.get("posted_at")
    if ts_posted:
        user_stats["posted_at"] = str(ts_posted)
    _age_days = _video_age_days_from_meta(meta)
    if _age_days is not None:
        user_stats["video_age_days"] = round(_age_days, 1)
    cc_raw = meta.get("commerce_conversion")
    if isinstance(cc_raw, dict) and cc_raw:
        user_stats["commerce_conversion"] = cc_raw
    elif meta.get("shop_order_count") is not None:
        try:
            user_stats["shop_order_count"] = int(meta["shop_order_count"])
        except (TypeError, ValueError):
            pass
    sh_raw = meta.get("stats_history")
    if isinstance(sh_raw, list) and sh_raw:
        user_stats["stats_history"] = sh_raw
    ds_raw = meta.get("distribution_shape")
    if ds_raw:
        user_stats["distribution_shape"] = str(ds_raw)
    # Stored boost attribution — the FE chip renders this exact value, so
    # signals must coordinate with it (seeding signal suppressed when the
    # chip says "Organic"; bug 2026-06-12).
    ba_raw = meta.get("boost_attribution")
    if ba_raw:
        user_stats["boost_attribution"] = str(ba_raw)
    ch_ratio_hint = meta.get("target_vs_creator_median")
    try:
        ch_ratio_f = float(ch_ratio_hint) if ch_ratio_hint is not None else None
    except (TypeError, ValueError):
        ch_ratio_f = None
    bright_spot_computed = compute_bright_spot_signal(
        er_percentile_rank,
        views_vs_avg_ratio,
        retention_end_pct=retention_end_pct,
        channel_views_ratio=ch_ratio_f,
    )
    view_scenarios_computed = compute_view_scenarios(
        performance_tier=performance_tier,
        views_vs_avg_ratio=views_vs_avg_ratio,
        channel_views_ratio=ch_ratio_f,
    )
    errors_prompt = list(errors)

    from getviews_pipeline.analysis_addressing import (
        fetch_viewer_tiktok_handle,
        resolve_video_addressing_mode,
    )

    viewer_handle = fetch_viewer_tiktok_handle(user_sb, user_id)
    addressing_mode = resolve_video_addressing_mode(
        video_creator_handle=creator_handle,
        viewer_tiktok_handle=viewer_handle,
    )
    out["addressing_mode"] = addressing_mode

    creator_format_history_block = ""
    if creator_handle:
        _hist = get_creator_format_history_sync(creator_handle, 10)
        creator_format_history_block = format_creator_format_history_for_diagnosis(
            creator_handle,
            _hist,
        )

    try:
        from getviews_pipeline.douyin_match import enrich_analysis_with_douyin_match
        from getviews_pipeline.supabase_client import get_service_client

        enrich_analysis_with_douyin_match(analysis, user_stats, get_service_client())
    except Exception:
        logger.debug("[video_narrative] douyin_match enrich skipped", exc_info=True)

    diagnosis_md = ""
    narrative_vi_out: dict[str, Any] | None = None
    format_cards_out: list[dict[str, Any]] | None = None
    try:
        diagnosis_md, narrative_vi_out, format_cards_out = synthesize_diagnosis_v2(
            **diagnosis_synthesis_kwargs(
                content_format=content_format or "unknown",
                niche_name=niche_name or "unknown",
                corpus_size=corpus_size,
                niche_meta=niche_meta,
                reference_videos=_truncate_transcripts(synthesis_refs),
                user_analysis=analysis,
                user_stats=user_stats,
                collapsed_questions=None,
                wants_directions=False,
                layer0_context="",
                corpus_citation="",
                persona_block="",
                performance_tier=performance_tier,
                channel_context=channel_context_payload,
                errors=errors_prompt or None,
                reference_evidence_block=evidence_block,
                creator_format_history_block=creator_format_history_block,
                cross_format_signal=(
                    out.get("cross_format_signal")
                    if isinstance(out.get("cross_format_signal"), dict)
                    else None
                ),
                niche_posting_context_block="",
                comment_radar=(
                    out.get("comment_radar")
                    if isinstance(out.get("comment_radar"), dict)
                    else None
                ),
                hook_effectiveness=(
                    out.get("hook_effectiveness")
                    if isinstance(out.get("hook_effectiveness"), list)
                    else None
                ),
                addressing_mode=addressing_mode,
                video_creator_handle=creator_handle or None,
            ),
        )
    except Exception:
        logger.exception("[video_narrative] synthesize_diagnosis_v2 failed")

    if narrative_vi_out is None:
        logger.warning(
            "[video_narrative] narrative_vi_out is None after synthesis — "
            "van_de_chinh will be missing. errors_prompt_len=%d analysis_keys=%s",
            len(errors_prompt),
            list((analysis or {}).keys())[:5],
        )
    if narrative_vi_out is not None and slim_refs:
        diag_pre = narrative_vi_out.get("diagnosis_vi")
        if isinstance(diag_pre, dict):
            from getviews_pipeline.gemini import repair_diagnosis_vi_embedded_tiles

            repair_diagnosis_vi_embedded_tiles(
                diag_pre,
                slim_refs,
                addressing_mode=str(out.get("addressing_mode") or "third_party"),
                target_views=int(user_stats.get("views") or 0) or None,
            )

    if narrative_vi_out is not None:
        dur_note = float(meta.get("duration_sec") or user_stats.get("duration_sec") or 0.0)
        # er_percentile_rank here is a ratio-derived score (~5–95), not a literal corpus
        # percentile — treat as a low-engagement proxy vs retention on short clips.
        if (
            dur_note > 0
            and dur_note <= 15.0
            and retention_end_pct is not None
            and retention_end_pct >= 75.0
            and er_percentile_rank is not None
            and er_percentile_rank < 40.0
        ):
            note = (
                "Lưu ý: với video ngắn dưới 15 giây, tỷ lệ giữ chân cao thường "
                "phản ánh độ dài clip chứ không phải mức độ quan tâm thực sự — "
                "chỉ số quyết định phân phối vẫn là ER và tỷ lệ lưu."
            )
            vd0 = str(narrative_vi_out.get("van_de_chinh") or "").strip()
            if note not in vd0:
                narrative_vi_out["van_de_chinh"] = f"{vd0} {note}".strip() if vd0 else note

    niche_id_finalize = int(meta.get("niche_id") or 0)
    if format_cards_out and niche_id_finalize:
        format_cards_out = enrich_format_cards_from_corpus(
            format_cards_out,
            niche_id_finalize,
            analyzed_content_format=content_format or None,
        )

    if step_queue is not None:
        emit(
            step_queue,
            {
                "type": "narrative_ready",
                "narrative_vi": narrative_vi_out,
                "format_cards": format_cards_out,
                "errors": errors,
                **(
                    {"bright_spot_signal": bright_spot_computed}
                    if bright_spot_computed is not None
                    else {}
                ),
                **(
                    {"view_scenarios": view_scenarios_computed}
                    if view_scenarios_computed is not None
                    else {}
                ),
            },
        )

    out["errors"] = errors
    out["structural_errors"] = errors
    if bright_spot_computed is not None:
        out["bright_spot_signal"] = bright_spot_computed
    if view_scenarios_computed is not None:
        out["view_scenarios"] = view_scenarios_computed
    out["performance_tier"] = performance_tier
    # Benchmark transparency — the FE chip shows the ratio that *generates*
    # the tier (and gates the verdict on benchmark sample size) instead of
    # a bare HIT/FLOP badge.
    if views_vs_avg_ratio is not None:
        out["tier_ratio"] = round(float(views_vs_avg_ratio), 2)
    if corpus_size:
        out["tier_benchmark_n"] = int(corpus_size)
    if channel_context_payload:
        out["channel_context"] = channel_context_payload
    if narrative_vi_out is not None:
        out["narrative_vi"] = narrative_vi_out
    if format_cards_out is not None:
        out["format_cards"] = format_cards_out
    if diagnosis_md:
        out["diagnosis"] = diagnosis_md
    # Phase 4.4.6 — stable BE marker so the FE can detect v5 responses
    # without brittle sentence-count heuristics on van_de_chinh.
    out["_schema_version"] = "v5"

    if _response_needs_embed_tile_repair(out):
        _apply_embed_tile_repair_to_out(
            out,
            fallback_niche_id=fallback_niche_id,
            user_sb=user_sb,
            service_sb=service_sb,
            user_id=user_id,
        )
    else:
        from getviews_pipeline.gemini import EMBED_CONTRACT_VERSION

        out["embed_contract_version"] = EMBED_CONTRACT_VERSION

    # Persist the narrative layer alongside the deterministic one so
    # the next request on the same video_id within the diagnostics TTL
    # short-circuits at the top of this function. on_demand outputs
    # don't have a corpus row (and aren't cached), so guard by
    # presence of __cache_video_id which run_video_analyze_pipeline
    # sets on the corpus path only.
    cache_vid = out.pop("__cache_video_id", None)
    if cache_vid and narrative_vi_out is not None:
        update_payload = _build_narrative_cache_update(
            narrative_vi=narrative_vi_out,
            format_cards=format_cards_out,
            diagnosis_md=diagnosis_md,
            performance_tier=performance_tier,
            bright_spot=bright_spot_computed,
            view_scenarios=view_scenarios_computed,
            channel_context=channel_context_payload,
            reference_videos=out.get("reference_videos"),
            niche_posting_context=None,
        )
        try:
            from getviews_pipeline.supabase_client import get_service_client

            get_service_client().table("video_diagnostics").update(
                update_payload,
            ).eq("video_id", cache_vid).eq("analysis_depth", depth).execute()
        except Exception as exc:
            # Non-fatal — failing to cache only loses the cost saving,
            # not the user-visible response. Bubble exception to logs.
            logger.warning(
                "[video_narrative] persist failed video_id=%s: %s", cache_vid, exc,
            )

    # On-demand persist. Strip pipeline-private keys and write the full
    # enriched response to ``cached_response`` so subsequent hits on the
    # same TikTok URL bypass the entire Gemini pipeline.
    on_demand_url = out.pop("__cache_on_demand_url", None)
    on_demand_vid = out.pop("__cache_on_demand_vid", None)
    if on_demand_url and on_demand_vid:
        from getviews_pipeline.observability import log_cache_event
        from getviews_pipeline.supabase_client import get_service_client

        service_client = get_service_client()
        cacheable = {k: v for k, v in out.items() if not k.startswith("__")}
        if isinstance(analysis, dict) and analysis:
            cacheable["extract_json"] = analysis
            cacheable["extract_schema_version"] = EXTRACT_JSON_SCHEMA_VERSION
        _persist_on_demand_cache(
            service_client,
            tiktok_url=on_demand_url,
            video_id=on_demand_vid,
            response=cacheable,
            analysis_depth=depth,
        )
        log_cache_event(
            event="cache_write",
            cache_source="on_demand_cache",
            video_id=on_demand_vid,
        )

        # Phase 5.1b — promote on-demand extraction to video_corpus.
        # The analysis was already paid for; adding the row grows the corpus
        # for free and improves future cohort benchmarks.
        try:
            from getviews_pipeline.services.corpus_quality import promote_on_demand_to_corpus

            _meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
            _analysis = analysis  # captured above before pop
            _niche_id_raw = _meta.get("niche_id") or out.get("niche_id")
            _niche_id = int(_niche_id_raw) if _niche_id_raw is not None else None
            if _niche_id and _analysis:
                promote_on_demand_to_corpus(
                    service_client,
                    video_id=on_demand_vid,
                    tiktok_url=on_demand_url,
                    creator_handle=str(_meta.get("creator_handle") or ""),
                    niche_id=_niche_id,
                    analysis_json=_analysis,
                    views=int(_meta.get("views") or 0),
                    likes=int(_meta.get("likes") or 0),
                    comments=int(_meta.get("comments") or 0),
                    shares=int(_meta.get("shares") or 0),
                    engagement_rate=float(_meta.get("engagement_rate") or 0.0),
                    content_type=str(_meta.get("content_type") or "video"),
                    thumbnail_url=str(_meta.get("thumbnail_url") or "") or None,
                )
        except Exception as _exc:
            logger.warning("[finalize] corpus promote failed video_id=%s: %s", on_demand_vid, _exc)

    _finalize_report_depth_fields(out)
    from getviews_pipeline.voice_copy import humanize_video_report_out

    humanize_video_report_out(out)
    _strip_on_demand_client_cache_fields(out)


def run_video_analyze_pipeline(
    service_sb: Any,
    user_sb: Any,
    *,
    video_id: str | None,
    tiktok_url: str | None,
    force_refresh: bool = False,
    mode: Literal["win", "flop"] | None = None,
    query_hint: str | None = None,
    step_queue: Any | None = None,
    analysis_depth: str | None = None,
    session_niche_id: int | None = None,
) -> dict[str, Any]:
    """Sync pipeline: read cache, else compute + Gemini + upsert. Returns API dict.

    When ``force_refresh`` is True, skip the 1h ``video_diagnostics`` TTL and
    always re-run Gemini + curve modeling (then upsert). Intended for debugging
    / prompt iteration only.

    When ``mode`` is ``"win"`` or ``"flop"``, that branch is used instead of
    the ``is_flop_mode`` heuristic. Because ``video_diagnostics`` is keyed by
    ``(video_id, analysis_depth)``, a mode override skips the fresh-diagnostics
    cache for that depth — same as an implicit ``force_refresh`` — so the
    response matches the requested path and the row is recomputed/upserted.
    """
    depth = _normalize_analysis_depth(analysis_depth)
    vid = resolve_video_id(user_sb, video_id=video_id, tiktok_url=tiktok_url)

    dres = (
        user_sb.table("video_diagnostics")
        .select("*")
        .eq("video_id", vid)
        .eq("analysis_depth", depth)
        .limit(1)
        .execute()
    )
    diag_row = (dres.data or [None])[0]

    video = _fetch_corpus_row(user_sb, vid)

    corpus_niche_id = int(video.get("niche_id") or 0)
    niche_id = (
        int(session_niche_id)
        if session_niche_id and int(session_niche_id) > 0
        else corpus_niche_id
    )
    from getviews_pipeline.content_format_guards import (
        coerce_analysis_dict,
        refresh_video_content_format,
    )

    analysis = coerce_analysis_dict(video.get("analysis_json"))
    # Re-classify BEFORE benchmark fetch so cohort + meta.content_class_id
    # match the guarded content_format (fixes stale haul→highlight rows).
    if niche_id and analysis:
        refresh_video_content_format(video, analysis, niche_id)
    elif video.get("content_format") and niche_id:
        from getviews_pipeline.corpus_ingest import _content_class_for

        content_class_id_fb = video.get("content_class_id")
        if content_class_id_fb is None or (
            session_niche_id and int(session_niche_id) > 0 and niche_id != corpus_niche_id
        ):
            content_class_id_fb = _content_class_for(niche_id, video.get("content_format"))
        if content_class_id_fb is not None:
            video["content_class_id"] = content_class_id_fb
    content_class_id = video.get("content_class_id")
    creator_tier = str(video.get("creator_tier") or "").strip() or None
    niche_intel, benchmark_axis = fetch_video_benchmark_with_axis(
        user_sb,
        niche_id=niche_id,
        content_class_id=content_class_id,
        creator_tier=creator_tier,
    )
    # A.1 — cross-niche format signal. Cheap read; returns None when
    # format is single-niche or sample is too thin so the FE renders
    # only when meaningful.
    from getviews_pipeline.cross_format import get_cross_format_signal
    cross_format_signal = get_cross_format_signal(
        user_sb,
        content_class_id=content_class_id,
        content_format=str(video.get("content_format") or "").strip() or None,
    )
    default_niche_meta = {
        "avg_views": None,
        "avg_retention": 0.5,
        "avg_ctr": 0.04,
        "sample_size": 0,
        "winners_sample_size": None,
    }
    dur = video_duration_sec(analysis)

    bypass_cache = force_refresh
    heuristic_mode: Literal["win", "flop"] = (
        "flop" if is_flop_mode(video, niche_intel) else "win"
    )

    from getviews_pipeline.video_report_coherence import pipeline_reconcile_mode

    caller_mode = mode if mode in ("win", "flop") else None
    mode_resolved = pipeline_reconcile_mode(
        heuristic_mode,
        video,
        niche_intel,
        query_hint=query_hint,
        caller_mode=caller_mode,
    )

    bench_payload = build_niche_benchmark_payload(
        niche_intel,
        niche_id=niche_id or 0,
        duration_sec=max(dur, 5.0),
        user_sb=user_sb,
        benchmark_axis=benchmark_axis,
        content_class_id=int(content_class_id) if content_class_id else None,
    )
    niche_benchmark = bench_payload["niche_benchmark_curve"]
    niche_meta = bench_payload["niche_meta"] if bench_payload.get("niche_meta") is not None else default_niche_meta
    # A.2.3 — tag meta with which axis the benchmark came from so the FE
    # can render "vs N similar-format videos" vs "vs N videos in your niche".
    if niche_meta is not default_niche_meta:
        niche_meta["benchmark_axis"] = benchmark_axis
        niche_meta = _apply_peer_tier_to_niche_meta(
            niche_meta,
            benchmark_axis=benchmark_axis,
            benchmark_row=niche_intel,
            views=int(video.get("views") or 0),
            content_format=str(video.get("content_format") or ""),
        )
    rs = bench_payload.get("retention_source") or "modeled"
    retention_source: RetentionSource = "real" if rs == "real" else "modeled"

    niche_label_resolved = _resolve_niche_label(user_sb, niche_id) if niche_id else ""

    bm = float(video.get("breakout_multiplier") or 1.0)
    retention_user, retention_structural_source, retention_risk_events = (
        _resolve_user_retention_curve(
            duration_sec=dur,
            analysis=analysis,
            niche_median_retention=float(niche_meta["avg_retention"]),
            breakout_multiplier=bm,
            video_id=vid,
            content_format=str(video.get("content_format") or ""),
        )
    )
    if retention_structural_source:
        retention_source = retention_structural_source

    if (
        diag_row
        and _diagnostics_fresh(diag_row)
        and not bypass_cache
        and not _diagnostics_legacy(diag_row)
    ):
        age_min = _cache_age_minutes(diag_row)
        logger.info(
            "[video_analyze] cache hit: video_id=%s age_min=%d force_refresh=%s",
            vid,
            age_min,
            force_refresh,
        )
        base = _response_from_diagnostics_row(
            video,
            diag_row,
            mode=mode_resolved,
            niche_meta=niche_meta,
            niche_benchmark=niche_benchmark,
            retention_user=retention_user,
            niche_label=niche_label_resolved,
            retention_source=retention_source,
            cross_format_signal=cross_format_signal,
            retention_risk_events=retention_risk_events or None,
            user_sb=user_sb,
        )
        base["__narrative_analysis"] = analysis
        base["__narrative_content_format"] = str(video.get("content_format") or "")
        base["__analysis_depth"] = depth
        # Cache key for finalize_video_narrative_layer's persist step.
        base["__cache_video_id"] = vid
        base["__cache_analysis_depth"] = depth
        if session_niche_id and int(session_niche_id) > 0:
            _apply_studio_session_niche_cohort(base, session_niche_id, user_sb=user_sb)
        return _merge_sidecars_into_response(
            base,
            video_id=vid,
            comment_count_hint=int(video.get("comments") or 0),
        )

    if diag_row and _diagnostics_fresh(diag_row) and not bypass_cache and _diagnostics_legacy(diag_row):
        logger.info(
            "[video_analyze] stale diagnostics schema — recomputing video_id=%s",
            vid,
        )

    # Gemini prompt label: last-resort literal when taxonomy row is missing.
    gemini_niche_label = niche_label_resolved or (f"niche_{niche_id}" if niche_id else "unknown")
    if not niche_label_resolved and niche_id:
        logger.warning(
            "[video_analyze] niche label fallback niche_%s for Gemini video_id=%s",
            niche_id,
            vid,
        )

    segments = decompose_segments(analysis)
    hook_cards = extract_hook_phases(analysis)
    from getviews_pipeline.video_report_coherence import (
        effective_depth_tier,
        infer_early_performance_tier,
        max_findings_for_tier,
        resolve_extraction_mode,
    )

    _views_ext = int(video.get("views") or 0)
    _corpus_avg_ext = float((niche_intel or {}).get("avg_views") or 0) or None
    _early_tier_ext = infer_early_performance_tier(
        _views_ext,
        _corpus_avg_ext,
        creator_median_views=video.get("creator_median_views"),
    )
    extraction_mode = resolve_extraction_mode(
        mode_resolved,
        video,
        niche_intel,
        performance_tier=_early_tier_ext,
    )
    _max_findings = max_findings_for_tier(
        effective_depth_tier(_early_tier_ext, mode_resolved)
    )
    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_process

        emit(step_queue, step_process("Đang kiểm tra cấu trúc video..."))
    raw_errs = extract_video_errors(
        extraction_mode=extraction_mode,
        video=video,
        analysis=analysis,
        niche_label=gemini_niche_label,
        niche_row=niche_intel,
        retention_curve=retention_user,
        retention_risk_events=retention_risk_events or None,
        max_findings=_max_findings,
    )
    content_format_str = str(video.get("content_format") or "")
    errors = apply_rule_based_video_errors(
        raw_errs,
        analysis,
        content_format_str,
        caption_hint=(str(video.get("caption") or "").strip() or None),
        duration_sec=float(dur) if dur > 0 else None,
    )
    for _h in hook_cards:
        if isinstance(_h, dict) and "body" in _h:
            del _h["body"]

    upsert_payload = {
        "video_id": vid,
        "analysis_depth": depth,
        "analysis_headline": None,
        "analysis_subtext": None,
        "lessons": [],
        "hook_phases": hook_cards,
        "segments": segments,
        "flop_issues": errors,
        "retention_curve": retention_user,
        "niche_benchmark_curve": niche_benchmark,
        "computed_at": datetime.now(UTC).isoformat(),
    }
    try:
        service_sb.table("video_diagnostics").upsert(
            upsert_payload,
            on_conflict="video_id,analysis_depth",
        ).execute()
    except Exception as exc:
        logger.exception("[video_analyze] upsert failed video_id=%s: %s", vid, exc)
        raise

    diag_read = upsert_payload
    out = _response_from_diagnostics_row(
        video,
        diag_read,
        mode=mode_resolved,
        niche_meta=niche_meta,
        niche_benchmark=niche_benchmark,
        retention_user=retention_user,
        niche_label=niche_label_resolved,
        retention_source=retention_source,
        cross_format_signal=cross_format_signal,
        retention_risk_events=retention_risk_events or None,
        user_sb=user_sb,
    )
    out["__narrative_analysis"] = analysis
    out["__narrative_content_format"] = content_format_str
    out["__analysis_depth"] = depth
    out["__cache_video_id"] = vid
    out["__cache_analysis_depth"] = depth
    if session_niche_id and int(session_niche_id) > 0:
        _apply_studio_session_niche_cohort(out, session_niche_id, user_sb=user_sb)
    return _merge_sidecars_into_response(
        out,
        video_id=vid,
        comment_count_hint=int(video.get("comments") or 0),
    )


# ── On-demand analysis (URL not in corpus) ────────────────────────────────


def _build_video_dict_from_aweme(
    aweme: dict[str, Any],
    analyze_result: dict[str, Any],
    niche_id: int,
) -> dict[str, Any]:
    """Synthesise a corpus-row-shaped dict from a fresh aweme + Gemini
    analysis so the downstream synth + response builders work unchanged.

    The on-demand path never persists this row — it just needs the same
    keys ``_response_from_diagnostics_row`` + ``_call_win_gemini`` /
    ``_call_flop_gemini`` + ``build_kpis`` read from a corpus row.
    """
    from getviews_pipeline import ensemble

    metadata = ensemble.parse_metadata(aweme)
    metrics = metadata.metrics
    handle = metadata.author.username if metadata.author else ""
    video_id = str(aweme.get("aweme_id", "") or metadata.video_id or "")

    create_time = aweme.get("create_time") or aweme.get("createTime")
    created_iso: str | None = None
    if isinstance(create_time, (int, float)):
        try:
            created_iso = datetime.fromtimestamp(int(create_time), tz=UTC).isoformat()
        except (OSError, ValueError, OverflowError):
            created_iso = None

    views = int(metrics.views or 0)
    saves = int(metrics.bookmarks or 0)
    save_rate = saves / max(views, 1) if views > 0 else 0.0

    return {
        "video_id": video_id,
        "creator_handle": handle,
        "views": views,
        "likes": int(metrics.likes or 0),
        "comments": int(metrics.comments or 0),
        "shares": int(metrics.shares or 0),
        "saves": saves,
        "save_rate": save_rate,
        "engagement_rate": float(metadata.engagement_rate or 0.0),
        "caption": (metadata.description or str(aweme.get("desc") or "")).strip()
        or None,
        # Frame-first (2026-06-11): the live analysis captured a permanent
        # R2 frame from the downloaded video — never store the expiring
        # platform cover when we have it.
        "thumbnail_url": (
            (analyze_result.get("analysis") or {}).get("r2_thumbnail_url")
            if isinstance(analyze_result.get("analysis"), dict)
            else None
        )
        or analyze_result.get("r2_thumbnail_url")
        or metadata.thumbnail_url,
        "created_at": created_iso,
        "niche_id": niche_id,
        # The Gemini-driven analysis dict — same shape as a corpus row's
        # analysis_json. Drives KPI/segment/hook decomposition downstream.
        "analysis_json": analyze_result.get("analysis") or {},
        # No corpus baseline → assume 1.0 multiplier so retention modeling
        # falls back to the niche median curve without breakout skew.
        "breakout_multiplier": 1.0,
        "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{video_id}"
        if handle and video_id
        else "",
    }


async def _classify_niche_id_async(
    service_sb: Any,
    aweme: dict[str, Any],
    *,
    fallback_session_niche_id: int | None = None,
    user_id: str | None = None,
) -> int:
    """Best-effort niche via ``resolve_live_niche_id`` ladder."""
    from getviews_pipeline.live_niche import resolve_live_niche_id

    try:
        return await resolve_live_niche_id(
            service_sb,
            aweme,
            fallback_session_niche_id=fallback_session_niche_id,
            user_id=user_id,
        )
    except Exception as exc:  # noqa: BLE001 — niche is best-effort, never fatal
        logger.warning(
            "[video_analyze_on_demand] niche resolve failed (continuing with 0): %s", exc,
        )
        return 0


async def _fetch_and_analyze_async(tiktok_url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch the aweme via EnsembleData + run Gemini analysis. Returns
    ``(aweme, analyze_result)``. Wrapped so the sync entry point can
    drive both steps under a single ``asyncio.run``.

    Creates a **fresh** httpx.AsyncClient instead of reusing the module-level
    singleton.  The singleton is bound to the main Cloud Run event loop; reusing
    it inside ``asyncio.run()`` (which creates a new event loop for the calling
    thread) raises ``RuntimeError: Event loop is closed`` in Python 3.12.

    skip_corpus_cache=True avoids the get_cached_analysis() call which uses the
    module-level _anon_client() Supabase client.  That client's httpx transport
    is bound to the uvicorn event loop (L1); using it inside asyncio.run() (L2)
    causes "RuntimeError: Event loop is closed".  The on-demand path already
    knows the video is not in corpus — skipping this lookup is both correct and
    required for event-loop isolation.
    """
    import httpx

    from getviews_pipeline import ensemble
    from getviews_pipeline.analysis_core import analyze_aweme

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=30.0, read=120.0)) as fresh_client:
        aweme = await ensemble.fetch_post_info(tiktok_url, _client=fresh_client)

    analyze_result = await analyze_aweme(
        aweme,
        include_diagnosis=False,
        skip_corpus_cache=True,  # avoids module-level Supabase client (event-loop-closed bug)
    )
    return aweme, analyze_result


def normalize_tiktok_url(url: str) -> str:
    """Phase 5.1.1 — Canonicalize a TikTok URL before cache lookup.

    Handles the most common variants that would cause spurious cache misses:
      - http vs https → always https
      - www. vs no www. → always www
      - trailing slash → stripped
      - query parameters (e.g. ?_r=1, ?share_app_id=...) → stripped
      - fragment (#comments) → stripped
      - vt.tiktok.com short links → kept as-is (can't resolve without HTTP)
      - vm.tiktok.com short links → kept as-is

    Returns a normalized canonical form so that repeat lookups on URL
    variants (copy-pasted from share sheet, slightly different query params)
    all resolve to the same cache key.
    """
    from urllib.parse import urlparse, urlunparse

    raw = str(url or "").strip()
    if not raw:
        return raw

    parsed = urlparse(raw)
    scheme = "https"
    netloc = parsed.netloc.lower()
    if not netloc.startswith("www.") and "tiktok.com" in netloc and "vt." not in netloc and "vm." not in netloc:
        netloc = "www." + netloc.lstrip("www.")
    # Strip query + fragment; keep path (strip trailing slash if path != /)
    path = parsed.path.rstrip("/") if parsed.path not in ("", "/") else parsed.path
    return urlunparse((scheme, netloc, path, "", "", ""))


def _try_on_demand_cache_hit(
    service_sb: Any,
    tiktok_url: str,
    *,
    step_queue: Any | None = None,
    user_sb: Any | None = None,
    fallback_niche_id: int | None = None,
    user_id: str | None = None,
    analysis_depth: str | None = None,
) -> dict[str, Any] | None:
    """Return a previously-cached on-demand response if one is fresh.

    Looks up ``video_diagnostics`` by ``tiktok_url`` (filtered to
    ``source='on_demand'`` so corpus rows can't collide). Returns the
    cached response dict on hit, ``None`` on miss / stale / error.
    Avoids the EnsembleData URL → aweme fetch (~4s) and the entire
    Gemini pipeline (~6 min) on hit.

    Phase 5.1.1 — normalizes the URL before lookup so variants
    (query params, http vs https, trailing slash) hit the same cache row.
    """
    if not tiktok_url:
        return None
    depth = _normalize_analysis_depth(analysis_depth)
    canonical_url = normalize_tiktok_url(tiktok_url)
    # Phase 5.8 — track URL normalization collisions (variant → canonical).
    if canonical_url != tiktok_url:
        try:
            from getviews_pipeline.observability import log_url_normalize_event
            log_url_normalize_event(
                raw_url=tiktok_url,
                canonical_url=canonical_url,
                was_normalized=True,
            )
        except Exception:
            pass
    try:
        res = (
            service_sb.table("video_diagnostics")
            .select("cached_response,computed_at")
            .eq("tiktok_url", canonical_url)
            .eq("source", "on_demand")
            .eq("analysis_depth", depth)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("[video_analyze:on_demand] cache lookup failed url=%s: %s", tiktok_url, exc)
        return None
    rows = getattr(res, "data", None) or []
    if not rows:
        return None
    row = rows[0]
    if not _diagnostics_fresh(row):
        return None
    cached = row.get("cached_response")
    if not isinstance(cached, dict) or not cached:
        return None
    if int(cached.get("response_schema_version") or 1) < ON_DEMAND_RESPONSE_SCHEMA_VERSION_MIN:
        return None
    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_process

        emit(step_queue, step_process("Đang tải kết quả..."))
    if _response_needs_embed_tile_repair(cached):
        _apply_embed_tile_repair_to_out(
            cached,
            fallback_niche_id=fallback_niche_id,
            user_sb=user_sb,
            service_sb=service_sb,
            user_id=user_id,
        )
        vid = str(cached.get("video_id") or "")
        if vid and tiktok_url:
            cacheable = {k: v for k, v in cached.items() if not str(k).startswith("__")}
            _persist_on_demand_cache(
                service_sb,
                tiktok_url=tiktok_url,
                video_id=vid,
                response=cacheable,
                analysis_depth=depth,
            )
    from getviews_pipeline.observability import log_cache_event
    log_cache_event(event="cache_hit", cache_source="on_demand_cache", video_id=None)
    _strip_on_demand_client_cache_fields(cached)
    return cached


def _persist_on_demand_cache(
    service_sb: Any,
    *,
    tiktok_url: str,
    video_id: str,
    response: dict[str, Any],
    analysis_depth: str | None = None,
) -> None:
    """Cache an on-demand response so the next request on the same URL
    can short-circuit. Non-fatal: any failure is logged and swallowed.

    Phase 5.1.1 — stores the canonical URL so future variant requests
    also hit this cache row.
    """
    if not tiktok_url or not video_id or not response:
        return
    canonical_url = normalize_tiktok_url(tiktok_url)
    depth = _normalize_analysis_depth(analysis_depth)
    try:
        service_sb.table("video_diagnostics").upsert(
            {
                "video_id": video_id,
                "analysis_depth": depth,
                "tiktok_url": canonical_url,
                "source": "on_demand",
                "cached_response": response,
                "computed_at": datetime.now(UTC).isoformat(),
            },
            on_conflict="video_id,analysis_depth",
        ).execute()
    except Exception as exc:
        logger.warning("[video_analyze:on_demand] cache write failed url=%s: %s", tiktok_url, exc)


def run_video_analyze_on_demand(
    service_sb: Any,
    user_sb: Any,
    *,
    tiktok_url: str,
    mode: Literal["win", "flop"] | None = None,
    query_hint: str | None = None,
    step_queue: Any | None = None,
    fallback_niche_id: int | None = None,
    user_id: str | None = None,
    analysis_depth: str | None = None,
) -> dict[str, Any]:
    """Sync pipeline for URLs not yet in ``video_corpus``.

    Mirrors the corpus-row branch of ``run_video_analyze_pipeline`` but:
      • Never reads or writes ``video_corpus`` (does write to
        ``video_diagnostics`` with ``source='on_demand'`` to cache
        the response and skip Gemini on subsequent hits).
      • Skips ``thumbnail_analysis`` during extract (corpus row sidecar).
        ``comment_radar`` is resolved in ``finalize_video_narrative_layer``
        for on-demand URLs when comments warrant it (§4.7 M5).
      • Best-effort niche resolution via hashtag classifier; when nothing
        matches, ``niche_id=0`` and ``niche_meta`` falls back to the same
        empty-pool copy the existing screen renders for sparse niches.

    Composer wiring (Studio → ``/app/video?url=…``) routes URL pastes
    through ``/video/analyze``; when ``_resolve_video_id`` raises
    ``"Không tìm thấy video trong corpus cho URL này"``, the router
    falls through to this function so the user gets a working analysis
    instead of a 404 dead-end. Result is flagged ``source: "on_demand"``
    so the FE can show a subtle "phân tích trực tiếp, không lưu corpus"
    hint without re-architecting the response shape.
    """
    depth = _normalize_analysis_depth(analysis_depth)
    # Cache hit: skip EnsembleData + Gemini entirely when we've already
    # analysed this URL within the 1h diagnostics TTL.
    cached = _try_on_demand_cache_hit(
        service_sb,
        tiktok_url,
        step_queue=step_queue,
        user_sb=user_sb,
        fallback_niche_id=fallback_niche_id,
        user_id=user_id,
        analysis_depth=depth,
    )
    if cached is not None:
        return cached

    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_process

        emit(
            step_queue,
            step_process("Đang phân tích video..."),
        )
    aweme, analyze_result = asyncio.run(_fetch_and_analyze_async(tiktok_url))

    if "error" in analyze_result or "analysis" not in analyze_result:
        # Gemini choked on the video; surface as a 500-class error rather
        # than masking it as "not found". Caller maps to HTTP 500.
        err = str(analyze_result.get("error") or "Phân tích video thất bại")
        # Carousel-specific errors have their own codes — re-raise so callers
        # can distinguish and surface a Vietnamese message instead of a 500.
        raise RuntimeError(err)

    from getviews_pipeline import ensemble

    meta_ed = ensemble.parse_metadata(aweme)
    video_desc_od = str(aweme.get("desc") or meta_ed.description or "")
    video_hashtags_od = [
        str(t.get("hashtag_name") or t.get("title") or "").lstrip("#")
        for t in (aweme.get("text_extra") or [])
        if t.get("hashtag_name") or t.get("title")
    ]
    if not video_hashtags_od and meta_ed.hashtags:
        video_hashtags_od = [str(h).lstrip("#") for h in meta_ed.hashtags]

    niche_id = asyncio.run(
        _classify_niche_id_async(
            service_sb,
            aweme,
            fallback_session_niche_id=fallback_niche_id,
            user_id=user_id,
        )
    )
    video = _build_video_dict_from_aweme(aweme, analyze_result, niche_id)
    vid = video["video_id"]
    if not vid:
        raise ValueError("Aweme thiếu video_id — không phân tích được")

    analysis = video["analysis_json"]
    dur = video_duration_sec(analysis)

    # A.2.3 — derive content_class_id from analysis so the on-demand path
    # (video not yet in corpus) can also benefit from sharper benchmarks.
    # classify_format does the format detection; _content_class_for maps
    # (niche × format) to a content_class.
    from getviews_pipeline.content_format_guards import refresh_video_content_format

    _on_demand_format = (
        refresh_video_content_format(video, analysis, niche_id) if niche_id else None
    )
    content_class_id = video.get("content_class_id")
    od_creator_tier = str(video.get("creator_tier") or "").strip() or None
    niche_intel, benchmark_axis = fetch_video_benchmark_with_axis(
        user_sb,
        niche_id=niche_id,
        content_class_id=content_class_id,
        creator_tier=od_creator_tier,
    )
    # A.1 — cross-niche format signal. Cheap read; returns None when
    # format is single-niche or sample is too thin so the FE renders
    # only when meaningful.
    from getviews_pipeline.cross_format import get_cross_format_signal
    cross_format_signal = get_cross_format_signal(
        user_sb,
        content_class_id=content_class_id,
        content_format=str(video.get("content_format") or "").strip() or None,
    )
    default_niche_meta = {
        "avg_views": None,
        "avg_retention": 0.5,
        "avg_ctr": 0.04,
        "sample_size": 0,
        "winners_sample_size": None,
    }

    heuristic_od: Literal["win", "flop"] = (
        "flop" if is_flop_mode(video, niche_intel) else "win"
    )
    from getviews_pipeline.video_report_coherence import pipeline_reconcile_mode

    caller_mode_od = mode if mode in ("win", "flop") else None
    mode_resolved = pipeline_reconcile_mode(
        heuristic_od,
        video,
        niche_intel,
        query_hint=query_hint,
        caller_mode=caller_mode_od,
    )

    bench_payload = build_niche_benchmark_payload(
        niche_intel,
        niche_id=niche_id,
        duration_sec=max(dur, 5.0),
        user_sb=user_sb,
        benchmark_axis=benchmark_axis,
        content_class_id=int(content_class_id) if content_class_id else None,
    )
    niche_benchmark = bench_payload["niche_benchmark_curve"]
    niche_meta = (
        bench_payload["niche_meta"]
        if bench_payload.get("niche_meta") is not None
        else default_niche_meta
    )
    # A.2.3 — tag axis (matches corpus path).
    if niche_meta is not default_niche_meta:
        niche_meta["benchmark_axis"] = benchmark_axis
        niche_meta = _apply_peer_tier_to_niche_meta(
            niche_meta,
            benchmark_axis=benchmark_axis,
            benchmark_row=niche_intel,
            views=int(video.get("views") or 0),
            content_format=str(video.get("content_format") or ""),
        )
    rs = bench_payload.get("retention_source") or "modeled"
    retention_source: RetentionSource = "real" if rs == "real" else "modeled"

    niche_label_resolved = _resolve_niche_label(user_sb, niche_id) if niche_id else ""
    gemini_niche_label = niche_label_resolved or "unknown"

    bm = float(video.get("breakout_multiplier") or 1.0)
    retention_user, retention_structural_source, retention_risk_events = (
        _resolve_user_retention_curve(
            duration_sec=dur,
            analysis=analysis,
            niche_median_retention=float(niche_meta["avg_retention"]),
            breakout_multiplier=bm,
            video_id=vid,
            content_format=str(video.get("content_format") or ""),
        )
    )
    if retention_structural_source:
        retention_source = retention_structural_source

    segments = decompose_segments(analysis)
    hook_cards = extract_hook_phases(analysis)
    from getviews_pipeline.video_report_coherence import (
        effective_depth_tier,
        infer_early_performance_tier,
        max_findings_for_tier,
        resolve_extraction_mode,
    )

    _views_od = int(video.get("views") or 0)
    _corpus_avg_od = float((niche_intel or {}).get("avg_views") or 0) or None
    _early_tier_od = infer_early_performance_tier(
        _views_od,
        _corpus_avg_od,
        creator_median_views=video.get("creator_median_views"),
    )
    extraction_mode_od = resolve_extraction_mode(
        mode_resolved,
        video,
        niche_intel,
        performance_tier=_early_tier_od,
    )
    _max_findings_od = max_findings_for_tier(
        effective_depth_tier(_early_tier_od, mode_resolved)
    )
    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_process

        emit(step_queue, step_process("Đang kiểm tra cấu trúc video..."))
    raw_errs_od = extract_video_errors(
        extraction_mode=extraction_mode_od,
        video=video,
        analysis=analysis,
        niche_label=gemini_niche_label,
        niche_row=niche_intel,
        retention_curve=retention_user,
        retention_risk_events=retention_risk_events or None,
        max_findings=_max_findings_od,
    )
    content_format_str_od = str(video.get("content_format") or "")
    _caption_od = str(video.get("caption") or "").strip()
    errors_od = apply_rule_based_video_errors(
        raw_errs_od,
        analysis,
        content_format_str_od,
        caption_hint=_caption_od or None,
        duration_sec=float(dur) if dur > 0 else None,
    )
    for _h in hook_cards:
        if isinstance(_h, dict) and "body" in _h:
            del _h["body"]

    diag_synth = {
        "video_id": vid,
        "analysis_headline": None,
        "analysis_subtext": None,
        "lessons": [],
        "hook_phases": hook_cards,
        "segments": segments,
        "flop_issues": errors_od,
        "retention_curve": retention_user,
        "niche_benchmark_curve": niche_benchmark,
        "computed_at": datetime.now(UTC).isoformat(),
    }

    out = _response_from_diagnostics_row(
        video,
        diag_synth,
        mode=mode_resolved,
        niche_meta=niche_meta,
        niche_benchmark=niche_benchmark,
        retention_user=retention_user,
        niche_label=niche_label_resolved,
        retention_source=retention_source,
        cross_format_signal=cross_format_signal,
        retention_risk_events=retention_risk_events or None,
        user_sb=user_sb,
    )
    out["__narrative_analysis"] = analysis
    out["__narrative_content_format"] = content_format_str_od
    out["__tiktok_desc"] = video_desc_od
    out["__tiktok_hashtags"] = video_hashtags_od
    out["__aweme_for_niche"] = aweme
    out["__fallback_niche_id"] = int(fallback_niche_id or 0)
    out["response_schema_version"] = ON_DEMAND_RESPONSE_SCHEMA_VERSION
    # Flag the response so the FE can render a subtle "phân tích trực tiếp"
    # badge — corpus rows don't set this, so the FE only highlights when
    # explicitly truthy.
    out["source"] = "on_demand"
    # Pipeline-private cache key — finalize_video_narrative_layer reads
    # this AFTER it mutates ``out`` with narrative_vi / format_cards /
    # performance_tier etc., then persists the full enriched response
    # so the next hit on this URL skips the full Gemini pipeline.
    out["__cache_on_demand_url"] = tiktok_url
    out["__cache_on_demand_vid"] = vid
    out["__analysis_depth"] = depth
    return out
