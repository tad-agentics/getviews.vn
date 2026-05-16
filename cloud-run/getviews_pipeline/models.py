"""Pydantic models mirroring SPEC sections 6–7."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from getviews_pipeline.two_axis_taxonomy import CreatorNicheSlug, FormatAxisSlug

# Post format (video vs photo carousel) — used on VideoMetadata and analyze payloads.
ContentType = Literal["video", "carousel"]

HookType = Literal[
    "question",
    "bold_claim",
    "shock_stat",
    "story_open",
    "controversy",
    "challenge",
    "how_to",
    "social_proof",
    "curiosity_gap",
    "pain_point",
    "trend_hijack",
    "none",
    "other",
]

FirstFrameType = Literal[
    "face",
    "face_with_text",
    "product",
    "text_only",
    "action",
    "screen_recording",
    "other",
]

SceneType = Literal[
    "face_to_camera",
    "product_shot",
    "screen_recording",
    "broll",
    "text_card",
    "demo",
    "action",
    "other",
]

# 2026-05-10 — Wave 2.5 Phase A PR #2: per-scene enrichment dimensions
# that back the "reference videos per script shot" matcher. All six
# fields are Optional on Scene so ingestions before this PR still
# validate; when Gemini can't classify confidently, it returns null
# rather than guessing — the matcher falls back to the legacy
# SceneType filter in that case.

FramingType = Literal[
    "close_up",          # subject fills most of frame
    "medium",            # subject from waist up
    "wide",              # full-body / landscape
    "extreme_close_up",  # eye / lip / texture level
]

PaceType = Literal[
    "static",      # no cuts, single locked shot
    "slow",        # ~1 cut every 3+ seconds
    "medium",      # ~1 cut every 1-3 seconds
    "fast",        # ~2-3 cuts per second
    "cut_heavy",   # rapid-fire montage, 3+ cuts/sec
]

OverlayStyleType = Literal[
    "none",         # no text overlay at all
    "bold_center",  # large centered headline text (TikTok "big text")
    "sub_caption",  # subtitle-style at bottom
    "chyron",       # lower-third banner / ticker
    "sticker",      # emoji/sticker overlay, decorative
]

SubjectType = Literal[
    "face",     # human face is the dominant subject
    "product",  # physical product (cosmetic, food, electronic, apparel)
    "text",     # text-driven frame (quote, headline)
    "action",   # motion-driven (dance, sport, gesture)
    "ambient",  # environment / B-roll / establishing
    "mixed",    # two or more equally weighted
]

MotionType = Literal[
    "static",      # locked camera, no movement
    "handheld",    # organic camera movement
    "slow_mo",     # slow-motion footage
    "time_lapse",  # sped-up footage
    "match_cut",   # graphic/motion match cut
]

# Same allowed values as SceneType — distinct name for carousel slide semantics.
SlideVisualType = Literal[
    "face_to_camera",
    "product_shot",
    "screen_recording",
    "broll",
    "text_card",
    "demo",
    "action",
    "other",
]

EnergyLevel = Literal["low", "medium", "high"]

ToneType = Literal[
    "educational",
    "entertaining",
    "emotional",
    "humorous",
    "inspirational",
    "urgent",
    "conversational",
    "authoritative",
]


# Maps known Gemini near-miss values → canonical HookType.
_HOOK_TYPE_ALIASES: dict[str, str] = {
    "pov": "story_open",
    "statistic": "shock_stat",
    "stat": "shock_stat",
    "question_hook": "question",
    "bold claim": "bold_claim",
    "shock stat": "shock_stat",
    "story open": "story_open",
    "how to": "how_to",
    "social proof": "social_proof",
    "curiosity gap": "curiosity_gap",
    "curiosity": "curiosity_gap",
    "pain point": "pain_point",
    "trend hijack": "trend_hijack",
    # "insider" / "secret" knowledge-base types → closest canonical HookType
    "insider": "social_proof",
    "secret": "social_proof",
    "bi_mat": "social_proof",
}


HookTimelineEventType = Literal[
    "face_enter",
    "first_word",
    "text_overlay",
    "sound_drop",
    "cut",
    "product_enter",
    "reveal",
]


class HookTimelineEvent(BaseModel):
    """One notable moment inside the opening hook window (0.0–3.0s).

    Gemini is asked to report 2-5 of these per video so creators see the
    frame-by-frame choreography of the hook instead of a single
    face_appears_at number. Optional — older corpus rows won't have it.
    """

    t: float = Field(..., ge=0.0, le=5.0, description="Seconds from video start.")
    event: HookTimelineEventType
    note: str = ""  # optional 1-3 word descriptor, e.g. "zoom-in" / "sản phẩm"


class HookAnalysis(BaseModel):
    first_frame_type: FirstFrameType
    face_appears_at: float | None = None
    first_speech_at: float | None = None
    hook_phrase: str
    hook_type: HookType
    hook_notes: str
    hook_timeline: list[HookTimelineEvent] = Field(default_factory=list)

    @field_validator("hook_type", mode="before")
    @classmethod
    def normalize_hook_type(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        normalized = v.strip().lower().replace("-", "_")
        return _HOOK_TYPE_ALIASES.get(normalized, normalized)


class TextOverlay(BaseModel):
    text: str
    appears_at: float


class Scene(BaseModel):
    type: SceneType
    start: float
    end: float
    # 2026-05-10 — Wave 2.5 Phase A PR #2: enrichment dimensions for the
    # per-shot reference-video matcher. All Optional so older ingests
    # + the fallback path (Gemini couldn't classify confidently) still
    # validate. Defaults to None → matcher falls back to SceneType filter
    # on that dimension. See video_shots table + artifacts/docs/
    # implementation-plan.md for the matcher design.
    framing: FramingType | None = None
    pace: PaceType | None = None
    overlay_style: OverlayStyleType | None = None
    subject: SubjectType | None = None
    motion: MotionType | None = None
    description: str | None = None  # 12–24 word VN human-readable gloss


class ContentDirection(BaseModel):
    what_works: str
    suggested_angles: list[str]


PromotionType = Literal["organic", "brand_deal", "affiliate", "self_promotion"]


class NarrativeViItem(BaseModel):
    error_id: str
    narrative: str
    evidence_aweme_id: str | None = None


class NarrativeVi(BaseModel):
    ket_luan_nhanh: str
    van_de_chinh: str
    loi_chinh_narrative: list[NarrativeViItem] = Field(default_factory=list)
    dinh_huong_chien_luoc: str


class BrightSpotSignal(BaseModel):
    signal_type: Literal[
        "hook_only_problem",
        "performing_well",
        "hook_and_distribution",
        "content_and_hook",
    ]
    message_vi: str


class FormatCardExample(BaseModel):
    aweme_id: str
    desc: str = ""
    play_count: int = 0
    creator_handle: str = ""
    tiktok_url: str


class FormatCard(BaseModel):
    format_name_vi: str
    mechanism_vi: str
    view_range: str
    engagement_rate: str
    example_hook_vi: str
    evidence_aweme_id: str | None = None
    format_examples: list[FormatCardExample] | None = None
    content_format: str | None = Field(
        default=None,
        description="Canonical slug matching video_corpus.content_format",
    )


class ReferenceVideoCard(BaseModel):
    aweme_id: str
    desc: str | None = None
    hook_type: str | None = None
    content_format: str | None = None
    views: int | None = None
    engagement_rate: float | None = None
    author_handle: str | None = None
    thumbnail_url: str | None = None
    tiktok_url: str | None = None
    source: Literal["corpus", "live_search"] = "corpus"


class ChannelContextVideo(BaseModel):
    aweme_id: str
    desc: str | None = None
    views: int | None = None
    content_format: str | None = None
    tiktok_url: str | None = None


class ChannelContext(BaseModel):
    available: bool
    reason: str | None = None
    top_videos: list[ChannelContextVideo] | None = None
    bottom_videos: list[ChannelContextVideo] | None = None
    best_performing_format: str | None = None
    sample_size: int | None = None
    median_views: float | None = None


ContentCreatorRole = Literal[
    "expert",
    "user_reviewer",
    "storyteller",
    "performer",
    "tutorial_host",
]

ContentPurpose = Literal[
    "educate",
    "entertain",
    "sell",
    "inspire",
    "review",
    "react",
]

LanguageRegister = Literal[
    "casual",
    "formal",
    "youth_slang",
    "expert_jargon",
]


class ProductMention(BaseModel):
    """Named product/brand in frame or speech — optional enrichment (HI-9)."""

    model_config = ConfigDict(extra="ignore")

    name: str
    brand: str | None = None
    category: str | None = None


class ContentContext(BaseModel):
    """Semantic scene understanding — optional; old corpus rows have null."""

    model_config = ConfigDict(extra="ignore")

    subject_matter: str | None = None
    """ONE Vietnamese sentence summarising what the content is about."""
    primary_subjects: list[str] | None = None
    setting: str | None = None
    products_mentioned: list[ProductMention] | None = None
    creator_role: ContentCreatorRole | None = None
    dominant_actions: list[str] | None = None
    content_purpose: ContentPurpose | None = None
    language_register: LanguageRegister | None = None
    topical_hashtags_implied: list[str] | None = None


class NicheClassification(BaseModel):
    """Two-axis niche × format classification — optional for legacy rows."""

    model_config = ConfigDict(extra="ignore")

    creator_niche_slug: CreatorNicheSlug | None = None
    format_axis: FormatAxisSlug | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str | None = None
    """ONE Vietnamese sentence justifying both axes."""
    alternative_creator_niche_slug: CreatorNicheSlug | None = None
    """Second-best creator niche when confidence < 0.8; else null."""


class VideoAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hook_analysis: HookAnalysis
    has_human_speaking_to_camera: bool = False
    has_expressed_opinion_or_question: bool = False
    text_overlays: list[TextOverlay] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)
    transitions_per_second: float
    energy_level: EnergyLevel
    key_timestamps: list[float] = Field(default_factory=list)
    audio_transcript: str
    tone: ToneType
    topics: list[str] = Field(default_factory=list)
    key_messages: list[str] = Field(default_factory=list)
    cta: str | None = None
    content_direction: ContentDirection
    target_audience: str = ""
    pain_points: list[str] = Field(default_factory=list)
    promotion_type: PromotionType = "organic"
    style_tags: list[str] = Field(default_factory=list)

    content_context: ContentContext | None = None
    niche_classification: NicheClassification | None = None

    @field_validator("promotion_type", mode="before")
    @classmethod
    def normalize_promotion_type(cls, v: object) -> str:
        # Mirror corpus_ingest._normalize_promotion_type: coerce any JSON value to str
        # so Gemini ints/bools/enums never reach Literal validation raw.
        s = str(v or "organic").strip().lower()
        if s in ("organic", "brand_deal", "affiliate", "self_promotion"):
            return s
        return "organic"


class SlideAnalysis(BaseModel):
    """One carousel slide; ``index`` is 0-based in the extracted batch (gaps if CDN skips)."""

    index: int = Field(ge=0)
    visual_type: SlideVisualType
    text_on_slide: list[str] = Field(default_factory=list)
    note: str = ""

    # Per-slide metrics for diagnosis (all Optional — existing analyses unaffected)
    text_density: str | None = None
    """Amount of text on slide: 'none', 'low', 'medium', or 'high'."""
    has_face: bool | None = None
    """True if a human face is prominently visible on this slide."""
    has_product: bool | None = None
    """True if a product (physical item for purchase) is prominently visible."""
    word_count: int | None = None
    """Approximate number of words of text visible on this slide."""


class CTASlide(BaseModel):
    """CTA presence on the final slide of a carousel."""

    has_cta: bool = False
    cta_type: str | None = None
    """One of: 'save', 'follow', 'comment', 'link_bio', 'shop_cart', or None."""
    cta_text: str | None = None
    """Verbatim CTA text extracted from the slide, if present."""


class CarouselAnalysis(BaseModel):
    """Gemini output for photo carousels — parallel to VideoAnalysis but slide-native.

    Intentionally omits text_overlays (timestamped video burns — not applicable to
    static images). Per-slide text lives in slides[].text_on_slide and
    slides[].text_density instead.

    transitions_per_second and key_timestamps are kept for schema compatibility with
    VideoAnalysis (shared ingest path reads both models uniformly) but are always 0/[]
    for carousels. The carousel diagnosis path (build_carousel_diagnosis_narrative_prompt)
    marks both as "skip" in FORMAT_ANALYSIS_WEIGHTS and never surfaces them to Gemini or
    users. Removing them would require a DB backfill migration and ingest code changes
    across corpus_ingest.py, layer0_niche.py, and layer0_sound.py for ~$0 token savings
    (~2 schema tokens per carousel call). Not worth the churn — leave them in place.
    """

    model_config = ConfigDict(extra="ignore")

    hook_analysis: HookAnalysis
    slides: list[SlideAnalysis]
    transitions_per_second: float
    energy_level: EnergyLevel
    key_timestamps: list[float] = Field(default_factory=list)
    audio_transcript: str
    tone: ToneType
    topics: list[str] = Field(default_factory=list)
    key_messages: list[str] = Field(default_factory=list)
    cta: str | None = None
    content_direction: ContentDirection

    # Carousel-level metrics (all Optional — existing cached analyses unaffected)
    content_arc: str | None = None
    """How content flows across slides: 'list', 'story', 'before_after', 'comparison',
    'tutorial_steps', or 'gallery'."""
    visual_consistency: str | None = None
    """Design consistency across slides: 'consistent', 'mixed', or 'inconsistent'."""
    estimated_read_time_seconds: int | None = None
    """Estimated total read/swipe time in seconds."""
    cta_slide: CTASlide | None = None
    """CTA presence on the final slide — typed Pydantic model for JSON schema generation."""
    has_numbered_hook: bool | None = None
    """True if slide 1 shows a number (e.g. '7 cách…') triggering completion bias."""
    swipe_trigger_type: str | None = None
    """Swipe mechanic: list_momentum, curiosity_chain, narrative_tension, or none."""

    content_context: ContentContext | None = None
    niche_classification: NicheClassification | None = None


class Metrics(BaseModel):
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    bookmarks: int | None = None


class Author(BaseModel):
    username: str
    display_name: str
    followers: int | None = None
    verified: bool = False


class Music(BaseModel):
    title: str | None = None
    artist: str | None = None
    is_original: bool | None = None


class VideoMetadata(BaseModel):
    video_id: str
    description: str
    hashtags: list[str] = Field(default_factory=list)
    content_type: ContentType = "video"
    slide_count: int | None = None
    duration_sec: float
    create_time: int | None = None
    metrics: Metrics
    engagement_rate: float | None = None
    author: Author
    music: Music
    thumbnail_url: str | None = None


class VideoAnalyzeResult(BaseModel):
    content_type: Literal["video"] = "video"
    metadata: VideoMetadata
    analysis: VideoAnalysis
    diagnosis: str
    narrative_vi: NarrativeVi | None = None
    bright_spot_signal: BrightSpotSignal | None = None
    format_cards: list[FormatCard] | None = None
    channel_context: ChannelContext | None = None
    reference_videos: list[ReferenceVideoCard] | None = None
    performance_tier: str | None = None


class CarouselAnalyzeResult(BaseModel):
    content_type: Literal["carousel"] = "carousel"
    metadata: VideoMetadata
    analysis: CarouselAnalysis
    diagnosis: str


# ── Phase 4.0 — v5 Channel-First Narrative response models ───────────────────

class VideoDiagnosisV5MetricItem(BaseModel):
    value: str
    label: str
    cohort_tag: str | None = None
    tone: Literal["default", "warn", "bad"] = "default"


class VideoDiagnosisV5Header(BaseModel):
    handle: str
    duration_s: float
    posted_at: str
    caption: str
    metrics: list[VideoDiagnosisV5MetricItem] = Field(default_factory=list)


class VideoDiagnosisV5ChannelProofCard(BaseModel):
    views_range: str
    format_label: str


class VideoDiagnosisV5ChannelProof(BaseModel):
    handle: str
    winner: VideoDiagnosisV5ChannelProofCard
    loser: VideoDiagnosisV5ChannelProofCard
    pattern_note: str


class VideoDiagnosisV5Error(BaseModel):
    rank: Literal[1, 2, 3]
    severity: Literal["critical", "major", "minor"]
    title: str
    body: str
    fix: str


class VideoDiagnosisV5CrossFormatCard(BaseModel):
    format_name: str
    description: str
    stat: dict[str, str]
    example: str


class VideoDiagnosisV5CrossFormatWinners(BaseModel):
    sample_size: int
    window_days: int
    cards: list[VideoDiagnosisV5CrossFormatCard] = Field(default_factory=list)


class VideoDiagnosisV5NextStep(BaseModel):
    bold_lead: str
    detail: str


class VideoDiagnosisV5Collapsibles(BaseModel):
    hook_analysis: dict[str, object] = Field(default_factory=dict)
    script_structure: dict[str, object] = Field(default_factory=dict)
    full_context: dict[str, object] = Field(default_factory=dict)


class VideoDiagnosisV5(BaseModel):
    """v5 Channel-First Narrative response (Phase 4.0).

    Mirrors the TypeScript ``VideoDiagnosisV5`` interface in api-types.ts.
    Enforced by the Phase 2.3 schema-contract CI test.
    """

    header: VideoDiagnosisV5Header
    van_de_chinh: str
    """3-sentence Vietnamese channel-first narrative lead."""
    channel_proof: VideoDiagnosisV5ChannelProof | None = None
    """null when ≥2 formats with n≥3 not met in channel_context.per_format_views."""
    errors: list[VideoDiagnosisV5Error] = Field(default_factory=list, max_length=3)
    """Max 3 errors, pre-sorted severity desc: critical → major → minor."""
    cross_format_winners: VideoDiagnosisV5CrossFormatWinners
    next_steps: list[VideoDiagnosisV5NextStep] = Field(default_factory=list)
    collapsibles: VideoDiagnosisV5Collapsibles = Field(
        default_factory=VideoDiagnosisV5Collapsibles
    )


class DiagnosisSynthesisInput(BaseModel):
    """Typed input contract for synthesize_diagnosis_v2 (Phase 3.7.2).

    Uses the HYBRID pattern from the plan:
    - Vietnamese natural-language system instructions remain in the f-string prompt
    - Structured arrays (reference_videos, errors, channel_context) are injected
      as a validated JSON sub-block via json.dumps(instance.json_payload())

    This makes the LLM INPUT boundary auditable by the Phase 2.3 schema-contract CI.
    """

    niche_label: str = Field(default="", max_length=80)
    content_format: str = Field(default="", max_length=80)
    corpus_size: int = Field(default=0, ge=0)
    performance_tier: str = Field(default="unknown", max_length=40)
    creator_handle: str = Field(default="", max_length=80)
    views: int = Field(default=0, ge=0)
    engagement_rate: float = Field(default=0.0, ge=0.0)
    # Structured arrays — injected as JSON sub-block
    errors: list[dict[str, object]] = Field(default_factory=list)
    """Max 3 errors for v5 UI (narrative references first 3 only)."""
    reference_video_ids: list[str] = Field(default_factory=list)
    """Allowed aweme_ids from reference pool — used for citation validation."""
    per_format_views: dict[str, object] | None = None
    """channel_context.per_format_views — injected when >=2 formats with n>=3."""
    channel_avg_views: float | None = None
    channel_avg_er: float | None = None

    def json_payload(self) -> dict[str, object]:
        """Return the structured sub-block for JSON injection into the prompt.

        Vietnamese natural-language instructions wrap this block; the LLM sees
        the field names from the Pydantic schema (same as TypeScript interface).
        """
        return {
            "niche_label": self.niche_label,
            "content_format": self.content_format,
            "corpus_size": self.corpus_size,
            "performance_tier": self.performance_tier,
            "creator_handle": self.creator_handle,
            "views": self.views,
            "engagement_rate": self.engagement_rate,
            "errors": self.errors[:3],
            "reference_video_ids": self.reference_video_ids,
            "channel": {
                "per_format_views": self.per_format_views,
                "avg_views": self.channel_avg_views,
                "avg_er": self.channel_avg_er,
            } if (self.per_format_views or self.channel_avg_views) else None,
        }


class DiagnosisInput(BaseModel):
    """Input contract for run_video_diagnosis_core (Phase 3.2).

    Packages everything the diagnosis layer needs — the extraction result plus
    niche/benchmark context — so the diagnosis core has zero Supabase reads.
    All reads happen in the caller before this model is constructed.
    """

    extraction: ExtractionResult
    """Typed output from run_extraction_core — must have ok=True."""
    video_row: dict[str, object]
    """Aweme-derived dict consumed by extract_video_errors / build_niche_benchmark."""
    niche_id: int | None = None
    niche_label: str = ""
    niche_row: dict[str, object] | None = None
    """Raw niche intelligence row from video_niche_benchmark queries."""
    niche_meta: dict[str, object] | None = None
    """Benchmark summary (avg_views, avg_retention, …) — from build_niche_benchmark_payload."""
    niche_benchmark: list[dict[str, object]] | None = None
    """Retention benchmark curve for the niche."""
    retention_user: list[dict[str, object]] | None = None
    """Modeled retention curve for this specific video."""
    mode: Literal["win", "flop"] = "flop"
    content_format: str = ""
    retention_source: Literal["real", "modeled"] = "modeled"


class DiagnosisResult(BaseModel):
    """Output contract from run_video_diagnosis_core (Phase 3.2).

    Populated by extract_video_errors + apply_rule_based_video_errors +
    synthesize_diagnosis_v2. Passed to finalize_video_narrative_layer.
    """

    errors: list[dict[str, object]] = Field(default_factory=list)
    """Structured VideoFlopIssue list — max 3 for v5 UI, raw for v4 compat."""
    hook_cards: list[dict[str, object]] = Field(default_factory=list)
    segments: list[dict[str, object]] = Field(default_factory=list)
    retention_curve: list[dict[str, object]] = Field(default_factory=list)
    niche_benchmark_curve: list[dict[str, object]] = Field(default_factory=list)
    performance_tier: str | None = None
    kpi: dict[str, object] | None = None
    bright_spot_signal: dict[str, object] | None = None
    view_scenarios: list[dict[str, object]] | None = None
    narrative_vi: dict[str, object] | None = None
    format_cards: list[dict[str, object]] | None = None
    channel_context: dict[str, object] | None = None
    creator_comparison: dict[str, object] | None = None


class ExtractionResult(BaseModel):
    """Typed boundary between the extraction core and the diagnosis core.

    ``run_extraction_core`` returns this; ``run_video_diagnosis_core`` accepts it.
    Keeping this boundary explicit means the two cores can evolve independently —
    the diagnosis core never needs to know *how* the frames were extracted.

    Phase 3.6 — typed contract; Phase 3.1 populates it at the extraction callsite.
    """

    video_id: str
    """Canonical aweme / TikTok video ID."""
    content_type: Literal["video", "carousel"] = "video"
    metadata: VideoMetadata
    analysis: VideoAnalysis | None = None
    """Frame-by-frame Gemini analysis; None for carousel or on error."""
    carousel_analysis: CarouselAnalysis | None = None
    """Carousel Gemini analysis; None for videos."""
    transcript_quality: dict[str, object] | None = None
    """validate_transcript verdict dict attached by _finish_analysis."""
    entry_cost: dict[str, object] | None = None
    """Entry-cost badge (tier + reasons) attached by _finish_analysis."""
    error: str | None = None
    """Non-None when Gemini analysis failed; downstream must check before using analysis."""

    @property
    def ok(self) -> bool:
        """True when the extraction succeeded and analysis is usable."""
        return self.error is None and (
            self.analysis is not None or self.carousel_analysis is not None
        )


# ── Thumbnail / frame-0 analysis ───────────────────────────────────────────

ThumbnailDominantElement = Literal["face", "product", "text", "environment"]
ThumbnailFacialExpression = Literal[
    "neutral", "surprised", "confused", "smiling", "focused"
]
ThumbnailColourContrast = Literal["high", "medium", "low"]


class ThumbnailAnalysis(BaseModel):
    """Gemini's read on why (or whether) the first frame stops the scroll.

    Emitted by a focused image-understanding call on the t=0 frame URL
    (R2-hosted for corpus videos, skipped for videos without extracted
    frames until a later extraction-on-demand path lands).
    """

    stop_power_score: float = Field(..., ge=0.0, le=10.0)
    dominant_element: ThumbnailDominantElement
    text_on_thumbnail: str | None = None  # verbatim, max 40 chars
    facial_expression: ThumbnailFacialExpression | None = None
    colour_contrast: ThumbnailColourContrast
    why_it_stops: str  # one Vietnamese sentence, <= 120 chars


class BatchSummary(BaseModel):
    avg_face_appears_at: float | None = None
    avg_first_speech_at: float | None = None
    common_first_frame_types: list[str] = Field(default_factory=list)
    avg_transitions_per_second: float | None = None
    top_patterns: list[str] = Field(default_factory=list)
    content_gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    winning_formula: str | None = None
