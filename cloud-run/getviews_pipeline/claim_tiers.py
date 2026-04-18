"""Claim-tier thresholds — single source of truth for "is this claim statistically valid?"

Each claim the synthesis prompt makes has a different minimum sample requirement.
Before viral-pattern-fingerprint + comment-sentiment + thumbnail-analysis shipped
the pipeline had one global threshold (SPARSE_THRESHOLD = 20); after those
features the bar for each output layer diverged.

This module centralises those thresholds so:
  • /admin/corpus-health can report per-niche which tiers pass
  • Callers can gate injection consistently ("is this tier valid?")
  • Thresholds are tunable in one place as the corpus grows

Design: artifacts/docs/corpus-health.md

The thresholds themselves are informed by statistical reasoning, not convention:
  - `reference_pool`: 5 videos so we can show 3 references without bottom-scrape
  - `basic_citation`: 20 — matches legacy SPARSE_THRESHOLD, the "feels
    representative" bar for generic niche talk
  - `niche_norms`: 30 — binary features (pct_face, has_cta) need ~30 samples
    for ±10% precision; below this they're directional at best
  - `hook_effectiveness`: 50 — 14 hook types × ≥5/bucket = 70 ideal, relaxed
    to 50 (assumes uneven distribution)
  - `trend_delta`: 100 — two weeks × ≥50 instances per week window
  - `pattern_spread`: 10 per pattern (not per niche) — a "pattern" with
    1-2 instances is a coincidence, not a signal
  - `cross_niche_spread`: 10 + must appear in ≥ 2 niches

These are calibration defaults. A later PR can add per-niche override via
niche_taxonomy when empirical data shows some niches need higher/lower bars.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ClaimTierName = Literal[
    "reference_pool",
    "basic_citation",
    "niche_norms",
    "hook_effectiveness",
    "trend_delta",
    "pattern_spread",
    "cross_niche_spread",
]

CLAIM_TIERS: dict[ClaimTierName, int] = {
    "reference_pool":     5,
    "basic_citation":     20,
    "niche_norms":        30,
    "hook_effectiveness": 50,
    "trend_delta":        100,
    "pattern_spread":     10,
    "cross_niche_spread": 10,
}

# Minimum instances per hook bucket before we cite a per-hook ER.
# 14 hook types × 5 per bucket = 70 total; we gate at 5 per bucket locally.
HOOK_EFFECTIVENESS_MIN_PER_BUCKET = 5

# A pattern must have this many instances before "lan sang N ngách" fires.
PATTERN_SPREAD_MIN_INSTANCES = CLAIM_TIERS["pattern_spread"]

# A pattern must touch this many niches before we call it "cross-niche".
PATTERN_SPREAD_MIN_NICHES = 2


@dataclass(frozen=True)
class ClaimTierFlags:
    """Per-niche pass/fail for each claim tier.

    Serialised into /admin/corpus-health responses so an operator can see
    at a glance which tiers are safe to make claims at today.
    """
    reference_pool: bool
    basic_citation: bool
    niche_norms: bool
    hook_effectiveness: bool
    trend_delta: bool

    def asdict(self) -> dict[str, bool]:
        return {
            "reference_pool":     self.reference_pool,
            "basic_citation":     self.basic_citation,
            "niche_norms":        self.niche_norms,
            "hook_effectiveness": self.hook_effectiveness,
            "trend_delta":        self.trend_delta,
        }

    @property
    def highest_passing_tier(self) -> str:
        """Return the most demanding tier this niche passes today."""
        for name in ("trend_delta", "hook_effectiveness", "niche_norms",
                     "basic_citation", "reference_pool"):
            if getattr(self, name):
                return name
        return "none"


def flags_for_count(videos_30d: int) -> ClaimTierFlags:
    """Compute which tiers this niche currently passes given videos_30d.

    Tiers are strictly nested (passing a higher tier implies the lower ones).
    """
    return ClaimTierFlags(
        reference_pool=     videos_30d >= CLAIM_TIERS["reference_pool"],
        basic_citation=     videos_30d >= CLAIM_TIERS["basic_citation"],
        niche_norms=        videos_30d >= CLAIM_TIERS["niche_norms"],
        hook_effectiveness= videos_30d >= CLAIM_TIERS["hook_effectiveness"],
        trend_delta=        videos_30d >= CLAIM_TIERS["trend_delta"],
    )


def should_cite_hook_effectiveness(total_samples: int) -> bool:
    """True if total hook-bucket samples clear the hook_effectiveness tier."""
    return total_samples >= CLAIM_TIERS["hook_effectiveness"]


def should_cite_niche_norms(sample_size: int | None) -> bool:
    """True if niche_intelligence has enough samples for its percentages
    to be anything better than directional."""
    if sample_size is None:
        return False
    return sample_size >= CLAIM_TIERS["niche_norms"]


def should_cite_pattern_spread(
    instance_count_week: int, niche_spread_count: int,
) -> bool:
    """True if a pattern has enough instances + niche reach to claim spread.

    Gate prevents "pattern X lan sang 2 ngách!" firing on a 2-instance
    pattern that coincidentally appeared once in each niche.
    """
    return (
        instance_count_week >= PATTERN_SPREAD_MIN_INSTANCES
        and niche_spread_count >= PATTERN_SPREAD_MIN_NICHES
    )


__all__ = [
    "CLAIM_TIERS",
    "ClaimTierFlags",
    "ClaimTierName",
    "HOOK_EFFECTIVENESS_MIN_PER_BUCKET",
    "PATTERN_SPREAD_MIN_INSTANCES",
    "PATTERN_SPREAD_MIN_NICHES",
    "flags_for_count",
    "should_cite_hook_effectiveness",
    "should_cite_niche_norms",
    "should_cite_pattern_spread",
]
