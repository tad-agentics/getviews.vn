"""``run_video_analyze_on_demand`` — fallback for URLs not in corpus.

The Studio composer routes URL pastes to ``/app/video?url=…`` via
``planAnswerEntry``. When the URL isn't in ``video_corpus`` the
endpoint used to 404 with "Không tìm thấy video trong corpus cho URL
này", leaving the user with a dead-end UI even though the BE has the
machinery to analyze any URL on demand (``ensemble.fetch_post_info`` +
``analyze_aweme``).

This module wires that fallback. Behaviour invariants under test:

  • Returns the same response shape as the corpus-row path so the FE
    renders identically — no special-case branch in the React tree.
  • Never reads or writes ``video_corpus`` / ``video_diagnostics`` —
    truly one-shot. Reruns re-charge ED + Gemini.
  • Skips the sidecar fetches (``thumbnail_analysis`` /
    ``comment_radar``) — those are corpus-only.
  • Best-effort niche resolution via ``classify_from_hashtags``;
    ``niche_id=0`` when nothing matches, and the FE's existing
    "Đang xây dựng pool" copy renders the empty cohort gracefully.
  • Tags the response ``source: "on_demand"`` so the FE can show a
    subtle "phân tích trực tiếp" hint.

These tests mock ``ensemble.fetch_post_info``, ``analyze_aweme``, the
hashtag classifier, and the win/flop Gemini synth — no network.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from getviews_pipeline.video_analyze import (
    FlopAnalysisLLM,
    FlopHeadline,
    FlopIssueLLM,
    LessonSlot,
    WinAnalysisLLM,
    _build_video_dict_from_aweme,
    run_video_analyze_on_demand,
)

# ── Test scaffolding ────────────────────────────────────────────────


def _aweme_fixture(
    *,
    aweme_id: str = "7630766288574369045",
    handle: str = "creatorx",
    views: int = 50_000,
    likes: int = 4_000,
    comments: int = 200,
    shares: int = 100,
    bookmarks: int = 800,
    desc: str = "video về làm đẹp",
    hashtags: tuple[str, ...] = ("skincare", "lamdep"),
    duration_ms: int = 30_000,
) -> dict:
    """Minimal aweme dict with the fields ``parse_metadata`` reads."""
    return {
        "aweme_id": aweme_id,
        "desc": desc,
        "create_time": 1_735_000_000,
        "video": {
            "duration": duration_ms,
            "origin_cover": {"url_list": ["https://cdn.test/cover.jpg"]},
            "play_addr": {"url_list": ["https://cdn.test/video.mp4"]},
        },
        "statistics": {
            "play_count": views,
            "digg_count": likes,
            "comment_count": comments,
            "share_count": shares,
            "collect_count": bookmarks,
        },
        "author": {
            "unique_id": handle,
            "nickname": handle,
            "uid": "u1",
        },
        "text_extra": [{"hashtag_name": h} for h in hashtags],
    }


def _analysis_result_fixture() -> dict:
    """Minimal Gemini analyze_aweme result with the keys downstream
    helpers (``decompose_segments``, ``extract_hook_phases``,
    ``video_duration_sec``) read."""
    return {
        "content_type": "video",
        "analysis": {
            "duration_sec": 30.0,
            "hook_analysis": {
                "hook_phrase": "Đây là cách",
                "hook_type": "demo",
            },
            "scenes": [
                {"start": 0.0, "end": 1.0, "label": "hook"},
                {"start": 1.0, "end": 30.0, "label": "body"},
            ],
        },
        "metadata": {},
    }


def _make_user_sb_mock(*, niche_taxonomy_row: dict | None = None) -> MagicMock:
    """User-scoped Supabase client — only ``niche_intelligence`` and
    ``niche_taxonomy`` matter on the on-demand path; ``video_diagnostics``
    and ``video_corpus`` MUST never be read or written here.
    """

    def _table(name: str) -> MagicMock:
        t = MagicMock()
        if name == "niche_intelligence":
            t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        elif name == "niche_taxonomy":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                MagicMock(data=[niche_taxonomy_row] if niche_taxonomy_row else [])
            )
        elif name in {"video_corpus", "video_diagnostics"}:
            raise AssertionError(
                f"on-demand path must NOT touch {name!r} — that's corpus-only"
            )
        return t

    sb = MagicMock()
    sb.table.side_effect = _table
    return sb


def _win_llm() -> WinAnalysisLLM:
    return WinAnalysisLLM(
        analysis_headline="Headline win",
        analysis_subtext="Subtext win",
        lessons=[
            LessonSlot(title=f"L{i}", body=f"Body {i}") for i in range(3)
        ],
        hook_bodies=["b0", "b1", "b2"],
    )


def _flop_llm() -> FlopAnalysisLLM:
    return FlopAnalysisLLM(
        analysis_headline=FlopHeadline(
            prefix="Video chỉ đạt ",
            view_accent="50K",
            middle=" view, dưới ngưỡng ngách. ",
            prediction_pos="Sửa hook",
            suffix=" để bật lên 200K.",
        ),
        flop_issues=[
            FlopIssueLLM(
                sev="high",
                t=0.0,
                end=2.0,
                title="Hook yếu",
                detail="Hook không neo được attention",
                fix="Thay bằng câu hỏi đảo",
            ),
        ],
    )


# ── 1. Builds corpus-shaped video dict from aweme + analysis ───────


def test_build_video_dict_maps_aweme_fields() -> None:
    """The synthesised video dict must carry every key the downstream
    builders read so we don't have to fork the corpus-row code path."""
    aweme = _aweme_fixture()
    analyze_result = _analysis_result_fixture()
    video = _build_video_dict_from_aweme(aweme, analyze_result, niche_id=3)

    assert video["video_id"] == "7630766288574369045"
    assert video["creator_handle"] == "creatorx"
    assert video["views"] == 50_000
    assert video["likes"] == 4_000
    assert video["comments"] == 200
    assert video["shares"] == 100
    assert video["saves"] == 800
    assert video["save_rate"] == pytest.approx(800 / 50_000)
    assert video["niche_id"] == 3
    assert video["breakout_multiplier"] == 1.0
    assert video["analysis_json"]["hook_analysis"]["hook_phrase"] == "Đây là cách"
    assert video["tiktok_url"] == (
        "https://www.tiktok.com/@creatorx/video/7630766288574369045"
    )
    # ``created_at`` is derived from create_time epoch seconds.
    assert video["created_at"] is not None
    assert video["created_at"].startswith("20")


def test_build_video_dict_handles_zero_views() -> None:
    """A brand-new private video may have 0 views — save_rate must
    not divide by zero."""
    aweme = _aweme_fixture(views=0, bookmarks=0)
    analyze_result = _analysis_result_fixture()
    video = _build_video_dict_from_aweme(aweme, analyze_result, niche_id=0)
    assert video["save_rate"] == 0.0
    assert video["views"] == 0


# ── 2. End-to-end happy path: URL → analysis without corpus write ──


def test_on_demand_returns_full_response_without_corpus_write() -> None:
    """Composer pastes a URL → on-demand path runs Gemini → returns a
    response shaped like the corpus path. No corpus / diagnostics writes."""
    aweme = _aweme_fixture()
    analyze_result = _analysis_result_fixture()
    user_sb = _make_user_sb_mock(
        niche_taxonomy_row={"name_vn": "Làm đẹp", "name_en": "Beauty"},
    )
    service_sb = MagicMock()
    # service_sb is only used by classify_from_hashtags' cache — it's
    # patched out here, so any real call is a regression.
    service_sb.table.side_effect = AssertionError(
        "service_sb must not be called when classify_from_hashtags is patched"
    )

    with patch(
        "getviews_pipeline.video_analyze._fetch_and_analyze_async",
        new=AsyncMock(return_value=(aweme, analyze_result)),
    ), patch(
        "getviews_pipeline.video_analyze._classify_niche_id_async",
        new=AsyncMock(return_value=3),
    ), patch(
        "getviews_pipeline.video_analyze._call_win_gemini",
        return_value=_win_llm(),
    ), patch(
        "getviews_pipeline.video_analyze._call_flop_gemini",
        side_effect=AssertionError("win mode must not call flop synth"),
    ), patch(
        "getviews_pipeline.video_analyze.fetch_niche_intelligence_sync",
        return_value=None,
    ):
        out = run_video_analyze_on_demand(
            service_sb, user_sb, tiktok_url="https://www.tiktok.com/@x/video/1",
        )

    # Response shape mirrors the corpus path.
    assert out["video_id"] == "7630766288574369045"
    assert out["mode"] == "win"
    assert out["meta"]["creator"] == "creatorx"
    assert out["meta"]["views"] == 50_000
    assert out["meta"]["niche_label"] == "Làm đẹp"
    assert out["analysis_headline"] == "Headline win"
    assert out["analysis_subtext"] == "Subtext win"
    assert len(out["lessons"]) == 3
    # Distinguishing flag for the FE.
    assert out["source"] == "on_demand"
    # Sidecars must NOT be on the response — those are corpus-only.
    assert "thumbnail_analysis" not in out
    assert "comment_radar" not in out


# ── 3. Win/flop heuristic still applies on the on-demand path ──────


def test_on_demand_picks_flop_when_below_niche_median() -> None:
    """``is_flop_mode`` runs on the synthesised video dict the same way
    it does on a corpus row — when views are sub-median, we render the
    flop UI even though we have no corpus history for this video."""
    # 30K views in a niche where organic_avg = 100K → flop heuristic fires.
    aweme = _aweme_fixture(views=30_000, likes=500)
    analyze_result = _analysis_result_fixture()
    user_sb = _make_user_sb_mock()
    service_sb = MagicMock()
    service_sb.table.side_effect = AssertionError("must be patched")

    niche_intel = {
        "niche_id": 3,
        "sample_size": 200,
        "organic_avg_views": 100_000,
        "commerce_avg_views": 0,
        "median_er": 0.05,
        "avg_engagement_rate": 0.06,
    }

    with patch(
        "getviews_pipeline.video_analyze._fetch_and_analyze_async",
        new=AsyncMock(return_value=(aweme, analyze_result)),
    ), patch(
        "getviews_pipeline.video_analyze._classify_niche_id_async",
        new=AsyncMock(return_value=3),
    ), patch(
        "getviews_pipeline.video_analyze._call_flop_gemini",
        return_value=_flop_llm(),
    ), patch(
        "getviews_pipeline.video_analyze._call_win_gemini",
        side_effect=AssertionError("flop mode must not call win synth"),
    ), patch(
        "getviews_pipeline.video_analyze.fetch_niche_intelligence_sync",
        return_value=niche_intel,
    ):
        out = run_video_analyze_on_demand(
            service_sb, user_sb, tiktok_url="https://www.tiktok.com/@x/video/1",
        )

    assert out["mode"] == "flop"
    assert out["flop_issues"] is not None and len(out["flop_issues"]) == 1
    assert out["projected_views"] is not None  # heuristic populated for flop


# ── 4. Mode override forces win/flop regardless of heuristic ───────


def test_on_demand_respects_explicit_mode_override() -> None:
    """``mode='win'`` from the request body bypasses the heuristic so
    a sub-niche-median video can still render the win UI when the user
    explicitly asks (existing behaviour on the corpus path)."""
    aweme = _aweme_fixture(views=30_000)
    analyze_result = _analysis_result_fixture()
    user_sb = _make_user_sb_mock()
    service_sb = MagicMock()
    service_sb.table.side_effect = AssertionError("must be patched")

    niche_intel = {
        "niche_id": 3,
        "organic_avg_views": 100_000,
        "median_er": 0.05,
    }

    with patch(
        "getviews_pipeline.video_analyze._fetch_and_analyze_async",
        new=AsyncMock(return_value=(aweme, analyze_result)),
    ), patch(
        "getviews_pipeline.video_analyze._classify_niche_id_async",
        new=AsyncMock(return_value=3),
    ), patch(
        "getviews_pipeline.video_analyze._call_win_gemini",
        return_value=_win_llm(),
    ), patch(
        "getviews_pipeline.video_analyze._call_flop_gemini",
        side_effect=AssertionError("explicit win override must not call flop"),
    ), patch(
        "getviews_pipeline.video_analyze.fetch_niche_intelligence_sync",
        return_value=niche_intel,
    ):
        out = run_video_analyze_on_demand(
            service_sb, user_sb,
            tiktok_url="https://www.tiktok.com/@x/video/1",
            mode="win",
        )

    assert out["mode"] == "win"


# ── 5. Niche=0 fallback (no hashtag match) renders empty cohort ────


def test_on_demand_handles_unknown_niche_gracefully() -> None:
    """When ``classify_from_hashtags`` returns None (no taxonomic match
    for the video's hashtags), niche_id is 0 and the response carries
    the default empty-niche-meta — the FE's null-fallback for
    ``winners_sample_size`` already handles this without crashing."""
    aweme = _aweme_fixture(hashtags=("randomhashtag",))
    analyze_result = _analysis_result_fixture()
    user_sb = _make_user_sb_mock()  # no niche_taxonomy row
    service_sb = MagicMock()
    service_sb.table.side_effect = AssertionError("must be patched")

    with patch(
        "getviews_pipeline.video_analyze._fetch_and_analyze_async",
        new=AsyncMock(return_value=(aweme, analyze_result)),
    ), patch(
        "getviews_pipeline.video_analyze._classify_niche_id_async",
        new=AsyncMock(return_value=0),
    ), patch(
        "getviews_pipeline.video_analyze._call_win_gemini",
        return_value=_win_llm(),
    ), patch(
        "getviews_pipeline.video_analyze.fetch_niche_intelligence_sync",
        return_value=None,
    ):
        out = run_video_analyze_on_demand(
            service_sb, user_sb, tiktok_url="https://www.tiktok.com/@x/video/1",
        )

    # niche_label is empty (taxonomy lookup skipped when niche_id=0).
    assert out["meta"]["niche_label"] is None or out["meta"]["niche_label"] == ""
    # niche_meta has the default zero-pool shape.
    assert out["niche_meta"]["sample_size"] == 0
    assert out["niche_meta"]["winners_sample_size"] is None


# ── 6. Failed Gemini analysis surfaces as RuntimeError ─────────────


def test_on_demand_surfaces_gemini_error() -> None:
    """If ``analyze_aweme`` returns an error envelope (e.g. video
    download blocked, Gemini quota exhausted), the helper raises so the
    router can surface a 500 — better than returning a malformed result."""
    aweme = _aweme_fixture()
    user_sb = _make_user_sb_mock()
    service_sb = MagicMock()

    with patch(
        "getviews_pipeline.video_analyze._fetch_and_analyze_async",
        new=AsyncMock(return_value=(aweme, {"error": "Gemini quota exhausted"})),
    ):
        with pytest.raises(RuntimeError, match="Gemini quota exhausted"):
            run_video_analyze_on_demand(
                service_sb, user_sb,
                tiktok_url="https://www.tiktok.com/@x/video/1",
            )


# ── 7. Missing aweme_id → ValueError (caller maps to 400) ──────────


def test_on_demand_rejects_aweme_with_no_id() -> None:
    """Defensive: if EnsembleData returns a payload without aweme_id
    (shouldn't happen but the wire format is permissive), raise a
    structurally-invalid ValueError — caller maps to 400 not 500."""
    aweme = _aweme_fixture()
    aweme["aweme_id"] = ""  # corrupt
    analyze_result = _analysis_result_fixture()
    user_sb = _make_user_sb_mock()
    service_sb = MagicMock()
    service_sb.table.side_effect = AssertionError("must be patched")

    with patch(
        "getviews_pipeline.video_analyze._fetch_and_analyze_async",
        new=AsyncMock(return_value=(aweme, analyze_result)),
    ), patch(
        "getviews_pipeline.video_analyze._classify_niche_id_async",
        new=AsyncMock(return_value=0),
    ):
        with pytest.raises(ValueError, match="thiếu video_id"):
            run_video_analyze_on_demand(
                service_sb, user_sb,
                tiktok_url="https://www.tiktok.com/@x/video/1",
            )
