"""Gemini prompts for video analysis, batch summary, and strategist diagnosis."""

from __future__ import annotations

import json
from typing import Any

from getviews_pipeline.carousel_knowledge import build_carousel_context
from getviews_pipeline.domain_knowledge import build_domain_knowledge_block
from getviews_pipeline.knowledge_base import (
    build_commerce_structure_block,
    build_hook_formula_instruction,
    build_hook_vocabulary_block,
    build_niche_hook_block,
)
from getviews_pipeline.models import ContentType
from getviews_pipeline.output_redesign import (
    build_carousel_diagnosis_narrative_prompt,
    build_diagnosis_narrative_prompt,
)
from getviews_pipeline.two_axis_taxonomy import (
    build_carousel_extraction_niche_glossary_block,
    build_extraction_niche_glossary_block,
)
from getviews_pipeline.voice_guide import ANTI_PATTERNS, build_voice_block

# ---------------------------------------------------------------------------
# Video analysis prompt — Gemini call 1
# ---------------------------------------------------------------------------

# §14 — extraction prompt (full schema enforced via response_json_schema).
# Vietnamese instructions for transcription / hook quality (HI-9).
# §0 commerce_intent: normative semantics + decision framing live in
# artifacts/docs/short-form-video-taxonomy-vietnam.md (§0); keep slug enums aligned
# with CommerceIntent in models.py.

_VIDEO_EXTRACTION_CORE_VI = """Phân tích video TikTok này. Chỉ trả về JSON khớp schema — không markdown, không lời dẫn.

QUY TẮC BẮT BUỘC:
- audio_transcript: Phiên âm ĐÚNG ngôn ngữ gốc (chủ yếu tiếng Việt). KHÔNG dịch sang tiếng Anh. Giữ dấu đầy đủ (ă â đ ê ô ơ ư …). Chỗ không nghe rõ → ghi "[không rõ]".
- hook_phrase: ĐÚNG nguyên văn lời mở đầu (thường tiếng Việt) — không diễn giải, không dịch. Nếu 3s đầu không có lời, dùng chữ overlay đầu tiên thấy rõ. Khi có khối CAPTION_TIKTOK bên dưới: nếu caption có câu mở/hook thuyết phục (câu hỏi, pain, promise) và overlay 0–3s chỉ là tagline marketing ("coming soon", ngày ra mắt, #newcollection, tên BST) → hook_phrase = câu mở đầu caption (nguyên văn); ghi overlay vào hook_timeline / text_overlay. KHÔNG thay audio_transcript bằng caption.
- hook_timeline: 2–5 sự kiện trong cửa sổ hook 0.0–3.0s; sắp xếp t tăng dần. Mỗi event thuộc một trong: face_enter, first_word, text_overlay, sound_drop, cut, product_enter, reveal. t tính bằng giây, chính xác 0.1s. Bỏ sự kiện không xảy ra trong 3s đầu. Bỏ qua nếu tín hiệu yếu.
- QUAN TRỌNG (GIẢI MÃ HOOK): Mỗi cửa sổ 0.0–0.8s / 0.8–1.8s / 1.8–3.0s chỉ mô tả việc xảy ra trong cửa sổ đó. Trong hook_timeline[].note: không viết "ngay đầu video", "khung hình đầu tiên", "cuối clip" trừ khi khớp hook_timeline[].t (vd t≈0 cho đầu video). Không gắn lời nói @X vào note nếu X không khớp gần t của sự kiện — dùng first_speech_at cho lời mở.
- hook_analysis.hook_type: CHỈ chọn một literal snake_case từ schema (vd: question, bold_claim, shock_stat, story_open, controversy, challenge, how_to, social_proof, curiosity_gap, pain_point, trend_hijack, warning, reaction, comparison, expose, insider, secret, pov, vach_tran, gia_soc, dialect_identity, fomo_urgency, tips_value, none, other) — không dùng tiếng Anh tự do, không dùng nhãn tiếng Việt làm giá trị.
- hook_analysis.hook_layering: single | dual | triple | null — số lớp tín hiệu đồng thời (hình + chữ + beat âm) trong 0–3s; null nếu không chắc.
- hook_analysis.hook_body_contract: true nếu phần thân (khoảng 4–15s) trả lời đúng lời hứa hook; false nếu hook hứa một đằng nội dung một nẻo; null nếu không đủ căn cứ.
- hook_analysis.dialect_detected: hue | quang_nam | southern | northern | none | null — chỉ khi giọng/từ vựng địa phương lộ rõ trong hook; không ép.
- hook_analysis.price_anchor_manipulation_suspected: true nếu neo giá gạch / % giảm gây hiểu nhầm (rủi ro comply TikTok Shop VN); false nếu không áp dụng; null nếu clip không gắn giá/thương mại.
- scenes: Mỗi lần cắt hình, đổi góc máy, hoặc đổi chủ thể rõ → scene mới. Video 15s thường 3–8 scene; 30s có thể 5–15. Mỗi scene điền các chiều phong phú dưới; không chắc → null, không đoán bừa.
- scenes[].framing: close_up | medium | wide | extreme_close_up — khớp định nghĩa schema.
- scenes[].pace: static | slow | medium | fast | cut_heavy — khớp định nghĩa schema.
- scenes[].overlay_style: none | bold_center | sub_caption | chyron | sticker.
- scenes[].subject: face | product | text | action | ambient | mixed.
- scenes[].motion: static | handheld | slow_mo | time_lapse | match_cut.
- scenes[].description: MỘT câu tiếng Việt 12–24 từ, mô tả khung hình thấy được (không phán xét). VD: "Cận mặt creator nói to câu mở, chữ nổi vàng phía trên."
- transitions_per_second: tổng ranh giới scene chia cho độ dài video (giây).
- face_appears_at: timestamp đầu tiên (giây) mặt người nổi bật; không có mặt → null.
- cta: Nguyên văn CTA tiếng Việt ở ~5s cuối hoặc chữ overlay cuối. Có động từ kêu gọi. Không diễn giải / không dịch. Không có lời kêu gọi rõ → null. Chỉ nhắc sản phẩm không động từ → không phải CTA. Chỉ URL/@ không động từ → không phải CTA.
- content_direction.what_works: Yếu tố CẤU TRÚC cụ thể khiến video hiệu quả — vd "mặt khung đầu + hook câu hỏi + cắt 3s/scene". Không khen chung chung.
- target_audience: MỘT cụm tiếng Việt ngắn — video dành cho ai. Cụ thể; tránh "mọi người", "TikTok users".
- pain_points: 0–3 cụm danh từ tiếng Việt — kích thích tâm lý. Không có hook đau → [].
- promotion_type: organic | brand_deal | affiliate | self_promotion — theo watermark, #ad, CTA, link hoa hồng. Mơ hồ → organic.
- commerce_intent (object §0 — luôn điền, kể cả organic):
  - conversion_objective: shop_direct | affiliate_shopee | livestream_funnel | brand_deal | koc_growth | entertainment_first — mục tiêu chuyển đổi chính của clip. Chỉ giải trí / không bán / không dẫn Shop → entertainment_first.
  - product_price_tier: under_150k | 150k_500k | over_500k | not_commerce — giá SP/dịch vụ chính (ước lượng từ lời/overlay); clip không thương mại → not_commerce.
  - creator_type: koc | kos_seller | brand_partner | entertainment | livestream_host — vai người lên hình (KOC review, chủ shop/KOS, brand, host live…).
  - verbal_cta_present: true nếu có lời nói trực tiếp kêu hành động mua/lưu/comment/inbox/vào giỏ rõ ràng; false nếu chỉ nhạc/ngầm.
  - verbal_cta_quote: nguyên văn câu CTA tiếng Việt từ lời (hoặc null).
  - disclosure_present: true nếu có tiết lộ quan hệ thương mại (#qc, tiết lộ giọng, chữ overlay “quảng cáo/tài trợ”…); false nếu không.
  - disclosure_form: hashtag | voice | text_overlay | none — hình thức tiết lộ chính; none nếu disclosure_present=false.
- §11 creator_persona + slang (object — luôn điền creator_persona + slang_terms_used; có thể []):
  - creator_persona: chuyen_gia | ban_than | nguoi_trai_nghiem_that | hai_huoc_vung_mien | chu_shop_kos | anh_chi_mentor | null — persona on-camera chính của clip (một slug).
  - persona_consistency_signals: object với khóa backdrop, costume, catchphrase, camera_angle, speech_register — mỗi giá trị aligned | drift | unknown | null. So sánh “clip này” với pattern thường gặp của creator khi đủ bằng chứng; không chắc → unknown hoặc null toàn object.
  - slang_terms_used: mảng cụm slang tiếng Việt thấy trong audio_transcript + chữ overlay (không dịch).
  - slang_freshness_score: current_quarter | last_quarter | dated | null — mức “hot” của slang vừa liệt kê; null nếu không có slang.
  - loop_architecture_score: số 0.0–1.0 — mức khớp khung mở vs khung cuối để loop/rewatch mượt (cao hơn = composition gợi ý loop); null nếu clip không đọc được cặp mở/đóng.
- §6 âm thanh / mix (object — luôn điền audio_track_role; các field còn lại null nếu không chắc):
  - audio_track_role: trending_sound | original_music | silent | spoken_overlay — vai track chính (nhạc trending vs nhạc gốc vs tắt vs lời đè).
  - sound_dialect_audio: hue | quang_nam | southern | northern | none | null — giọng vùng miền trong nhạc nền / vocal sample (khác dialect lời thoại; không ép).
  - sound_layering: thin | balanced | rich | null — thin = hầu như chỉ một lane (vd chỉ BGM hoặc chỉ VO); rich = BGM + lời rõ + hiệu ứng/ASMR tách lớp; balanced = ở giữa.
- §1 metadata / vùng an toàn (object — luôn điền safe_zone_status + tiktok_account_type_heuristic; trending_vpop_sound null nếu không chắc):
  - safe_zone_status: ok | bottom_overlay_risk | unknown — ok = chữ kêu gọi/giá/CTA quan trọng không nằm vùng ~35% dưới khung (tránh đè nút Shop/giỏ); bottom_overlay_risk = có chữ quan trọng (giá, mua, lưu, link) sát mép dưới trong vùng rủi ro; unknown = không đủ bằng chứng.
  - tiktok_account_type_heuristic: business | personal | unknown — business nếu thấy UI/badge tài khoản doanh nghiệp, cửa hàng, TikTok Shop rõ; personal nếu profile creator thường; unknown nếu không thấy UI đó.
  - trending_vpop_sound: true | false | null — true nếu nhạc nền rõ là V-pop/ballad remix trending Việt Nam đang viral; false nếu trend quốc tế/beat khác; null nếu silent hoặc không chắc.
- §5 hậu kỳ / chữ trên hình (object — null field khi không chắc):
  - color_grading_style: native_capcut | high_key_beauty | desaturated_serious | over_processed | neutral | unknown | null — tông màu tổng thể.
  - text_overlay_font_size_tier: large | medium | small | none | unknown | null — cỡ chữ overlay chính (đọc trên mobile).
  - text_overlay_color_emphasis: true nếu có từ khóa/số tô màu nổi (giá, %, CTA) khác nền; false nếu chữ đơn sắc hoặc không có overlay chữ; null nếu không áp dụng.
- §8 Douyin / nguồn gốc format (object — trong bước extract: luôn để null; server merge sau khi khớp ``douyin_video_corpus``):
  - douyin_origin: null
  - vietnam_adoption_stage: null
  - migration_fit_assessment: null
- §7 hành vi chia sẻ / lưu (khi có — không ép; none nếu không rõ):
  - share_trigger_type: none | utility_reference | emotion_relief | identity_belonging | social_currency_pack | humor_meme | other — lý do chính khiến người xem bấm chia sẻ (tiện ích, cảm xúc, bộc lộ identity, có thể gửi nhóm, hài…).
  - save_trigger_type: none | how_to_checklist | product_deal_sheet | recipe_steps | quote_stat_card | tutorial_bookmark | other — lý do bấm lưu (checklist, deal, công thức…).
- §4 cấu trúc script affiliate + livestream (chỉ điền khi conversion_objective khớp; null nếu không áp dụng):
  - affiliate_script_phases (object): hook_attention, product_showcase, usage_demo, social_proof, closing_cta — mỗi field true | false | null; true = có đủ căn cứ trong clip; false = thiếu hoặc chỉ lướt; null = không đủ frame để chấm.
  - livestream_funnel_demo: teaser_open_loop | balanced | over_complete | null — chỉ khi conversion_objective=livestream_funnel: teaser_open_loop = cố tình mở vòng để kéo vào live; over_complete = demo đủ chi tiết vô tình làm khán giả không cần vào live; balanced = vừa đủ.
- style_tags: 2–5 tag trong danh sách schema: text_overlay_heavy, talking_head, voiceover_only, b_roll_heavy, fast_cuts, slow_reveal, meme_format, before_after, reaction, duet_stitch, green_screen, product_showcase, lifestyle_b_roll, educational_slides, trending_audio. Chỉ tag thấy rõ; không đoán.
- has_human_speaking_to_camera: true nếu có mặt và người đó nói hướng khán giả (hoặc đối thoại với viewer); false nếu faceless hoàn toàn, chỉ ASMR sản phẩm, montage không talking head.
- has_expressed_opinion_or_question: true nếu lời nói / overlay / caption có ý kiến, câu hỏi, hoặc POV cá nhân ("mình", "theo mình"); false nếu thuần mô tả trung tính."""

_HI9_ENRICHMENT_VIDEO = """
=== Nội dung ngữ nghĩa + phân loại hai trục (bắt buộc điền đầy đủ — HI-9) ===
- content_context (object):
  - subject_matter: MỘT câu tiếng Việt — video nói về điều gì (vd: "Review serum vitamin C cho da dầu tại nhà").
  - primary_subjects: 2–6 cụm khóa (sản phẩm, người, bối cảnh).
  - setting: một cụm mô tả bối cảnh quay (phòng ngủ, studio đèn ring, quán cà phê…); không rõ → null.
  - products_mentioned: mảng {name, brand?, category?}; có thể [] nếu không có sản phẩm đặt tên.
  - creator_role: expert | user_reviewer | storyteller | performer | tutorial_host
  - dominant_actions: hành động thấy rõ trong video (cụm tiếng Việt ngắn).
  - content_purpose: educate | entertain | sell | inspire | review | react
  - language_register: casual | formal | youth_slang | expert_jargon
  - topical_hashtags_implied: 3–8 hashtag phù hợp nội dung (có thể không xuất hiện trên caption).

- niche_classification (object) — creator_niche_slug và format_axis CHỈ được chọn từ glossary ngay sau đây (đúng chuỗi snake_case):
  - creator_niche_slug: một giá trị trong glossary creator niches.
  - format_axis: một giá trị trong glossary format_axis — mô tả ĐỊNH DẠNG dựng video, không nhầm với chủ đề sản phẩm.
  - confidence: số 0.0–1.0 — mức tự tin chung cho cặp (niche + format).
  - rationale: MỘT câu tiếng Việt giải thích vì sao chọn đôi slug+axis này.
  - alternative_creator_niche_slug: niche thứ hai từ glossary nếu confidence < 0.8; nếu confidence ≥ 0.8 thì null.
"""

_HI9_VIDEO_FEW_SHOT_VI = """
=== Ví dụ minh hoạ (chỉ là MẪU CẤU TRÚC — bám video thật của bạn, không copy) ===
Ví dụ 1 — Làm đẹp + review_unboxing:
  content_context.subject_matter: "Review serum vitamin C giá học sinh cho da dầu mụn."
  niche_classification.creator_niche_slug: "beauty"
  niche_classification.format_axis: "review_unboxing"
  niche_classification.confidence: 0.91
  niche_classification.rationale: "Cận mặt swatch và so sánh sản phẩm — rõ định dạng review mỹ phẩm trong ngách làm đẹp."
  niche_classification.alternative_creator_niche_slug: null

Ví dụ 2 — Ẩm thực + vlog_daily:
  content_context.subject_matter: "Đi ăn street food đêm ở chợ Hồ Thị Kỷ, quay POV ăn thử."
  niche_classification.creator_niche_slug: "food"
  niche_classification.format_axis: "vlog_daily"
  niche_classification.confidence: 0.88
  niche_classification.rationale: "Đi dạo quay cảnh ăn uống, không công thức từng bước — đúng vlog ẩm thực."
  niche_classification.alternative_creator_niche_slug: "travel"

Ví dụ 3 — Hài + skit_scripted:
  content_context.subject_matter: "Skit chơi lại trend 'khi mẹ hỏi con đi đâu' với twist cuối."
  niche_classification.creator_niche_slug: "comedy"
  niche_classification.format_axis: "skit_scripted"
  niche_classification.confidence: 0.93
  niche_classification.rationale: "Nhiều vai, thoại kịch bản, cài twist — không phải talking head tư vấn."
  niche_classification.alternative_creator_niche_slug: null
"""


def build_video_extraction_system_instruction() -> str:
    """Static extraction instructions + niche glossary → ``system_instruction`` (HI-8)."""
    return (
        _VIDEO_EXTRACTION_CORE_VI
        + _HI9_ENRICHMENT_VIDEO
        + _HI9_VIDEO_FEW_SHOT_VI
        + "\n\n"
        + build_extraction_niche_glossary_block()
    )


# User turn only — static rules live in ``build_video_extraction_system_instruction``.
VIDEO_EXTRACTION_USER_TURN_VI = (
    "Phân tích video đính kèm (khung hình + âm thanh). "
    "Chỉ trả về JSON khớp schema — không markdown, không lời dẫn."
)


def build_video_extraction_user_turn_vi(
    *,
    dual_hook_window: bool,
    hook_window_seconds: float,
    base_fps_display: float | None = None,
) -> str:
    """User turn for ``analyze_video``: single Part vs HI-15 dual-window Parts.

    ``hook_window_seconds`` should match the **clamped** value used on
    ``VideoMetadata.end_offset`` so prompt text cannot disagree with the API.
    ``base_fps_display`` mirrors ``GEMINI_VIDEO_BASE_FPS`` (post-clamp) for copy.
    """
    if not dual_hook_window:
        return VIDEO_EXTRACTION_USER_TURN_VI
    sec = float(hook_window_seconds)
    if sec == int(sec):
        sec_label = str(int(sec))
    else:
        sec_label = str(sec).rstrip("0").rstrip(".")
    bf = float(base_fps_display) if base_fps_display is not None else 1.0
    if bf == int(bf):
        bf_label = str(int(bf))
    else:
        bf_label = str(bf).rstrip("0").rstrip(".")
    return (
        "Hai đoạn video liên tiếp là cùng một clip: "
        f"(1) toàn bộ ở ~{bf_label} FPS cho bối cảnh và chuyển động tổng thể; "
        f"(2) {sec_label} giây đầu ở FPS cao để bắt text overlay / phụ đề cực ngắn "
        "trên hook. "
        "Phân tích khung hình + âm thanh. "
        "Chỉ trả về JSON khớp schema — không markdown, không lời dẫn."
    )


def format_vietnamese_asr_supplement_for_video_extraction_vi(
    segments: list[dict[str, Any]],
) -> str:
    """HI-14 — human-readable Vietnamese block from STT segments (user turn prefix).

    Empty segments → empty string (caller skips injection).
    """
    lines: list[str] = []
    for seg in segments:
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        start = seg.get("start_sec")
        end = seg.get("end_sec")
        if start is not None and end is not None:
            try:
                t0 = float(start)
                t1 = float(end)
                lines.append(f"[{t0:.1f}s–{t1:.1f}s] {text}")
                continue
            except (TypeError, ValueError):
                pass
        lines.append(text)
    if not lines:
        return ""
    body = "\n".join(lines)
    return (
        "Bản ghi tham chiếu (Google STT vi-VN; mốc thời gian gần đúng):\n"
        f"{body}\n"
        "Dùng để bổ trợ trường audio_transcript / lời nói; ưu tiên khớp hình nếu lệch."
    )


# Back-compat + tests: full static block (same text as system_instruction path).
VIDEO_EXTRACTION_PROMPT = build_video_extraction_system_instruction()


_CAROUSEL_EXTRACTION_CORE_VI = """Phân tích carousel ảnh TikTok (các phần ảnh nằm TRƯỚC đoạn text này). Chỉ trả về JSON khớp schema — không markdown, không lời dẫn.

QUY TẮC BẮT BUỘC:
- hook_analysis.hook_phrase: Nguyên văn chữ thấy trên slide 1; không diễn giải. Không chữ → mô tả yếu tố hình ảnh chủ đạo bằng tiếng Việt.
- slides[].text_on_slide: Liệt kê MỌI chữ đọc được trên slide (tiêu đề, giá, watermark, hashtag in trong ảnh). Chỉ dùng [] nếu hoàn toàn không có chữ.
- slides[].text_density: none | low | medium | high — khớp text_on_slide; text_on_slide khác rỗng thì không được none.
- slides[].has_face: true nếu mặt người NỔI BẬT; ngược lại false.
- slides[].has_product: true nếu sản phẩm vật lý là chủ thể chính.
- slides[].word_count: số từ chữ trên slide; không chữ → 0.
- content_arc: list | story | before_after | comparison | tutorial_steps | gallery.
- visual_consistency: consistent | mixed | inconsistent.
- estimated_read_time_seconds: ước lượng thời gian đọc/vuốt hết; ~2s/slide nhiều chữ, ~1s/slide chủ yếu ảnh.
- cta_slide: CHỈ slide cuối. has_cta true nếu có kêu gọi (follow, save, comment, link, mua). cta_type: save | follow | comment | link_bio | shop_cart | null. cta_text nguyên văn hoặc null.
- has_numbered_hook: true nếu slide 1 có số tạo completion bias ("7 cách…", "3 lỗi…").
- swipe_trigger_type: list_momentum | curiosity_chain | narrative_tension | none.
- slides[].swipe_anchor (ME-19): tại sao khán giả vuốt sang slide tiếp? cliffhanger_image | incomplete_text | numbered_progression | curiosity_question | none — một giá trị/slide; none nếu không rõ.
- slides[].layout (ME-19): single_image | split_screen | text_only | photo_with_caption | infographic | meme_format.
- audio_track_role (ME-19, cấp carousel): trending_sound | original_music | silent | spoken_overlay — nhạc nền viral vs nhạc gốc vs tắt vs lời đè.
- dominant_color_palette (ME-19): một cụm ngắn tiếng Việt mô tả tông màu chủ đạo (vd. "pastel hồng + nude"); null nếu không rõ.
- slide_pacing_score (ME-19): số 0.0–1.0 — độ đều phân bổ chữ giữa các slide; pacing đều ~0.8–1.0; lệch nặng ~0.3–0.5; null nếu không đủ cơ sở.
- Map slides đúng batch index được cung cấp."""

_HI9_ENRICHMENT_CAROUSEL = """
=== Nội dung ngữ nghĩa + phân loại hai trục (carousel — HI-16; KHÔNG dùng format_axis của video) ===
- content_context: giống video — subject_matter là MỘT câu tiếng Việt tóm cả carousel (vuốt qua slide); các trường khác lấy tổng thể slide.
- niche_classification: điền creator_niche_slug + **carousel_format_axis** (CHỈ 5 giá trị trong glossary carousel_format_axis); rationale tiếng Việt; confidence 0–1; alternative_creator_niche_slug khi lệch ngách.
- Khớp carousel_format_axis với kiểu vuốt (không chọn talking_head_advice / vlog_daily vì đó là trục video):
  • tutorial_carousel — từng bước, checklist, recipe slides, số thứ tự hướng dẫn.
  • listicle_carousel — "7 điều", "5 lỗi", nhiều bullet ngắn, tips xếp lớp.
  • story_carousel — kể chuyện, POV, twist, tiến triển cảm xúc qua slide.
  • comparison_carousel — before/after, A vs B, bảng so sánh hai phía.
  • gallery_carousel — chủ yếu ảnh/moodboard, ít chữ, aesthetic/lookbook.

Ví dụ JSON (carousel):
  content_context.subject_matter: "Carousel 4 bước chọn serum cho da dầu."
  niche_classification.creator_niche_slug: "beauty"
  niche_classification.carousel_format_axis: "tutorial_carousel"
  niche_classification.confidence: 0.9
  niche_classification.rationale: "Mỗi slide một bước rõ ràng — đúng carousel hướng dẫn trong ngách làm đẹp."
  niche_classification.alternative_creator_niche_slug: null

  content_context.subject_matter: "So sánh iphone cũ vs android tầm trung qua 6 slide."
  niche_classification.creator_niche_slug: "tech_gaming"
  niche_classification.carousel_format_axis: "comparison_carousel"
  niche_classification.confidence: 0.88
  niche_classification.rationale: "Luân phiên hai phía và kết luận ưu nhược — định dạng so sánh."
  niche_classification.alternative_creator_niche_slug: null
"""

def build_carousel_extraction_system_instruction() -> str:
    """Carousel static instructions + carousel two-axis glossary (HI-8 + HI-16)."""
    return (
        _CAROUSEL_EXTRACTION_CORE_VI
        + _HI9_ENRICHMENT_CAROUSEL
        + "\n\n"
        + build_carousel_extraction_niche_glossary_block()
    )


CAROUSEL_EXTRACTION_USER_PREFIX_VI = (
    "Phân tích các slide ảnh đính kèm theo quy tắc hệ thống. "
    "Chỉ trả về JSON khớp schema — không markdown, không lời dẫn."
)

CAROUSEL_EXTRACTION_PROMPT = build_carousel_extraction_system_instruction()


# ---------------------------------------------------------------------------
# Thumbnail / cover-frame analysis — focused one-shot on t=0 frame.
# Called by thumbnail_analysis.analyze_thumbnail. Schema enforced via
# ThumbnailAnalysis.model_json_schema().
# ---------------------------------------------------------------------------

THUMBNAIL_PROMPT = """Analyze this TikTok cover frame for stop-power.
Return ONLY JSON matching the schema — no markdown.

- stop_power_score (0.0–10.0): composite of face presence, facial expression
  intensity, colour contrast, text readability. Calibration examples:
    3 = bored neutral face on beige, no text
    5 = product shot, clean but generic
    7 = face + clear overlay, decent contrast
    9 = extreme close-up startled expression + bold 3-word text, yellow on black
- dominant_element: ONE of face / product / text / environment. Pick the element
  a thumb-sized viewer's eye lands on first, not just what's largest.
- text_on_thumbnail: EXACT visible text, verbatim Vietnamese with diacritics.
  Max 40 chars. null if the frame has no readable text at all (watermarks /
  tiny timestamps don't count).
- facial_expression: REQUIRED when dominant_element=face. Use the 5 listed
  values. null when no face is prominent.
- colour_contrast: high = vibrant or complementary palette (yellow+black,
  red+white, high-saturation). medium = mid-tone, natural. low = washed,
  monochrome, flat.
- why_it_stops: ONE Vietnamese sentence naming the SPECIFIC element —
  not generic praise.
    GOOD: "Mặt lớn cận + biểu cảm ngạc nhiên + chữ vàng trên đen — dừng scroll."
    BAD:  "Hình đẹp và thu hút." (không nêu cụ thể)
  Max 120 chars. If stop_power is low, say WHY it fails
  (e.g. "Ảnh sản phẩm tĩnh, không mặt, màu nhạt — dễ bị scroll qua.")."""





# ---------------------------------------------------------------------------
# Domain knowledge — benchmarks, failure taxonomy, signal hierarchy.
# Voice/persona/anti-patterns live in voice_guide.py (single source of truth).
# Inject _DOMAIN_KNOWLEDGE AFTER {voice} — never instead of it.
# Hook taxonomy injected from knowledge_base.py at module load time.
# ---------------------------------------------------------------------------

_DOMAIN_KNOWLEDGE_TEMPLATE = """
TRÌNH TỰ CHẨN ĐOÁN — luôn đánh giá theo thứ tự này:
1. Hook (3 giây đầu): hook hỏng thì phần còn lại chưa đáng bàn
2. Giữ chân (3s → 50%): khớp lời hứa–nội dung, nhịp độ, pattern interrupt
3. Thân bài (50% → 80%): giá trị, đa dạng cảnh, năng lượng ổn định
4. CTA (20% cuối): cụ thể, thời điểm, dual delivery (lời nói + chữ trên màn hình)

CAROUSEL ẢNH — khi metadata.content_type là "carousel", phân tích theo một đơn vị tổng hợp mỗi slide (xem JSON).
Áp cùng trình tự như câu chuyện vuốt: slide 1 = hook, giữa = giữ chân/thân, slide cuối = CTA/payoff.
Đánh giá tiến triển chữ trên slide và việc carousel có xứng đáng được save — không phải nhịp cắt như phim.

CTA VS HOOK (không gộp lẫn):
- Tên thương hiệu trong hook mở đầu hoặc overlay hook không tự động là "CTA bán hàng".
  Nhìn offer rõ ràng, URL, "link in bio" và thời điểm xuất hiện so với khoảnh khắc hook (thường giữa/cuối).
- Nếu text_overlays có copy hook khác với dòng brand/URL sau → vai trò khác nhau.

THỨ BẬC TÍN HIỆU SẢN XUẤT khi suy luận vấn đề:
khung hình đầu > thời điểm xuất hiện mặt > text overlay > nhịp độ > âm thanh > CTA

CHUẨN HIỆU SUẤT (organic — dùng khi diễn giải số liệu):
- Hook rate (lượt xem 2s ÷ impressions): <25% = yếu  |  25–35% = ổn  |  >40% = mạnh
- Completion rate / tỷ lệ hoàn thành: <40% ≈ chết ~200 lượt xem  |  60–70% = đẩy thuật toán  |  80%+ = ứng viên viral
- Hold rate (15s ÷ 3s): <30% = lời hứa–nội dung lệch  |  >60% = mạnh
- Tương tác theo lượt xem: <1% = yếu  |  3–5% = ổn  |  >6% = rất tốt
- Mặt trong khung đầu: +35% tương tác so với không mặt
- Text overlay khung đầu: +50% giữ chân 3 giây
- Saves = giá trị lâu dài (bookmark để quay lại hoặc mua)
- Shares = tiền tệ xã hội (chia sẻ vì giải trí hoặc đồng cảm)
- Shares ≈ Saves = hiếm — vừa utility vừa entertainment
- Like cao + chỉ số khác thấp = thụ động, thuật toán không khuếch đại mạnh
- Lượt xem thấp + ER tốt + save/bookmark có ý nghĩa: ghép ER với lượt xem — thường là pool phân phối/seed,
  chưa chắc "creative dở" theo mặc định

PHÂN LOẠI LỖI — gọi đúng tên lỗi, không chỉ triệu chứng:
- Hook failure: sụt mạnh 3 giây đầu → sửa khung mở hoặc câu mở đầu
- Promise-content mismatch: giữ 3s tốt, sụt 8–12s → trả lời lời hứa hook nhanh hơn, người xem cảm giác bị lừa
- Pacing failure: tụt dần giữa video → pattern interrupt mỗi 3–4s, không cảnh tĩnh >5s
- CTA failure: giữ chân tốt suốt, chuyển đổi yếu → sharpen CTA cuối
- Duration mismatch: độ dài vượt hợp đồng ngầm của kiểu hook
  (hook dạng "question" hứa trả lời nhanh — 2 phút phá vỡ hợp đồng đó)

{domain_knowledge}

TỪ VỰNG CHUYÊN NGÀNH (giữ tiếng Anh vì creator VN dùng hàng ngày):
- hook rate, completion rate, pattern interrupt, open loop, CTA, dual delivery
- Creative fatigue: hiệu suất giảm do lạm dụng cùng format
- Dead air: giây không có thông tin hình/âm mới — chết trên TikTok
- FYP: For You Page — nơi thuật toán đưa video vào feed
(Từ vựng tiếng Việt đầy đủ → xem voice_guide — voice_guide là nguồn chuẩn)

{hook_vocabulary}

{hook_formula_instruction}

QUY TẮC TRÍCH DẪN VIDEO (P0-2):
Khi nhắc đến video cụ thể từ corpus, LUÔN kèm theo một JSON block trên một dòng riêng ngay sau câu đó:
{{"type": "video_ref", "video_id": "<id>", "handle": "@<handle>", "views": <số>, "days_ago": <số>, "breakout": <số hoặc bỏ qua nếu ≤1>}}

- Chỉ xuất block khi có video_id thật từ dữ liệu JSON bên dưới — KHÔNG tự tạo ID
- Mỗi video chỉ xuất 1 block (không lặp lại cùng video_id)
- Đặt block ngay sau câu nhắc đến video, không gom về cuối bài
- Dùng days_ago từ metadata — không tính lại
"""

# Resolve placeholders once at import — no per-call overhead
_DOMAIN_KNOWLEDGE = _DOMAIN_KNOWLEDGE_TEMPLATE.format(
    domain_knowledge=build_domain_knowledge_block(),
    hook_vocabulary=build_hook_vocabulary_block(),
    hook_formula_instruction=build_hook_formula_instruction(),
)


def build_voice_domain_system_instruction(
    *,
    include_diagnosis_examples: bool = False,
) -> str:
    """Static voice + domain block for ``GenerateContentConfig(system_instruction=…)``.

    Per-request strings (layer0_context, creator_format_history) stay in the user
    message so the system slice stays cache-friendly (HI-8 Phase B).
    """
    voice = build_voice_block(
        include_examples=include_diagnosis_examples,
        example_type="diagnosis",
    )
    return f"{voice}\n\n---\n\n{_DOMAIN_KNOWLEDGE}"


# ---------------------------------------------------------------------------
# Diagnosis prompt — Gemini call 2
# ---------------------------------------------------------------------------


def _serialize_diagnosis_inputs(
    analysis: dict[str, Any], metadata: dict[str, Any]
) -> tuple[str, str]:
    serialized_analysis = json.dumps(analysis, ensure_ascii=False, indent=2)
    serialized_metadata = json.dumps(metadata, ensure_ascii=False, indent=2)
    return serialized_analysis, serialized_metadata


_CAROUSEL_SYNTHESIS_FRAMING = """
Đây là carousel (ảnh trượt), KHÔNG PHẢI video.

PHÂN TÍCH 2 TẦNG — theo đúng thứ tự:

**TẦNG 1: PHÂN PHỐI — TẠI SAO ÍT NGƯỜI THẤY (từ metadata)**
Phân tích TRƯỚC KHI nói về nội dung. Carousel có thể đẹp nhưng không ai thấy vì phân phối sai. Kiểm tra:

a) Hashtag: có phải tiếng Việt + cụ thể cho ngách không?
   Hashtag generic tiếng Anh (#trendingtiktok #ootd) = thuật toán không biết đẩy cho ai.
   Carousel chạy tốt dùng hashtag Vietnamese ngách cụ thể.
   Nếu hashtag user quá chung → đây là nguyên nhân chính, nói trước.

b) Caption: có text mô tả nội dung không?
   Caption trống (chỉ hashtag) = thiếu context cho thuật toán.
   Caption tốt = 1-2 câu mô tả + hook + hashtag cuối.

c) Tỷ lệ tương tác vs views:
   Nếu ER cao nhưng views thấp → vấn đề PHÂN PHỐI (ít người thấy, nhưng người thấy thì thích).
   Nói rõ: "Content không dở — reach bị hạn chế."
   Nếu ER thấp VÀ views thấp → vấn đề CẢ HAI.

d) Sound: kiểm tra `metadata.music` (title, artist, is_original):
   - Nếu is_original = true → dùng âm thanh tự tạo. So sánh với niche_norms.pct_original_sound:
     nếu niche dưới 30% dùng âm thanh gốc → đây là lựa chọn khác biệt, đề cập ngắn.
   - Nếu is_original = false → dùng nhạc trending/remix. Tích cực: thuật toán ưu tiên sound trending.
   - Nếu music.title có tên bài cụ thể → đề cập tên sound và ngắn gọn nói nó đang trending hay không.
   - Nếu music là null hoặc thiếu → bỏ qua mục này, KHÔNG đề cập.

**TẦNG 2: NỘI DUNG — LOGIC LƯỚT (từ Gemini phân tích slides)**
Chỉ phân tích sau khi đã nói về tầng phân phối.

Video tự chạy — viewer thụ động. Carousel yêu cầu viewer LƯỚT — mỗi lần lướt là 1 quyết định.
Phân tích theo logic lướt:

a) Slide 1 → dừng lướt:
   Có dừng được feed scroll không? Có chữ/câu hỏi/con số tạo tò mò không?
   Có mặt người không (slides[0].has_face)? So sánh với slide 1 của carousel đang chạy trong ngách.

b) Slide 1→2 → có lý do lướt tiếp không:
   3 loại lý do lướt: tò mò (câu hỏi chưa trả lời), danh sách (còn item chưa xem),
   câu chuyện (chưa biết kết quả). content_arc cho biết arc nào đang được dùng.

c) Momentum giữa các slide:
   visual_consistency — thiếu nhất quán làm mất tin cậy thương hiệu.
   text_density thay đổi đột ngột — slide chữ dày xen kẽ ảnh tạo nhịp tốt.

d) Slide cuối → hành động:
   cta_slide.has_cta — nếu False thì bỏ lỡ cơ hội. Carousel có tỷ lệ lưu cao gấp 2-3x video.

KHÔNG phân tích yếu tố video:
❌ nhịp cắt cảnh / transitions / audio / watch time / face_appears_at theo giây

QUAN TRỌNG:
- Nếu tầng 1 (phân phối) là vấn đề chính → nói rõ: "Sửa hashtag + caption TRƯỚC — content carousel có thể không cần thay đổi nhiều."
- Nếu tầng 2 (nội dung) là vấn đề chính → tầng 1 chỉ mention ngắn.
- Nếu cả hai → nói cả hai, nhưng ưu tiên thứ tự: phân phối trước, nội dung sau.
"""

_CAROUSEL_DIAGNOSIS_FEW_SHOT_V2 = """
=== EXAMPLE: Fashion accessory carousel — distribution problem, strong content ===

INPUT DATA:
{
  "metadata": {
    "author": "@blingblingbienhinh",
    "content_type": "carousel",
    "slide_count": 8,
    "metrics": { "views": 2493, "likes": 64, "comments": 0, "shares": 0, "bookmarks": 0 },
    "engagement_rate": 2.57,
    "description": "#trendingtiktok #OOTD #outfitideas #beachoutfit",
    "hashtags": ["trendingtiktok", "OOTD", "outfitideas", "beachoutfit"]
  },
  "analysis": {
    "hook_analysis": {
      "first_frame_type": "product_only",
      "face_appears_at": null,
      "hook_phrase": "",
      "hook_type": "none",
      "hook_notes": "Slide 1 is a product photo with no text overlay"
    },
    "slides": [
      { "index": 0, "visual_type": "product_photo", "text_on_slide": [], "has_face": false, "has_product": true, "text_density": "none", "note": "Accessory on plain background" },
      { "index": 1, "visual_type": "product_photo", "text_on_slide": [], "has_face": false, "has_product": true, "text_density": "none", "note": "Different angle" },
      { "index": 7, "visual_type": "product_photo", "text_on_slide": [], "has_face": false, "has_product": true, "text_density": "none", "note": "Final slide, no CTA text" }
    ],
    "content_arc": "gallery",
    "visual_consistency": "consistent",
    "estimated_read_time_seconds": 8,
    "cta_slide": { "has_cta": false, "cta_type": "none", "cta_text": "" },
    "transitions_per_second": 0.0
  }
}

CORRECT DIAGNOSIS OUTPUT:
Carousel @blingblingbienhinh — 8 slides, 2.493 views. Tỷ lệ tương tác 2,57% — người nào thấy thì có tương tác. Vấn đề chính không phải content dở mà là ít người được thấy.

**Tại sao ít người thấy carousel này:**
Nguyên nhân rõ nhất: hashtag. Bạn dùng #trendingtiktok #OOTD #outfitideas #beachoutfit — 4 hashtag tiếng Anh cực kỳ chung chung, hàng triệu post dùng mỗi ngày. Thuật toán TikTok không biết nên đẩy carousel này cho ai vì không có tín hiệu ngách cụ thể nào.

Caption cũng trống — chỉ có hashtag, không có dòng mô tả nào. Thuật toán cần text để hiểu nội dung và đẩy đúng người.

So sánh: carousel chạy tốt trong ngách thời trang Việt Nam dùng hashtag Vietnamese cụ thể: #phukienbienhoa #trangsucdep #outfitvietnam #phoidohanngay. Caption kiểu: "Mấy món phụ kiện này mình phối đồ nào cũng hợp luôn á" — vừa tự nhiên vừa cho thuật toán context.

Sửa hashtag + caption TRƯỚC — content carousel có thể không cần thay đổi nhiều.

**Nội dung carousel — phân tích theo logic lướt:**

Slide 1 → dừng lướt: 🔴
Ảnh sản phẩm đẹp nhưng thiếu dòng chữ hook — người xem thấy phụ kiện, không biết có gì đặc biệt, lướt đi. Không có mặt người (has_face = false) để tạo kết nối cảm xúc.
So sánh: carousel thời trang chạy tốt thường mở slide 1 bằng "7 phụ kiện dưới 100K phối đồ nào cũng hợp" — con số + giới hạn giá cho viewer 2 lý do dừng lại.

Slide 1→2 → lý do lướt tiếp: 🔴
content_arc = gallery — không có câu hỏi, không có danh sách, không có câu chuyện. Viewer không biết carousel có bao nhiêu slide hay bao nhiêu item. Thiếu momentum ngay từ đầu.
Chạy vì: carousel cần cho viewer biết "có X thứ để xem" ngay từ slide đầu — tạo kỳ vọng để lướt đến cuối.

Slide cuối → hành động: 🔴
cta_slide.has_cta = false — kết thúc bằng ảnh sản phẩm, không CTA. Viewer đã lướt đến slide 8 — đó là lúc dễ nhất để họ lưu lại. Bỏ lỡ cơ hội này đáng tiếc vì carousel có tỷ lệ lưu cao gấp 2-3x so với video.

**5 hướng content carousel cho ngách thời trang:**

1. **Danh sách có số** — "[Số] phụ kiện dưới [giá] phối đồ nào cũng hợp"
   Logic lướt: con số trên slide 1 tạo kỳ vọng — viewer lướt để xem hết danh sách.
   Slide 1: tiêu đề lớn + ảnh item đẹp nhất. Slide 2-8: mỗi slide = 1 item + giá.
   Slide cuối: "Lưu lại mua dần nha."
   Hashtag gợi ý: #phukien #phukiengiare #phoidohanngay

2. **So sánh A vs B** — "[Phụ kiện A] vs [B] — cái nào hợp hơn?"
   Logic lướt: câu hỏi ở slide 1 tạo tension — viewer lướt để tìm câu trả lời.
   Slide 1: 2 sản phẩm cạnh nhau + câu hỏi. Slide 2-5: so sánh từng tiêu chí. Slide cuối: verdict + "Comment cho mình biết bạn chọn cái nào."

3. **Biến hình phối đồ** — "1 chiếc [phụ kiện] phối 5 kiểu khác nhau"
   Logic lướt: "còn kiểu nào nữa?" — tò mò vì mỗi slide là cách phối mới.
   Slide 1: outfit đẹp nhất. Slide 2-6: mỗi slide = 1 cách phối hoàn toàn khác. Slide cuối: "Follow để xem thêm cách phối mỗi ngày."

4. **Trước / Sau** — "Phối phụ kiện sai vs đúng — khác nhau một trời một vực"
   Logic lướt: slide "sai" tạo tension → viewer lướt để thấy phiên bản "đúng".
   Slide 1: ảnh phối sai. Slide 2: cùng outfit + phụ kiện đúng. Lặp lại 3-4 cặp. Slide cuối: "Lưu lại để nhớ khi đi mua nha."

5. **Câu chuyện mua hàng** — "Mình đặt [sản phẩm] Shopee [giá] — mở ra thấy..."
   Logic lướt: bỏ lửng ở slide 1 → viewer lướt để biết kết quả.
   Slide 1: hook "Mua về mở ra thấy..." + ảnh hộp hàng. Slide 2-4: quá trình dùng. Slide cuối: verdict + "Lưu lại nếu muốn mua."

**Điều duy nhất cần thay đổi cho carousel tiếp:**
Đổi hashtag sang tiếng Việt cụ thể cho ngách (#phukiengiare #phoidohanngay) và thêm 1 dòng caption mô tả. Chỉ riêng việc này đã giúp thuật toán biết đẩy cho ai — đó là sự khác biệt giữa 2.000 views và 20.000+ views cho cùng content.
"""


def build_carousel_diagnosis_prompt(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
    include_directions: bool = False,
    user_message: str = "",
) -> str:
    """Strategist markdown synthesis for **photo carousel** analysis (`analysis.slides`).

    include_directions: when True (or detected from user_message compound keywords),
    appends an instruction asking Gemini for 4-5 carousel content directions.
    user_message: raw user text — checked for compound direction keywords.
    """
    serialized_analysis, serialized_metadata = _serialize_diagnosis_inputs(
        analysis, metadata
    )
    voice = build_voice_block(include_examples=False)
    carousel_context = build_carousel_context()

    # Compound keywords only — single words like "cho tôi" match too broadly
    _direction_keywords = [
        "gợi ý định dạng",
        "gợi ý hướng",
        "ý tưởng content",
        "đề xuất format",
        "gợi ý carousel",
        "gợi ý cho tôi",
        "cho tôi 4",
        "cho tôi 5",
        "cho mình mấy",
        "định dạng nội dung",
        "hướng content",
    ]
    wants_directions = include_directions or any(
        kw in user_message.lower() for kw in _direction_keywords
    )

    directions_instruction = ""
    if wants_directions:
        directions_instruction = """
Sau phần chẩn đoán, thêm phần **"Hướng content carousel cho ngách này"** với 4-5 công thức carousel cụ thể.
Mỗi hướng gồm: tên công thức, LOGIC LƯỚT (giải thích tại sao viewer lướt hết — dùng đúng tên tâm lý: completion bias, information gap, Zeigarnik effect, micro-commitment), hook slide 1, nội dung slide giữa, CTA slide cuối.
Kèm gợi ý hashtag tiếng Việt ngách cụ thể + caption mẫu ≥200 ký tự.
"""

    return f"""{voice}

---

{_DOMAIN_KNOWLEDGE}

{_CAROUSEL_SYNTHESIS_FRAMING}

---
{carousel_context}

---

Viết chẩn đoán như ví dụ **carousel** dưới — cùng thanh giọng với video (thẳng,
creator-native, số liệu diễn giải thành ý nghĩa) nhưng mọi nhận định phải bám `analysis.slides`
(index, visual_type, text_on_slide, has_face, has_product, text_density, word_count, note),
content_arc, visual_consistency, cta_slide, has_numbered_hook, swipe_trigger_type, và caption/metadata.

Nếu metadata nói slide bị cắt, CDN lỗi chỉ số, hoặc tải một phần, hãy phản ánh vào độ tin cậy và câu hỏi.

{_CAROUSEL_DIAGNOSIS_FEW_SHOT_V2}

=== CHẨN ĐOÁN BÀI ĐĂNG NÀY (CAROUSEL ẢNH) ===

INPUT DATA:
{{
  "metadata": {serialized_metadata},
  "analysis": {serialized_analysis}
}}

CẤU TRÚC — theo PHÂN TÍCH 2 TẦNG (phân phối TRƯỚC, nội dung SAU):

**TẦNG 1: TẠI SAO ÍT NGƯỜI THẤY** (2-3 đoạn)
Phân tích hashtag, caption, ER vs views, và sound (từ metadata.music + niche_norms.pct_original_sound nếu có).
Kết luận bằng priority: phân phối hay nội dung là vấn đề chính.

**TẦNG 2: LOGIC LƯỚT** (slide 1 → slide giữa → slide cuối)
Mỗi phần: nhận xét cụ thể từ slides data + emoji [🔴🟡🟢] + "Chạy vì:" hoặc "Gợi ý:".
Trích slides[].index, has_face, text_density, text_on_slide, word_count, has_numbered_hook, swipe_trigger_type, cta_slide.has_cta khi hữu ích.
Giải thích bằng tên tâm lý lướt (completion bias, information gap, Zeigarnik effect, goal gradient, micro-commitment) — không phải thuật ngữ kỹ thuật chung chung.
QUAN TRỌNG — text trên slide: NẾU slides[].text_on_slide có nội dung (list không rỗng), PHẢI trích dẫn text đó khi phân tích slide đó. KHÔNG được nói "slide không có chữ" khi text_on_slide có dữ liệu.
KHÔNG đề cập: transitions/s, face_appears_at tính bằng giây, audio, watch time.

**MỘT ĐIỀU DUY NHẤT** cần thay đổi cho carousel tiếp (câu kết luận).
{directions_instruction}

QUY TẮC CỨNG:
- Viết như người, không như hệ thống
- Không dùng: "analysis indicates", "signals suggest", "it is recommended"
- Không né tránh nhận định chính
- Không dựng bảng tóm tắt hay dump field/value
- Tất cả nội dung phải bằng tiếng Việt.

Viết chẩn đoán ngay. Không lời dẫn hay kết chữ ký.
"""


def build_carousel_diagnosis_prompt_v2(
    carousel_format: str,
    niche_name: str,
    corpus_size: int,
    niche_meta: dict[str, Any],
    reference_carousels: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    wants_directions: bool = False,
    corpus_citation: str = "",
    persona_block: str = "",
) -> str:
    """V2 carousel diagnosis prompt — 2-layer narrative, corpus-aware.

    Mirrors build_diagnosis_synthesis_prompt_v2() for video but uses:
    - CAROUSEL_NARRATIVE_OUTPUT_STRUCTURE (2-layer: distribution + swipe logic)
    - carousel-specific FORMAT_ANALYSIS_WEIGHTS
    - carousel_knowledge.build_carousel_context() for swipe psychology
    - reference_carousels instead of reference_videos

    Static voice + domain ship in ``system_instruction`` (gemini.py). Optional
    ``layer0_context`` / ``creator_format_history_block`` are prefixed to the
    user message by the caller.

    Called by gemini.py:synthesize_diagnosis_carousel_v2().

    Args:
        carousel_format:    One of: carousel, carousel_product_roundup,
                            carousel_tutorial, carousel_story.
        niche_name:         Human-readable niche name.
        corpus_size:        Carousel count in corpus for this niche (last 30 days).
        niche_meta:        Dict from niche_intelligence (carousel-filtered).
        reference_carousels: List of 3 top-performing carousel dicts with analysis + metadata.
        user_analysis:      Gemini carousel extraction result.
        user_stats:         User carousel stats (views, breakout_multiplier, etc.).
        wants_directions:   If True, appends 4-5 content direction suggestions.
    """
    carousel_context = build_carousel_context()

    return build_carousel_diagnosis_narrative_prompt(
        voice_block="",
        carousel_knowledge_block=carousel_context,
        carousel_synthesis_framing=_CAROUSEL_SYNTHESIS_FRAMING,
        carousel_format=carousel_format,
        niche_name=niche_name,
        corpus_size=corpus_size,
        niche_meta=niche_meta,
        reference_carousels=reference_carousels,
        user_analysis=user_analysis,
        user_stats=user_stats,
        wants_directions=wants_directions,
        corpus_citation=corpus_citation,
        persona_block=persona_block,
    )


def build_diagnosis_prompt(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
    content_type: ContentType = "video",
    include_carousel_directions: bool = False,
    user_message: str = "",
) -> str:
    """Route to the carousel strategist prompt (v1 — legacy).

    Video path uses build_diagnosis_synthesis_prompt_v2() via synthesize_diagnosis_v2().
    Carousel path uses build_carousel_diagnosis_prompt_v2() via synthesize_diagnosis_carousel_v2().
    This function is kept for analysis_core.py callers that pass raw analysis/metadata
    dicts without corpus context. New carousel calls should use the v2 path via pipelines.py.
    """
    if content_type == "carousel":
        return build_carousel_diagnosis_prompt(
            analysis,
            metadata,
            include_directions=include_carousel_directions,
            user_message=user_message,
        )
    # Video: v2 prompt (build_diagnosis_synthesis_prompt_v2) is the active path.
    # This branch is a safety fallback for legacy callers — returns empty string
    # so callers that check for a non-empty string will fall through gracefully.
    return ""


# ---------------------------------------------------------------------------
# Batch summary — Gemini call 3 (JSON only)
# ---------------------------------------------------------------------------


def _focus_instructions(focus: str) -> str:
    f = focus.lower().strip()
    if f == "hooks":
        return (
            "Nhấn mạnh pattern thời điểm hook: trung bình face_appears_at và first_speech_at, "
            "và các giá trị first_frame_type phổ biến xuyên video."
        )
    if f == "format":
        return (
            "Nhấn mạnh cấu trúc và nhịp: video `scenes` so với carousel `slides`, "
            "transitions_per_second, và xu hướng energy_level."
        )
    if f == "competitor":
        return (
            "Nhấn mạnh pattern cấu trúc và khoảng trống nội dung trên các video kiểu đối thủ."
        )
    return "Tổng quan cân bằng về hook, format, nhịp và messaging."


def build_summary_prompt(
    analyses: list[dict[str, Any]],
    focus: str,
    computed_stats: dict[str, Any],
) -> str:
    """Build a text-only prompt for qualitative cross-video summary JSON."""
    raw = focus.lower().strip()
    valid_focus = raw if raw in ("general", "hooks", "format", "competitor") else "general"

    serialized = json.dumps(analyses, ensure_ascii=False, indent=2)
    stats = json.dumps(computed_stats, ensure_ascii=False, indent=2)
    fi = _focus_instructions(valid_focus)

    return f"""Bạn được cung cấp các phân tích có cấu trúc của nhiều bài đăng TikTok (mảng JSON bên dưới).
Mỗi mục là phân tích video (có `scenes`) hoặc phân tích carousel (có `slides`).

Trọng tâm tóm tắt: {valid_focus}
Hướng dẫn: {fi}

Các thống kê số bên dưới đã được tính bằng Python. Xem chúng là sự thật.

Chỉ trả về JSON hợp lệ — không markdown, không lời dẫn — với cấu trúc chính xác này:
{{
  "top_patterns": ["<structural patterns across successful analyses>"],
  "content_gaps": ["<angles or formats not covered>"],
  "recommendations": ["<actionable next steps>"],
  "winning_formula": "<1-2 sentence synthesis of shared structural elements>"
}}

Thống kê đã tính (JSON):
{stats}

Phân tích video (JSON):
{serialized}
"""


def build_knowledge_system_instruction(message: str) -> str:
    """Voice + optional domain block for knowledge Q&A (``system_instruction``)."""
    voice = build_voice_block(include_examples=False)

    _domain_kws = (
        "thuật toán",
        "algorithm",
        "fyp",
        "reach",
        "viral",
        "trending",
        "flop",
        "chạy",
        "bóp",
        "shadowban",
        "lên xu hướng",
        "views",
        "lượt xem",
        "watch time",
        "completion",
        "tương tác",
        "save",
        "share",
        "comment",
        "hook",
        "đăng",
        "posting",
        "thời gian",
        "sound",
        "shopee",
        "affiliate",
        "kiếm tiền",
        "commission",
    )
    msg_lower = message.lower()
    domain_block = f"\n{_DOMAIN_KNOWLEDGE}\n" if any(kw in msg_lower for kw in _domain_kws) else ""
    return (f"{voice}\n\n---\n\n{domain_block}").rstrip() + "\n"


def build_knowledge_user_prompt(message: str, session_context: dict[str, Any]) -> str:
    """Session + question + reply rules (user turn)."""
    prior_context_block = ""
    completed = session_context.get("completed_intents", [])
    if completed:
        summary = session_context.get("analyses_summary", {})
        prior_context_block = f"""
Ngữ cảnh phiên trước — tham chiếu nếu liên quan đến câu hỏi:
{json.dumps(summary, indent=2, ensure_ascii=False)}
"""

    return f"""{prior_context_block}
Câu hỏi người dùng: {message}

Trả lời thẳng thắn và cụ thể — không né tránh câu trả lời.
Tham chiếu ngữ cảnh phiên trên nếu liên quan.
Không dùng bảng field/value. Không dùng bullet point trừ khi câu hỏi bản chất là danh sách.
"""


def build_knowledge_prompt(message: str, session_context: dict[str, Any]) -> str:
    """§3a Rule A — full prompt string (legacy compose).

    Prefer ``build_knowledge_system_instruction`` +
    ``build_knowledge_user_prompt`` with ``system_instruction`` on the API call.
    """
    return f"{build_knowledge_system_instruction(message)}\n{build_knowledge_user_prompt(message, session_context)}"


# ---------------------------------------------------------------------------
# Synthesis few-shot examples — voice / structure anchor for build_synthesis_prompt
# ---------------------------------------------------------------------------

_SYNTHESIS_FEW_SHOTS: dict[str, str] = {
    # video_diagnosis: examples are now injected by voice_guide.build_voice_block()
    # — no entry here to avoid duplication. build_synthesis_prompt skips this key.
    "content_directions": """
=== EXAMPLE: content_directions — niche sneaker, 3 reference videos ===

INPUT PAYLOAD (excerpt):
{
  "niche": "sneaker",
  "reference_count": 3,
  "analyzed_videos": [
    {"metadata": {"author": "@cucusneaker", "views": 1623886, "engagement_rate": 3.81}, "analysis": {"hook_analysis": {"hook_type": "bold_claim", "first_frame_type": "product"}, "scenes": [{"type": "action"}, {"type": "product_shot"}], "energy_level": "medium"}},
    {"metadata": {"author": "@sneakerhead.vn", "views": 420300, "engagement_rate": 5.2}, "analysis": {"hook_analysis": {"hook_type": "curiosity_gap", "first_frame_type": "face_with_text"}, "scenes": [{"type": "face_to_camera"}, {"type": "product_shot"}], "energy_level": "high"}},
    {"metadata": {"author": "@giayxin_daily", "views": 89000, "engagement_rate": 7.1}, "analysis": {"hook_analysis": {"hook_type": "how_to", "first_frame_type": "face"}, "scenes": [{"type": "face_to_camera"}, {"type": "demo"}], "energy_level": "medium"}}
  ]
}

CORRECT SYNTHESIS OUTPUT:
Ba video tham chiếu có lượt xem từ 89k đến 1,6 triệu nhưng chia sẻ một pattern cấu trúc: sản phẩm phải lên hình trong 2 giây đầu. Video nào trì hoãn product shot quá 3 giây đều có ER thấp hơn nhóm.

**Hướng 1: Unboxing bold claim — "Let me show you why…"**
- @cucusneaker chứng minh không cần mặt nếu hành động unboxing đủ mạnh. Bold claim + mystery packaging = open loop kép. Format này phù hợp nếu sản phẩm có visual distinctive (hộp lạ, texture đặc biệt, colorway giới hạn)
- Rủi ro: không mặt = không trust signal. Chỉ chạy khi sản phẩm tự gánh được attention

**Hướng 2: Face-to-camera + review nhanh**
- @sneakerhead.vn và @giayxin_daily đều mở bằng mặt. ER cao hơn (5.2% và 7.1%) dù view thấp hơn — face tạo connection mà product-only không có
- Format phù hợp nhất cho review chân thật, so sánh real vs fake, "mang thử 1 tuần"

**Hướng 3: How-to/demo styling**
- @giayxin_daily 89k view nhưng ER 7.1% — cao nhất nhóm. Hook "how to" + demo scene = audience ở lại để học
- Dạng "3 cách phối giày này" hoặc "outfit check" — utility content giữ save cao

**Khoảng trống chưa khai thác**
- Không video nào dùng so sánh trực tiếp (A vs B side-by-side). Format này thường viral trong sneaker quốc tế
- Chưa thấy carousel review — format ảnh có thể capture save tốt hơn video ngắn cho audience bookmark-to-buy
""",
    "trend_spike": """
=== EXAMPLE: trend_spike — niche skincare, 7-day window ===

INPUT PAYLOAD (excerpt):
{
  "niche": "skincare",
  "window_days": 7,
  "analyzed_videos": [
    {"metadata": {"video_id": "7381234567890", "author": "@drskn.vn", "views": 2100000, "engagement_rate": 4.8, "create_time": 1712500000}, "analysis": {"hook_analysis": {"hook_type": "shock_stat"}, "tone": "educational", "topics": ["retinol", "da nhạy cảm"]}},
    {"metadata": {"video_id": "7381234567891", "author": "@beautyclassic", "views": 680000, "engagement_rate": 6.1, "create_time": 1712600000}, "analysis": {"hook_analysis": {"hook_type": "controversy"}, "tone": "entertaining", "topics": ["skincare routine", "sai lầm"]}}
  ]
}

CORRECT SYNTHESIS OUTPUT:
Tuần qua skincare TikTok VN có hai trend đang tăng tốc cùng lúc — và chúng mâu thuẫn nhau, tạo cơ hội.

**Trend 1: Retinol cho da nhạy cảm — educational shock**
{"type":"trend_card","title":"Retinol cho da nhạy cảm","recency":"Mới 4 ngày","signal":"rising","breakout":"3,1x","videos":["7381234567890"],"hook_formula":"SỰ THẬT về [thành phần] mà bác sĩ da liễu không nói","mechanism":"Authority claim ngược mainstream giữ người xem đến hết để kiểm chứng — comment tranh luận đẩy reach","corpus_cite":"89 video skincare · tuần này"}
Bác sĩ da liễu + claim ngược mainstream ("retinol không nguy hiểm như bạn nghĩ") = authority + controversy nhẹ. Tone educational thắng ở velocity cao nhất tuần — audience đang tìm thông tin đáng tin. Cửa sổ: 5-7 ngày trước khi format bị copy.

**Trend 2: Sai lầm skincare — controversy giải trí**
{"type":"trend_card","title":"Sai lầm skincare","recency":"Mới 3 ngày","signal":"rising","breakout":"2,4x","videos":["7381234567891"],"hook_formula":"ĐỪNG làm [hành động] nếu bạn đang dùng [sản phẩm]","mechanism":"Format warning kích hoạt sợ bỏ lỡ — viewer ở lại xem mình có mắc lỗi không, comment tự check","corpus_cite":"89 video skincare · tuần này"}
ER 6.1% cao hơn video 2 triệu view. Format "đừng làm điều này" outperform "hãy làm điều này" trong tuần qua — social proof ngược mạnh hơn lời khuyên tích cực.

**Cơ hội giao nhau**
- Chưa ai kết hợp cả hai: "3 sai lầm retinol mà cả bác sĩ cũng mắc" — authority + controversy + list format
- Timing: cả hai trend đang tăng, chưa saturation. Cửa sổ khoảng 5-7 ngày trước khi format bị copy rộng
""",
}


# ---------------------------------------------------------------------------
# Intent synthesis framing — goal line injected per intent
# ---------------------------------------------------------------------------

INTENT_SYNTHESIS_FRAMING: dict[str, str] = {
    "content_directions": (
        "MỤC TIÊU: Xu hướng nội dung nổi bật trong niche. Xác định những gì các video tham chiếu thực hiện về mặt cấu trúc (hook, nhịp độ, format). Nêu 2–3 hướng nội dung kèm bằng chứng từ JSON.\n\n"
        "NẾU reference videos có metadata.pattern_display_name: gom 2-3 video cùng pattern thành một hướng (VD: 'Hướng 1: Pattern Câu hỏi + trước/sau — đã thấy trong 3 video tham chiếu'). Đặt tên pattern làm tiêu đề hướng để người đọc nhận ra sự lặp lại.\n"
        "NẾU không có pattern_display_name: giữ cấu trúc 3 hướng dựa trên cấu trúc cá nhân của từng video — đừng ép pattern khi không có dữ liệu.\n\n"
        "TIẾT CHẾ: KHÔNG elaborate những mục dưới đây — mỗi cái có nút follow-up riêng:\n"
        "  - Ưu tiên hướng nào trước (có nút 'Hướng nào nên thử trước?').\n"
        "  - Kế hoạch 30 ngày trộn 3 hướng (cadence / tần suất đăng từng hướng).\n"
        "  - Metric target tuần đầu cho mỗi hướng (% ER, views kỳ vọng).\n"
        "Chỉ đưa 1 câu gợi ý cho mỗi hướng về '3 lần thử đầu nên làm gì' — không cần full kế hoạch."
    ),
    "trend_spike": (
        "MỤC TIÊU: Trend đang tăng tốc — nhấn mạnh những gì đang bứt phá gần đây so với các format đã ổn định.\n\n"
        "MỞ ĐẦU — Nếu payload có trường `patterns` với ≥1 phần tử:\n"
        "  Mở bằng 1-2 câu ĐẦU TIÊN đề cập pattern có weekly_delta cao nhất, VD:\n"
        "  \"Tuần này pattern **{display_name}** bứt phá — {instance_count_week} video, tăng +{weekly_delta} so với tuần trước, đã lan sang {niche_spread_count} ngách.\"\n"
        "  Sau đó mới vào các trend_card riêng lẻ. Nếu `patterns` rỗng, bỏ qua — mở bằng trend_card luôn.\n\n"
        "ĐỊNH DẠNG BẮT BUỘC — mỗi trend PHẢI là một JSON block trên một dòng riêng, ngay sau câu giới thiệu trend:\n"
        '{"type":"trend_card","title":"<tên trend>","recency":"<vd: Mới 3 ngày>","signal":"<rising|early|stable|declining>",'
        '"breakout":"<vd: 4,2x hoặc bỏ trống nếu không rõ>","videos":["<video_id1>","<video_id2>","<video_id3>"],'
        '"hook_formula":"<template điền vào: ĐỪNG [hành động] nếu...>","mechanism":"<lý do chạy vì: 1 câu>","corpus_cite":"<vd: 412 video · tuần này>"}\n\n'
        "- Chỉ dùng video_id từ JSON bên dưới — KHÔNG tự tạo ID\n"
        '- signal: "rising" = đang tăng nhanh, "early" = mới xuất hiện, "stable" = ổn định, "declining" = đang giảm\n'
        "- breakout: tỷ lệ views/trung bình niche — dùng dấu phẩy Việt Nam: 3,2x không 3.2x\n"
        "- Sau JSON block, thêm 1-2 dòng về cơ chế — KHÔNG giải thích dài về timing / rủi ro / saturation (dành cho follow-up)\n"
        "- Kết thúc bằng mục **Cơ hội giao nhau** nếu có pattern xuyên trend"
        "\n\nÂM THANH XU HƯỚNG (từ khóa trending_sounds trong JSON):\n"
        "- Nếu JSON chứa trending_sounds với usage_count >= 3, xuất mỗi âm thanh là một JSON block:\n"
        '{"type":"sound_card","sound_name":"<tên>","usage_count":<số>,"total_views":<tổng views>,"commerce_signal":<true|false>}\n'
        "- Đặt sound_card block ngay sau trend_card block liên quan nhất (cùng niche/format)\n"
        "- commerce_signal: true nếu âm thanh được dùng nhiều trong video TikTok Shop / review sản phẩm\n"
        "- Bỏ qua nếu danh sách trending_sounds rỗng hoặc tất cả usage_count < 3\n"
        "- Không thêm prose giải thích quanh sound_card block — tự nó là đủ\n\n"
        "TIẾT CHẾ: KHÔNG elaborate những mục dưới đây — mỗi cái có nút follow-up riêng:\n"
        "  - Mức độ cạnh tranh / bão hoà của từng trend (saturation score).\n"
        "  - Dự báo dải uplift (VD: 'early adopters +5-10x baseline').\n"
        "  - Chi phí sản xuất / độ khó entry (easy/medium/hard).\n"
        "  - Adaptation cụ thể cho ngách khác ngoài trend gốc.\n"
        "  - Hashtag + sound bundle dạng copy-paste đầy đủ (dùng sound_card JSON đã đủ cho core response)."
    ),
    "competitor_profile": (
        "MỤC TIÊU: Phân tích tài khoản đối thủ — tóm tắt công thức nội dung lặp lại của họ từ các bài đăng.\n"
        "CẤU TRÚC (GIỮ NGẮN — cốt lõi + dưới 250 từ):\n"
        "- Nhận định chính (1-2 câu): vì sao họ đang chạy tốt.\n"
        "- **Content mix** 1 dòng: tỉ lệ xấp xỉ các loại content (VD: 70% review · 20% GRWM · 10% trend).\n"
        "- **Công thức copy được** — chỉ 1 hook pattern duy nhất (không liệt kê 3), kèm ví dụ cụ thể từ data.\n"
        "- **Khoảng trống** — 1 câu về chủ đề/format họ CHƯA đụng mà user có thể chiếm.\n\n"
        "TIẾT CHẾ: KHÔNG elaborate những mục dưới đây (có nút follow-up riêng, user sẽ hỏi khi cần):\n"
        "  - Top 3 hook formula chi tiết kèm template (có nút 'công thức hook hay nhất của họ').\n"
        "  - Posting pattern / khung giờ tối ưu.\n"
        "  - Tín hiệu monetization (TikTok Shop, sponsored posts).\n"
        "  - Brief nhái phong cách của họ."
    ),
    # ``series_audit`` dropped 2026-04-22 — no template, no classifier
    # label. If a legacy session still has this intent, it falls through
    # to the framing default in build_synthesis_prompt.
    "brief_generation": (
        "MỤC TIÊU: Brief sản xuất — xuất brief quay phim ngắn gọn, seller/agency có thể gửi thẳng Zalo cho KOL.\n"
        "CẤU TRÚC (core — seller đọc trong 30 giây):\n"
        "- **Hook** (câu mở + hành động khung đầu, 1 dòng).\n"
        "- **Beat sheet** (3-5 beat, mỗi beat 1 dòng: thời lượng + hành động + chữ trên màn hình).\n"
        "- **CTA** (câu kết + overlay).\n"
        "- **Ghi chú sản xuất** (1-2 dòng: setup, prop, tone).\n\n"
        "TIẾT CHẾ: KHÔNG thêm vào response này — mỗi mục có nút follow-up riêng:\n"
        "  - Budget / giá ước / KPI commitment (mức views / ER target, điều kiện reshoot).\n"
        "  - Deliverables checklist chi tiết (video chính + Story + Caption + Usage rights clause).\n"
        "  - Template disclosure / nhãn #hợp tác / #ad theo luật VN.\n"
        "  - Thời hạn, timeline sản xuất + posting window.\n"
        "  - Usage rights (brand repost thời gian bao lâu, kênh nào).\n"
        "Brief core phải là phần CREATIVE — phần hợp đồng/thương mại để seller mở chip khi cần."
    ),
    "shot_list": (
        "MỤC TIÊU: Danh sách cảnh quay chi tiết — xuất shot list dạng có cấu trúc, mỗi beat là một JSON block.\n\n"
        "ĐỊNH DẠNG BẮT BUỘC — mỗi beat PHẢI là một JSON block trên một dòng riêng:\n"
        '{"type":"shot_item","beat":1,"duration":"0:00–0:03","action":"Cầm sản phẩm, nhìn thẳng camera","overlay":"ĐỪNG mua [sản phẩm] khi chưa xem video này","note":""}\n'
        '{"type":"shot_item","beat":2,"duration":"0:03–0:08","action":"Zoom vào chi tiết đặc biệt của sản phẩm","overlay":"","note":"B-roll cận cảnh"}\n\n'
        "QUYẾT ĐỊNH FORMAT:\n"
        "- Review/unboxing: 5–7 beat, bắt đầu bằng hook reveal\n"
        "- Tutorial/how-to: 4–6 beat, step-by-step logic\n"
        "- Reaction/comparison: 3–5 beat, build-up tension\n"
        "- GRWM/vlog: 4–5 beat, lifestyle flow\n\n"
        "QUY TẮC:\n"
        "- Tổng thời lượng 15–60 giây — ghi rõ duration từng beat\n"
        "- action: hành động camera/diễn viên, ngắn gọn, tiếng Việt\n"
        "- overlay: chữ trên màn hình — LUÔN dùng tiếng Việt, dùng [ngoặc] cho phần thay thế\n"
        "- note: ghi chú sản xuất (setup, prop, ánh sáng) — để trống nếu không cần\n"
        "- Sau tất cả JSON beats, chỉ thêm 1 dòng tổng runtime + tone (VD: 'Tổng ~45s · Tone: tự nhiên, reaction mạnh').\n"
        "- Kết thúc bằng **CTA beat**: câu kết + overlay kêu gọi hành động\n\n"
        "TIẾT CHẾ: KHÔNG viết trong response này (có nút follow-up riêng):\n"
        "  - Caption draft + 5 hashtag bundle.\n"
        "  - Đề xuất cover/thumbnail chi tiết.\n"
        "  - Checklist chuẩn bị quay (dụng cụ, ánh sáng, prop — chỉ ghi qua trong 'note').\n"
        "  - Bản variant 15s / 30s / 60s.\n"
        "Lý do: mỗi mục trên đều là 1 câu chat follow-up riêng — người dùng sẽ nhấn khi cần."
    ),
    "creator_search": (
        "MỤC TIÊU: Tìm KOC/creator phù hợp để quay UGC — từ các bài đăng tham chiếu trong JSON, gợi ý tài khoản và lý do phù hợp với sản phẩm/thương hiệu của người dùng.\n"
        "QUAN TRỌNG: Niche trong payload là niche đã được suy ra từ câu hỏi của người dùng — dùng niche đó để đánh giá mức độ phù hợp của từng KOC với sản phẩm.\n"
        "CẤU TRÚC: Liệt kê 3-5 tài khoản, mỗi tài khoản: **@handle** — followers ước tính, ER, hook style, và đánh giá fit với sản phẩm trong niche (1-2 câu). "
        "Kết thúc bằng **Gợi ý tiếp cận** (1-2 câu — cách liên hệ hoặc brief KOC phù hợp với loại sản phẩm này)."
    ),
    "own_channel": (
        "MỤC TIÊU: Soi kênh của người dùng — đối chiếu với benchmark niche từ video tham chiếu; chỉ ra điểm khớp/lệch và hành động.\n"
        "CẤU TRÚC (core — ngắn, hành động được):\n"
        "- Nhận định chính (1-2 câu): momentum + điểm cần sửa lớn nhất.\n"
        "- **Đang làm đúng** (2 gạch — không 3).\n"
        "- **Đang lệch** (2 gạch — so sánh cụ thể với reference).\n"
        "- **Hành động ưu tiên** (1 gạch duy nhất — việc user làm tuần này).\n\n"
        "TIẾT CHẾ: KHÔNG elaborate những mục dưới đây — mỗi cái có nút follow-up riêng:\n"
        "  - Phân tích content mix (% review / GRWM / trend) của user.\n"
        "  - Niche drift check (5 video gần nhất có còn đúng ngách không).\n"
        "  - 3 hook thí nghiệm cụ thể cho tuần sau.\n"
        "  - Metric target 4 tuần tới (views / ER tăng bao nhiêu)."
    ),
}


def build_synthesis_prompt(
    intent_key: str,
    payload: dict[str, Any],
    *,
    collapsed_questions: list[str] | None = None,
    niche_key: str | None = None,
    corpus_citation: str = "",
    persona_block: str = "",
) -> str:
    """§18 item 17 — intent-specific framing + optional collapsed questions.

    Args:
        intent_key:           Routing key from INTENT_SYNTHESIS_FRAMING.
        payload:              Dynamic corpus data from video_corpus / niche_intelligence.
        collapsed_questions:  Optional multi-question list from the user.
        niche_key:            Optional niche identifier (e.g. "skincare") — when provided,
                              injects niche-specific hook guidance from knowledge_base.py.
                              Particularly useful for brief_generation and content_directions.
        corpus_citation:      Optional pre-built citation block from corpus_context.py
                              (build_corpus_citation_block). Injected above the framing
                              so Gemini grounds every claim in real corpus size + timeframe.
    """
    data_json = json.dumps(payload, ensure_ascii=False, indent=2)
    framing = INTENT_SYNTHESIS_FRAMING.get(
        intent_key,
        "MỤC TIÊU: Tổng hợp chiến lược TikTok — mọi nhận định phải bám bằng chứng trong JSON.",
    )
    qblock = ""
    if collapsed_questions:
        qblock = (
            "\n\nNgười dùng hỏi nhiều câu; thêm mục có tiêu đề rõ cho từng câu:\n"
        )
        qblock += "\n".join(f"- {q}" for q in collapsed_questions)

    # P0-1: corpus citation block — grounds all claims in real data size + timeframe
    citation_block = f"\n{corpus_citation}" if corpus_citation else ""
    # P2-1: persona block — keeps audience_age / pain_points / geography in output
    persona_context = f"\n{persona_block}" if persona_block else ""

    # Static knowledge blocks — injected per intent to keep token count lean.
    # Note: video_diagnosis routes to build_diagnosis_synthesis_prompt_v2(), not here.
    knowledge_block = ""
    if intent_key == "brief_generation":
        knowledge_block = "\n" + build_commerce_structure_block()
        if niche_key:
            knowledge_block += "\n\n" + build_niche_hook_block(niche_key)
    elif intent_key in ("content_directions", "trend_spike", "shot_list"):
        if niche_key:
            knowledge_block = "\n" + build_niche_hook_block(niche_key)

    few_shot = _SYNTHESIS_FEW_SHOTS.get(intent_key, "")
    few_shot_block = ""
    if few_shot:
        few_shot_block = f"""
Viết phân tích giống ví dụ dưới — học giọng, cấu trúc, độ sâu:

{few_shot}

=== PHÂN TÍCH DỮ LIỆU MỚI ===
"""

    return f"""{knowledge_block}
{citation_block}
{persona_context}
{framing}
{qblock}
{few_shot_block}
Bằng chứng (JSON):
{data_json}

Viết markdown phân tích chiến lược. Không lặp lại JSON thô. Không dùng bảng field-value."""


# ---------------------------------------------------------------------------
# V2 diagnosis synthesis — narrative structure, format-aware
# ---------------------------------------------------------------------------

def build_diagnosis_synthesis_prompt_v2(
    content_format: str,
    niche_name: str,
    corpus_size: int,
    niche_meta: dict[str, Any],
    reference_videos: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    wants_directions: bool = False,
    corpus_citation: str = "",
    persona_block: str = "",
    *,
    performance_tier: str = "unknown",
    channel_context: dict[str, Any] | None = None,
    errors: list[dict[str, Any]] | None = None,
    reference_evidence_block: str = "",
) -> str:
    """V2 diagnosis synthesis prompt — narrative structure, format-aware.

    Replaces checklist-style output for Intent ① (video_diagnosis).
    Called by gemini.py:synthesize_diagnosis_v2().

    Static voice + domain ship in ``system_instruction`` (gemini.py).
    Optional ``layer0_context`` is prefixed to the user message by the caller.

    Args:
        content_format:   Detected format string (e.g. "tutorial", "mukbang").
        niche_name:       Human-readable niche name (e.g. "skincare").
        corpus_size:      Number of videos in corpus for this niche (last 30 days).
        niche_meta:      Dict from niche_intelligence materialized view.
        reference_videos: List of reference video dicts with analysis + metadata.
        user_analysis:    Gemini extraction result for the user's video.
        user_stats:       User video stats dict (views, breakout_multiplier, etc.).
        wants_directions: If True, appends 4-5 content direction suggestions after diagnosis.
    """
    return build_diagnosis_narrative_prompt(
        voice_block="",
        examples_block="",
        anti_patterns=ANTI_PATTERNS,
        content_format=content_format,
        niche_name=niche_name,
        corpus_size=corpus_size,
        niche_meta=niche_meta,
        reference_videos=reference_videos,
        user_analysis=user_analysis,
        user_stats=user_stats,
        wants_directions=wants_directions,
        corpus_citation=corpus_citation,
        persona_block=persona_block,
        performance_tier=performance_tier,
        channel_context=channel_context,
        errors=errors,
        reference_evidence_block=reference_evidence_block,
    )


_CAPTION_PREFIX_MAX_CHARS = 2000


def build_tiktok_caption_extraction_prefix(
    description: str | None,
    hashtags: list[str] | None,
) -> str | None:
    """Prepended to Gemini extraction user turn (live + batch, TD-7 parity)."""
    desc = (description or "").strip()
    tag_parts = [
        f"#{str(h).lstrip('#')}"
        for h in (hashtags or [])
        if str(h).strip()
    ]
    if not desc and not tag_parts:
        return None
    lines = [
        "CAPTION_TIKTOK (nguồn đăng bài, không phải overlay trong clip):",
        desc[:_CAPTION_PREFIX_MAX_CHARS] if desc else "",
    ]
    body = "\n".join(line for line in lines if line)
    if tag_parts:
        body = f"{body}\n\nHASHTAGS: {' '.join(tag_parts[:40])}"
    return body.strip() or None


def merge_extraction_supplemental_prefixes(*parts: str | None) -> str | None:
    """Join ASR + caption blocks for ``analyze_video`` / batch JSONL."""
    merged = "\n\n".join(p.strip() for p in parts if p and str(p).strip())
    return merged or None
