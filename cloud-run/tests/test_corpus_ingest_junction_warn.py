"""HI-9 acceptance — junction-miss WARN at corpus shadow telemetry."""

from __future__ import annotations

import logging

from getviews_pipeline.corpus_ingest import _niche_resolution_shadow_fields


def test_junction_miss_emits_warn(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="getviews_pipeline.corpus_ingest")
    out = _niche_resolution_shadow_fields(
        {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "format_axis": "live_commerce",  # not in PR1/PR6 junction seed
                "confidence": 0.92,
            }
        },
        resolver_niche_id=2,
        video_id="vid_test_junction_miss",
    )
    assert any(
        "junction miss" in rec.message and "vid_test_junction_miss" in rec.message
        for rec in caplog.records
    ), caplog.text
    assert out["niche_resolution_source"] == "gemini_two_axis"


def test_junction_hit_no_warn(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="getviews_pipeline.corpus_ingest")
    _niche_resolution_shadow_fields(
        {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "format_axis": "review_unboxing",  # seeded
                "confidence": 0.92,
            }
        },
        resolver_niche_id=2,
        video_id="vid_test_junction_hit",
    )
    assert not any("junction miss" in rec.message for rec in caplog.records), caplog.text


def test_junction_hit_carousel_axis_no_warn(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="getviews_pipeline.corpus_ingest")
    _niche_resolution_shadow_fields(
        {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "carousel_format_axis": "tutorial_carousel",
                "confidence": 0.92,
            }
        },
        resolver_niche_id=2,
        video_id="vid_carousel_junction_hit",
        content_type="carousel",
    )
    assert not any("junction miss" in rec.message for rec in caplog.records), caplog.text


def test_junction_miss_carousel_axis_emits_warn(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="getviews_pipeline.corpus_ingest")
    _niche_resolution_shadow_fields(
        {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "carousel_format_axis": "not_a_valid_carousel_axis",
                "confidence": 0.92,
            }
        },
        resolver_niche_id=2,
        video_id="vid_carousel_junction_miss",
        content_type="carousel",
    )
    assert any(
        "junction miss" in rec.message and "vid_carousel_junction_miss" in rec.message
        for rec in caplog.records
    ), caplog.text


def test_video_uses_format_axis_when_both_present_no_warn(caplog) -> None:
    """Shadow junction check matches route: video ignores stray ``carousel_format_axis``."""
    caplog.set_level(logging.WARNING, logger="getviews_pipeline.corpus_ingest")
    _niche_resolution_shadow_fields(
        {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "format_axis": "review_unboxing",
                "carousel_format_axis": "not_a_valid_carousel_axis",
                "confidence": 0.92,
            }
        },
        resolver_niche_id=2,
        video_id="vid_video_dual_axis_hit",
    )
    assert not any("junction miss" in rec.message for rec in caplog.records), caplog.text


def test_video_junction_miss_on_video_axis_not_carousel_ok(caplog) -> None:
    """If ``format_axis`` misses the junction, WARN even when carousel axis would hit."""
    caplog.set_level(logging.WARNING, logger="getviews_pipeline.corpus_ingest")
    _niche_resolution_shadow_fields(
        {
            "niche_classification": {
                "creator_niche_slug": "beauty",
                "format_axis": "live_commerce",
                "carousel_format_axis": "tutorial_carousel",
                "confidence": 0.92,
            }
        },
        resolver_niche_id=2,
        video_id="vid_video_dual_axis_miss",
    )
    assert any(
        "junction miss" in rec.message and "vid_video_dual_axis_miss" in rec.message
        for rec in caplog.records
    ), caplog.text


def test_no_niche_classification_no_warn(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="getviews_pipeline.corpus_ingest")
    out = _niche_resolution_shadow_fields(
        {},
        resolver_niche_id=2,
        video_id="vid_no_nc",
    )
    assert out["niche_resolution_source"] == "hashtag"
    assert not any("junction miss" in rec.message for rec in caplog.records)
