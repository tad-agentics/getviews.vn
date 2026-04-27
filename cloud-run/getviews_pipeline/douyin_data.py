"""D4a (2026-06-04) — Kho Douyin · read models for ``GET /douyin/feed``.

Single feed endpoint that returns BOTH the active niche taxonomy AND
the corpus videos in one round-trip. Why one call instead of two:

  • Mobile / slow networks — one HTTP round-trip beats two for the
    initial paint.
  • Filter chips render from ``niches`` while videos load — but
    rendering one without the other is awkward UX (chip strip with no
    counts, or cards with no chip filter). Loading them together
    matches what the FE actually needs to render the first frame.
  • Backend cost is the same — two SELECTs either way; combining at
    the API layer saves one HTTP overhead.

Active filtering is server-side (ingest cap is small enough that
returning all rows is fine):
  • Drops corpus rows whose niche is ``active=FALSE`` in the taxonomy
    (a paused niche shouldn't surface in the chip strip OR the grid).
  • No pagination — D2 cap is ~50 videos/day × ~30-day retention =
    ~1.5K rows max. Easy enough to ship over the wire as JSON.

Future endpoint shapes (not in D4a):
  • ``GET /douyin/videos/:id`` — single-row drill-down for the modal.
    D4d uses the cached row from the feed instead, but a dedicated
    endpoint would let us paginate beyond the in-memory cache later.
  • ``POST /douyin/saved`` — server-persisted saved set (D4 ships
    localStorage-only; cloud-sync is an explicit follow-up).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def fetch_douyin_feed(sb: Any) -> dict[str, Any]:
    """Build the ``/douyin/feed`` response payload.

    Returns:
        ``{"niches": [...], "videos": [...]}``. Both lists are ordered:
        niches by ``id`` (matches the chip-strip ordering); videos by
        ``views DESC`` (the FE re-sorts client-side per the user's
        sort dropdown, but a sensible default keeps the first paint
        meaningful).
    """
    # ── 1) Active niche taxonomy ────────────────────────────────
    niches: list[dict[str, Any]] = []
    active_niche_ids: set[int] = set()
    try:
        n_res = (
            sb.table("douyin_niche_taxonomy")
            .select("id, slug, name_vn, name_zh, name_en")
            .eq("active", True)
            .order("id")
            .execute()
        )
        for row in n_res.data or []:
            if row.get("id") is None:
                continue
            niches.append({
                "id": int(row["id"]),
                "slug": str(row.get("slug") or ""),
                "name_vn": str(row.get("name_vn") or ""),
                "name_zh": str(row.get("name_zh") or ""),
                "name_en": str(row.get("name_en") or ""),
            })
            active_niche_ids.add(int(row["id"]))
    except Exception as exc:
        logger.exception("[douyin/feed] niche fetch failed: %s", exc)
        # Surfaces as an empty-niches FE state — the chip strip + grid
        # both render an empty state rather than crash.
        return {"niches": [], "videos": []}

    if not active_niche_ids:
        return {"niches": niches, "videos": []}

    # ── 2) Corpus videos for those niches ───────────────────────
    videos: list[dict[str, Any]] = []
    try:
        v_res = (
            sb.table("douyin_video_corpus")
            .select(
                "video_id, douyin_url, niche_id, "
                "creator_handle, creator_name, "
                "thumbnail_url, video_url, video_duration, "
                "views, likes, saves, engagement_rate, posted_at, "
                "title_zh, title_vi, sub_vi, hashtags_zh, "
                "adapt_level, adapt_reason, eta_weeks_min, eta_weeks_max, "
                "cn_rise_pct, translator_notes, synth_computed_at, "
                "indexed_at"
            )
            .in_("niche_id", sorted(active_niche_ids))
            .order("views", desc=True)
            .execute()
        )
        for row in v_res.data or []:
            if not row.get("video_id"):
                continue
            videos.append(_serialize_video(row))
    except Exception as exc:
        logger.exception("[douyin/feed] video fetch failed: %s", exc)
        # Fall through to empty videos rather than crashing the whole
        # response — the niche chip strip can still render.
        return {"niches": niches, "videos": []}

    return {"niches": niches, "videos": videos}


def _serialize_video(row: dict[str, Any]) -> dict[str, Any]:
    """Project a Supabase row into the FE-facing shape.

    Keeps the BE column names but coerces NULLs to safe defaults the FE
    can branch on without optional-chaining everything.
    """

    def _int_or_none(v: Any) -> int | None:
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    def _float_or_none(v: Any) -> float | None:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    # translator_notes is JSONB on the DB; supabase-py returns the
    # parsed list/None directly. Defend against unexpected shapes.
    # D6e (audit L4) — strip the note text before truthiness so a
    # whitespace-only note (reachable only via direct DB tampering;
    # Pydantic synth enforces min_length=12) doesn't render an empty
    # card on the FE modal.
    raw_notes = row.get("translator_notes")
    notes: list[dict[str, str]] = []
    if isinstance(raw_notes, list):
        for n in raw_notes:
            if not isinstance(n, dict):
                continue
            tag = (n.get("tag") or "").strip() if isinstance(n.get("tag"), str) else ""
            note = (n.get("note") or "").strip() if isinstance(n.get("note"), str) else ""
            if tag and note:
                notes.append({"tag": tag, "note": note})

    # hashtags_zh: TEXT[] on DB; supabase-py returns a list.
    raw_hashtags = row.get("hashtags_zh")
    hashtags: list[str] = []
    if isinstance(raw_hashtags, list):
        for h in raw_hashtags:
            if isinstance(h, str) and h.strip():
                hashtags.append(h.strip())

    return {
        "video_id": str(row["video_id"]),
        "douyin_url": row.get("douyin_url"),
        "niche_id": _int_or_none(row.get("niche_id")),
        "creator_handle": row.get("creator_handle"),
        "creator_name": row.get("creator_name"),
        "thumbnail_url": row.get("thumbnail_url"),
        "video_url": row.get("video_url"),
        "video_duration": _float_or_none(row.get("video_duration")),
        "views": _int_or_none(row.get("views")) or 0,
        "likes": _int_or_none(row.get("likes")) or 0,
        "saves": _int_or_none(row.get("saves")) or 0,
        "engagement_rate": _float_or_none(row.get("engagement_rate")),
        "posted_at": row.get("posted_at"),
        # Captions (CN raw + VN translation + short gloss).
        "title_zh": row.get("title_zh"),
        "title_vi": row.get("title_vi"),
        "sub_vi": row.get("sub_vi"),
        "hashtags_zh": hashtags,
        # D3b synth fields — may be NULL on freshly-ingested rows that
        # the synth cron hasn't yet covered. FE renders the "human
        # review pending" caveat below the chip when null.
        "adapt_level": row.get("adapt_level"),  # green | yellow | red | None
        "adapt_reason": row.get("adapt_reason"),
        "eta_weeks_min": _int_or_none(row.get("eta_weeks_min")),
        "eta_weeks_max": _int_or_none(row.get("eta_weeks_max")),
        "cn_rise_pct": _float_or_none(row.get("cn_rise_pct")),
        "translator_notes": notes,
        "synth_computed_at": row.get("synth_computed_at"),
        # Bookkeeping for the FE "X ngày trước" relative time chip.
        "indexed_at": row.get("indexed_at"),
    }
