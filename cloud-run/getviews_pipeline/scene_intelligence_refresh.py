"""B.4.1 — Refresh ``scene_intelligence`` from ``video_corpus.analysis_json``.

Run nightly (or on-demand) with service_role::

    python -m getviews_pipeline.scene_intelligence_refresh
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 90
MIN_VIDEOS_PER_SCENE_TYPE = 30
WINNER_FRAC = 0.25
# ``analysis_json`` is a multi-kB blob per row (scenes + overlays). A full
# page of 500 used to trip Supabase's HTTP/2 stream reset on large responses.
# 100 keeps each page comfortably under the transport ceiling.
PAGE_SIZE = 100
_FETCH_RETRIES = 4
_FETCH_BACKOFF_S = (2, 4, 8, 16)


def _is_transient_transport_error(exc: BaseException) -> bool:
    """True when ``exc`` is an httpx/h2/gateway transport blip worth retrying."""
    name = type(exc).__name__
    if name in {
        "StreamReset",
        "RemoteProtocolError",
        "ReadError",
        "ReadTimeout",
        "WriteError",
        "ConnectError",
        "ConnectTimeout",
        "PoolTimeout",
    }:
        return True
    # supabase-py wraps PostgREST errors in APIError; bad gateways (502/503/504)
    # are worth another shot too.
    msg = str(exc)
    if "StreamReset" in msg or "remote_reset" in msg:
        return True
    return False


def _norm_scene_type(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "other"
    t = raw.strip().lower().replace("-", "_")
    if t == "face":
        return "face_to_camera"
    return t


def events_from_video_row(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Flatten one ``video_corpus`` row into scene-level events for aggregation."""
    aj = row.get("analysis_json") or {}
    if not isinstance(aj, dict):
        return []
    scenes = aj.get("scenes") or []
    overlays = aj.get("text_overlays") or []
    if not isinstance(scenes, list):
        return []
    if not isinstance(overlays, list):
        overlays = []

    vid = str(row.get("video_id") or "")
    if not vid:
        return []
    try:
        nid = int(row["niche_id"])
    except (TypeError, ValueError, KeyError):
        return []
    views = int(row.get("views") or 0)

    out: list[dict[str, Any]] = []
    for s in scenes:
        if not isinstance(s, dict):
            continue
        try:
            start = float(s.get("start") or 0.0)
            end = float(s.get("end") or 0.0)
        except (TypeError, ValueError):
            continue
        dur = max(0.0, end - start)
        if dur <= 0:
            continue
        stype = _norm_scene_type(s.get("type"))
        otexts: list[str] = []
        for o in overlays:
            if not isinstance(o, dict):
                continue
            try:
                at = float(o.get("appears_at") or -1.0)
            except (TypeError, ValueError):
                continue
            if start <= at <= end:
                txt = str(o.get("text") or "").strip()
                if txt:
                    otexts.append(txt)
        out.append(
            {
                "niche_id": nid,
                "scene_type": stype,
                "video_id": vid,
                "views": views,
                "duration": dur,
                "overlay_texts": otexts,
            }
        )
    return out


def aggregate_scene_intelligence(
    events: Iterable[dict[str, Any]],
    *,
    min_videos: int = MIN_VIDEOS_PER_SCENE_TYPE,
    winner_frac: float = WINNER_FRAC,
) -> list[dict[str, Any]]:
    """Pure aggregation used by the refresh job and unit tests."""
    key_events: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for e in events:
        key = (int(e["niche_id"]), str(e["scene_type"]))
        key_events[key].append(e)

    now_iso = datetime.now(timezone.utc).isoformat()
    rows_out: list[dict[str, Any]] = []

    for (nid, stype), evs in key_events.items():
        vids = {str(e["video_id"]) for e in evs}
        if len(vids) < min_videos:
            continue

        corpus_avg = sum(float(e["duration"]) for e in evs) / len(evs)

        vid_views: dict[str, int] = {}
        for e in evs:
            v = str(e["video_id"])
            vv = int(e.get("views") or 0)
            vid_views[v] = max(vid_views.get(v, 0), vv)

        ranked = sorted(vid_views.items(), key=lambda x: x[1], reverse=True)
        k = max(10, int(len(ranked) * winner_frac))
        winner_set = {vid for vid, _ in ranked[:k]}

        w_durs = [float(e["duration"]) for e in evs if str(e["video_id"]) in winner_set]
        winner_avg = sum(w_durs) / len(w_durs) if w_durs else corpus_avg

        ref_ids = [vid for vid, _ in ranked[:3]]

        seen_txt: set[str] = set()
        samples: list[str] = []
        for e in evs:
            if str(e["video_id"]) not in winner_set:
                continue
            for t in e.get("overlay_texts") or []:
                if not isinstance(t, str) or not t.strip():
                    continue
                t = t.strip()[:200]
                if t in seen_txt:
                    continue
                seen_txt.add(t)
                samples.append(t)
                if len(samples) >= 5:
                    break
            if len(samples) >= 5:
                break

        style = "TEXT_TITLE" if samples else "NONE"
        tip = (
            f"Độ dài shot kiểu «{stype}» trong ngách: TB cả mẫu {corpus_avg:.1f}s; "
            f"video có lượt xem cao TB ~{winner_avg:.1f}s."
        )

        rows_out.append(
            {
                "niche_id": nid,
                "scene_type": stype,
                "corpus_avg_duration": round(corpus_avg, 2),
                "winner_avg_duration": round(winner_avg, 2),
                "winner_overlay_style": style,
                "overlay_samples": samples,
                "tip": tip,
                "reference_video_ids": ref_ids,
                "sample_size": len(vids),
                "computed_at": now_iso,
            }
        )

    rows_out.sort(key=lambda r: (r["niche_id"], r["scene_type"]))
    return rows_out


def _fetch_page_with_retry(client: Any, cutoff_iso: str, start: int) -> list[dict[str, Any]]:
    """One paginated select, retrying on transient transport errors.

    Returns the raw ``data`` list. Raises on non-transient or exhausted retries.
    """
    last_exc: BaseException | None = None
    for attempt in range(_FETCH_RETRIES):
        try:
            res = (
                client.table("video_corpus")
                .select("video_id, niche_id, views, analysis_json")
                .gte("indexed_at", cutoff_iso)
                .range(start, start + PAGE_SIZE - 1)
                .execute()
            )
            return res.data or []
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not _is_transient_transport_error(exc):
                raise
            if attempt == _FETCH_RETRIES - 1:
                break
            delay = _FETCH_BACKOFF_S[min(attempt, len(_FETCH_BACKOFF_S) - 1)]
            logger.warning(
                "[scene_intelligence] transient fetch error at offset=%d "
                "(attempt %d/%d), retrying in %ds: %s",
                start, attempt + 1, _FETCH_RETRIES, delay, exc,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def _fetch_all_events_sync(client: Any, cutoff_iso: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    start = 0
    pages = 0
    while True:
        chunk = _fetch_page_with_retry(client, cutoff_iso, start)
        for row in chunk:
            if not isinstance(row, dict):
                continue
            events.extend(events_from_video_row(row))
        pages += 1
        if pages % 20 == 0:
            logger.info(
                "[scene_intelligence] fetched %d pages (%d rows so far), events=%d",
                pages, start + len(chunk), len(events),
            )
        if len(chunk) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    logger.info(
        "[scene_intelligence] parsed %d scene events from corpus across %d pages",
        len(events), pages,
    )
    return events


def refresh_scene_intelligence_sync(client: Any) -> dict[str, Any]:
    """Recompute all rows (service_role). Deletes per niche before insert."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    events = _fetch_all_events_sync(client, cutoff)
    aggregated = aggregate_scene_intelligence(events)

    by_niche: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in aggregated:
        by_niche[int(r["niche_id"])].append(r)

    existing_res = client.table("scene_intelligence").select("niche_id").execute()
    existing_niches = {int(r["niche_id"]) for r in (existing_res.data or []) if r.get("niche_id") is not None}
    new_niches = set(by_niche.keys())

    for nid in existing_niches - new_niches:
        client.table("scene_intelligence").delete().eq("niche_id", nid).execute()

    inserted = 0
    for nid, rows_n in by_niche.items():
        client.table("scene_intelligence").delete().eq("niche_id", nid).execute()
        if rows_n:
            client.table("scene_intelligence").insert(rows_n).execute()
            inserted += len(rows_n)

    logger.info(
        "[scene_intelligence] refresh done niches=%d rows=%d",
        len(by_niche),
        inserted,
    )
    return {
        "niches_written": len(by_niche),
        "rows_upserted": inserted,
        "scene_events": len(events),
    }


def main() -> None:
    from getviews_pipeline.supabase_client import get_service_client

    logging.basicConfig(level=logging.INFO)
    stats = refresh_scene_intelligence_sync(get_service_client())
    print(stats)


if __name__ == "__main__":
    main()
