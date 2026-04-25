"""Wave 5+ Phase 2 — thin-niche quota multiplier tests.

Pins:

* ``compute_thin_niche_multiplier`` — boundary cases (at-target,
  over-target, empty-niche), linear interpolation in between, and the
  defensive-config fallbacks (target ≤ 0, max_multiplier ≤ 1.0).
* ``apply_thin_niche_multiplier`` — integer rounding semantics, hard
  cap, never returns < 1.
* ``_fetch_niche_counts_sync`` — happy-path aggregation + fail-open
  on DB error.
* End-to-end allocation — given a mocked corpus snapshot, verify the
  thinnest niches receive the highest vpn allocation and rich niches
  stay near the base.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from getviews_pipeline.corpus_ingest import (
    BATCH_VIDEOS_PER_NICHE,
    CORPUS_TARGET_PER_NICHE,
    THIN_NICHE_MAX_MULTIPLIER,
    _fetch_niche_counts_sync,
    apply_thin_niche_multiplier,
    compute_thin_niche_multiplier,
)

# ── compute_thin_niche_multiplier — boundary + interpolation ─────────


def test_multiplier_caps_at_1_when_at_target() -> None:
    """At target → no boost. The richest niches don't get extra ED
    spend just because the multiplier exists."""
    assert compute_thin_niche_multiplier(200, target=200) == pytest.approx(1.0)


def test_multiplier_caps_at_1_when_above_target() -> None:
    """Above target — gap clamps to 0, multiplier stays at 1.0."""
    assert compute_thin_niche_multiplier(500, target=200) == pytest.approx(1.0)


def test_multiplier_hits_max_when_empty() -> None:
    """Empty niche → max_multiplier (gap fraction = 1.0)."""
    assert compute_thin_niche_multiplier(0, target=200, max_multiplier=3.0) == pytest.approx(3.0)


def test_multiplier_interpolates_linearly() -> None:
    """At 50% of target with 3× cap: 1 + 2*0.5 = 2.0."""
    assert compute_thin_niche_multiplier(100, target=200, max_multiplier=3.0) == pytest.approx(2.0)


def test_multiplier_at_25_pct_of_target() -> None:
    """At 25% of target with 3× cap: gap=0.75, mult = 1 + 2*0.75 = 2.5."""
    assert compute_thin_niche_multiplier(50, target=200, max_multiplier=3.0) == pytest.approx(2.5)


def test_multiplier_negative_count_treated_as_empty() -> None:
    """Negative input shouldn't push multiplier above max — clamps to
    empty (gap fraction caps at 1.0)."""
    assert compute_thin_niche_multiplier(-10, target=200, max_multiplier=3.0) == pytest.approx(3.0)


def test_multiplier_returns_1_on_zero_target() -> None:
    """Defensive: misconfig (target=0) returns 1.0 instead of dividing
    by zero or going wild."""
    assert compute_thin_niche_multiplier(50, target=0) == 1.0


def test_multiplier_returns_1_when_max_is_1_or_less() -> None:
    """Defensive: max_multiplier ≤ 1.0 means thin-niche boost is
    effectively disabled — return 1.0 regardless of count."""
    assert compute_thin_niche_multiplier(0, max_multiplier=1.0) == 1.0
    assert compute_thin_niche_multiplier(0, max_multiplier=0.5) == 1.0


# ── apply_thin_niche_multiplier — int math + hard cap ────────────────


def test_apply_multiplier_rounds_to_int() -> None:
    assert apply_thin_niche_multiplier(10, 1.5) == 15
    # 10 * 1.16 = 11.6 → rounds to 12.
    assert apply_thin_niche_multiplier(10, 1.16) == 12


def test_apply_multiplier_never_below_1() -> None:
    """Even with base 0 + multiplier 0, must return at least 1 — a
    misconfig should still ingest something rather than skip the niche."""
    assert apply_thin_niche_multiplier(0, 0.0) == 1


def test_apply_multiplier_treats_below_1_as_1() -> None:
    """Multiplier < 1 doesn't shrink the base — base_vpn is the floor.
    Prevents a future tweak from accidentally starving rich niches."""
    assert apply_thin_niche_multiplier(10, 0.5) == 10


def test_apply_multiplier_respects_hard_cap() -> None:
    """Hard cap prevents a 5× misconfig from overspending ED."""
    assert apply_thin_niche_multiplier(10, 5.0, hard_cap=30) == 30
    assert apply_thin_niche_multiplier(10, 2.5, hard_cap=30) == 25


def test_apply_multiplier_no_cap_passes_through() -> None:
    assert apply_thin_niche_multiplier(10, 5.0, hard_cap=None) == 50


# ── _fetch_niche_counts_sync — aggregation + fail-open ───────────────


def _mock_client(rows: list[dict] | None, *, raise_on_execute: bool = False) -> MagicMock:
    chain = MagicMock()
    chain.select.return_value = chain
    chain.not_.is_.return_value = chain
    chain.limit.return_value = chain
    if raise_on_execute:
        chain.execute.side_effect = RuntimeError("DB blip")
    else:
        chain.execute.return_value = SimpleNamespace(data=rows)
    client = MagicMock()
    client.table.return_value = chain
    return client


def test_fetch_niche_counts_aggregates_correctly() -> None:
    rows = [
        {"niche_id": 1}, {"niche_id": 1}, {"niche_id": 1},  # 3
        {"niche_id": 2}, {"niche_id": 2},                    # 2
        {"niche_id": 7},                                      # 1
    ]
    counts = _fetch_niche_counts_sync(_mock_client(rows))
    assert counts == {1: 3, 2: 2, 7: 1}


def test_fetch_niche_counts_drops_null_niche_id() -> None:
    rows = [{"niche_id": 1}, {"niche_id": None}, {"niche_id": 1}]
    counts = _fetch_niche_counts_sync(_mock_client(rows))
    assert counts == {1: 2}


def test_fetch_niche_counts_returns_empty_on_db_error() -> None:
    """Fail-open — batch then runs with uniform default (pre-Phase-2
    behaviour) instead of crashing."""
    counts = _fetch_niche_counts_sync(_mock_client(None, raise_on_execute=True))
    assert counts == {}


def test_fetch_niche_counts_returns_empty_on_no_rows() -> None:
    counts = _fetch_niche_counts_sync(_mock_client([]))
    assert counts == {}


# ── End-to-end allocation snapshot ───────────────────────────────────


def test_allocation_snapshot_thinnest_gets_most_videos() -> None:
    """Pin the prioritization invariant: niche with the lowest current
    count gets the highest vpn allocation, niche at/above target gets
    the base. Uses live module constants so a tweak to the defaults
    propagates here too."""
    base = BATCH_VIDEOS_PER_NICHE
    target = CORPUS_TARGET_PER_NICHE
    max_mult = THIN_NICHE_MAX_MULTIPLIER
    hard_cap = int(base * max_mult)

    cases = [
        ("rich",  target),
        ("mid",   target // 2),
        ("thin",  target // 10),
        ("empty", 0),
    ]
    allocations = {
        name: apply_thin_niche_multiplier(
            base, compute_thin_niche_multiplier(count), hard_cap=hard_cap,
        )
        for name, count in cases
    }
    # Strictly monotone: thinner = more videos.
    assert allocations["empty"] > allocations["thin"]
    assert allocations["thin"] > allocations["mid"]
    assert allocations["mid"] > allocations["rich"]
    # Rich stays at base, empty hits the cap.
    assert allocations["rich"] == base
    assert allocations["empty"] == hard_cap
