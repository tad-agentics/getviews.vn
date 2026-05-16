"""ME-20 — carousel vs video corpus multiplier surfaced in diagnosis context."""

from __future__ import annotations

from getviews_pipeline.corpus_context import (
    aggregate_creator_format_history_from_rows,
    format_creator_format_history_for_diagnosis,
)


def test_aggregate_empty_rows() -> None:
    assert aggregate_creator_format_history_from_rows([]) is None


def test_format_skips_when_no_carousels() -> None:
    h = {"carousel_count": 0, "video_count": 5, "total_posts": 5}
    assert format_creator_format_history_for_diagnosis("user", h) == ""


def test_format_carousel_strong_line_at_15x() -> None:
    h = {
        "total_posts": 10,
        "carousel_count": 2,
        "video_count": 8,
        "carousel_avg_views": 300_000,
        "video_recent_avg": 150_000,
        "multiplier": 2.0,
        "top_carousel_views": 400_000,
    }
    out = format_creator_format_history_for_diagnosis("beautybc", h)
    assert "2.0×" in out
    assert "ưu tiên carousel" in out


def test_format_video_strong_when_multiplier_low() -> None:
    h = {
        "total_posts": 10,
        "carousel_count": 3,
        "video_count": 7,
        "carousel_avg_views": 50_000,
        "video_recent_avg": 100_000,
        "multiplier": 0.5,
        "top_carousel_views": 80_000,
    }
    out = format_creator_format_history_for_diagnosis("creatorx", h)
    assert "2.0×" in out  # inverse 1/0.5
    assert "carousel chưa phải thế mạnh" in out


def test_format_no_verdict_in_ambiguous_band() -> None:
    h = {
        "total_posts": 8,
        "carousel_count": 2,
        "video_count": 6,
        "carousel_avg_views": 100_000,
        "video_recent_avg": 100_000,
        "multiplier": 1.0,
        "top_carousel_views": 120_000,
    }
    out = format_creator_format_history_for_diagnosis("miduser", h)
    assert "LỊCH SỬ FORMAT" in out
    assert "ưu tiên carousel" not in out
    assert "chưa phải thế mạnh" not in out
