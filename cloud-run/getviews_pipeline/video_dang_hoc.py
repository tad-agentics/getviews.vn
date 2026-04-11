"""P2-12: Video Đáng Học — daily rankings from video_corpus (Cloud Run batch)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

LIST_BUNG_NO = "bung_no"
LIST_DANG_HOT = "dang_hot"


@dataclass
class VideoDangHocResult:
    bung_no_count: int = 0
    dang_hot_count: int = 0
    errors: list[str] = field(default_factory=list)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _fetch_bung_no_sync(client: Any) -> list[dict[str, Any]]:
    """High breakout: breakout_multiplier > 3, indexed in last 7 days, top 20 by views."""
    cutoff = (_now_utc() - timedelta(days=7)).isoformat()
    result = (
        client.table("video_corpus")
        .select("video_id, breakout_multiplier, views")
        .gt("breakout_multiplier", 3)
        .gt("indexed_at", cutoff)
        .order("views", desc=True)
        .limit(20)
        .execute()
    )
    return result.data or []


def _velocity_for_row(row: dict[str, Any], now: datetime) -> float:
    views = float(row.get("views") or 0)
    indexed_raw = row.get("indexed_at")
    if not indexed_raw:
        return 0.0
    if isinstance(indexed_raw, str):
        indexed = datetime.fromisoformat(indexed_raw.replace("Z", "+00:00"))
    else:
        indexed = indexed_raw
    if indexed.tzinfo is None:
        indexed = indexed.replace(tzinfo=timezone.utc)
    hours = max((now - indexed).total_seconds() / 3600.0, 1.0)
    return views / hours


def _fetch_dang_hot_sync(client: Any) -> list[dict[str, Any]]:
    """High velocity: views per hour since indexed, last 48h, top 20 by velocity."""
    cutoff = (_now_utc() - timedelta(hours=48)).isoformat()
    result = (
        client.table("video_corpus")
        .select("video_id, views, indexed_at")
        .gt("indexed_at", cutoff)
        .execute()
    )
    rows = result.data or []
    now = _now_utc()
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        v = _velocity_for_row(row, now)
        scored.append((v, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:20]
    out: list[dict[str, Any]] = []
    for vel, row in top:
        out.append({"video_id": row["video_id"], "velocity": vel})
    return out


def _delete_list_sync(client: Any, list_type: str) -> None:
    client.table("video_dang_hoc").delete().eq("list_type", list_type).execute()


def _insert_rows_sync(
    client: Any,
    list_type: str,
    items: list[dict[str, Any]],
    *,
    bung_no: bool,
) -> int:
    if not items:
        _delete_list_sync(client, list_type)
        return 0

    refreshed = _now_utc().isoformat()
    payload: list[dict[str, Any]] = []
    for rank, item in enumerate(items, start=1):
        vid = item["video_id"]
        row: dict[str, Any] = {
            "video_id": vid,
            "list_type": list_type,
            "rank": rank,
            "refreshed_at": refreshed,
        }
        if bung_no:
            row["breakout_multiplier"] = float(item.get("breakout_multiplier") or 0)
            row["velocity"] = None
        else:
            row["breakout_multiplier"] = None
            row["velocity"] = float(item.get("velocity") or 0)
        payload.append(row)

    _delete_list_sync(client, list_type)
    client.table("video_dang_hoc").insert(payload).execute()
    return len(payload)


def _run_bung_no_sync(client: Any) -> int:
    rows = _fetch_bung_no_sync(client)
    return _insert_rows_sync(client, LIST_BUNG_NO, rows, bung_no=True)


def _run_dang_hot_sync(client: Any) -> int:
    rows = _fetch_dang_hot_sync(client)
    return _insert_rows_sync(client, LIST_DANG_HOT, rows, bung_no=False)


async def run_video_dang_hoc(client: Any) -> VideoDangHocResult:
    """Refresh both lists: delete per list_type, insert ranked rows."""
    result = VideoDangHocResult()
    loop = asyncio.get_event_loop()

    try:
        result.bung_no_count = await loop.run_in_executor(
            None,
            lambda: _run_bung_no_sync(client),
        )
    except Exception as exc:
        msg = f"bung_no: {exc}"
        logger.error("[video_dang_hoc] %s", msg)
        result.errors.append(msg)

    try:
        result.dang_hot_count = await loop.run_in_executor(
            None,
            lambda: _run_dang_hot_sync(client),
        )
    except Exception as exc:
        msg = f"dang_hot: {exc}"
        logger.error("[video_dang_hoc] %s", msg)
        result.errors.append(msg)

    return result
