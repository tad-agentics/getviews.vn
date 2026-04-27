"""Wave 2.5 Phase A PR #4 — dual-write helper for the ``video_shots`` table.

The per-shot reference-video matcher (Phase B PR #5) queries ``video_shots``
directly rather than scanning ``video_corpus.analysis_json.scenes[]``, because
a JSONB scan across 10K+ rows can't meet the sub-millisecond budget inside
``/script/generate``. This module is the seam that keeps ``video_shots`` in
sync with the authoritative ``analysis_json.scenes[]`` data on every corpus
ingest.

Design:

* ``build_video_shot_rows`` is a pure function — it maps one ``video_corpus``
  row + an optional ``{scene_index: frame_url}`` dict into the ``video_shots``
  row dicts. No IO. Easy to unit-test and reuse from the backfill path.

* ``upsert_video_shots_sync`` is the tiny DB-facing wrapper, symmetric to
  ``_upsert_rows_sync`` in ``corpus_ingest.py``.

Denormalized columns (``niche_id``, ``hook_type``, ``creator_handle``,
``thumbnail_url``, ``tiktok_url``) are copied from the corpus row at write
time so the matcher never needs a join — see the migration comment in
``supabase/migrations/20260510000003_video_shots_table.sql`` for rationale.

Scenes with invalid bounds (``end <= start``, missing start/end, or negative
values) are silently dropped; the legacy ingest can produce these when Gemini
emits a degenerate scene array, and the ``video_shots_start_end_valid`` CHECK
constraint would fail the whole batch if we forwarded them.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _coerce_optional_str(v: Any) -> str | None:
    """Treat empty strings as None — matches the writer-side coercion
    documented in test_description_empty_string_treated_as_none_on_our_side."""
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def build_video_shot_rows(
    corpus_row: dict[str, Any],
    scene_frame_urls: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """Project a ``video_corpus`` row + per-scene frame URLs into
    ``video_shots`` row dicts ready for upsert.

    ``corpus_row`` is the dict produced by ``corpus_ingest._build_corpus_row``
    (or a row fetched from ``video_corpus`` during backfill). Only
    ``analysis_json``, ``video_id``, ``niche_id``, plus the denormalized
    columns, are read — other keys are ignored.

    ``scene_frame_urls`` maps ``scene_index`` → R2 public URL; scenes without
    an entry get ``frame_url=None`` (matches the migration comment: "NULL
    when not yet extracted").

    Returns ``[]`` when there are no valid scenes — no exceptions for
    degenerate input.
    """
    video_id = corpus_row.get("video_id")
    niche_id = corpus_row.get("niche_id")
    if not video_id or niche_id is None:
        return []

    analysis_json = corpus_row.get("analysis_json") or {}
    scenes = analysis_json.get("scenes") or []
    if not scenes:
        return []

    hook_type = corpus_row.get("hook_type")
    creator_handle = corpus_row.get("creator_handle")
    thumbnail_url = corpus_row.get("thumbnail_url")
    tiktok_url = corpus_row.get("tiktok_url")
    # Denormalized for the RefClipCard "X view" credibility chip.
    # ``views`` may be missing on older corpus rows — keep it None
    # rather than coercing to 0 so the FE branches on "unknown" cleanly.
    views_raw = corpus_row.get("views")
    try:
        views = int(views_raw) if views_raw is not None else None
    except (TypeError, ValueError):
        views = None

    frame_urls = scene_frame_urls or {}

    rows: list[dict[str, Any]] = []
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        start = scene.get("start")
        end = scene.get("end")
        try:
            start_f = float(start) if start is not None else None
            end_f = float(end) if end is not None else None
        except (TypeError, ValueError):
            continue
        # Drop degenerate scenes so we don't trip the CHECK constraint
        # (start_s <= end_s) and don't pollute the matcher with empty spans.
        if start_f is None or end_f is None or end_f <= start_f:
            continue

        rows.append({
            "video_id": str(video_id),
            "niche_id": int(niche_id),
            "scene_index": i,
            "start_s": start_f,
            "end_s": end_f,
            "scene_type": _coerce_optional_str(scene.get("type")),
            "framing": _coerce_optional_str(scene.get("framing")),
            "pace": _coerce_optional_str(scene.get("pace")),
            "overlay_style": _coerce_optional_str(scene.get("overlay_style")),
            "subject": _coerce_optional_str(scene.get("subject")),
            "motion": _coerce_optional_str(scene.get("motion")),
            "description": _coerce_optional_str(scene.get("description")),
            "hook_type": _coerce_optional_str(hook_type),
            "creator_handle": _coerce_optional_str(creator_handle),
            "thumbnail_url": _coerce_optional_str(thumbnail_url),
            "tiktok_url": _coerce_optional_str(tiktok_url),
            "frame_url": frame_urls.get(i),
            "views": views,
        })

    return rows


def upsert_video_shots_sync(
    client: Any,
    shot_rows: list[dict[str, Any]],
) -> None:
    """Upsert shot rows on (video_id, scene_index). No-op on empty input."""
    if not shot_rows:
        return
    client.table("video_shots").upsert(
        shot_rows, on_conflict="video_id,scene_index",
    ).execute()
