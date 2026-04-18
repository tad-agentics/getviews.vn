"""Unit tests for claim_tiers — the "is this claim statistically valid?" gate."""

from __future__ import annotations

from getviews_pipeline.claim_tiers import (
    CLAIM_TIERS,
    flags_for_count,
    should_cite_hook_effectiveness,
    should_cite_niche_norms,
    should_cite_pattern_spread,
)


# ── flags_for_count ────────────────────────────────────────────────────────


def test_flags_empty_corpus_passes_nothing() -> None:
    f = flags_for_count(0)
    assert f.reference_pool is False
    assert f.basic_citation is False
    assert f.niche_norms is False
    assert f.hook_effectiveness is False
    assert f.trend_delta is False
    assert f.highest_passing_tier == "none"


def test_flags_tiny_corpus_passes_reference_pool_only() -> None:
    f = flags_for_count(10)  # >= reference_pool (5), < basic_citation (20)
    assert f.reference_pool is True
    assert f.basic_citation is False
    assert f.highest_passing_tier == "reference_pool"


def test_flags_typical_niche_at_alpha() -> None:
    # 25 videos — a weak-alpha niche. Passes basic_citation, misses niche_norms.
    f = flags_for_count(25)
    assert f.reference_pool is True
    assert f.basic_citation is True
    assert f.niche_norms is False
    assert f.hook_effectiveness is False
    assert f.highest_passing_tier == "basic_citation"


def test_flags_at_current_corpus_average() -> None:
    # ~33 videos/niche (current 700/21). Just clears niche_norms threshold.
    f = flags_for_count(33)
    assert f.basic_citation is True
    assert f.niche_norms is True
    assert f.hook_effectiveness is False
    assert f.highest_passing_tier == "niche_norms"


def test_flags_beta_ready() -> None:
    # 60 videos — passes niche_norms + hook_effectiveness, misses trend_delta.
    f = flags_for_count(60)
    assert f.niche_norms is True
    assert f.hook_effectiveness is True
    assert f.trend_delta is False
    assert f.highest_passing_tier == "hook_effectiveness"


def test_flags_production_ready() -> None:
    f = flags_for_count(250)
    assert all([
        f.reference_pool, f.basic_citation, f.niche_norms,
        f.hook_effectiveness, f.trend_delta,
    ])
    assert f.highest_passing_tier == "trend_delta"


def test_flags_exactly_at_threshold() -> None:
    # Each threshold is inclusive — hitting exactly N passes.
    assert flags_for_count(CLAIM_TIERS["reference_pool"]).reference_pool is True
    assert flags_for_count(CLAIM_TIERS["basic_citation"]).basic_citation is True
    assert flags_for_count(CLAIM_TIERS["niche_norms"]).niche_norms is True
    assert flags_for_count(CLAIM_TIERS["hook_effectiveness"]).hook_effectiveness is True
    assert flags_for_count(CLAIM_TIERS["trend_delta"]).trend_delta is True


# ── should_cite_* helpers ──────────────────────────────────────────────────


def test_should_cite_hook_effectiveness() -> None:
    assert should_cite_hook_effectiveness(0) is False
    assert should_cite_hook_effectiveness(49) is False
    assert should_cite_hook_effectiveness(50) is True
    assert should_cite_hook_effectiveness(500) is True


def test_should_cite_niche_norms_none_is_false() -> None:
    assert should_cite_niche_norms(None) is False


def test_should_cite_niche_norms_thresholds() -> None:
    assert should_cite_niche_norms(0) is False
    assert should_cite_niche_norms(29) is False
    assert should_cite_niche_norms(30) is True
    assert should_cite_niche_norms(500) is True


def test_should_cite_pattern_spread_requires_both() -> None:
    # 10 instances but only 1 niche → not cross-niche spread
    assert should_cite_pattern_spread(10, 1) is False
    # 2 niches but only 3 instances → coincidence, not spread
    assert should_cite_pattern_spread(3, 2) is False
    # Both thresholds met
    assert should_cite_pattern_spread(10, 2) is True
    assert should_cite_pattern_spread(50, 5) is True


def test_should_cite_pattern_spread_zero_instances() -> None:
    assert should_cite_pattern_spread(0, 5) is False
