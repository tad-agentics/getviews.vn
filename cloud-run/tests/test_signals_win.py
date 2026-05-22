"""Wave 1 W1-6 — Win path W0 signals (tier_gate=hit)."""

from __future__ import annotations

from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest
from getviews_pipeline.signals.win import (
    extract_win_er_above_niche_p75_signal,
    extract_win_hook_aligns_niche_top_signal,
    extract_win_signals,
)


def _hit_ctx(**overrides: object) -> dict:
    base = build_diagnosis_ctx(
        user_analysis={
            "hook_analysis": {"hook_type": "curiosity_gap"},
        },
        user_stats={"views": 120_000, "engagement_rate": 5.2},
        reference_videos=[],
        channel_context=None,
        performance_tier="hit",
        niche_meta={
            "sample_size": 80,
            "median_er": 3.5,
            "hook_distribution": {"curiosity_gap": 40, "pov": 30},
        },
    )
    base.update(overrides)
    return base


def test_win_signals_empty_when_not_hit_tier() -> None:
    ctx = _hit_ctx(performance_tier="flop")
    assert extract_win_signals(ctx) == []


def test_win_er_above_niche_p75_fires_on_hit() -> None:
    sigs = extract_win_er_above_niche_p75_signal(_hit_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "win_er_above_niche_p75"
    assert sigs[0].salience >= 0.85


def test_win_hook_aligns_niche_top_fires_on_hit() -> None:
    sigs = extract_win_hook_aligns_niche_top_signal(_hit_ctx())
    assert len(sigs) == 1
    assert sigs[0].id == "win_hook_aligns_niche_top"


def test_win_signals_in_manifest_on_hit() -> None:
    manifest = build_signal_manifest(_hit_ctx())
    ids = {s.id for lst in manifest.values() for s in lst}
    assert "win_er_above_niche_p75" in ids
    assert "win_hook_aligns_niche_top" in ids


def test_win_signals_absent_on_flop_manifest() -> None:
    manifest = build_signal_manifest(_hit_ctx(performance_tier="average"))
    ids = {s.id for lst in manifest.values() for s in lst}
    assert "win_er_above_niche_p75" not in ids
    assert "win_hook_aligns_niche_top" not in ids
