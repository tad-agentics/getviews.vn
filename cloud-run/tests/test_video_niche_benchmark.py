"""Tests for Phase B niche benchmark mapping (B.1.2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from getviews_pipeline.video_niche_benchmark import (
    build_niche_benchmark_payload,
    count_winners_sample_in_niche_sync,
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


def test_niche_row_to_video_meta_null_views_when_both_zero() -> None:
    row = {
        "organic_avg_views": 0,
        "commerce_avg_views": 0,
        "median_er": 0.04,
        "sample_size": 10,
    }
    meta = niche_row_to_video_meta(row)
    assert meta["avg_views"] is None


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
    assert out["niche_meta"].get("winners_sample_size") is None
    assert out["computed_at"] == "2026-01-01T00:00:00Z"
    assert out["reference_duration_sec"] == 58.0


def test_build_payload_winners_sample_size_with_user_sb() -> None:
    row = {
        "organic_avg_views": 50000,
        "commerce_avg_views": 0,
        "median_er": 0.06,
        "sample_size": 40,
        "computed_at": "2026-01-01T00:00:00Z",
    }
    mock_res = MagicMock()
    mock_res.count = 42
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.or_.return_value.execute.return_value = mock_res
    out = build_niche_benchmark_payload(row, niche_id=7, duration_sec=58.0, user_sb=sb)
    assert out["niche_meta"]["winners_sample_size"] == 42
    sb.table.assert_called_once_with("video_corpus")


def test_count_winners_returns_none_without_sb() -> None:
    assert count_winners_sample_in_niche_sync(None, 1, 0.05) is None


def test_niche_row_to_video_meta_falls_back_to_avg_views_for_content_class() -> None:
    # content_class_intelligence MV has no organic/commerce split — it
    # exposes avg_views directly. Previously this row produced
    # avg_views=None, which cascaded into "—" KPI multiplier and
    # performance_tier="unknown" → narrative flop tone for hit videos.
    row = {
        "avg_views": 82000,
        "median_views": 60000,
        "median_er": 0.05,
        "sample_size": 25,
    }
    meta = niche_row_to_video_meta(row)
    assert meta["avg_views"] == 82000
    assert meta["sample_size"] == 25


def test_niche_row_to_video_meta_falls_back_to_median_views_when_avg_missing() -> None:
    row = {
        "median_views": 41000,
        "median_er": 0.03,
        "sample_size": 18,
    }
    meta = niche_row_to_video_meta(row)
    assert meta["avg_views"] == 41000


def test_niche_row_to_video_meta_still_null_when_no_views_column_set() -> None:
    # Defence: row that genuinely has no positive view signal in any
    # known column still maps to None (FE renders "—").
    row = {
        "organic_avg_views": 0,
        "commerce_avg_views": 0,
        "avg_views": 0,
        "median_views": 0,
        "median_er": 0.04,
        "sample_size": 10,
    }
    meta = niche_row_to_video_meta(row)
    assert meta["avg_views"] is None
