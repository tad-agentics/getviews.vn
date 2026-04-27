"""D5c (2026-06-05) — Kho Douyin · weekly pattern-signals orchestrator.

Wires D5b (``douyin_patterns_synth.synth_douyin_patterns``) into the
weekly cron. For each active Douyin niche:

  1. Compute the ISO Monday 00:00 UTC ``week_of`` date for this run.
  2. Skip the niche if a row for ``(niche_id, week_of)`` already exists
     and is fresh (cron retry idempotence).
  3. Pull the niche's last-7d corpus (ordered by views DESC, capped
     at the per-niche pool size).
  4. Call ``synth_douyin_patterns`` to cluster into 3 ranked patterns.
  5. UPSERT the 3 rows on ``(niche_id, week_of, rank)``, computing
     ``cn_rise_pct_avg`` from the sample videos' ``cn_rise_pct``.

Cron cadence: Mondays 21:00 UTC (Mondays 04:00 Asia/Ho_Chi_Minh) —
late enough that the Sunday's ingest+synth crons (22:00 UTC + 23:00
UTC respectively) have completed two full days, so the corpus snapshot
the synthesiser sees is fresh.

Cost envelope: 10 niches × ~600 output tokens × flash-preview ≈
$0.0015/week. Wall-clock ≈ 90 seconds for 10 sequential synths.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from statistics import mean
from typing import Any

from getviews_pipeline.douyin_patterns_synth import (
    DouyinPatternsSynth,
    DouyinPatternsSynthInputVideo,
    synth_douyin_patterns,
)

logger = logging.getLogger(__name__)


# ── Config ──────────────────────────────────────────────────────────

# Per-niche corpus pool size sent to the synthesiser. Larger pools
# improve clustering but increase input tokens; 30 is enough for a
# clear top-3 separation without bloating the prompt.
DEFAULT_POOL_PER_NICHE = 30

# How far back to scan ``douyin_video_corpus.indexed_at`` for the
# clustering pool. The Douyin daily ingest only retains last 7d; this
# matches the corpus retention so the synth never sees stale rows.
LOOKBACK_DAYS = 7

# Bound the live Gemini calls to keep wall-clock predictable.
DEFAULT_MAX_NICHES = 20

# Weekly synth doesn't need a stale-row check beyond "row already
# exists for this (niche, week_of) AND was computed within this
# threshold". 6 days lets a cron retry on Mon-Tue land cleanly while
# Wed manual reruns force a re-compute.
SYNTH_FRESH_FOR = timedelta(days=6)


# ── Result type ─────────────────────────────────────────────────────


@dataclass
class DouyinPatternsBatchSummary:
    considered_niches: int = 0
    skipped_thin_pool: int = 0    # < MIN_INPUT_POOL rows in last 7d
    skipped_fresh: int = 0        # already computed for this week
    failed_synth: int = 0         # Gemini error / hallucination guard
    failed_upsert: int = 0
    written_rows: int = 0         # 3 per successful niche
    week_of: str | None = None
    errors: list[str] = field(default_factory=list)


# ── Helpers ─────────────────────────────────────────────────────────


def _service_client() -> Any:
    from getviews_pipeline.supabase_client import get_service_client

    return get_service_client()


def _iso_monday_utc(now: datetime | None = None) -> date:
    """ISO Monday 00:00 UTC of the synth week. Stored as DATE in
    ``douyin_patterns.week_of`` so equality joins are TZ-safe."""
    n = now or datetime.now(UTC)
    # weekday(): Mon=0..Sun=6. Subtract weekday() to land on this
    # week's Monday.
    monday = n.date() - timedelta(days=n.weekday())
    return monday


def _fetch_active_niches(
    client: Any,
    *,
    niche_ids: list[int] | None,
) -> list[dict[str, Any]]:
    """Return active Douyin niches in deterministic id-asc order."""
    try:
        q = (
            client.table("douyin_niche_taxonomy")
            .select("id, slug, name_vn, name_zh")
            .eq("active", True)
        )
        if niche_ids:
            q = q.in_("id", sorted(set(int(n) for n in niche_ids)))
        res = q.order("id", desc=False).execute()
        return list(res.data or [])
    except Exception as exc:
        logger.exception("[douyin-patterns-batch] niche fetch failed: %s", exc)
        return []


def _fetch_existing_week_rows(
    client: Any,
    *,
    week_of: date,
) -> dict[int, datetime]:
    """``{niche_id: computed_at}`` for rows already written this week.

    The orchestrator uses this to short-circuit fresh niches on cron
    retries — only re-computing if the existing row is older than
    ``SYNTH_FRESH_FOR``.
    """
    try:
        res = (
            client.table("douyin_patterns")
            .select("niche_id, computed_at")
            .eq("week_of", week_of.isoformat())
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        logger.warning(
            "[douyin-patterns-batch] existing-week fetch failed: %s", exc,
        )
        return {}

    out: dict[int, datetime] = {}
    for r in rows:
        if r.get("niche_id") is None or not r.get("computed_at"):
            continue
        try:
            ts = datetime.fromisoformat(str(r["computed_at"]).replace("Z", "+00:00"))
        except ValueError:
            continue
        # Keep the latest computed_at per niche (3 rows per niche).
        existing = out.get(int(r["niche_id"]))
        if existing is None or ts > existing:
            out[int(r["niche_id"])] = ts
    return out


def _fetch_niche_corpus(
    client: Any,
    *,
    niche_id: int,
    pool_size: int,
    lookback_days: int,
) -> list[DouyinPatternsSynthInputVideo]:
    cutoff = (
        datetime.now(UTC) - timedelta(days=lookback_days)
    ).isoformat()
    try:
        res = (
            client.table("douyin_video_corpus")
            .select(
                "video_id, title_zh, title_vi, hook_phrase, hook_type, "
                "content_format, views, cn_rise_pct"
            )
            .eq("niche_id", niche_id)
            .gte("indexed_at", cutoff)
            .order("views", desc=True)
            .limit(pool_size)
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        logger.warning(
            "[douyin-patterns-batch] niche=%d corpus fetch failed: %s",
            niche_id, exc,
        )
        return []

    out: list[DouyinPatternsSynthInputVideo] = []
    for r in rows:
        vid = str(r.get("video_id") or "").strip()
        if not vid:
            continue
        out.append(
            DouyinPatternsSynthInputVideo(
                video_id=vid,
                title_zh=r.get("title_zh"),
                title_vi=r.get("title_vi"),
                hook_phrase=r.get("hook_phrase"),
                hook_type=r.get("hook_type"),
                content_format=r.get("content_format"),
                views=int(r.get("views") or 0),
                cn_rise_pct=(
                    float(r["cn_rise_pct"])
                    if r.get("cn_rise_pct") is not None
                    else None
                ),
            ),
        )
    return out


def _avg_cn_rise_for_sample(
    pool: list[DouyinPatternsSynthInputVideo],
    sample_video_ids: list[str],
) -> float | None:
    """Mean ``cn_rise_pct`` across the sample. None when no sampled
    row has a delta yet (Douyin re-ingest hasn't seen a 2nd snapshot)."""
    by_id = {v.video_id: v for v in pool}
    values: list[float] = []
    for sid in sample_video_ids:
        v = by_id.get(sid)
        if v and v.cn_rise_pct is not None:
            values.append(float(v.cn_rise_pct))
    if not values:
        return None
    return float(mean(values))


def _upsert_pattern_rows(
    client: Any,
    *,
    niche_id: int,
    week_of: date,
    synth: DouyinPatternsSynth,
    pool: list[DouyinPatternsSynthInputVideo],
) -> int:
    """UPSERT exactly 3 rows on (niche_id, week_of, rank). Returns
    the count of rows successfully written."""
    payload = []
    now_iso = datetime.now(UTC).isoformat()
    for p in synth.patterns:
        avg = _avg_cn_rise_for_sample(pool, list(p.sample_video_ids))
        payload.append({
            "niche_id": niche_id,
            "week_of": week_of.isoformat(),
            "rank": int(p.rank),
            "name_vn": p.name_vn,
            "name_zh": p.name_zh,
            "hook_template_vi": p.hook_template_vi,
            "format_signal_vi": p.format_signal_vi,
            "sample_video_ids": list(p.sample_video_ids),
            "cn_rise_pct_avg": avg,
            "computed_at": now_iso,
        })
    try:
        (
            client.table("douyin_patterns")
            .upsert(payload, on_conflict="niche_id,week_of,rank")
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "[douyin-patterns-batch] niche=%d week=%s upsert failed: %s",
            niche_id, week_of.isoformat(), exc,
        )
        return 0
    return len(payload)


# ── Top-level orchestrator ─────────────────────────────────────────


def run_douyin_patterns_batch(
    client: Any | None = None,
    *,
    niche_ids: list[int] | None = None,
    pool_size: int = DEFAULT_POOL_PER_NICHE,
    lookback_days: int = LOOKBACK_DAYS,
    max_niches: int = DEFAULT_MAX_NICHES,
    force: bool = False,
    now: datetime | None = None,
) -> DouyinPatternsBatchSummary:
    """Synthesize this week's 3 pattern signals for each active niche.

    ``niche_ids`` overrides the active-niches query — admin manual
    reruns of a single niche after a synth-prompt bump.

    ``force=True`` ignores the ``SYNTH_FRESH_FOR`` short-circuit and
    re-computes every niche (admin reruns; cron uses ``force=False``).

    ``now`` is injected for testability — keeps ``_iso_monday_utc`` and
    the corpus lookback cutoff deterministic in tests.
    """
    sb = client or _service_client()
    week_of = _iso_monday_utc(now)
    summary = DouyinPatternsBatchSummary(week_of=week_of.isoformat())

    niches = _fetch_active_niches(sb, niche_ids=niche_ids)
    if max_niches and len(niches) > max_niches:
        niches = niches[:max_niches]
    summary.considered_niches = len(niches)
    if not niches:
        return summary

    existing = {} if force else _fetch_existing_week_rows(sb, week_of=week_of)
    cutoff_now = now or datetime.now(UTC)

    for niche in niches:
        nid = int(niche.get("id") or 0)
        if nid <= 0:
            continue

        # Idempotence — skip if a fresh row already exists for this
        # (niche, week). Cron retries on the same day are no-ops.
        prev_ts = existing.get(nid)
        if prev_ts is not None and (cutoff_now - prev_ts) < SYNTH_FRESH_FOR:
            summary.skipped_fresh += 1
            continue

        pool = _fetch_niche_corpus(
            sb,
            niche_id=nid,
            pool_size=pool_size,
            lookback_days=lookback_days,
        )

        synth = synth_douyin_patterns(
            niche_name_vn=str(niche.get("name_vn") or ""),
            niche_name_zh=str(niche.get("name_zh") or ""),
            videos=pool,
        )
        if synth is None:
            # Distinguish thin-pool from synth-error so observability
            # has a clean signal.
            from getviews_pipeline.douyin_patterns_synth import MIN_INPUT_POOL

            if len(pool) < MIN_INPUT_POOL:
                summary.skipped_thin_pool += 1
            else:
                summary.failed_synth += 1
            continue

        written = _upsert_pattern_rows(
            sb,
            niche_id=nid,
            week_of=week_of,
            synth=synth,
            pool=pool,
        )
        if written == 0:
            summary.failed_upsert += 1
            continue
        summary.written_rows += written

    logger.info(
        "[douyin-patterns-batch] done — week=%s considered=%d written=%d "
        "skipped_fresh=%d skipped_thin=%d failed_synth=%d failed_upsert=%d",
        summary.week_of, summary.considered_niches, summary.written_rows,
        summary.skipped_fresh, summary.skipped_thin_pool,
        summary.failed_synth, summary.failed_upsert,
    )
    return summary


__all__ = [
    "DEFAULT_MAX_NICHES",
    "DEFAULT_POOL_PER_NICHE",
    "LOOKBACK_DAYS",
    "SYNTH_FRESH_FOR",
    "DouyinPatternsBatchSummary",
    "run_douyin_patterns_batch",
]
