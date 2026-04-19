"""Unit tests for Phase B video analyze helpers (no Gemini, no Supabase network)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from postgrest.exceptions import APIError

from getviews_pipeline.video_analyze import (
    LessonSlot,
    WinAnalysisLLM,
    _diagnostics_fresh,
    _fetch_corpus_row,
    _response_from_diagnostics_row,
    is_flop_mode,
    projected_views_heuristic,
    run_video_analyze_pipeline,
)


def test_is_flop_mode_low_views_vs_niche() -> None:
    niche = {
        "organic_avg_views": 100_000,
        "commerce_avg_views": 0,
        "median_er": 0.05,
    }
    video = {"views": 30_000, "engagement_rate": 0.06}
    assert is_flop_mode(video, niche) is True


def test_is_flop_mode_low_er() -> None:
    niche = {
        "organic_avg_views": 50_000,
        "commerce_avg_views": 0,
        "median_er": 0.05,
    }
    video = {"views": 80_000, "engagement_rate": 0.02}
    assert is_flop_mode(video, niche) is True


def test_is_flop_mode_winning() -> None:
    niche = {
        "organic_avg_views": 50_000,
        "commerce_avg_views": 0,
        "median_er": 0.04,
    }
    video = {"views": 100_000, "engagement_rate": 0.06}
    assert is_flop_mode(video, niche) is False


def test_diagnostics_fresh_within_ttl() -> None:
    now = datetime.now(timezone.utc)
    row = {"computed_at": now.isoformat()}
    assert _diagnostics_fresh(row) is True


def test_diagnostics_stale_after_ttl() -> None:
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    row = {"computed_at": old.isoformat()}
    assert _diagnostics_fresh(row) is False


def test_projected_views_heuristic_caps() -> None:
    p = projected_views_heuristic(
        views=10_000,
        niche_avg_views=100_000,
        flop_issues=[{"sev": "high"}, {"sev": "high"}],
    )
    assert p <= int(100_000 * 1.15)


def test_projected_views_heuristic_zero_niche_avg_not_zero() -> None:
    """When niche intelligence is missing, cap must not collapse to 0."""
    p = projected_views_heuristic(
        views=10_000,
        niche_avg_views=0,
        flop_issues=[{"sev": "high"}],
    )
    assert p == int(10_000 * 2.2)


@pytest.mark.parametrize(
    "execute_side",
    ["maybe_single_none", "pgrst116"],
    ids=["no_row_response", "pgrst116_error"],
)
def test_corpus_row_missing_raises_value_error(execute_side: str) -> None:
    sb = MagicMock()
    chain = sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value
    if execute_side == "maybe_single_none":
        chain.execute.return_value = None
    else:
        chain.execute.side_effect = APIError(
            {
                "message": "JSON object requested, multiple (or no) rows returned",
                "code": "PGRST116",
                "details": "The result contains 0 rows",
            }
        )
    with pytest.raises(ValueError, match="video not in corpus"):
        _fetch_corpus_row(sb, "missing-id")


def test_response_from_diagnostics_row_prefers_cached_curves() -> None:
    cached_ret = [{"t": 0.0, "pct": 50.0}, {"t": 60.0, "pct": 99.0}]
    cached_bench = [{"t": 0.0, "pct": 40.0}, {"t": 60.0, "pct": 41.0}]
    fallback_ret = [{"t": 0.0, "pct": 1.0}, {"t": 60.0, "pct": 2.0}]
    fallback_bench = [{"t": 0.0, "pct": 3.0}, {"t": 60.0, "pct": 4.0}]
    video = {
        "video_id": "v1",
        "creator_handle": "u",
        "views": 10_000,
        "likes": 1,
        "comments": 1,
        "shares": 1,
        "saves": 10,
        "save_rate": None,
        "analysis_json": {},
        "created_at": None,
    }
    diag = {
        "retention_curve": cached_ret,
        "niche_benchmark_curve": cached_bench,
        "segments": [],
        "hook_phases": [],
        "lessons": [],
    }
    out = _response_from_diagnostics_row(
        video,
        diag,
        mode="win",
        niche_meta={"avg_views": 50_000, "avg_retention": 0.5, "avg_ctr": 0.04, "sample_size": 10},
        niche_benchmark=fallback_bench,
        retention_user=fallback_ret,
        niche_label="Làm đẹp",
        retention_source="modeled",
    )
    assert out["retention_curve"] == cached_ret
    assert out["niche_benchmark_curve"] == cached_bench
    assert out["meta"]["niche_label"] == "Làm đẹp"
    assert out["meta"]["retention_source"] == "modeled"


def test_response_from_diagnostics_row_falls_back_when_curves_missing() -> None:
    fallback_ret = [{"t": 0.0, "pct": 11.0}, {"t": 60.0, "pct": 22.0}]
    fallback_bench = [{"t": 0.0, "pct": 33.0}, {"t": 60.0, "pct": 44.0}]
    video = {
        "video_id": "v1",
        "creator_handle": "u",
        "views": 10_000,
        "likes": 1,
        "comments": 1,
        "shares": 1,
        "saves": 10,
        "save_rate": None,
        "analysis_json": {},
        "created_at": None,
    }
    diag: dict = {"segments": [], "hook_phases": [], "lessons": []}
    out = _response_from_diagnostics_row(
        video,
        diag,
        mode="win",
        niche_meta={"avg_views": 50_000, "avg_retention": 0.5, "avg_ctr": 0.04, "sample_size": 10},
        niche_benchmark=fallback_bench,
        retention_user=fallback_ret,
        niche_label="",
        retention_source="modeled",
    )
    assert out["retention_curve"] == fallback_ret
    assert out["niche_benchmark_curve"] == fallback_bench
    assert out["meta"]["niche_label"] is None


def _make_analyze_mocks(
    *,
    diag_row: dict | None,
    video_row: dict,
    niche_rows: list | None,
) -> tuple[MagicMock, MagicMock]:
    """User-scoped client + service client for ``run_video_analyze_pipeline``."""
    now_iso = datetime.now(timezone.utc).isoformat()
    diag_list = [diag_row] if diag_row is not None else []

    def user_table(name: str) -> MagicMock:
        t = MagicMock()
        if name == "video_diagnostics":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=diag_list
            )
        elif name == "video_corpus":
            t.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
                SimpleNamespace(data=video_row)
            )
        elif name == "niche_intelligence":
            t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=niche_rows or [])
        elif name == "niche_taxonomy":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"name_vn": "Làm đẹp", "name_en": "Beauty"}]
            )
        return t

    user_sb = MagicMock()
    user_sb.table.side_effect = user_table

    service_sb = MagicMock()
    diag_tbl = MagicMock()
    diag_tbl.upsert.return_value.on_conflict.return_value.execute.return_value = MagicMock()
    service_sb.table.return_value = diag_tbl

    return user_sb, service_sb


def test_run_pipeline_cache_hit_skips_gemini() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    diag_row = {
        "computed_at": now_iso,
        "analysis_headline": "from cache",
        "analysis_subtext": "sub",
        "lessons": [],
        "hook_phases": [],
        "segments": [],
        "flop_issues": None,
        "retention_curve": [{"t": 0.0, "pct": 55.0}],
        "niche_benchmark_curve": [{"t": 0.0, "pct": 44.0}],
    }
    video_row = {
        "video_id": "vid-cache",
        "creator_handle": "creator",
        "views": 500_000,
        "likes": 1,
        "comments": 1,
        "shares": 1,
        "saves": 100,
        "save_rate": None,
        "engagement_rate": 0.08,
        "thumbnail_url": None,
        "created_at": "2025-06-01T12:00:00Z",
        "niche_id": 3,
        "analysis_json": {},
        "breakout_multiplier": 1.0,
        "tiktok_url": "https://tiktok.com/@x/video/1",
    }
    niche_intel = [
        {
            "niche_id": 3,
            "sample_size": 200,
            "organic_avg_views": 40_000,
            "commerce_avg_views": 0,
            "median_er": 0.04,
            "avg_engagement_rate": 0.05,
            "computed_at": now_iso,
        }
    ]
    user_sb, service_sb = _make_analyze_mocks(
        diag_row=diag_row,
        video_row=video_row,
        niche_rows=niche_intel,
    )

    with patch(
        "getviews_pipeline.video_analyze._call_win_gemini",
        side_effect=AssertionError("Gemini must not run on cache hit"),
    ):
        with patch(
            "getviews_pipeline.video_analyze._call_flop_gemini",
            side_effect=AssertionError("Flop Gemini must not run on cache hit"),
        ):
            out = run_video_analyze_pipeline(
                service_sb,
                user_sb,
                video_id="vid-cache",
                tiktok_url=None,
                force_refresh=False,
            )

    assert out["analysis_headline"] == "from cache"
    assert out["meta"]["niche_label"] == "Làm đẹp"
    assert out["meta"]["retention_source"] == "modeled"
    service_sb.table.assert_not_called()


def test_force_refresh_skips_cache_hit() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    diag_row = {
        "computed_at": now_iso,
        "analysis_headline": "stale cache headline",
        "analysis_subtext": "old",
        "lessons": [],
        "hook_phases": [{"label": "a", "t0": 0, "t1": 1, "body": "x"}] * 3,
        "segments": [],
        "flop_issues": None,
        "retention_curve": [{"t": 0.0, "pct": 1.0}],
        "niche_benchmark_curve": [{"t": 0.0, "pct": 2.0}],
    }
    video_row = {
        "video_id": "vid-refresh",
        "creator_handle": "creator",
        "views": 600_000,
        "likes": 2,
        "comments": 2,
        "shares": 2,
        "saves": 200,
        "save_rate": None,
        "engagement_rate": 0.09,
        "thumbnail_url": None,
        "created_at": "2025-06-01T12:00:00Z",
        "niche_id": 3,
        "analysis_json": {},
        "breakout_multiplier": 1.0,
        "tiktok_url": "https://tiktok.com/@x/video/2",
    }
    niche_intel = [
        {
            "niche_id": 3,
            "sample_size": 200,
            "organic_avg_views": 30_000,
            "commerce_avg_views": 0,
            "median_er": 0.04,
            "avg_engagement_rate": 0.05,
            "computed_at": now_iso,
        }
    ]
    user_sb, service_sb = _make_analyze_mocks(
        diag_row=diag_row,
        video_row=video_row,
        niche_rows=niche_intel,
    )

    llm_out = WinAnalysisLLM(
        analysis_headline="fresh from mock",
        analysis_subtext="new sub",
        lessons=[
            LessonSlot(title="L1", body="b1"),
            LessonSlot(title="L2", body="b2"),
            LessonSlot(title="L3", body="b3"),
        ],
        hook_bodies=["hb1", "hb2", "hb3"],
    )
    gemini_called: list[str] = []

    def fake_win(**kwargs: object) -> WinAnalysisLLM:
        gemini_called.append("win")
        return llm_out

    with patch("getviews_pipeline.video_analyze._call_win_gemini", side_effect=fake_win):
        out = run_video_analyze_pipeline(
            service_sb,
            user_sb,
            video_id="vid-refresh",
            tiktok_url=None,
            force_refresh=True,
        )

    assert gemini_called == ["win"]
    assert out["analysis_headline"] == "fresh from mock"
    service_sb.table.assert_called_once_with("video_diagnostics")
