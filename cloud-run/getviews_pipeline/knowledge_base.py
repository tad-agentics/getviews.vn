"""
Vietnamese TikTok Hook Knowledge Base — static vocabulary for Gemini synthesis.

SOURCE: Research report — Vietnamese TikTok Hook Formulas (April 2026)
MIRROR: src/lib/prompts/knowledge-base.ts (frontend reference copy)

PURPOSE
-------
This module is STATIC structural knowledge. It does not change weekly.
The DYNAMIC layer (which hooks are performing right now, in this niche)
comes from video_corpus at runtime via corpus_ingest + niche_intelligence.

USAGE PATTERN
-------------
Synthesis prompt combines both layers:
  Static:  "Cảnh Báo — template: 'ĐỪNG [hành động]...', cơ chế: tạo FOMO"
  Dynamic: "Based on 412 videos this month, Cảnh Báo is #1 in skincare (38%)"
  Output:  Gemini writes a brief with the correct template + real performance data.

CONSUMERS
---------
  - prompts.py: _STRATEGIST_CONTEXT injects HOOK_KNOWLEDGE_BLOCK
  - build_synthesis_prompt: brief_generation intent injects full block
  - build_synthesis_prompt: video_diagnosis intent injects hook vocabulary
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Hook categories — 9 categories, Vietnamese-native labels
# ---------------------------------------------------------------------------

HOOK_CATEGORIES: dict[str, dict] = {
    "canh_bao": {
        "name_vi": "Cảnh Báo",
        "name_en": "warning",
        "templates": [
            "ĐỪNG [hành động] nếu chưa xem video này",
            "Sai lầm này khiến mình mất [thời gian] làm content không hiệu quả",
            "ĐỪNG [mua/dùng] [sản phẩm] — lý do ở cuối video",
            "Sai lầm khi [hành động] khiến bạn mất [hậu quả] mà không biết",
        ],
        "mechanism_vi": "Chạy vì: tạo cảm giác sợ bỏ lỡ, người xem phải xem hết để biết lý do",
        "best_niches": ["skincare", "review_do_gia_dung", "tech", "tai_chinh"],
        "visual_pairing": "Mở bằng mặt nghiêm túc nhìn camera + text overlay lớn trong 0.5s đầu",
    },
    "gia_soc": {
        "name_vi": "Giá Sốc",
        "name_en": "price_shock",
        "templates": [
            "[Sản phẩm] chỉ [giá] — mua ở đâu?",
            "Bạn có tin chỉ với [giá] bạn có thể [kết quả]?",
            "[Số] món đồ Shopee dưới [giá] mà dùng mãi không hết",
            "[Sản phẩm] Shopee mall [giá] — rẻ hơn cửa hàng [số]K",
        ],
        "mechanism_vi": 'Chạy vì: giá bất ngờ tạo phản ứng "thật hả?" → xem tiếp để xác nhận',
        "best_niches": ["review_do_gia_dung", "thoi_trang", "do_dien_tu", "shopee_haul"],
        "visual_pairing": "Text giá lớn + highlight màu đỏ/vàng trong frame đầu",
    },
    "phan_ung": {
        "name_vi": "Phản Ứng",
        "name_en": "reaction",
        "templates": [
            "Mua [sản phẩm] về dùng thử và...",
            "Thử [sản phẩm] 7 ngày — kết quả bất ngờ",
            "Mình mua [sản phẩm] viral và đây là sự thật...",
            "Trước và sau khi dùng [sản phẩm] [thời gian]",
        ],
        "mechanism_vi": 'Chạy vì: kết quả bỏ lửng ("và...") buộc xem đến cuối. Chân thật hơn quảng cáo.',
        "best_niches": ["skincare", "review_do_gia_dung", "thuc_pham", "my_pham"],
        "visual_pairing": "B-roll mở hộp + cận mặt phản ứng. Kết quả reveal ở giữa video.",
    },
    "so_sanh": {
        "name_vi": "So Sánh",
        "name_en": "comparison",
        "templates": [
            "[Sản phẩm A] vs [Sản phẩm B] — cái nào đáng tiền hơn?",
            "So sánh [A] giá [giá A] và [B] giá [giá B] — khác biệt ở đâu?",
            "[Sản phẩm] Shopee vs [sản phẩm] chính hãng — có khác gì?",
            "Xử lý vấn đề [A] có thực sự khó như lời đồn?",
        ],
        "mechanism_vi": "Chạy vì: ai cũng muốn biết cái nào tốt hơn. Comment tranh luận → algorithm đẩy.",
        "best_niches": ["skincare", "tech", "thoi_trang", "do_dien_tu"],
        "visual_pairing": "Split screen hoặc 2 sản phẩm cạnh nhau. Text so sánh 2 cột.",
    },
    "boc_phot": {
        "name_vi": "Bóc Phốt",
        "name_en": "expose",
        "templates": [
            "Sự thật về [sản phẩm/trend] mà không ai nói cho bạn",
            '[Sản phẩm] quảng cáo "thần thánh" — sự thật đằng sau',
            "Điều mà [X] năm học [lĩnh vực] không dạy bạn",
            "Vì sao [sản phẩm viral] không đáng mua — review thật",
        ],
        "mechanism_vi": 'Chạy vì: người xem cảm giác được biết "inside info". Comment chia phe → engagement cao.',
        "best_niches": ["skincare", "giao_duc", "tai_chinh", "review_do_gia_dung"],
        "visual_pairing": 'Mặt nghiêm túc + text "SỰ THẬT" overlay. Tone giọng tự tin, không thì thầm.',
    },
    "huong_dan": {
        "name_vi": "Hướng Dẫn",
        "name_en": "tutorial",
        "templates": [
            "Cách [hành động] trong [thời gian] — ai cũng làm được",
            "Mẹo [topic] mà 99% không biết",
            "[Số] bước đơn giản để [kết quả]",
            "Tool này giúp mình [kết quả] mà không cần [nỗ lực]",
        ],
        "mechanism_vi": "Chạy vì: hứa hẹn kết quả cụ thể + thời gian ngắn. Save rate cao → algorithm ưu tiên.",
        "best_niches": ["giao_duc", "tech", "skincare", "nau_an", "tai_chinh"],
        "visual_pairing": "Show kết quả trước (3s đầu) → quay lại hướng dẫn từ đầu",
    },
    "ke_chuyen": {
        "name_vi": "Kể Chuyện",
        "name_en": "story",
        "templates": [
            "Hôm qua mình [sự việc] và [kết quả bất ngờ]",
            "Mình từng suýt [từ bỏ], cho đến khi...",
            "1 năm trước mình vẫn chưa biết [lĩnh vực] là gì...",
            "Một bạn học viên từng [kết quả] chỉ nhờ [hành động đơn giản]",
        ],
        "mechanism_vi": "Chạy vì: não bộ phản ứng với câu chuyện mạnh hơn số liệu. Tạo trust trước khi bán.",
        "best_niches": ["tai_chinh", "giao_duc", "skincare", "shopee_affiliate"],
        "visual_pairing": "Nói chuyện trực tiếp với camera, casual (ngồi xe, đi bộ, uống cà phê). Không studio.",
    },
    "pov": {
        "name_vi": "POV",
        "name_en": "pov",
        "templates": [
            "POV: bạn là [nhân vật] và [tình huống]",
            "POV: ba mẹ hỏi điểm thi",
            "POV: bạn vừa tìm được [giải pháp] cho [vấn đề]",
            "POV: bà ngoại ép ăn thêm cơm",
        ],
        "mechanism_vi": "Chạy vì: người xem tưởng tượng mình trong tình huống → watch time cao. Vietnamese-specific POV chạy tốt hơn POV quốc tế.",
        "best_niches": ["giai_tri", "giao_duc", "thoi_trang", "skincare"],
        "visual_pairing": "Camera đặt ngang mặt. Acting tự nhiên. Text overlay mô tả tình huống.",
    },
    "bang_chung": {
        "name_vi": "Bằng Chứng",
        "name_en": "social_proof",
        "templates": [
            "Trước: [số] đơn/ngày. Sau: [số] đơn/ngày, chỉ vì thay đổi đúng 1 [điều]",
            "Tụi mình đã tăng [số] lượt tiếp cận chỉ bằng cách [hành động đơn giản]",
            "Content bạn flop không phải do thuật toán, mà do bạn sai ngay từ [phần]",
            "[Số]% người [hành động] mà quên bước này",
        ],
        "mechanism_vi": 'Chạy vì: số liệu cụ thể tạo uy tín ngay lập tức. "Trước/Sau" format chạy đặc biệt tốt.',
        "best_niches": ["giao_duc", "tai_chinh", "marketing", "shopee_affiliate"],
        "visual_pairing": "Text overlay số liệu lớn, JetBrains Mono style. Screenshot kết quả thật.",
    },
}

# ---------------------------------------------------------------------------
# Niche-specific hook guidance
# ---------------------------------------------------------------------------

NICHE_HOOK_GUIDANCE: dict[str, dict] = {
    "skincare": {
        "name_vi": "Skincare / Làm đẹp",
        "top_hooks": ["boc_phot", "phan_ung", "so_sanh", "canh_bao"],
        "signature_phrases": [
            "Đây là những món skincare tui chấm 10/10 nhưng trên thị trường rất flop",
            "5 lý do khiến cho mọi người skincare mà da vẫn không hết được mụn",
            "Mình đã dùng qua 5 loại, đều thất vọng vì...",
        ],
        "visual_notes": "GRWM format + cận da mặt. Ánh sáng tự nhiên. Show kết quả trên da thật.",
    },
    "review_do_gia_dung": {
        "name_vi": "Review đồ gia dụng / Đồ bếp",
        "top_hooks": ["gia_soc", "canh_bao", "phan_ung", "so_sanh"],
        "signature_phrases": [
            "Mua về dùng thử và bất ngờ...",
            "Đồ bếp dưới 100K mà xài cực đã",
            "ĐỪNG MUA đồ bếp nếu chưa xem video này",
        ],
        "visual_notes": "Cầm sản phẩm demo trực tiếp. Cận tay thao tác. B-roll sản phẩm đang hoạt động.",
    },
    "thoi_trang": {
        "name_vi": "Thời trang",
        "top_hooks": ["pov", "so_sanh", "gia_soc", "phan_ung"],
        "signature_phrases": [
            "Biến hình từ đồ ở nhà → outfit đi chơi chỉ trong 5 giây",
            "Outfit công sở dưới 300K — mua ở Shopee",
            "Shopee haul thời trang — món nào mặc được, món nào trả",
        ],
        "visual_notes": "Transition outfit change trong 3s đầu. Quay full body + cận chi tiết.",
    },
    "nau_an": {
        "name_vi": "Nấu ăn / Món ăn",
        "top_hooks": ["huong_dan", "phan_ung", "ke_chuyen"],
        "signature_phrases": [
            "Show thành phẩm trước → quay lại từ đầu",
            "Mẹ tôi dạy tôi cách làm [món] và nó đã thay đổi cuộc chơi",
            "Nấu ăn 3 phút cho sinh viên",
        ],
        "visual_notes": "Thành phẩm ở frame đầu (sensory hook). Cận tay nấu. #NauAn3Phut trending.",
    },
    "tech": {
        "name_vi": "Công nghệ / Đồ điện tử",
        "top_hooks": ["canh_bao", "so_sanh", "boc_phot", "gia_soc"],
        "signature_phrases": [
            "iPhone giá 3 triệu — hàng thật hay hàng giả?",
            "ĐỪNG MUA tai nghe nếu chưa biết điều này",
            "So sánh [A] vs [B] — cái nào đáng tiền?",
        ],
        "visual_notes": "Unbox close-up + spec text overlay. So sánh side-by-side trên bàn.",
    },
    "giao_duc": {
        "name_vi": "Giáo dục / Học tập",
        "top_hooks": ["bang_chung", "boc_phot", "huong_dan", "canh_bao"],
        "signature_phrases": [
            "99% người không biết công cụ này",
            "Sai lầm khiến 90% người học content không bao giờ tiến bộ",
            "Điều mà 4 năm đại học không dạy bạn",
        ],
        "visual_notes": "Text overlay số liệu lớn. Nói chuyện trực tiếp camera. Tone tự tin.",
    },
    "tai_chinh": {
        "name_vi": "Tài chính / Kiếm tiền",
        "top_hooks": ["ke_chuyen", "bang_chung", "canh_bao", "boc_phot"],
        "signature_phrases": [
            "Hồi mới làm content, mình từng tiêu 30 triệu mà không ra đơn nào",
            "Thu nhập tháng này: [số] triệu — làm gì mà nhiều vậy?",
            "Sai lầm tài chính khiến bạn mãi không giàu",
        ],
        "visual_notes": "Screenshot thu nhập (thật). Nói chuyện casual, không studio.",
    },
    "shopee_affiliate": {
        "name_vi": "Shopee Affiliate / Tiếp thị liên kết",
        "top_hooks": ["gia_soc", "phan_ung", "ke_chuyen", "bang_chung"],
        "signature_phrases": [
            "Haul Shopee dưới 200K — dùng thật rồi mới review",
            "Trước 3 đơn/ngày, sau 21 đơn/ngày, chỉ vì thay đổi 1 dòng",
            "Cách mình kiếm [số] triệu/tháng từ Shopee Affiliate",
        ],
        "visual_notes": "Mở hộp hàng loạt. Cận sản phẩm + giá. CTA giỏ hàng vàng cuối video.",
    },
}

# ---------------------------------------------------------------------------
# Video structure — 5-phase commerce formula
# ---------------------------------------------------------------------------

COMMERCE_VIDEO_STRUCTURE = [
    {"phase": 1, "name_vi": "Hook", "time": "0-3s", "description": "Câu hook + mặt/text overlay. Quyết định video sống hay chết."},
    {"phase": 2, "name_vi": "Giới thiệu sản phẩm", "time": "3-10s", "description": "Show sản phẩm + giá + USP chính. Cầm sản phẩm lên hoặc unbox."},
    {"phase": 3, "name_vi": "Demo/Lợi ích", "time": "10-40s", "description": "Demo trực tiếp hoặc kể trải nghiệm. Nếu skincare: show kết quả trên da."},
    {"phase": 4, "name_vi": "Social proof", "time": "optional", "description": "Screenshot review, số đơn đã bán, hoặc feedback khách hàng."},
    {"phase": 5, "name_vi": "CTA", "time": "cuối 5-10s", "description": 'Hướng dẫn mua: "link ở bio" / "bấm giỏ hàng vàng" + nhắc lại giá sale.'},
]

# ---------------------------------------------------------------------------
# 3-second rule — hook effectiveness framework
# ---------------------------------------------------------------------------

HOOK_EFFECTIVENESS = {
    "rule": "First 3 seconds determine algorithmic distribution. Videos with 3s retention >65% get 4-7x more impressions.",
    "principles": [
        'Negative framing outperforms positive: "Cơ thể bạn sẽ hỏng dần..." > "Trong video này chúng tôi sẽ nói về..."',
        "Text overlay trong 0.5s đầu — Vietnamese users respond strongly to text hooks",
        "Mở bằng mặt (face in first frame) — 92% top videos in most niches show face within 0.5s",
        "Show kết quả trước, hướng dẫn sau — đặc biệt với tutorial và before/after",
        'Bỏ lửng (...) buộc xem tiếp — "Mua về dùng thử và..." hiệu quả hơn "Mua về dùng thử rất tốt"',
    ],
    "metrics": {
        "retention_3s_good": 0.65,
        "retention_3s_great": 0.80,
        "completion_rate_good": 0.30,
        "save_rate_high": 0.02,
    },
}

# ---------------------------------------------------------------------------
# Creator terminology — Vietnamese ↔ English mapping
# ---------------------------------------------------------------------------

CREATOR_TERMS = {
    "performance": {
        "chạy": "video/content đang có nhiều views, engagement tốt",
        "flop": "video ít views, không được algorithm đẩy",
        "lên xu hướng": "getting on trending/FYP",
        "lên FYP": "getting on For You Page",
        "bóp reach": "algorithm suppression / shadowban",
        "bóp tương tác": "engagement suppression",
    },
    "influencer_tiers": {
        "KOL": "Key Opinion Leader — macro influencer, chuyên gia",
        "KOC": "Key Opinion Consumer — micro influencer, review như người tiêu dùng thật (<50K followers)",
        "KOS": "Key Opinion Sales — chuyên gia livestream bán hàng, chốt đơn",
    },
    "commerce": {
        "chốt đơn": "finalize/close an order (critical livestream action)",
        "ra đơn": "generate orders / get sales",
        "hoa hồng": "commission",
        "giỏ hàng vàng": "TikTok Shop yellow cart icon (product tag)",
        "giỏ hàng cam": "Shopee orange cart",
        "seeding": "planting promotional comments (English loanword)",
        "freeship": "free shipping (English loanword, dominant form)",
    },
    "english_loanwords": [
        "hook", "content", "viral", "trend", "brief", "format", "niche",
        "view", "follower", "like", "share", "comment", "creator",
        "haul", "unbox", "GRWM", "POV", "CTA", "flash sale",
        "livestream", "filter", "effect", "edit", "caption", "hashtag",
        "KOL", "KOC", "KOS", "freeship", "seeding",
    ],
    "slang": {
        "đỉnh": "awesome / top-tier (also: đỉnh khoai)",
        "toang": "collapsed / went wrong",
        "sống ảo": "staging life for social media",
        "+1 máy": "expressing agreement (biggest slang trend 2025)",
        "bảnh": "cool / stylish (Gen Z)",
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_top_hooks_for_niche(niche_key: str) -> list[str]:
    """Returns top hook category keys for a niche. Falls back to safe defaults."""
    return NICHE_HOOK_GUIDANCE.get(niche_key, {}).get(
        "top_hooks", ["canh_bao", "phan_ung", "huong_dan"]
    )


def get_hook_name_vi(category_key: str) -> str:
    return HOOK_CATEGORIES.get(category_key, {}).get("name_vi", category_key)


def build_hook_vocabulary_block() -> str:
    """Compact hook taxonomy block for injection into Gemini system prompt.

    Format: one paragraph per hook — name, mechanism, 1 template example.
    Kept short so it doesn't bloat token count on every call.
    """
    lines: list[str] = ["HOOK TAXONOMY (9 loại hook Vietnamese TikTok):"]
    for key, h in HOOK_CATEGORIES.items():
        template_ex = h["templates"][0] if h["templates"] else ""
        lines.append(
            f'• {h["name_vi"]} ({key}): {h["mechanism_vi"]} | VD: "{template_ex}"'
        )
    return "\n".join(lines)


def build_niche_hook_block(niche_key: str) -> str:
    """Per-niche hook guidance block — injected into brief_generation and video_diagnosis.

    Returns empty string if niche_key not found.
    """
    guidance = NICHE_HOOK_GUIDANCE.get(niche_key)
    if not guidance:
        return ""
    top = ", ".join(
        f'{get_hook_name_vi(k)} ({k})' for k in guidance["top_hooks"]
    )
    phrases = "\n".join(f'  – "{p}"' for p in guidance["signature_phrases"])
    return (
        f'NICHE HOOK GUIDANCE ({guidance["name_vi"]}):\n'
        f"Top hooks: {top}\n"
        f"Signature phrases:\n{phrases}\n"
        f'Visual notes: {guidance["visual_notes"]}'
    )


def build_commerce_structure_block() -> str:
    """5-phase commerce formula — injected into brief_generation intent."""
    lines = ["VIDEO STRUCTURE (5-phase commerce formula):"]
    for p in COMMERCE_VIDEO_STRUCTURE:
        lines.append(f'  Phase {p["phase"]} [{p["time"]}] {p["name_vi"]}: {p["description"]}')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shopee-specific hook formulas (P0-3) — affiliate/commerce creator staples
# ---------------------------------------------------------------------------

SHOPEE_HOOK_FORMULAS: list[str] = [
    "Shopee sale [ngày] — [số] món đồ đáng mua nhất",
    "[Sản phẩm] Shopee mall [giá] — rẻ hơn cửa hàng [số]K",
    "Haul Shopee dưới [giá] — món nào dùng được, món nào vứt",
    "Mã giảm giá Shopee hôm nay — tiết kiệm [số]K",
    "[Số] món đồ Shopee dưới 50K mà dùng mãi không hết",
]


def build_hook_formula_instruction() -> str:
    """P0-3: Hook formula instruction block for synthesis system prompt.

    Tells Gemini to always output hooks as fill-in-the-blank Vietnamese templates.
    Includes the 8 structural patterns + 5 Shopee-specific formulas.
    Injected into the _STRATEGIST_CONTEXT once at module load.
    """
    # Build compact formula list: name + first template
    formula_lines: list[str] = []
    for key, h in HOOK_CATEGORIES.items():
        tpl = h["templates"][0] if h["templates"] else ""
        formula_lines.append(f'  {h["name_vi"]}: "{tpl}"')

    shopee_lines = "\n".join(f'  "{t}"' for t in SHOPEE_HOOK_FORMULAS)

    return f"""QUY TẮC HOOK FORMULA (P0-3):
Khi đề xuất hook, LUÔN viết dưới dạng template copy-paste được.
Dùng [ngoặc vuông] cho phần thay thế — LUÔN bằng tiếng Việt.

✅ Đúng: "ĐỪNG [hành động] nếu chưa xem video này"
✅ Đúng: "[Sản phẩm] chỉ [giá] — mua ở đâu?"
❌ Sai:  "ĐỪNG [action] nếu chưa xem" — không dùng placeholder tiếng Anh

Không bao giờ chỉ nói "nên cải thiện hook" mà không đưa ra template cụ thể.
Mỗi hook đề xuất phải bắt đầu bằng "Hook:" và là một dòng riêng.

8 template hook phổ biến nhất:
{chr(10).join(formula_lines)}

5 template Shopee dành cho affiliate/commerce content:
{shopee_lines}"""
