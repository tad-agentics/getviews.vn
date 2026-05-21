"""Boost-suspect heuristic for corpus ingest (§4.7 M1 proxy).

Shadow Phase 1: log ``would_reject_boost_suspect``. Phase 5: optional hard
reject when ``CORPUS_BOOST_HARD_REJECT=true``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

BoostAttribution = Literal[
    "unknown",
    "organic_confident",
    "suspect_low",
    "suspect_medium",
]


@dataclass(frozen=True)
class BoostPercentiles:
    """Niche or global trailing corpus percentiles for boost heuristic."""

    sample_size: int = 0
    p10_comment_rate: float = 0.001
    p25_er: float = 2.0
    p75_views: float = 10_000.0
    p90_views: float = 50_000.0
    thin: bool = True


@dataclass(frozen=True)
class BoostSuspectResult:
    attribution: BoostAttribution
    would_reject: bool
    reference_eligible: bool
    reasons: tuple[str, ...] = ()


def classify_boost_suspect(
    *,
    views: int,
    er: float,
    comments: int,
    percentiles: BoostPercentiles,
    hard_reject_enabled: bool,
) -> BoostSuspectResult:
    """Classify paid-boost / seeding skew from public ED stats only."""
    reasons: list[str] = []
    attribution: BoostAttribution = "organic_confident"
    suspect_medium = False

    comment_rate = (comments / views) if views > 0 else 0.0
    p75_views = max(float(percentiles.p75_views), 10_000.0)

    if views >= percentiles.p90_views and (
        er < percentiles.p25_er or comment_rate < percentiles.p10_comment_rate
    ):
        suspect_medium = True
        reasons.append("high_views_low_er_or_comments")

    if comments == 0 and views >= p75_views:
        suspect_medium = True
        reasons.append("zero_comments_high_views")

    if suspect_medium:
        attribution = "suspect_medium"
    elif views >= percentiles.p90_views and er < percentiles.p25_er * 1.25:
        attribution = "suspect_low"
        reasons.append("elevated_views_moderate_er")

    would_reject = hard_reject_enabled and attribution == "suspect_medium"
    reference_eligible = attribution != "suspect_medium"

    return BoostSuspectResult(
        attribution=attribution,
        would_reject=would_reject,
        reference_eligible=reference_eligible,
        reasons=tuple(reasons),
    )


def boost_percentiles_from_niche_intel(row: dict[str, Any] | None) -> BoostPercentiles:
    """Map ``niche_intelligence`` row to boost percentiles (pre-Phase-5: all rows)."""
    if not row:
        return BoostPercentiles(thin=True)
    sample = int(row.get("sample_size") or 0)
    thin = sample < 50
    return BoostPercentiles(
        sample_size=sample,
        p10_comment_rate=float(row.get("p10_comment_rate") or 0.001),
        p25_er=float(row.get("p25_er") or row.get("median_er") or 2.0),
        p75_views=float(row.get("p75_views") or row.get("median_views") or 10_000),
        p90_views=float(row.get("p90_views") or row.get("median_views") or 50_000) * 1.8,
        thin=thin,
    )
