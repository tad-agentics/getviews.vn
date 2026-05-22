"""Canonical two-axis labels aligned with Supabase ``creator_niches`` + ``format_axis``.

Source: ``20260510000004_two_axis_niche_pr1_schema.sql`` + ``20260630000003`` (16 niches)
+ ``20260728000000`` (retire ``comedy``, ``pets_home`` → 14 active UX buckets).
"""

from __future__ import annotations

from typing import Any, Final, Literal

# UX-facing creator niches — must match ``creator_niches.slug`` (active rows).
CREATOR_NICHE_SLUGS: Final[tuple[str, ...]] = (
    "beauty",
    "fashion",
    "food",
    "lifestyle",
    "family",
    "education",
    "tech_gaming",
    "business",
    "wellness",
    "travel",
    "auto",
    "gym_fitness",
    "music_dance",
    "real_estate",
)

# Distinct ``format_axis`` values from ``content_classifications`` seed (PR1).
# ``observational_relatable`` renamed from ``comedy_observational`` (20260823000003).
FORMAT_AXIS_SLUGS: Final[tuple[str, ...]] = (
    "observational_relatable",
    "dance_choreography",
    "live_commerce",
    "montage_highlights",
    "music_performance",
    "pov_storytelling",
    "react_commentary",
    "review_unboxing",
    "skit_scripted",
    "talking_head_advice",
    "tutorial",
    "vlog_daily",
)

CREATOR_NICHE_VI: Final[dict[str, str]] = {
    "beauty": "Làm đẹp · Skincare",
    "fashion": "Thời trang · Phụ kiện",
    "food": "Ẩm thực · Ăn uống",
    "lifestyle": "Đời sống · Tâm sự",
    "family": "Nuôi con · Gia đình",
    "education": "Giáo dục · Sự nghiệp",
    "tech_gaming": "Công nghệ · Gaming",
    "business": "Kinh doanh · Tài chính",
    "wellness": "Sức khoẻ · Wellness",
    "travel": "Du lịch · Thể thao",
    "auto": "Ô tô · Xe máy",
    "gym_fitness": "Gym · Fitness",
    "music_dance": "Âm nhạc · Vũ đạo",
    "real_estate": "Bất động sản · Nhà đất",
}

FORMAT_AXIS_VI: Final[dict[str, str]] = {
    "tutorial": "Hướng dẫn từng bước (công thức, form tập, software, DIY)",
    "review_unboxing": "Review / mở hộp / đánh giá sản phẩm hoặc địa điểm",
    "pov_storytelling": "POV kể chuyện / trải nghiệm cá nhân",
    "montage_highlights": "Montage highlight, lookbook nhanh, compilation",
    "vlog_daily": "Vlog đời sống / travel / routine / tour",
    "react_commentary": "Reaction, commentary, challenge ăn uống",
    "talking_head_advice": "Talking head — lời khuyên, tài chính, góc nhìn chuyên gia",
    "music_performance": "Biểu diễn âm nhạc / cover hát",
    "dance_choreography": "Dance / choreography / dance challenge",
    "skit_scripted": "Skit kịch bản / parody có kịch bản",
    "live_commerce": "Livestream bán hàng / anchor giới thiệu deal",
    "observational_relatable": "Hài quan sát / relatable (kể cả mẹ bỉm humor) — không trùng class slug",
}

CreatorNicheSlug = Literal[
    "beauty",
    "fashion",
    "food",
    "lifestyle",
    "family",
    "education",
    "tech_gaming",
    "business",
    "wellness",
    "travel",
    "auto",
    "gym_fitness",
    "music_dance",
    "real_estate",
]

FormatAxisSlug = Literal[
    "observational_relatable",
    "dance_choreography",
    "live_commerce",
    "montage_highlights",
    "music_performance",
    "pov_storytelling",
    "react_commentary",
    "review_unboxing",
    "skit_scripted",
    "talking_head_advice",
    "tutorial",
    "vlog_daily",
]

# HI-16 — carousel extraction only (distinct from video ``format_axis``).
CAROUSEL_FORMAT_AXIS_SLUGS: Final[tuple[str, ...]] = (
    "tutorial_carousel",
    "listicle_carousel",
    "story_carousel",
    "comparison_carousel",
    "gallery_carousel",
)

CarouselFormatAxisSlug = Literal[
    "tutorial_carousel",
    "listicle_carousel",
    "story_carousel",
    "comparison_carousel",
    "gallery_carousel",
]

CAROUSEL_FORMAT_AXIS_VI: Final[dict[str, str]] = {
    "tutorial_carousel": (
        "Carousel hướng dẫn từng bước (recipe, checklist, công thức slide-by-slide)"
    ),
    "listicle_carousel": "Carousel list / tips (số thứ tự, nhiều ý ngắn trên nhiều slide)",
    "story_carousel": "Carousel kể chuyện (narrative, twist, POV vuốt qua slide)",
    "comparison_carousel": "Carousel so sánh / before-after / A vs B rõ hai phía",
    "gallery_carousel": "Carousel gallery / moodboard (nhấn ảnh, ít chữ, aesthetic vuốt)",
}


# Junction: ``VIDEO_JUNCTION_NICHE_FORMAT_PAIRS`` = 50 (14 niches, post-20260728);
# ``CAROUSEL_JUNCTION_NICHE_FORMAT_PAIRS`` = 70 (14 × 5 carousel axes, HI-16).
# Union = ``JUNCTION_NICHE_FORMAT_PAIRS`` (120). Tests: ``tests/test_hi9_junction_seed.py``.
VIDEO_JUNCTION_NICHE_FORMAT_PAIRS: Final[frozenset[tuple[str, str]]] = frozenset({
    ("auto", "review_unboxing"),
    ("auto", "talking_head_advice"),
    ("auto", "tutorial"),
    ("auto", "vlog_daily"),
    ("beauty", "pov_storytelling"),
    ("beauty", "review_unboxing"),
    ("beauty", "tutorial"),
    ("business", "live_commerce"),
    ("business", "pov_storytelling"),
    ("business", "review_unboxing"),
    ("business", "talking_head_advice"),
    ("business", "vlog_daily"),
    ("education", "talking_head_advice"),
    ("education", "tutorial"),
    ("family", "observational_relatable"),
    ("family", "talking_head_advice"),
    ("family", "vlog_daily"),
    ("fashion", "montage_highlights"),
    ("fashion", "pov_storytelling"),
    ("fashion", "review_unboxing"),
    ("fashion", "vlog_daily"),
    ("food", "pov_storytelling"),
    ("food", "react_commentary"),
    ("food", "review_unboxing"),
    ("food", "tutorial"),
    ("food", "vlog_daily"),
    ("gym_fitness", "tutorial"),
    ("gym_fitness", "vlog_daily"),
    ("lifestyle", "dance_choreography"),
    ("lifestyle", "montage_highlights"),
    ("lifestyle", "music_performance"),
    ("lifestyle", "pov_storytelling"),
    ("lifestyle", "react_commentary"),
    ("lifestyle", "skit_scripted"),
    ("lifestyle", "talking_head_advice"),
    ("lifestyle", "tutorial"),
    ("lifestyle", "vlog_daily"),
    ("music_dance", "dance_choreography"),
    ("music_dance", "music_performance"),
    ("real_estate", "vlog_daily"),
    ("tech_gaming", "montage_highlights"),
    ("tech_gaming", "review_unboxing"),
    ("tech_gaming", "talking_head_advice"),
    ("tech_gaming", "tutorial"),
    ("travel", "montage_highlights"),
    ("travel", "talking_head_advice"),
    ("travel", "vlog_daily"),
    ("wellness", "talking_head_advice"),
    ("wellness", "tutorial"),
    ("wellness", "vlog_daily"),
})

CAROUSEL_JUNCTION_NICHE_FORMAT_PAIRS: Final[frozenset[tuple[str, str]]] = frozenset(
    (niche, fmt) for niche in CREATOR_NICHE_SLUGS for fmt in CAROUSEL_FORMAT_AXIS_SLUGS
)

JUNCTION_NICHE_FORMAT_PAIRS: Final[frozenset[tuple[str, str]]] = (
    VIDEO_JUNCTION_NICHE_FORMAT_PAIRS | CAROUSEL_JUNCTION_NICHE_FORMAT_PAIRS
)


def junction_has_pair(creator_niche_slug: str | None, format_axis: str | None) -> bool:
    """True iff (slug, format_axis) is seeded in ``creator_niche_content_classes``.

    Caller should WARN — not fail — when False so HI-11 routing can downgrade
    deterministically instead of silently writing a NULL ``content_class_id``.
    """
    if not creator_niche_slug or not format_axis:
        return False
    return (creator_niche_slug, format_axis) in JUNCTION_NICHE_FORMAT_PAIRS


def build_carousel_extraction_niche_glossary_block() -> str:
    """Glossary for carousel extraction — creator niches + carousel_format_axis only (HI-16)."""
    lines: list[str] = [
        "=== glossary — creator_niche_slug (CHỌN ĐÚNG MỘT giá trị snake_case) ===",
    ]
    for slug in CREATOR_NICHE_SLUGS:
        lines.append(f'- "{slug}" — {CREATOR_NICHE_VI[slug]}')
    lines.append("")
    lines.append("=== glossary — carousel_format_axis (CHỌN ĐÚNG MỘT — CHỈ cho carousel) ===")
    for axis in CAROUSEL_FORMAT_AXIS_SLUGS:
        lines.append(f'- "{axis}" — {CAROUSEL_FORMAT_AXIS_VI[axis]}')
    return "\n".join(lines)


def build_extraction_niche_glossary_block() -> str:
    """Vietnamese glossary of allowed enum values for the **video** extraction prompt."""
    lines: list[str] = [
        "=== glossary — creator_niche_slug (CHỌN ĐÚNG MỘT giá trị snake_case) ===",
    ]
    for slug in CREATOR_NICHE_SLUGS:
        lines.append(f'- "{slug}" — {CREATOR_NICHE_VI[slug]}')
    lines.append("")
    lines.append("=== glossary — format_axis (CHỌN ĐÚNG MỘT giá trị snake_case) ===")
    for axis in FORMAT_AXIS_SLUGS:
        lines.append(f'- "{axis}" — {FORMAT_AXIS_VI[axis]}')
    return "\n".join(lines)


def extract_subject_matter_from_analysis_json(
    analysis_json: Any,
    *,
    max_len: int = 200,
) -> str | None:
    """Best-effort `content_context.subject_matter` for downstream prompts (HI-18)."""
    if not isinstance(analysis_json, dict):
        return None
    cc = analysis_json.get("content_context")
    if not isinstance(cc, dict):
        return None
    sm = str(cc.get("subject_matter") or "").strip()
    if not sm:
        return None
    return sm[:max_len]
