"""W4-1 — build_channel_findings P0 + prompt inject."""

from __future__ import annotations

import pytest

from datetime import UTC, datetime, timedelta

from getviews_pipeline.channel_findings import (
    build_channel_findings,
    format_distribution_from_corpus_rows,
    format_findings_for_prompt,
    _cohort_er_threshold_pct,
)
from getviews_pipeline.channel_diagnose_prompts import build_channel_diagnosis_context


def _video(
    *,
    views: int,
    likes: int = 0,
    comments: int = 0,
    days_ago: int = 1,
    fmt: str = "product_closeup",
) -> dict:
    return {
        "views": views,
        "likes": likes,
        "comments": comments,
        "posted_at": datetime.now(tz=UTC) - timedelta(days=days_ago),
        "content_format": fmt,
        "caption": "test",
        "duration_sec": 20,
    }


def test_finding_channel_view_ceiling_300():
    videos = [_video(views=200, likes=1, comments=0, days_ago=i) for i in range(4)]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={"global_avg_views": 500, "max_views": 2000},
        recent_window_30d={"avg_views": 200, "video_count": 4},
        inflection=None,
    )
    ids = [f.id for f in findings]
    assert "channel_view_ceiling_300" in ids


def test_finding_channel_format_entropy_high():
    fmts = ["a", "b", "c", "d", "e", "f", "g", "h"]
    videos = [_video(views=5000, fmt=fmts[i % len(fmts)]) for i in range(16)]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={"global_avg_views": 5000, "max_views": 8000},
        recent_window_30d={"avg_views": 5000, "video_count": 16},
        inflection=None,
    )
    assert any(f.id == "channel_format_entropy_high" for f in findings)


def test_finding_channel_recent_vs_peak_er_drop():
    recent = [_video(views=1000, likes=50, comments=5, days_ago=i) for i in range(3)]
    old_peak = [_video(views=8000, likes=800, comments=80, days_ago=60 + i) for i in range(3)]
    findings = build_channel_findings(
        videos=recent + old_peak,
        channel_pattern={"global_avg_views": 3000, "max_views": 8000},
        recent_window_30d={"avg_views": 1000, "video_count": 3},
        inflection={
            "peak_avg": 8000,
            "current_avg": 1000,
            "drop_pct": 87.5,
            "peak_quarter": "2025Q4",
            "current_quarter": "2026Q1",
        },
    )
    assert any(f.id == "channel_recent_vs_peak_er_drop" for f in findings)


def test_finding_channel_peer_format_saturation():
    peer_rows = [
        {"content_format": "unboxing_process", "views": 9000}
        for _ in range(8)
    ] + [{"content_format": "product_closeup", "views": 5000} for _ in range(2)]
    findings = build_channel_findings(
        videos=[_video(views=4000, fmt="unboxing_process") for _ in range(6)],
        channel_pattern={"global_avg_views": 4000, "max_views": 6000},
        recent_window_30d={"avg_views": 4000, "video_count": 6},
        inflection=None,
        peer_corpus_rows=peer_rows,
        dominant_format="unboxing_process",
    )
    assert any(f.id == "channel_peer_format_saturation" for f in findings)


def test_prompt_contains_channel_findings_block():
    videos = [_video(views=150, likes=1, comments=0, days_ago=i) for i in range(4)]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={"global_avg_views": 200, "max_views": 500},
        recent_window_30d={"avg_views": 150, "video_count": 4},
        inflection=None,
    )
    ctx = build_channel_diagnosis_context(
        handle="testchan",
        videos=videos,
        trajectory="stagnant",
        channel_pattern={"global_avg_views": 200, "max_views": 500, "formats": {}},
        recent_window_30d={"avg_views": 150, "video_count": 4},
        inflection=None,
        top_performers=[],
        worst_performers=[],
        creator_match=None,
        ugc_creators=[],
        niche_benchmarks=None,
        channel_findings=findings,
    )
    assert "<<<CHANNEL FINDINGS>>>" in ctx
    assert format_findings_for_prompt(findings).startswith("<<<CHANNEL FINDINGS>>>")


def test_format_distribution_from_corpus_rows():
    rows = [
        {"content_format": "product_closeup"},
        {"content_format": "product_closeup"},
        {"content_format": "unboxing_process"},
    ]
    dist = format_distribution_from_corpus_rows(rows)
    assert dist["product_closeup"] == 67
    assert dist["unboxing_process"] == 33


def test_cohort_er_threshold_uses_p50_proxy():
    assert _cohort_er_threshold_pct({"engagement_p50": 0.04}) == pytest.approx(3.4, rel=0.01)


def test_cohort_er_threshold_default():
    assert _cohort_er_threshold_pct(None) == 2.0
