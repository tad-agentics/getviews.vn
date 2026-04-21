"""Layer 0C — Cross-Niche Migration Detection.

Runs weekly (Sunday) after Layer 0A in _run_weekly_analytics.
Queries video_corpus directly for the full hook×format distribution
across all niches over 2 weeks, then asks Gemini to identify
format migrations (combos spreading from one niche into another).

Output: updates cross_niche_signals column in niche_insights for
affected target niches.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _week_start_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


async def _fetch_distribution(client: Any, loop: asyncio.AbstractEventLoop) -> list[dict]:
    """Fetch hook×format distribution across all niches for last 14 days.

    Groups in Python rather than relying on Supabase GROUP BY (not supported via JS client).
    """
    since_iso = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    this_week_start = _week_start_monday(date.today())
    last_week_start = this_week_start - timedelta(days=7)

    def _query() -> list[dict]:
        return (
            client.table("video_corpus")
            .select("niche_id,hook_type,content_format,indexed_at,views")
            .not_.is_("hook_type", None)
            .not_.is_("content_format", None)
            .gte("indexed_at", since_iso)
            .execute()
        ).data or []

    rows = await loop.run_in_executor(None, _query)

    # Group by (niche_id, hook_type, content_format, week)
    from collections import defaultdict
    counts: dict[tuple, dict[str, Any]] = defaultdict(lambda: {"this_week": 0, "last_week": 0, "total_views": 0})

    for r in rows:
        niche_id = r.get("niche_id")
        hook = r.get("hook_type")
        fmt = r.get("content_format")
        indexed_at = r.get("indexed_at") or ""
        views = int(r.get("views") or 0)

        if not (niche_id and hook and fmt and indexed_at):
            continue

        # Determine which week bucket
        try:
            dt = datetime.fromisoformat(indexed_at.replace("Z", "+00:00"))
            row_week = _week_start_monday(dt.date())
        except (ValueError, AttributeError):
            continue

        key = (int(niche_id), hook, fmt)
        counts[key]["total_views"] += views
        if row_week >= this_week_start:
            counts[key]["this_week"] += 1
        elif row_week >= last_week_start:
            counts[key]["last_week"] += 1

    distribution = []
    for (niche_id, hook, fmt), data in counts.items():
        distribution.append({
            "niche_id": niche_id,
            "hook_type": hook,
            "content_format": fmt,
            "this_week": data["this_week"],
            "last_week": data["last_week"],
            "avg_views": data["total_views"] // max(data["this_week"] + data["last_week"], 1),
        })

    return distribution


async def _fetch_niche_names(client: Any, loop: asyncio.AbstractEventLoop) -> dict[int, str]:
    def _query() -> list[dict]:
        return (
            client.table("niche_taxonomy")
            .select("id,name_vn,name_en")
            .execute()
        ).data or []

    rows = await loop.run_in_executor(None, _query)
    return {
        int(r["id"]): (r.get("name_vn") or r.get("name_en") or str(r["id"]))
        for r in rows
    }


async def run_cross_niche_migration(client: Any | None = None) -> dict[str, Any]:
    """Module 0C entry point. Called from _run_weekly_analytics in corpus_ingest.py."""
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.gemini import _generate_content_models, _response_text, _normalize_response
    from getviews_pipeline.config import GEMINI_SYNTHESIS_MODEL, GEMINI_SYNTHESIS_FALLBACKS
    from getviews_pipeline.layer0_prompts import CROSS_NICHE_PROMPT_TEMPLATE, LAYER0_MIGRATION_RESPONSE_SCHEMA
    from google.genai import types

    if client is None:
        client = get_service_client()

    loop = asyncio.get_event_loop()
    week_of_str = _week_start_monday(date.today()).isoformat()

    distribution, niche_names = await asyncio.gather(
        _fetch_distribution(client, loop),
        _fetch_niche_names(client, loop),
    )

    if not distribution:
        logger.info("[layer0c] No distribution data — skipping")
        return {"migrations_found": 0}

    # Annotate distribution with niche names for Gemini
    annotated = [
        {**row, "niche_name": niche_names.get(row["niche_id"], str(row["niche_id"]))}
        for row in distribution
    ]

    distributions_json = json.dumps(annotated, ensure_ascii=False, indent=2)
    prompt = CROSS_NICHE_PROMPT_TEMPLATE.format(distributions_json=distributions_json)

    cfg = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        response_json_schema=LAYER0_MIGRATION_RESPONSE_SCHEMA,
    )

    try:
        response = await loop.run_in_executor(
            None,
            lambda: _generate_content_models(
                [prompt],
                primary_model=GEMINI_SYNTHESIS_MODEL,
                fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
                config=cfg,
            ),
        )
        text = _response_text(response)
        parsed = json.loads(_normalize_response(text)) if text.strip() else {}
        migrations: list[dict] = parsed.get("migrations", []) if isinstance(parsed, dict) else []
    except Exception as exc:
        logger.error("[layer0c] Gemini call failed: %s", exc)
        return {"migrations_found": 0, "error": str(exc)}

    if not migrations:
        logger.info("[layer0c] No format migrations detected this week")
        return {"migrations_found": 0}

    logger.info("[layer0c] %d migrations detected", len(migrations))

    # Group migrations by target niche and update cross_niche_signals in niche_insights
    target_map: dict[str, list[dict]] = {}
    for m in migrations:
        target = m.get("target_niche", "")
        target_map.setdefault(target, []).append(m)

    # Resolve target niche names → IDs
    name_to_id = {v: k for k, v in niche_names.items()}
    updates_written = 0

    for target_niche_name, signals in target_map.items():
        niche_id = name_to_id.get(target_niche_name)
        if not niche_id:
            logger.warning("[layer0c] Could not resolve niche_id for '%s'", target_niche_name)
            continue

        def _update(nid: int = niche_id, sigs: list = signals) -> None:
            client.table("niche_insights").update(
                {"cross_niche_signals": sigs}
            ).eq("niche_id", nid).eq("week_of", week_of_str).execute()

        try:
            await loop.run_in_executor(None, _update)
            updates_written += 1
        except Exception as exc:
            logger.error("[layer0c] Failed to update niche_id=%d: %s", niche_id, exc)

    logger.info(
        "[layer0c] done: migrations=%d niche_updates=%d",
        len(migrations), updates_written,
    )
    return {"migrations_found": len(migrations), "niche_updates": updates_written}
