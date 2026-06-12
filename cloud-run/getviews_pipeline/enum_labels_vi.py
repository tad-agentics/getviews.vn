"""Vietnamese display labels for corpus enum values.

Why this module exists: the QA audit on 2026-04-22 (BUG-02) caught raw
enum codes leaking into user-facing copy — ``face_enter``, ``face_with_text``,
``how_to``, ``text_overlay``, etc. were concatenated directly into labels
like ``"face_enter: Speaker's face is visible"`` and ``"Mở face with text"``.
The root cause was ``extract_hook_phases`` doing ``value.replace("_", " ")``
and calling it a day.

Rule: anywhere a model enum value flows into a user-facing string, it MUST
go through ``vi_label(*)`` first. The fallback (``default=<value>``) keeps
the raw code visible in admin / debug surfaces so we can still diagnose
unmapped values, but production UI copy will never show an English enum.
"""

from __future__ import annotations

# Gemini ``first_frame_type`` — first-frame composition.
FIRST_FRAME_VI: dict[str, str] = {
    "face": "Cận mặt",
    "face_with_text": "Cận mặt + chữ",
    "product": "Sản phẩm",
    "text_only": "Chỉ chữ",
    "action": "Hành động",
    "screen_recording": "Quay màn hình",
    "other": "Khác",
}

# ``hook_type`` — same vocabulary as src/lib/constants/hook-names-vi.ts.
HOOK_TYPE_VI: dict[str, str] = {
    "question": "Đặt câu hỏi",
    "bold_claim": "Tuyên bố táo bạo",
    "shock_stat": "Số liệu gây sốc",
    "story_open": "Mở đầu bằng câu chuyện",
    "controversy": "Gây tranh cãi",
    "challenge": "Thử thách",
    "how_to": "Hướng dẫn thực hành",
    "tips_value": "Tips / giá trị nhanh",
    "social_proof": "Chứng minh xã hội",
    "curiosity_gap": "Tạo khoảng trống tò mò",
    "pain_point": "Chạm nỗi đau",
    "trend_hijack": "Bắt trend",
    "fomo_urgency": "FOMO / gấp",
    "warning": "Cảnh báo",
    "reaction": "Phản ứng",
    "comparison": "So sánh",
    "expose": "Bóc phốt",
    "vach_tran": "Vạch trần",
    "pov": "POV",
    "dialect_identity": "Giọng miền",
    "gia_soc": "Giá sốc",
    "price_shock": "Giá sốc",
    "insider": "Nội bộ / insider",
    "secret": "Bí mật",
    "testimonial": "Chia sẻ trải nghiệm",
    "transformation": "Trước & sau",
    "listicle": "Danh sách",
    "product_reveal": "Hé lộ sản phẩm",
    "none": "Khác",
    "other": "Khác",
}

# ``hook_timeline.event`` — what's happening at time t in the opening.
HOOK_TIMELINE_EVENT_VI: dict[str, str] = {
    "face_enter": "Khuôn mặt xuất hiện",
    "first_word": "Lời thoại đầu",
    "text_overlay": "Chữ hiện lên màn hình",
    "sound_drop": "Nhạc/âm thanh bắt đầu",
    "cut": "Cắt cảnh đầu tiên",
    "product_enter": "Sản phẩm xuất hiện",
    "reveal": "Khoảnh khắc chốt hạ",
}

# ``SceneType`` — used across video + script pipelines.
SCENE_TYPE_VI: dict[str, str] = {
    "face_to_camera": "Cận mặt",
    "product_shot": "Cận sản phẩm",
    "screen_recording": "Quay màn hình",
    "broll": "B-roll",
    "text_card": "Thẻ chữ",
    "demo": "Demo sản phẩm",
    "action": "Hành động",
    "other": "Khác",
}

# ``VideoAnalysis.tone`` — creative voice read from Gemini extraction.
VIDEO_TONE_VI: dict[str, str] = {
    "educational": "Giáo dục",
    "entertaining": "Giải trí",
    "emotional": "Cảm xúc",
    "humorous": "Hài hước",
    "inspirational": "Truyền cảm hứng",
    "urgent": "Khẩn trương",
    "conversational": "Trò chuyện",
    "authoritative": "Chuyên gia",
}


# Enum values produced by _carousel_subformat() in pipelines.py.
CAROUSEL_SUBFORMAT_VI: dict[str, str] = {
    "carousel_product_roundup": "So sánh",
    "carousel_tutorial": "Hướng dẫn",
    "carousel_story": "Kể chuyện",
    "carousel": "Ảnh carousel",
}

# ``commerce_intent.conversion_objective`` (models.py _COMMERCE_OBJECTIVES)
# plus the promotion_type values that can substitute for it in
# extract_conversion_objective_signal.
CONVERSION_OBJECTIVE_VI: dict[str, str] = {
    "shop_direct": "Bán hàng TikTok Shop trực tiếp",
    "affiliate_shopee": "Affiliate Shopee",
    "livestream_funnel": "Kéo người xem về livestream",
    "brand_deal": "Hợp tác nhãn hàng (booking)",
    "koc_growth": "Xây kênh KOC",
    "entertainment_first": "Giải trí là chính (chưa bán hàng)",
    # promotion_type fallbacks
    "organic": "Organic (không quảng bá)",
    "affiliate": "Affiliate",
    "brand_partnership": "Hợp tác nhãn hàng",
    "own_product": "Bán sản phẩm của chính mình",
    "ads": "Chạy quảng cáo",
}


# Enrichment ``style_tags`` — production-style chips ("KIỂU SẢN XUẤT").
# Open vocabulary from Gemini; mirrors src/lib/constants/enum-labels-vi.ts
# STYLE_TAG_VI (live audit 2026-06-12: product_showcase / lifestyle_b_roll /
# text_overlay_heavy rendered raw on the report).
STYLE_TAG_VI: dict[str, str] = {
    "product_showcase": "Trưng bày sản phẩm",
    "lifestyle_b_roll": "B-roll đời thường",
    "text_overlay_heavy": "Nhiều chữ trên màn hình",
    "talking_head": "Nói trước camera",
    "voiceover": "Lồng tiếng",
    "voiceover_b_roll": "Lồng tiếng + B-roll",
    "asmr": "ASMR",
    "unboxing": "Đập hộp",
    "before_after": "Trước — sau",
    "tutorial": "Hướng dẫn từng bước",
    "pov": "POV",
    "street_interview": "Phỏng vấn đường phố",
    "skit": "Tiểu phẩm",
    "vlog": "Vlog",
    "green_screen": "Phông xanh",
    "fast_cuts": "Cắt cảnh nhanh",
    "cinematic": "Quay điện ảnh",
    "screen_recording": "Quay màn hình",
}


# Text overlay style — surfaces in script editor + Chế độ quay.
OVERLAY_STYLE_VI: dict[str, str] = {
    "TEXT_TITLE": "Tiêu đề lớn",
    "BOLD_CENTER": "Chữ in đậm ở giữa",
    "BOLD CENTER": "Chữ in đậm ở giữa",
    "SUB_CAPTION": "Phụ đề",
    "SUB-CAPTION": "Phụ đề",
    "QUESTION_XL": "Câu hỏi cỡ lớn",
    "STAT_BURST": "Số liệu nổi bật",
    "LABEL": "Nhãn",
    "NONE": "Không có chữ",
    "": "Không có chữ",
}


def _lookup(table: dict[str, str], value: str | None, default: str | None = None) -> str:
    if not value:
        return default if default is not None else ""
    raw = str(value).strip()
    if raw in table:
        return table[raw]
    # Case-insensitive + space/underscore agnostic lookup so Gemini's
    # stylistic drift ("bold claim" vs "bold_claim", "FACE_ENTER" vs
    # "face_enter") still resolves to Vietnamese.
    norm = raw.lower().replace("-", "_").replace(" ", "_")
    for k, v in table.items():
        if k.lower().replace("-", "_").replace(" ", "_") == norm:
            return v
    return default if default is not None else raw


def first_frame_vi(value: str | None, *, default: str | None = None) -> str:
    return _lookup(FIRST_FRAME_VI, value, default)


def hook_type_vi(value: str | None, *, default: str | None = None) -> str:
    return _lookup(HOOK_TYPE_VI, value, default)


def hook_timeline_event_vi(value: str | None, *, default: str | None = None) -> str:
    return _lookup(HOOK_TIMELINE_EVENT_VI, value, default)


def scene_type_vi(value: str | None, *, default: str | None = None) -> str:
    return _lookup(SCENE_TYPE_VI, value, default)


def overlay_style_vi(value: str | None, *, default: str | None = None) -> str:
    return _lookup(OVERLAY_STYLE_VI, value, default)


def video_tone_vi(value: str | None, *, default: str | None = None) -> str:
    return _lookup(VIDEO_TONE_VI, value, default)


def carousel_subformat_vi(value: str | None, *, default: str | None = None) -> str:
    return _lookup(CAROUSEL_SUBFORMAT_VI, value, default)


def conversion_objective_vi(value: str | None, *, default: str | None = None) -> str:
    return _lookup(CONVERSION_OBJECTIVE_VI, value, default)


def style_tag_vi(value: str | None, *, default: str | None = None) -> str:
    """Mapped Vietnamese, else humanized (underscores → spaces) — never the raw enum."""
    humanized = " ".join(str(value or "").replace("_", " ").replace("-", " ").split())
    return _lookup(STYLE_TAG_VI, value, default if default is not None else humanized)
