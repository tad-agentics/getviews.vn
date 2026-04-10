"""Pydantic models mirroring SPEC sections 6–7."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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


class HookAnalysis(BaseModel):
    first_frame_type: FirstFrameType
    face_appears_at: float | None = None
    first_speech_at: float | None = None
    hook_phrase: str
    hook_type: HookType
    hook_notes: str


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


class CarouselAnalysis(BaseModel):
    """Gemini output for photo carousels — parallel to VideoAnalysis but slide-native."""

    hook_analysis: HookAnalysis
    slides: list[SlideAnalysis]
    text_overlays: list[TextOverlay] = Field(default_factory=list)
    transitions_per_second: float
    energy_level: EnergyLevel
    key_timestamps: list[float] = Field(default_factory=list)
    audio_transcript: str
    tone: ToneType
    topics: list[str] = Field(default_factory=list)
    key_messages: list[str] = Field(default_factory=list)
    cta: str | None = None
    content_direction: ContentDirection


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
