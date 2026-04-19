"""Tests for Phase B niche benchmark mapping (B.1.2)."""

from __future__ import annotations

from getviews_pipeline.video_niche_benchmark import (
    build_niche_benchmark_payload,
    niche_row_to_video_meta,
)


def test_niche_row_to_video_meta_averages_views() -> None:
    row = {
        "organic_avg_views": 80000,
        "commerce_avg_views": 120000,
        "median_er": 0.05,
        "sample_size": 100,
    }
    meta = niche_row_to_video_meta(row)
    assert meta["avg_views"] == 100000
    assert meta["sample_size"] == 100
    assert 0.28 <= meta["avg_retention"] <= 0.92
    assert meta["avg_ctr"] > 0


def test_build_payload_empty_row() -> None:
    out = build_niche_benchmark_payload(None, niche_id=4, duration_sec=40.0)
    assert out["niche_id"] == 4
    assert out["niche_meta"] is None
    assert out["niche_benchmark_curve"] == []
    assert out["retention_source"] == "modeled"


def test_build_payload_has_twenty_curve_points() -> None:
    row = {
        "organic_avg_views": 50000,
        "commerce_avg_views": 0,
        "median_er": 0.06,
        "sample_size": 40,
        "computed_at": "2026-01-01T00:00:00Z",
    }
    out = build_niche_benchmark_payload(row, niche_id=2, duration_sec=58.0)
    assert len(out["niche_benchmark_curve"]) == 20
    assert out["niche_meta"]["sample_size"] == 40
    assert out["computed_at"] == "2026-01-01T00:00:00Z"
    assert out["reference_duration_sec"] == 58.0
