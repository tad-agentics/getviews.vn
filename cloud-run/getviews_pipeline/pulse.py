"""Home-screen pulse aggregator — the niche's week in four numbers.

Feeds the design's **PulseCard** on the Home screen: a bignum (total views
in the niche this week) + week-over-week delta + supporting stats
(videos ingested, new creators, viral count, new hooks).

Kept cheap on purpose — one SELECT per field, no Gemini calls. Results are
cached at the endpoint level (1h) so we're not thrashing Supabase on every
home open.

Claim-tier integration: the `adequacy` field tells the frontend how thick
the niche's corpus is today (reference_pool / basic_citation / niche_norms
/ hook_effectiveness / trend_delta / none). The UI uses this to decide
whether to render precise deltas or a softer "sắp có dữ liệu" state.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline.claim_tiers import flags_for_count

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PulseStats:
    """What PulseCard renders. Every field is degradable — zero on missing data."""

    niche_id: int
    views_this_week: int
    views_last_week: int
    views_delta_pct: float        # (this - last) / last * 100; 0 when last == 0
    videos_this_week: int
    new_creators_this_week: int
    viral_count_this_week: int    # videos with breakout_multiplier >= 3.0
    new_hooks_this_week: int      # video_patterns where last_seen_at >= 7d ago
    top_hook_name: str | None     # most-viewed pattern display_name this week
    adequacy: str                 # claim_tiers.highest_passing_tier
    as_of: str                    # ISO timestamp

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


VIRAL_BREAKOUT_THRESHOLD = 3.0


async def compute_pulse(client: Any, niche_id: int) -> PulseStats:
    """Run the six pulse queries for a single niche."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _compute_pulse_sync, client, niche_id)


def _compute_pulse_sync(client: Any, niche_id: int) -> PulseStats:
    now = datetime.now(timezone.utc)
    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)

    videos_this_week = 0
    views_this_week = 0
    views_last_week = 0
    viral_count = 0
    creator_handles_this_week: set[str] = set()
    creator_handles_last_week: set[str] = set()
    top_hook_name: str | None = None
    new_hooks_this_week = 0

    # ── this week + last week video_corpus slice ──────────────────────────
    try:
        rows = (
            client.table("video_corpus")
            .select("creator_handle, views, breakout_multiplier, created_at")
            .eq("niche_id", niche_id)
            .gte("created_at", last_week_start.isoformat())
            .execute()
            .data or []
        )
        for r in rows:
            created = r.get("created_at") or ""
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                continue
            v = int(r.get("views") or 0)
            handle = (r.get("creator_handle") or "").strip()
            bm = r.get("breakout_multiplier")
            if created_dt >= this_week_start:
                videos_this_week += 1
                views_this_week += v
                if handle:
                    creator_handles_this_week.add(handle)
                if bm is not None and float(bm) >= VIRAL_BREAKOUT_THRESHOLD:
                    viral_count += 1
            else:
                views_last_week += v
                if handle:
                    creator_handles_last_week.add(handle)
    except Exception as exc:
        logger.warning("[pulse] video_corpus query failed niche=%s: %s", niche_id, exc)

    new_creators = len(creator_handles_this_week - creator_handles_last_week)

    # ── hook patterns that touched this niche this week ───────────────────
    try:
        pat_rows = (
            client.table("video_patterns")
            .select("display_name, niche_spread, last_seen_at, weekly_instance_count, is_active")
            .eq("is_active", True)
            .gte("last_seen_at", this_week_start.isoformat())
            .execute()
            .data or []
        )
        patterns_in_niche = [
            p for p in pat_rows
            if niche_id in (p.get("niche_spread") or [])
        ]
        new_hooks_this_week = len(patterns_in_niche)
        if patterns_in_niche:
            top = max(
                patterns_in_niche,
                key=lambda p: int(p.get("weekly_instance_count") or 0),
            )
            top_hook_name = (top.get("display_name") or "").strip() or None
    except Exception as exc:
        logger.warning("[pulse] video_patterns query failed niche=%s: %s", niche_id, exc)

    delta_pct = (
        ((views_this_week - views_last_week) / views_last_week) * 100.0
        if views_last_week > 0 else 0.0
    )

    adequacy = flags_for_count(videos_this_week).highest_passing_tier

    return PulseStats(
        niche_id=niche_id,
        views_this_week=views_this_week,
        views_last_week=views_last_week,
        views_delta_pct=round(delta_pct, 1),
        videos_this_week=videos_this_week,
        new_creators_this_week=new_creators,
        viral_count_this_week=viral_count,
        new_hooks_this_week=new_hooks_this_week,
        top_hook_name=top_hook_name,
        adequacy=adequacy,
        as_of=now.isoformat(),
    )


__all__ = ["PulseStats", "VIRAL_BREAKOUT_THRESHOLD", "compute_pulse"]
