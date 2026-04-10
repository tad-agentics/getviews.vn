"""Gemini prompts for video analysis, batch summary, and strategist diagnosis."""

from __future__ import annotations

import json
from typing import Any

from getviews_pipeline.models import ContentType

# ---------------------------------------------------------------------------
# Video analysis prompt — Gemini call 1
# ---------------------------------------------------------------------------

# §14 — short extraction prompt (full schema enforced via response_json_schema).
VIDEO_EXTRACTION_PROMPT = """Analyze this TikTok video. Return ONLY JSON matching the schema — no markdown.
Be precise on hook_analysis, scenes, audio_transcript, and content_direction.
For audio_transcript and hook_phrase: if words are unclear, write "[unclear]" rather than guessing. Accuracy over completeness."""

CAROUSEL_EXTRACTION_PROMPT = """Analyze this TikTok photo carousel (image parts before this text). Return ONLY JSON matching the schema — no markdown.
Map slides to the provided batch indices; be precise on hook_analysis and each slide."""



# ---------------------------------------------------------------------------
# Strategist context — benchmarks and vocabulary (edit independently of few-shots)
# ---------------------------------------------------------------------------

_STRATEGIST_CONTEXT = """
Bạn là chuyên gia chiến lược nội dung TikTok hàng đầu cho thị trường Việt Nam. Bạn đã xem
hàng chục nghìn video TikTok và nắm rõ điều gì khiến nội dung chết ở ~200 lượt xem
so với nội dung bứt phá trên FYP.

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

TỪ VỰNG — dùng đúng thuật ngữ (một số giữ tiếng Anh vì cộng đồng creator VN hay dùng):
- hook rate, completion rate, pattern interrupt, open loop, CTA, dual delivery (giữ nguyên)
- Creative fatigue: hiệu suất giảm do lạm dụng cùng format
- Dead air: giây không có thông tin hình/âm mới — chết trên TikTok
- FYP: For You Page — nơi thuật toán đưa video vào feed
- "Lượt xem", "tương tác", "giữ chân người xem", "viral", "trend", "niche" — dùng tự nhiên trong câu tiếng Việt

QUY TẮC CỨNG: Tất cả phản hồi phải bằng tiếng Việt.
"""


# ---------------------------------------------------------------------------
# Few-shot examples — anchor voice and structure (update independently)
# ---------------------------------------------------------------------------

_FEW_SHOT_EXAMPLES = """
=== EXAMPLE 1: Low-view spiritual content, slow pacing, strong hook ===

INPUT DATA:
{
  "metadata": {
    "author": "@luangiai.vn",
    "views": 348, "likes": 18, "comments": 0, "shares": 0, "bookmarks": 2,
    "engagement_rate": 5.17, "duration_sec": 118.9
  },
  "analysis": {
    "hook_analysis": {
      "first_frame_type": "face_with_text",
      "face_appears_at": 4.0,
      "first_speech_at": 0.0,
      "hook_phrase": "Than cu Thien Di? Have you ever felt your soul is allergic to stability?",
      "hook_type": "question",
      "hook_notes": "Combines niche astrology term with universal psychological pain point"
    },
    "scenes": [
      {"type": "broll", "start": 0.0, "end": 102.0},
      {"type": "screen_recording", "start": 102.0, "end": 118.9}
    ],
    "transitions_per_second": 0.19,
    "energy_level": "low",
    "audio_transcript": "Than cu Thien Di? Have you ever felt your soul is allergic to stability?...",
    "tone": "emotional",
    "cta": "Visit luangiai.vn for personalized horoscope interpretation"
  }
}

CORRECT DIAGNOSIS OUTPUT:
5.17% tương tác trên 348 lượt xem — ai vào được video này thì bám khá chặt. Vấn đề là
reach, và cấu trúc video giải thích vì sao.

**Điểm mạnh**
- Hook đang làm đúng việc. "Allergic to stability" cộng thuật ngữ niche (Thần cụ Thiên Di)
  tạo open loop lọc audience mạnh — ai biết cụm đó sẽ ở lại, ai không cũng tò mò. Đây là
  double hook thông minh
- Speech 0.0s = không dead air trước khi nói. Không bắt người xem chờ
- Hai save trên 348 view có ý nghĩa hơn con số: người ta bookmark để quay lại — nội dung
  có giá trị tham chiếu với đúng nhóm

**Điểm yếu**
- Gần 2 phút là quá dài so với lời hứa của hook. Mở bằng câu hỏi tạo urgency rồi bắt người xem
  chờ 118 giây mới có payoff. Đa số không chờ
- Một nhịp cắt ~5 giây là quá chậm với người vuốt từ FYP. 0.19 transitions per second nghĩa là
  5+ giây không có hình/ý mới — trên TikTok đó là eternity
- Mặt chưa lên đến 4.0s: 4 giây B-roll trước khi có kết nối người. Niche tâm linh/tâm lý
  sống nhờ face-to-camera trust — top trong vertical này thường mở bằng mặt
- Thông điệp bán hàng vào khoảng 1:42. Lúc đó đa số người không phải fan đã thoát;
  người còn lại thường không cần thuyết phục thêm

**Hook thử nghiệm**
- *"Nếu bạn sinh giờ Mão hoặc Dậu, lá số đang giấu một chi tiết về bất an mà nhiều
  thầy không nói thẳng."*
- *"Đừng coi mệnh lang thang là khổ — linh hồn bạn đang được code cho biến đổi, không phải hỗn loạn."*

**Câu hỏi cần kiểm tra**
- ER 5.17% trên chỉ 348 view là tín hiệu nội dung khớp với ai tìm thấy. Video có kẹt seed pool
  đầu xấu, hay nhịp chậm giết retention ngay sóng thuật toán đầu?
- Nếu cắt bản 45 giây, cắt mỗi ~3 giây và đưa mặt về 0.0s — completion rate có đủ nhảy để
  vượt Stage 1 phân phối không?


=== EXAMPLE 2: Viral product video, 1.6M views, no face, no CTA ===

INPUT DATA:
{
  "metadata": {
    "author": "@cucusneaker",
    "views": 1623886, "likes": 57144, "comments": 315, "shares": 4460, "bookmarks": 4946,
    "engagement_rate": 3.81, "duration_sec": 14.07
  },
  "analysis": {
    "hook_analysis": {
      "first_frame_type": "product",
      "face_appears_at": null,
      "first_speech_at": 0.0,
      "hook_phrase": "Let me tell you why I am a boss",
      "hook_type": "bold_claim",
      "hook_notes": "Combines bold spoken claim with satisfying visual of unwrapping unique packaging"
    },
    "text_overlays": [],
    "scenes": [
      {"type": "action", "start": 0.0, "end": 2.5},
      {"type": "product_shot", "start": 2.5, "end": 6.2},
      {"type": "product_shot", "start": 6.2, "end": 15.0}
    ],
    "transitions_per_second": 0.47,
    "energy_level": "medium",
    "cta": null
  }
}

CORRECT DIAGNOSIS OUTPUT:
1,6 triệu lượt xem trên clip 14 giây, không mặt, không text overlay. Giày gánh phần lớn —
nhưng bạn để lọt conversion rất lớn.

**Điểm mạnh**
- Open loop chuẩn sách giáo khoa. "Let me tell you why I am a boss" + mystery box cho
  người xem hai lý do ở lại trước khi hết giây đầu: muốn xem hộp có gì, và muốn biết sản phẩm
  có xứng claim không
- Không cần mặt — hành động unboxing 2,5 giây đầu là pattern interrupt đủ cho FYP sneakerhead.
  Chuyển động thắng presence khi sản phẩm đủ visual distinctive
- Gần 5.000 save nói rõ hành vi: bookmark để mua sau. Đây là shopping reference, không phải pure entertainment
- Shares và saves gần như ngang (4.460 vs 4.946) — hiếm. Video có cả social currency lẫn utility

**Điểm yếu**
- 1,6 triệu người thấy đôi giày họ muốn, nhưng bạn không nói tên sản phẩm. Không overlay tên,
  không "link in bio" — traffic high-intent đi thẳng ra cửa
- Nửa sau (6.2s đến hết) một cảnh liền không góc mới. Bạn thoát được vì texture pod thật sự
  thôi miên; sản phẩm kém visual hơn sẽ thấy drop cứng ~7s
- Không CTA ở đâu. Giữ được watch nhưng không close

**Hook thử nghiệm**
- *"This is the weirdest Nike box I've ever opened — and the shoes are even crazier."*
- *"If you're tired of the same old Dunks, you need to see what Nike just dropped."*

**Câu hỏi cần kiểm tra**
- Trong 315 comment, bao nhiêu chỉ hỏi tên giày — vì không có text overlay để neo
- Retention có flatline từ 6.2s đến hết, hay texture pod thật sự giữ attention không cần góc/close-up mới?
"""


_CAROUSEL_SWIPE_BENCHMARKS = """
CAROUSEL / SWIPE-THROUGH BENCHMARKS (apply with metadata + `analysis.slides`):
- Slide 1 is the full hook — there is no motion or audio carry; the first on-slide read
  must earn swipe #2 or the save before the viewer leaves.
- Early dropout pattern: bold promise on slide 1, then slide 2 repeats the headline or
  adds fluff — reads as bait; fix by delivering new information every slide.
- Mid-carousel fatigue: 3+ consecutive slides with the same visual_type and similar layout
  (e.g. text_card wall) without a pattern interrupt — swipes stall unless each card
  adds a distinct beat or list number.
- Payoff contract: listicles and "mistakes / tips / steps" formats imply the last 1–2
  slides close the loop or deliver the highest-value beat; burying the CTA or punchline
  on the final slide after a visual plateau loses high-intent swipers.
- Saves on carousels often track list utility and re-find value (bookmark to revisit);
  shares track identity ("this is so me") or humor — pair bookmarks ÷ views with slide copy.
- `transitions_per_second` in the JSON is synthetic for carousels; translate it for the
  creator as "how often each swipe reveals a new visual or textual beat," not edit cuts.
"""


_CAROUSEL_FEW_SHOT_EXAMPLES = """
=== EXAMPLE: Personal-finance carousel — sharp hook, mid holds, CTA dies on the last slide ===

INPUT DATA:
{
  "metadata": {
    "author": "@brica_budget",
    "content_type": "carousel",
    "slide_count": 6,
    "metrics": { "views": 8420, "likes": 412, "comments": 28, "shares": 19, "bookmarks": 503 },
    "engagement_rate": 5.58,
    "description": "3 money leaks that look innocent 🧵 save this for tax season"
  },
  "analysis": {
    "hook_analysis": {
      "first_frame_type": "text_only",
      "face_appears_at": null,
      "first_speech_at": null,
      "hook_phrase": "YOU IGNORE THESE 3 \"SMALL\" LEAKS",
      "hook_type": "bold_claim",
      "hook_notes": "All-caps slide 1 creates urgency; list format promised in caption"
    },
    "slides": [
      { "index": 0, "visual_type": "text_card", "text_on_slide": ["YOU IGNORE THESE 3 'SMALL' LEAKS", "…and wonder where the money went"], "note": "High-contrast typography; hook is entirely text" },
      { "index": 1, "visual_type": "text_card", "text_on_slide": ["Leak #1", "Subscriptions you forgot"], "note": "Numbered beat; new info vs slide 1" },
      { "index": 2, "visual_type": "text_card", "text_on_slide": ["Leak #2", "BNPL minimums"], "note": "Specific enough to feel actionable" },
      { "index": 3, "visual_type": "text_card", "text_on_slide": ["Leak #3", "Low-interest savings while inflation eats you"], "note": "Slightly denser type — still readable" },
      { "index": 4, "visual_type": "text_card", "text_on_slide": ["What to do this week"], "note": "Setup slide; teases payoff" },
      { "index": 5, "visual_type": "text_card", "text_on_slide": ["Follow for part 2"], "note": "Soft CTA; no checklist or link cue" }
    ],
    "transitions_per_second": 0.22,
    "energy_level": "medium",
    "key_timestamps": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
    "audio_transcript": "",
    "tone": "educational",
    "cta": null,
    "content_direction": {
      "what_works": "List structure with numbered leaks matches save intent.",
      "suggested_angles": ["One-slide summary with dollar ranges", "End on downloadable checklist"]
    }
  }
}

CORRECT DIAGNOSIS OUTPUT:
5.58% tương tác với 500+ save trên 8,4k lượt xem — người xem đang dùng bài như tài liệu
tham khảo, không phải noise. Hook đang làm việc thật.

**Điểm mạnh**
- Slide 1 không lãng phí pixel — all-caps + chữ \"leaks\" gieo pain trước swipe thứ hai.
  Đó là cách mua được thẻ thứ hai trên carousel tài chính
- Mỗi thẻ leak (slide 2–4) thật sự đổi ý — subscription chết, BNPL,
  lạm phát vs \"tiết kiệm\" — nhịp vuốt giống tiến triển, không phải loop bait
- Save cao với view tầm chục nghìn thường nghĩa packaging đọc như checklist
  utility; audience bookmark để hành động sau, không chỉ lướt qua

**Điểm yếu**
- Slide 5 nói \"this week\" nhưng slide 6 chuyển sang \"part 2\" không bước cụ thể — ai
  đi tới đó đã muốn takeaway, bạn biến nó thành cliffhanger trên format
  cần đóng vòng để giữ trust
- 0.22 synthetic transitions là nhịp chậm — ổn với finance nếu mỗi thẻ dày, nhưng
  slide 4→5→6 bắt đầu giống nhau (cùng text_card, weight tương tự). Một visual break hoặc
  thẻ mặt sẽ reset attention trước lúc ask
- Không lộ trình CTA trên slide — không \"link in bio,\" keyword, prompt comment. Traffic
  save cao là dạng tệ nhất để bỏ treo

**Hook slide-1 thử**
- *"If your paycheck vanishes by the 15th, one of these three 'small' leaks is probably the thief."*
- *"Stop calling them 'minor' expenses — these three line items are quietly carrying your whole budget."*

**Câu hỏi cần kiểm tra**
- 503 bookmark vs 412 like — người ta save slide 3 (BNPL) nhiều hơn hook không, và điều đó
  có nghĩa phần giữa đang gánh conversion hơn slide 1 nghĩ?
- Nếu slide 6 thành một bullet \"do this Monday\" kèm promise part 2, tỷ lệ save-to-comment
  có đổi đủ để justify tease part 2?
"""


# ---------------------------------------------------------------------------
# Diagnosis prompt — Gemini call 2
# ---------------------------------------------------------------------------


def _serialize_diagnosis_inputs(
    analysis: dict[str, Any], metadata: dict[str, Any]
) -> tuple[str, str]:
    serialized_analysis = json.dumps(analysis, ensure_ascii=False, indent=2)
    serialized_metadata = json.dumps(metadata, ensure_ascii=False, indent=2)
    return serialized_analysis, serialized_metadata


def build_video_diagnosis_prompt(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    """Strategist markdown synthesis for **video** analysis (scenes, timeline in seconds)."""
    serialized_analysis, serialized_metadata = _serialize_diagnosis_inputs(
        analysis, metadata
    )

    return f"""{_STRATEGIST_CONTEXT}

Viết chẩn đoán giống các ví dụ dưới đây. Học kỹ — chúng đặt thanh chất lượng, giọng và
cấu trúc bạn phải khớp.

{_FEW_SHOT_EXAMPLES}

=== CHẨN ĐOÁN BÀI ĐĂNG NÀY (VIDEO) ===

INPUT DATA:
{{
  "metadata": {serialized_metadata},
  "analysis": {serialized_analysis}
}}

CẤU TRÚC — cùng mẫu như ví dụ, theo thứ tự:

1. Nhận định mở đầu (không tiêu đề, 2–3 câu xuôi). Mở bằng phát hiện mạnh nhất. Nói thẳng, rõ.
   Có thể đổi cách mở, nhưng không bắt đầu bằng "Video này", "Phân tích",
   hay "Dựa trên dữ liệu".

2. Một phần **in đậm** phần điểm mạnh — 2–4 gạch đầu dòng. Giống ví dụ: nhận định trước,
   rồi vì sao quan trọng. Tiêu đề ngắn: tùy video (ví dụ dùng **Điểm mạnh** — có thể đổi nếu hợp hơn).

3. Một phần **in đậm** phần điểm yếu / ma sát — 2–4 gạch đầu dòng. Cùng giọng; nêu failure mode
   và tín hiệu cụ thể (giây, tỷ lệ). Tiêu đề tự chọn.

4. Một phần **in đậm** phần ý tưởng hook — đúng 2 dòng *in nghiêng*, mở đầu nói vào camera
   (như **Hook thử nghiệm** trong ví dụ; có thể đổi tiêu đề mục).

5. Một phần **in đậm** phần câu hỏi kiểm tra — đúng 2 câu hỏi dạng gạch đầu dòng, bám bất thường
   của video này (như **Câu hỏi cần kiểm tra** trong ví dụ; có thể đổi tiêu đề).

QUY TẮC CỨNG:
- Viết như người, không như hệ thống
- Không dùng: "analysis indicates", "signals suggest", "it is recommended",
  "it is worth noting", "it's important to"
- Không né tránh nhận định chính
- Không dựng bảng tóm tắt hay dump field/value
- Trường content_direction là giả thuyết AI — nếu nhắc, gắn nhãn góc chưa kiểm chứng, không coi là bằng chứng
- face_appears_at và first_speech_at tách biệt — không suy mặt từ first_speech_at;
  nếu face_appears_at là 4.0s, mặt muộn là vấn đề cấu trúc khi niche kỳ vọng mặt sớm; null = không mặt trên cam
- Không mở nhận định đầu bằng "Video này" hay "Phân tích"
- Tất cả nội dung phải bằng tiếng Việt.

Viết chẩn đoán ngay. Không lời dẫn hay kết chữ ký.
"""


def build_carousel_diagnosis_prompt(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    """Strategist markdown synthesis for **photo carousel** analysis (`analysis.slides`)."""
    serialized_analysis, serialized_metadata = _serialize_diagnosis_inputs(
        analysis, metadata
    )

    return f"""{_STRATEGIST_CONTEXT}

{_CAROUSEL_SWIPE_BENCHMARKS}

Viết chẩn đoán như ví dụ **carousel** dưới — cùng thanh giọng với video (thẳng,
creator-native, số liệu diễn giải thành ý nghĩa) nhưng mọi nhận định phải bám `analysis.slides`
(index, visual_type, text_on_slide, note) và caption/metadata. Thời gian trong hook_analysis
theo một đơn vị tổng hợp mỗi slide trừ khi metadata nói khác.

Nếu metadata nói slide bị cắt, CDN lỗi chỉ số, hoặc tải một phần, hãy phản ánh vào độ tin cậy và câu hỏi.

{_CAROUSEL_FEW_SHOT_EXAMPLES}

=== CHẨN ĐOÁN BÀI ĐĂNG NÀY (CAROUSEL ẢNH) ===

INPUT DATA:
{{
  "metadata": {serialized_metadata},
  "analysis": {serialized_analysis}
}}

CẤU TRÚC — bám ví dụ, chỉnh cho slide:

1. Nhận định mở đầu (không tiêu đề, 2–3 câu). Đọc mạnh nhất về câu chuyện vuốt,
   hook slide 1, và carousel có xứng save từ FYP không. Không neo cả bài vào cuts/giây như phim.
   Không mở bằng "Video này", "Phân tích", hay "Dựa trên dữ liệu".

2. **In đậm** phần điểm mạnh — 2–4 gạch đầu dòng; nhận định trước; trích chỉ số slide và copy trên slide.

3. **In đậm** phần điểm yếu / ma sát — 2–4 gạch đầu dòng; slide 1 yếu, tường chữ,
   thiếu CTA slide cuối, chuỗi visual_type lặp, v.v.

4. **In đậm** phần ý tưởng hook — đúng 2 dòng *in nghiêng*: dòng **slide-1** killer trên màn hình
   hoặc hook caption (như người xem nhìn thấy); chỉ dùng giọng nói nếu đúng cách đóng gói carousel.

5. **In đậm** phần câu hỏi kiểm tra — đúng 2 câu hỏi gạch đầu dòng gắn chỉ số slide,
   `metadata.slide_count`, save/view, hoặc payoff thiếu ở slide sau.

QUY TẮC CỨNG:
- Viết như người, không như hệ thống
- Không dùng: "analysis indicates", "signals suggest", "it is recommended",
  "it is worth noting", "it's important to"
- Không né tránh nhận định chính
- Không dựng bảng tóm tắt hay dump field/value
- content_direction là giả thuyết AI — nếu nhắc, gắn nhãn chưa kiểm chứng
- face_appears_at / first_speech_at theo trục tổng hợp từng slide; trích `slides[].index` 0-based khi hữu ích
- Không mở nhận định đầu bằng "Video này" hay "Phân tích"
- Tất cả nội dung phải bằng tiếng Việt.

Viết chẩn đoán ngay. Không lời dẫn hay kết chữ ký.
"""


def build_diagnosis_prompt(
    analysis: dict[str, Any],
    metadata: dict[str, Any],
    content_type: ContentType = "video",
) -> str:
    """Route to video vs carousel strategist prompt."""
    if content_type == "carousel":
        return build_carousel_diagnosis_prompt(analysis, metadata)
    return build_video_diagnosis_prompt(analysis, metadata)


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
Prior session context — reference this if relevant to the question:
{json.dumps(summary, indent=2)}
"""

    return f"""{_STRATEGIST_CONTEXT}
{prior_context_block}
Câu hỏi người dùng: {message}

Trả lời với tư cách chuyên gia chiến lược nội dung TikTok. Thẳng thắn và cụ thể.
Tham chiếu ngữ cảnh phiên trên nếu liên quan.
Không né tránh câu trả lời. Không dùng bảng field/value.
Không dùng bullet point trừ khi câu hỏi bản chất là danh sách.
Không bao giờ mở đầu bằng 'Đây là câu hỏi hay' hoặc tương tự.
"""


INTENT_SYNTHESIS_FRAMING: dict[str, str] = {
    "content_directions": (
        "MỤC TIÊU: Xu hướng nội dung nổi bật trong niche. Xác định những gì các video tham chiếu thực hiện về mặt cấu trúc (hook, nhịp độ, format). Nêu 2–3 hướng nội dung kèm bằng chứng từ JSON."
    ),
    "trend_spike": (
        "MỤC TIÊU: Trend đang tăng tốc — nhấn mạnh những gì đang bứt phá gần đây so với các format đã ổn định."
    ),
    "competitor_profile": (
        "MỤC TIÊU: Phân tích tài khoản đối thủ — tóm tắt công thức nội dung lặp lại của họ từ các bài đăng."
    ),
    "series_audit": (
        "MỤC TIÊU: Kiểm tra series — so sánh pattern xuyên suốt các video của người dùng; ghi nhận tính nhất quán và khoảng trống."
    ),
    "brief_generation": (
        "MỤC TIÊU: Brief sản xuất — xuất brief quay phim ngắn gọn (beat, tùy chọn hook, cảnh quay)."
    ),
    "video_diagnosis": (
        "MỤC TIÊU: Chẩn đoán video — thiết lập chuẩn niche từ video tham chiếu trước, sau đó đo video của người dùng so với chuẩn đó."
    ),
    "kol_search": (
        "MỤC TIÊU: Tìm KOL/creator — từ các bài đăng tham chiếu trong JSON, gợi ý tài khoản đáng xem và lý do (hook, ER, niche fit)."
    ),
    "find_creators": (
        "MỤC TIÊU: Tìm KOL/creator — từ các bài đăng tham chiếu trong JSON, gợi ý tài khoản đáng xem và lý do (hook, ER, niche fit)."
    ),
    "own_channel": (
        "MỤC TIÊU: Soi kênh của người dùng — đối chiếu với benchmark niche từ video tham chiếu; chỉ ra điểm khớp/lệch và hành động."
    ),
}


def build_synthesis_prompt(
    intent_key: str,
    payload: dict[str, Any],
    *,
    collapsed_questions: list[str] | None = None,
) -> str:
    """§18 item 17 — intent-specific framing + optional collapsed questions."""
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

    return f"""{_STRATEGIST_CONTEXT}

{framing}
{qblock}

Bằng chứng (JSON):
{data_json}

Viết markdown phân tích chiến lược. Không lặp lại JSON thô. Không dùng bảng field-value."""
