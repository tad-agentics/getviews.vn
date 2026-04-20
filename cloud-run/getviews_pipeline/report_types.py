"""§J ReportV1 pydantic models — mirror `src/lib/api-types.ts` (phase-c-plan.md)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ConfidenceStrip(BaseModel):
    sample_size: int
    window_days: int
    niche_scope: str | None = None
    freshness_hours: int
    intent_confidence: Literal["high", "medium", "low"]
    what_stalled_reason: str | None = None


class Metric(BaseModel):
    value: str
    numeric: float
    definition: str


class Lifecycle(BaseModel):
    first_seen: str
    peak: str
    momentum: Literal["rising", "plateau", "declining"]


class ContrastAgainst(BaseModel):
    pattern: str
    why_this_won: str = Field(max_length=200)


class HookFinding(BaseModel):
    rank: int
    pattern: str
    retention: Metric
    delta: Metric
    uses: int
    lifecycle: Lifecycle
    contrast_against: ContrastAgainst
    prerequisites: list[str] = Field(default_factory=list)
    insight: str = Field(max_length=200)
    evidence_video_ids: list[str] = Field(default_factory=list)


class SumStat(BaseModel):
    label: str
    value: str
    trend: str
    tone: Literal["up", "down", "neutral"]


class EvidenceCardPayload(BaseModel):
    video_id: str
    creator_handle: str
    title: str
    views: int
    retention: float
    duration_sec: int
    bg_color: str
    hook_family: str


class PatternCellPayload(BaseModel):
    title: str
    finding: str
    detail: str
    chart_kind: Literal["duration", "hook_timing", "sound_mix", "cta_bars"]
    chart_data: Any = None


class ActionCardPayload(BaseModel):
    icon: str
    title: str
    sub: str
    cta: str
    primary: bool | None = None
    route: str | None = None
    forecast: dict[str, str]


class SourceRow(BaseModel):
    kind: Literal["video", "channel", "creator", "datapoint"]
    label: str
    count: int
    sub: str


class WoWDiff(BaseModel):
    new_entries: list[dict[str, Any]] = Field(default_factory=list)
    dropped: list[dict[str, Any]] = Field(default_factory=list)
    rank_changes: list[dict[str, Any]] = Field(default_factory=list)


class PatternPayload(BaseModel):
    confidence: ConfidenceStrip
    wow_diff: WoWDiff | None = None
    tldr: dict[str, Any]
    findings: list[HookFinding]
    what_stalled: list[HookFinding]
    evidence_videos: list[EvidenceCardPayload]
    patterns: list[PatternCellPayload]
    actions: list[ActionCardPayload]
    sources: list[SourceRow]
    related_questions: list[str]
    subreports: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _what_stalled_invariant(self) -> PatternPayload:
        """§5 non-negotiable: either 2–3 stalled patterns OR empty with reason.

        A real Gemini call that returns `what_stalled=[]` without setting
        `confidence.what_stalled_reason` is a model hallucination — reject
        at the schema boundary rather than silently render a missing section.
        The fixture path sets reason explicitly (see report_pattern.py).
        """
        n = len(self.what_stalled)
        if n == 0 and not self.confidence.what_stalled_reason:
            raise ValueError(
                "what_stalled invariant violated: empty list requires "
                "confidence.what_stalled_reason to be set"
            )
        if n > 3:
            raise ValueError(
                f"what_stalled invariant violated: at most 3 entries allowed, got {n}"
            )
        return self


class IdeaBlockPayload(BaseModel):
    id: str
    title: str
    tag: str
    angle: str
    why_works: str
    evidence_video_ids: list[str]
    hook: str
    slides: list[dict[str, Any]]
    metric: dict[str, str]
    prerequisites: list[str]
    confidence: dict[str, int]
    style: str


class IdeasPayload(BaseModel):
    confidence: ConfidenceStrip
    lead: str
    ideas: list[IdeaBlockPayload]
    style_cards: list[dict[str, Any]]
    stop_doing: list[dict[str, str]]
    actions: list[ActionCardPayload]
    sources: list[SourceRow]
    related_questions: list[str]
    variant: Literal["standard", "hook_variants"]


class TimingPayload(BaseModel):
    confidence: ConfidenceStrip
    top_window: dict[str, Any]
    top_3_windows: list[dict[str, Any]]
    lowest_window: dict[str, str]
    grid: list[list[float]]
    variance_note: dict[str, str]
    fatigue_band: dict[str, Any] | None = None
    actions: list[ActionCardPayload]
    sources: list[SourceRow]
    related_questions: list[str]


class GenericPayload(BaseModel):
    confidence: ConfidenceStrip
    off_taxonomy: dict[str, Any]
    narrative: dict[str, Any]
    evidence_videos: list[EvidenceCardPayload]
    sources: list[SourceRow]
    related_questions: list[str]


class ReportV1(BaseModel):
    kind: Literal["pattern", "ideas", "timing", "generic"]
    report: PatternPayload | IdeasPayload | TimingPayload | GenericPayload


def validate_and_store_report(kind: str, report: dict[str, Any]) -> dict[str, Any]:
    """Validate inner report dict and return full §J envelope for JSONB storage."""
    k: Literal["pattern", "ideas", "timing", "generic"] = (
        kind if kind in ("pattern", "ideas", "timing", "generic") else "generic"
    )
    if k == "pattern":
        PatternPayload.model_validate(report)
    elif k == "ideas":
        IdeasPayload.model_validate(report)
    elif k == "timing":
        TimingPayload.model_validate(report)
    else:
        GenericPayload.model_validate(report)
    return {"kind": k, "report": report}


def validate_pattern_payload(payload: dict[str, Any]) -> PatternPayload:
    return PatternPayload.model_validate(payload)
