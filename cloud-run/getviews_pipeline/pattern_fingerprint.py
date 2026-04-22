"""Viral pattern fingerprinting — clusters videos by creative formula.

Design: artifacts/docs/features/viral-pattern-fingerprint.md
Schema: supabase/migrations/20260420000046_video_patterns.sql

Two audiences:

1. corpus_ingest.py — every new video gets a pattern_id stamped at ingest time.
   See compute_and_upsert_pattern().

2. pipelines.py (trend_spike / content_directions / video_diagnosis) — queries
   patterns for top weekly-delta or by niche. See get_top_delta_patterns().

Pure functions (signature, hash, display name) are unit-testable without a
Supabase client. The DB-touching helpers fail open — a pattern miss never
breaks the primary flow; pattern_id stays NULL and downstream code degrades
to the pre-pattern narrative.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pure signature logic
# ---------------------------------------------------------------------------

# Bucket edges for transitions_per_second. A video with tps=1.49 and another
# at tps=1.51 should land in the same bucket — otherwise a drifting sampling
# rate in the extractor would create thousands of spurious patterns.
#
# The edges correspond to human pacing archetypes:
#   0    –  0.3  = "long take" / minimal editing
#   0.3  –  0.8  = "standard" / GRWM / talking-head
#   0.8  –  1.3  = "tight cut" / review / reaction
#   1.3  –  2.0  = "fast cut" / energy content
#   2.0+         = "hyper cut" / edit-heavy montage
_TPS_EDGES: tuple[float, ...] = (0.3, 0.8, 1.3, 2.0)
_TPS_BUCKET_LABELS: tuple[str, ...] = (
    "long_take",
    "standard",
    "tight_cut",
    "fast_cut",
    "hyper_cut",
)


def bucket_tps(tps: float | None) -> str:
    """Map transitions_per_second to a stable pacing bucket label."""
    if tps is None:
        return "standard"
    t = float(tps)
    for edge, label in zip(_TPS_EDGES, _TPS_BUCKET_LABELS):
        if t < edge:
            return label
    return _TPS_BUCKET_LABELS[-1]


def _has_text_overlay(analysis: dict[str, Any]) -> bool:
    overlays = analysis.get("text_overlays") or []
    return any(
        str((o or {}).get("text") or "").strip()
        for o in overlays
    )


def _face_first(analysis: dict[str, Any]) -> bool:
    face_at = (analysis.get("hook_analysis") or {}).get("face_appears_at")
    try:
        return face_at is not None and float(face_at) < 1.0
    except (TypeError, ValueError):
        return False


def compute_signature(analysis: dict[str, Any]) -> dict[str, Any]:
    """Return a stable signature dict for clustering.

    Seven fields — coarse enough that minor extractor drift doesn't fracture
    patterns, specific enough that genuinely different creative formulas
    don't collide.
    """
    hook = analysis.get("hook_analysis") or {}
    return {
        "hook_type": str(hook.get("hook_type") or "other"),
        "content_arc": str(analysis.get("content_arc") or "none"),
        "tone": str(analysis.get("tone") or "educational"),
        "energy_level": str(analysis.get("energy_level") or "medium"),
        "tps_bucket": bucket_tps(analysis.get("transitions_per_second")),
        "face_first": _face_first(analysis),
        "has_text_overlay": _has_text_overlay(analysis),
    }


def signature_hash(signature: dict[str, Any]) -> str:
    """Deterministic short hash of the signature — used as video_patterns.signature_hash.

    JSON-sorts keys so the hash is independent of dict insertion order.
    SHA-256 truncated to 16 hex chars (~10^-19 collision odds per niche).
    """
    blob = json.dumps(signature, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Display name heuristic
# ---------------------------------------------------------------------------

_HOOK_TYPE_VI: dict[str, str] = {
    "question": "Câu hỏi",
    "bold_claim": "Tuyên bố mạnh",
    "shock_stat": "Số liệu sốc",
    "story_open": "Kể chuyện",
    "controversy": "Tranh cãi",
    "challenge": "Thử thách",
    "how_to": "Hướng dẫn",
    "social_proof": "Dẫn chứng",
    "curiosity_gap": "Gợi tò mò",
    "pain_point": "Chạm đau",
    "trend_hijack": "Bắt trend",
    "warning": "Cảnh báo",
    "other": "Khác",
}

_ARC_VI: dict[str, str] = {
    "list": "danh sách",
    "story": "kể chuyện",
    "before_after": "trước/sau",
    "comparison": "so sánh",
    "tutorial_steps": "hướng dẫn từng bước",
    "gallery": "phòng trưng bày",
    "none": "",
}

_PACE_VI: dict[str, str] = {
    "long_take": "quay dài",
    "standard": "",   # standard is default, omit
    "tight_cut": "cắt nhịp chặt",
    "fast_cut": "cắt nhanh",
    "hyper_cut": "cắt dồn dập",
}


def build_display_name(signature: dict[str, Any]) -> str:
    """Build a short Vietnamese label from signature fields.

    Rule-based — produces names like "Câu hỏi + trước/sau" or "Cảnh báo
    + cắt nhanh + mặt người". When every element is default, returns the
    hook_type alone.

    Phase 2 replacement: one Gemini call per new pattern to generate a
    snappier label (spec §Open Questions #2). The DB column is nullable
    so we can swap later without re-fingerprinting.
    """
    hook_vi = _HOOK_TYPE_VI.get(signature.get("hook_type", "other"), "Khác")
    parts = [hook_vi]

    arc_vi = _ARC_VI.get(signature.get("content_arc", "none"), "")
    if arc_vi:
        parts.append(arc_vi)

    pace_vi = _PACE_VI.get(signature.get("tps_bucket", "standard"), "")
    if pace_vi:
        parts.append(pace_vi)

    if signature.get("face_first"):
        parts.append("mặt người")

    return " + ".join(parts)


# ---------------------------------------------------------------------------
# Gemini display-name generator — called once per brand-new pattern.
# Fails open to build_display_name(signature) so the pipeline never blocks
# on a Gemini outage / missing API key.
# ---------------------------------------------------------------------------


def _name_prompt(signature: dict[str, Any], analysis: dict[str, Any] | None) -> str:
    hook_vi = _HOOK_TYPE_VI.get(signature.get("hook_type", "other"), "Khác")
    arc_vi = _ARC_VI.get(signature.get("content_arc", "none"), "") or "không có arc rõ"
    pace_vi = _PACE_VI.get(signature.get("tps_bucket", "standard"), "") or "nhịp chuẩn"
    energy = str(signature.get("energy_level", "medium"))
    face = "Có mặt người trong 1s đầu" if signature.get("face_first") else "Không có mặt người sớm"
    text_overlay = "Có text overlay" if signature.get("has_text_overlay") else "Không có text overlay"

    hook_phrase = ""
    what_works = ""
    if isinstance(analysis, dict):
        hook_phrase = str(((analysis.get("hook_analysis") or {}).get("hook_phrase") or "")).strip()[:160]
        what_works = str(((analysis.get("content_direction") or {}).get("what_works") or "")).strip()[:200]

    example_block = ""
    if hook_phrase or what_works:
        parts: list[str] = []
        if hook_phrase:
            parts.append(f'- Hook phrase: "{hook_phrase}"')
        if what_works:
            parts.append(f"- Cơ chế chạy: {what_works}")
        example_block = "\n\nVí dụ video thuộc pattern này:\n" + "\n".join(parts)

    return (
        "Đặt cho pattern TikTok này một cái tên tiếng Việt ngắn gọn, dễ nhớ (3-6 từ).\n\n"
        "Đặc điểm pattern:\n"
        f"- Hook type: {hook_vi}\n"
        f"- Content arc: {arc_vi}\n"
        f"- Nhịp: {pace_vi}\n"
        f"- Năng lượng: {energy}\n"
        f"- {face}\n"
        f"- {text_overlay}"
        f"{example_block}\n\n"
        "Yêu cầu:\n"
        '- 3-6 từ tiếng Việt, gợi hình (VD: "Cảnh báo phá vỡ niềm tin", "Trước sau cắt dồn dập", "Cận mặt bất ngờ")\n'
        "- KHÔNG dùng dấu câu cuối, KHÔNG bọc trong dấu ngoặc kép\n"
        "- KHÔNG giải thích, CHỈ trả về tên pattern\n\n"
        "Tên pattern:"
    )


# Sanity limits for the returned name. Gemini occasionally streams Markdown
# bullets or trailing commentary despite the "chỉ trả về tên" instruction.
_NAME_MAX_CHARS = 60


def _clean_generated_name(raw: str) -> str:
    """Trim / sanitize a Gemini-returned pattern name.

    Strips quotes, Markdown prefixes, trailing punctuation, and caps length.
    Returns "" when the cleaned string is too short to be useful — caller
    then falls back to the rule-based builder.
    """
    if not raw:
        return ""
    name = str(raw).strip()
    # Drop common Gemini pre-ambles.
    name = re.sub(r"^\s*(tên pattern\s*:|pattern name\s*:|name\s*:)\s*", "", name, flags=re.IGNORECASE)
    # Take the first line only.
    name = name.split("\n", 1)[0].strip()
    # Strip wrapping quotes + Markdown bullets.
    name = name.strip("\"'`*•- ").strip()
    # Strip trailing punctuation.
    name = re.sub(r"[.;!?,]+$", "", name).strip()
    if len(name) > _NAME_MAX_CHARS:
        name = name[:_NAME_MAX_CHARS].rstrip() + "…"
    # Require at least one Vietnamese/latin letter or 3+ chars total.
    if len(name) < 3:
        return ""
    return name


def _generate_gemini_pattern_name(
    signature: dict[str, Any], analysis: dict[str, Any] | None,
) -> str | None:
    """Ask Gemini Flash-Lite for a snappy Vietnamese pattern name.

    Returns None on any failure so callers fall back to build_display_name.
    Synchronous — caller already runs this under a thread-pool executor via
    the async compute_and_upsert_pattern wrapper.
    """
    try:
        from google.genai import types as _types  # type: ignore

        from getviews_pipeline.config import (
            GEMINI_KNOWLEDGE_FALLBACKS,
            GEMINI_KNOWLEDGE_MODEL,
        )
        from getviews_pipeline.gemini import _generate_content_models, _response_text
    except Exception as exc:
        logger.info("[pattern_fingerprint] Gemini unavailable for naming: %s", exc)
        return None

    try:
        prompt = _name_prompt(signature, analysis)
        cfg = _types.GenerateContentConfig(temperature=0.4, max_output_tokens=64)
        response = _generate_content_models(
            [prompt],
            primary_model=GEMINI_KNOWLEDGE_MODEL,
            fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
            config=cfg,
        )
        cleaned = _clean_generated_name(_response_text(response) or "")
        return cleaned or None
    except Exception as exc:
        logger.warning("[pattern_fingerprint] Gemini naming failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# DB helpers — upsert + read
# ---------------------------------------------------------------------------


def _upsert_pattern_sync(
    client: Any,
    signature: dict[str, Any],
    sig_hash: str,
    niche_id: int,
    now_iso: str,
    analysis: dict[str, Any] | None = None,
) -> str | None:
    """Insert or touch a video_patterns row and return its id.

    Fails open — returns None on any Supabase error so corpus_ingest can
    proceed without a pattern_id.
    """
    try:
        # Try SELECT first to avoid blind inserts fighting the unique constraint.
        existing = (
            client.table("video_patterns")
            .select("id, niche_spread, instance_count")
            .eq("signature_hash", sig_hash)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        if rows:
            row = rows[0]
            new_spread = list(row.get("niche_spread") or [])
            if niche_id not in new_spread:
                new_spread.append(niche_id)
            update = {
                "last_seen_at": now_iso,
                "instance_count": int(row.get("instance_count") or 0) + 1,
                "niche_spread": new_spread,
                "is_active": True,
                "computed_at": now_iso,
            }
            client.table("video_patterns").update(update).eq("id", row["id"]).execute()
            return str(row["id"])

        # Fresh pattern — insert. Try Gemini for a snappier Vietnamese name;
        # fall back to the rule-based builder on any failure. Only runs on
        # brand-new patterns (maybe a handful/week after first-run bootstrap),
        # so Gemini cost is negligible.
        display = _generate_gemini_pattern_name(signature, analysis) or build_display_name(signature)
        insert_res = (
            client.table("video_patterns")
            .insert(
                {
                    "signature_hash": sig_hash,
                    "signature": signature,
                    "display_name": display,
                    "first_seen_at": now_iso,
                    "last_seen_at": now_iso,
                    "instance_count": 1,
                    "niche_spread": [niche_id],
                    "is_active": True,
                    "computed_at": now_iso,
                }
            )
            .execute()
        )
        new_rows = insert_res.data or []
        if new_rows:
            return str(new_rows[0]["id"])
    except Exception as exc:
        logger.warning("[pattern_fingerprint] upsert failed: %s", exc)

    return None


async def compute_and_upsert_pattern(
    client: Any,
    analysis: dict[str, Any],
    niche_id: int,
) -> str | None:
    """Compute a signature for `analysis` and upsert into video_patterns.

    Returns the pattern_id UUID to stamp on the video_corpus row, or None if
    any step fails (so the corpus insert never blocks on fingerprinting).
    """
    from getviews_pipeline.runtime import run_sync

    sig = compute_signature(analysis)
    sig_hash = signature_hash(sig)
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    return await run_sync(
        _upsert_pattern_sync, client, sig, sig_hash, niche_id, now_iso, analysis,
    )


def _annotate_with_pattern_names_sync(
    client: Any, video_ids: list[str],
) -> dict[str, str]:
    """Fetch {video_id: pattern_display_name} for a batch of corpus video_ids."""
    if not video_ids:
        return {}
    try:
        res = (
            client.table("video_corpus")
            .select("video_id, pattern_id, video_patterns(display_name)")
            .in_("video_id", video_ids)
            .execute()
        )
        out: dict[str, str] = {}
        for row in res.data or []:
            pid = row.get("pattern_id")
            if not pid:
                continue
            pat = row.get("video_patterns") or {}
            name = (pat or {}).get("display_name")
            if name:
                out[str(row.get("video_id") or "")] = str(name)
        return out
    except Exception as exc:
        logger.warning("[pattern_fingerprint] annotate failed: %s", exc)
        return {}


async def annotate_with_pattern_names(
    client: Any, video_ids: list[str],
) -> dict[str, str]:
    """Async wrapper — batched lookup of pattern display names for corpus videos."""
    from getviews_pipeline.runtime import run_sync

    return await run_sync(_annotate_with_pattern_names_sync, client, video_ids)


def _get_top_delta_patterns_sync(
    client: Any,
    niche_id: int | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Return patterns with highest weekly-instance delta (rising fastest)."""
    try:
        query = (
            client.table("video_patterns")
            .select(
                "id, signature, display_name, instance_count, niche_spread, "
                "weekly_instance_count, weekly_instance_count_prev, first_seen_at"
            )
            .eq("is_active", True)
        )
        if niche_id is not None:
            query = query.contains("niche_spread", [niche_id])
        rows = (query.limit(200).execute()).data or []
        # Sort client-side by delta (Supabase can't order on a computed expression
        # without a generated column).
        def _delta(r: dict[str, Any]) -> int:
            return int(r.get("weekly_instance_count") or 0) - int(
                r.get("weekly_instance_count_prev") or 0
            )

        rows.sort(key=_delta, reverse=True)
        return rows[:limit]
    except Exception as exc:
        logger.warning("[pattern_fingerprint] top_delta query failed: %s", exc)
        return []


async def get_top_delta_patterns(
    client: Any,
    niche_id: int | None,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Async wrapper around the top-delta query.

    Used by run_trend_spike to surface "pattern #1 this week (+325%)" style
    signals in the synthesis payload.
    """
    from getviews_pipeline.runtime import run_sync

    return await run_sync(_get_top_delta_patterns_sync, client, niche_id, limit)


# ---------------------------------------------------------------------------
# Weekly-delta maintenance — must be called by a scheduled job.
# ---------------------------------------------------------------------------


def _recompute_weekly_counts_sync(client: Any, now_iso: str | None = None) -> int:
    """Refresh weekly_instance_count + weekly_instance_count_prev for all patterns.

    Counts distinct video_corpus rows per pattern_id bucketed by
    indexed_at — the last-7-days count vs the 7-to-14-days-ago count.

    Returns the number of pattern rows updated. Idempotent.

    Wire to a weekly cron (Sunday 06:00 ICT, say). Not called from the live
    stream — too expensive.
    """
    # BUG-11 (QA audit 2026-04-22): the literal ``"now() - interval '14 days'"``
    # string was being passed through to PostgREST which can't evaluate SQL
    # expressions in filter values. Every scheduled recompute fetched zero
    # rows and left ``weekly_instance_count`` at 0 for all 303 rows —
    # Studio's "LƯỢT DÙNG" column was thus always 0. Fix: compute the ISO
    # cutoff in Python before issuing the filter.
    from datetime import datetime as _dt, timedelta, timezone as _tz

    cutoff_iso = (_dt.now(tz=_tz.utc) - timedelta(days=14)).isoformat()
    try:
        # One round-trip: fetch all pattern_ids with corpus rows in last 14 days.
        cur = (
            client.table("video_corpus")
            .select("pattern_id, indexed_at")
            .gte("indexed_at", cutoff_iso)
            .not_.is_("pattern_id", "null")
            .limit(100_000)
            .execute()
        )
        rows = cur.data or []
    except Exception as exc:
        logger.warning("[pattern_fingerprint] recompute fetch failed: %s", exc)
        return 0

    from collections import Counter

    now = _dt.now(tz=_tz.utc)
    week_ago = now - timedelta(days=7)

    cur_week: Counter[str] = Counter()
    prev_week: Counter[str] = Counter()
    for r in rows:
        pid = r.get("pattern_id")
        ts_raw = r.get("indexed_at")
        if not pid or not ts_raw:
            continue
        try:
            ts = _dt.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts >= week_ago:
            cur_week[str(pid)] += 1
        else:
            prev_week[str(pid)] += 1

    touched = 0
    all_pids = set(cur_week) | set(prev_week)
    for pid in all_pids:
        try:
            client.table("video_patterns").update(
                {
                    "weekly_instance_count": int(cur_week.get(pid, 0)),
                    "weekly_instance_count_prev": int(prev_week.get(pid, 0)),
                    "computed_at": now_iso or now.isoformat(),
                }
            ).eq("id", pid).execute()
            touched += 1
        except Exception as exc:
            logger.warning("[pattern_fingerprint] update %s failed: %s", pid, exc)
    return touched


async def recompute_weekly_counts(client: Any) -> int:
    """Async entry point for the weekly cron."""
    from getviews_pipeline.runtime import run_sync

    return await run_sync(_recompute_weekly_counts_sync, client, None)


__all__ = [
    "annotate_with_pattern_names",
    "bucket_tps",
    "build_display_name",
    "compute_and_upsert_pattern",
    "compute_signature",
    "get_top_delta_patterns",
    "recompute_weekly_counts",
    "signature_hash",
]
