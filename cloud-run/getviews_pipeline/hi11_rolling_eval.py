"""Phase 1b — rolling HI-11 reliability eval (no one-time human golden set)."""

from __future__ import annotations

import json
import logging
import statistics
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from getviews_pipeline.junction_content_class import content_class_id_for_creator_niche_format

logger = logging.getLogger(__name__)

AGREEMENT_TARGET = 0.85
JUNCTION_MISS_TARGET = 0.05
OUTLIER_TARGET = 0.10
HI9_SHADOW_TARGET = 0.85
HEALTHY_SAMPLE_PER_CLASS = 50
THIN_SAMPLE_PER_CLASS = 20
ROLLING_NIGHTS = 7


def _caption_hashtags(aweme_or_row: dict[str, Any]) -> list[str]:
    tags = aweme_or_row.get("hashtags") or []
    if tags:
        return [str(t).lower().lstrip("#") for t in tags]
    desc = str(aweme_or_row.get("caption") or aweme_or_row.get("desc") or "")
    return [w.lstrip("#") for w in desc.split() if w.startswith("#")]


def _hashtag_class_agreement(
    client: Any,
    rows: list[dict[str, Any]],
) -> tuple[float, int]:
    """Fraction of rows where hashtag_class_map agrees with stored content_class_id."""
    if not rows:
        return 1.0, 0
    try:
        map_rows = (
            client.table("hashtag_class_map")
            .select("hashtag, content_class_id, confidence")
            .gte("confidence", 0.5)
            .limit(5000)
            .execute()
            .data
            or []
        )
    except Exception:
        return 1.0, 0
    tag_to_cc: dict[str, int] = {}
    for m in map_rows:
        h = str(m.get("hashtag") or "").lower().lstrip("#")
        if h:
            tag_to_cc[h] = int(m["content_class_id"])
    agree = 0
    checked = 0
    for row in rows:
        stored = row.get("content_class_id")
        if stored is None:
            continue
        stored_i = int(stored)
        tags = _caption_hashtags(row)
        if not tags:
            continue
        preds = [tag_to_cc[t] for t in tags if t in tag_to_cc]
        if not preds:
            continue
        checked += 1
        if stored_i in preds:
            agree += 1
    if checked == 0:
        return 1.0, 0
    return round(agree / checked, 4), checked


def _hi9_shadow_agreement(rows: list[dict[str, Any]]) -> tuple[float, int]:
    """Re-derive class from analysis_json format_axis + inferred creator niche (no frames)."""
    agree = 0
    checked = 0
    for row in rows:
        stored = row.get("content_class_id")
        if stored is None:
            continue
        stored_i = int(stored)
        aj = row.get("analysis_json") or {}
        if isinstance(aj, str):
            try:
                aj = json.loads(aj)
            except json.JSONDecodeError:
                aj = {}
        nc = aj.get("niche_classification") or {}
        fmt = str(nc.get("format_axis") or aj.get("format_axis") or "").strip()
        cn_id = row.get("inferred_creator_niche_id") or nc.get("creator_niche_id")
        if not fmt or cn_id is None:
            continue
        try:
            predicted = content_class_id_for_creator_niche_format(int(cn_id), fmt)
        except (TypeError, ValueError):
            continue
        if predicted is None:
            continue
        checked += 1
        if predicted == stored_i:
            agree += 1
    if checked == 0:
        return 1.0, 0
    return round(agree / checked, 4), checked


def _junction_miss_rate(rows: list[dict[str, Any]]) -> float:
    misses = 0
    checked = 0
    for row in rows:
        conf = row.get("niche_resolution_confidence")
        try:
            c = float(conf) if conf is not None else 0.0
        except (TypeError, ValueError):
            c = 0.0
        if c < 0.6:
            continue
        checked += 1
        src = str(row.get("niche_resolution_source") or "")
        if "junction_miss" in src or src.endswith("_miss"):
            misses += 1
        elif row.get("content_class_id") is None:
            misses += 1
    if checked == 0:
        return 0.0
    return round(misses / checked, 4)


def _hook_kl_outlier_rate(
    client: Any,
    rows: list[dict[str, Any]],
) -> float:
    """Share of rows whose hook_type is absent from class MV distribution."""
    if not rows:
        return 0.0
    cc_ids = {int(r["content_class_id"]) for r in rows if r.get("content_class_id") is not None}
    if not cc_ids:
        return 0.0
    try:
        mv_rows = (
            client.table("content_class_intelligence")
            .select("content_class_id, hook_distribution")
            .in_("content_class_id", list(cc_ids))
            .execute()
            .data
            or []
        )
    except Exception:
        return 0.0
    dist_by_cc: dict[int, set[str]] = {}
    for mv in mv_rows:
        cc = int(mv["content_class_id"])
        hd = mv.get("hook_distribution") or {}
        if isinstance(hd, dict):
            dist_by_cc[cc] = set(hd.keys())
    outliers = 0
    for row in rows:
        cc = row.get("content_class_id")
        ht = row.get("hook_type")
        if cc is None or not ht:
            continue
        allowed = dist_by_cc.get(int(cc), set())
        if allowed and str(ht) not in allowed:
            outliers += 1
    return round(outliers / max(len(rows), 1), 4)


def _rolling_median(
    history: list[dict[str, Any]],
    field: str,
    *,
    nights: int = ROLLING_NIGHTS,
) -> float | None:
    vals: list[float] = []
    for entry in history[-nights:]:
        v = entry.get(field)
        if v is not None:
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                pass
    if not vals:
        return None
    return round(statistics.median(vals), 4)


def run_hi11_rolling_eval(client: Any) -> dict[str, Any]:
    """Sample recent corpus rows and emit rolling eval metrics."""
    now = datetime.now(UTC)
    since = (now - timedelta(days=7)).isoformat()

    healthy_cc = (
        client.table("content_class_ingest_targets")
        .select("content_class_id")
        .eq("viability_tier", "Healthy")
        .eq("active", True)
        .limit(30)
        .execute()
        .data
        or []
    )
    thin_cc = (
        client.table("content_class_ingest_targets")
        .select("content_class_id")
        .eq("viability_tier", "Thin")
        .limit(20)
        .execute()
        .data
        or []
    )

    select_cols = (
        "video_id, content_class_id, niche_id, hook_type, hashtags, caption, "
        "niche_resolution_confidence, niche_resolution_source, analysis_json, "
        "inferred_creator_niche_id"
    )

    sample_rows: list[dict[str, Any]] = []
    for t in healthy_cc:
        cc = int(t["content_class_id"])
        chunk = (
            client.table("video_corpus")
            .select(select_cols)
            .eq("content_class_id", cc)
            .gte("indexed_at", since)
            .limit(HEALTHY_SAMPLE_PER_CLASS)
            .execute()
            .data
            or []
        )
        sample_rows.extend(chunk)
    for t in thin_cc:
        cc = int(t["content_class_id"])
        chunk = (
            client.table("video_corpus")
            .select(select_cols)
            .eq("content_class_id", cc)
            .gte("indexed_at", since)
            .limit(THIN_SAMPLE_PER_CLASS)
            .execute()
            .data
            or []
        )
        sample_rows.extend(chunk)

    agreement, agreement_n = _hashtag_class_agreement(client, sample_rows)
    hi9_agree, hi9_n = _hi9_shadow_agreement(sample_rows)
    j_miss = _junction_miss_rate(sample_rows)
    outlier = _hook_kl_outlier_rate(client, sample_rows)

    pass_agreement = agreement >= AGREEMENT_TARGET
    pass_hi9 = hi9_agree >= HI9_SHADOW_TARGET
    pass_junction = j_miss <= JUNCTION_MISS_TARGET
    pass_outlier = outlier <= OUTLIER_TARGET
    overall_pass = pass_agreement and pass_hi9 and pass_junction and pass_outlier

    summary: dict[str, Any] = {
        "run_at": now.isoformat(),
        "sample_size": len(sample_rows),
        "healthy_classes_sampled": len(healthy_cc),
        "thin_classes_sampled": len(thin_cc),
        "hashtag_class_agreement": agreement,
        "hashtag_class_agreement_n": agreement_n,
        "hi9_shadow_agreement": hi9_agree,
        "hi9_shadow_agreement_n": hi9_n,
        "junction_miss_rate": j_miss,
        "hook_outlier_rate": outlier,
        "thresholds": {
            "agreement_min": AGREEMENT_TARGET,
            "hi9_shadow_min": HI9_SHADOW_TARGET,
            "junction_miss_max": JUNCTION_MISS_TARGET,
            "outlier_max": OUTLIER_TARGET,
        },
        "pass": {
            "agreement": pass_agreement,
            "hi9_shadow": pass_hi9,
            "junction": pass_junction,
            "outlier": pass_outlier,
            "overall": overall_pass,
        },
    }

    history = _append_artifact(summary)
    summary["rolling_7night"] = {
        "hashtag_class_agreement_median": _rolling_median(
            history, "hashtag_class_agreement",
        ),
        "hi9_shadow_agreement_median": _rolling_median(history, "hi9_shadow_agreement"),
        "junction_miss_rate_median": _rolling_median(history, "junction_miss_rate"),
        "hook_outlier_rate_median": _rolling_median(history, "hook_outlier_rate"),
        "nights": min(len(history), ROLLING_NIGHTS),
    }
    med = summary["rolling_7night"]
    summary["pass_7night"] = (
        med["nights"] >= ROLLING_NIGHTS
        and (med["hashtag_class_agreement_median"] or 0) >= AGREEMENT_TARGET
        and (med["hi9_shadow_agreement_median"] or 0) >= HI9_SHADOW_TARGET
        and (med["junction_miss_rate_median"] or 1) <= JUNCTION_MISS_TARGET
        and (med["hook_outlier_rate_median"] or 1) <= OUTLIER_TARGET
    )

    logger.info("[hi11_rolling] %s", json.dumps(summary, ensure_ascii=False))
    return summary


def _append_artifact(summary: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        root = Path(__file__).resolve().parents[2]
        out = root / "artifacts" / "qa-reports" / "hi11-rolling-eval.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        existing: list[dict[str, Any]] = []
        if out.is_file():
            try:
                existing = json.loads(out.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = [existing]
            except json.JSONDecodeError:
                existing = []
        existing.append(summary)
        if len(existing) > 30:
            existing = existing[-30:]
        out.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return existing
    except OSError as exc:
        logger.debug("[hi11_rolling] artifact skipped: %s", exc)
        return []
