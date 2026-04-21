"""Unit tests for Phase B video analyze helpers (no Gemini, no Supabase network)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from postgrest.exceptions import APIError

from getviews_pipeline.video_analyze import (
    FlopAnalysisLLM,
    FlopHeadline,
    FlopIssueLLM,
    LessonSlot,
    WinAnalysisLLM,
    _coerce_analysis_headline_for_api,
    _diagnostics_fresh,
    _fetch_corpus_row,
    _merge_sidecars_into_response,
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


def test_flop_headline_total_at_400_ok() -> None:
    FlopHeadline(
        prefix="a" * 120,
        view_accent="b" * 40,
        middle="c" * 200,
        prediction_pos="d" * 39,
        suffix="e",
    )


def test_flop_headline_rejects_over_400_chars() -> None:
    with pytest.raises(ValueError, match="exceeds 400"):
        FlopHeadline(
            prefix="a" * 120,
            view_accent="b" * 40,
            middle="c" * 200,
            prediction_pos="d" * 40,
            suffix="e",
        )


def test_coerce_flop_headline_parses_json_string() -> None:
    payload = {
        "prefix": "Video dừng ở ",
        "view_accent": "8.4K view",
        "middle": " vì hook rơi muộn.",
        "prediction_pos": "~34K",
        "suffix": "",
    }
    raw = json.dumps(payload, ensure_ascii=False)
    out = _coerce_analysis_headline_for_api(raw, "flop")
    assert out == payload


def test_coerce_flop_headline_legacy_plain_string() -> None:
    assert _coerce_analysis_headline_for_api("Một headline cũ dạng text", "flop") == "Một headline cũ dạng text"


def test_response_from_diagnostics_row_flop_structured_headline() -> None:
    fh = {
        "prefix": "P",
        "view_accent": "V",
        "middle": "M",
        "prediction_pos": "~1K",
        "suffix": ".",
    }
    video = {
        "video_id": "v1",
        "creator_handle": "u",
        "views": 1000,
        "likes": 1,
        "comments": 1,
        "shares": 1,
        "saves": 10,
        "save_rate": None,
        "analysis_json": {},
        "created_at": None,
    }
    diag = {
        "analysis_headline": json.dumps(fh, ensure_ascii=False),
        "segments": [],
        "hook_phases": [],
        "lessons": [],
        "flop_issues": [{"sev": "high", "t": 0, "end": 1, "title": "t", "detail": "d", "fix": "f"}],
    }
    out = _response_from_diagnostics_row(
        video,
        diag,
        mode="flop",
        niche_meta={"avg_views": 50_000, "avg_retention": 0.5, "avg_ctr": 0.04, "sample_size": 10},
        niche_benchmark=[],
        retention_user=[],
        niche_label="Tech",
        retention_source="modeled",
    )
    assert out["analysis_headline"] == fh


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


def test_merge_sidecars_adds_optional_fields() -> None:
    thumb = {"contrast_score": 0.8}
    radar = {
        "sampled": 10,
        "total_available": 50,
        "sentiment": {"positive_pct": 0.5, "negative_pct": 0.2, "neutral_pct": 0.3},
        "purchase_intent": {"count": 1, "top_phrases": ["mua"]},
        "questions_asked": 2,
        "language": "vi",
    }
    base = {"video_id": "v1", "mode": "win"}
    with patch(
        "getviews_pipeline.video_analyze._fetch_sidecars_sync",
        return_value=(thumb, radar),
    ):
        out = _merge_sidecars_into_response(
            dict(base),
            video_id="v1",
            comment_count_hint=100,
        )
    assert out["thumbnail_analysis"] == thumb
    assert out["comment_radar"] == radar


def test_merge_sidecars_swallows_fetch_errors() -> None:
    base = {"video_id": "v1", "mode": "win"}
    with patch(
        "getviews_pipeline.video_analyze._fetch_sidecars_sync",
        side_effect=RuntimeError("network"),
    ):
        out = _merge_sidecars_into_response(
            dict(base),
            video_id="v1",
            comment_count_hint=0,
        )
    assert out == base
    assert "thumbnail_analysis" not in out
    assert "comment_radar" not in out


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
        "getviews_pipeline.video_analyze._fetch_sidecars_sync",
        return_value=(None, None),
    ):
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

    with patch(
        "getviews_pipeline.video_analyze._fetch_sidecars_sync",
        return_value=(None, None),
    ):
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


def test_run_pipeline_respects_mode_override() -> None:
    """Heuristic would choose win; ``mode='flop'`` must run flop Gemini, not win."""
    now_iso = datetime.now(timezone.utc).isoformat()
    video_row = {
        "video_id": "vid-mode-override",
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
        "tiktok_url": "https://tiktok.com/@x/video/99",
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
        diag_row=None,
        video_row=video_row,
        niche_rows=niche_intel,
    )
    llm_flop = FlopAnalysisLLM(
        analysis_headline=FlopHeadline(
            prefix="p",
            view_accent="v",
            middle="m",
            prediction_pos="~1",
            suffix=".",
        ),
        flop_issues=[FlopIssueLLM(sev="high", t=0, end=1, title="t", detail="d", fix="f")],
    )
    gemini_called: list[str] = []

    def fake_flop(**kwargs: object) -> FlopAnalysisLLM:
        gemini_called.append("flop")
        return llm_flop

    with patch(
        "getviews_pipeline.video_analyze._fetch_sidecars_sync",
        return_value=(None, None),
    ):
        with patch("getviews_pipeline.video_analyze._call_flop_gemini", side_effect=fake_flop):
            with patch(
                "getviews_pipeline.video_analyze._call_win_gemini",
                side_effect=AssertionError("win Gemini must not run when mode=flop override"),
            ):
                out = run_video_analyze_pipeline(
                    service_sb,
                    user_sb,
                    video_id="vid-mode-override",
                    tiktok_url=None,
                    mode="flop",
                )

    assert gemini_called == ["flop"]
    assert out["mode"] == "flop"
    assert isinstance(out["flop_issues"], list)
    assert len(out["flop_issues"]) >= 1
    assert out["flop_issues"][0].get("title") == "t"
    assert out["lessons"] == []
    assert out["analysis_subtext"] is None
    service_sb.table.assert_called_once_with("video_diagnostics")
