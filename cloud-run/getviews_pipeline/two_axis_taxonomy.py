"""Canonical two-axis labels aligned with Supabase ``creator_niches`` + ``format_axis``.

Source: ``20260510000004_two_axis_niche_pr1_schema.sql`` + ``20260630000003`` (16 niches).
"""

from __future__ import annotations

from typing import Any, Final, Literal

# UX-facing creator niches — must match ``creator_niches.slug`` (active rows).
CREATOR_NICHE_SLUGS: Final[tuple[str, ...]] = (
    "beauty",
    "fashion",
    "food",
    "lifestyle",
    "comedy",
    "family",
    "education",
    "tech_gaming",
    "business",
    "wellness",
    "travel",
    "auto",
    "pets_home",
    "gym_fitness",
    "music_dance",
    "real_estate",
)

# Distinct ``format_axis`` values from ``content_classifications`` seed (PR1).
FORMAT_AXIS_SLUGS: Final[tuple[str, ...]] = (
    "comedy_observational",
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
    "comedy": "Hài · Giải trí",
    "family": "Nuôi con · Gia đình",
    "education": "Giáo dục · Sự nghiệp",
    "tech_gaming": "Công nghệ · Gaming",
    "business": "Kinh doanh · Tài chính",
    "wellness": "Sức khoẻ · Wellness",
    "travel": "Du lịch · Thể thao",
    "auto": "Ô tô · Xe máy",
    "pets_home": "Thú cưng · Nhà cửa",
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
    "comedy_observational": "Hài quan sát / relatable (kể cả mẹ bỉm humor)",
}

CreatorNicheSlug = Literal[
    "beauty",
    "fashion",
    "food",
    "lifestyle",
    "comedy",
    "family",
    "education",
    "tech_gaming",
    "business",
    "wellness",
    "travel",
    "auto",
    "pets_home",
    "gym_fitness",
    "music_dance",
    "real_estate",
]

FormatAxisSlug = Literal[
    "comedy_observational",
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


def build_extraction_niche_glossary_block() -> str:
    """Vietnamese glossary of allowed enum values for the extraction prompt."""
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
