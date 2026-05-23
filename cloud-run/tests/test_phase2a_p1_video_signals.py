"""Phase 2a.2 — video P1 pacing signals (hook_timeline + cut frequency)."""

from __future__ import annotations

from getviews_pipeline.signals.editing import extract_editing_cut_pace_outlier_signal
from getviews_pipeline.signals.hook import (
    extract_hook_pacing_cut_frequency_signal,
    extract_hook_signals,
    extract_hook_timeline_pacing_signal,
)
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest


def _niche_meta(**overrides: object) -> dict:
    base = {
        "sample_size": 80,
        "avg_transitions_per_second": 0.8,
        "p25_transitions_per_second": 0.5,
        "p75_transitions_per_second": 1.1,
    }
    base.update(overrides)
    return base


def _ctx(**overrides: object) -> dict:
    ua = {
        "hook_analysis": {
            "first_frame_type": "face",
            "hook_phrase": "test",
            "hook_type": "question",
            "hook_notes": "",
            "hook_timeline": [],
        },
        "transitions_per_second": 0.8,
    }
    base = build_diagnosis_ctx(
        user_analysis=ua,
        user_stats={"views": 5000, "engagement_rate": 3.0},
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
        niche_meta=_niche_meta(),
    )
    base.update(overrides)
    return base


def test_hook_timeline_pacing_sparse_fires_on_single_event() -> None:
    ctx = _ctx()
    ctx["user_analysis"]["hook_analysis"]["hook_timeline"] = [
        {"t": 0.4, "event": "face_enter", "note": "zoom"},
    ]
    sigs = extract_hook_timeline_pacing_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "hook_timeline_pacing_sparse"
    assert sigs[0].section_id == "hook_analysis"


def test_hook_timeline_pacing_sparse_absent_with_two_events() -> None:
    ctx = _ctx()
    ctx["user_analysis"]["hook_analysis"]["hook_timeline"] = [
        {"t": 0.2, "event": "text_overlay", "note": "hook"},
        {"t": 1.4, "event": "cut", "note": "jump"},
    ]
    assert extract_hook_timeline_pacing_signal(ctx) == []


def test_hook_pacing_cut_frequency_fires_when_slow_vs_niche() -> None:
    ctx = _ctx()
    ctx["user_analysis"]["transitions_per_second"] = 0.3
    sigs = extract_hook_pacing_cut_frequency_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "hook_pacing_cut_frequency"


def test_hook_pacing_cut_frequency_skips_when_at_niche_avg() -> None:
    ctx = _ctx()
    ctx["user_analysis"]["transitions_per_second"] = 0.8
    assert extract_hook_pacing_cut_frequency_signal(ctx) == []


def test_hook_pacing_cut_frequency_skips_thin_niche() -> None:
    ctx = _ctx(niche_meta=_niche_meta(sample_size=10))
    ctx["user_analysis"]["transitions_per_second"] = 0.2
    assert extract_hook_pacing_cut_frequency_signal(ctx) == []


def test_editing_cut_pace_outlier_slow() -> None:
    ctx = _ctx()
    ctx["user_analysis"]["transitions_per_second"] = 0.3
    sigs = extract_editing_cut_pace_outlier_signal(ctx)
    assert len(sigs) == 1
    assert sigs[0].id == "editing_cut_pace_outlier"
    assert sigs[0].section_id == "editing"
    assert "p25" in sigs[0].claim


def test_editing_cut_pace_outlier_fast() -> None:
    ctx = _ctx()
    ctx["user_analysis"]["transitions_per_second"] = 1.5
    sigs = extract_editing_cut_pace_outlier_signal(ctx)
    assert len(sigs) == 1
    assert "p75" in sigs[0].claim


def test_editing_cut_pace_outlier_in_band() -> None:
    ctx = _ctx()
    ctx["user_analysis"]["transitions_per_second"] = 0.8
    assert extract_editing_cut_pace_outlier_signal(ctx) == []


def test_editing_cut_pace_outlier_derives_p25_p75_from_avg() -> None:
    ctx = _ctx(
        niche_meta=_niche_meta(
            p25_transitions_per_second=None,
            p75_transitions_per_second=None,
            avg_transitions_per_second=1.0,
        )
    )
    ctx["user_analysis"]["transitions_per_second"] = 0.5
    sigs = extract_editing_cut_pace_outlier_signal(ctx)
    assert len(sigs) == 1


def test_manifest_includes_phase2a_p1_signal_ids() -> None:
    ctx = _ctx()
    ctx["user_analysis"]["hook_analysis"]["hook_timeline"] = [
        {"t": 0.5, "event": "text_overlay", "note": "x"},
    ]
    ctx["user_analysis"]["transitions_per_second"] = 0.3
    manifest = build_signal_manifest(ctx)
    all_ids = {s.id for lst in manifest.values() for s in lst}
    assert "hook_timeline_pacing_sparse" in all_ids
    assert "hook_pacing_cut_frequency" in all_ids
    assert "editing_cut_pace_outlier" in all_ids


def test_extract_hook_signals_includes_new_ids() -> None:
    ctx = _ctx()
    ctx["user_analysis"]["hook_analysis"]["hook_timeline"] = []
    ctx["user_analysis"]["transitions_per_second"] = 0.2
    ids = {s.id for s in extract_hook_signals(ctx)}
    assert "hook_timeline_pacing_sparse" in ids
    assert "hook_pacing_cut_frequency" in ids
