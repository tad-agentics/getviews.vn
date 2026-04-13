"""Domain knowledge constants for Gemini synthesis prompts.

Three knowledge layers:
1. DISTRIBUTION_ALGORITHM — how TikTok decides who sees a video
2. VIEWER_PSYCHOLOGY — why viewers stay, leave, save, share, comment
3. VIETNAM_MARKET — Vietnamese-specific patterns, timing, monetization

Injected into synthesis prompts alongside voice_guide (HOW to write)
and performance benchmarks (WHAT numbers mean). These blocks explain
WHY things work — the causal chain from creative decision → algorithm
signal → distribution outcome.
"""

from __future__ import annotations


DISTRIBUTION_ALGORITHM = """
THUẬT TOÁN PHÂN PHỐI TIKTOK — cách TikTok quyết định ai xem video:

TikTok phân phối theo sóng. Mỗi sóng là một bài kiểm tra — video phải vượt ngưỡng để lên sóng tiếp:

Sóng 0 — Seed pool (~200-500 views):
- Thời gian: 30-60 phút đầu sau khi đăng
- Thuật toán kiểm tra: tỷ lệ xem hết (completion rate) + tỷ lệ bỏ qua (skip rate)
- Ngưỡng vượt: completion ~50%+ để lên sóng tiếp
- Nếu chết ở đây: vấn đề là HOOK, không phải nội dung. Người xem quyết định trong 1,5 giây đầu

Sóng 1 — Distribution mở rộng (~1K-5K views):
- Thời gian: 2-6 giờ sau khi đăng
- Thuật toán kiểm tra: tương tác thật (like, comment, share, save) + tốc độ tương tác
- Ngưỡng vượt: ER >3% VÀ completion >50%
- Nếu chết ở đây: nội dung không giữ được hoặc không kích thích hành động

Sóng 2 — FYP rộng (~5K-50K views):
- Thời gian: 6-24 giờ
- Thuật toán kiểm tra: tất cả tín hiệu + tốc độ tăng tương tác (velocity)
- Đây là nơi đa số content "tốt nhưng không viral" dừng lại
- Nếu chết ở đây: velocity quá chậm — timing sai hoặc ngách đã bão hoà format này

Sóng 3 — Viral push (~50K+ views):
- Thuật toán đẩy ra nhiều nhóm demographic khác nhau
- Kiểm tra: watch time nhất quán ĐA DẠNG khán giả (không chỉ fan có sẵn)

ÁP DỤNG KHI CHẨN ĐOÁN:
- View thấp + ER tốt = kẹt Sóng 0 → vấn đề hook, KHÔNG phải nội dung dở
- View cao + ER thấp = lên Sóng 1 nhưng dừng → nội dung không giữ chân
- View dừng ~5K = fail Sóng 2 → velocity chậm hoặc bão hoà format
- Save cao + share thấp = utility content → thuật toán đẩy nhưng không viral
- Share cao + save thấp = entertainment → viral tiềm năng nhưng không bền
- Comment nhiều trong 30 phút đầu = tín hiệu mạnh gấp 3x so với comment muộn

TIKTOK SHOP / SHOPEE:
- Video có giỏ hàng (Shopping tag) chạy trong feed Shopping riêng — thuật toán khác FYP
- Conversion rate (click giỏ hàng ÷ views) quan trọng hơn ER cho video bán hàng
- Video bán hàng thường ER thấp hơn (1-2%) nhưng vẫn "chạy" nếu conversion cao
"""


VIEWER_PSYCHOLOGY = """
TÂM LÝ NGƯỜI XEM — tại sao người xem ở lại, rời đi, lưu, chia sẻ:

5 ĐIỂM QUYẾT ĐỊNH (khi người xem quyết định ở lại hay lướt tiếp):
- 0-1,5 giây: Kiểm tra ngắt nhịp — video này khác 50 video trước không?
  → Đây là lý do mặt + text overlay trong frame đầu tăng 35% tương tác
- 1,5-3 giây: Kiểm tra lời hứa — video này có gì mình muốn biết/xem?
  → Hook phải đặt câu hỏi hoặc hứa hẹn cụ thể, không mơ hồ
- 3-8 giây: Kiểm tra trả lời — lời hứa có được deliver? (vùng bỏ nhiều nhất)
  → Promise-content mismatch chết ở đây: hook hứa trả lời nhanh, video lại vòng vo
- 8-15 giây: Kiểm tra cam kết — đã đầu tư đủ thời gian, có đáng xem hết?
  → Pattern interrupt mỗi 3-4 giây giữ chân qua vùng này
- 15 giây+: Chi phí chìm — đã cam kết, chỉ lỗi nhịp cực mạnh mới mất người xem

TẠI SAO SAVE XẢY RA (tín hiệu giá trị cao nhất của TikTok):
- "Mình cần cái này sau" — utility (tutorial, list, hack, recipe)
- "Mình muốn cho ai đó xem" — social proof + identity
- "Mình muốn thử cái này" — aspiration (outfit, workout, recipe)
Save thể hiện Ý ĐỊNH — người xem sẽ quay lại. TikTok coi đây là tín hiệu mạnh nhất.

TẠI SAO COMMENT XẢY RA:
- Phản ứng cảm xúc (đồng ý, không đồng ý, bất ngờ)
- So sánh xã hội ("mình cũng vậy", "ai giống mình?")
- Yêu cầu thông tin ("mua ở đâu?", "giá bao nhiêu?", "tên sản phẩm?")
Comment trong 30 phút đầu giá trị gấp 3x comment muộn — thuật toán đo velocity.

TẠI SAO SHARE XẢY RA:
- Giải trí ("xem cái này đi" — humor, drama, shock)
- Bản sắc ("đúng mình luôn" — relatable content)
- Giá trị xã hội ("bạn cần biết cái này" — useful info)
Share ≈ Save cùng lúc = hiếm — video vừa có giá trị utility vừa có social currency.

VIETNAMESE-SPECIFIC:
- Người Việt lướt nhanh hơn trung bình — cửa sổ hook gần 1,5 giây, không phải 3 giây
- Comment tiếng Việt thường dài hơn — thuật toán đọc thời gian gõ, comment dài = tín hiệu mạnh
- "Cấm đọc comment" (đừng đọc comment) = reverse psychology hook cực mạnh ở VN
- Emoji reaction (❤️ thả tim) tính như like, không như comment — giá trị thấp hơn text comment
"""


VIETNAM_MARKET = """
THỊ TRƯỜNG TIKTOK VIỆT NAM — context đặc thù:

QUY MÔ:
- 50 triệu+ người dùng hàng tháng — thị trường lớn thứ 3 thế giới (sau Mỹ, Indonesia)
- Người dùng trung bình mở TikTok 10+ lần/ngày, xem 90+ phút/ngày

THỜI GIAN ĐĂNG TỐI ƯU (giờ Việt Nam, UTC+7):
- Khung vàng sáng: 7:00-9:00 (trước giờ làm/đi học — Minh đăng lúc 7 AM)
- Khung vàng trưa: 11:30-13:00 (giờ nghỉ trưa)
- Khung vàng tối: 19:00-22:00 (sau giờ làm — peak traffic)
- Chủ nhật: traffic cao hơn 15-20% so với ngày thường
- THỨ HAI sáng: nếu muốn lên FYP đầu tuần, đăng Chủ nhật 21:00-22:00

NGÁCH PHỔ BIẾN NHẤT (theo thứ tự lượt xem):
- Review đồ Shopee / TikTok Shop (đập hộp, chấm điểm, so sánh)
- Skincare / làm đẹp (routine, review mỹ phẩm, before-after)
- Ẩm thực (recipe, mukbang, street food)
- Hài / giải trí (skit, trend dance, reaction)
- Thời trang (outfit, OOTD, mix đồ)
- Giáo dục / EduTok (tips, kiến thức, fun facts)

KIẾM TIỀN:
- Đa số creator VN kiếm tiền qua affiliate (Shopee, TikTok Shop) — KHÔNG phải Creator Fund
- Commission Shopee: 5-15% giá sản phẩm. Video 100K views + 2% click-through + 5% conversion = ~500K-2M VND
- CTA "link in bio" hoặc "giỏ hàng" quan trọng hơn bất kỳ metric nào cho creator affiliate
- Trung bình creator 10-20M VND/tháng = ~30-50 video/tháng, mỗi video cần optimize cho click

HOOK ĐẶC THÙ VIỆT NAM (hoạt động ở VN nhưng không hoạt động quốc tế):
- "Cấm đọc comment" — reverse psychology, comment tăng 5-10x
- "Đồ Trung Quốc [giá] — có đáng không?" — cheap product test, audience khổng lồ
- "Thử [X] trong 30 ngày" — challenge format, completion rate cao vì muốn biết kết quả
- Vietnamese subtitle trên content quốc tế — translation/curation format
- "Mình sai rồi" / "đừng như mình" — confession hook, trust building cực mạnh
- "Giá gốc vs giá sale" — price comparison, kích thích FOMO mua hàng

SOUND/NHẠC:
- TikTok VN có hệ sinh thái âm thanh riêng — thường từ nhạc Việt pop, remix, hoặc clip hài
- Dùng sound đang trending tăng reach ~20-30% (thuật toán ưu tiên sound phổ biến)
- Original sound có giá trị lâu dài hơn — nếu sound của bạn viral, mọi video dùng sound đó đều link về bạn
"""


def build_domain_knowledge_block() -> str:
    """Assemble all domain knowledge into one injection block.

    Called once at module load time by prompts.py. The returned string
    is injected between voice rules and intent-specific framing.
    """
    return f"""{DISTRIBUTION_ALGORITHM}
{VIEWER_PSYCHOLOGY}
{VIETNAM_MARKET}"""
