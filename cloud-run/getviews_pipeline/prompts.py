"""Gemini prompts for video analysis, batch summary, and strategist diagnosis."""

from __future__ import annotations

import json
from typing import Any

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
from getviews_pipeline.carousel_knowledge import build_carousel_context
from getviews_pipeline.voice_guide import ANTI_PATTERNS, build_voice_block

# ---------------------------------------------------------------------------
# Video analysis prompt — Gemini call 1
# ---------------------------------------------------------------------------

# §14 — extraction prompt (full schema enforced via response_json_schema).
# Keep instructions field-specific — generic "be precise" is ignored by Gemini.
VIDEO_EXTRACTION_PROMPT = """Analyze this TikTok video. Return ONLY JSON matching the schema — no markdown.

CRITICAL RULES:
- audio_transcript: Transcribe EXACTLY in the original language (mostly Vietnamese). Do NOT translate to English. Preserve Vietnamese diacritics (ă, â, đ, ê, ô, ơ, ư, etc.). If words are unclear, write "[không rõ]".
- hook_phrase: The EXACT opening spoken words in Vietnamese — verbatim, not paraphrased, not translated. If no speech in the first 3s, use the first visible text overlay instead.
- scenes: Mark a new scene at EVERY visual cut, camera angle change, or significant subject change. Err toward more scenes rather than fewer. A 15s video typically has 3–8 scenes; a 30s video has 5–15.
- transitions_per_second: Count total scene boundaries ÷ video duration in seconds.
- face_appears_at: The FIRST timestamp (in seconds) where a human face is prominently visible. Set to null if no face appears in the entire video.
- content_direction.what_works: Name the specific STRUCTURAL element making this video effective — e.g. "face in first frame + question hook + 3s scene cuts". NOT generic praise like "good visuals" or "engaging content"."""

CAROUSEL_EXTRACTION_PROMPT = """Analyze this TikTok photo carousel (image parts before this text). Return ONLY JSON matching the schema — no markdown.

CRITICAL RULES:
- hook_analysis.hook_phrase: The EXACT text visible on slide 1 (first image) — verbatim, not paraphrased. If no text on slide 1, describe the dominant visual element in Vietnamese.
- slides[].text_on_slide: List ALL readable text strings visible on this slide — titles, captions, labels, prices, watermarks, hashtags burned into the image. Even 1-2 words count. Use an empty list [] ONLY if the slide has absolutely zero text of any kind.
- slides[].text_density: Classify text amount per slide as exactly one of: 'none' (no text — text_on_slide must also be []), 'low' (1-2 short words/phrases), 'medium' (3-5 lines), 'high' (6+ lines or dense text block). MUST be consistent with text_on_slide: if text_on_slide is non-empty, text_density CANNOT be 'none'.
- slides[].has_face: true if a human face is PROMINENTLY visible (not just background), false otherwise.
- slides[].has_product: true if a physical product (clothing, food, cosmetic, electronics, etc.) is the main subject, false otherwise.
- slides[].word_count: Count the total number of words of visible text on this slide. 0 if no text.
- content_arc: How content flows across ALL slides — exactly one of: 'list' (numbered items), 'story' (narrative progression), 'before_after' (contrast pair), 'comparison' (side-by-side options), 'tutorial_steps' (how-to sequence), 'gallery' (independent items with no arc).
- visual_consistency: Design coherence across slides — 'consistent' (same palette/font/style), 'mixed' (mostly consistent with 1-2 outliers), 'inconsistent' (different styles per slide).
- estimated_read_time_seconds: Realistic total time to read/swipe the full carousel. Base: 2s per text-heavy slide, 1s per image/product slide.
- cta_slide: Analyze the LAST slide only. Set has_cta=true if it contains a call-to-action (follow, save, comment, link, buy). Set cta_type to one of: 'save', 'follow', 'comment', 'link_bio', 'shop_cart', or null. Set cta_text to the exact CTA text or null.
- has_numbered_hook: true if slide 1 visibly shows a number (e.g. "7 cách…", "3 lỗi…", "5 outfit…") that creates completion bias, false otherwise.
- swipe_trigger_type: The dominant psychological mechanism driving swipes — exactly one of: 'list_momentum' (numbered list, people swipe to complete the count), 'curiosity_chain' (each slide withholds something, creating information gap), 'narrative_tension' (story arc with unresolved outcome), 'none' (no clear swipe trigger).
- Map slides to the provided batch indices precisely."""



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
    hook_vocabulary=build_hook_vocabulary_block(),
    hook_formula_instruction=build_hook_formula_instruction(),
)



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
    niche_norms: dict[str, Any],
    reference_carousels: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    wants_directions: bool = False,
) -> str:
    """V2 carousel diagnosis prompt — 2-layer narrative, corpus-aware.

    Mirrors build_diagnosis_synthesis_prompt_v2() for video but uses:
    - CAROUSEL_NARRATIVE_OUTPUT_STRUCTURE (2-layer: distribution + swipe logic)
    - carousel-specific FORMAT_ANALYSIS_WEIGHTS
    - carousel_knowledge.build_carousel_context() for swipe psychology
    - reference_carousels instead of reference_videos

    Called by gemini.py:synthesize_diagnosis_carousel_v2().

    Args:
        carousel_format:    One of: carousel, carousel_product_roundup,
                            carousel_tutorial, carousel_story.
        niche_name:         Human-readable niche name.
        corpus_size:        Carousel count in corpus for this niche (last 30 days).
        niche_norms:        Dict from niche_intelligence (carousel-filtered).
        reference_carousels: List of 3 top-performing carousel dicts with analysis + metadata.
        user_analysis:      Gemini carousel extraction result.
        user_stats:         User carousel stats (views, breakout_multiplier, etc.).
        wants_directions:   If True, appends 4-5 content direction suggestions.
    """
    voice = build_voice_block(include_examples=False)
    carousel_context = build_carousel_context()

    return build_carousel_diagnosis_narrative_prompt(
        voice_block=voice,
        carousel_knowledge_block=carousel_context,
        carousel_synthesis_framing=_CAROUSEL_SYNTHESIS_FRAMING,
        carousel_format=carousel_format,
        niche_name=niche_name,
        corpus_size=corpus_size,
        niche_norms=niche_norms,
        reference_carousels=reference_carousels,
        user_analysis=user_analysis,
        user_stats=user_stats,
        wants_directions=wants_directions,
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


def build_knowledge_prompt(message: str, session_context: dict[str, Any]) -> str:
    """§3a Rule A — text-only knowledge with optional session summary."""
    prior_context_block = ""
    completed = session_context.get("completed_intents", [])
    if completed:
        summary = session_context.get("analyses_summary", {})
        prior_context_block = f"""
Ngữ cảnh phiên trước — tham chiếu nếu liên quan đến câu hỏi:
{json.dumps(summary, indent=2, ensure_ascii=False)}
"""

    # include_examples=False: knowledge Q&A doesn't need diagnosis examples
    voice = build_voice_block(include_examples=False)

    return f"""{voice}

---

{_DOMAIN_KNOWLEDGE}
{prior_context_block}
Câu hỏi người dùng: {message}

Trả lời thẳng thắn và cụ thể — không né tránh câu trả lời.
Tham chiếu ngữ cảnh phiên trên nếu liên quan.
Không dùng bảng field/value. Không dùng bullet point trừ khi câu hỏi bản chất là danh sách.
"""


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
        "MỤC TIÊU: Xu hướng nội dung nổi bật trong niche. Xác định những gì các video tham chiếu thực hiện về mặt cấu trúc (hook, nhịp độ, format). Nêu 2–3 hướng nội dung kèm bằng chứng từ JSON."
    ),
    "trend_spike": (
        "MỤC TIÊU: Trend đang tăng tốc — nhấn mạnh những gì đang bứt phá gần đây so với các format đã ổn định.\n\n"
        "ĐỊNH DẠNG BẮT BUỘC — mỗi trend PHẢI là một JSON block trên một dòng riêng, ngay sau câu giới thiệu trend:\n"
        '{"type":"trend_card","title":"<tên trend>","recency":"<vd: Mới 3 ngày>","signal":"<rising|early|stable|declining>",'
        '"breakout":"<vd: 4,2x hoặc bỏ trống nếu không rõ>","videos":["<video_id1>","<video_id2>","<video_id3>"],'
        '"hook_formula":"<template điền vào: ĐỪNG [hành động] nếu...>","mechanism":"<lý do chạy vì: 1 câu>","corpus_cite":"<vd: 412 video · tuần này>"}\n\n'
        "- Chỉ dùng video_id từ JSON bên dưới — KHÔNG tự tạo ID\n"
        '- signal: "rising" = đang tăng nhanh, "early" = mới xuất hiện, "stable" = ổn định, "declining" = đang giảm\n'
        "- breakout: tỷ lệ views/trung bình niche — dùng dấu phẩy Việt Nam: 3,2x không 3.2x\n"
        "- Sau JSON block, thêm 2-3 dòng phân tích sâu về trend đó (cơ chế, timing, rủi ro)\n"
        "- Kết thúc bằng mục **Cơ hội giao nhau** nếu có pattern xuyên trend"
        "\n\nÂM THANH XU HƯỚNG (từ khóa trending_sounds trong JSON):\n"
        "- Nếu JSON chứa trending_sounds, LUÔN đề cập ít nhất 1 âm thanh đang trending trong phân tích\n"
        "- Format: **Âm thanh đang nổi:** '[tên âm thanh]' — dùng trong X video, [nhận định ngắn]\n"
        "- Chỉ đề cập nếu usage_count >= 3 — bỏ qua nếu danh sách rỗng hoặc không đủ dữ liệu"
    ),
    "competitor_profile": (
        "MỤC TIÊU: Phân tích tài khoản đối thủ — tóm tắt công thức nội dung lặp lại của họ từ các bài đăng.\n"
        "CẤU TRÚC: Mở bằng nhận định chính về đối thủ (1-2 câu). Sau đó: **Công thức lặp** (hook style, format, nhịp — 2-3 gạch đầu dòng), "
        "**Điểm mạnh cần học** (2-3 gạch), **Điểm yếu khai thác được** (2-3 gạch), **Khoảng trống** (1-2 gạch — chủ đề/format họ chưa đụng)."
    ),
    "series_audit": (
        "MỤC TIÊU: Kiểm tra series — so sánh pattern xuyên suốt các video của người dùng; ghi nhận tính nhất quán và khoảng trống.\n"
        "CẤU TRÚC: Mở bằng nhận định chính về series (1-2 câu). Sau đó: **Pattern nhất quán** (hook, format, nhịp lặp — 2-3 gạch), "
        "**Bài đứng đầu và vì sao** (1-2 gạch, trích số liệu), **Bài yếu nhất và vì sao** (1-2 gạch), **Hành động tiếp** (2-3 gạch cụ thể)."
    ),
    "brief_generation": (
        "MỤC TIÊU: Brief sản xuất — xuất brief quay phim ngắn gọn.\n"
        "CẤU TRÚC: **Hook** (câu mở + hành động khung đầu), **Beat sheet** (3-5 beat, mỗi beat 1 dòng: thời lượng + hành động + chữ trên màn hình), "
        "**CTA** (câu kết + overlay), **Ghi chú sản xuất** (setup, prop, âm nhạc nếu cần). Ngắn gọn — creator cần đọc trong 30 giây."
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
        "- Sau tất cả JSON beats, thêm **Ghi chú sản xuất tổng** (1 đoạn ngắn: setup, nhạc nền gợi ý, tone)\n"
        "- Kết thúc bằng **CTA beat**: câu kết + overlay kêu gọi hành động"
    ),
    "video_diagnosis": (
        "MỤC TIÊU: Chẩn đoán video — thiết lập chuẩn niche từ niche_norms + video tham chiếu, sau đó đo video của người dùng so với chuẩn đó.\n\n"

        "## INPUT BẠN NHẬN ĐƯỢC (từ JSON bên dưới)\n"
        "- user_video: kết quả Gemini extraction của video người dùng (hook_analysis, scenes, tone, text_overlays, transcript, transitions_per_second, metadata)\n"
        "- reference_videos: 3 video top-performing cùng niche (metadata + analysis)\n"
        "- niche_norms: từ materialized view niche_intelligence. Các trường quan trọng:\n"
        "    • Kỹ thuật video: avg_face_appears_at, pct_face_in_half_sec, avg_transitions_per_second, avg_text_overlays, has_cta_pct, median_duration\n"
        "    • Phân phối: pct_has_specific_hashtags (% top video dùng hashtag cụ thể cho ngách — không phải #trending #fyp chung chung), pct_has_caption_text (% top video có caption mô tả thật), avg_hashtag_count (số hashtag trung bình), pct_original_sound (% dùng âm thanh gốc tự tạo)\n"
        "    • Performance: avg_engagement_rate, commerce_pct, sample_size\n"
        "    • Phân bố nội dung: hook_distribution, format_distribution\n"
        "    CÁCH DÙNG pct_has_specific_hashtags và pct_has_caption_text: nếu user dùng hashtag chung chung hoặc thiếu caption, so sánh với % này trong niche để đưa ra nhận định phân phối cụ thể.\n"
        "- corpus_size: tổng video trong niche 30 ngày qua\n\n"

        "## CẤU TRÚC OUTPUT BẮT BUỘC\n\n"

        "**Dòng mở đầu (verdict):** 1–2 câu, KHÔNG có tiêu đề, nhảy thẳng vào.\n"
        'Format: "Video bạn [X]x views so với niche [tên niche]. Dựa trên {corpus_size} video tháng này."\n'
        "- Breakout > 2x: dùng cụm vượt trội\n"
        "- Breakout 0.5–2x: ngang mức trung bình niche\n"
        "- Breakout < 0.5x: thấp hơn norm, nêu rõ khoảng cách\n"
        "- Nếu không có breakout_multiplier trong metadata: mở bằng nhận định mạnh nhất từ data có trong tay\n\n"

        "**Chẩn đoán theo timeline video** — theo thứ tự xuất hiện, dùng **bold** cho label:\n\n"

        "**Hook: [🔴🟡🟢] [Tên hook type tiếng Việt]**\n"
        "1 câu mô tả hook cụ thể của video — KHÔNG mô tả chung chung.\n"
        '"Chạy vì: [mechanism — tại sao hook này chạy hoặc flop]."\n'
        "Nếu 🔴: thêm 'Gợi ý: [hook template copy-paste được, dùng [ngoặc vuông] tiếng Việt cho placeholder].'\n"
        "So sánh với niche: 'Top hook niche [tên niche]: [tên hook] — [X]% top video dùng.' (dùng hook_distribution từ niche_norms nếu có)\n\n"

        "**Mặt xuất hiện: [🔴🟡🟢] [X]s (chuẩn niche: [avg_face_appears_at]s)**\n"
        "Chỉ hiển thị nếu face_appears_at có trong analysis. Nếu chậm hơn norm: trích pct_face_in_half_sec.\n\n"

        "**Text overlay: [🔴🟡🟢] [X] overlays (chuẩn niche: [avg_text_overlays])**\n"
        "Nếu 0: nhắc Vietnamese viewers đọc text mạnh, thêm text hook trong 0,5s đầu.\n"
        "QUAN TRỌNG — CAROUSEL: Nếu content_type = 'carousel', text không nằm trong text_overlays (trường đó dành cho video timeline). "
        "Text trên ảnh carousel nằm trong slides[].text_on_slide và slides[].text_density. "
        "Đánh giá text từ slides[] — KHÔNG báo '0 text overlays' cho carousel.\n\n"

        "**Nhịp cắt cảnh: [🔴🟡🟢] [X] transitions/s (chuẩn niche: [avg_transitions_per_second])**\n"
        "Nếu thấp: gợi ý cụ thể (B-roll, cắt cảnh). Nếu có timestamp lặp: chỉ ra khoảng giây đó.\n"
        "QUAN TRỌNG: Nếu content_type = 'carousel', KHÔNG đề cập transitions/s — không áp dụng cho carousel.\n\n"

        "**CTA: [🔴🟡🟢]**\n"
        "Nếu không có: gợi ý CTA cụ thể kèm lý do save rate. Nếu có: nhận xét ngắn.\n\n"

        "**So với niche — video tham chiếu:**\n"
        "Liệt kê 3 reference_videos: @handle — [views] views — hook: [hook_type_vi] — [days_ago] ngày trước\n"
        "Với mỗi video tham chiếu: xuất JSON block trên dòng riêng ngay sau câu nhắc đến video:\n"
        '{"type": "video_ref", "video_id": "<id>", "handle": "@<handle>", "views": <số>, "days_ago": <số từ metadata>, "breakout": <số nếu >1>}\n\n'

        "**Video tiếp theo nên làm gì:**\n"
        "2–3 dòng max. Kết thúc bằng hook template copy-paste được.\n"
        "'Hook template: [câu mở đầu dùng [ngoặc vuông] tiếng Việt cho phần thay thế]'\n\n"

        "## 14 RULES BẮT BUỘC\n\n"

        "R1: KHÔNG tự giới thiệu. KHÔNG 'Chào bạn', KHÔNG 'với tư cách là chuyên gia'. Nhảy thẳng vào verdict.\n"
        "R2: Dùng 'Chạy vì:' cho MỌI mechanism. KHÔNG 'Cơ chế:', KHÔNG 'Tại sao hiệu quả:', KHÔNG 'Lý do:'.\n"
        "R3: KHÔNG fabricate metrics. KHÔNG 'Dự kiến >45%', KHÔNG 'Hook rate ước tính'. Chỉ report số từ data thật trong JSON. Nếu không có data → KHÔNG đề cập metric đó.\n"
        "R4: MỌI nhận định phải có data backing từ JSON. 'Vượt chuẩn' → vượt bao nhiêu x? So với bao nhiêu video? Timeframe?\n"
        "R5: Corpus citation BẮT BUỘC ở dòng đầu. Dùng corpus_size và niche từ JSON.\n"
        "R6: 3 reference videos BẮT BUỘC — hiển thị @handle + views + hook type + days_ago. Xuất video_ref JSON block cho mỗi video.\n"
        "R7: Hook template BẮT BUỘC ở cuối — copy-paste được, dùng [ngoặc vuông] tiếng Việt cho placeholder.\n"
        "R8: Số dùng format Vietnamese: dấu chấm cho hàng nghìn (1.200), dấu phẩy cho thập phân (3,2x, 4,5%).\n"
        "R9: English loanwords giữ nguyên: hook, content, view, save, format, trend, CTA, creator, viral, share, comment, like, follower. MỌI TỪ KHÁC viết tiếng Việt. KHÔNG để English trong ngoặc đơn.\n"
        "R10: KHÔNG dùng heading markdown (##, ###, ####). Dùng **bold** cho label section. Output là chat, không phải report.\n"
        "R11: KHÔNG dùng cụm báo chí: 'làm mưa làm gió', 'gây bão', 'hot hit', 'đình đám'.\n"
        "R12: KHÔNG đánh số section (1., 2., 3.). Chẩn đoán chảy tự nhiên theo timeline video.\n"
        "R13: 'Gợi ý:' cho fix recommendation. KHÔNG 'Sửa lỗi:' (nghe như bug report).\n"
        "R14: Tone: creator nói chuyện với creator. Casual nhưng professional. Dùng 'bạn', không dùng 'quý vị'. Dùng 'chạy/flop' tự nhiên.\n\n"

        "NẾU niche_norms rỗng hoặc thiếu trường: bỏ qua so sánh với chuẩn niche cho trường đó — KHÔNG tự tạo số."
    ),
    "kol_search": (
        "MỤC TIÊU: Tìm KOL/creator — từ các bài đăng tham chiếu trong JSON, gợi ý tài khoản đáng xem và lý do.\n"
        "CẤU TRÚC: Liệt kê 3-5 tài khoản, mỗi tài khoản: **@handle** — nhận định chính (hook style, ER, niche fit) + vì sao nên theo dõi/hợp tác. "
        "Kết thúc bằng **Pattern chung** (1-2 câu — điểm chung giữa các KOL top)."
    ),
    "find_creators": (
        "MỤC TIÊU: Tìm KOL/creator — từ các bài đăng tham chiếu trong JSON, gợi ý tài khoản đáng xem và lý do.\n"
        "CẤU TRÚC: Liệt kê 3-5 tài khoản, mỗi tài khoản: **@handle** — nhận định chính (hook style, ER, niche fit) + vì sao nên theo dõi/hợp tác. "
        "Kết thúc bằng **Pattern chung** (1-2 câu — điểm chung giữa các KOL top)."
    ),
    "own_channel": (
        "MỤC TIÊU: Soi kênh của người dùng — đối chiếu với benchmark niche từ video tham chiếu; chỉ ra điểm khớp/lệch và hành động.\n"
        "CẤU TRÚC: Mở bằng nhận định chính (1-2 câu). **Đang làm đúng** (2-3 gạch — pattern khớp niche benchmark), "
        "**Đang lệch** (2-3 gạch — so sánh cụ thể với reference videos), **Hành động ưu tiên** (2-3 gạch — việc cụ thể, đo được)."
    ),
}


def build_synthesis_prompt(
    intent_key: str,
    payload: dict[str, Any],
    *,
    collapsed_questions: list[str] | None = None,
    niche_key: str | None = None,
    corpus_citation: str = "",
) -> str:
    """§18 item 17 — intent-specific framing + optional collapsed questions.

    Args:
        intent_key:           Routing key from INTENT_SYNTHESIS_FRAMING.
        payload:              Dynamic corpus data from video_corpus / niche_intelligence.
        collapsed_questions:  Optional multi-question list from the user.
        niche_key:            Optional niche identifier (e.g. "skincare") — when provided,
                              injects niche-specific hook guidance from knowledge_base.py.
                              Particularly useful for brief_generation and video_diagnosis.
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

    # Static knowledge blocks — injected per intent to keep token count lean
    knowledge_block = ""
    if intent_key == "brief_generation":
        knowledge_block = "\n" + build_commerce_structure_block()
        if niche_key:
            knowledge_block += "\n\n" + build_niche_hook_block(niche_key)
    elif intent_key in ("video_diagnosis", "content_directions", "trend_spike", "shot_list"):
        if niche_key:
            knowledge_block = "\n" + build_niche_hook_block(niche_key)

    # voice_guide injects examples for video_diagnosis — skip _SYNTHESIS_FEW_SHOTS for that
    # intent to avoid duplication. Other intents still get their own few-shot blocks.
    include_ex = intent_key == "video_diagnosis"
    voice = build_voice_block(include_examples=include_ex, example_type="diagnosis")

    few_shot = "" if intent_key == "video_diagnosis" else _SYNTHESIS_FEW_SHOTS.get(intent_key, "")
    few_shot_block = ""
    if few_shot:
        few_shot_block = f"""
Viết phân tích giống ví dụ dưới — học giọng, cấu trúc, độ sâu:

{few_shot}

=== PHÂN TÍCH DỮ LIỆU MỚI ===
"""

    return f"""{voice}

---

{_DOMAIN_KNOWLEDGE}
{knowledge_block}
{citation_block}
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
    niche_norms: dict[str, Any],
    reference_videos: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
) -> str:
    """V2 diagnosis synthesis prompt — narrative structure, format-aware.

    Replaces checklist-style output for Intent ① (video_diagnosis).
    Called by gemini.py:synthesize_diagnosis_v2().

    Args:
        content_format:   Detected format string (e.g. "tutorial", "mukbang").
        niche_name:       Human-readable niche name (e.g. "skincare").
        corpus_size:      Number of videos in corpus for this niche (last 30 days).
        niche_norms:      Dict from niche_intelligence materialized view.
        reference_videos: List of reference video dicts with analysis + metadata.
        user_analysis:    Gemini extraction result for the user's video.
        user_stats:       User video stats dict (views, breakout_multiplier, etc.).
    """
    voice = build_voice_block(include_examples=True, example_type="diagnosis")

    return build_diagnosis_narrative_prompt(
        voice_block=voice,
        examples_block="",  # already included in voice_block when include_examples=True
        anti_patterns=ANTI_PATTERNS,
        content_format=content_format,
        niche_name=niche_name,
        corpus_size=corpus_size,
        niche_norms=niche_norms,
        reference_videos=reference_videos,
        user_analysis=user_analysis,
        user_stats=user_stats,
    )
