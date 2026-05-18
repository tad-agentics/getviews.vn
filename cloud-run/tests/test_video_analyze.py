"""Unit tests for Phase B video analyze helpers (no Gemini, no Supabase network)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from postgrest.exceptions import APIError

from getviews_pipeline.video_analyze import (
    _diagnostics_fresh,
    _fetch_corpus_row,
    _merge_sidecars_into_response,
    _response_from_diagnostics_row,
    is_flop_mode,
    resolve_video_id,
    run_video_analyze_pipeline,
)


@pytest.fixture
def sample_rows_for_quantiles() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in (100, 200, 300, 400, 500, 600, 700, 800, 900, 1000):
        rows.append({"views": 10_000, "shares": 0, "saves": s})
    return rows


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


def test_build_kpis_save_rate_thap_when_below_cohort_p25() -> None:
    from getviews_pipeline.video_analyze import build_kpis

    out = build_kpis(
        {"views": 10_000, "shares": 100, "saves": 0},
        {"avg_views": 50_000},
        mode="flop",
        retention_end_pct=60,
        cohort_save_p25_pct=0.05,
        cohort_save_p75_pct=1.5,
    )
    save_kpi = next(k for k in out if k["label"] == "SAVE RATE")
    assert save_kpi["delta"] == "thấp"


def test_build_kpis_save_rate_empty_delta_when_no_cohort_band() -> None:
    from getviews_pipeline.video_analyze import build_kpis

    out = build_kpis(
        {"views": 10_000, "shares": 0, "saves": 0},
        {"avg_views": 50_000},
        mode="flop",
        retention_end_pct=60,
    )
    save_kpi = next(k for k in out if k["label"] == "SAVE RATE")
    assert save_kpi["delta"] == ""


def test_build_kpis_rat_cao_when_no_cohort_and_save_high() -> None:
    from getviews_pipeline.video_analyze import build_kpis

    out = build_kpis(
        {"views": 10_000, "shares": 0, "saves": 400},
        {"avg_views": 50_000},
        mode="flop",
        retention_end_pct=60,
    )
    save_kpi = next(k for k in out if k["label"] == "SAVE RATE")
    assert save_kpi["delta"] == "rất cao"


def test_build_kpis_tertile_when_absolute_high_but_below_cohort_p75() -> None:
    """Above 2% absolute but below niche p75 → không dùng ``rất cao``."""
    from getviews_pipeline.video_analyze import build_kpis

    out = build_kpis(
        {"views": 10_000, "shares": 0, "saves": 500},
        {"avg_views": 50_000},
        mode="flop",
        retention_end_pct=60,
        cohort_save_p25_pct=2.5,
        cohort_save_p75_pct=8.0,
    )
    save_kpi = next(k for k in out if k["label"] == "SAVE RATE")
    assert save_kpi["delta"] == "TB"


def test_fetch_niche_quantiles_use_saves_over_views(sample_rows_for_quantiles: list[dict[str, Any]]) -> None:
    import getviews_pipeline.video_analyze as va

    va._KPI_QUANT_CACHE.clear()
    mock_res = MagicMock()
    mock_res.data = sample_rows_for_quantiles
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.gt.return_value.gte.return_value.limit.return_value.execute.return_value = mock_res

    (s25, s75), _sh = va.fetch_niche_save_share_pct_quantiles_sync(sb, 4242, min_samples=5, limit=200)
    assert s25 == 3.0 and s75 == 8.0


def test_response_from_diagnostics_row_maps_flop_issues_to_errors() -> None:
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
    err = {"error_id": "ERR_1", "sev": "high", "t": 0, "end": 1, "title": "t", "detail": "d", "fix": "f"}
    diag = {
        "analysis_headline": None,
        "analysis_subtext": None,
        "segments": [],
        "hook_phases": [],
        "lessons": [],
        "flop_issues": [err],
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
    assert out["errors"] == [err]


def test_is_flop_mode_winning() -> None:
    niche = {
        "organic_avg_views": 50_000,
        "commerce_avg_views": 0,
        "median_er": 0.04,
    }
    video = {"views": 100_000, "engagement_rate": 0.06}
    assert is_flop_mode(video, niche) is False


# ── Niche-less fallback (PR-A) ──────────────────────────────────────


def test_is_flop_mode_niche_less_clear_underperformance() -> None:
    """No niche cohort → absolute floor. Pre-fix this branch silently
    defaulted to win regardless of metrics, mis-rendering every URL
    paste whose hashtags didn't classify."""
    # 2K views = clear under-performance, doesn't matter what ER is.
    video = {"views": 2_000, "engagement_rate": 5.0}
    assert is_flop_mode(video, niche_row=None) is True


def test_is_flop_mode_niche_less_low_er_at_modest_views() -> None:
    """Decent reach (12K views) but weak ER (0.8%) — flop. The AND
    on the loose tier protects against false positives on
    passive-consumption niches; weak engagement at moderate views
    is the genuine flop signal."""
    video = {"views": 12_000, "engagement_rate": 0.8}
    assert is_flop_mode(video, niche_row=None) is True


def test_is_flop_mode_niche_less_high_views_pass_even_with_low_er() -> None:
    """50K views with low ER (0.5%) — passive-consumption niches
    (asmr/sleep/relax) can have low ER but high reach. Don't flag
    these as flop in the niche-less fallback. Niche-cohort path
    can still flag if available; absolute thresholds are
    deliberately conservative."""
    video = {"views": 50_000, "engagement_rate": 0.5}
    assert is_flop_mode(video, niche_row=None) is False


def test_is_flop_mode_niche_less_modest_views_with_strong_er_pass() -> None:
    """10K views + 4% ER — modest reach but engaging. Not a flop;
    the loose tier requires BOTH weak views AND weak ER."""
    video = {"views": 10_000, "engagement_rate": 4.0}
    assert is_flop_mode(video, niche_row=None) is False


def test_is_flop_mode_niche_less_zero_views_no_signal() -> None:
    """0 views — brand-new post, no metrics yet. Fallback shouldn't
    flag this as flop (the floor checks ``> 0``)."""
    video = {"views": 0, "engagement_rate": 0.0}
    assert is_flop_mode(video, niche_row=None) is False


def test_diagnostics_fresh_within_ttl() -> None:
    now = datetime.now(UTC)
    row = {"computed_at": now.isoformat()}
    assert _diagnostics_fresh(row) is True


def test_diagnostics_stale_after_ttl() -> None:
    old = datetime.now(UTC) - timedelta(hours=2)
    row = {"computed_at": old.isoformat()}
    assert _diagnostics_fresh(row) is False


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
        "analysis_headline": None,
        "flop_issues": [],
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
    diag: dict = {
        "segments": [],
        "hook_phases": [],
        "lessons": [],
        "analysis_headline": None,
        "flop_issues": [],
    }
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
    now_iso = datetime.now(UTC).isoformat()
    diag_row = {
        "computed_at": now_iso,
        "analysis_headline": None,
        "analysis_subtext": None,
        "lessons": [],
        "hook_phases": [],
        "segments": [],
        "flop_issues": [
            {"error_id": "cached", "sev": "high", "t": 0, "end": 1, "title": "t", "detail": "d", "fix": "f"},
        ],
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
            "getviews_pipeline.video_analyze.extract_video_errors",
            side_effect=AssertionError("extract_video_errors must not run on cache hit"),
        ):
            out = run_video_analyze_pipeline(
                service_sb,
                user_sb,
                video_id="vid-cache",
                tiktok_url=None,
                force_refresh=False,
            )

    assert out["errors"][0].get("error_id") == "cached"
    assert out["meta"]["niche_label"] == "Làm đẹp"
    assert out["meta"]["retention_source"] == "modeled"
    service_sb.table.assert_not_called()


def test_force_refresh_skips_cache_hit() -> None:
    now_iso = datetime.now(UTC).isoformat()
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

    llm_out = [{"error_id": "fresh", "sev": "mid", "t": 0, "end": 1, "title": "fresh", "detail": "d", "fix": "f"}]
    gemini_called: list[str] = []

    def fake_extract(**kwargs: object) -> list:
        gemini_called.append("extract")
        return llm_out

    with patch(
        "getviews_pipeline.video_analyze._fetch_sidecars_sync",
        return_value=(None, None),
    ):
        with patch("getviews_pipeline.video_analyze.extract_video_errors", side_effect=fake_extract):
            out = run_video_analyze_pipeline(
                service_sb,
                user_sb,
                video_id="vid-refresh",
                tiktok_url=None,
                force_refresh=True,
            )

    assert gemini_called == ["extract"]
    assert any(e.get("title") == "fresh" for e in out["errors"])
    service_sb.table.assert_called_once_with("video_diagnostics")


def test_run_pipeline_respects_mode_override() -> None:
    """Heuristic would choose win; ``mode='flop'`` must run flop Gemini, not win."""
    now_iso = datetime.now(UTC).isoformat()
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
    raw = [{"error_id": "ERR_test", "sev": "high", "t": 0, "end": 1, "title": "t", "detail": "d", "fix": "f"}]
    gemini_called: list[str] = []

    def fake_extract(**kwargs: object) -> list:
        gemini_called.append("extract")
        assert kwargs.get("extraction_mode") == "flop"
        return raw

    with patch(
        "getviews_pipeline.video_analyze._fetch_sidecars_sync",
        return_value=(None, None),
    ):
        with patch("getviews_pipeline.video_analyze.extract_video_errors", side_effect=fake_extract):
            out = run_video_analyze_pipeline(
                service_sb,
                user_sb,
                video_id="vid-mode-override",
                tiktok_url=None,
                mode="flop",
            )

    assert gemini_called == ["extract"]
    assert out["mode"] == "flop"
    assert isinstance(out["errors"], list)
    assert len(out["errors"]) >= 1
    assert out["errors"][0].get("title") == "t"
    service_sb.table.assert_called_once_with("video_diagnostics")


# ── resolve_video_id — tolerates both aweme_id + video_corpus.id (UUID) ────


def test_resolve_video_id_returns_aweme_id_as_is() -> None:
    """Canonical shape: numeric aweme_id passes through unchanged."""
    sb = MagicMock()
    out = resolve_video_id(sb, video_id="7630766288574369045", tiktok_url=None)
    assert out == "7630766288574369045"
    # No corpus lookup needed for aweme_id input.
    sb.table.assert_not_called()


def test_resolve_video_id_tolerates_corpus_row_uuid() -> None:
    """Explore grid passes video_corpus.id instead of aweme_id — resolve
    by looking up the row and returning its video_id column."""
    sb = MagicMock()
    chain = sb.table.return_value.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = SimpleNamespace(
        data=[{"video_id": "7630766288574369045"}]
    )

    out = resolve_video_id(
        sb,
        video_id="1298c980-1df3-4b24-aee1-7feff3427bfa",
        tiktok_url=None,
    )
    assert out == "7630766288574369045"
    sb.table.assert_called_with("video_corpus")
    # Lookup must filter on `id`, not `video_id` — that's the whole point.
    sb.table.return_value.select.assert_called_with("video_id")
    sb.table.return_value.select.return_value.eq.assert_called_with(
        "id", "1298c980-1df3-4b24-aee1-7feff3427bfa"
    )


def test_resolve_video_id_uuid_with_no_corpus_row_raises() -> None:
    """If the UUID doesn't match any corpus row, surface a clear error
    rather than silently returning the UUID (which would then fail
    downstream with the misleading 'video not in corpus')."""
    sb = MagicMock()
    chain = sb.table.return_value.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = SimpleNamespace(data=[])

    with pytest.raises(ValueError, match="Không tìm thấy video trong corpus cho id này"):
        resolve_video_id(
            sb,
            video_id="00000000-0000-0000-0000-000000000000",
            tiktok_url=None,
        )


def test_resolve_video_id_uppercase_uuid_matches_pattern() -> None:
    """UUID matcher is case-insensitive — some callers upper-case."""
    sb = MagicMock()
    chain = sb.table.return_value.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = SimpleNamespace(
        data=[{"video_id": "7630766288574369045"}]
    )
    out = resolve_video_id(
        sb,
        video_id="1298C980-1DF3-4B24-AEE1-7FEFF3427BFA",
        tiktok_url=None,
    )
    assert out == "7630766288574369045"


def test_resolve_video_id_falls_back_to_tiktok_url() -> None:
    """No video_id, but tiktok_url present — look up by URL."""
    sb = MagicMock()
    chain = sb.table.return_value.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = SimpleNamespace(
        data=[{"video_id": "7630766288574369045"}]
    )
    out = resolve_video_id(
        sb,
        video_id=None,
        tiktok_url="https://www.tiktok.com/@bbskincare1/video/7630766288574369045",
    )
    assert out == "7630766288574369045"
    sb.table.return_value.select.return_value.eq.assert_called_with(
        "tiktok_url", "https://www.tiktok.com/@bbskincare1/video/7630766288574369045"
    )


def test_resolve_video_id_neither_raises() -> None:
    sb = MagicMock()
    with pytest.raises(ValueError, match="Cần video_id hoặc tiktok_url"):
        resolve_video_id(sb, video_id=None, tiktok_url=None)


# ── target_vs_creator_median + enrichment surface (2026-05-08) ──────────


def _video_for_response(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "video_id": "v1",
        "creator_handle": "u",
        "views": 250_000,
        "likes": 18_000,
        "comments": 800,
        "shares": 1_200,
        "saves": 10_000,
        "save_rate": 0.04,
        "analysis_json": {},
        "created_at": None,
    }
    base.update(overrides)
    return base


def _empty_diag() -> dict[str, Any]:
    return {
        "analysis_headline": None,
        "analysis_subtext": None,
        "segments": [],
        "hook_phases": [],
        "lessons": [],
        "flop_issues": [],
    }


def test_response_meta_carries_creator_median_views_and_ratio() -> None:
    """`creator_median_views` from the corpus row should pass through to
    `meta` along with the pre-computed `target_vs_creator_median` ratio
    (rounded 2dp). FE renders the "X.Y× kênh trung bình" tag from these."""
    video = _video_for_response(views=1_000_000, creator_median_views=400_000)
    out = _response_from_diagnostics_row(
        video,
        _empty_diag(),
        mode="win",
        niche_meta={"avg_views": 50_000, "avg_retention": 0.5, "avg_ctr": 0.04, "sample_size": 10},
        niche_benchmark=[],
        retention_user=[],
        niche_label="Tech",
        retention_source="modeled",
    )
    assert out["meta"]["creator_median_views"] == 400_000
    assert out["meta"]["target_vs_creator_median"] == 2.5


def test_response_meta_omits_ratio_when_creator_median_missing() -> None:
    """On-demand path (or pre-2026-05-08 corpus rows) has no
    `creator_median_views` — meta should report None for both fields
    so the FE just hides the strip instead of dividing by zero."""
    video = _video_for_response()  # no creator_median_views
    out = _response_from_diagnostics_row(
        video,
        _empty_diag(),
        mode="win",
        niche_meta={"avg_views": 50_000, "avg_retention": 0.5, "avg_ctr": 0.04, "sample_size": 10},
        niche_benchmark=[],
        retention_user=[],
        niche_label="Tech",
        retention_source="modeled",
    )
    assert out["meta"]["creator_median_views"] is None
    assert out["meta"]["target_vs_creator_median"] is None


def test_response_surfaces_enrichment_from_analysis_json() -> None:
    """`target_audience` / `pain_points` / `promotion_type` / `style_tags`
    are extracted by Gemini into VideoAnalysis but never previously
    surfaced. Pulling from `analysis_json` works for both corpus and
    on-demand paths since both populate the same dict."""
    video = _video_for_response(analysis_json={
        "target_audience": "phụ nữ 25–34 vùng đô thị",
        "pain_points": ["da dầu mụn ẩn", "ngân sách hạn chế"],
        "promotion_type": "brand_deal",
        "style_tags": ["talking_head", "POV", "fast_cuts"],
    })
    out = _response_from_diagnostics_row(
        video,
        _empty_diag(),
        mode="win",
        niche_meta={"avg_views": 50_000, "avg_retention": 0.5, "avg_ctr": 0.04, "sample_size": 10},
        niche_benchmark=[],
        retention_user=[],
        niche_label="Beauty",
        retention_source="modeled",
    )
    enrichment = out["enrichment"]
    assert enrichment is not None
    assert enrichment["target_audience"] == "phụ nữ 25–34 vùng đô thị"
    assert enrichment["pain_points"] == ["da dầu mụn ẩn", "ngân sách hạn chế"]
    assert enrichment["promotion_type"] == "brand_deal"
    assert enrichment["style_tags"] == ["talking_head", "POV", "fast_cuts"]


def test_response_omits_enrichment_when_analysis_empty() -> None:
    """Default VideoAnalysis values (empty audience, empty lists, organic
    promotion) signal "Gemini didn't surface anything useful" — emit
    None so FE hides the section instead of rendering a blank chip row."""
    video = _video_for_response(analysis_json={
        "target_audience": "",
        "pain_points": [],
        "promotion_type": "organic",
        "style_tags": [],
    })
    out = _response_from_diagnostics_row(
        video,
        _empty_diag(),
        mode="win",
        niche_meta={"avg_views": 50_000, "avg_retention": 0.5, "avg_ctr": 0.04, "sample_size": 10},
        niche_benchmark=[],
        retention_user=[],
        niche_label="Tech",
        retention_source="modeled",
    )
    assert out["enrichment"] is None


# ── KPI delta — niche-relative multiplier (× ngách) ─────────────────


def test_build_kpis_views_delta_uses_nguach_label_with_thick_cohort() -> None:
    """Honest label: it's a niche-cohort comparison, not a channel one.
    Was previously "× kênh" which conflicts with the true channel-
    relative ratio in ContextStrip."""
    from getviews_pipeline.video_analyze import build_kpis

    out = build_kpis(
        {"views": 250_000, "shares": 0, "saves": 0},
        {"avg_views": 100_000},
        mode="win",
        retention_end_pct=70,
    )
    assert out[0]["label"] == "VIEW"
    assert out[0]["delta"] == "2.5× ngách"


def test_build_kpis_hides_views_delta_when_cohort_is_sparse() -> None:
    """Pre-2026-05-08 a sparse niche (avg_views = 0 → max(0,1) = 1)
    produced "126192.0× kênh" for a 126K-view video. Now: any cohort
    avg < 1_000 is too thin to anchor a ratio — show "—" instead."""
    from getviews_pipeline.video_analyze import build_kpis

    out = build_kpis(
        {"views": 126_192, "shares": 0, "saves": 0},
        {"avg_views": 0},  # niche cohort thin → no benchmark
        mode="win",
        retention_end_pct=50,
    )
    assert out[0]["delta"] == "—"


def test_build_kpis_hides_views_delta_when_cohort_below_floor() -> None:
    """Threshold check at 1_000 — anything below is treated as
    too-thin to publish a multiplier the user will trust."""
    from getviews_pipeline.video_analyze import build_kpis

    out = build_kpis(
        {"views": 50_000, "shares": 0, "saves": 0},
        {"avg_views": 800},
        mode="win",
        retention_end_pct=50,
    )
    assert out[0]["delta"] == "—"


def test_response_enrichment_normalizes_unknown_promotion_type() -> None:
    """Defensive: any unrecognised `promotion_type` (older corpus rows,
    Gemini hallucination) should fall back to `organic`, never leaked
    raw — VideoEnrichmentPayload has a strict Literal."""
    video = _video_for_response(analysis_json={
        "target_audience": "audience",
        "promotion_type": "viral_paid",  # not in the literal
    })
    out = _response_from_diagnostics_row(
        video,
        _empty_diag(),
        mode="win",
        niche_meta={"avg_views": 50_000, "avg_retention": 0.5, "avg_ctr": 0.04, "sample_size": 10},
        niche_benchmark=[],
        retention_user=[],
        niche_label="Tech",
        retention_source="modeled",
    )
    assert out["enrichment"]["promotion_type"] == "organic"


# ── Narrative cache update — partial-synth NULL overwrite guard ────────


def test_narrative_cache_update_omits_keys_when_synth_returns_none() -> None:
    """Regression for the c69d0cd family of bug — a partial-success synth
    must NOT NULL-out a valid cached row. Only keys whose computed value
    is present should appear in the UPDATE payload."""
    from getviews_pipeline.video_analyze import _build_narrative_cache_update

    payload = _build_narrative_cache_update(
        narrative_vi={"van_de_chinh": "ok"},
        format_cards=None,
        diagnosis_md=None,
        performance_tier=None,
        bright_spot=None,
        view_scenarios=None,
        channel_context=None,
        reference_videos=None,
    )
    # narrative_vi is the anchor — always written.
    assert "narrative_vi" in payload
    # Everything else missing → omitted, preserving any prior cached value.
    for k in (
        "format_cards",
        "diagnosis",
        "performance_tier",
        "bright_spot_signal",
        "view_scenarios",
        "channel_context",
        "reference_videos",
        "niche_posting_context",
    ):
        assert k not in payload, f"{k} would have NULL-overwritten the cache"


def test_narrative_cache_update_includes_all_keys_when_all_present() -> None:
    """Happy path — full synth output writes everything."""
    from getviews_pipeline.video_analyze import _build_narrative_cache_update

    payload = _build_narrative_cache_update(
        narrative_vi={"van_de_chinh": "ok"},
        format_cards=[{"format_name_vi": "x"}],
        diagnosis_md="md",
        performance_tier="hit",
        bright_spot={"signal_type": "performing_well"},
        view_scenarios=[{"focus_vi": "a"}],
        channel_context={"available": True},
        reference_videos=[{"aweme_id": "x"}],
        niche_posting_context={"sample_size": 20, "window_days": 14, "grid": [[0.0] * 8] * 7},
    )
    for k in (
        "narrative_vi",
        "format_cards",
        "diagnosis",
        "performance_tier",
        "bright_spot_signal",
        "view_scenarios",
        "channel_context",
        "reference_videos",
        "niche_posting_context",
    ):
        assert k in payload
