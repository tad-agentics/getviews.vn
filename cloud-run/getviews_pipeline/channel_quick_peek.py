"""F5 — lightweight channel peek for Trends cards (W5-4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from getviews_pipeline.channel_diagnose import normalize_handle
from getviews_pipeline.channel_findings import build_channel_findings, pick_channel_quick_peek
from getviews_pipeline.supabase_client import get_service_client


def _parse_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def channel_quick_peek_for_handle(handle: str) -> dict[str, str | None]:
    """Corpus-only P0 teaser — no credits, no SSE."""
    h = normalize_handle(handle)
    if not h:
        return {"finding_id": None, "teaser": None}

    sb = get_service_client()
    res = (
        sb.table("video_corpus")
        .select("views,likes,comments,content_format,posted_at")
        .eq("creator_handle", h)
        .order("posted_at", desc=True)
        .limit(40)
        .execute()
    )
    videos: list[dict[str, Any]] = []
    for row in res.data or []:
        videos.append(
            {
                "views": row.get("views"),
                "likes": row.get("likes"),
                "comments": row.get("comments"),
                "content_format": row.get("content_format"),
                "posted_at": _parse_ts(row.get("posted_at")),
            }
        )

    if len(videos) < 3:
        return {"finding_id": None, "teaser": None}

    findings = build_channel_findings(
        videos=videos,
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
    )
    peek = pick_channel_quick_peek(findings)
    if peek:
        return {"finding_id": peek["finding_id"], "teaser": peek["teaser"]}
    return {"finding_id": None, "teaser": None}
