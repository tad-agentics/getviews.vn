"""ACQE — Automated Class Quality Engine (content-class corpus pivot Phase 0).

Nightly: viability tiers per content_class, ingest target VPN/active, row assignment flags.
Cold-start: first 3 runs skip validated-subset filters; no red-alert escalation.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

ViabilityTier = Literal["Healthy", "Thin", "Dormant"]
COLD_START_RUNS = 3
HEALTHY_MIN_SAMPLE = 30
HEALTHY_MIN_INGEST_7D = 3
THIN_MIN_SAMPLE = 10
VALIDATED_CONF_MIN = 0.6
VALIDATED_DISAGREEMENT_MAX = 0.3
MERGE_CONFUSION_RATE = 0.15
PEER_SANITY_BREAKOUT = 5.0


def _tier_for_class(sample_30d: int, ingest_7d: int) -> ViabilityTier:
    if sample_30d >= HEALTHY_MIN_SAMPLE and ingest_7d >= HEALTHY_MIN_INGEST_7D:
        return "Healthy"
    if sample_30d >= THIN_MIN_SAMPLE or ingest_7d >= 1:
        return "Thin"
    return "Dormant"


def _vpn_for_tier(tier: ViabilityTier) -> tuple[int, bool]:
    if tier == "Healthy":
        return 15, True
    if tier == "Thin":
        return 8, True
    return 0, False


def _assignment_tier(conf: float | None, disagreement: float | None) -> str | None:
    if conf is None:
        return None
    if conf >= VALIDATED_CONF_MIN and (disagreement is None or disagreement < VALIDATED_DISAGREEMENT_MAX):
        return "validated"
    if conf >= 0.4:
        return "low_conf"
    return "flagged"


def _disagreement_score(
    loop_cc: int | None,
    stored_cc: int | None,
    conf: float | None,
) -> float | None:
    if loop_cc is None or stored_cc is None:
        return None
    if loop_cc == stored_cc:
        return 0.0 if conf and conf >= VALIDATED_CONF_MIN else 0.2
    return min(1.0, 0.5 + (1.0 - (conf or 0.0)) * 0.5)


def _fetch_class_metrics(client: Any, since_30d: str, since_7d: str) -> dict[int, dict[str, Any]]:
    rows = (
        client.table("video_corpus")
        .select("content_class_id, indexed_at")
        .gte("indexed_at", since_30d)
        .eq("language", "vi")
        .not_.is_("content_class_id", "null")
        .limit(100_000)
        .execute()
        .data
        or []
    )
    out: dict[int, dict[str, Any]] = {}
    since_7d_dt = datetime.fromisoformat(since_7d.replace("Z", "+00:00"))
    for row in rows:
        cc = row.get("content_class_id")
        if cc is None:
            continue
        cc_id = int(cc)
        bucket = out.setdefault(cc_id, {"sample_30d": 0, "ingest_7d": 0})
        bucket["sample_30d"] += 1
        idx = row.get("indexed_at")
        if idx:
            try:
                ts = datetime.fromisoformat(str(idx).replace("Z", "+00:00"))
                if ts >= since_7d_dt:
                    bucket["ingest_7d"] += 1
            except ValueError:
                pass
    return out


def _update_recent_assignment_flags(
    client: Any,
    *,
    since_7d: str,
    use_validated_subset: bool,
) -> int:
    q = (
        client.table("video_corpus")
        .select(
            "video_id, content_class_id, ingest_loop_content_class_id, "
            "niche_resolution_confidence, hook_type"
        )
        .gte("indexed_at", since_7d)
        .limit(5000)
    )
    if use_validated_subset:
        q = q.gte("niche_resolution_confidence", VALIDATED_CONF_MIN)
    rows = q.execute().data or []
    updated = 0
    for row in rows:
        vid = row.get("video_id")
        if not vid:
            continue
        conf_raw = row.get("niche_resolution_confidence")
        try:
            conf = float(conf_raw) if conf_raw is not None else None
        except (TypeError, ValueError):
            conf = None
        loop_cc = row.get("ingest_loop_content_class_id")
        stored_cc = row.get("content_class_id")
        try:
            loop_i = int(loop_cc) if loop_cc is not None else None
            stored_i = int(stored_cc) if stored_cc is not None else None
        except (TypeError, ValueError):
            loop_i, stored_i = None, None
        disagree = _disagreement_score(loop_i, stored_i, conf)
        tier = _assignment_tier(conf, disagree)
        patch: dict[str, Any] = {
            "class_assignment_tier": tier,
            "class_assignment_disagreement": disagree,
        }
        if loop_i is not None and stored_i is not None and loop_i != stored_i:
            patch["score_cohort_mismatch"] = True
        try:
            client.table("video_corpus").update(patch).eq("video_id", vid).execute()
            updated += 1
        except Exception as exc:
            logger.warning("[acqe] assignment patch failed video_id=%s: %s", vid, exc)
    return updated


def _flag_cohort_outliers(client: Any, *, since_7d: str) -> int:
    """Mark rows whose hook_type is absent from class MV distribution (coherence)."""
    try:
        mv_rows = (
            client.table("content_class_intelligence")
            .select("content_class_id, hook_distribution")
            .execute()
            .data
            or []
        )
    except Exception:
        return 0
    allowed: dict[int, set[str]] = {}
    for mv in mv_rows:
        cc = mv.get("content_class_id")
        hd = mv.get("hook_distribution") or {}
        if cc is not None and isinstance(hd, dict):
            allowed[int(cc)] = set(hd.keys())

    rows = (
        client.table("video_corpus")
        .select("video_id, content_class_id, hook_type")
        .gte("indexed_at", since_7d)
        .not_.is_("content_class_id", "null")
        .not_.is_("hook_type", "null")
        .limit(3000)
        .execute()
        .data
        or []
    )
    flagged = 0
    for row in rows:
        cc = row.get("content_class_id")
        ht = row.get("hook_type")
        if cc is None or not ht:
            continue
        dist = allowed.get(int(cc), set())
        if dist and str(ht) not in dist:
            try:
                client.table("video_corpus").update({
                    "class_assignment_tier": "flagged",
                }).eq("video_id", row["video_id"]).execute()
                flagged += 1
            except Exception:
                pass
    return flagged


def _log_peer_sanity_outliers(client: Any, *, since_7d: str) -> int:
    """Log-only: extreme breakout_ratio without velocity (Phase 0–1 downrank deferred)."""
    rows = (
        client.table("video_corpus")
        .select("video_id, breakout_ratio, views, content_class_id")
        .gte("indexed_at", since_7d)
        .gte("breakout_ratio", PEER_SANITY_BREAKOUT)
        .limit(500)
        .execute()
        .data
        or []
    )
    logged = 0
    for row in rows:
        views = int(row.get("views") or 0)
        if views < 10_000:
            logged += 1
            logger.info(
                "[acqe/peer_sanity] video_id=%s breakout_ratio=%s views=%s cc=%s",
                row.get("video_id"),
                row.get("breakout_ratio"),
                views,
                row.get("content_class_id"),
            )
    return logged


def _find_duplicate_class_pairs(client: Any) -> list[tuple[int, int, str]]:
    """Same format_axis under one creator_niche via junction → merge candidate (keep lower id)."""
    try:
        cc_rows = (
            client.table("content_classifications")
            .select("id, format_axis")
            .execute()
            .data
            or []
        )
        junction = (
            client.table("creator_niche_content_classes")
            .select("creator_niche_id, content_class_id, is_primary")
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[acqe] duplicate scan failed: %s", exc)
        return []

    fmt_by_cc = {int(r["id"]): str(r.get("format_axis") or "") for r in cc_rows}
    by_niche_fmt: dict[tuple[int, str], list[int]] = defaultdict(list)
    for j in junction:
        cn = int(j["creator_niche_id"])
        cc = int(j["content_class_id"])
        fmt = fmt_by_cc.get(cc, "")
        if fmt:
            by_niche_fmt[(cn, fmt)].append(cc)

    pairs: list[tuple[int, int, str]] = []
    for (_cn, fmt), ids in by_niche_fmt.items():
        uniq = sorted(set(ids))
        if len(uniq) < 2:
            continue
        keep, drop = uniq[0], uniq[1]
        pairs.append((keep, drop, fmt))
    return pairs


def _merge_content_class_ids(client: Any, keep_id: int, drop_id: int) -> bool:
    """Repoint corpus + map rows from drop_id → keep_id; deactivate drop ingest target."""
    try:
        client.table("video_corpus").update({
            "content_class_id": keep_id,
        }).eq("content_class_id", drop_id).execute()

        client.table("hashtag_class_map").update({
            "content_class_id": keep_id,
        }).eq("content_class_id", drop_id).execute()

        client.table("creator_niche_content_classes").delete().eq(
            "content_class_id", drop_id,
        ).execute()

        client.table("content_class_ingest_targets").update({
            "active": False,
            "viability_tier": "Dormant",
            "daily_vpn": 0,
        }).eq("content_class_id", drop_id).execute()
        return True
    except Exception as exc:
        logger.warning("[acqe] merge %s→%s failed: %s", drop_id, keep_id, exc)
        return False


def _auto_merge_duplicate_classes(
    client: Any,
    *,
    cold_start: bool,
    since_7d: str,
) -> dict[str, Any]:
    """Merge duplicate format_axis classes; dry-run during cold-start."""
    pairs = _find_duplicate_class_pairs(client)
    merged: list[dict[str, Any]] = []
    for keep, drop, fmt in pairs[:5]:
        entry: dict[str, Any] = {"keep": keep, "drop": drop, "format_axis": fmt}
        if cold_start:
            entry["dry_run"] = True
            merged.append(entry)
            continue
        confusion_rate = _class_confusion_rate(client, keep, drop, since_7d=since_7d)
        entry["confusion_rate_7d"] = confusion_rate
        if confusion_rate >= MERGE_CONFUSION_RATE:
            entry["merged"] = _merge_content_class_ids(client, keep, drop)
            merged.append(entry)
        else:
            entry["skipped"] = True
            merged.append(entry)
    return {"candidates": len(pairs), "actions": merged}


def _class_confusion_rate(
    client: Any,
    keep_id: int,
    drop_id: int,
    *,
    since_7d: str,
) -> float:
    """Share of rows that flip between keep/drop class ids (proxy for HI-11 confusion)."""
    try:
        rows = (
            client.table("video_corpus")
            .select("content_class_id, ingest_loop_content_class_id")
            .gte("indexed_at", since_7d)
            .in_("content_class_id", [keep_id, drop_id])
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception:
        return 0.0
    if not rows:
        return 0.0
    confused = 0
    for r in rows:
        stored = r.get("content_class_id")
        loop = r.get("ingest_loop_content_class_id")
        if stored is None or loop is None:
            continue
        if int(stored) != int(loop):
            confused += 1
    return round(confused / len(rows), 4)


def _export_junction_proposals(client: Any, *, since_7d: str) -> dict[str, Any]:
    """Nightly export when (creator_niche_id, content_class_id) appears ≥5 videos/3 nights without junction."""
    from getviews_pipeline.junction_content_class import creator_niche_has_content_class
    from getviews_pipeline.profile_niches import CREATOR_NICHE_SLUG_TO_ID

    try:
        rows = (
            client.table("video_corpus")
            .select(
                "content_class_id, inferred_creator_niche_id, niche_resolution_confidence"
            )
            .gte("indexed_at", since_7d)
            .gte("niche_resolution_confidence", VALIDATED_CONF_MIN)
            .not_.is_("content_class_id", "null")
            .not_.is_("inferred_creator_niche_id", "null")
            .limit(10_000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("[acqe] junction proposal scan failed: %s", exc)
        return {"proposals": [], "error": str(exc)}

    counts: dict[tuple[int, int], int] = defaultdict(int)
    for row in rows:
        cn = row.get("inferred_creator_niche_id")
        cc = row.get("content_class_id")
        if cn is None or cc is None:
            continue
        try:
            cn_i, cc_i = int(cn), int(cc)
        except (TypeError, ValueError):
            continue
        if creator_niche_has_content_class(cn_i, cc_i):
            continue
        counts[(cn_i, cc_i)] += 1

    slug_by_id = {v: k for k, v in CREATOR_NICHE_SLUG_TO_ID.items()}
    proposals = [
        {
            "creator_niche_id": cn,
            "creator_niche_slug": slug_by_id.get(cn),
            "content_class_id": cc,
            "videos_7d": n,
            "recommendation": "human_review_add_junction_is_primary_false",
        }
        for (cn, cc), n in sorted(counts.items(), key=lambda x: -x[1])
        if n >= 5
    ]

    history_path = (
        Path(__file__).resolve().parents[2]
        / "artifacts"
        / "qa-reports"
        / "acqe-junction-proposals-history.json"
    )
    history: dict[str, int] = {}
    try:
        if history_path.is_file():
            history = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        history = {}

    for prop in proposals:
        k = f"{prop['creator_niche_id']}:{prop['content_class_id']}"
        history[k] = history.get(k, 0) + 1

    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except OSError:
        pass

    stable = [
        p for p in proposals
        if history.get(f"{p['creator_niche_id']}:{p['content_class_id']}", 0) >= 3
    ]

    artifact = {
        "run_at": datetime.now(UTC).isoformat(),
        "proposals": stable,
        "candidates_7d": proposals,
        "auto_add": False,
        "alert_threshold_nights": 3,
        "min_videos_7d": 5,
    }

    try:
        out = (
            Path(__file__).resolve().parents[2]
            / "artifacts"
            / "qa-reports"
            / "acqe-junction-proposals.json"
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.debug("[acqe] junction proposals artifact skipped: %s", exc)

    return artifact


def _junction_invalid_rate_alert(client: Any, *, since_7d: str) -> dict[str, Any]:
    """Alert wiring when junction-invalid >0.5% on validated subset."""
    from getviews_pipeline.junction_content_class import creator_niche_has_content_class
    from getviews_pipeline.profile_niches import creator_niche_id_for_legacy_niche

    try:
        rows = (
            client.table("video_corpus")
            .select("content_class_id, ingest_loop_niche_id, niche_resolution_confidence")
            .gte("indexed_at", since_7d)
            .gte("niche_resolution_confidence", VALIDATED_CONF_MIN)
            .not_.is_("content_class_id", "null")
            .limit(5000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        return {"checked": 0, "invalid_rate": None, "alert": False, "error": str(exc)}

    invalid = 0
    checked = 0
    for row in rows:
        cc = row.get("content_class_id")
        loop = row.get("ingest_loop_niche_id")
        if cc is None or loop is None:
            continue
        cn = creator_niche_id_for_legacy_niche(int(loop))
        if cn is None:
            continue
        checked += 1
        if not creator_niche_has_content_class(cn, int(cc)):
            invalid += 1

    rate = round(invalid / max(checked, 1), 4)
    alert = checked > 0 and rate > 0.005
    if alert:
        logger.error(
            "[acqe] junction_invalid_rate=%.2f%% exceeds 0.5%% threshold (invalid=%d checked=%d)",
            rate * 100,
            invalid,
            checked,
        )
    return {
        "checked": checked,
        "invalid": invalid,
        "invalid_rate": rate,
        "alert": alert,
        "threshold": 0.005,
    }


def _write_qa_artifact(filename: str, payload: dict[str, Any]) -> None:
    try:
        out = Path(__file__).resolve().parents[2] / "artifacts" / "qa-reports" / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.debug("[acqe] artifact %s skipped: %s", filename, exc)


def _export_hook_marker_candidates(client: Any, *, since_7d: str) -> dict[str, Any]:
    """Tier-2 caption vs Tier-3 hook_type mismatch → candidate queue (no auto-append regex)."""
    from getviews_pipeline.corpus_instructiveness import predict_hook_from_caption

    try:
        rows = (
            client.table("video_corpus")
            .select("video_id, caption, hook_type, breakout_ratio")
            .gte("indexed_at", since_7d)
            .not_.is_("caption", "null")
            .not_.is_("hook_type", "null")
            .gte("breakout_ratio", 1.5)
            .limit(3000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        return {"candidates": [], "error": str(exc)}

    phrase_counts: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        caption = str(row.get("caption") or "").strip()
        gemini_hook = str(row.get("hook_type") or "").strip()
        if len(caption) < 8 or not gemini_hook:
            continue
        tier2 = predict_hook_from_caption(caption)
        if tier2 is not None and tier2 == gemini_hook:
            continue
        snippet = caption[:48].strip()
        if len(snippet) < 6:
            continue
        phrase_counts[(snippet, gemini_hook)] += 1

    candidates = [
        {
            "caption_snippet": phrase,
            "suggested_hook_type": hook,
            "videos_7d": count,
            "recommendation": "human_review_append_hook_marker",
        }
        for (phrase, hook), count in sorted(phrase_counts.items(), key=lambda x: -x[1])
        if count >= 3
    ][:20]

    artifact = {
        "run_at": datetime.now(UTC).isoformat(),
        "candidates": candidates,
        "auto_append": False,
        "min_videos_7d": 3,
    }
    _write_qa_artifact("hook-marker-candidates.json", artifact)
    return artifact


def _export_taxonomy_drift_candidates(client: Any, *, since_7d: str) -> dict[str, Any]:
    """High-breakout junction drift clusters → PD alert (no unclassified_unknown class)."""
    from getviews_pipeline.junction_content_class import creator_niche_has_content_class
    from getviews_pipeline.profile_niches import creator_niche_id_for_legacy_niche

    try:
        rows = (
            client.table("video_corpus")
            .select(
                "video_id, content_class_id, ingest_loop_niche_id, "
                "niche_resolution_confidence, breakout_ratio, analysis_json"
            )
            .gte("indexed_at", since_7d)
            .gte("niche_resolution_confidence", VALIDATED_CONF_MIN)
            .gte("breakout_ratio", 2.0)
            .not_.is_("content_class_id", "null")
            .limit(5000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        return {"clusters": [], "error": str(exc)}

    clusters: dict[tuple[int, str], dict[str, Any]] = {}
    total_validated = 0
    drift_count = 0

    for row in rows:
        total_validated += 1
        cc = int(row["content_class_id"])
        loop = row.get("ingest_loop_niche_id")
        cn = creator_niche_id_for_legacy_niche(int(loop)) if loop is not None else None
        junction_ok = cn is not None and creator_niche_has_content_class(cn, cc)
        aj = row.get("analysis_json") if isinstance(row.get("analysis_json"), dict) else {}
        cc_ctx = aj.get("content_context") if isinstance(aj.get("content_context"), dict) else {}
        subject = str(cc_ctx.get("subject_matter") or "").strip()[:120] or "unknown_subject"
        if junction_ok:
            continue
        drift_count += 1
        key = (cc, subject)
        bucket = clusters.setdefault(
            key,
            {
                "content_class_id": cc,
                "subject_matter_sample": subject,
                "video_ids": [],
                "videos_7d": 0,
            },
        )
        bucket["videos_7d"] += 1
        vid = row.get("video_id")
        if vid and len(bucket["video_ids"]) < 5:
            bucket["video_ids"].append(str(vid))

    stable = [
        {**v, "recommendation": "human_review_new_class_or_junction"}
        for v in sorted(clusters.values(), key=lambda x: -x["videos_7d"])
        if v["videos_7d"] >= 3
    ][:15]

    drift_rate = round(drift_count / max(total_validated, 1), 4)
    alert = total_validated > 0 and drift_rate >= 0.05

    artifact = {
        "run_at": datetime.now(UTC).isoformat(),
        "clusters": stable,
        "drift_rate_7d": drift_rate,
        "alert": alert,
        "alert_threshold": 0.05,
        "auto_add_class": False,
    }
    _write_qa_artifact("taxonomy-drift-candidates.json", artifact)
    if alert:
        logger.error(
            "[acqe] taxonomy_drift_rate=%.2f%% exceeds 5%% — review taxonomy-drift-candidates.json",
            drift_rate * 100,
        )
    return artifact


def run_acqe_nightly(client: Any) -> dict[str, Any]:
    """Run ACQE after corpus MV refresh. Returns summary dict for artifact logging."""
    now = datetime.now(UTC)
    since_30d = (now - timedelta(days=30)).isoformat()
    since_7d = (now - timedelta(days=7)).isoformat()

    state_row = (
        client.table("acqe_run_state")
        .select("run_count, cold_start_complete, discovery_relax_active")
        .eq("id", 1)
        .maybe_single()
        .execute()
        .data
    ) or {}
    run_count = int(state_row.get("run_count") or 0) + 1
    cold_start = run_count <= COLD_START_RUNS
    use_validated_subset = not cold_start

    metrics = _fetch_class_metrics(client, since_30d, since_7d)
    targets = (
        client.table("content_class_ingest_targets")
        .select("content_class_id")
        .execute()
        .data
        or []
    )
    tier_counts: dict[str, int] = {"Healthy": 0, "Thin": 0, "Dormant": 0}
    target_updates = 0
    discovery_relax = False

    for t in targets:
        cc_id = int(t["content_class_id"])
        m = metrics.get(cc_id, {"sample_30d": 0, "ingest_7d": 0})
        tier = _tier_for_class(m["sample_30d"], m["ingest_7d"])
        if tier in ("Thin", "Dormant"):
            discovery_relax = True
        vpn, active = _vpn_for_tier(tier)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        try:
            client.table("content_class_ingest_targets").update({
                "viability_tier": tier,
                "daily_vpn": vpn,
                "active": active,
                "updated_at": now.isoformat(),
            }).eq("content_class_id", cc_id).execute()
            target_updates += 1
        except Exception as exc:
            logger.warning("[acqe] target update failed cc=%s: %s", cc_id, exc)

    assignment_patched = _update_recent_assignment_flags(
        client,
        since_7d=since_7d,
        use_validated_subset=use_validated_subset,
    )
    outlier_flagged = _flag_cohort_outliers(client, since_7d=since_7d)
    peer_sanity_logged = _log_peer_sanity_outliers(client, since_7d=since_7d)
    merge_summary = _auto_merge_duplicate_classes(
        client, cold_start=cold_start, since_7d=since_7d,
    )
    junction_proposals = _export_junction_proposals(client, since_7d=since_7d)
    junction_alert = _junction_invalid_rate_alert(client, since_7d=since_7d)
    hook_marker_candidates = _export_hook_marker_candidates(client, since_7d=since_7d)
    taxonomy_drift = _export_taxonomy_drift_candidates(client, since_7d=since_7d)

    cross_niche_rate: float | None = None

    red_alert = (
        not cold_start
        and cross_niche_rate is not None
        and cross_niche_rate > 0.25
    )

    client.table("acqe_run_state").upsert({
        "id": 1,
        "run_count": run_count,
        "last_run_at": now.isoformat(),
        "cold_start_complete": run_count > COLD_START_RUNS,
        "discovery_relax_active": discovery_relax,
    }).execute()

    summary: dict[str, Any] = {
        "run_at": now.isoformat(),
        "run_count": run_count,
        "cold_start": cold_start,
        "tier_counts": tier_counts,
        "target_updates": target_updates,
        "assignment_rows_patched": assignment_patched,
        "cohort_outliers_flagged": outlier_flagged,
        "peer_sanity_logged": peer_sanity_logged,
        "auto_merge": merge_summary,
        "junction_proposals": junction_proposals,
        "junction_invalid_alert": junction_alert,
        "hook_marker_candidates": hook_marker_candidates,
        "taxonomy_drift_candidates": taxonomy_drift,
        "discovery_relax_active": discovery_relax,
        "cross_niche_migration_rate_7d": cross_niche_rate,
        "red_alert": red_alert,
        "red_alert_suppressed": cold_start,
    }

    _write_artifact(summary)
    logger.info("[acqe] %s", json.dumps(summary, ensure_ascii=False))
    return summary


def _write_artifact(summary: dict[str, Any]) -> None:
    """Best-effort write to artifacts/qa-reports (skipped when path unavailable)."""
    try:
        root = Path(__file__).resolve().parents[2]
        out_dir = root / "artifacts" / "qa-reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        path = out_dir / f"acqe-nightly-{day}.json"
        path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.debug("[acqe] artifact write skipped: %s", exc)
