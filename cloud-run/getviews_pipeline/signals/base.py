from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

EvidenceType = Literal[
    "aweme_id",
    "niche_norms_pct",
    "user_analysis_field",
    "channel_field",
]


@dataclass(frozen=True)
class Evidence:
    type: EvidenceType
    quote: str
    location: str | None = None


@dataclass
class Signal:
    id: str
    section_id: str
    taxonomy_ref: str
    salience: float
    claim: str
    evidence: list[Evidence] = field(default_factory=list)
    suggested_fix: str | None = None


class SignalExtractor(Protocol):
    """Pure function: diagnosis ctx dict in → signals out."""

    def __call__(self, ctx: dict) -> list[Signal]: ...
