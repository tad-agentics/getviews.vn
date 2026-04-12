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
# Hook taxonomy is injected from knowledge_base.py at module load time.
# ---------------------------------------------------------------------------

_STRATEGIST_CONTEXT_TEMPLATE = """
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

{hook_vocabulary}

{hook_formula_instruction}

QUY TẮC CƠ CHẾ (P0-5):
Sau mỗi nhận định hoặc đề xuất, LUÔN giải thích TẠI SAO trong 1-2 câu.
Dùng "Chạy vì:" — KHÔNG dùng "Tại sao hiệu quả:" (quá formal, không giống creator nói).

Pattern chuẩn: "[Nhận định]. Chạy vì: [lý do cụ thể dựa trên data]."

✅ Đúng: "Hook 'ĐỪNG MUA...' đang 3,2x views. Chạy vì: bỏ câu trả lời cliché, buộc người xem tò mò → comment hỏi thêm → algorithm đẩy reach."
❌ Sai:  "Tại sao hiệu quả: cơ chế tâm lý tạo sự tò mò..." (giáo trình, không phải creator)

Viết như đang nói chuyện với creator khác, không phải viết báo cáo.
"Chạy" = content performs well. "Flop" = content không được algorithm đẩy.
Tham chiếu dữ liệu thật khi có ("92% top video mở bằng mặt trong niche này").

CỤM TỪ CẤM — không bao giờ dùng:
"nên cân nhắc", "thử nhiều cách", "analysis indicates", "signals suggest",
"it is recommended", "it is worth noting", "it's important to",
"Dựa trên dữ liệu" (dùng cụm tự nhiên hơn thay thế).

QUY TẮC TRÍCH DẪN VIDEO (P0-2):
Khi nhắc đến video cụ thể từ corpus, LUÔN kèm theo một JSON block trên một dòng riêng ngay sau câu đó:
{{"type": "video_ref", "video_id": "<id>", "handle": "@<handle>", "views": <số>, "days_ago": <số>}}

- Chỉ xuất block khi có video_id thật từ dữ liệu JSON bên dưới — KHÔNG tự tạo ID
- Mỗi video chỉ xuất 1 block (không lặp lại cùng video_id)
- Đặt block ngay sau câu nhắc đến video, không gom về cuối bài

QUY TẮC CỨNG: Tất cả phản hồi phải bằng tiếng Việt.
"""

# Resolve placeholders once at import — no per-call overhead
_STRATEGIST_CONTEXT = _STRATEGIST_CONTEXT_TEMPLATE.format(
    hook_vocabulary=build_hook_vocabulary_block(),
    hook_formula_instruction=build_hook_formula_instruction(),
)


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
- Trường content_direction phản ánh pattern cấu trúc mà extraction model nhận diện — dùng như quan sát bổ sung, không dùng làm bằng chứng chính cho nhận định
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
- content_direction phản ánh pattern cấu trúc mà extraction model nhận diện — dùng như quan sát bổ sung, không dùng làm bằng chứng chính cho nhận định
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
Ngữ cảnh phiên trước — tham chiếu nếu liên quan đến câu hỏi:
{json.dumps(summary, indent=2, ensure_ascii=False)}
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


# ---------------------------------------------------------------------------
# Synthesis few-shot examples — voice / structure anchor for build_synthesis_prompt
# ---------------------------------------------------------------------------

_SYNTHESIS_FEW_SHOTS: dict[str, str] = {
    "video_diagnosis": """
=== EXAMPLE: video_diagnosis — skincare niche, 1,2M views, weak CTA, corpus-backed ===

INPUT PAYLOAD (excerpt):
{
  "niche": "skincare",
  "corpus_size": 412,
  "niche_norms": {
    "sample_size": 412,
    "avg_face_appears_at": 0.6,
    "pct_face_in_half_sec": 71,
    "avg_transitions_per_second": 0.42,
    "avg_text_overlays": 3.1,
    "avg_engagement_rate": 0.038,
    "has_cta_pct": 58,
    "hook_distribution": {"boc_phot": 38, "phan_ung": 27, "canh_bao": 19, "so_sanh": 12},
    "median_duration": 28
  },
  "user_video": {
    "metadata": {
      "author": "@drskn.vn", "views": 1200000, "likes": 41000, "comments": 890,
      "shares": 3200, "bookmarks": 5100, "engagement_rate": 3.52, "duration_sec": 42
    },
    "analysis": {
      "hook_analysis": {
        "hook_type": "boc_phot", "hook_phrase": "Sự thật về retinol mà hầu hết bác sĩ không nói",
        "face_appears_at": 0.3, "first_speech_at": 0.0, "first_frame_type": "face_with_text"
      },
      "text_overlays": ["SỰ THẬT VỀ RETINOL", "Da nhạy cảm đọc ngay"],
      "transitions_per_second": 0.38,
      "cta": null, "tone": "educational"
    }
  },
  "reference_videos": [
    {"metadata": {"video_id": "7381001", "author": "@beautyclassic", "views": 2100000, "engagement_rate": 4.8}, "analysis": {"hook_analysis": {"hook_type": "boc_phot", "first_frame_type": "face_with_text"}, "transitions_per_second": 0.51}},
    {"metadata": {"video_id": "7381002", "author": "@skinvn.daily", "views": 890000, "engagement_rate": 5.2}, "analysis": {"hook_analysis": {"hook_type": "canh_bao", "first_frame_type": "face"}, "transitions_per_second": 0.45}},
    {"metadata": {"video_id": "7381003", "author": "@drfacevn", "views": 640000, "engagement_rate": 6.1}, "analysis": {"hook_analysis": {"hook_type": "boc_phot", "first_frame_type": "face_with_text"}, "transitions_per_second": 0.44}}
  ]
}

CORRECT SYNTHESIS OUTPUT:
1,2 triệu view — ngang tốp niche skincare tháng này. Dựa trên 412 video tháng này, median niche vào khoảng 280k, tức video bạn đang ~4,3x. Vấn đề không phải reach, mà là bạn đang để conversion đi qua tay.

**Hook: 🟢 Bóc Phốt**
"Sự thật về retinol mà hầu hết bác sĩ không nói" — dùng authority ngược mainstream + pain point người dùng skincare nhạy cảm. Mặt lên 0,3s, text overlay "SỰ THẬT VỀ RETINOL" trong frame đầu.
Chạy vì: claim ngược lại điều người nghe đã biết buộc họ ở lại để kiểm chứng. Bác sĩ tự phủ nhận chính sách ngành = controversy nhẹ, comment tranh luận đẩy reach vòng 2.
Top hook niche skincare: Bóc Phốt — 38% top video dùng (niche_norms). Bạn đang dùng đúng.

**Mặt xuất hiện: 🟢 0,3s (chuẩn niche: 0,6s)**
Sớm hơn chuẩn niche — 71% top video mở bằng mặt trong 0,5s. Bạn đang ở nhóm tốt.

**Text overlay: 🟢 2 overlays (chuẩn niche: 3,1)**
Có, nhưng thấp hơn norm một chút. "Da nhạy cảm đọc ngay" là hook phụ tốt — thêm 1 overlay tại phần payoff (khoảng 15–20s) để neo takeaway.

**Nhịp cắt cảnh: 🟡 0,38 transitions/s (chuẩn niche: 0,42)**
Sát chuẩn nhưng hơi chậm. @beautyclassic và @skinvn.daily — cả hai chạy 0,44–0,51 với ER cao hơn bạn. Video 42 giây mà nhịp dưới 0,4 = người xem cảm giác kéo dài khoảng giây 25–35. Thêm 1–2 cận da hoặc cut sang text slide ở đoạn đó.

**CTA: 🔴 Không có**
1,2 triệu người vừa xem video về retinol — không ai được chỉ bước tiếp theo. 5.100 bookmark nói rõ intent: audience muốn quay lại, nhưng bạn không đóng vòng.
Gợi ý: thêm CTA "Lưu lại để không quên — da nhạy cảm cần đọc kỹ bước 2" ở giây 38–40. Save CTA outperform follow CTA khoảng 2x trong niche educational skincare.

**So với niche — video tham chiếu:**
@beautyclassic — 2.100.000 views — hook: Bóc Phốt — 5 ngày trước
{"type": "video_ref", "video_id": "7381001", "handle": "@beautyclassic", "views": 2100000, "days_ago": 5}
@skinvn.daily — 890.000 views — hook: Cảnh Báo — 8 ngày trước
{"type": "video_ref", "video_id": "7381002", "handle": "@skinvn.daily", "views": 890000, "days_ago": 8}
@drfacevn — 640.000 views — hook: Bóc Phốt — 11 ngày trước
{"type": "video_ref", "video_id": "7381003", "handle": "@drfacevn", "views": 640000, "days_ago": 11}
Cả 3 đều dùng face_with_text trong frame đầu và có CTA rõ ràng — điểm chung của top skincare tháng này.

**Video tiếp theo nên làm gì:**
Giữ nguyên hook Bóc Phốt — đang chạy đúng format. Thêm CTA save vào 5 giây cuối và 1 cut thêm ở đoạn giữa để kéo nhịp lên 0,45+. Nếu muốn thử format mới, Cảnh Báo đang là hook thứ 3 trong niche và chưa bão hòa.
Hook template: "ĐỪNG dùng [thành phần] nếu da bạn đang [tình trạng] — bác sĩ không nói điều này"
""",
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
        "- niche_norms: từ materialized view niche_intelligence — sample_size, avg_face_appears_at, pct_face_in_half_sec, avg_transitions_per_second, hook_distribution, format_distribution, avg_text_overlays, avg_engagement_rate, has_cta_pct, commerce_pct, median_duration\n"
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
        "Nếu 0: nhắc Vietnamese viewers đọc text mạnh, thêm text hook trong 0,5s đầu.\n\n"

        "**Nhịp cắt cảnh: [🔴🟡🟢] [X] transitions/s (chuẩn niche: [avg_transitions_per_second])**\n"
        "Nếu thấp: gợi ý cụ thể (B-roll, cắt cảnh). Nếu có timestamp lặp: chỉ ra khoảng giây đó.\n\n"

        "**CTA: [🔴🟡🟢]**\n"
        "Nếu không có: gợi ý CTA cụ thể kèm lý do save rate. Nếu có: nhận xét ngắn.\n\n"

        "**So với niche — video tham chiếu:**\n"
        "Liệt kê 3 reference_videos: @handle — [views] views — hook: [hook_type_vi] — [days_ago] ngày trước\n"
        "Với mỗi video tham chiếu: xuất JSON block trên dòng riêng ngay sau câu nhắc đến video:\n"
        '{"type": "video_ref", "video_id": "<id>", "handle": "@<handle>", "views": <số>, "days_ago": <số>}\n\n'

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

    few_shot = _SYNTHESIS_FEW_SHOTS.get(intent_key, "")
    few_shot_block = ""
    if few_shot:
        few_shot_block = f"""
Viết phân tích giống ví dụ dưới — học giọng, cấu trúc, độ sâu:

{few_shot}

=== PHÂN TÍCH DỮ LIỆU MỚI ===
"""

    return f"""{_STRATEGIST_CONTEXT}
{knowledge_block}
{citation_block}
{framing}
{qblock}
{few_shot_block}
Bằng chứng (JSON):
{data_json}

Viết markdown phân tích chiến lược. Không lặp lại JSON thô. Không dùng bảng field-value."""
