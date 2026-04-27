"""D3b (2026-06-04) — Kho Douyin · daily adapt-synth orchestrator.

Wires D3a (``douyin_synth.synth_douyin_adapt``) into the daily cron.
After D2 ingest fills ``douyin_video_corpus`` with raw videos, this
module walks the stale rows (synth_computed_at NULL or older than the
freshness window) and grades each with a Gemini call, then upserts the
adapt fields back onto the row.

Stale-row policy mirrors ``pattern_deck_synth``:
  • Walk ``douyin_video_corpus`` ordered by ``synth_computed_at NULLS
    FIRST`` (uses the partial index ``idx_douyin_corpus_synth_stale``
    from D1's migration).
  • ``synth_computed_at`` is set to ``now()`` after every successful
    synth so the next cron skips fresh rows.
  • Re-grading window = 7 days (same as ``DECK_STALE_AFTER``). If a
    creator's video metadata changes (rare) or the synth prompt is
    bumped, rows roll back into the queue automatically.

Cron cadence: 23:00 UTC (06:00 Asia/Ho_Chi_Minh), 1 hour after the D2
ingest at 22:00 UTC. Bounded daily cost ≈ $0.50 (50 rows × ~$0.01
Gemini synth at flash-preview pricing).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline.douyin_synth import synth_douyin_adapt

logger = logging.getLogger(__name__)


# ── Config ──────────────────────────────────────────────────────────

# Cap per batch. The D2 cron creates ~50 rows/day; cap=100 lets the
# synth catch up if a previous day failed without blowing the budget.
DEFAULT_BATCH_CAP = 100

# Re-grade rows older than this. Mirrors ``DECK_STALE_AFTER`` from
# pattern_deck_synth — 7 days lets prompt rolls / corpus updates
# re-percolate without a manual re-run.
SYNTH_STALE_AFTER = timedelta(days=7)


# ── Result type ─────────────────────────────────────────────────────


@dataclass
class DouyinAdaptBatchSummary:
    considered: int = 0
    generated: int = 0
    failed_synth: int = 0
    failed_upsert: int = 0
    skipped_no_title: int = 0  # row had no title_zh — synth skipped
    errors: list[str] = field(default_factory=list)


# ── Service-client accessor (test hook) ─────────────────────────────


def _service_client() -> Any:
    from getviews_pipeline.supabase_client import get_service_client

    return get_service_client()


# ── Stale-rows fetcher ──────────────────────────────────────────────


def _fetch_stale_corpus_rows(
    client: Any,
    *,
    cap: int,
) -> list[dict[str, Any]]:
    """Rows ordered by ``synth_computed_at NULLS FIRST`` — null first
    (never-graded), then oldest re-grade window. Uses the partial
    index ``idx_douyin_corpus_synth_stale``.

    Returns the columns ``synth_douyin_adapt`` needs as inputs +
    ``video_id`` (for upsert) + ``niche_id`` (for the niche-label
    join). Only fetches what's needed to keep the payload small —
    ``analysis_json`` is intentionally NOT pulled.
    """
    cutoff = (datetime.now(timezone.utc) - SYNTH_STALE_AFTER).isoformat()
    try:
        res = (
            client.table("douyin_video_corpus")
            .select(
                "video_id, niche_id, title_zh, title_vi, "
                "hook_phrase, hook_type, content_format, synth_computed_at"
            )
            .or_(f"synth_computed_at.is.null,synth_computed_at.lt.{cutoff}")
            .order("synth_computed_at", desc=False, nullsfirst=True)
            .limit(cap)
            .execute()
        )
        return list(res.data or [])
    except Exception as exc:
        logger.exception("[douyin-synth-batch] stale fetch failed: %s", exc)
        return []


# ── Niche label resolver ────────────────────────────────────────────


def _fetch_niche_labels(
    client: Any,
    niche_ids: list[int],
) -> dict[int, dict[str, str]]:
    """Single batch query → ``{niche_id: {name_vn, name_zh}}``.

    Avoids N+1 — D2 daily ingest only seeds ~10 niches, but a re-grade
    batch may touch hundreds of rows spanning all of them.
    """
    if not niche_ids:
        return {}
    deduped = sorted(set(int(n) for n in niche_ids))
    try:
        res = (
            client.table("douyin_niche_taxonomy")
            .select("id, name_vn, name_zh")
            .in_("id", deduped)
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        logger.warning(
            "[douyin-synth-batch] niche label fetch failed: %s", exc,
        )
        return {}
    return {
        int(r["id"]): {
            "name_vn": str(r.get("name_vn") or ""),
            "name_zh": str(r.get("name_zh") or ""),
        }
        for r in rows
        if r.get("id") is not None
    }


# ── Single-row upsert ──────────────────────────────────────────────


def _upsert_synth_result(
    client: Any,
    *,
    video_id: str,
    synth: Any,  # DouyinAdaptSynth
) -> bool:
    """Persist the synth result back onto the row + stamp
    ``synth_computed_at``. Returns True on success."""
    try:
        client.table("douyin_video_corpus").update({
            "adapt_level": synth.adapt_level,
            "adapt_reason": synth.adapt_reason,
            "eta_weeks_min": int(synth.eta_weeks_min),
            "eta_weeks_max": int(synth.eta_weeks_max),
            # Sub_vi: the synth's gloss may be richer than the D2a
            # translator's because it sees the niche + hook context.
            # Overwriting the translator's earlier value is intentional.
            "sub_vi": synth.sub_vi,
            "translator_notes": [n.model_dump() for n in synth.translator_notes],
            "synth_computed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("video_id", video_id).execute()
        return True
    except Exception as exc:
        logger.warning(
            "[douyin-synth-batch] upsert failed video_id=%s: %s",
            video_id, exc,
        )
        return False


# ── Top-level orchestrator ─────────────────────────────────────────


def run_douyin_adapt_batch(
    client: Any | None = None,
    *,
    cap: int = DEFAULT_BATCH_CAP,
    video_ids: list[str] | None = None,
) -> DouyinAdaptBatchSummary:
    """Synthesize adapt grades for the staleest ``cap`` corpus rows.

    ``video_ids`` overrides the staleness query — useful for smoke
    tests + admin manual reruns of specific videos.

    The function is synchronous (no async I/O) because the underlying
    Gemini call is sync; the Cloud Run wrapper handles event-loop
    integration via ``run_sync`` upstream.
    """
    summary = DouyinAdaptBatchSummary()
    sb = client or _service_client()

    # ── Fetch candidate rows ─────────────────────────────────────
    if video_ids:
        try:
            res = (
                sb.table("douyin_video_corpus")
                .select(
                    "video_id, niche_id, title_zh, title_vi, "
                    "hook_phrase, hook_type, content_format, synth_computed_at"
                )
                .in_("video_id", video_ids)
                .execute()
            )
            rows = list(res.data or [])
        except Exception as exc:
            logger.exception(
                "[douyin-synth-batch] explicit-id fetch failed: %s", exc,
            )
            summary.errors.append(f"id_fetch: {exc}")
            return summary
    else:
        rows = _fetch_stale_corpus_rows(sb, cap=cap)

    summary.considered = len(rows)
    if not rows:
        return summary

    # ── Resolve niche labels in one batched query ───────────────
    niche_ids = [r["niche_id"] for r in rows if r.get("niche_id") is not None]
    niches_by_id = _fetch_niche_labels(sb, niche_ids)

    # ── Per-row synth → upsert ──────────────────────────────────
    for row in rows:
        vid = str(row.get("video_id") or "")
        title_zh = str(row.get("title_zh") or "").strip()
        if not vid:
            continue
        if not title_zh:
            summary.skipped_no_title += 1
            # Stamp synth_computed_at so we don't re-poll this row every
            # day — the corpus row literally has nothing to grade.
            try:
                sb.table("douyin_video_corpus").update({
                    "synth_computed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("video_id", vid).execute()
            except Exception:
                pass
            continue

        niche_meta = niches_by_id.get(int(row.get("niche_id") or -1)) or {
            "name_vn": "", "name_zh": "",
        }

        synth = synth_douyin_adapt(
            title_zh=title_zh,
            title_vi=row.get("title_vi"),
            hook_phrase=row.get("hook_phrase"),
            hook_type=row.get("hook_type"),
            niche_name_vn=niche_meta["name_vn"],
            niche_name_zh=niche_meta["name_zh"],
            content_format_hints=row.get("content_format"),
        )
        if synth is None:
            summary.failed_synth += 1
            continue

        if _upsert_synth_result(sb, video_id=vid, synth=synth):
            summary.generated += 1
        else:
            summary.failed_upsert += 1

    logger.info(
        "[douyin-synth-batch] done — considered=%d generated=%d "
        "failed_synth=%d failed_upsert=%d skipped_no_title=%d",
        summary.considered, summary.generated, summary.failed_synth,
        summary.failed_upsert, summary.skipped_no_title,
    )
    return summary


__all__ = [
    "DEFAULT_BATCH_CAP",
    "SYNTH_STALE_AFTER",
    "DouyinAdaptBatchSummary",
    "run_douyin_adapt_batch",
]
