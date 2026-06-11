"""Prompt templates + context builder for the channel diagnosis feature.

The LLM emits **stable section IDs** wrapped in ``=== ... ===``, followed
immediately by a ``TITLE: <Vietnamese>`` line. The server parser extracts the
TITLE line and attaches it to the section payload; the FE renders it verbatim.

Input context blocks use ``<<<...>>>`` delimiters — intentionally different
from the ``=== ... ===`` output markers to prevent any parser collision.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from getviews_pipeline.channel_diagnose import TrajectoryShape
from getviews_pipeline.voice_lint import build_forbidden_phrases_prompt_block

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_CHANNEL_COPY_RULES_BLOCK = build_forbidden_phrases_prompt_block()

CHANNEL_DIAGNOSIS_SYSTEM_PROMPT = """\
Bạn là chuyên gia phân tích kênh TikTok cho thị trường Việt Nam. Nhiệm vụ là \
viết một bản phân tích dạng memo tư vấn — thẳng thắn, dựa trên số liệu thực, \
bằng tiếng Việt tự nhiên như đang nói chuyện với creator. KHÔNG phải báo cáo \
kiểm toán, KHÔNG phải bảng đánh giá theo tiêu chí.

""" + _CHANNEL_COPY_RULES_BLOCK + """

NGẮN GỌN & VERDICT-FIRST — BẮT BUỘC (creator đọc lướt trên mobile):
- Mỗi section mở bằng MỘT câu verdict in đậm (hoặc câu đầu in đậm) — đọc riêng các câu đậm xuyên suốt là đủ hiểu.
- Tối đa 2 câu chứng minh sau verdict. Toàn memo ~350-450 từ. KHÔNG luận văn.
- Ưu tiên VIỆC CẦN LÀM + VIDEO THAM CHIẾU hơn giải thích dài.

ĐĂNG BÀI — KHÔNG ĐÁNH GIÁ GIỜ ĐĂNG (BẮT BUỘC):
- Giờ đăng KHÔNG quyết định view. View do nội dung quyết định.
- TUYỆT ĐỐI KHÔNG viết "đăng sai giờ", "khung giờ vàng", "lệch khung giờ". KHÔNG heatmap giờ đăng.
- Cadence (đăng đều 3-4 lần/tuần) được phép nhắc 1 câu; giờ-trong-ngày thì không.

=== QUY TẮC BẮT BUỘC: DỮ LIỆU + DIỄN GIẢI ===
Mọi số liệu (view, P%, tỉ lệ format…) phải có ngay câu giải thích ý nghĩa cho creator \
(không để số trần). Mỗi đoạn: nêu số → giải thích → hàm ý hành động (ngắn).

Khi có block <<<CHANNEL FINDINGS>>>: dùng từng finding làm bằng chứng số trong memo; \
KHÔNG khẳng định FYP % hay shadowban chắc chắn — chỉ diễn giải “có dấu hiệu”.

=== QUY TẮC VIẾT ===

Phong cách:
- Viết như bạn đang giải thích với một creator thông minh, không cần giải thích \
khái niệm cơ bản.
- Dùng số liệu cụ thể từ context: số view, số video, tên format, khoảng thời gian.
- Số lượt xem viết trong ngoặc đơn: (202K views), (1.6M views). KHÔNG dùng \
[[cite:...]] hay [[creator:...]].
- Trích dẫn video bằng format + view + tháng/năm từ <<<TOP PERFORMERS>>> khi nói đỉnh.
- KHÔNG dùng nhãn thời gian: [TUẦN NÀY], [2 TUẦN TỚI], [THÁNG TỚI].

KỶ LUẬT CÂU (bắt buộc — đây là giọng của báo cáo):
- Câu ngắn, tuyên bố thẳng. Mỗi câu đúng một ý. Đoạn 2-3 câu, không dài hơn.
- Mỗi câu phải mang số liệu hoặc tên video/creator/format cụ thể. Câu không có \
bằng chứng thì cắt.
- CẤM câu đệm: "có thể thấy rằng", "nhìn chung", "như đã đề cập", "điều này cho thấy", \
"một điều đáng chú ý là". Vào thẳng ý.
- Verdict trước, bằng chứng ngay sau. Nhịp đúng: "Đỉnh kênh 10M view. Tháng này \
1.5K-33K. Đây không phải đen đủi thuật toán — nội dung đã thay đổi tận gốc."
- Sau khi đã trích ≥3 video làm bằng chứng: chốt bằng 1 câu "khóa pattern" tổng quát \
hoá từ CHÍNH các video đó ("Mọi video trên 100K của kênh đều có ít nhất 2 trong 3: \
mặt người, quy trình thoả mãn, khung list/xếp hạng."). Không bịa pattern ngoài video đã trích.
- Mỗi nhận định "cái gì hiệu quả / cái gì hỏng" phải gắn đúng 1 video có trong \
<<<TOP PERFORMERS>>> / <<<WORST PERFORMERS>>> / <<<UGC CREATORS>>> — FE hiển thị thẻ video \
ngay cạnh prose, nên prose và thẻ phải nói về cùng video.
- Nếu <<<UGC CREATORS>>> có creator ngoài vượt video tốt nhất của kênh: nêu thẳng bội số \
("@handle đạt 1.6M với 1 video — gấp 50× video tốt nhất tháng của kênh. Vấn đề không nằm \
ở sản phẩm — nằm ở cách kênh tự nói về mình.").

Cấu trúc output (BẮT BUỘC):
Mỗi section mở đầu bằng marker ổn định + dòng TITLE:

=== verdict ===
TITLE: BỨC TRANH TỔNG THỂ
Cấu trúc 3 phần trong 2–4 đoạn ngắn:
(1) Dữ liệu + diễn giải: trích 1 video cụ thể từ <<<TOP PERFORMERS>>> (view + format + thời điểm) \
và giải thích ý nghĩa số đó.
(2) Nếu có <<<INFLECTION POINT>>> với before/after format mix: nêu thời điểm, tỉ lệ format trước/sau, \
và hệ quả lên before_avg vs after_avg. Quy kết nguyên nhân thẳng: gọi tên thay đổi nội dung và loại trừ \
lý do thuật toán («Đây không phải đen đủi thuật toán — từ <thời điểm>, kênh chuyển từ <format A> sang \
<format B>»). KHÔNG đổ cho thuật toán khi format mix đã đổi.
(3) Một câu chốt trajectory + hàm ý 30 ngày tới.

=== what_worked ===
TITLE: <trajectory-specific title — xem bảng bên dưới>
ĐIỂM MẠNH: đúng 3 gạch đầu dòng. Mỗi gạch mở bằng **tên pattern 2-4 từ tự đặt** (nhãn tiếng Việt dễ nhớ \
cho archetype nội dung — «Quy trình đóng hộp», «List 5 món», «Mặt người kể chuyện»; KHÔNG dùng nhãn \
taxonomy khô), rồi: <format>: <số liệu> — <vì sao work> — <hàm ý hành động>.
Kết: 1 câu KHÓA PATTERN in đậm — tổng quát hoá ngưỡng từ CHÍNH các video đã trích: «Mọi video trên <X> \
view của kênh đều có <A> hoặc <B> — thường cả hai». <X> là số tròn, THẤP HƠN view của video thấp nhất \
được trích; chỉ viết khi đã trích ≥3 video — nếu ít hơn, thay bằng 1 câu chốt lợi thế cấu trúc.

=== what_falling ===    [BỎ QUA khi trajectory là breakout hoặc new_account]
TITLE: <trajectory-specific title>
ĐIỂM YẾU: đúng 3 gạch đầu dòng. Mỗi gạch mở bằng **tên pattern 2-4 từ tự đặt** (như what_worked — \
«Ảnh catalog tĩnh», «Caption mô tả sản phẩm»), rồi: <điểm yếu>: <số liệu so sánh> — <nguyên nhân> — <cách sửa>.
Nếu có <<<RECENT CONTENT AUDIT>>>: trích thẳng tỉ lệ thiếu làm bằng chứng («X/Y video gần nhất không có \
mặt người») — audit là số đếm thật trên video đã phân tích khung hình, không suy đoán. Có \
avg_views_with_face vs without thì nêu chênh lệch.
Kết: 1 câu chốt nguyên nhân lớn nhất + 1 hành động tuần này.

=== video_vs_channel ===    [CHỈ emit khi context có THIS VIDEO]
TITLE: VIDEO NÀY SO VỚI KÊNH
<1-2 đoạn so sánh video target với baseline kênh cùng format>

=== competitive_landscape ===
TITLE: ĐỐI THỦ CÙNG NGÁCH ĐANG LÀM GÌ
Với MỖI peer trong <<<KÊNH CÙNG NGÁCH>>>, 1 câu riêng: họ mạnh/yếu ở điểm gì (format, tần suất, hook) \
và insight cho kênh đang phân tích.
Cuối section: 1 câu GAP — bạn ĐANG THIẾU gì so với peer mạnh nhất (format share, cadence, hoặc góc nội dung).
Nếu peer_source=thin: so sánh thận trọng với số peer hiện có, không tuyên bố mạnh.

=== ugc_vs_channel ===    [CHỈ emit khi context có <<<UGC CREATORS>>>]
TITLE: UGC VS KÊNH CHÍNH
Mỗi creator trong <<<UGC CREATORS>>> 1 câu: họ làm gì khác kênh chính (góc cá nhân, bối cảnh đời thường, \
câu hỏi thật của người xem) mà đạt bội số đó — dùng đúng số multiplier trong block.
Câu chốt: nếu UGC vượt kênh nhiều lần với follower ít hơn → vấn đề không nằm ở sản phẩm, nằm ở cách kênh \
tự nói về mình + 1 hành động cụ thể (repost/duet/hợp tác với creator đã nêu).

=== next_video ===
TITLE: VIDEO TIẾP THEO NÊN QUAY
Dựa <<<NEXT VIDEO CONCEPT>>>:
- HOOK (1 dòng, ≤12 từ, cụ thể tiếng Việt)
- PREMISE (1 dòng kịch bản ~18–25s)
- FORMAT + thời lượng từ concept
- LÝ DO: 2 phần — bằng chứng peer + gap kênh (dùng số từ concept)
- KHÁC GÌ LẦN TRƯỚC (1 dòng): concept này khác gì video gần nhất cùng format của kênh (đối chiếu \
<<<TOP PERFORMERS>>> / <<<FORMAT PERFORMANCE>>>) — nói rõ nâng cấp gì, không lặp y nguyên cái kênh vừa làm
- KỲ VỌNG (1 dòng optional): dải view dự kiến nếu execute tốt

=== recommendations ===
TITLE: KẾ HOẠCH HÀNH ĐỘNG
Sau phần khuyến nghị chính, BẮT BUỘC có delimiter riêng một dòng:
--- NGỪNG LÀM ---
Cấu trúc:
1. **ƯU TIÊN — <hành động cụ thể>**
Thân đoạn gồm:
BẰNG CHỨNG: <số liệu từ context>
KỲ VỌNG: <impact 30 ngày, conservative>

2. **<Hành động>**
<1 câu + bằng chứng số liệu>

3–4. tương tự (mỗi mục có 1 dòng bằng chứng số liệu).

Mỗi hành động phải gọi lại đúng **tên pattern** đã đặt ở what_worked / what_falling (khi áp dụng) + 1 \
bằng chứng video/creator đã trích trong memo — không khuyến nghị chung chung không bám bằng chứng.

--- NGỪNG LÀM ---
- <Việc cần ngừng> — <bằng chứng số>
  Thay vào: <cách thay thế cụ thể>
- <Mục 2> — <bằng chứng>
  Thay vào: <cách thay thể>

=== account_health ===    [CHỈ emit khi <<<OPTIONAL MEMO SECTIONS>>> liệt kê account_health]
TITLE: SỨC KHỎE TÀI KHOẢN
1–2 đoạn: dùng finding account_health (view ceiling, boost share) — chỉ “có dấu hiệu”, \
không khẳng định shadowban/FYP %. Gợi ý kiểm tra Account Status trong app TikTok.

=== policy_risk ===    [CHỈ emit khi <<<OPTIONAL MEMO SECTIONS>>> liệt kê policy_risk]
TITLE: RỦI RO CHÍNH SÁCH & COMPLIANCE
1–2 đoạn: roll-up compliance (restricted phrase, disclosure, copyright/CML) từ findings — \
nêu số video flag + hành động sửa caption/VO trước khi đăng tiếp.

=== QUY TẮC TRAJECTORY ===

Đọc <<SCENARIO>> để xác định trajectory. Áp dụng đúng framing:

- decline_from_peak:
  §1 mở bằng "Kênh từng đạt <peak_views>. Hiện tại về còn <recent_avg>."
  §3 TITLE: "NHỮNG GÌ ĐANG GIẢM" — tập trung vào pattern thất bại + inflection.

- stagnant:
  §1 mở bằng "Kênh chưa tìm được pattern bứt phá."
  §3 TITLE: "TẠI SAO MÃI KHÔNG ĐỘT PHÁ" — diagnose lý do bị plateau.

- steady_growth:
  §1 mở bằng "Kênh đang lên đều — đây là nhịp cần tăng tốc."
  §3 TITLE: "NHỮNG GÌ CẦN TĂNG TỐC" — focus vào scaling cái đang work.
  KHÔNG viết như channel đang có vấn đề.

- bursty:
  §1 mở bằng "Kênh có hit-and-miss rõ rệt — biến động lớn."
  §3 TITLE: "ĐIỀU GÌ TẠO RA SỰ CHÊNH LỆCH" — contrast hit vs miss videos.

- breakout:
  §1 mở bằng con số breakout. BỎ QUA toàn bộ === what_falling ===.
  §2 TITLE: "ĐỘT PHÁ GẦN ĐÂY" — mô tả cái vừa work và lý do.

- new_account:
  §1 mở bằng "Kênh mới — chưa đủ data để nói pattern."
  §2 TITLE: "GỢI Ý TỪ NGÁCH" — dùng niche peer videos làm reference.
  BỎ QUA === what_falling ===.
  §6 recommendations: focus vào chiến lược 30 video đầu tiên.

=== MANDATORY SECTIONS ===
Khi có block <<<SECTIONS TO EMIT>>>: CHỈ emit đúng các section trong danh sách — bỏ qua mọi section khác.
Không có block đó: verdict, what_worked, competitive_landscape, next_video, recommendations là BẮT BUỘC;
what_falling BẮT BUỘC trừ breakout và new_account; video_vs_channel CHỈ khi có THIS VIDEO.
"""

# ---------------------------------------------------------------------------
# Default titles — fallback per (section_id, trajectory)
# ---------------------------------------------------------------------------

DEFAULT_TITLES: dict[tuple[str, str], str] = {
    # verdict — always the same
    ("verdict", "decline_from_peak"): "BỨC TRANH TỔNG THỂ",
    ("verdict", "stagnant"): "BỨC TRANH TỔNG THỂ",
    ("verdict", "steady_growth"): "BỨC TRANH TỔNG THỂ",
    ("verdict", "breakout"): "BỨC TRANH TỔNG THỂ",
    ("verdict", "bursty"): "BỨC TRANH TỔNG THỂ",
    ("verdict", "new_account"): "BỨC TRANH TỔNG THỂ",
    # what_worked — varies
    ("what_worked", "decline_from_peak"): "NHỮNG GÌ TỪNG HOẠT ĐỘNG",
    ("what_worked", "stagnant"): "NHỮNG GÌ TỪNG HOẠT ĐỘNG",
    ("what_worked", "steady_growth"): "NHỮNG GÌ ĐANG HOẠT ĐỘNG",
    ("what_worked", "breakout"): "ĐỘT PHÁ GẦN ĐÂY",
    ("what_worked", "bursty"): "NHỮNG GÌ TỪNG HOẠT ĐỘNG",
    ("what_worked", "new_account"): "GỢI Ý TỪ NGÁCH",
    # what_falling — varies; only emitted for non-breakout, non-new_account
    ("what_falling", "decline_from_peak"): "NHỮNG GÌ ĐANG GIẢM",
    ("what_falling", "stagnant"): "TẠI SAO MÃI KHÔNG ĐỘT PHÁ",
    ("what_falling", "steady_growth"): "NHỮNG GÌ CẦN TĂNG TỐC",
    ("what_falling", "bursty"): "ĐIỀU GÌ TẠO RA SỰ CHÊNH LỆCH",
    # video_vs_channel
    ("video_vs_channel", "decline_from_peak"): "VIDEO NÀY SO VỚI KÊNH",
    ("video_vs_channel", "stagnant"): "VIDEO NÀY SO VỚI KÊNH",
    ("video_vs_channel", "steady_growth"): "VIDEO NÀY SO VỚI KÊNH",
    ("video_vs_channel", "breakout"): "VIDEO NÀY SO VỚI KÊNH",
    ("video_vs_channel", "bursty"): "VIDEO NÀY SO VỚI KÊNH",
    ("video_vs_channel", "new_account"): "VIDEO NÀY SO VỚI KÊNH",
    # competitive_landscape
    ("competitive_landscape", "decline_from_peak"): "ĐỐI THỦ CÙNG NGÁCH ĐANG LÀM GÌ",
    ("competitive_landscape", "stagnant"): "ĐỐI THỦ CÙNG NGÁCH ĐANG LÀM GÌ",
    ("competitive_landscape", "steady_growth"): "ĐỐI THỦ CÙNG NGÁCH ĐANG LÀM GÌ",
    ("competitive_landscape", "breakout"): "ĐỐI THỦ CÙNG NGÁCH ĐANG LÀM GÌ",
    ("competitive_landscape", "bursty"): "ĐỐI THỦ CÙNG NGÁCH ĐANG LÀM GÌ",
    ("competitive_landscape", "new_account"): "ĐỐI THỦ CÙNG NGÁCH ĐANG LÀM GÌ",
    # ugc_vs_channel — P3 (Lightreel G5), emitted only when brand UGC found
    ("ugc_vs_channel", "decline_from_peak"): "UGC VS KÊNH CHÍNH",
    ("ugc_vs_channel", "stagnant"): "UGC VS KÊNH CHÍNH",
    ("ugc_vs_channel", "steady_growth"): "UGC VS KÊNH CHÍNH",
    ("ugc_vs_channel", "breakout"): "UGC VS KÊNH CHÍNH",
    ("ugc_vs_channel", "bursty"): "UGC VS KÊNH CHÍNH",
    ("ugc_vs_channel", "new_account"): "UGC VS KÊNH CHÍNH",
    # next_video — title often overridden by model
    ("next_video", "decline_from_peak"): "VIDEO TIẾP THEO NÊN QUAY",
    ("next_video", "stagnant"): "VIDEO TIẾP THEO NÊN QUAY",
    ("next_video", "steady_growth"): "VIDEO TIẾP THEO NÊN QUAY",
    ("next_video", "breakout"): "VIDEO TIẾP THEO NÊN QUAY",
    ("next_video", "bursty"): "VIDEO TIẾP THEO NÊN QUAY",
    ("next_video", "new_account"): "VIDEO TIẾP THEO NÊN QUAY",
    # hashtag_insights — synthetic section (template on server)
    ("hashtag_insights", "decline_from_peak"): "HASHTAG NÀO ĐANG WORK CHO BẠN",
    ("hashtag_insights", "stagnant"): "HASHTAG NÀO ĐANG WORK CHO BẠN",
    ("hashtag_insights", "steady_growth"): "HASHTAG NÀO ĐANG WORK CHO BẠN",
    ("hashtag_insights", "breakout"): "HASHTAG NÀO ĐANG WORK CHO BẠN",
    ("hashtag_insights", "bursty"): "HASHTAG NÀO ĐANG WORK CHO BẠN",
    ("hashtag_insights", "new_account"): "HASHTAG NÀO ĐANG WORK CHO BẠN",
    # recommendations
    ("recommendations", "decline_from_peak"): "KẾ HOẠCH HÀNH ĐỘNG",
    ("recommendations", "stagnant"): "KẾ HOẠCH HÀNH ĐỘNG",
    ("recommendations", "steady_growth"): "KẾ HOẠCH HÀNH ĐỘNG",
    ("recommendations", "breakout"): "KẾ HOẠCH HÀNH ĐỘNG",
    ("recommendations", "bursty"): "KẾ HOẠCH HÀNH ĐỘNG",
    ("recommendations", "new_account"): "KẾ HOẠCH HÀNH ĐỘNG",
    # optional Layer B (§5.3.2)
    ("account_health", "decline_from_peak"): "SỨC KHỎE TÀI KHOẢN",
    ("account_health", "stagnant"): "SỨC KHỎE TÀI KHOẢN",
    ("account_health", "steady_growth"): "SỨC KHỎE TÀI KHOẢN",
    ("account_health", "breakout"): "SỨC KHỎE TÀI KHOẢN",
    ("account_health", "bursty"): "SỨC KHỎE TÀI KHOẢN",
    ("account_health", "new_account"): "SỨC KHỎE TÀI KHOẢN",
    ("policy_risk", "decline_from_peak"): "RỦI RO CHÍNH SÁCH & COMPLIANCE",
    ("policy_risk", "stagnant"): "RỦI RO CHÍNH SÁCH & COMPLIANCE",
    ("policy_risk", "steady_growth"): "RỦI RO CHÍNH SÁCH & COMPLIANCE",
    ("policy_risk", "breakout"): "RỦI RO CHÍNH SÁCH & COMPLIANCE",
    ("policy_risk", "bursty"): "RỦI RO CHÍNH SÁCH & COMPLIANCE",
    ("policy_risk", "new_account"): "RỦI RO CHÍNH SÁCH & COMPLIANCE",
}


def get_default_title(section_id: str, trajectory: str) -> str:
    """Return the default Vietnamese title for a (section_id, trajectory) pair."""
    if section_id == "hashtag_insights":
        return "HASHTAG NÀO ĐANG WORK CHO BẠN"
    if section_id == "next_video":
        return "VIDEO TIẾP THEO NÊN QUAY"
    return DEFAULT_TITLES.get((section_id, trajectory), section_id.upper().replace("_", " "))


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------


def _fmt_views(n: int | float) -> str:
    """Format an integer view count as a human-readable string."""
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1_000}K"
    return str(n)


def build_channel_diagnosis_context(
    handle: str,
    videos: list[dict[str, Any]],
    trajectory: TrajectoryShape,
    channel_pattern: dict[str, Any],
    recent_window_30d: dict[str, Any],
    inflection: dict[str, Any] | None,
    top_performers: list[dict[str, Any]],
    worst_performers: list[dict[str, Any]],
    creator_match: dict[str, Any] | None,
    ugc_creators: list[dict[str, Any]],
    niche_benchmarks: dict[str, Any] | None,
    channel_persona: dict[str, Any] | None = None,
    peer_source: str | None = None,
    next_video_concept: dict[str, Any] | None = None,
    channel_findings: list[Any] | None = None,
    optional_memo_sections: list[str] | None = None,
    sections_to_emit: list[str] | None = None,
    recent_content_audit: dict[str, Any] | None = None,
    brand_ugc_creators: list[dict[str, Any]] | None = None,
) -> str:
    """Build the user-facing context string with ``<<<BLOCK>>>`` delimiters.

    The ``<<<...>>>`` delimiter is intentionally different from the ``=== ... ===``
    output section markers so the LLM can't accidentally echo an input delimiter
    into the output and trip the section-header regex.
    """
    now = datetime.now(tz=UTC)
    total_videos = len(videos)
    follower_count = next((v.get("author_followers", 0) for v in videos), 0)

    # Oldest video
    oldest_dt = None
    for v in videos:
        dt = v.get("posted_at")
        if dt and (oldest_dt is None or dt < oldest_dt):
            oldest_dt = dt
    oldest_age_days = (now - oldest_dt).days if oldest_dt else 0

    global_avg = channel_pattern.get("global_avg_views", 0)
    max_views = channel_pattern.get("max_views", 0)
    recent_avg = recent_window_30d.get("avg_views", 0)
    recent_count = recent_window_30d.get("video_count", 0)
    inflection_drop = inflection.get("drop_pct", 0) if inflection else None

    blocks: list[str] = []

    # --- <<<SCENARIO>>> ---
    scenario_lines = [
        f"trajectory: {trajectory}",
        f"total_videos: {total_videos}",
        f"oldest_video_age_days: {oldest_age_days}",
        f"peak_views: {_fmt_views(max_views)}",
        f"recent_30d_avg_views: {_fmt_views(recent_avg)}",
        f"recent_30d_video_count: {recent_count}",
    ]
    if inflection_drop is not None:
        scenario_lines.append(f"inflection_drop_pct: {inflection_drop:.1f}%")
    if inflection:
        peak_q = inflection.get("peak_quarter", "")
        curr_q = inflection.get("current_quarter", "")
        if peak_q and curr_q:
            scenario_lines.append(
                f"inflection: peak at {peak_q} ({_fmt_views(inflection.get('peak_avg', 0))})"
                f" → {curr_q} ({_fmt_views(inflection.get('current_avg', 0))})"
            )
    blocks.append("<<<SCENARIO>>>\n" + "\n".join(scenario_lines))

    # --- <<<CHANNEL OVERVIEW>>> ---
    overview_lines = [
        f"handle: @{handle}",
        f"followers: {_fmt_views(follower_count)}",
        f"total_videos_analysed: {total_videos}",
        f"global_avg_views: {_fmt_views(global_avg)}",
        f"peak_views_ever: {_fmt_views(max_views)}",
        f"recent_30d_avg: {_fmt_views(recent_avg)} ({recent_count} videos)",
    ]
    blocks.append("<<<CHANNEL OVERVIEW>>>\n" + "\n".join(overview_lines))

    # --- Persona (two-axis) ---
    if channel_persona:
        dom_fmt = channel_persona.get("dominant_format") or ""
        cat = channel_persona.get("content_class_label") or ""
        ccid = channel_persona.get("dominant_content_class_id")
        blocks.append(
            "<<<KÊNH ĐANG PHÂN TÍCH>>>\n"
            f"@{handle} | dominant_format={dom_fmt} | category_vn={cat} | "
            f"content_class_id={ccid}\n"
            "(Khi nói category, dùng category_vn — không nói chung chung «lifestyle» nếu có nhãn cụ thể.)"
        )

    # --- <<<FORMAT PERFORMANCE>>> ---
    formats_data = channel_pattern.get("formats") or {}
    if formats_data:
        fmt_rows = ["format | count | avg_views | recent_avg | flag"]
        sorted_fmts = sorted(
            formats_data.items(), key=lambda kv: kv[1].get("avg_views", 0), reverse=True
        )
        for fmt, d in sorted_fmts:
            flag = " [THIN DATA]" if d.get("quality_flag") == "thin" else ""
            fmt_rows.append(
                f"{fmt} | {d.get('count', 0)} | {_fmt_views(d.get('avg_views', 0))} | "
                f"{_fmt_views(d.get('recent_avg', 0))} |{flag}"
            )
        blocks.append("<<<FORMAT PERFORMANCE>>>\n" + "\n".join(fmt_rows))

    # --- <<<TOP PERFORMERS>>> ---
    if top_performers:
        perf_lines = []
        for t in top_performers:
            snippet = str(t.get("caption_snippet") or t.get("captionSnippet") or "")[:80]
            views = t.get("views") or t.get("views", 0)
            fmt_label = t.get("format_label") or t.get("formatLabel") or ""
            vid_id = t.get("video_id") or t.get("videoId") or ""
            perf_lines.append(f'- {vid_id} | {_fmt_views(views)} views | {fmt_label} | "{snippet}"')
        blocks.append("<<<TOP PERFORMERS>>>\n" + "\n".join(perf_lines))

    # --- <<<WORST RECENT PERFORMERS>>> ---
    # Omit when trajectory is breakout or new_account (§3 not rendered)
    if worst_performers and trajectory not in ("breakout", "new_account"):
        worst_lines = []
        for t in worst_performers:
            snippet = str(t.get("caption_snippet") or t.get("captionSnippet") or "")[:80]
            views = t.get("views") or t.get("views", 0)
            fmt_label = t.get("format_label") or t.get("formatLabel") or ""
            vid_id = t.get("video_id") or t.get("videoId") or ""
            worst_lines.append(
                f'- {vid_id} | {_fmt_views(views)} views | {fmt_label} | "{snippet}"'
            )
        blocks.append("<<<WORST RECENT PERFORMERS>>>\n" + "\n".join(worst_lines))

    # --- <<<RECENT CONTENT AUDIT>>> (P3/G4 — deterministic feature counts) ---
    if recent_content_audit:
        a = recent_content_audit
        n_scanned = int(a.get("videos_scanned") or 0)
        audit_lines = [
            f"videos_scanned: {n_scanned} (video gần nhất của kênh đã có phân tích khung hình trong kho mẫu)",
            f"has_human_face: {int(a.get('face_videos') or 0)}/{n_scanned}",
            f"has_hook_first_3s: {int(a.get('hook_videos') or 0)}/{n_scanned}",
            f"has_text_overlay: {int(a.get('overlay_videos') or 0)}/{n_scanned}",
        ]
        roles = a.get("audio_roles") or {}
        if roles:
            audit_lines.append(
                "audio_track_role: " + ", ".join(f"{k}={v}" for k, v in sorted(roles.items()))
            )
        if a.get("avg_views_with_face") is not None:
            audit_lines.append(
                f"avg_views_with_face: {_fmt_views(a['avg_views_with_face'])} "
                f"vs avg_views_without_face: {_fmt_views(a['avg_views_without_face'])}"
            )
        blocks.append(
            "<<<RECENT CONTENT AUDIT (đặc điểm nội dung gần đây — số đếm thật)>>>\n"
            + "\n".join(audit_lines)
        )

    # --- <<<INFLECTION POINT>>> ---
    if inflection:
        inf_lines: list[str] = []
        if inflection.get("date_iso"):
            inf_lines.append(f"boundary_date: {inflection['date_iso']}")
        bfm = inflection.get("before_format_mix") or {}
        afm = inflection.get("after_format_mix") or {}
        if bfm:
            inf_lines.append(
                "before_format_mix: " + ", ".join(f"{k}={v}%" for k, v in bfm.items())
            )
        if afm:
            inf_lines.append(
                "after_format_mix: " + ", ".join(f"{k}={v}%" for k, v in afm.items())
            )
        if inflection.get("before_avg_views") is not None:
            inf_lines.append(f"before_avg_views: {_fmt_views(inflection.get('before_avg_views', 0))}")
        if inflection.get("after_avg_views") is not None:
            inf_lines.append(f"after_avg_views: {_fmt_views(inflection.get('after_avg_views', 0))}")
        q_avgs = inflection.get("quarter_avgs") or []
        for q, avg in q_avgs:
            inf_lines.append(f"  {q}: {_fmt_views(avg)} avg")
        if inf_lines:
            blocks.append("<<<INFLECTION POINT>>>\n" + "\n".join(inf_lines))

    # --- <<<THIS VIDEO VS CHANNEL BASELINE>>> ---
    if creator_match:
        match_lines = [
            f"target_format: {creator_match.get('target_format', '')}",
            f"target_video_views: {_fmt_views(creator_match.get('target_views', 0))}",
            f"same_format_channel_avg: {_fmt_views(creator_match.get('same_format_avg', 0))}",
            f"best_format: {creator_match.get('best_format', '')} "
            f"(avg {_fmt_views(creator_match.get('best_format_avg', 0))})",
        ]
        blocks.append("<<<THIS VIDEO VS CHANNEL BASELINE>>>\n" + "\n".join(match_lines))

    # --- Peer creators (corpus-verified) ---
    src = peer_source or "unknown"
    if ugc_creators:
        ugc_lines = []
        for c in ugc_creators:
            handle_c = c.get("handle") or ""
            followers_c = c.get("followers")
            followers_str = (
                f"{_fmt_views(int(followers_c))} followers"
                if followers_c not in (None, 0)
                else "N/A followers"
            )
            avg_v = c.get("avg_views") or 0
            fmt = c.get("format_label") or ""
            samples = c.get("sample_videos") or []
            sample_str = ", ".join(f"{_fmt_views(s.get('views', 0))} views" for s in samples[:2])
            ugc_lines.append(
                f"@{handle_c} | {followers_str} | avg {_fmt_views(avg_v)} | {fmt} | samples: {sample_str}"
            )
        blocks.append(
            f"<<<KÊNH CÙNG NGÁCH (đã có trong kho video mẫu, peer_source={src})>>>\n"
            + "\n".join(ugc_lines)
        )
    else:
        blocks.append(
            f"<<<KÊNH CÙNG NGÁCH (peer_source={src})>>>\n"
            "(Không đủ kênh cùng ngách trong kho dữ liệu để so sánh — nói rõ trong competitive_landscape.)"
        )

    # --- <<<UGC CREATORS>>> (P3/G5 — external creators posting ABOUT this brand) ---
    # Block name matches the system-prompt multiplier rule («Nếu <<<UGC CREATORS>>>
    # có creator ngoài vượt video tốt nhất của kênh: nêu thẳng bội số…»).
    if brand_ugc_creators:
        brand_lines = []
        for c in brand_ugc_creators:
            followers_c = c.get("followers")
            followers_str = (
                f"{_fmt_views(int(followers_c))} followers"
                if followers_c not in (None, 0)
                else "N/A followers"
            )
            snippet = str(c.get("caption_snippet") or "")[:80]
            brand_lines.append(
                f"@{c.get('handle')} | {followers_str} | video {_fmt_views(int(c.get('views') or 0))} views "
                f"(gấp {c.get('multiplier')}× TB 30 ngày của kênh) | \"{snippet}\""
            )
        blocks.append(
            "<<<UGC CREATORS (creator NGOÀI đăng video về brand/kênh này)>>>\n"
            + "\n".join(brand_lines)
        )

    # --- <<<NICHE BENCHMARK>>> ---
    # Omit when niche peer count < 10
    if niche_benchmarks and int(niche_benchmarks.get("channel_count") or 0) >= 10:
        bench_lines = [
            f"niche_channel_count: {niche_benchmarks.get('channel_count', 0)}",
            f"niche_avg_views_p25: {_fmt_views(niche_benchmarks.get('avg_views_p25', 0))}",
            f"niche_avg_views_p50: {_fmt_views(niche_benchmarks.get('avg_views_p50', 0))}",
            f"niche_avg_views_p75: {_fmt_views(niche_benchmarks.get('avg_views_p75', 0))}",
            f"niche_engagement_p75: {float(niche_benchmarks.get('engagement_p75', 0)):.2%}",
        ]
        blocks.append("<<<NICHE BENCHMARK>>>\n" + "\n".join(bench_lines))

    if next_video_concept:
        nv_lines = [
            f"format: {next_video_concept.get('format')}",
            f"format_label_vn: {next_video_concept.get('format_label')}",
            f"duration_sec: {next_video_concept.get('duration_sec')}",
            f"sample_peer: @{next_video_concept.get('sample_peer_handle')}",
            f"peer_avg_views: {_fmt_views(next_video_concept.get('peer_avg_views', 0))}",
            f"channel_share_of_format_pct: {next_video_concept.get('channel_share_pct')}",
            f"rationale_struct: {next_video_concept.get('rationale_struct')}",
            f"sample_video_url: {next_video_concept.get('sample_video_url')}",
        ]
        blocks.append("<<<NEXT VIDEO CONCEPT>>>\n" + "\n".join(nv_lines))

    if channel_findings:
        from getviews_pipeline.channel_findings import format_findings_for_prompt

        block = format_findings_for_prompt(channel_findings)
        if block:
            blocks.append(block)

    if sections_to_emit:
        blocks.append(
            "<<<SECTIONS TO EMIT>>>\n"
            + "\n".join(f"- {sid}" for sid in sections_to_emit)
            + "\n(Chỉ emit đúng các section trên — bỏ qua section không có trong danh sách.)"
        )

    if optional_memo_sections:
        blocks.append(
            "<<<OPTIONAL MEMO SECTIONS>>>\n"
            + "\n".join(f"- {sid}" for sid in optional_memo_sections)
            + "\n(Bắt buộc emit đúng các section trên sau recommendations, trước kết thúc.)"
        )

    return "\n\n".join(blocks)
