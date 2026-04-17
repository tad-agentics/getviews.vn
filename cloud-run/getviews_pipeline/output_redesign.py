"""Narrative output redesign — format-aware diagnosis synthesis.

Exports:
    FORMAT_ANALYSIS_WEIGHTS            — per-format signal importance map (video + carousel)
    NARRATIVE_OUTPUT_STRUCTURE         — 4-part narrative structure spec (video)
    CAROUSEL_NARRATIVE_OUTPUT_STRUCTURE — 2-layer + 4-part narrative structure spec (carousel)
    PATTERN_EXTRACTION_PROMPT          — instruction block for scene-level pattern analysis
    HOOK_TYPE_NAMES_CONSTRAINT         — enforces 15-name fixed hook type taxonomy
    get_analysis_focus()               — returns format-specific analysis focus string (video)
    get_carousel_analysis_focus()      — returns carousel sub-format focus string
    build_diagnosis_narrative_prompt() — video diagnosis prompt builder
    build_carousel_diagnosis_narrative_prompt() — carousel diagnosis prompt builder
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Format → signal weights
# ---------------------------------------------------------------------------

# ━━━ TAXONOMY LOCK ━━━
# Keys here are the canonical content_format values written by classify_format()
# in corpus_ingest.py. These two must stay in sync — see the TAXONOMY LOCK comment
# in classify_format() for the full list of downstream dependencies before changing.
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
## CẤU TRÚC OUTPUT — 5 PHẦN (KHÔNG đánh số, KHÔNG dùng heading markdown)

**PHẦN 0 — PHÂN PHỐI (luôn đánh giá TRƯỚC nội dung)**
Đây là bộ lọc đầu tiên — ER cao + views thấp = vấn đề phân phối, không phải nội dung.
Mở đầu bắt buộc: "**[views] views · [likes] likes · [shares] shares · [bookmarks] lưu**" — dùng số thật từ user_stats, format 1.234 cho số nghìn. Tính ER = (likes+comments+shares)/views×100 và ghi rõ.
Đánh giá theo thứ tự:
1. Hashtag: so sánh hashtag của video với pct_has_specific_hashtags trong niche_norms.
   - Hashtag chung chung (#trending, #fyp, #viral) = thuật toán không biết đẩy cho ai → 🔴
   - Có hashtag cụ thể cho ngách + ≤10 total hashtag = 🟢
   - Thiếu hashtag hoặc dùng hỗn hợp = 🟡 kèm gợi ý cụ thể
2. Caption: so sánh với pct_has_caption_text trong niche_norms.
   - Không có caption hoặc <50 ký tự = mất ~3x tìm kiếm tiềm năng → 🔴
   - Caption ≥100 ký tự + từ khoá ngách = 🟢
3. Âm thanh: nếu niche_norms có pct_original_sound — video dùng âm thanh gốc hay trending?
   - Chỉ đề cập nếu có dữ liệu pct_original_sound trong niche_norms
4. Kết luận: 1 câu thẳng thắn — phân phối hay nội dung là vấn đề chính? Chọn 1, không né.
   - Nếu phân phối là vấn đề: nói rõ để creator fix phân phối TRƯỚC khi nghĩ đến nội dung
   - Nếu phân phối ổn: xác nhận và chuyển sang phần nội dung
Tối đa 4-5 dòng. KHÔNG phân tích nội dung ở phần này.

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
Phân tích tất cả reference_videos. Viết TOÀN BỘ phân tích text trước, sau đó xuất TẤT CẢ video_ref JSON blocks LIÊN TIẾP nhau ở cuối — KHÔNG xen kẽ JSON vào giữa các đoạn text.

Với mỗi video (phần text):
- "@handle — [views] views — hook: [tên hook type] — [days_ago] ngày trước"
- 1-2 câu mô tả cụ thể CẢNH (nếu có scenes) và TẠI SAO chạy

Sau khi kết thúc tất cả phân tích text, xuất các JSON blocks LIÊN TIẾP:
{"type": "video_ref", "video_id": "<id>", "handle": "@<handle>", "views": <số>, "days_ago": <số>, "breakout": <số nếu >1>, "thumbnail_url": "<thumbnail_url từ metadata nếu có, nếu không bỏ qua field này>"}

Thứ tự ĐÚNG:
  @handle1 — ... — câu mô tả...
  @handle2 — ... — câu mô tả...
  @handle3 — ... — câu mô tả...
  {"type":"video_ref","video_id":"id1",...}
  {"type":"video_ref","video_id":"id2",...}
  {"type":"video_ref","video_id":"id3",...}

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
POV, Bằng Chứng, Tò Mò / Gợi Mở, Tuyên Bố Mạnh, Câu Hỏi, Nỗi Đau, Đu Trend, Bí Mật / Nội Bộ.

✅ "Hook: Tuyên Bố Mạnh"      ❌ "Hook: Khẳng Định Mạnh Mẽ"
✅ "Hook: Đu Trend"            ❌ "Hook: Theo Trend"
✅ "Hook: Tò Mò / Gợi Mở"     ❌ "Hook: Gây Tò Mò"
✅ "Hook: Bí Mật / Nội Bộ"    ❌ "Hook: Insider" hoặc "Hook: Bí Mật"
"""

# Canonical English hook type enum → Vietnamese display name (14-name fixed list).
# Keyed by all values that can appear in analysis_json.hook_analysis.hook_type.
HOOK_TYPE_VI: dict[str, str] = {
    "warning": "Cảnh Báo",
    "price_shock": "Giá Sốc",
    "shock_stat": "Thống Kê Gây Sốc",
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
    "insider": "Bí Mật / Nội Bộ",
    "secret": "Bí Mật / Nội Bộ",    # "secret" ≈ insider in Vietnamese creator vocab
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
    wants_directions: bool = False,
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
        wants_directions:  If True, appends 4-5 content direction suggestions after diagnosis.
    """
    analysis_focus = get_analysis_focus(content_format)
    niche_norms_json = json.dumps(niche_norms, ensure_ascii=False, indent=2)
    ref_videos_json = json.dumps(reference_videos, ensure_ascii=False, indent=2)
    user_analysis_json = json.dumps(user_analysis, ensure_ascii=False, indent=2)
    user_stats_json = json.dumps(user_stats, ensure_ascii=False, indent=2)

    examples_section = f"\n{examples_block}\n" if examples_block.strip() else ""

    directions_block = ""
    if wants_directions:
        directions_block = """

---

## GỢI Ý HƯỚNG CONTENT VIDEO

Người dùng yêu cầu gợi ý định dạng nội dung video.
Sau phần chẩn đoán, thêm phần **"Hướng content video cho ngách này"** với 4-5 công thức cụ thể.
Mỗi hướng gồm: tên công thức, hook type (dùng đúng 14 tên cố định), cấu trúc beat ngắn (3-4 beat),
lý do chạy trong niche này (1 câu), hook template điền vào ([ngoặc vuông] cho placeholder).
Không lặp lại định dạng đã được chẩn đoán ở phần trên — gợi ý hướng mới chưa thử.
"""

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

**Reference videos (top-performing):**
{ref_videos_json}
{examples_section}
---

## QUY TẮC BẮT BUỘC

R1: KHÔNG tự giới thiệu. KHÔNG "Chào bạn". Nhảy thẳng vào PHẦN 0 — phân phối.
R2: Mở PHẦN 1 bằng CÔNG THỨC CỦA NICHE, không phải điểm số video người dùng.
R3: "Chạy vì:" tối đa 1-2 câu. Không giải thích dài dòng.
R4: KHÔNG fabricate metrics. Chỉ dùng số thật từ data JSON.
R5: Hook type phải từ 14 tên cố định. Không đặt tên mới.
R6: Bỏ qua yếu tố có weight "skip" cho format {content_format}.
R7: Tất cả reference videos BẮT BUỘC — xuất video_ref JSON blocks LIÊN TIẾP ở cuối PHẦN 3, KHÔNG xen kẽ với text mô tả.
R8: Hook template BẮT BUỘC ở cuối PHẦN 4.
R9: 1 khuyến nghị duy nhất ở PHẦN 4, không phải danh sách.
R10: Số dùng format Vietnamese: 1.200 (hàng nghìn), 3,2x (thập phân).
R11: KHÔNG dùng heading markdown (##, ###). Dùng **bold** cho label.
R12: KHÔNG đánh số section.
R13: Hoàn thành đủ 5 phần (bao gồm PHẦN 0 — Phân phối) — không truncate.
{directions_block}
Viết chẩn đoán ngay."""


# ---------------------------------------------------------------------------
# Carousel narrative output structure — 2-layer + 4-part
# Mirrors NARRATIVE_OUTPUT_STRUCTURE but replaces video signals with slide signals.
# ---------------------------------------------------------------------------

CAROUSEL_NARRATIVE_OUTPUT_STRUCTURE = """
## CẤU TRÚC OUTPUT CAROUSEL — 2 TẦNG PHÂN TÍCH

**TẦNG 1 — PHÂN PHỐI (luôn đánh giá TRƯỚC nội dung)**
Đây là tầng quyết định — ER cao + views thấp = vấn đề phân phối, không phải nội dung.

PHẦN 1A — CÔNG THỨC CAROUSEL TRONG NGÁCH (niche pattern)
Mở đầu bằng pattern của ngách, KHÔNG phải điểm số carousel người dùng.
Format: "Trong [tên ngách], carousel [X]% top post tháng này dùng [arc / hook type] — [lý do ngắn gọn tại sao chạy]."
Dùng hook_distribution, content_arc_distribution từ niche_norms nếu có. Trích corpus_size.
Nếu niche_norms có pct_with_vi_hashtags hoặc pct_has_caption_text: thêm 1 câu về chuẩn phân phối ngách.
Ví dụ: "[X]% top carousel trong ngách dùng hashtag tiếng Việt cụ thể (không phải #trending #ootd) và caption ≥200 ký tự."
Tối đa 3-4 câu. KHÔNG đề cập carousel người dùng ở phần này.

PHẦN 1B — PHÂN PHỐI CAROUSEL NÀY
Mở đầu bắt buộc: "**[views] views · [likes] likes · [shares] shares · [bookmarks] lưu**" — dùng số thật từ user_stats, format 1.234 cho số nghìn.
Sau đó phân tích theo thứ tự:
1. Hashtag: tiếng Việt + cụ thể ngách không? Hashtag tiếng Anh chung chung = thuật toán không biết đẩy cho ai.
2. Caption: ≥200 ký tự + từ khoá ngách không? Caption ngắn = mất ~3x views tiềm năng.
3. ER vs views: tính ER = (likes+comments+shares)/views×100, so với mức niche — nói thẳng con số.
4. Upload mode: dấu hiệu Photo Mode vs video slideshow nếu có trong metadata.
Kết luận: phân phối hay nội dung là vấn đề chính — chọn 1, không né.

---

**TẦNG 2 — LOGIC LƯỚT (slide-by-slide swipe analysis)**
Carousel yêu cầu LƯỚT — mỗi lần lướt là 1 quyết định chủ động. Khác hoàn toàn với video autoplay.

PHẦN 2A — CAROUSEL NÀY SO VỚI NGÁCH
Verdict 1-2 câu: "[X]x so với mức trung bình của ngách [tên ngách] — dựa trên [corpus_size] carousel tháng này."
Sau đó đánh giá từng điểm THEO THỨ TỰ QUAN TRỌNG của format (xem FORMAT_ANALYSIS_WEIGHTS carousel):
- Mỗi điểm: **Label: [🔴🟡🟢]** + 1 câu cụ thể từ slides data + "Chạy vì:" hoặc "Gợi ý:"
- Trích slides[].index, text_on_slide, has_face, text_density, word_count khi hữu ích
- NẾU slides[].text_on_slide có nội dung: PHẢI trích dẫn text đó khi phân tích slide đó
- Giải thích bằng tên tâm lý lướt: completion bias, information gap, Zeigarnik effect, goal gradient, micro-commitment
- KHÔNG đề cập: transitions/s, face_appears_at theo giây, audio, watch time

Đánh giá 4 điểm quyết định lướt:
① Slide 1 → dừng lướt + tạo lý do lướt tiếp (hook + swipe trigger)
② Slide 1→2 → khoảng trống thông tin (information gap, completion bias, narrative tension)
③ Momentum slide giữa → giá trị mới mỗi slide? ≤30 từ/slide? Thiết kế đồng nhất?
④ Slide cuối → chuyển đổi: CHỈ 1 CTA, tỷ lệ lưu >3% = tốt, >5% = xuất sắc

PHẦN 2B — CAROUSEL THAM CHIẾU (phân tích riêng từng carousel)
Phân tích tất cả reference_carousels. Viết TOÀN BỘ phân tích text trước, sau đó xuất TẤT CẢ video_ref JSON blocks LIÊN TIẾP ở cuối phần này — KHÔNG xen kẽ JSON vào giữa các đoạn text.

Với mỗi carousel (phần text):
- "@handle — [views] views — arc: [content_arc] — [days_ago] ngày trước"
- 1-2 câu mô tả cụ thể LOGIC LƯỚT và TẠI SAO chạy (dùng tên tâm lý lướt)

Sau khi kết thúc tất cả phân tích text, xuất các JSON blocks LIÊN TIẾP:
{"type": "video_ref", "video_id": "<id>", "handle": "@<handle>", "views": <số>, "days_ago": <số>, "breakout": <số nếu >1>, "thumbnail_url": "<thumbnail_url từ metadata nếu có, nếu không bỏ qua field này>"}

PHẦN 2C — CAROUSEL TIẾP THEO
1 khuyến nghị duy nhất — không phải danh sách 5-7 điểm.
Format: "Carousel tiếp: [1 câu hành động cụ thể — arc + hook slide 1 + CTA slide cuối]."
Kết thúc bắt buộc bằng Hook template slide 1: "[câu hook dùng [ngoặc vuông] tiếng Việt cho placeholder]"
"""

# ---------------------------------------------------------------------------
# Carousel format-specific analysis focus
# ---------------------------------------------------------------------------

_CAROUSEL_FORMAT_FOCUS_MAP: dict[str, str] = {
    "carousel": (
        "Format CAROUSEL (chung) — ưu tiên: hook_slide (slide 1 = dừng lướt + swipe trigger), "
        "content_arc (list/story/before_after/comparison/tutorial_steps/gallery), "
        "visual_consistency (đồng nhất thiết kế), cta_slide (CTA slide cuối). "
        "KHÔNG đề cập transitions, audio, face_appears_at theo giây."
    ),
    "carousel_product_roundup": (
        "Format CAROUSEL PRODUCT ROUNDUP (danh sách sản phẩm) — ưu tiên: "
        "slide_count (nhiều slide = nhiều giá trị cảm nhận), text_density (giá + tên sản phẩm rõ), "
        "hook_slide (con số + giới hạn giá kích hoạt completion bias). "
        "content_arc PHẢI là 'list'. KHÔNG đề cập audio hay transitions."
    ),
    "carousel_tutorial": (
        "Format CAROUSEL TUTORIAL (hướng dẫn từng bước) — ưu tiên: "
        "text_density CRITICAL (mỗi bước phải đọc được trong ≤4s), "
        "content_arc PHẢI là 'tutorial_steps', slide_count (quá nhiều bước = cognitive overload). "
        "CTA slide cuối nên là 'save' — người xem muốn quay lại xem hướng dẫn."
    ),
    "carousel_story": (
        "Format CAROUSEL STORY (câu chuyện) — ưu tiên: "
        "hook_slide CRITICAL (cliffhanger hoặc bỏ lửng ở slide 1 — Zeigarnik effect), "
        "content_arc PHẢI là 'story', visual_consistency (câu chuyện cần phong cách nhất quán). "
        "Narrative tension phải duy trì đến slide cuối trước khi resolve."
    ),
}


def get_carousel_analysis_focus(carousel_format: str) -> str:
    """Return the carousel sub-format analysis focus instruction string."""
    return _CAROUSEL_FORMAT_FOCUS_MAP.get(
        carousel_format, _CAROUSEL_FORMAT_FOCUS_MAP["carousel"]
    )


# ---------------------------------------------------------------------------
# Carousel diagnosis narrative prompt builder
# ---------------------------------------------------------------------------

def build_carousel_diagnosis_narrative_prompt(
    voice_block: str,
    carousel_knowledge_block: str,
    carousel_synthesis_framing: str,
    carousel_format: str,
    niche_name: str,
    corpus_size: int,
    niche_norms: dict[str, Any],
    reference_carousels: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    wants_directions: bool = False,
) -> str:
    """Carousel v2 diagnosis prompt — 2-layer narrative, format-aware.

    Architecture mirrors build_diagnosis_narrative_prompt() for video but replaces:
    - scene-level pattern extraction → slide-level swipe analysis
    - HOOK_TYPE_NAMES_CONSTRAINT → carousel hook psychology taxonomy
    - NARRATIVE_OUTPUT_STRUCTURE → CAROUSEL_NARRATIVE_OUTPUT_STRUCTURE

    Args:
        voice_block:               Output of build_voice_block().
        carousel_knowledge_block:  Output of carousel_knowledge.build_carousel_context().
        carousel_synthesis_framing: _CAROUSEL_SYNTHESIS_FRAMING from prompts.py.
        carousel_format:           One of: carousel, carousel_product_roundup,
                                   carousel_tutorial, carousel_story.
        niche_name:                Human-readable niche name.
        corpus_size:               Carousel count in corpus for this niche (last 30 days).
        niche_norms:               Dict from niche_intelligence (carousel-filtered).
        reference_carousels:       List of 3 reference carousel dicts with analysis + metadata.
        user_analysis:             Gemini carousel extraction result.
        user_stats:                User carousel stats (views, breakout_multiplier, etc.).
        wants_directions:          If True, appends direction generation instruction.
    """
    analysis_focus = get_carousel_analysis_focus(carousel_format)
    niche_norms_json = json.dumps(niche_norms, ensure_ascii=False, indent=2)
    ref_carousels_json = json.dumps(reference_carousels, ensure_ascii=False, indent=2)
    user_analysis_json = json.dumps(user_analysis, ensure_ascii=False, indent=2)
    user_stats_json = json.dumps(user_stats, ensure_ascii=False, indent=2)

    directions_block = ""
    if wants_directions:
        directions_block = """

---

## GỢI Ý HƯỚNG CONTENT CAROUSEL

Người dùng yêu cầu gợi ý hướng content carousel.
Sau phần chẩn đoán, thêm phần **"Hướng content carousel cho ngách này"** với 4-5 công thức cụ thể.
Mỗi hướng gồm: tên công thức, LOGIC LƯỚT (dùng đúng tên tâm lý: completion bias, information gap, \
Zeigarnik effect, micro-commitment), hook slide 1, nội dung slide giữa, CTA slide cuối.
Kèm gợi ý hashtag tiếng Việt ngách cụ thể + caption mẫu ≥200 ký tự.
"""

    return f"""{voice_block}

---

{carousel_synthesis_framing}

---

{carousel_knowledge_block}

---

{CAROUSEL_NARRATIVE_OUTPUT_STRUCTURE}

---

## FORMAT-SPECIFIC FOCUS

Format được phát hiện: **{carousel_format}**

{analysis_focus}

---

## DỮ LIỆU ĐẦU VÀO

**Ngách:** {niche_name}
**Corpus size (30 ngày):** {corpus_size} carousel

**Niche norms (carousel):**
{niche_norms_json}

**Carousel người dùng — Gemini extraction:**
{user_analysis_json}

**Stats carousel người dùng:**
{user_stats_json}

**3 carousel tham chiếu (top-performing):**
{ref_carousels_json}
{directions_block}

---

## QUY TẮC BẮT BUỘC

R1: KHÔNG tự giới thiệu. KHÔNG "Chào bạn". Nhảy thẳng vào PHẦN 1A — niche pattern carousel.
R2: TẦNG 1 (phân phối) TRƯỚC TẦNG 2 (logic lướt) — luôn luôn.
R3: "Chạy vì:" tối đa 1-2 câu. Không giải thích dài dòng.
R4: KHÔNG fabricate metrics. Chỉ dùng số thật từ data JSON.
R5: NẾU slides[].text_on_slide có nội dung, PHẢI trích dẫn — KHÔNG nói "slide không có chữ".
R6: Bỏ qua tín hiệu video: transitions/s, face_appears_at theo giây, audio, watch time.
R7: 3 reference carousels BẮT BUỘC — video_ref JSON block cho mỗi carousel.
R8: Hook template slide 1 BẮT BUỘC ở cuối PHẦN 2C.
R9: 1 khuyến nghị duy nhất ở PHẦN 2C, không phải danh sách.
R10: Số dùng format Vietnamese: 1.200 (hàng nghìn), 3,2x (thập phân).
R11: KHÔNG dùng heading markdown (##, ###). Dùng **bold** cho label.
R12: KHÔNG đánh số section.
R13: Hoàn thành đủ 2 tầng — không truncate.
R14: Giải thích swipe psychology bằng tên đúng: completion bias, information gap, Zeigarnik effect, goal gradient, micro-commitment.

Viết chẩn đoán ngay."""
