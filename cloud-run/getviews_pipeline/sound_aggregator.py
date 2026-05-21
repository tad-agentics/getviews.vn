"""Weekly batch: aggregate trending sounds from video_corpus into trending_sounds table."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _week_start_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


async def run_sound_aggregation(client: Any | None = None) -> dict[str, Any]:
    """Aggregate top non-original sounds per content class for current week."""
    from getviews_pipeline.layer0_sound import infer_sound_lifecycle_phase
    from getviews_pipeline.supabase_client import get_service_client

    if client is None:
        client = get_service_client()

    week_of = _week_start_monday(date.today())
    week_of_str = week_of.isoformat()
    prev_week_str = (week_of - timedelta(days=7)).isoformat()
    since_dt = datetime.now(UTC) - timedelta(days=7)
    since_iso = since_dt.isoformat()

    loop = asyncio.get_event_loop()

    def _class_ids() -> list[int]:
        res = (
            client.table("content_class_ingest_targets")
            .select("content_class_id")
            .eq("is_active", True)
            .execute()
        )
        return [
            int(r["content_class_id"])
            for r in (res.data or [])
            if r.get("content_class_id") is not None
        ]

    try:
        class_ids = await loop.run_in_executor(None, _class_ids)
    except Exception as exc:
        logger.error("[sound_aggregation] content_class_ingest_targets: %s", exc)
        return {"upserted": 0, "error": str(exc)}

    total_upserted = 0
    for content_class_id in class_ids:
        try:

            def _fetch_corpus(_cc: int = content_class_id) -> list[dict[str, Any]]:
                return (
                    client.table("video_corpus")
                    .select("sound_id,sound_name,is_original_sound,views")
                    .eq("content_class_id", _cc)
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

            sound_ids_top = [str(s["sound_id"]) for s in top]

            def _prev_counts_for_sids(_cc: int = content_class_id) -> dict[str, int]:
                if not sound_ids_top:
                    return {}
                try:
                    prev_res = (
                        client.table("trending_sounds")
                        .select("sound_id,usage_count")
                        .eq("content_class_id", _cc)
                        .eq("week_of", prev_week_str)
                        .in_("sound_id", sound_ids_top)
                        .execute()
                    )
                except Exception:
                    return {}
                out: dict[str, int] = {}
                for pr in prev_res.data or []:
                    sid = pr.get("sound_id")
                    if not sid:
                        continue
                    out[str(sid)] = int(pr.get("usage_count") or 0)
                return out

            prev_by_sound = await loop.run_in_executor(None, _prev_counts_for_sids)

            upsert_rows = []
            for s in top:
                sid = s["sound_id"]
                prev_u = int(prev_by_sound.get(str(sid), 0))
                curr_u = int(s["usage_count"])
                lifecycle = infer_sound_lifecycle_phase(prev_u, curr_u)
                cml_ok = True if not s["is_original_sound"] else None
                upsert_rows.append({
                    "content_class_id": content_class_id,
                    "sound_id": sid,
                    "sound_name": s["sound_name"],
                    "usage_count": curr_u,
                    "is_original_sound": s["is_original_sound"],
                    "total_views": s["total_views"],
                    "commerce_signal": False,
                    "week_of": week_of_str,
                    "lifecycle_phase": lifecycle,
                    "commercial_music_library_eligible": cml_ok,
                })

            def _upsert() -> None:
                client.table("trending_sounds").upsert(
                    upsert_rows,
                    on_conflict="content_class_id,sound_id,week_of",
                ).execute()

            await loop.run_in_executor(None, _upsert)
            total_upserted += len(upsert_rows)
        except Exception as exc:
            logger.warning(
                "sound_aggregation content_class=%s error: %s",
                content_class_id,
                exc,
            )

    logger.info("sound_aggregation done: %d rows upserted", total_upserted)
    return {"upserted": total_upserted}
