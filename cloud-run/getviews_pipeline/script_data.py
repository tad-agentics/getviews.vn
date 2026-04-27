"""B.4.2 — Read models for ``GET /script/scene-intelligence`` and ``GET /script/hook-patterns``."""

from __future__ import annotations

import logging
import math
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


# ── Idea references ────────────────────────────────────────────────────
# S3 — Drives the IdeaRefStrip above the storyboard in /app/script
# (per design pack ``screens/script.jsx`` lines 1284-1360). For a chosen
# idea we surface the top N viral videos in the same niche that share
# the idea's hook_type — proof-points the creator can study for cadence,
# overlay, and pacing reference.

_IDEA_REF_FALLBACK_LIMIT = 50  # candidates we score before slicing to ``limit``


def _resolve_hook_type(value: str | None) -> str | None:
    """Accept either the raw enum (``"question"``) or the VN display label
    (``"Câu hỏi mở đầu"``). FE callers may pass whichever they have on
    hand — RitualScript carries both, but the URL prefill scheme drops
    one of them on the floor (see ``scriptPrefillFromRitual``).

    Returns the normalized raw enum, or ``None`` when the value can't be
    resolved (caller falls back to niche-only filtering)."""
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    # Already a raw enum?
    if v in HOOK_TYPE_PATTERN_VI:
        return v
    # Reverse lookup VN label → raw enum.
    for raw, label in HOOK_TYPE_PATTERN_VI.items():
        if label == v:
            return raw
    return None


def _score_idea_reference(
    views: int,
    *,
    hook_match: bool,
) -> int:
    """Match% in the 50–100 range. Drives the top-right pill on each
    RefClipCard (design's 96/91/87/84/81 spread is cosmetic — we compute
    the actual signal). Niche match is a hard pre-filter so it counts
    for the 50-point base. Hook match adds 30, views log-bonus adds up
    to 20.

    Pure function — easy to unit-test."""
    score = 50
    if hook_match:
        score += 30
    if views > 0:
        # log10(100) = 2 → 8 pts, log10(10K) = 4 → 16 pts, log10(1M) = 6 → 20 pts.
        score += min(20, int(round(math.log10(max(views, 10)) * 4)))
    return min(100, max(50, score))


def fetch_idea_references_for_niche(
    sb: Any,
    niche_id: int,
    hook_type: str | None,
    limit: int = 5,
    exclude_video_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Top viral videos in the niche matching the chosen idea's hook_type.

    Two-stage candidate pull:

      1. Niche + hook_type filter, top-50 by views.
      2. If that yielded < ``limit``, drop the hook_type filter and refill
         from the niche's overall top-views pool (still excluding the
         already-included video_ids). Keeps the strip populated for
         narrow hook_types where the corpus only has 2-3 hits.

    Match% is computed in ``_score_idea_reference`` — niche pre-filter
    contributes 50 points, hook match adds 30, views contribute up to
    20 on a log scale. Strip is sorted by score DESC then views DESC.
    """
    excluded = set(exclude_video_ids or [])
    resolved_hook = _resolve_hook_type(hook_type)
    select_cols = (
        "video_id, creator_handle, tiktok_url, thumbnail_url, "
        "views, video_duration, hook_type, hook_phrase, caption"
    )

    # Stage 1 — hook_type filter when known.
    primary_rows: list[dict[str, Any]] = []
    if resolved_hook:
        try:
            primary_rows = (
                sb.table("video_corpus")
                .select(select_cols)
                .eq("niche_id", niche_id)
                .eq("hook_type", resolved_hook)
                .order("views", desc=True)
                .limit(_IDEA_REF_FALLBACK_LIMIT)
                .execute()
                .data
            ) or []
        except Exception as exc:
            logger.warning(
                "[idea-references] primary fetch failed niche_id=%s hook=%s: %s",
                niche_id, resolved_hook, exc,
            )
            primary_rows = []

    # Stage 2 — fallback to overall niche top-views when primary thin.
    fallback_rows: list[dict[str, Any]] = []
    if len(primary_rows) < max(1, int(limit)):
        try:
            fallback_rows = (
                sb.table("video_corpus")
                .select(select_cols)
                .eq("niche_id", niche_id)
                .order("views", desc=True)
                .limit(_IDEA_REF_FALLBACK_LIMIT)
                .execute()
                .data
            ) or []
        except Exception as exc:
            logger.warning(
                "[idea-references] fallback fetch failed niche_id=%s: %s",
                niche_id, exc,
            )
            fallback_rows = []

    # Merge with stable de-dupe — primary rows keep their hook_match=True,
    # fallback rows get hook_match only if the column happens to align.
    seen: set[str] = set(excluded)
    merged: list[tuple[dict[str, Any], bool]] = []
    for row in primary_rows:
        vid = str(row.get("video_id") or "")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        merged.append((row, True))
    for row in fallback_rows:
        vid = str(row.get("video_id") or "")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        hook_match = bool(
            resolved_hook and row.get("hook_type") == resolved_hook
        )
        merged.append((row, hook_match))

    references: list[dict[str, Any]] = []
    for row, hook_match in merged:
        views = int(row.get("views") or 0)
        match_pct = _score_idea_reference(views, hook_match=hook_match)
        duration_raw = row.get("video_duration")
        try:
            duration_sec = (
                int(round(float(duration_raw))) if duration_raw is not None else None
            )
        except (TypeError, ValueError):
            duration_sec = None
        # ``hook_phrase`` is the actual opening sentence ("Mình vừa test ___");
        # falls back to a trimmed caption snippet when the corpus row didn't
        # carry one (legacy ingest path). Either way, the FE shows it as the
        # on-card "shot purpose" gloss.
        shot_label = (row.get("hook_phrase") or "").strip()
        if not shot_label:
            cap = (row.get("caption") or "").strip()
            shot_label = cap[:80] + ("…" if len(cap) > 80 else "")
        references.append(
            {
                "video_id": str(row.get("video_id") or ""),
                "creator_handle": row.get("creator_handle"),
                "tiktok_url": row.get("tiktok_url"),
                "thumbnail_url": row.get("thumbnail_url"),
                "views": views,
                "duration_sec": duration_sec,
                "hook_type": row.get("hook_type"),
                "shot_label": shot_label or None,
                "match_pct": match_pct,
            }
        )

    references.sort(
        key=lambda r: (-int(r["match_pct"]), -int(r["views"])),
    )
    return {
        "niche_id": niche_id,
        "hook_type": resolved_hook,
        "references": references[: max(0, int(limit))],
    }
