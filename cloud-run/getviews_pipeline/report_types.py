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
    thumbnail_url: str | None = None


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


class NicheInsight(BaseModel):
    """Layer 0 weekly-computed niche insight, attached to Pattern + Ideas
    report payloads so the UI can surface ``execution_tip`` as the
    "what to do next" slot and ``insight_text`` as preamble context.

    Sourced from ``niche_insights`` table via ``fetch_niche_insight``;
    nullable on the parent payload because the Layer 0 cron may not
    have run yet for a given niche / week (new niches, sparse corpus,
    or post-cron-failure state).
    """
    insight_text: str | None = None
    execution_tip: str | None = None
    top_formula_hook: str | None = None
    top_formula_format: str | None = None
    week_of: str | None = None              # ISO date string
    staleness_risk: Literal["LOW", "MODERATE", "HIGH"] | None = None


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
    # 2026-05-10 — Wave 2 PR #1 (state-of-corpus Appendix B Gap 2):
    # Layer 0 niche_insights injection. Optional because the cron may
    # not have populated a row for this niche yet.
    niche_insight: NicheInsight | None = None

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
    # 2026-05-10 — Wave 2 PR #1: Layer 0 injection (same as PatternPayload).
    niche_insight: NicheInsight | None = None


# Named alias for ``CalendarSlot.kind`` — intentionally distinct from
# ``ReportV1.kind`` even though the two share some literal values. Making
# the alias visible in type signatures prevents the kind-vs-kind trap
# where a ``ReportV1`` could accidentally be passed where a slot kind is
# expected, or vice versa. The wire field name stays ``kind`` so stored
# JSONB payloads + the TypeScript counterpart don't drift.
CalendarSlotKind = Literal["pattern", "ideas", "timing", "repost"]


class CalendarSlot(BaseModel):
    """One day's suggested post slot in a Timing content-calendar view.

    Added 2026-04-22 to absorb the ``content_calendar`` intent into
    ``TimingPayload`` without a new envelope kind. Empty ``calendar_slots``
    means the session is a pure timing query (heatmap only, no plan).

    NB: ``kind`` here is a slot-type classifier, NOT the ``ReportV1.kind``
    discriminator. Share no type, just the field name (wire-level contract).
    """

    day_idx: int = Field(ge=0, le=6)  # 0 = Thứ 2 … 6 = Chủ nhật
    day: str                          # pre-formatted Vietnamese label e.g. "Thứ 4"
    suggested_time: str = Field(max_length=12)  # "20:00"
    kind: CalendarSlotKind
    title: str = Field(max_length=120)          # "Hook cảm xúc mới"
    rationale: str = Field(max_length=240)      # why this slot got picked


class TimingPayload(BaseModel):
    confidence: ConfidenceStrip
    top_window: dict[str, Any]
    top_3_windows: list[dict[str, Any]]
    lowest_window: dict[str, str]
    grid: list[list[float]]
    variance_note: dict[str, str]
    fatigue_band: dict[str, Any] | None = None
    # New 2026-04-22: populated when the intent is content_calendar (or
    # when the query contains scheduling keywords). Empty for pure timing
    # queries — the frontend hides the calendar strip in that case.
    calendar_slots: list[CalendarSlot] = Field(default_factory=list, max_length=7)
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


# ─── Lifecycle template (2026-04-22 — serves format_lifecycle_optimize /
# fatigue / subniche_breakdown; see artifacts/docs/report-template-prd-
# lifecycle.md). Replaces the pattern force-fit for these 3 intents.
# Discriminated by ``mode`` so a single template renders all three queries
# through one shared cell/pill/bar primitive.


LifecycleMode = Literal["format", "hook_fatigue", "subniche"]
LifecycleStage = Literal["rising", "peak", "plateau", "declining"]


class LifecycleCell(BaseModel):
    """One ranked entity in the lifecycle rail.

    Shape reuses the ``stage`` + ``reach_delta_pct`` + ``health_score``
    triad across all three modes so the frontend has one renderer. Mode-
    specific fields are optional (``retention_pct`` for format mode,
    ``instance_count`` for subniche mode).
    """

    name: str = Field(max_length=120)  # "Short-form 15-30s" / "Ingredient deep-dive"
    stage: LifecycleStage
    reach_delta_pct: float            # +28.0 / -12.0 (raw percentage points)
    health_score: int = Field(ge=0, le=100)
    retention_pct: float | None = None        # None in subniche mode
    instance_count: int | None = None         # None in pure-format mode
    insight: str = Field(max_length=240)


class RefreshMove(BaseModel):
    """Short tactic for refreshing a declining/plateau entity."""

    title: str = Field(max_length=120)
    detail: str = Field(max_length=280)
    effort: Literal["low", "medium", "high"]


class LifecyclePayload(BaseModel):
    confidence: ConfidenceStrip
    mode: LifecycleMode
    subject_line: str = Field(max_length=240)
    cells: list[LifecycleCell] = Field(min_length=1, max_length=12)
    refresh_moves: list[RefreshMove] = Field(default_factory=list, max_length=4)
    actions: list[ActionCardPayload]
    sources: list[SourceRow]
    related_questions: list[str]

    @model_validator(mode="after")
    def _refresh_moves_only_for_declining_or_plateau(self) -> LifecyclePayload:
        """Honest invariant: rising/peak cells should not carry refresh
        prescriptions. If every cell is healthy there's nothing to refresh,
        and emitting ``refresh_moves`` anyway would ship unsolicited advice.
        """
        if not self.refresh_moves:
            return self
        has_weak = any(
            c.stage in ("declining", "plateau") for c in self.cells
        )
        if not has_weak:
            raise ValueError(
                "lifecycle invariant: refresh_moves present but no cell is "
                "declining or plateau — nothing to refresh"
            )
        return self


# ── Diagnostic template (2026-04-22) ──────────────────────────────────────
#
# Serves exactly ``own_flop_no_url`` — "my last video flopped and I don't
# have the link." Reference design is Claude Chat's Report 4 (VIDEO
# DIAGNOSIS) but scoped down: no per-category numeric score because we
# don't have the video itself, only the user's self-reported symptoms.
# See ``artifacts/docs/report-template-prd-diagnostic.md``.

DiagnosticVerdict = Literal[
    "likely_issue",
    "possible_issue",
    "unclear",
    "probably_fine",
]


class DiagnosticCategory(BaseModel):
    """One of 5 fixed failure-mode categories with a confidence-weighted verdict.

    ``fix_preview`` is intentionally optional: when ``verdict`` is
    ``probably_fine`` there's nothing to fix, so the UI can hide the
    line rather than render a placeholder.
    """

    name: str = Field(max_length=80)
    verdict: DiagnosticVerdict
    finding: str = Field(max_length=280)
    fix_preview: str | None = Field(default=None, max_length=240)


class DiagnosticPrescription(BaseModel):
    priority: Literal["P1", "P2", "P3"]
    action: str = Field(max_length=160)
    impact: str = Field(max_length=160)
    effort: Literal["low", "medium", "high"]


def _default_paste_link_cta() -> dict[str, str]:
    return {
        "title": "Có link video? Mở /app/video để chấm điểm chính xác từng phần.",
        "route": "/app/video",
    }


class DiagnosticPayload(BaseModel):
    """URL-less flop diagnostic payload.

    Invariant enforced below (``_no_probably_fine_without_fix_exclusion``):
    a category marked ``probably_fine`` must not carry a ``fix_preview``.
    The other direction is optional — ``unclear`` / ``possible_issue`` can
    omit ``fix_preview`` when the model isn't confident enough to suggest
    a tactic.

    The ``min_length=5 max_length=5`` on ``categories`` is deliberate —
    the 5 categories (Hook / Pacing / CTA / Sound / Caption+Hashtag) are
    a hard contract the frontend pins by position, not by name.
    """

    confidence: ConfidenceStrip
    framing: str = Field(max_length=240)
    categories: list[DiagnosticCategory] = Field(min_length=5, max_length=5)
    prescriptions: list[DiagnosticPrescription] = Field(min_length=1, max_length=3)
    paste_link_cta: dict[str, str] = Field(default_factory=_default_paste_link_cta)
    sources: list[SourceRow]
    related_questions: list[str]

    @model_validator(mode="after")
    def _no_probably_fine_with_fix(self) -> "DiagnosticPayload":
        for c in self.categories:
            if c.verdict == "probably_fine" and c.fix_preview:
                raise ValueError(
                    "diagnostic invariant: probably_fine category must not "
                    f"carry fix_preview (category {c.name!r})"
                )
        return self


ReportKind = Literal["pattern", "ideas", "timing", "generic", "lifecycle", "diagnostic"]
_REPORT_KINDS: frozenset[str] = frozenset(
    {"pattern", "ideas", "timing", "generic", "lifecycle", "diagnostic"}
)


class ReportV1(BaseModel):
    kind: ReportKind
    report: (
        PatternPayload
        | IdeasPayload
        | TimingPayload
        | GenericPayload
        | LifecyclePayload
        | DiagnosticPayload
    )


def validate_and_store_report(kind: str, report: dict[str, Any]) -> dict[str, Any]:
    """Validate inner report dict and return full §J envelope for JSONB storage."""
    k: ReportKind = kind if kind in _REPORT_KINDS else "generic"  # type: ignore[assignment]
    if k == "pattern":
        PatternPayload.model_validate(report)
    elif k == "ideas":
        IdeasPayload.model_validate(report)
    elif k == "timing":
        TimingPayload.model_validate(report)
    elif k == "lifecycle":
        LifecyclePayload.model_validate(report)
    elif k == "diagnostic":
        DiagnosticPayload.model_validate(report)
    else:
        GenericPayload.model_validate(report)
    return {"kind": k, "report": report}


def validate_pattern_payload(payload: dict[str, Any]) -> PatternPayload:
    return PatternPayload.model_validate(payload)
