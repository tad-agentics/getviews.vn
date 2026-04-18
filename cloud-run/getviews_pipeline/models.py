"""Pydantic models mirroring SPEC sections 6–7."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

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


class ContentDirection(BaseModel):
    what_works: str
    suggested_angles: list[str]


class VideoAnalysis(BaseModel):
    hook_analysis: HookAnalysis
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
    """Dominant swipe mechanic: 'list_momentum', 'curiosity_chain', 'narrative_tension', or 'none'."""


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


class CarouselAnalyzeResult(BaseModel):
    content_type: Literal["carousel"] = "carousel"
    metadata: VideoMetadata
    analysis: CarouselAnalysis
    diagnosis: str


class BatchSummary(BaseModel):
    avg_face_appears_at: float | None = None
    avg_first_speech_at: float | None = None
    common_first_frame_types: list[str] = Field(default_factory=list)
    avg_transitions_per_second: float | None = None
    top_patterns: list[str] = Field(default_factory=list)
    content_gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    winning_formula: str | None = None
