"""Wave 2.5 Phase A PR #4 — video_shots dual-write helper tests.

Exercises ``build_video_shot_rows`` (pure) and ``upsert_video_shots_sync``
(thin DB wrapper). No real Supabase, no real Gemini — the writer is
deterministic over a corpus_row shape we construct in-memory.

Pins:

* scene_index tracks list position, not anything Gemini emits
* Invalid-bounds scenes are silently dropped (matches CHECK constraint
  ``video_shots_start_end_valid``)
* Denormalized columns copy from corpus_row (hook_type / creator_handle /
  thumbnail_url / tiktok_url)
* frame_url picks up the dict entry by scene_index; missing entries → None
* Empty description coerces to None (writer side; see
  test_scene_enrichment.test_description_empty_string_treated_as_none_on_our_side)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from getviews_pipeline.video_shots_writer import (
    build_video_shot_rows,
    upsert_video_shots_sync,
)


def _corpus_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "video_id": "vid-1",
        "niche_id": 7,
        "hook_type": "question",
        "creator_handle": "@creator",
        "thumbnail_url": "https://cdn/thumb.jpg",
        "tiktok_url": "https://tiktok.com/@creator/video/vid-1",
        "analysis_json": {
            "scenes": [
                {
                    "type": "face_to_camera",
                    "start": 0.0, "end": 2.0,
                    "framing": "close_up", "pace": "slow",
                    "overlay_style": "bold_center", "subject": "face",
                    "motion": "static",
                    "description": "Cận mặt creator nói hook.",
                },
                {
                    "type": "product_shot",
                    "start": 2.0, "end": 5.5,
                    "framing": "medium", "pace": "medium",
                },
            ],
        },
    }
    base.update(overrides)
    return base


# ── Happy path — all fields project correctly ────────────────────────

def test_build_projects_all_enrichment_fields() -> None:
    row = _corpus_row()
    shots = build_video_shot_rows(row)
    assert len(shots) == 2
    s0 = shots[0]
    assert s0["video_id"] == "vid-1"
    assert s0["niche_id"] == 7
    assert s0["scene_index"] == 0
    assert s0["start_s"] == 0.0
    assert s0["end_s"] == 2.0
    assert s0["scene_type"] == "face_to_camera"
    assert s0["framing"] == "close_up"
    assert s0["pace"] == "slow"
    assert s0["overlay_style"] == "bold_center"
    assert s0["subject"] == "face"
    assert s0["motion"] == "static"
    assert s0["description"].startswith("Cận mặt")
    # Denormalized from corpus row
    assert s0["hook_type"] == "question"
    assert s0["creator_handle"] == "@creator"
    assert s0["thumbnail_url"] == "https://cdn/thumb.jpg"
    assert s0["tiktok_url"].endswith("/vid-1")
    # frame_url defaults to None when no mapping passed
    assert s0["frame_url"] is None


def test_build_scene_index_tracks_list_position() -> None:
    row = _corpus_row()
    shots = build_video_shot_rows(row)
    assert [s["scene_index"] for s in shots] == [0, 1]


# ── frame_url mapping ────────────────────────────────────────────────

def test_build_populates_frame_url_from_mapping() -> None:
    row = _corpus_row()
    shots = build_video_shot_rows(
        row, {0: "https://cdn/video_shots/vid-1/0.jpg"},
    )
    assert shots[0]["frame_url"] == "https://cdn/video_shots/vid-1/0.jpg"
    # Scene 1 has no mapping — stays None
    assert shots[1]["frame_url"] is None


def test_build_frame_url_mapping_is_optional() -> None:
    """Backfill path calls with no frame URLs at all."""
    row = _corpus_row()
    shots = build_video_shot_rows(row)
    assert all(s["frame_url"] is None for s in shots)


def test_build_frame_url_mapping_can_be_empty_dict() -> None:
    row = _corpus_row()
    shots = build_video_shot_rows(row, {})
    assert all(s["frame_url"] is None for s in shots)


# ── Invalid-bounds scenes dropped ────────────────────────────────────

def test_build_drops_scene_with_end_lte_start() -> None:
    row = _corpus_row(analysis_json={
        "scenes": [
            {"type": "face_to_camera", "start": 0.0, "end": 2.0},
            {"type": "broll", "start": 3.0, "end": 2.0},     # inverted
            {"type": "broll", "start": 5.0, "end": 5.0},     # zero-length
            {"type": "demo", "start": 6.0, "end": 9.0},
        ],
    })
    shots = build_video_shot_rows(row)
    assert [s["scene_index"] for s in shots] == [0, 3]


def test_build_drops_scene_with_missing_bounds() -> None:
    row = _corpus_row(analysis_json={
        "scenes": [
            {"type": "face_to_camera", "start": 0.0, "end": 2.0},
            {"type": "broll"},                               # no start/end
            {"type": "broll", "start": None, "end": 5.0},    # null start
        ],
    })
    shots = build_video_shot_rows(row)
    assert [s["scene_index"] for s in shots] == [0]


def test_build_drops_scene_with_non_numeric_bounds() -> None:
    row = _corpus_row(analysis_json={
        "scenes": [
            {"type": "face_to_camera", "start": "bad", "end": 2.0},
            {"type": "broll", "start": 0.0, "end": 2.0},
        ],
    })
    shots = build_video_shot_rows(row)
    assert len(shots) == 1
    assert shots[0]["scene_index"] == 1


# ── Empty-input degeneracy ───────────────────────────────────────────

def test_build_returns_empty_when_scenes_missing() -> None:
    row = _corpus_row(analysis_json={})
    assert build_video_shot_rows(row) == []


def test_build_returns_empty_when_analysis_json_missing() -> None:
    row = _corpus_row()
    row.pop("analysis_json", None)
    assert build_video_shot_rows(row) == []


def test_build_returns_empty_when_video_id_missing() -> None:
    row = _corpus_row(video_id=None)
    assert build_video_shot_rows(row) == []


def test_build_returns_empty_when_niche_id_missing() -> None:
    row = _corpus_row(niche_id=None)
    assert build_video_shot_rows(row) == []


def test_build_skips_non_dict_scene_entries() -> None:
    row = _corpus_row(analysis_json={
        "scenes": [
            "not-a-dict",
            {"type": "face_to_camera", "start": 0.0, "end": 2.0},
        ],
    })
    shots = build_video_shot_rows(row)
    assert [s["scene_index"] for s in shots] == [1]


# ── Empty-string coercion (per scene enrichment test agreement) ──────

def test_build_coerces_empty_description_to_none() -> None:
    row = _corpus_row(analysis_json={
        "scenes": [
            {"type": "face_to_camera", "start": 0.0, "end": 2.0, "description": ""},
        ],
    })
    shots = build_video_shot_rows(row)
    assert shots[0]["description"] is None


def test_build_coerces_whitespace_description_to_none() -> None:
    row = _corpus_row(analysis_json={
        "scenes": [
            {"type": "face_to_camera", "start": 0.0, "end": 2.0, "description": "   "},
        ],
    })
    shots = build_video_shot_rows(row)
    assert shots[0]["description"] is None


def test_build_preserves_nonempty_description() -> None:
    row = _corpus_row(analysis_json={
        "scenes": [
            {
                "type": "face_to_camera", "start": 0.0, "end": 2.0,
                "description": "Cận mặt creator.",
            },
        ],
    })
    shots = build_video_shot_rows(row)
    assert shots[0]["description"] == "Cận mặt creator."


# ── Denormalized columns ─────────────────────────────────────────────

def test_build_passes_through_null_denormalized_columns() -> None:
    """Some corpus rows (older ingests) may lack thumbnail_url or
    creator_handle. Null→None, never fabricated."""
    row = _corpus_row(
        thumbnail_url=None,
        creator_handle="",  # empty string normalizes to None
        hook_type=None,
    )
    shots = build_video_shot_rows(row)
    assert shots[0]["thumbnail_url"] is None
    assert shots[0]["creator_handle"] is None
    assert shots[0]["hook_type"] is None
    # tiktok_url still populated from base fixture
    assert shots[0]["tiktok_url"]


# ── Partial enrichment — back-compat with PR #2 Optional fields ──────

def test_build_accepts_scene_with_partial_enrichment() -> None:
    """Legacy scenes (pre-2026-05-10) have only type/start/end. The
    writer should still emit a row, with the 6 new dimensions as None."""
    row = _corpus_row(analysis_json={
        "scenes": [{"type": "face_to_camera", "start": 0.0, "end": 2.0}],
    })
    shots = build_video_shot_rows(row)
    assert len(shots) == 1
    s = shots[0]
    assert s["framing"] is None
    assert s["pace"] is None
    assert s["overlay_style"] is None
    assert s["subject"] is None
    assert s["motion"] is None
    assert s["description"] is None


# ── views passthrough (denormalized from video_corpus) ───────────────

def test_build_passes_views_through_when_present() -> None:
    """Views from corpus row are denormalized so the FE RefClipCard can
    render the "256K view" credibility chip without a join."""
    row = _corpus_row(views=156_000)
    shots = build_video_shot_rows(row)
    assert all(s["views"] == 156_000 for s in shots)


def test_build_views_none_when_missing_from_corpus_row() -> None:
    """Pre-backfill corpus rows have no views key — writer should emit
    None rather than crash or coerce to 0."""
    row = _corpus_row()  # no views in fixture
    shots = build_video_shot_rows(row)
    assert all(s["views"] is None for s in shots)


def test_build_views_none_when_unparseable() -> None:
    """Garbage views value (non-numeric string from a bad ingest) must
    fall through to None instead of raising."""
    row = _corpus_row(views="not-a-number")
    shots = build_video_shot_rows(row)
    assert all(s["views"] is None for s in shots)


def test_build_views_zero_preserved() -> None:
    """Zero views is meaningful (just-published) — not coerced to None."""
    row = _corpus_row(views=0)
    shots = build_video_shot_rows(row)
    assert all(s["views"] == 0 for s in shots)


# ── upsert_video_shots_sync — thin DB wrapper ────────────────────────

def test_upsert_calls_table_with_correct_on_conflict() -> None:
    client = MagicMock()
    rows = [{"video_id": "v1", "scene_index": 0, "niche_id": 7}]
    upsert_video_shots_sync(client, rows)
    client.table.assert_called_once_with("video_shots")
    upsert_call = client.table.return_value.upsert
    upsert_call.assert_called_once_with(
        rows, on_conflict="video_id,scene_index",
    )
    upsert_call.return_value.execute.assert_called_once()


def test_upsert_is_noop_on_empty_input() -> None:
    client = MagicMock()
    upsert_video_shots_sync(client, [])
    client.table.assert_not_called()
