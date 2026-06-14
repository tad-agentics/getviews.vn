"""Outcome-driven signal calibration — Loop A/B/C infrastructure.

Periodic batch job learns viral-score weights and per-lever predictive ρ
from ``video_corpus`` outcomes. Readers are flag-gated; static weights
remain the floor when the flag is off or gates fail.
"""

from __future__ import annotations

import logging
import random
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache, wraps
from typing import Any

from getviews_pipeline.claim_tiers import CLAIM_TIERS
from getviews_pipeline.settings import settings
from getviews_pipeline.viral_alignment_backtest import (
    TOP_N,
    W_FORMAT,
    W_HOOK,
    W_TIME,
    _by_niche,
    _mode_hour,
    compute_alignment_components,
    spearman_rho,
)

logger = logging.getLogger(__name__)

# Calibration-specific sample floors (distinct from claim_tiers display gates).
GLOBAL_SAMPLE_FLOOR = 200
CLASS_SAMPLE_FLOOR = CLAIM_TIERS["niche_norms"]  # 30
SPEARMAN_GATE = 0.35
ADOPT_EPS = 0.02
WEIGHT_MIN = 0.1
WEIGHT_MAX = 0.7
WEIGHT_STEP = 0.05
TRAIN_FRACTION = 0.7
CALIBRATION_SEED = 2026

# Lever keys stored in signal_predictive_value (Loop B substrate for C).
LEVER_SIGNAL_TYPES = ("viral_hook", "viral_format", "viral_time")

SALIENCE_MULTIPLIER_FLOOR = 0.5
DEMOTE_RHO_THRESHOLD = 0.05
PREDICTIVE_SAMPLE_FLOOR = CLASS_SAMPLE_FLOOR

# Reader TTL — the user pod is long-lived (min-instances:1), so an unbounded
# lru_cache would serve last cycle's calibration until pod restart. A short
# TTL lets a weekly run's new rows surface within the pod's lifetime while
# still collapsing the per-diagnosis read storm. ~83 keys max (classes + None).
CALIBRATION_READER_TTL_S = 6 * 3600


def _ttl_cache(ttl_seconds: int) -> Callable:
    """Minimal TTL memoization with an lru_cache-compatible ``cache_clear``."""

    def decorator(fn: Callable) -> Callable:
        store: dict[tuple, tuple[float, Any]] = {}

        @wraps(fn)
        def wrapper(*args: Any) -> Any:
            now = time.monotonic()
            hit = store.get(args)
            if hit is not None and now - hit[0] < ttl_seconds:
                return hit[1]
            value = fn(*args)
            store[args] = (now, value)
            return value

        wrapper.cache_clear = store.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator

# Map manifest signal id prefixes → lever for salience demotion.
_SIGNAL_PREFIX_TO_LEVER: tuple[tuple[str, str], ...] = (
    ("hook_", "viral_hook"),
    ("script_", "viral_format"),
    ("format_", "viral_format"),
    ("structure_", "viral_format"),
    ("timing_", "viral_time"),
    ("posting_", "viral_time"),
    ("distribution_", "viral_time"),
    ("metadata_", "viral_time"),
)


@dataclass(frozen=True)
class CalibrationFeature:
    """One scoreable corpus row with alignment components + outcome."""

    niche_id: int
    content_class_id: int | None
    hook_align: float
    format_align: float
    time_align: float
    breakout: float


def weighted_score(
    hook_align: float,
    format_align: float,
    time_align: float,
    weights: tuple[float, float, float],
) -> float:
    wh, wf, wt = weights
    return 100.0 * (wh * hook_align + wf * format_align + wt * time_align)


def simplex_weights(*, step: float = WEIGHT_STEP) -> list[tuple[float, float, float]]:
    """Generate (w_hook, w_format, w_time) on a coarse simplex grid."""
    combos: list[tuple[float, float, float]] = []
    n_steps = int(round(1.0 / step))
    for i in range(n_steps + 1):
        for j in range(n_steps + 1 - i):
            k = n_steps - i - j
            wh = round(i * step, 4)
            wf = round(j * step, 4)
            wt = round(k * step, 4)
            if abs(wh + wf + wt - 1.0) > 1e-6:
                continue
            if (
                WEIGHT_MIN <= wh <= WEIGHT_MAX
                and WEIGHT_MIN <= wf <= WEIGHT_MAX
                and WEIGHT_MIN <= wt <= WEIGHT_MAX
            ):
                combos.append((wh, wf, wt))
    return combos


def adopt_guard(
    rho_holdout: float,
    rho_baseline: float,
    sample_size: int,
    floor: int,
    *,
    eps: float = ADOPT_EPS,
) -> bool:
    """True when tuned weights beat static on holdout and clear sample floor."""
    if sample_size < floor:
        return False
    threshold = max(SPEARMAN_GATE, rho_baseline + eps)
    return rho_holdout >= threshold


def sweep_best_weights(
    features: list[CalibrationFeature],
    *,
    step: float = WEIGHT_STEP,
) -> tuple[tuple[float, float, float], float]:
    """Argmax train ρ over the simplex grid."""
    if len(features) < 2:
        return (W_HOOK, W_FORMAT, W_TIME), 0.0

    breakouts = [f.breakout for f in features]
    best_weights = (W_HOOK, W_FORMAT, W_TIME)
    best_rho = -1.0

    for weights in simplex_weights(step=step):
        scores = [
            weighted_score(f.hook_align, f.format_align, f.time_align, weights)
            for f in features
        ]
        rho = spearman_rho(breakouts, scores)
        if rho > best_rho:
            best_rho = rho
            best_weights = weights

    return best_weights, best_rho


def _evaluate_weights(
    features: list[CalibrationFeature],
    weights: tuple[float, float, float],
) -> float:
    if len(features) < 2:
        return 0.0
    breakouts = [f.breakout for f in features]
    scores = [
        weighted_score(f.hook_align, f.format_align, f.time_align, weights)
        for f in features
    ]
    return spearman_rho(breakouts, scores)


def extract_calibration_features(client: Any) -> list[CalibrationFeature]:
    """Pull corpus rows and compute alignment components + breakout."""
    result = (
        client.table("video_corpus")
        .select(
            "video_id,niche_id:ingest_loop_niche_id,content_class_id,hook_type,"
            "content_format,posting_hour,breakout_multiplier"
        )
        .not_.is_("breakout_multiplier", "null")
        .not_.is_("ingest_loop_niche_id", "null")
        .limit(5000)
        .execute()
    )
    rows = list(result.data or [])
    by_niche = _by_niche(rows)
    peak_hour_by_niche: dict[int, int | None] = {
        nid: _mode_hour(pool[:TOP_N]) for nid, pool in by_niche.items()
    }

    features: list[CalibrationFeature] = []
    for row in rows:
        nid_raw = row.get("niche_id")
        if nid_raw is None:
            continue
        nid = int(nid_raw)
        pool = by_niche.get(nid, [])
        align = compute_alignment_components(
            hook_type=row.get("hook_type"),
            content_format=row.get("content_format"),
            posting_hour=row.get("posting_hour"),
            niche_top30=pool,
            niche_peak_hour=peak_hour_by_niche.get(nid),
        )
        if align is None:
            continue
        bm = row.get("breakout_multiplier")
        if bm is None:
            continue
        cc_raw = row.get("content_class_id")
        cc_id = int(cc_raw) if cc_raw is not None else None
        features.append(
            CalibrationFeature(
                niche_id=nid,
                content_class_id=cc_id,
                hook_align=align[0],
                format_align=align[1],
                time_align=align[2],
                breakout=float(bm),
            )
        )
    return features


def _split_train_holdout(
    features: list[CalibrationFeature],
    *,
    seed: int = CALIBRATION_SEED,
) -> tuple[list[CalibrationFeature], list[CalibrationFeature]]:
    if not features:
        return [], []
    rng = random.Random(seed)
    shuffled = list(features)
    rng.shuffle(shuffled)
    split_at = max(1, int(len(shuffled) * TRAIN_FRACTION))
    if split_at >= len(shuffled):
        split_at = len(shuffled) - 1
    return shuffled[:split_at], shuffled[split_at:]


def _insert_calibration_row(
    client: Any,
    *,
    scope: str,
    content_class_id: int | None,
    weights: tuple[float, float, float],
    rho_holdout: float,
    rho_baseline: float,
    sample_size: int,
    adopted: bool,
    computed_at: str,
) -> None:
    client.table("signal_calibration").insert({
        "scope": scope,
        "content_class_id": content_class_id,
        "w_hook": weights[0],
        "w_format": weights[1],
        "w_time": weights[2],
        "rho_holdout": round(rho_holdout, 4),
        "rho_baseline": round(rho_baseline, 4),
        "sample_size": sample_size,
        "adopted": adopted,
        "computed_at": computed_at,
    }).execute()


def _insert_predictive_rows(
    client: Any,
    *,
    content_class_id: int | None,
    lever_rhos: dict[str, float],
    sample_size: int,
    computed_at: str,
) -> int:
    written = 0
    for signal_type, rho in lever_rhos.items():
        client.table("signal_predictive_value").insert({
            "signal_type": signal_type,
            "content_class_id": content_class_id,
            "predictive_rho": round(rho, 4),
            "sample_size": sample_size,
            "computed_at": computed_at,
        }).execute()
        written += 1
    return written


def _lever_rhos(features: list[CalibrationFeature]) -> dict[str, float]:
    if len(features) < PREDICTIVE_SAMPLE_FLOOR:
        return {}
    breakouts = [f.breakout for f in features]
    return {
        "viral_hook": spearman_rho(breakouts, [f.hook_align for f in features]),
        "viral_format": spearman_rho(breakouts, [f.format_align for f in features]),
        "viral_time": spearman_rho(breakouts, [f.time_align for f in features]),
    }


def _calibrate_scope(
    client: Any,
    *,
    scope: str,
    content_class_id: int | None,
    features: list[CalibrationFeature],
    floor: int,
    computed_at: str,
) -> dict[str, Any]:
    train, holdout = _split_train_holdout(features)
    baseline_weights = (W_HOOK, W_FORMAT, W_TIME)
    best_weights, _train_rho = sweep_best_weights(train)
    rho_baseline = _evaluate_weights(holdout, baseline_weights)
    rho_holdout = _evaluate_weights(holdout, best_weights)
    adopted = adopt_guard(rho_holdout, rho_baseline, len(features), floor)
    weights_to_store = best_weights if adopted else baseline_weights

    _insert_calibration_row(
        client,
        scope=scope,
        content_class_id=content_class_id,
        weights=weights_to_store,
        rho_holdout=rho_holdout,
        rho_baseline=rho_baseline,
        sample_size=len(features),
        adopted=adopted,
        computed_at=computed_at,
    )

    lever_rhos = _lever_rhos(features)
    predictive_written = 0
    if lever_rhos:
        predictive_written = _insert_predictive_rows(
            client,
            content_class_id=content_class_id,
            lever_rhos=lever_rhos,
            sample_size=len(features),
            computed_at=computed_at,
        )

    return {
        "scope": scope,
        "content_class_id": content_class_id,
        "sample_size": len(features),
        "adopted": adopted,
        "rho_holdout": round(rho_holdout, 4),
        "rho_baseline": round(rho_baseline, 4),
        "weights": {
            "hook": weights_to_store[0],
            "format": weights_to_store[1],
            "time": weights_to_store[2],
        },
        "predictive_rows": predictive_written,
    }


def run_signal_calibration(client: Any) -> dict[str, Any]:
    """Weekly calibration job — writes append-only rows (shadow + adopted)."""
    computed_at = datetime.now(tz=UTC).isoformat()
    all_features = extract_calibration_features(client)

    by_class: dict[int, list[CalibrationFeature]] = defaultdict(list)
    for feat in all_features:
        if feat.content_class_id is not None:
            by_class[feat.content_class_id].append(feat)

    class_results: list[dict[str, Any]] = []
    classes_adopted = 0
    for class_id, class_feats in sorted(by_class.items()):
        if len(class_feats) < CLASS_SAMPLE_FLOOR:
            continue
        result = _calibrate_scope(
            client,
            scope="content_class",
            content_class_id=class_id,
            features=class_feats,
            floor=CLASS_SAMPLE_FLOOR,
            computed_at=computed_at,
        )
        class_results.append(result)
        if result["adopted"]:
            classes_adopted += 1

    global_result: dict[str, Any] | None = None
    if len(all_features) >= GLOBAL_SAMPLE_FLOOR:
        global_result = _calibrate_scope(
            client,
            scope="global",
            content_class_id=None,
            features=all_features,
            floor=GLOBAL_SAMPLE_FLOOR,
            computed_at=computed_at,
        )

    rho_deltas = [
        r["rho_holdout"] - r["rho_baseline"]
        for r in class_results
        if r.get("rho_holdout") is not None
    ]
    mean_delta = round(sum(rho_deltas) / len(rho_deltas), 4) if rho_deltas else None

    summary = {
        "feature_count": len(all_features),
        "classes_calibrated": len(class_results),
        "classes_adopted": classes_adopted,
        "global_adopted": bool(global_result and global_result["adopted"]),
        "mean_rho_delta": mean_delta,
        "global": global_result,
        "per_class": class_results,
        "computed_at": computed_at,
    }
    logger.info("[calibration] %s", summary)
    _clear_reader_caches()
    return summary


def _static_weights() -> tuple[float, float, float]:
    return (W_HOOK, W_FORMAT, W_TIME)


def _fetch_latest_calibration(
    client: Any,
    *,
    scope: str,
    content_class_id: int | None,
) -> dict[str, Any] | None:
    q = (
        client.table("signal_calibration")
        .select(
            "w_hook,w_format,w_time,rho_holdout,rho_baseline,sample_size,adopted,computed_at"
        )
        .eq("scope", scope)
        .order("computed_at", desc=True)
        .limit(1)
    )
    if content_class_id is None:
        q = q.is_("content_class_id", "null")
    else:
        q = q.eq("content_class_id", content_class_id)
    rows = (q.execute()).data or []
    return rows[0] if rows else None


def _fetch_latest_predictive(
    client: Any,
    *,
    signal_type: str,
    content_class_id: int | None,
) -> dict[str, Any] | None:
    q = (
        client.table("signal_predictive_value")
        .select("predictive_rho,sample_size,computed_at")
        .eq("signal_type", signal_type)
        .order("computed_at", desc=True)
        .limit(1)
    )
    if content_class_id is None:
        q = q.is_("content_class_id", "null")
    else:
        q = q.eq("content_class_id", content_class_id)
    rows = (q.execute()).data or []
    return rows[0] if rows else None


@lru_cache(maxsize=1)
def _service_client_cached() -> Any:
    from getviews_pipeline.supabase_client import get_service_client

    return get_service_client()


def _clear_reader_caches() -> None:
    viral_score_weights.cache_clear()
    signal_salience_multiplier.cache_clear()
    calibration_row_for_class.cache_clear()
    predictive_rho_for_lever.cache_clear()


@_ttl_cache(CALIBRATION_READER_TTL_S)
def viral_score_weights(content_class_id: int | None) -> tuple[float, float, float]:
    """Class → global → static ladder. Flag-off returns static constants."""
    if not settings.signal_calibration_adaptive:
        return _static_weights()

    client = _service_client_cached()
    for scope, cid in (("content_class", content_class_id), ("global", None)):
        if scope == "content_class" and cid is None:
            continue
        row = _fetch_latest_calibration(client, scope=scope, content_class_id=cid)
        if row and row.get("adopted"):
            return (
                float(row["w_hook"]),
                float(row["w_format"]),
                float(row["w_time"]),
            )
    return _static_weights()


@_ttl_cache(CALIBRATION_READER_TTL_S)
def predictive_rho_for_lever(
    lever: str,
    content_class_id: int | None,
) -> float | None:
    """Latest predictive ρ for a lever (class → global). None when uncalibrated."""
    if lever not in LEVER_SIGNAL_TYPES:
        return None
    client = _service_client_cached()
    for cid in (content_class_id, None):
        row = _fetch_latest_predictive(
            client, signal_type=lever, content_class_id=cid,
        )
        if row and int(row.get("sample_size") or 0) >= PREDICTIVE_SAMPLE_FLOOR:
            return float(row["predictive_rho"])
    return None


def _lever_for_signal_id(signal_id: str) -> str | None:
    for prefix, lever in _SIGNAL_PREFIX_TO_LEVER:
        if signal_id.startswith(prefix):
            return lever
    return None


@_ttl_cache(CALIBRATION_READER_TTL_S)
def signal_salience_multiplier(
    signal_id: str,
    content_class_id: int | None,
) -> float:
    """Demote-only salience multiplier from measured lever ρ (flag-gated)."""
    if not settings.signal_calibration_adaptive:
        return 1.0

    lever = _lever_for_signal_id(signal_id)
    if lever is None:
        return 1.0

    rho = predictive_rho_for_lever(lever, content_class_id)
    if rho is None or rho >= DEMOTE_RHO_THRESHOLD:
        return 1.0

    # Map weak/negative ρ to [SALIENCE_MULTIPLIER_FLOOR, 1.0).
    demotion = max(SALIENCE_MULTIPLIER_FLOOR, 1.0 + rho)
    return min(1.0, demotion)


@_ttl_cache(CALIBRATION_READER_TTL_S)
def calibration_row_for_class(content_class_id: int | None) -> dict[str, Any] | None:
    """Latest adopted calibration metadata for synthesis priors."""
    if not settings.signal_calibration_adaptive:
        return None

    client = _service_client_cached()
    for scope, cid in (("content_class", content_class_id), ("global", None)):
        if scope == "content_class" and cid is None:
            continue
        row = _fetch_latest_calibration(client, scope=scope, content_class_id=cid)
        if row and row.get("adopted"):
            return row
    return None


def predictive_strength_for_signal(
    signal_id: str,
    content_class_id: int | None,
) -> float | None:
    """Per-signal predictive strength for synthesis payload (Loop C)."""
    if not settings.signal_calibration_adaptive:
        return None
    lever = _lever_for_signal_id(signal_id)
    if lever is None:
        return None
    return predictive_rho_for_lever(lever, content_class_id)


def build_calibration_priors(content_class_id: int | None) -> str | None:
    """Compact digest for diagnosis synthesis — deepen, don't spawn topics."""
    if not settings.signal_calibration_adaptive:
        return None

    cal_row = calibration_row_for_class(content_class_id)
    if cal_row is None:
        return None

    sample_size = int(cal_row.get("sample_size") or 0)
    cite_numeric = sample_size >= CLASS_SAMPLE_FLOOR

    weights = (
        float(cal_row["w_hook"]),
        float(cal_row["w_format"]),
        float(cal_row["w_time"]),
    )
    lever_labels = sorted(
        (
            ("hook", weights[0], "viral_hook"),
            ("format", weights[1], "viral_format"),
            ("timing", weights[2], "viral_time"),
        ),
        key=lambda x: -x[1],
    )
    ranking = " > ".join(lbl for lbl, _, _ in lever_labels)

    lines: list[str] = [
        "CALIBRATION_PRIORS (đo từ corpus — dùng để ưu tiên lever và làm sâu lý do trong findings hiện có; "
        "KHÔNG mở section mới):",
    ]

    if cite_numeric:
        rho_h = float(cal_row.get("rho_holdout") or 0)
        lines.append(
            f"- Trọng số rubric ngách: {ranking} (ρ_holdout={rho_h:.2f}, n={sample_size})."
        )
    else:
        lines.append(f"- Trọng số rubric ngách (n={sample_size}, chưa đủ mẫu để trích ρ): {ranking}.")

    for _, _, lever_key in lever_labels:
        rho = predictive_rho_for_lever(lever_key, content_class_id)
        if rho is None:
            continue
        label = lever_key.replace("viral_", "")
        if cite_numeric and sample_size >= CLAIM_TIERS["hook_effectiveness"]:
            lines.append(f"- Lever {label}: ρ={rho:.2f} vs breakout (n={sample_size}).")
        elif cite_numeric:
            lines.append(f"- Lever {label}: theo dữ liệu ngách hiện có, ρ≈{rho:.2f} (n={sample_size}).")
        else:
            lines.append(f"- Lever {label}: theo dữ liệu ngách hiện có (chưa trích số ρ).")

    lines.append(
        "- Dùng predictive_strength trong SIGNAL_MANIFEST để sắp xếp nhấn mạnh trong prose; "
        "lead bằng lever có trọng số/ρ cao nhất khi evidence hỗ trợ."
    )
    return "\n".join(lines)


__all__ = [
    "CalibrationFeature",
    "adopt_guard",
    "build_calibration_priors",
    "calibration_row_for_class",
    "extract_calibration_features",
    "predictive_rho_for_lever",
    "predictive_strength_for_signal",
    "run_signal_calibration",
    "signal_salience_multiplier",
    "simplex_weights",
    "spearman_rho",
    "sweep_best_weights",
    "viral_score_weights",
    "weighted_score",
]
