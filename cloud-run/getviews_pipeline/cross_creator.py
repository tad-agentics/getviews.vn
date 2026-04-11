"""P2-11: Cross-creator pattern detection from video_corpus (weekly batch)."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_LOOKBACK = "7"


def _lookback_days() -> int:
    raw = os.environ.get("CROSS_CREATOR_LOOKBACK_DAYS", _DEFAULT_LOOKBACK).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return int(_DEFAULT_LOOKBACK)


def _insert_chunk_size() -> int:
    raw = os.environ.get("CROSS_CREATOR_INSERT_CHUNK", "500").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 500


@dataclass
class CrossCreatorResult:
    patterns_written: int = 0
    niches_affected: int = 0
    errors: list[str] = field(default_factory=list)


def _week_start_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _sync_delete_week(client: Any, week_of_iso: str) -> None:
    client.table("cross_creator_patterns").delete().eq("week_of", week_of_iso).execute()


def _sync_rpc_aggregate(client: Any, lookback_days: int) -> list[dict[str, Any]]:
    res = client.rpc(
        "cross_creator_pattern_aggregate",
        {"p_lookback_days": lookback_days},
    ).execute()
    raw = res.data
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def _sync_insert_chunk(client: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    client.table("cross_creator_patterns").insert(rows).execute()


async def run_cross_creator_detection(client: Any | None = None) -> CrossCreatorResult:
    """Aggregate hook patterns used by 3+ distinct creators in the lookback window; store per ISO week."""
    result = CrossCreatorResult()
    loop = asyncio.get_event_loop()

    try:
        if client is None:
            try:
                from getviews_pipeline.supabase_client import get_service_client

                client = get_service_client()
            except Exception as exc:
                result.errors.append(str(exc))
                return result

        today = date.today()
        week_of = _week_start_monday(today)
        week_iso = week_of.isoformat()

        try:
            await loop.run_in_executor(None, _sync_delete_week, client, week_iso)
        except Exception as exc:
            result.errors.append(f"xóa tuần: {exc}")
            return result

        try:
            lookback = _lookback_days()
            rows_raw = await loop.run_in_executor(
                None,
                _sync_rpc_aggregate,
                client,
                lookback,
            )
        except Exception as exc:
            result.errors.append(f"aggregate: {exc}")
            return result

        computed_at = datetime.now(timezone.utc).isoformat()
        payloads: list[dict[str, Any]] = []
        niche_ids: set[int] = set()

        for row in rows_raw:
            try:
                nid = int(row["niche_id"])
                hook = str(row["hook_type"])
                cc = int(row["creator_count"])
                tv = int(row["total_views"])
                creators = row.get("creators")
                if not isinstance(creators, list):
                    creators = list(creators) if creators else []
                creators = [str(c) for c in creators if c is not None]
                niche_ids.add(nid)
                payloads.append(
                    {
                        "niche_id": nid,
                        "hook_type": hook,
                        "creator_count": cc,
                        "total_views": tv,
                        "creators": creators,
                        "week_of": week_iso,
                        "computed_at": computed_at,
                    }
                )
            except (KeyError, TypeError, ValueError) as exc:
                result.errors.append(f"row parse: {exc}")

        chunk_sz = _insert_chunk_size()
        for i in range(0, len(payloads), chunk_sz):
            chunk = payloads[i : i + chunk_sz]
            try:
                await loop.run_in_executor(None, _sync_insert_chunk, client, chunk)
                result.patterns_written += len(chunk)
            except Exception as exc:
                result.errors.append(f"insert chunk {i}: {exc}")

        result.niches_affected = len(niche_ids)
        return result
    except Exception as exc:
        result.errors.append(f"cross_creator: {exc}")
        return result
