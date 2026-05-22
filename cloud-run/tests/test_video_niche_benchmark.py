"""Tests for Phase B niche benchmark mapping (B.1.2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from getviews_pipeline.video_niche_benchmark import (
    build_niche_benchmark_payload,
    carousel_diagnosis_thresholds,
    count_winners_sample_in_niche_sync,
    niche_row_to_video_meta,
    peer_percentile,
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


def test_avg_retention_varies_with_median_er_percent_scale() -> None:
    # median_er is stored as percent. Previously the formula used it as
    # a ratio so any niche with ≥ 0.14% ER saturated to retention
    # ≈ 0.848 — i.e. every niche modeled to the same retention. After
    # the percent→ratio conversion, different median_er values produce
    # different retention values within the [0.28, 0.92] band.
    lo = niche_row_to_video_meta({"median_er": 1.0, "sample_size": 10})  # 1%
    mid = niche_row_to_video_meta({"median_er": 5.0, "sample_size": 10})  # 5%
    hi = niche_row_to_video_meta({"median_er": 12.0, "sample_size": 10})  # 12%
    assert lo["avg_retention"] < mid["avg_retention"] < hi["avg_retention"]
    # Sanity: none clamp to the upper bound.
    assert lo["avg_retention"] < 0.92


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


def test_peer_percentile_above_median() -> None:
    assert peer_percentile(150_000, median=80_000, p75=120_000) == 93.0


def test_peer_percentile_below_median() -> None:
    assert peer_percentile(30_000, median=80_000) == 15.0


def test_attach_peer_percentile_label_vi() -> None:
    from getviews_pipeline.video_niche_benchmark import attach_peer_percentile_label

    out = attach_peer_percentile_label({"peer_percentile": 82.0})
    assert out["peer_percentile_label"]
    assert "82" in out["peer_percentile_label"]


def test_finalize_niche_meta_peer_tier_skips_non_tier_axis() -> None:
    from getviews_pipeline.video_niche_benchmark import finalize_niche_meta_peer_tier

    meta = {"avg_views": 10_000, "sample_size": 50}
    out = finalize_niche_meta_peer_tier(
        meta,
        benchmark_axis="content_class",
        benchmark_row={"median_views": 8_000, "p75_views": 12_000},
        views=15_000,
    )
    assert "peer_percentile" not in out


def test_carousel_diagnosis_thresholds_topic_axis() -> None:
    th = carousel_diagnosis_thresholds()
    assert th["topic_axis"] == "carousel"
    assert th["swipe_through_rate_strong"] == 0.60
    assert th["slide_count_ideal"] == 7
