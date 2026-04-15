"""Layer 0B — Sound Insight.

Runs daily (after video_dang_hoc in corpus_ingest.py daily batch).
Detects "emerging" sounds in trending_sounds (this week vs last week)
and generates a Vietnamese paragraph explaining WHY the sound works.

Emerging = usage_count this week >= 3 AND last week <= 1 (or absent).
Output stored as sound_insight_text in trending_sounds.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# A sound is "emerging" if it meets both thresholds
EMERGING_MIN_THIS_WEEK = 3
EMERGING_MAX_LAST_WEEK = 1


def _week_start_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


async def _find_emerging_sounds(client: Any, loop: asyncio.AbstractEventLoop) -> list[dict]:
    """Detect sounds that jumped from ≤1 video last week to ≥3 this week.

    Queries trending_sounds with a self-join on week_of. No niche_daily_sounds needed.
    """
    this_week = _week_start_monday(date.today()).isoformat()
    last_week = (date.fromisoformat(this_week) - timedelta(days=7)).isoformat()

    def _fetch_this_week() -> list[dict]:
        return (
            client.table("trending_sounds")
            .select("id,niche_id,sound_id,sound_name,usage_count,week_of")
            .eq("week_of", this_week)
            .gte("usage_count", EMERGING_MIN_THIS_WEEK)
            .execute()
        ).data or []

    def _fetch_last_week() -> list[dict]:
        return (
            client.table("trending_sounds")
            .select("sound_id,niche_id,usage_count")
            .eq("week_of", last_week)
            .execute()
        ).data or []

    this_week_rows, last_week_rows = await asyncio.gather(
        loop.run_in_executor(None, _fetch_this_week),
        loop.run_in_executor(None, _fetch_last_week),
    )

    # Build last-week lookup: (sound_id, niche_id) → usage_count
    last_week_map: dict[tuple[str, int], int] = {
        (r["sound_id"], int(r["niche_id"])): int(r.get("usage_count") or 0)
        for r in last_week_rows
    }

    emerging = []
    for row in this_week_rows:
        key = (row["sound_id"], int(row["niche_id"]))
        prev_count = last_week_map.get(key, 0)
        if prev_count <= EMERGING_MAX_LAST_WEEK:
            emerging.append({**row, "prev_count": prev_count})

    return emerging


async def _fetch_sound_videos(
    client: Any,
    loop: asyncio.AbstractEventLoop,
    sound_id: str,
    niche_id: int,
    since_iso: str,
) -> list[dict]:
    """Fetch trimmed analysis for up to 5 videos using this sound in this niche."""

    def _query() -> list[dict]:
        return (
            client.table("video_corpus")
            .select("video_id,analysis_json,views,likes,comments,shares")
            .eq("niche_id", niche_id)
            .eq("sound_id", sound_id)
            .gte("indexed_at", since_iso)
            .order("views", desc=True)
            .limit(5)
            .execute()
        ).data or []

    rows = await loop.run_in_executor(None, _query)
    result = []
    for r in rows:
        analysis = r.get("analysis_json") or {}
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except json.JSONDecodeError:
                analysis = {}
        hook = analysis.get("hook_analysis") or {}
        scenes = analysis.get("scenes") or []
        result.append({
            "hook_type": hook.get("hook_type"),
            "tone": analysis.get("tone"),
            "scene_sequence": [s.get("type") for s in scenes[:5]],
            "transitions_per_second": analysis.get("transitions_per_second"),
            "views": int(r.get("views") or 0),
        })
    return result


async def _fetch_niche_name(client: Any, loop: asyncio.AbstractEventLoop, niche_id: int) -> str:
    def _query() -> list[dict]:
        return (
            client.table("niche_taxonomy")
            .select("name_vn,name_en")
            .eq("id", niche_id)
            .limit(1)
            .execute()
        ).data or []

    rows = await loop.run_in_executor(None, _query)
    if rows:
        return rows[0].get("name_vn") or rows[0].get("name_en") or str(niche_id)
    return str(niche_id)


async def run_sound_insights(client: Any | None = None) -> dict[str, int]:
    """Module 0B entry point. Called from daily batch in corpus_ingest.py."""
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.gemini import gemini_text_only
    from getviews_pipeline.layer0_prompts import SOUND_INSIGHT_PROMPT_TEMPLATE

    if client is None:
        client = get_service_client()

    loop = asyncio.get_event_loop()
    analyzed = 0
    errors = 0

    from datetime import datetime, timezone, timedelta
    since_iso = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    emerging_sounds = await _find_emerging_sounds(client, loop)
    if not emerging_sounds:
        logger.info("[layer0b] No emerging sounds this week — skipping")
        return {"analyzed": 0, "errors": 0}

    logger.info("[layer0b] %d emerging sounds detected", len(emerging_sounds))

    for sound in emerging_sounds:
        sound_id = sound["sound_id"]
        sound_name = sound.get("sound_name") or sound_id
        niche_id = int(sound["niche_id"])
        count = int(sound.get("usage_count") or 0)
        prev_count = int(sound.get("prev_count") or 0)
        row_id = sound.get("id")

        try:
            niche_name, videos = await asyncio.gather(
                _fetch_niche_name(client, loop, niche_id),
                _fetch_sound_videos(client, loop, sound_id, niche_id, since_iso),
            )

            if not videos:
                logger.info("[layer0b] sound=%s: no videos found — skipping", sound_name)
                continue

            trimmed_json = json.dumps(videos, ensure_ascii=False, indent=2)
            prompt = SOUND_INSIGHT_PROMPT_TEMPLATE.format(
                sound_name=sound_name,
                niche_name=niche_name,
                count=count,
                prev_count=prev_count,
                trimmed_analysis_jsons=trimmed_json,
            )

            # Use gemini_text_only for lightweight text response (no JSON schema needed)
            insight_text = await loop.run_in_executor(
                None,
                gemini_text_only,
                prompt,
                {},  # empty session_context — Layer 0 is stateless
            )
            insight_text = insight_text.strip()

            if not insight_text:
                logger.warning("[layer0b] sound=%s: empty insight returned", sound_name)
                continue

            # Update sound_insight_text on the trending_sounds row
            if row_id:
                def _update_sound(rid: str = row_id, text: str = insight_text) -> None:
                    client.table("trending_sounds").update(
                        {"sound_insight_text": text}
                    ).eq("id", rid).execute()

                await loop.run_in_executor(None, _update_sound)

            analyzed += 1
            logger.info("[layer0b] sound=%s niche=%s: insight written", sound_name, niche_name)

        except Exception as exc:
            logger.error("[layer0b] sound=%s: %s", sound_name, exc)
            errors += 1

    logger.info("[layer0b] done: analyzed=%d errors=%d", analyzed, errors)
    return {"analyzed": analyzed, "errors": errors}
