"""Weekly batch: aggregate trending sounds from video_corpus into trending_sounds table."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _week_start_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


async def run_sound_aggregation(client: Any | None = None) -> dict[str, Any]:
    """Aggregate top non-original sounds per niche for current week. Upsert trending_sounds."""
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    week_of = _week_start_monday(date.today())
    week_of_str = week_of.isoformat()
    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    since_iso = since_dt.isoformat()

    loop = asyncio.get_event_loop()

    def _niche_ids() -> list[int]:
        niches_res = client.table("niche_taxonomy").select("id").execute()
        return [int(r["id"]) for r in (niches_res.data or [])]

    try:
        niches = await loop.run_in_executor(None, _niche_ids)
    except Exception as exc:
        logger.error("[sound_aggregation] niche_taxonomy: %s", exc)
        return {"upserted": 0, "error": str(exc)}

    total_upserted = 0
    for niche_id in niches:
        try:

            def _fetch_corpus(_nid: int = niche_id) -> list[dict[str, Any]]:
                return (
                    client.table("video_corpus")
                    .select("sound_id,sound_name,is_original_sound,views")
                    .eq("niche_id", _nid)
                    .not_.is_("sound_id", None)
                    .gte("indexed_at", since_iso)
                    .execute()
                ).data or []

            rows = await loop.run_in_executor(None, _fetch_corpus)
            if not rows:
                continue

            agg: dict[str, dict[str, Any]] = {}
            for row in rows:
                sid = row.get("sound_id")
                if not sid:
                    continue
                if sid not in agg:
                    agg[sid] = {
                        "sound_id": sid,
                        "sound_name": row.get("sound_name") or sid,
                        "is_original_sound": bool(row.get("is_original_sound")),
                        "usage_count": 0,
                        "total_views": 0,
                    }
                agg[sid]["usage_count"] += 1
                agg[sid]["total_views"] += int(row.get("views") or 0)

            top = sorted(
                [v for v in agg.values() if not v["is_original_sound"]],
                key=lambda x: x["usage_count"],
                reverse=True,
            )[:10]

            if not top:
                continue

            upsert_rows = [
                {
                    "niche_id": niche_id,
                    "sound_id": s["sound_id"],
                    "sound_name": s["sound_name"],
                    "usage_count": s["usage_count"],
                    "is_original_sound": s["is_original_sound"],
                    "total_views": s["total_views"],
                    "commerce_signal": False,
                    "week_of": week_of_str,
                }
                for s in top
            ]

            def _upsert() -> None:
                client.table("trending_sounds").upsert(
                    upsert_rows,
                    on_conflict="niche_id,sound_id,week_of",
                ).execute()

            await loop.run_in_executor(None, _upsert)
            total_upserted += len(upsert_rows)
        except Exception as exc:
            logger.warning("sound_aggregation niche=%s error: %s", niche_id, exc)

    logger.info("sound_aggregation done: %d rows upserted", total_upserted)
    return {"upserted": total_upserted}
