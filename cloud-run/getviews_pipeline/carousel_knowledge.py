"""Research-backed carousel intelligence for synthesis prompts.

Sources: Fanpage Karma (700K posts), PostWaffle, SocialInsider,
TikTok official, Usevisuals, CCExperts VN, Kind Content Academy VN.

NOTE: ANTI_PATTERNS is named CAROUSEL_ANTI_PATTERNS to avoid collision
with voice_guide.py which also exports ANTI_PATTERNS.
"""

from __future__ import annotations

ALGORITHM_SIGNALS = {
    "swipe_through_rate": {
        "strong": 0.60,
        "weak": 0.20,
        "note": "Most important carousel metric. Low STR kills distribution.",
    },
    "completion_rate": {
        "strong": 0.80,
        "healthy_8plus": [0.40, 0.60],
    },
    "dwell_time_per_slide_seconds": [3, 5],
    "reverse_swipes": "Strongest positive signal — content worth revisiting.",
    "save_rate": {
        "strong": 0.03,
        "exceptional": 0.05,
        "note": ">5% triggers wider distribution.",
    },
    "key_difference": (
        "Each slide = separate engagement signal. "
        "10-slide carousel = 10 signals vs 1 for video."
    ),
}

OPTIMAL_SPECS = {
    "slide_count": {
        "min": 5,
        "ideal": 7,
        "max": 10,
        "structure": "1 hook + 5 value + 1 CTA",
    },
    "text_per_slide": {
        "max_words": 30,
        "max_seconds": 4,
        "min_font_pt": 36,
    },
    "caption": {
        "min_chars": 200,
        "reason": "~3x views with long captions (TikTok confirmed)",
    },
    "hashtags": {
        "count": [3, 5],
        "rule": "Niche-specific Vietnamese. NEVER generic English.",
    },
    "dimensions": "1080x1920 (9:16)",
    "safe_zone": "Text in center 60-70%",
    "upload": "Photo Mode only. Video slideshow = no carousel algorithm.",
}

SWIPE_PSYCHOLOGY = {
    "zeigarnik_effect": (
        "Incomplete tasks create tension that must be resolved. "
        "Story carousels = 2.3x saves."
    ),
    "information_gap": (
        "Reveal ~70% per slide, withhold ~30%. "
        "Gap not too wide, not too narrow."
    ),
    "completion_bias": (
        "Numbered lists ('7 things...') = must-finish urge. "
        "Odd numbers > even."
    ),
    "goal_gradient": "Past midpoint → people accelerate swiping to end.",
    "micro_commitment": "Each swipe = sunk cost → pressure to continue.",
}

CAROUSEL_HOOK_FORMULAS_VI = [
    {
        "name": "Sai Lầm",
        "template": "[Số] sai lầm đang khiến [vấn đề] tệ hơn",
        "trigger": "fear + completion_bias",
    },
    {
        "name": "Ngược Dòng",
        "template": "Đừng [lời khuyên phổ biến] — đây là lý do",
        "trigger": "contrarian + curiosity",
    },
    {
        "name": "Bí Mật",
        "template": "Điều không ai nói về [chủ đề]",
        "trigger": "curiosity_gap",
    },
    {
        "name": "Danh Sách",
        "template": "[Số] [thứ] dưới [giá] mà [audience] cần",
        "trigger": "completion_bias + utility",
    },
    {
        "name": "Bằng Chứng",
        "template": "[Thứ này] giúp mình [kết quả]",
        "trigger": "proof",
    },
    {
        "name": "So Sánh",
        "template": "[A] vs [B] — cái nào đáng hơn?",
        "trigger": "curiosity + tension",
    },
    {
        "name": "Biến Hình",
        "template": "1 [item] phối [số] kiểu khác nhau",
        "trigger": "novelty + completion_bias",
    },
]

VIETNAM_PATTERNS = {
    "faceless_affiliate": (
        "Canva 9:16 → AI voice (VBEE/FPT/CapCut) "
        "→ trending audio → affiliate link"
    ),
    "regional": {
        "northern": "educational tone",
        "southern": "energetic, trend-savvy",
    },
    "commerce_niches": {
        "beauty": "22.5% TikTok Shop VN GMV",
        "fashion": "12.56%",
    },
    "hashtag_rule": "Vietnamese niche hashtags only. #phukiengiare not #accessories.",
}

VS_VIDEO = {
    "engagement_lift": "81% higher ER (Fanpage Karma, 700K posts)",
    "adoption": "3% of TikTok posts use carousel",
    "save_advantage": "2-3x save rate vs video",
    "tiktok_claims": "2.9x comments, 1.9x likes, 2.6x shares",
}

CAROUSEL_ANTI_PATTERNS = [
    "Video Mode instead of Photo Mode",
    "Weak slide 1 (vague, no number, no question)",
    "Text overload per slide (>30 words)",
    "No CTA on last slide",
    "Mixed dimensions / low resolution",
    "Inconsistent visual style",
    "Empty caption without niche keywords",
]


def build_carousel_context() -> str:
    """Assemble carousel knowledge into a string for injection into the synthesis prompt.

    Similar pattern to build_voice_block() in voice_guide.py.
    """
    psychology_lines = "\n".join(
        f"  - {name}: {desc}" for name, desc in SWIPE_PSYCHOLOGY.items()
    )
    hooks_lines = "\n".join(
        f"  - {h['name']}: \"{h['template']}\" (trigger: {h['trigger']})"
        for h in CAROUSEL_HOOK_FORMULAS_VI
    )
    anti_lines = "\n".join(f"  \u274c {p}" for p in CAROUSEL_ANTI_PATTERNS)
    specs = OPTIMAL_SPECS

    return f"""
KIẾN THỨC CAROUSEL (dựa trên nghiên cứu 700K bài TikTok):

Carousel có lợi thế cấu trúc: tỷ lệ tương tác cao hơn video 81%.
Tỷ lệ lưu gấp 2-3x video. Chỉ 3% bài TikTok dùng carousel — cơ hội lớn.

Thông số tối ưu:
  - Số slide: {specs['slide_count']['min']}-{specs['slide_count']['max']} (lý tưởng: {specs['slide_count']['ideal']})
  - Cấu trúc: {specs['slide_count']['structure']}
  - Chữ mỗi slide: tối đa {specs['text_per_slide']['max_words']} từ, đọc trong {specs['text_per_slide']['max_seconds']}s
  - Caption: tối thiểu {specs['caption']['min_chars']} ký tự + từ khoá ngách
  - Hashtag: {specs['hashtags']['count'][0]}-{specs['hashtags']['count'][1]} hashtag Vietnamese cụ thể

Tâm lý lướt (dùng để giải thích TẠI SAO trong phân tích):
{psychology_lines}

Công thức hook carousel (tiếng Việt):
{hooks_lines}

Lỗi phổ biến giết views:
{anti_lines}
"""
