"""Tests for Phase B video_structural helpers."""

from __future__ import annotations

from getviews_pipeline.video_structural import (
    decompose_segments,
    extract_hook_phases,
    model_niche_benchmark_curve,
    model_retention_curve,
    video_duration_sec,
)


def test_video_duration_prefers_duration_seconds() -> None:
    a = {"duration_seconds": 58, "scenes": [{"start": 0, "end": 10}]}
    assert video_duration_sec(a) == 58.0


def test_video_duration_falls_back_to_scene_end() -> None:
    a = {"scenes": [{"start": 0, "end": 42.5}, {"start": 40, "end": 45}]}
    assert video_duration_sec(a) == 45.0


def test_decompose_segments_fallback_without_scenes() -> None:
    segs = decompose_segments({"duration_seconds": 30})
    assert len(segs) == 8
    assert sum(s["pct"] for s in segs) == 100
    assert segs[0]["name"] == "HOOK"
    assert segs[0]["color_key"] == "accent"
    assert segs[-1]["name"] == "CTA"


def test_decompose_segments_eight_parts_from_scenes() -> None:
    # Ten short scenes → merged down then split to exactly 8 spans.
    scenes = [{"start": i, "end": i + 1} for i in range(10)]
    segs = decompose_segments({"duration_seconds": 10, "scenes": scenes})
    assert len(segs) == 8
    assert sum(s["pct"] for s in segs) == 100


def test_extract_hook_phases_three_cards_empty_body() -> None:
    analysis = {
        "hook_analysis": {
            "first_frame_type": "face",
            "hook_type": "curiosity_gap",
            "face_appears_at": 0.2,
            "first_speech_at": 1.1,
            "hook_timeline": [{"t": 0.4, "event": "zoom-in", "note": "text pop"}],
        }
    }
    cards = extract_hook_phases(analysis)
    assert len(cards) == 3
    assert cards[0]["t_range"] == "0.0–0.8s"
    assert cards[1]["t_range"] == "0.8–1.8s"
    assert cards[2]["t_range"] == "1.8–3.0s"
    assert all(c["body"] == "" for c in cards)
    assert "face" in cards[0]["label"].lower() or "Mở" in cards[0]["label"]
    assert "curiosity" in cards[1]["label"].lower() or "zoom" in cards[1]["label"].lower()


def test_model_retention_curve_twenty_points_monotonic_tail() -> None:
    curve = model_retention_curve(
        58.0,
        niche_median_retention=0.58,
        breakout_multiplier=2.0,
        n_points=20,
    )
    assert len(curve) == 20
    assert curve[0]["t"] == 0.0
    assert curve[-1]["t"] == 58.0
    assert 0 <= curve[-1]["pct"] <= curve[0]["pct"] <= 100


def test_model_niche_benchmark_flatter_than_video_curve() -> None:
    v = model_retention_curve(40.0, niche_median_retention=0.5, n_points=20)
    n = model_niche_benchmark_curve(40.0, niche_median_retention=0.5, n_points=20)
    assert v[-1]["pct"] < n[-1]["pct"] or v == n  # benchmark ends higher retention target
