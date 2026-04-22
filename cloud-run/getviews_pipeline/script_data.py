"""B.4.2 — Read models for ``GET /script/scene-intelligence`` and ``GET /script/hook-patterns``."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Display labels for ``hook_effectiveness.hook_type`` (Vietnamese UI).
HOOK_TYPE_PATTERN_VI: dict[str, str] = {
    "question": "Câu hỏi mở đầu",
    "bold_claim": "Tuyên bố táo bạo",
    "shock_stat": "Số liệu gây sốc",
    "story_open": "Mở đầu câu chuyện",
    "controversy": "Gây tranh cãi",
    "challenge": "Thử thách",
    "how_to": "Hướng dẫn nhanh",
    "social_proof": "Bằng chứng xã hội",
    "curiosity_gap": "Khoảng trống tò mò",
    "pain_point": "Điểm đau",
    "trend_hijack": "Bám trend",
    "none": "Không rõ hook",
    "other": "Hook khác",
}


def _pattern_label(hook_type: str) -> str:
    key = (hook_type or "").strip().lower().replace("-", "_")
    return HOOK_TYPE_PATTERN_VI.get(key, hook_type.replace("_", " ").title() or "Hook")


def _fmt_delta_pct(avg_views: int, baseline: float) -> str:
    if baseline <= 0:
        return "+0%"
    pct = (float(avg_views) / baseline - 1.0) * 100.0
    sign = "+" if pct >= 0 else ""
    return f"{sign}{int(round(pct))}%"


def latest_hook_effectiveness_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep newest row per ``hook_type`` (table may contain history)."""
    by_hook: dict[str, dict[str, Any]] = {}
    for r in sorted(rows, key=lambda x: str(x.get("computed_at") or ""), reverse=True):
        ht = str(r.get("hook_type") or "")
        if not ht or ht in by_hook:
            continue
        by_hook[ht] = r
    out = list(by_hook.values())
    out.sort(key=lambda x: int(x.get("avg_views") or 0), reverse=True)
    return out


def fetch_scene_intelligence_for_niche(sb: Any, niche_id: int) -> dict[str, Any]:
    res = (
        sb.table("scene_intelligence")
        .select(
            "niche_id, scene_type, corpus_avg_duration, winner_avg_duration, "
            "winner_overlay_style, overlay_samples, tip, reference_video_ids, sample_size, computed_at"
        )
        .eq("niche_id", niche_id)
        .order("scene_type")
        .execute()
    )
    scenes = res.data or []
    return {"niche_id": niche_id, "scenes": scenes}


def fetch_hook_patterns_for_niche(sb: Any, niche_id: int) -> dict[str, Any]:
    label = ""
    try:
        nt = sb.table("niche_taxonomy").select("name_vn, name_en").eq("id", niche_id).maybe_single().execute()
        row = nt.data or {}
        label = str(row.get("name_vn") or row.get("name_en") or "")
    except Exception as exc:
        logger.warning("[hook-patterns] niche_taxonomy lookup failed: %s", exc)

    ni_res = (
        sb.table("niche_intelligence")
        .select("organic_avg_views, commerce_avg_views, sample_size")
        .eq("niche_id", niche_id)
        .maybe_single()
        .execute()
    )
    ni = ni_res.data or {}
    org = float(ni.get("organic_avg_views") or 0.0)
    com = float(ni.get("commerce_avg_views") or 0.0)
    baseline = org if org > 0 else com
    if baseline <= 0:
        baseline = 1.0

    he_res = (
        sb.table("hook_effectiveness")
        .select("hook_type, avg_views, sample_size, trend_direction, computed_at")
        .eq("niche_id", niche_id)
        .order("computed_at", desc=True)
        .limit(200)
        .execute()
    )
    raw_rows = he_res.data or []
    latest = latest_hook_effectiveness_rows(raw_rows if isinstance(raw_rows, list) else [])

    hook_patterns: list[dict[str, Any]] = []
    max_uses = 0
    for r in latest[:12]:
        av = int(r.get("avg_views") or 0)
        sz = int(r.get("sample_size") or 0)
        max_uses = max(max_uses, sz)
        hook_patterns.append(
            {
                "pattern": _pattern_label(str(r.get("hook_type") or "")),
                "delta": _fmt_delta_pct(av, baseline),
                "uses": sz,
                "avg_views": av,
            }
        )

    # BUG-13 (QA audit 2026-04-22): hook_effectiveness rows are only written
    # by seed scripts in this build — the live ingest pipeline aggregates
    # into video_patterns / video_corpus instead. When the table is empty
    # (new niche, fresh environment) the script page used to render
    # "Chưa có dữ liệu hook cho ngách." even though 113+ indexed videos
    # existed. Fallback: derive the same leaderboard shape from
    # video_corpus.hook_type so the script surface always has data
    # whenever the Studio HooksTable has data.
    if not hook_patterns:
        hook_patterns, fallback_max_uses = _derive_hook_patterns_from_corpus(sb, niche_id, baseline)
        max_uses = max(max_uses, fallback_max_uses)

    citation = {
        "sample_size": max_uses or int(ni.get("sample_size") or 0),
        "niche_label": label,
        "window_days": 7,
    }

    return {
        "niche_id": niche_id,
        "hook_patterns": hook_patterns,
        "citation": citation,
    }


def _derive_hook_patterns_from_corpus(
    sb: Any, niche_id: int, baseline: float
) -> tuple[list[dict[str, Any]], int]:
    """Aggregate ``hook_type`` stats from ``video_corpus`` — fallback for
    BUG-13 when ``hook_effectiveness`` is empty. Returns the same
    ``hook_patterns`` shape (pattern / delta / uses / avg_views) ordered
    by avg_views desc, capped to 12."""
    try:
        res = (
            sb.table("video_corpus")
            .select("hook_type, views")
            .eq("niche_id", niche_id)
            .not_.is_("hook_type", "null")
            .limit(2000)
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        logger.warning("[hook-patterns] corpus fallback failed niche_id=%s: %s", niche_id, exc)
        return [], 0

    buckets: dict[str, dict[str, int]] = {}
    for r in rows:
        ht = str(r.get("hook_type") or "").strip().lower()
        if not ht or ht == "none":
            continue
        v = int(r.get("views") or 0)
        b = buckets.setdefault(ht, {"sum_views": 0, "n": 0})
        b["sum_views"] += v
        b["n"] += 1

    derived: list[dict[str, Any]] = []
    max_uses = 0
    for ht, b in buckets.items():
        n = b["n"]
        if n <= 0:
            continue
        av = int(round(b["sum_views"] / n))
        max_uses = max(max_uses, n)
        derived.append(
            {
                "pattern": _pattern_label(ht),
                "delta": _fmt_delta_pct(av, baseline),
                "uses": n,
                "avg_views": av,
            }
        )
    derived.sort(key=lambda r: (int(r.get("avg_views") or 0), int(r.get("uses") or 0)), reverse=True)
    return derived[:12], max_uses
