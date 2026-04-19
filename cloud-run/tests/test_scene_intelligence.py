"""B.4.1 — scene_intelligence aggregation (no Supabase)."""

from __future__ import annotations

from getviews_pipeline.scene_intelligence_refresh import (
    aggregate_scene_intelligence,
    events_from_video_row,
)


def test_events_from_video_row_parses_scenes_and_overlays() -> None:
    row = {
        "video_id": "abc",
        "niche_id": 3,
        "views": 5000,
        "analysis_json": {
            "scenes": [
                {"type": "face", "start": 0.0, "end": 2.0},
                {"type": "product_shot", "start": 2.0, "end": 5.0},
            ],
            "text_overlays": [{"text": "  SALE  ", "appears_at": 1.0}],
        },
    }
    evs = events_from_video_row(row)
    assert len(evs) == 2
    assert evs[0]["scene_type"] == "face_to_camera"
    assert evs[0]["duration"] == 2.0
    assert evs[0]["overlay_texts"] == ["SALE"]
    assert evs[1]["scene_type"] == "product_shot"
    assert evs[1]["overlay_texts"] == []


def test_aggregate_skips_when_under_min_videos() -> None:
    events = [
        {
            "niche_id": 1,
            "scene_type": "action",
            "video_id": f"v{i}",
            "views": 100,
            "duration": 1.0,
            "overlay_texts": [],
        }
        for i in range(29)
    ]
    assert aggregate_scene_intelligence(events, min_videos=30) == []


def test_aggregate_emits_row_when_threshold_met() -> None:
    events = []
    for i in range(40):
        events.append(
            {
                "niche_id": 2,
                "scene_type": "face_to_camera",
                "video_id": f"v{i}",
                "views": 1000 + i * 50,
                "duration": 2.0,
                "overlay_texts": ["hi"] if i >= 30 else [],
            }
        )
    rows = aggregate_scene_intelligence(events, min_videos=30)
    assert len(rows) == 1
    r = rows[0]
    assert r["niche_id"] == 2
    assert r["scene_type"] == "face_to_camera"
    assert r["sample_size"] == 40
    assert r["corpus_avg_duration"] == 2.0
    assert len(r["reference_video_ids"]) == 3
    assert r["winner_overlay_style"] == "TEXT_TITLE"


def test_overlay_samples_capped_at_five_across_winner_events() -> None:
    """Inner ``break`` only exits the text loop; outer must stop once ``samples`` reaches 5."""
    events = []
    for i in range(40):
        overlays: list[str] = []
        if i == 30:
            overlays = ["a", "b", "c"]
        elif i == 31:
            overlays = ["d", "e", "f"]
        elif i >= 32:
            overlays = ["should-not-appear"]
        events.append(
            {
                "niche_id": 2,
                "scene_type": "demo_cap",
                "video_id": f"v{i}",
                "views": 1000 + i * 50,
                "duration": 2.0,
                "overlay_texts": overlays,
            }
        )
    rows = aggregate_scene_intelligence(events, min_videos=30)
    assert len(rows) == 1
    assert len(rows[0]["overlay_samples"]) == 5
    assert "should-not-appear" not in rows[0]["overlay_samples"]
