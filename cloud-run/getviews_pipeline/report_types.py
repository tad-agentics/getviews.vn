"""§J ReportV1 pydantic models — mirror `src/lib/api-types.ts` (phase-c-plan.md)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

SourceEntry = Literal["trends", "trends_douyin", "composer", "evidence", "intent_cta"]
_SOURCE_ENTRIES: frozenset[str] = frozenset(
    {"trends", "trends_douyin", "composer", "evidence", "intent_cta"}
)


def normalize_source_entry(value: str | None) -> SourceEntry | None:
    """§4.6 — allowlisted handoff attribution for turn-1 video payloads."""
    if value and value in _SOURCE_ENTRIES:
        return value  # type: ignore[return-value]
    return None

# ``report_compare`` only pulls ``voice_lint`` (stdlib-only) at module load —
# its diagnosis-pipeline imports are function-local — so this is cycle-safe.
from getviews_pipeline.report_compare import ComparePayload


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
    cultural_framing: str | None = None
    creator_count: int | None = None
    # Narrative upgrade — all optional; absent = graceful fallback to `insight`
    narrative: str | None = Field(default=None, max_length=500)
    why_it_works: str | None = Field(default=None, max_length=350)
    micro_pattern: str | None = Field(default=None, max_length=220)


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
    breakout_ratio: float | None = None  # display: DB breakout_ratio or breakout_multiplier
    engagement_rate: float | None = None
    days_ago: int | None = None
    tiktok_url: str | None = None


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


class OutlierStory(BaseModel):
    """Single highest-breakout row in the pattern window (corpus social proof)."""

    creator_handle: str
    views: int
    breakout_ratio: float  # e.g. 340 → "340× median" in copy
    hook_type: str  # Vietnamese label
    days_ago: int | None = None


class ABPairVideo(BaseModel):
    video_id: str
    tiktok_url: str | None = None
    views: int
    hook_type: str  # Vietnamese label
    days_ago: int | None = None


class PatternABPair(BaseModel):
    """Same-creator hit/flop from corpus — only hook_type differs."""

    creator_handle: str
    hit: ABPairVideo
    flop: ABPairVideo
    delta: int  # hit.views / flop.views, e.g. 28
    hook_contrast: str


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
    outlier_story: OutlierStory | None = None
    cross_pattern_synthesis: list[str] = Field(default_factory=list)
    ab_pair: PatternABPair | None = None

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
    # 2026-05-10 — Wave 2 PR #2: fields for the "5 video tiếp theo"
    # content-calendar reframe. Defaults keep back-compat with existing
    # fixtures; the builder fills them structurally until the Gemini
    # prompt upgrade (PR #3) emits the richer Vietnamese variants.
    rank: int = 0                                                    # 1..5; 0 = unranked (legacy)
    opening_line: str = ""                                           # 6–12 word VN example of first spoken line
    lifecycle_stage: Literal["early", "peak", "decline"] | None = None


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
    # Only when classify_variance says sparse (lift < 1.3): time slot is not a lever.
    contrarian_note: str | None = None
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
    # PR-3 of the video-as-template migration replaced /app/video with
    # /app/answer; the FE composer detects pasted URLs and creates a
    # video_diagnosis session there.
    return {
        "title": "Có link video? Dán vào composer để chấm điểm chính xác từng phần.",
        "route": "/app/answer",
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

    ``niche_execution_tip`` is the Wave 3 "peer expert, not product pitch"
    callout — the current week's Layer 0 execution tip for this niche
    (from ``niche_insights.execution_tip``). Optional because the tip
    table may be empty for sparse niches; the frontend hides the surface
    when null. Max 240 chars to match the single-sentence Layer 0 voice.
    """

    confidence: ConfidenceStrip
    framing: str = Field(max_length=240)
    categories: list[DiagnosticCategory] = Field(min_length=5, max_length=5)
    prescriptions: list[DiagnosticPrescription] = Field(min_length=1, max_length=3)
    paste_link_cta: dict[str, str] = Field(default_factory=_default_paste_link_cta)
    sources: list[SourceRow]
    related_questions: list[str]
    niche_execution_tip: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def _no_probably_fine_with_fix(self) -> DiagnosticPayload:
        for c in self.categories:
            if c.verdict == "probably_fine" and c.fix_preview:
                raise ValueError(
                    "diagnostic invariant: probably_fine category must not "
                    f"carry fix_preview (category {c.name!r})"
                )
        return self


# ── Video payload (mirrors src/lib/api-types.ts VideoAnalyzeResponse) ─────
#
# The on-screen video diagnosis report — KPI strip + retention curve +
# hook phases + lessons / flop_issues. Wraps the existing /video/analyze
# response shape so the answer surface can render it as just another
# session format alongside Pattern, Ideas, Timing, Lifecycle, Diagnostic.
#
# Validation is intentionally permissive (``extra="allow"``) — the
# /video/analyze endpoint already produces a battle-tested shape; this
# model just pins the envelope so the answer-session writer doesn't
# silently drop fields it doesn't recognise. PR-2 will tighten if a
# concrete shape mismatch surfaces.


class VideoMeta(BaseModel):
    creator: str
    views: int
    likes: int
    comments: int
    shares: int
    save_rate: float
    duration_sec: float
    thumbnail_url: str | None = None
    date_posted: str | None = None
    title: str | None = None
    caption: str | None = None
    hook_phrase: str | None = None
    niche_label: str | None = None
    is_breakout: bool | None = None
    saves: int | None = None
    retention_source: Literal["real", "modeled"] | None = None
    # Channel-relative breakout — views vs the creator's own median posts.
    # Distinct from CreatorComparison.delta (which is hit / flop within the
    # same channel). target_vs_creator_median answers "is this a hit *for me*"
    # — the answer creators most want from the report.
    creator_median_views: int | None = None
    target_vs_creator_median: float | None = None

    model_config = {"extra": "allow"}


class VideoEnrichmentPayload(BaseModel):
    """Gemini-extracted creative context for the analysed video.

    Mirrors VideoAnalysis fields surfaced from corpus_ingest's enrichment
    schema (2026-05-08): audience read, pain points, promotion classification,
    style tags. Renders only when at least one signal is populated.
    """

    target_audience: str | None = None
    pain_points: list[str] = Field(default_factory=list)
    promotion_type: Literal["organic", "brand_deal", "affiliate", "self_promotion"] = "organic"
    style_tags: list[str] = Field(default_factory=list)
    tone: (
        Literal[
            "educational",
            "entertaining",
            "emotional",
            "humorous",
            "inspirational",
            "urgent",
            "conversational",
            "authoritative",
        ]
        | None
    ) = None

    model_config = {"extra": "allow"}


class VideoNicheMetaPayload(BaseModel):
    avg_views: float | None = None
    avg_retention: float = 0.5
    avg_ctr: float = 0.04
    sample_size: int = 0
    winners_sample_size: int | None = None
    peer_percentile: float | None = None
    peer_percentile_label: str | None = None

    model_config = {"extra": "allow"}


class CreatorComparisonVideo(BaseModel):
    video_id: str | None = None
    tiktok_url: str | None = None
    views: int
    # Caption excerpt (≤60 chars) from Ensemble post — field name is legacy.
    hook_type: str | None = None
    thumbnail_url: str | None = None


class CreatorComparisonFormatMatch(BaseModel):
    """Phase 4.2 — whether the analyzed video's format matches the creator's best format.

    Drives the channel-first narrative: if format_matches=False, the narrative can
    say "bạn đang đăng format mà kênh của bạn không hoạt động tốt".
    """

    format_matches: bool
    """True when the analyzed video's content_format == creator's best_performing_format."""
    analyzed_format: str | None = None
    """Detected format of the analyzed video (content_format field)."""
    best_format: str | None = None
    """Creator's strongest format from recent posts (by avg views)."""
    note_vi: str | None = None
    """Vietnamese note explaining the match/mismatch — used by narrative synthesis."""


class CreatorComparison(BaseModel):
    """Same-creator hit/flop comparison for video diagnosis (Lightreel-style)."""

    creator_handle: str
    total_posts_analyzed: int
    median_views: int
    hit: CreatorComparisonVideo
    flop: CreatorComparisonVideo
    delta: int
    target_vs_median: float
    target_percentile: str
    format_match: CreatorComparisonFormatMatch | None = None
    """Phase 4.2 — format match analysis; None when format data is unavailable."""


class VideoPayload(BaseModel):
    """Video diagnosis report — mirror of the /video/analyze response.

    Used by the answer surface as a session format. The /stream emit
    layer (PR-2) re-uses the existing run_video_analyze_pipeline +
    run_video_analyze_on_demand helpers; no recomputation here.
    """

    video_id: str
    mode: Literal["win", "flop"]
    meta: VideoMeta
    kpis: list[dict[str, Any]] = Field(default_factory=list)
    segments: list[dict[str, Any]] = Field(default_factory=list)
    hook_phases: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    structural_errors: list[dict[str, Any]] | None = None
    retention_curve: list[dict[str, float]] | None = None
    niche_benchmark_curve: list[dict[str, float]] | None = None
    niche_meta: VideoNicheMetaPayload | None = None
    thumbnail_analysis: dict[str, Any] | None = None
    comment_radar: dict[str, Any] | None = None
    # Flag set by run_video_analyze_on_demand so the FE can hint
    # "phân tích trực tiếp, không lưu corpus" when the report came
    # from a fresh URL (not a corpus row).
    source: Literal["corpus", "on_demand"] | None = None
    # Common ReportV1 fields the answer-shell reads generically
    # (AnswerSourcesCard + RelatedQs). Video reports populate them
    # best-effort: sources often empty (single-video diagnosis has no
    # cohort to cite), related_questions optional follow-up prompts.
    sources: list[SourceRow] = Field(default_factory=list)
    related_questions: list[str] = Field(default_factory=list)
    creator_comparison: CreatorComparison | None = None
    enrichment: VideoEnrichmentPayload | None = None
    # Narrative rebuild fields (2026-05-13) — headline_vi + lessons live inside narrative_vi
    narrative_vi: dict[str, Any] | None = None
    format_cards: list[dict[str, Any]] | None = None
    performance_tier: str | None = None
    bright_spot_signal: dict[str, Any] | None = None
    view_scenarios: list[dict[str, Any]] | None = None
    channel_context: dict[str, Any] | None = None
    reference_videos: list[dict[str, Any]] | None = None
    diagnosis: str | None = None
    # §4.6 — turn-1 handoff attribution (trends / composer / evidence / …).
    source_entry: SourceEntry | None = None

    model_config = {"extra": "allow"}


class ScriptPayload(BaseModel):
    """6-shot TikTok script plan (Studio answer session)."""

    topic: str = Field(..., max_length=500)
    hook: str = Field(..., max_length=200)
    hook_delay_ms: int = Field(ge=400, le=3000)
    duration: int = Field(ge=15, le=90)
    tone: str = Field(..., max_length=20)
    niche_label: str = Field(default="", max_length=120)
    shots: list[dict[str, Any]] = Field(min_length=6, max_length=6)
    sources: list[SourceRow] = Field(default_factory=list)
    related_questions: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


ReportKind = Literal[
    "pattern", "ideas", "timing", "generic", "lifecycle", "diagnostic", "video", "script", "compare",
]
_REPORT_KINDS: frozenset[str] = frozenset(
    {"pattern", "ideas", "timing", "generic", "lifecycle", "diagnostic", "video", "script", "compare"}
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
        | VideoPayload
        | ScriptPayload
        | ComparePayload
    )


def validate_and_store_report(kind: str, report: dict[str, Any]) -> dict[str, Any]:
    """Validate inner report dict and return full §J envelope for JSONB storage."""
    _attach_narrative_vi_headline(report, kind)
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
    elif k == "video":
        VideoPayload.model_validate(report)
    elif k == "script":
        ScriptPayload.model_validate(report)
    elif k == "compare":
        ComparePayload.model_validate(report)
    else:
        GenericPayload.model_validate(report)
    return {"kind": k, "report": report}


def _headline_vi_for_report(kind: str, report: dict[str, Any]) -> str | None:
    """Map legacy headline fields → unified ``narrative_vi.headline_vi`` (W5-2)."""
    if kind == "pattern":
        thesis = str((report.get("tldr") or {}).get("thesis") or "").strip()
        return thesis[:240] if thesis else None
    if kind == "ideas":
        lead = str(report.get("lead") or "").strip()
        return lead[:240] if lead else None
    if kind == "timing":
        tw = report.get("top_window") if isinstance(report.get("top_window"), dict) else {}
        insight = str(tw.get("insight") or "").strip()
        if insight:
            return insight[:240]
        day = str(tw.get("day") or "").strip()
        hours = str(tw.get("hours") or "").strip()
        if day and hours:
            return f"{day}, {hours}"[:240]
        return None
    if kind == "lifecycle":
        subject = str(report.get("subject_line") or "").strip()
        return subject[:240] if subject else None
    if kind == "generic":
        narrative = report.get("narrative") if isinstance(report.get("narrative"), dict) else {}
        paras = narrative.get("paragraphs") if isinstance(narrative.get("paragraphs"), list) else []
        if paras:
            first = str(paras[0] or "").strip()
            return first[:240] if first else None
        return None
    return None


def _attach_narrative_vi_headline(report: dict[str, Any], kind: str) -> None:
    headline = _headline_vi_for_report(kind, report)
    if not headline:
        return
    existing = report.get("narrative_vi")
    if isinstance(existing, dict) and str(existing.get("headline_vi") or "").strip():
        return
    if isinstance(existing, dict):
        existing["headline_vi"] = headline
    else:
        report["narrative_vi"] = {"headline_vi": headline}


def validate_pattern_payload(payload: dict[str, Any]) -> PatternPayload:
    return PatternPayload.model_validate(payload)
