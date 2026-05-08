"""WhatStalled acceptance — empty list requires what_stalled_reason (Phase C.2)."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.report_pattern import (
    build_fixture_pattern_report,
    build_pattern_report,
    build_thin_corpus_pattern_report,
    fetch_pattern_wow_diff_rows,
    wow_rows_to_wow_diff,
)
from getviews_pipeline.report_pattern_compute import compute_what_stalled
from getviews_pipeline.report_types import PatternPayload, validate_and_store_report


def test_fixture_what_stalled_invariant() -> None:
    inner = build_fixture_pattern_report()
    p = PatternPayload.model_validate(inner)
    assert p.what_stalled == []
    assert p.confidence.what_stalled_reason is not None


def test_validate_and_store_pattern_envelope() -> None:
    inner = build_fixture_pattern_report()
    env = validate_and_store_report("pattern", inner)
    assert env["kind"] == "pattern"
    assert "report" in env


def test_empty_stalled_without_reason_raises() -> None:
    """Regression — §C.2 invariant must reject empty list + null reason."""
    inner = copy.deepcopy(build_fixture_pattern_report())
    inner["confidence"]["what_stalled_reason"] = None
    assert inner["what_stalled"] == []
    with pytest.raises(ValueError, match="what_stalled invariant violated"):
        PatternPayload.model_validate(inner)


def test_what_stalled_cap_at_three() -> None:
    """Regression — §C.2 invariant caps what_stalled at 3 entries."""
    inner = copy.deepcopy(build_fixture_pattern_report())
    # Synthesise 4 stalled findings by duplicating the first finding shape.
    if not inner["findings"]:
        pytest.skip("fixture has no findings to clone")
    base = inner["findings"][0]
    inner["what_stalled"] = [base] * 4
    with pytest.raises(ValueError, match="at most 3 entries"):
        PatternPayload.model_validate(inner)


def test_validate_and_store_rejects_invariant_violation() -> None:
    """Envelope validator must propagate the invariant error, not swallow it."""
    inner = copy.deepcopy(build_fixture_pattern_report())
    inner["confidence"]["what_stalled_reason"] = None
    with pytest.raises(ValueError, match="what_stalled invariant violated"):
        validate_and_store_report("pattern", inner)


# —— C.2.1 — WoW RPC mapping + thin corpus + build_pattern_report merge ——


def test_wow_rows_to_wow_diff_empty() -> None:
    w = wow_rows_to_wow_diff([])
    assert w.new_entries == [] and w.dropped == [] and w.rank_changes == []


def test_wow_rows_to_wow_diff_buckets() -> None:
    rows = [
        {"hook_type": "a", "rank_now": 1, "rank_prior": 0, "rank_change": 1, "is_new": True, "is_dropped": False},
        {"hook_type": "b", "rank_now": 4, "rank_prior": 2, "rank_change": 2, "is_new": False, "is_dropped": True},
        {"hook_type": "c", "rank_now": 2, "rank_prior": 3, "rank_change": -1, "is_new": False, "is_dropped": False},
    ]
    w = wow_rows_to_wow_diff(rows)
    assert len(w.new_entries) == 1 and w.new_entries[0]["hook_type"] == "a"
    assert len(w.dropped) == 1 and w.dropped[0]["hook_type"] == "b"
    assert len(w.rank_changes) == 1 and w.rank_changes[0]["hook_type"] == "c"


def test_wow_rows_skips_null_hook_type() -> None:
    w = wow_rows_to_wow_diff([{"hook_type": None, "is_new": True}])
    assert w.new_entries == []


def test_thin_corpus_payload_validates() -> None:
    inner = build_thin_corpus_pattern_report()
    p = PatternPayload.model_validate(inner)
    assert p.confidence.sample_size < 30
    assert p.what_stalled == []
    assert p.confidence.what_stalled_reason


def test_thin_corpus_never_leaks_fixture_evidence() -> None:
    """BUG-01 regression: thin-corpus path used to call ``build_fixture_pattern_report``
    which hardcoded 6 copies of ``@demo / Stub video`` evidence. Live
    responses must never include that placeholder.
    """
    inner = build_thin_corpus_pattern_report(sample_size=5, niche_label="Skincare")
    for ev in inner.get("evidence_videos") or []:
        assert ev.get("creator_handle") != "@demo"
        assert ev.get("title") != "Stub video"
        assert ev.get("video_id") != "stub-1"
    for f in inner.get("findings") or []:
        assert f.get("pattern") != "Mình vừa test ___ và"
    # Niche label flows through so the user sees their niche, not "Tech".
    assert inner["confidence"]["niche_scope"] == "Skincare"


def test_empty_pattern_report_has_no_stub_evidence() -> None:
    """BUG-01 regression: the empty-state payload used when the service
    client is unavailable or the niche has zero usable rows must return
    an empty evidence list, not the fixture's @demo cards.
    """
    from getviews_pipeline.report_pattern import build_empty_pattern_report

    inner = build_empty_pattern_report(niche_label="Làm đẹp / Skincare", window_days=7)
    p = PatternPayload.model_validate(inner)
    assert p.evidence_videos == []
    assert p.findings == []
    assert p.what_stalled == []
    assert p.confidence.niche_scope == "Làm đẹp / Skincare"
    assert p.confidence.what_stalled_reason  # non-empty humility reason


def test_full_fixture_is_full_corpus() -> None:
    inner = build_fixture_pattern_report()
    p = PatternPayload.model_validate(inner)
    assert p.confidence.sample_size >= 30


@patch("getviews_pipeline.report_pattern.fetch_pattern_wow_diff_rows")
def test_build_pattern_report_merges_wow(mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = [
        {
            "hook_type": "hook_a",
            "rank_now": 2,
            "rank_prior": 5,
            "rank_change": 3,
            "is_new": True,
            "is_dropped": False,
        }
    ]
    out = build_pattern_report(42, "q", "trend_spike", window_days=14)
    assert out["wow_diff"]["new_entries"] and out["wow_diff"]["new_entries"][0]["hook_type"] == "hook_a"
    assert out["confidence"]["window_days"] == 14
    mock_fetch.assert_called_once_with(42)


@patch(
    "getviews_pipeline.supabase_client.get_service_client",
    side_effect=ValueError("no env"),
)
def test_fetch_pattern_wow_diff_rows_fail_open(_mock: MagicMock) -> None:
    assert fetch_pattern_wow_diff_rows(1) == []


# ── L1.4: trending_sounds wire-through ─────────────────────────────────────


def test_top_sounds_payload_filters_originals_and_shapes_to_three() -> None:
    """`_top_sounds_payload` keeps non-original sounds, capped at 3, name+count only."""
    from getviews_pipeline.report_pattern_compute import _top_sounds_payload

    rows = [
        {"sound_name": "Original BGM", "usage_count": 99, "is_original_sound": True},
        {"sound_name": "Trend A", "usage_count": 12, "is_original_sound": False},
        {"sound_name": "Trend B", "usage_count": 8, "is_original_sound": False},
        {"sound_name": "Trend C", "usage_count": 6, "is_original_sound": False},
        {"sound_name": "Trend D", "usage_count": 3, "is_original_sound": False},
        {"sound_name": "", "usage_count": 1, "is_original_sound": False},
    ]
    out = _top_sounds_payload(rows)
    assert out == [
        {"name": "Trend A", "usage_count": 12},
        {"name": "Trend B", "usage_count": 8},
        {"name": "Trend C", "usage_count": 6},
    ]


def test_top_sounds_payload_empty_when_no_rows() -> None:
    from getviews_pipeline.report_pattern_compute import _top_sounds_payload

    assert _top_sounds_payload(None) == []
    assert _top_sounds_payload([]) == []


def test_build_pattern_cells_embeds_trending_sounds_in_sound_mix() -> None:
    """Sound_mix cell carries top_sounds in chart_data when supplied."""
    from getviews_pipeline.report_pattern_compute import build_pattern_cells

    ni = {"pct_original_sound": 0.62, "median_duration": 28, "median_hook_offset_norm": 0.4}
    sounds = [
        {"sound_name": "Trend A", "usage_count": 12, "is_original_sound": False},
        {"sound_name": "Trend B", "usage_count": 8, "is_original_sound": False},
    ]
    cells = build_pattern_cells(ni, trending_sounds=sounds)

    sound_cell = next(c for c in cells if c.chart_kind == "sound_mix")
    assert sound_cell.chart_data["top_sounds"] == [
        {"name": "Trend A", "usage_count": 12},
        {"name": "Trend B", "usage_count": 8},
    ]
    assert "Trend A" in sound_cell.detail


def test_build_pattern_cells_falls_back_when_no_sounds() -> None:
    """Sound_mix cell keeps legacy detail copy + empty top_sounds when absent."""
    from getviews_pipeline.report_pattern_compute import build_pattern_cells

    ni = {"pct_original_sound": 0.62, "median_duration": 28, "median_hook_offset_norm": 0.4}
    cells = build_pattern_cells(ni, trending_sounds=None)

    sound_cell = next(c for c in cells if c.chart_kind == "sound_mix")
    assert sound_cell.chart_data["top_sounds"] == []
    assert sound_cell.detail == "ước lượng từ corpus"


def test_c22_what_stalled_acceptance_invariant() -> None:
    """Either 2–3 stalled rows or [] with non-null reason (C.2.2)."""
    he = [
        {"hook_type": "a", "avg_views": 1000, "avg_completion_rate": 0.8, "sample_size": 10, "trend_direction": "rising"},
        {"hook_type": "b", "avg_views": 900, "avg_completion_rate": 0.75, "sample_size": 10, "trend_direction": "stable"},
        {"hook_type": "c", "avg_views": 800, "avg_completion_rate": 0.7, "sample_size": 10, "trend_direction": "stable"},
        {"hook_type": "d", "avg_views": 100, "avg_completion_rate": 0.1, "sample_size": 10, "trend_direction": "declining"},
        {"hook_type": "e", "avg_views": 90, "avg_completion_rate": 0.09, "sample_size": 10, "trend_direction": "declining"},
    ]
    top3 = {"a", "b", "c"}
    stalled, reason = compute_what_stalled(he, top3, baseline_views=500.0)
    if not stalled:
        assert reason
    else:
        assert 2 <= len(stalled) <= 3
        assert reason is None


def test_find_ab_pair_same_creator_best_delta() -> None:
    from getviews_pipeline.report_pattern_compute import find_ab_pair

    corpus = [
        {"creator_handle": "@alice", "hook_type": "bold_claim", "views": 50_000, "video_id": "1"},
        {"creator_handle": "alice", "hook_type": "question", "views": 5000, "video_id": "2"},
        {"creator_handle": "@bob", "hook_type": "bold_claim", "views": 100_000, "video_id": "3"},
        {"creator_handle": "@bob", "hook_type": "question", "views": 25_000, "video_id": "4"},
    ]
    pair = find_ab_pair(corpus, "bold_claim", min_delta=5)
    assert pair is not None
    assert pair.creator_handle == "@alice"
    assert pair.hit.views == 50_000
    assert pair.flop.views == 5000
    assert pair.delta == 10


def test_find_ab_pair_returns_none_below_min_ratio() -> None:
    from getviews_pipeline.report_pattern_compute import find_ab_pair

    corpus = [
        {"creator_handle": "@alice", "hook_type": "bold_claim", "views": 20_000, "video_id": "1"},
        {"creator_handle": "@alice", "hook_type": "question", "views": 5000, "video_id": "2"},
    ]
    assert find_ab_pair(corpus, "bold_claim", min_delta=5) is None


# Audit Pass-2 fix #1 — guard against zero-view flops producing fake A/B pairs.
def test_find_ab_pair_skips_zero_view_flops() -> None:
    """EnsembleData often returns ``play_count: 0`` for fresh / private
    posts. Without the guard, ``max(flop_views, 1)`` floored division
    produced misleading mega-deltas (e.g. ``5K view / 0 view = 5,000×``)
    that the FE then rendered as evidence on Pattern + StudioHero."""
    from getviews_pipeline.report_pattern_compute import find_ab_pair

    corpus = [
        {"creator_handle": "@alice", "hook_type": "bold_claim", "views": 5_000, "video_id": "1"},
        {"creator_handle": "@alice", "hook_type": "question", "views": 0, "video_id": "2"},
    ]
    # Without the guard this would return a misleading delta=5000 pair.
    assert find_ab_pair(corpus, "bold_claim", min_delta=5) is None


def test_find_ab_pair_skips_low_view_flops_under_threshold() -> None:
    """Same guard at the boundary — a flop with <100 views is treated
    as ``too noisy to be a baseline``. This filters genuinely-no-reach
    posts (e.g. fresh uploads in the first hour) without the explicit
    zero-guard test passing alone."""
    from getviews_pipeline.report_pattern_compute import find_ab_pair

    corpus = [
        {"creator_handle": "@alice", "hook_type": "bold_claim", "views": 50_000, "video_id": "1"},
        {"creator_handle": "@alice", "hook_type": "question", "views": 50, "video_id": "2"},
    ]
    assert find_ab_pair(corpus, "bold_claim", min_delta=5) is None


def test_find_ab_pair_accepts_flop_at_threshold_boundary() -> None:
    """Sanity: 100 views is the floor — at-or-above must pass."""
    from getviews_pipeline.report_pattern_compute import find_ab_pair

    corpus = [
        {"creator_handle": "@alice", "hook_type": "bold_claim", "views": 1_000, "video_id": "1"},
        {"creator_handle": "@alice", "hook_type": "question", "views": 100, "video_id": "2"},
    ]
    pair = find_ab_pair(corpus, "bold_claim", min_delta=5)
    assert pair is not None
    assert pair.delta == 10  # 1000 / 100


# ── build_top_performers_context — week math + cite-ready format ────────


def test_build_top_performers_context_emits_handle_and_views() -> None:
    """Smoke test on the new helper added in commit 94aef14 (no test
    coverage prior to Audit Pass-2)."""
    from getviews_pipeline.report_pattern_compute import (
        build_top_performers_context,
    )

    corpus = [
        {
            "creator_handle": "@alice",
            "hook_type": "bold_claim",
            "views": 1_500_000,
            "indexed_at": "2026-04-25T00:00:00+00:00",
        },
    ]
    out = build_top_performers_context(corpus, ["bold_claim"], top_n=2)
    # Citation-ready string — handle + view K/M short form
    assert "@alice" in out
    assert "1.5M" in out


def test_build_top_performers_context_handles_empty_match() -> None:
    """No matching hook_type → empty string (NOT a section header
    that misleadingly suggests "no winners found in this hook")."""
    from getviews_pipeline.report_pattern_compute import (
        build_top_performers_context,
    )

    out = build_top_performers_context(
        [{"creator_handle": "@alice", "hook_type": "story_open", "views": 100}],
        ["bold_claim"],
        top_n=2,
    )
    assert out == ""
