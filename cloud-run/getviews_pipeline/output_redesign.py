"""Narrative output redesign — format-aware diagnosis synthesis.

Exports:
    FORMAT_ANALYSIS_WEIGHTS   — per-format signal importance map
    NARRATIVE_OUTPUT_STRUCTURE — 4-part narrative structure spec
    PATTERN_EXTRACTION_PROMPT  — instruction block for scene-level pattern analysis
    HOOK_TYPE_NAMES_CONSTRAINT — enforces 14-name fixed hook type taxonomy
    get_analysis_focus()       — returns format-specific analysis focus string
    build_diagnosis_narrative_prompt() — main prompt builder (renamed from build_synthesis_prompt)
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Format → signal weights
# ---------------------------------------------------------------------------

FORMAT_ANALYSIS_WEIGHTS: dict[str, dict[str, str]] = {
    "tutorial": {
        "hook": "critical",
        "face_at": "important",
        "text_overlays": "critical",
        "transitions": "moderate",
        "cta": "critical",
        "transcript": "critical",
    },
    "review": {
        "hook": "critical",
        "face_at": "critical",
        "text_overlays": "important",
        "transitions": "moderate",
        "cta": "important",
        "transcript": "important",
    },
    "haul": {
        "hook": "critical",
        "face_at": "critical",
        "text_overlays": "important",
        "transitions": "moderate",
        "cta": "important",
        "transcript": "important",
    },
    "mukbang": {
        "hook": "critical",
        "face_at": "critical",
        "text_overlays": "moderate",
        "transitions": "skip",    # mukbang: do NOT mention transitions
        "cta": "moderate",
        "transcript": "moderate",
    },
    "dance": {
        "hook": "critical",
        "face_at": "critical",
        "text_overlays": "moderate",
        "transitions": "skip",    # dance/catwalk: do NOT mention CTA or transcript
        "cta": "skip",
        "transcript": "skip",
    },
    "outfit_transition": {
        "hook": "critical",
        "face_at": "critical",
        "text_overlays": "moderate",
        "transitions": "skip",
        "cta": "skip",
        "transcript": "skip",
    },
    "grwm": {
        "hook": "critical",
        "face_at": "critical",
        "text_overlays": "moderate",
        "transitions": "moderate",
        "cta": "important",
        "transcript": "moderate",
    },
    "recipe": {
        "hook": "critical",
        "face_at": "moderate",
        "text_overlays": "critical",
        "transitions": "moderate",
        "cta": "important",
        "transcript": "moderate",
    },
    "storytelling": {
        "hook": "critical",
        "face_at": "critical",
        "text_overlays": "moderate",
        "transitions": "moderate",
        "cta": "moderate",
        "transcript": "critical",
    },
    "before_after": {
        "hook": "critical",
        "face_at": "important",
        "text_overlays": "important",
        "transitions": "moderate",
        "cta": "important",
        "transcript": "moderate",
    },
    "comparison": {
        "hook": "critical",
        "face_at": "important",
        "text_overlays": "important",
        "transitions": "moderate",
        "cta": "important",
        "transcript": "important",
    },
    "vlog": {
        "hook": "critical",
        "face_at": "critical",
        "text_overlays": "moderate",
        "transitions": "moderate",
        "cta": "moderate",
        "transcript": "moderate",
    },
    "pov": {
        "hook": "critical",
        "face_at": "important",
        "text_overlays": "important",
        "transitions": "moderate",
        "cta": "moderate",
        "transcript": "important",
    },
    "faceless": {
        "hook": "critical",
        "face_at": "skip",
        "text_overlays": "critical",
        "transitions": "moderate",
        "cta": "critical",
        "transcript": "critical",
    },
    "other": {
        "hook": "critical",
        "face_at": "important",
        "text_overlays": "important",
        "transitions": "moderate",
        "cta": "moderate",
        "transcript": "moderate",
    },

    # ── Carousel formats ──────────────────────────────────────────────────────
    # Carousel metrics differ from video: slide-native signals replace video signals.
    # Transitions/s, face_appears_at (timed), audio, and transcript are all skipped.
    # has_face on slide 0 is the carousel equivalent of face_appears_at for video.
    "carousel": {
        "hook_slide":             "primary",    # slide 1 = the hook; no autoplay to carry it
        "slide_count":            "primary",    # too few = thin, too many = drop-off
        "text_density":           "primary",    # per-slide text amount — too dense = abandonment
        "visual_consistency":     "primary",    # same design style across slides → brand trust
        "cta_slide":              "primary",    # last slide CTA — highest-leverage moment
        "content_arc":            "primary",    # how content flows: list/story/before_after/etc.
        "visual_energy":          "skip",       # no transitions in carousel
        "music_sync":             "skip",       # irrelevant — no audio at swipe point
        "transitions_per_second": "skip",       # does not apply to static images
        "face_appears_at":        "skip",       # use slides[0].has_face instead
        "audio_quality":          "skip",       # no audio analysis
        "transcript":             "skip",       # no speech
    },
    "carousel_product_roundup": {
        # e.g. "5 phụ kiện dưới 200K" — slide_count matters more (too few = thin)
        "hook_slide":             "primary",
        "slide_count":            "critical",   # more slides = more value perceived
        "text_density":           "primary",    # price/name on each slide
        "visual_consistency":     "primary",
        "cta_slide":              "primary",
        "content_arc":            "primary",    # should be 'list'
        "transitions_per_second": "skip",
        "face_appears_at":        "skip",
        "audio_quality":          "skip",
        "transcript":             "skip",
    },
    "carousel_tutorial": {
        # e.g. "3 bước chăm sóc da" — text_density more important (steps need clear text)
        "hook_slide":             "primary",
        "slide_count":            "primary",    # too many steps = cognitive overload
        "text_density":           "critical",   # each step must be readable
        "visual_consistency":     "primary",
        "cta_slide":              "primary",
        "content_arc":            "critical",   # should be 'tutorial_steps'
        "transitions_per_second": "skip",
        "face_appears_at":        "skip",
        "audio_quality":          "skip",
        "transcript":             "skip",
    },
    "carousel_story": {
        # e.g. "Câu chuyện mua hàng" or emotional narrative — progression matters
        "hook_slide":             "critical",   # cliffhanger on slide 1 critical
        "slide_count":            "primary",
        "text_density":           "primary",
        "visual_consistency":     "primary",
        "cta_slide":              "primary",
        "content_arc":            "critical",   # should be 'story'
        "transitions_per_second": "skip",
        "face_appears_at":        "skip",
        "audio_quality":          "skip",
        "transcript":             "skip",
    },
}

# ---------------------------------------------------------------------------
# 4-part narrative output structure
# ---------------------------------------------------------------------------

NARRATIVE_OUTPUT_STRUCTURE = """
## CẤU TRÚC OUTPUT — 4 PHẦN (KHÔNG đánh số, KHÔNG dùng heading markdown)

**PHẦN 1 — CÔNG THỨC ĐANG CHẠY (niche pattern)**
Mở đầu bằng pattern của niche, KHÔNG phải điểm số video người dùng.
Format: "Trong [tên niche], [X]% top video tháng này dùng [công thức] — [lý do ngắn gọn tại sao chạy]."
Dùng hook_distribution, format_distribution từ niche_norms. Trích corpus_size.
Tối đa 3-4 câu. KHÔNG đề cập video người dùng ở phần này.

**PHẦN 2 — VIDEO CỦA BẠN SO VỚI CÔNG THỨC ĐÓ**
Verdict 1-2 câu: "Video bạn [X]x so với mức trung bình của niche [tên niche]."
Sau đó chẩn đoán từng yếu tố THEO THỨ TỰ QUAN TRỌNG của format (xem FORMAT_ANALYSIS_WEIGHTS):
- Mỗi yếu tố: **Label: [🔴🟡🟢]** + 1 câu mô tả cụ thể + "Chạy vì:" hoặc "Gợi ý:"
- Bỏ qua yếu tố có weight = "skip" cho format này
- Nếu yếu tố "critical" mà thiếu data: ghi "(không có dữ liệu)" và bỏ qua

**PHẦN 3 — VIDEO THAM CHIẾU (phân tích riêng từng video)**
Phân tích 3 reference_videos. Với mỗi video:
- "@handle — [views] views — hook: [tên hook type] — [days_ago] ngày trước"
- 1-2 câu mô tả cụ thể CẢNH (nếu có scenes) và TẠI SAO chạy
- Xuất video_ref JSON block ngay sau
Format JSON bắt buộc: {"type": "video_ref", "video_id": "<id>", "handle": "@<handle>", "views": <số>, "days_ago": <số>, "breakout": <số nếu >1>}

**PHẦN 4 — VIDEO TIẾP THEO**
1 khuyến nghị duy nhất — không phải danh sách 5-7 điểm.
Format: "Video tiếp: [1 câu hành động cụ thể]."
Kết thúc bắt buộc bằng Hook template: "[câu mở đầu dùng [ngoặc vuông] tiếng Việt cho placeholder]"
"""

# ---------------------------------------------------------------------------
# Pattern extraction from scenes
# ---------------------------------------------------------------------------

PATTERN_EXTRACTION_PROMPT = """
## PHÂN TÍCH CẢNH (scenes) — PATTERN EXTRACTION

Khi reference_videos có dữ liệu scenes, trích xuất pattern cảnh của từng video:
Format: "[format]([thời gian]s) → [format]([thời gian]s) → ..."
Ví dụ: "face_to_camera(0-3s) → demo(3-15s) → face_to_camera(15-25s)"

Dùng pattern này để giải thích TẠI SAO video chạy tốt ở phần PHẦN 3.
KHÔNG liệt kê từng cảnh một — tổng hợp thành pattern ngắn gọn.

Nếu không có scenes data: bỏ qua, phân tích dựa trên hook_analysis và metadata.
"""

# ---------------------------------------------------------------------------
# Hook type names — fixed taxonomy (14 names)
# ---------------------------------------------------------------------------

HOOK_TYPE_NAMES_CONSTRAINT = """
Tên loại hook PHẢI dùng đúng tên trong danh sách sau. KHÔNG tự đặt tên mới:
Cảnh Báo, Giá Sốc, Phản Ứng, So Sánh, Bóc Phốt, Hướng Dẫn, Kể Chuyện,
POV, Bằng Chứng, Tò Mò / Gợi Mở, Tuyên Bố Mạnh, Câu Hỏi, Nỗi Đau, Đu Trend.

✅ "Hook: Tuyên Bố Mạnh"   ❌ "Hook: Khẳng Định Mạnh Mẽ"
✅ "Hook: Đu Trend"         ❌ "Hook: Theo Trend"
✅ "Hook: Tò Mò / Gợi Mở"  ❌ "Hook: Gây Tò Mò"
"""

# Canonical English hook type enum → Vietnamese display name (14-name fixed list).
# Keyed by all values that can appear in analysis_json.hook_analysis.hook_type.
HOOK_TYPE_VI: dict[str, str] = {
    "warning": "Cảnh Báo",
    "price_shock": "Giá Sốc",
    "shock_stat": "Giá Sốc",        # shock_stat closest to price_shock in impact
    "reaction": "Phản Ứng",
    "comparison": "So Sánh",
    "expose": "Bóc Phốt",
    "controversy": "Bóc Phốt",      # controversy ≈ expose in Vietnamese creator vocab
    "how_to": "Hướng Dẫn",
    "story_open": "Kể Chuyện",
    "pov": "POV",
    "social_proof": "Bằng Chứng",
    "curiosity_gap": "Tò Mò / Gợi Mở",
    "bold_claim": "Tuyên Bố Mạnh",
    "challenge": "Tuyên Bố Mạnh",   # challenge often functions as bold claim
    "question": "Câu Hỏi",
    "pain_point": "Nỗi Đau",
    "trend_hijack": "Đu Trend",
    "none": "",
    "other": "",
}


def hook_type_vi(hook_type: str) -> str:
    """Return the Vietnamese display name for a canonical hook type enum value.

    Returns an empty string for unknown or absent hook types so callers can
    decide whether to omit the field rather than showing a raw English enum.
    """
    return HOOK_TYPE_VI.get((hook_type or "").lower(), "")


# ---------------------------------------------------------------------------
# Format-specific analysis focus
# ---------------------------------------------------------------------------

_FORMAT_FOCUS_MAP: dict[str, str] = {
    "tutorial": (
        "Format TUTORIAL — ưu tiên: CTA lưu, text overlay hướng dẫn, transcript rõ từng bước. "
        "KHÔNG nhận xét về transitions (không quan trọng cho format này)."
    ),
    "review": (
        "Format REVIEW — ưu tiên: face_at (độ tin cậy), hook type (cảnh báo/bóc phốt thường thắng), "
        "CTA lưu hoặc follow. Transcript hỗ trợ nhưng không bắt buộc."
    ),
    "haul": (
        "Format HAUL — ưu tiên: hook reveal sản phẩm ngay frame 1, face_at, "
        "CTA shop/link_bio. Không cần text overlay nhiều."
    ),
    "mukbang": (
        "Format MUKBANG — ưu tiên: face_at, hook âm thanh/ASMR, năng lượng xuyên suốt. "
        "KHÔNG đề cập transitions hay CTA — không phù hợp format này."
    ),
    "dance": (
        "Format DANCE/CATWALK — ưu tiên: hook visual frame đầu, nhịp theo nhạc. "
        "KHÔNG đề cập CTA, transcript, hay text overlay — không phù hợp format này."
    ),
    "outfit_transition": (
        "Format OUTFIT TRANSITION — ưu tiên: hook visual, transition timing theo nhịp nhạc. "
        "KHÔNG đề cập CTA hay transcript."
    ),
    "grwm": (
        "Format GRWM — ưu tiên: face_at, hook personal/relatable, CTA follow. "
        "Text overlay hỗ trợ nhưng không bắt buộc."
    ),
    "recipe": (
        "Format RECIPE/CÔNG THỨC — ưu tiên: text overlay từng bước, hook nguyên liệu/thành phẩm, "
        "CTA lưu. Face_at ít quan trọng hơn các format khác."
    ),
    "storytelling": (
        "Format KỂ CHUYỆN — ưu tiên: hook mở đầu câu chuyện, transcript mạch lạc, "
        "hook type thường là Kể Chuyện hoặc POV."
    ),
    "before_after": (
        "Format BEFORE/AFTER — ưu tiên: hook reveal kết quả, text overlay stages, "
        "CTA lưu/follow. Transitions quan trọng để tạo contrast."
    ),
    "comparison": (
        "Format SO SÁNH — ưu tiên: hook loại nào tốt hơn, text overlay rõ tiêu chí, "
        "CTA comment để tạo engagement."
    ),
    "vlog": (
        "Format VLOG — ưu tiên: face_at, hook 'một ngày của tôi', CTA follow. "
        "Năng lượng và authenticity quan trọng hơn text overlay."
    ),
    "pov": (
        "Format POV — ưu tiên: hook setup situation, text overlay xác nhận scenario, "
        "hook type thường là POV hoặc Nỗi Đau."
    ),
    "faceless": (
        "Format FACELESS — ưu tiên: text overlay (thay thế face), hook visual sản phẩm, "
        "CTA lưu/mua. Face_at không áp dụng cho format này."
    ),
    "other": (
        "Format chưa phân loại — phân tích theo thứ tự chuẩn: hook → face_at → text_overlay → "
        "transitions → CTA."
    ),
}


def get_analysis_focus(content_format: str) -> str:
    """Return the format-specific analysis focus instruction string."""
    return _FORMAT_FOCUS_MAP.get(content_format, _FORMAT_FOCUS_MAP["other"])


# ---------------------------------------------------------------------------
# Main prompt builder
# ---------------------------------------------------------------------------

def build_diagnosis_narrative_prompt(
    voice_block: str,
    examples_block: str,
    anti_patterns: str,
    content_format: str,
    niche_name: str,
    corpus_size: int,
    niche_norms: dict[str, Any],
    reference_videos: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
) -> str:
    """V2 diagnosis synthesis prompt — narrative structure, format-aware.

    Args:
        voice_block:       Output of build_voice_block() — voice rules + examples.
        examples_block:    Additional examples string (pass "" if already in voice_block).
        anti_patterns:     ANTI_PATTERNS constant from voice_guide.
        content_format:    Detected format string (e.g. "tutorial", "mukbang", "dance").
        niche_name:        Human-readable niche name (e.g. "skincare", "ẩm thực").
        corpus_size:       Number of videos in corpus for this niche (last 30 days).
        niche_norms:       Dict from niche_intelligence materialized view.
        reference_videos:  List of reference video dicts with analysis + metadata.
        user_analysis:     Gemini extraction result for the user's video.
        user_stats:        User video stats dict (views, breakout_multiplier, etc.).
    """
    analysis_focus = get_analysis_focus(content_format)
    niche_norms_json = json.dumps(niche_norms, ensure_ascii=False, indent=2)
    ref_videos_json = json.dumps(reference_videos, ensure_ascii=False, indent=2)
    user_analysis_json = json.dumps(user_analysis, ensure_ascii=False, indent=2)
    user_stats_json = json.dumps(user_stats, ensure_ascii=False, indent=2)

    examples_section = f"\n{examples_block}\n" if examples_block.strip() else ""

    return f"""{voice_block}

---

{HOOK_TYPE_NAMES_CONSTRAINT}

---

{PATTERN_EXTRACTION_PROMPT}

---

{NARRATIVE_OUTPUT_STRUCTURE}

---

## FORMAT-SPECIFIC FOCUS

Format được phát hiện: **{content_format}**

{analysis_focus}

---

## DỮ LIỆU ĐẦU VÀO

**Niche:** {niche_name}
**Corpus size (30 ngày):** {corpus_size} video

**Niche norms (từ niche_intelligence):**
{niche_norms_json}

**User video analysis (Gemini extraction):**
{user_analysis_json}

**User video stats:**
{user_stats_json}

**Reference videos (3 top-performing):**
{ref_videos_json}
{examples_section}
---

## QUY TẮC BẮT BUỘC

R1: KHÔNG tự giới thiệu. KHÔNG "Chào bạn". Nhảy thẳng vào PHẦN 1 — niche pattern.
R2: Mở đầu bằng CÔNG THỨC CỦA NICHE, không phải điểm số video người dùng.
R3: "Chạy vì:" tối đa 1-2 câu. Không giải thích dài dòng.
R4: KHÔNG fabricate metrics. Chỉ dùng số thật từ data JSON.
R5: Hook type phải từ 14 tên cố định. Không đặt tên mới.
R6: Bỏ qua yếu tố có weight "skip" cho format {content_format}.
R7: 3 reference videos BẮT BUỘC — video_ref JSON block cho mỗi video.
R8: Hook template BẮT BUỘC ở cuối PHẦN 4.
R9: 1 khuyến nghị duy nhất ở PHẦN 4, không phải danh sách.
R10: Số dùng format Vietnamese: 1.200 (hàng nghìn), 3,2x (thập phân).
R11: KHÔNG dùng heading markdown (##, ###). Dùng **bold** cho label.
R12: KHÔNG đánh số section.
R13: Hoàn thành đủ 4 phần — không truncate.

Viết chẩn đoán ngay."""
