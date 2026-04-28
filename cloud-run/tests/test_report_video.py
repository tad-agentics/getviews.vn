"""``build_video_report`` — answer-session bridge to /video/analyze.

The video diagnosis report becomes a session format on /app/answer
(PR-1 added the type infra; this PR-2 adds the builder + dispatch
+ FE rendering). ``answer_session.append_turn`` calls
``build_video_report`` when ``builder_fmt == "video"``; the builder:

  1. Pulls a TikTok URL out of the user's free-form query.
  2. Tries the corpus path (run_video_analyze_pipeline).
  3. Falls through to the on-demand path on a corpus miss
     (mirrors the routers/video.py fallback wired in PR #286).
  4. Returns the ``VideoAnalyzeResponse``-shaped dict, augmented
     with empty ``sources`` + ``related_questions`` so the
     answer-shell readers type-narrow cleanly.

These tests pin the bridge contract — what query shapes parse,
which path runs, and what shape lands in ``answer_turns.payload``.
``run_video_analyze_pipeline`` and ``run_video_analyze_on_demand``
themselves have their own dedicated test files; here we only
verify the dispatch + envelope behaviour of the bridge.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.report_video import (
    build_video_report,
    detect_mode_from_query,
    extract_aweme_id,
    extract_tiktok_url,
)


# ── extract_tiktok_url ──────────────────────────────────────────────


def test_extract_tiktok_url_finds_first_match() -> None:
    """Vietnamese question + URL — the URL gets pulled cleanly even
    when surrounded by free text."""
    q = "tại sao video này không có view https://www.tiktok.com/@x/video/123"
    assert extract_tiktok_url(q) == "https://www.tiktok.com/@x/video/123"


def test_extract_tiktok_url_handles_short_link() -> None:
    """``vm.tiktok.com`` short-links resolve via post_info redirects;
    extractor must pass them through verbatim."""
    q = "soi giúp em https://vm.tiktok.com/abc123/"
    assert extract_tiktok_url(q) == "https://vm.tiktok.com/abc123/"


def test_extract_tiktok_url_handles_m_tiktok() -> None:
    """Mobile-share URLs use ``m.tiktok.com``."""
    q = "https://m.tiktok.com/@user/video/9876543210"
    assert extract_tiktok_url(q) == "https://m.tiktok.com/@user/video/9876543210"


def test_extract_tiktok_url_returns_none_when_no_url() -> None:
    """Pure-text query (no URL) → None. The caller raises."""
    assert extract_tiktok_url("tại sao video này flop?") is None


def test_extract_tiktok_url_returns_none_for_non_tiktok_url() -> None:
    """A YouTube URL must not match — the analyzer is TikTok-only."""
    assert extract_tiktok_url("https://www.youtube.com/watch?v=abc") is None


def test_extract_tiktok_url_picks_first_when_multiple() -> None:
    """Multi-URL queries (compare flow) shouldn't reach this builder,
    but defensive: the regex returns the first match — matches the
    /video/analyze single-URL contract."""
    q = "https://www.tiktok.com/@a/video/1 vs https://www.tiktok.com/@b/video/2"
    assert extract_tiktok_url(q) == "https://www.tiktok.com/@a/video/1"


# ── extract_aweme_id ────────────────────────────────────────────────


def test_extract_aweme_id_finds_bare_numeric_id() -> None:
    """PR-3 evidence-tile click path: ``state.prefillUrl`` is just
    the corpus row's video_id (no creator handle to build a URL).
    The builder must accept it as a corpus lookup key."""
    assert extract_aweme_id("7630766288574369045") == "7630766288574369045"


def test_extract_aweme_id_returns_none_for_short_runs() -> None:
    """Years (4 digits), follower counts, etc. must not match —
    aweme_ids are strictly 15-21 digits."""
    assert extract_aweme_id("Đăng năm 2026") is None
    assert extract_aweme_id("100K views") is None


def test_extract_aweme_id_returns_none_for_text() -> None:
    assert extract_aweme_id("tại sao video flop") is None


# ── build_video_report — aweme_id-only path ─────────────────────────


def test_build_video_report_corpus_path_with_bare_aweme_id() -> None:
    """Evidence-tile click sends just the video_id as prefillUrl.
    The builder routes it through ``video_id=`` instead of
    ``tiktok_url=`` so the corpus lookup uses the canonical id key."""
    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock):
        build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query="7630766288574369045",
        )

    call_kwargs = pipeline_mock.call_args.kwargs
    assert call_kwargs["video_id"] == "7630766288574369045"
    assert call_kwargs["tiktok_url"] is None


def test_build_video_report_aweme_id_corpus_miss_does_not_call_on_demand() -> None:
    """On-demand path needs a real URL to fetch from EnsembleData —
    a bare aweme_id can't drive that fetch. So an id-only request
    that misses corpus must hard-404, not silently degrade."""

    def _pipeline_raises(*_a, **_kw):
        raise ValueError("Không tìm thấy video trong corpus cho URL này")

    pipeline_mock = MagicMock(side_effect=_pipeline_raises)
    on_demand_mock = MagicMock(return_value="must-not-be-called")

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock), \
         patch("getviews_pipeline.report_video.run_video_analyze_on_demand",
               on_demand_mock):
        with pytest.raises(ValueError, match="cho id này"):
            build_video_report(
                service_sb=MagicMock(),
                user_sb=MagicMock(),
                query="7630766288574369045",
            )

    on_demand_mock.assert_not_called()


def test_build_video_report_prefers_url_over_aweme_id_when_both_present() -> None:
    """When the query has both a URL and a stray digit run, prefer
    the URL — it's the structurally-richer signal."""
    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock):
        build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query="https://www.tiktok.com/@x/video/123 7630766288574369045",
        )

    call_kwargs = pipeline_mock.call_args.kwargs
    # URL won — video_id stays None.
    assert call_kwargs["tiktok_url"] == "https://www.tiktok.com/@x/video/123"
    assert call_kwargs["video_id"] is None


# ── build_video_report — happy paths ────────────────────────────────


def _video_response_fixture() -> dict[str, Any]:
    """Minimal VideoAnalyzeResponse-shaped dict (matches what
    run_video_analyze_pipeline / on_demand return)."""
    return {
        "video_id": "7630766288574369045",
        "mode": "win",
        "meta": {
            "creator": "creatorx",
            "views": 250_000,
            "likes": 18_000,
            "comments": 800,
            "shares": 1_200,
            "save_rate": 0.04,
            "duration_sec": 28.5,
            "thumbnail_url": "https://r2.test/thumbnails/x.png",
            "date_posted": "2026-04-15",
            "title": "Đây là cách",
            "niche_label": "Làm đẹp",
            "retention_source": "modeled",
        },
        "kpis": [], "segments": [], "hook_phases": [], "lessons": [],
        "analysis_headline": "Headline win", "analysis_subtext": "Subtext",
        "flop_issues": None, "retention_curve": [], "niche_benchmark_curve": [],
        "niche_meta": {"avg_views": 100_000, "avg_retention": 0.55,
                       "avg_ctr": 0.04, "sample_size": 200,
                       "winners_sample_size": 30},
    }


def test_build_video_report_corpus_path_when_url_indexed() -> None:
    """URL is in ``video_corpus`` → run_video_analyze_pipeline returns
    cleanly → on-demand path NEVER called."""
    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)
    on_demand_mock = MagicMock(return_value="should-not-be-called")

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock), \
         patch("getviews_pipeline.report_video.run_video_analyze_on_demand",
               on_demand_mock):
        out = build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query="soi giúp https://www.tiktok.com/@x/video/1",
        )

    pipeline_mock.assert_called_once()
    on_demand_mock.assert_not_called()
    assert out["video_id"] == expected["video_id"]
    # Common ReportV1 fields are populated as empty defaults so the
    # answer-shell readers (sources card, related qs) type-narrow.
    assert out["sources"] == []
    assert out["related_questions"] == []


def test_build_video_report_falls_through_to_on_demand_on_corpus_miss() -> None:
    """URL NOT in ``video_corpus`` → corpus path raises ValueError
    with the documented "Không tìm thấy ... URL này" copy → bridge
    falls through to on-demand path. Same fallback the
    routers/video.py wired in PR #286."""
    expected = _video_response_fixture()
    expected["source"] = "on_demand"  # on-demand path tags the response

    def _pipeline_raises(*_a, **_kw):
        raise ValueError("Không tìm thấy video trong corpus cho URL này")

    pipeline_mock = MagicMock(side_effect=_pipeline_raises)
    on_demand_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock), \
         patch("getviews_pipeline.report_video.run_video_analyze_on_demand",
               on_demand_mock):
        out = build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query="soi giúp https://www.tiktok.com/@x/video/1",
        )

    pipeline_mock.assert_called_once()
    on_demand_mock.assert_called_once()
    assert out["source"] == "on_demand"


def test_build_video_report_propagates_non_url_miss_value_errors() -> None:
    """A ValueError from the corpus path that's NOT a URL miss (e.g.
    invalid UUID, missing video_id) must NOT trigger the on-demand
    fallback — the on-demand path can only resolve URLs."""

    def _pipeline_raises(*_a, **_kw):
        raise ValueError("Cần video_id hoặc tiktok_url")

    pipeline_mock = MagicMock(side_effect=_pipeline_raises)
    on_demand_mock = MagicMock(return_value="must-not-be-called")

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock), \
         patch("getviews_pipeline.report_video.run_video_analyze_on_demand",
               on_demand_mock):
        with pytest.raises(ValueError, match="Cần video_id"):
            build_video_report(
                service_sb=MagicMock(),
                user_sb=MagicMock(),
                query="soi giúp https://www.tiktok.com/@x/video/1",
            )

    on_demand_mock.assert_not_called()


def test_build_video_report_rejects_query_without_url() -> None:
    """Pure-text query ('tại sao video này flop?') reaches the builder
    only if the FE classifier missed → defensive 400. The session
    intent is video_diagnosis only when a URL was detected, but the
    builder still validates."""
    pipeline_mock = MagicMock()
    on_demand_mock = MagicMock()

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock), \
         patch("getviews_pipeline.report_video.run_video_analyze_on_demand",
               on_demand_mock):
        with pytest.raises(ValueError, match="Không tìm thấy link TikTok"):
            build_video_report(
                service_sb=MagicMock(),
                user_sb=MagicMock(),
                query="tại sao video này flop?",
            )

    pipeline_mock.assert_not_called()
    on_demand_mock.assert_not_called()


def test_build_video_report_passes_explicit_mode_to_pipeline() -> None:
    """Caller can request win/flop explicitly; the bridge forwards
    only valid literals (filters None / unknown)."""
    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock):
        build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query="soi giúp https://www.tiktok.com/@x/video/1",
            mode="flop",
        )

    call_kwargs = pipeline_mock.call_args.kwargs
    assert call_kwargs["mode"] == "flop"


def test_build_video_report_filters_invalid_mode_strings() -> None:
    """Defensive: caller passes ``mode="invalid"`` (e.g. from a stale
    URL param) → forward None instead, let the heuristic decide."""
    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock):
        build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query="soi giúp https://www.tiktok.com/@x/video/1",
            mode="something-bogus",
        )

    assert pipeline_mock.call_args.kwargs["mode"] is None


def test_build_video_report_response_validates_via_videopayload() -> None:
    """The returned dict must round-trip through ``VideoPayload`` —
    that's what ``answer_session`` will hand to
    ``validate_and_store_report("video", ...)``."""
    from getviews_pipeline.report_types import VideoPayload

    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock):
        out = build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query="https://www.tiktok.com/@x/video/1",
        )

    # Must validate cleanly so append_turn → validate_and_store_report
    # → answer_turns.payload INSERT doesn't blow up at runtime.
    VideoPayload.model_validate(out)


# ── detect_mode_from_query ──────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "tại sao video này không có view",
        "vì sao chưa có view nhỉ",
        "video flop",
        "video này flop quá",
        "tại sao kém vậy",
        "vì sao không nổ",
        "tại sao chưa nổ",
        "ít view quá em ơi",
        "view thấp",
        "video này không lên xu hướng",
        "tại sao chưa lên trending",
        "video tệ quá",
        "video kém",
    ],
)
def test_detect_mode_from_query_returns_flop_for_loss_signals(query: str) -> None:
    """Vietnamese flop phrasings the detector must catch — these are
    the dominant patterns observed in creator prompts. Adding new
    phrasings is fine; these existing ones must NEVER stop matching."""
    assert detect_mode_from_query(query) == "flop"


@pytest.mark.parametrize(
    "query",
    [
        "tại sao video này viral",
        "vì sao video nổ",
        "video viral lắm",
        "tại sao nổ",
        "vì sao thành công",
        "vì sao nhiều view",
        "video lên top",
        "video lên xu hướng",
        "tại sao lên trending",
        "video thành công vậy",
    ],
)
def test_detect_mode_from_query_returns_win_for_success_signals(query: str) -> None:
    """Vietnamese win phrasings — same contract as flop, different
    direction."""
    assert detect_mode_from_query(query) == "win"


def test_detect_mode_from_query_returns_none_for_neutral_text() -> None:
    """Pure URL paste, no question. Falls through to the BE
    ``is_flop_mode`` heuristic."""
    assert detect_mode_from_query("https://www.tiktok.com/@x/video/1") is None
    assert detect_mode_from_query("phân tích video này") is None
    assert detect_mode_from_query("") is None


def test_detect_mode_from_query_returns_none_when_signals_contradict() -> None:
    """Both signals present (rare but possible — user pastes one URL
    that flopped + another that went viral, asks both at once). Defer
    to the heuristic rather than guess."""
    assert detect_mode_from_query("video này flop nhưng viral") is None


def test_detect_mode_from_query_is_case_insensitive() -> None:
    """Lower-cased + capitalized + caps all match the same pattern."""
    assert detect_mode_from_query("VIRAL") == "win"
    assert detect_mode_from_query("Tại sao FLOP") == "flop"


# ── build_video_report — mode auto-detection from query ─────────────


def test_build_video_report_passes_detected_flop_mode_to_pipeline() -> None:
    """Mode hint flows: detect_mode_from_query → build_video_report
    forwards as ``mode="flop"`` to the pipeline. The Gemini synth
    runs the flop branch instead of letting the niche heuristic
    flip it (which gets it wrong when there's no cohort)."""
    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock):
        build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query=(
                "tại sao video này không có view "
                "https://www.tiktok.com/@x/video/1"
            ),
        )

    assert pipeline_mock.call_args.kwargs["mode"] == "flop"


def test_build_video_report_passes_detected_win_mode_to_pipeline() -> None:
    """Win-mode signal mirror of the flop case."""
    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock):
        build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query="vì sao video này viral https://www.tiktok.com/@x/video/1",
        )

    assert pipeline_mock.call_args.kwargs["mode"] == "win"


def test_build_video_report_explicit_mode_overrides_detection() -> None:
    """Caller-supplied ``mode`` wins over keyword detection. (Today
    no caller passes mode explicitly, but the contract matters for
    future surfaces — e.g. an admin force-refresh that needs to pin
    a specific branch.)"""
    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock):
        build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query=(
                "tại sao video này không có view "  # would detect flop
                "https://www.tiktok.com/@x/video/1"
            ),
            mode="win",  # explicit override
        )

    assert pipeline_mock.call_args.kwargs["mode"] == "win"


def test_build_video_report_no_mode_signal_passes_none() -> None:
    """Neutral query — no mode hint, ``is_flop_mode`` heuristic
    decides downstream."""
    expected = _video_response_fixture()
    pipeline_mock = MagicMock(return_value=expected)

    with patch("getviews_pipeline.report_video.run_video_analyze_pipeline",
               pipeline_mock):
        build_video_report(
            service_sb=MagicMock(),
            user_sb=MagicMock(),
            query="phân tích https://www.tiktok.com/@x/video/1",
        )

    assert pipeline_mock.call_args.kwargs["mode"] is None
