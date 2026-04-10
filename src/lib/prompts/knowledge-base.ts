/**
 * GetViews Vietnamese TikTok Hook Knowledge Base
 * ================================================
 * Source: Research report — Vietnamese TikTok Hook Formulas (April 2026)
 * Location: src/lib/prompts/knowledge-base.ts
 *
 * PURPOSE
 * -------
 * This file is STATIC structural knowledge — hook categories, templates, niche guidance,
 * creator terminology, and video structure formulas. It does not change week-to-week.
 *
 * The DYNAMIC layer (which hooks are performing right now, in this niche, this week)
 * comes from video_corpus at runtime via the synthesis pipeline.
 *
 * USAGE PATTERN
 * -------------
 * Synthesis prompt combines both:
 *   Static:  "Cảnh Báo hook — template: 'ĐỪNG [hành động]...', mechanism: tạo FOMO"
 *   Dynamic: "Based on 412 videos this month, Cảnh Báo is the #1 hook in skincare (38%)"
 *   Output:  Gemini writes a brief with the correct template + real performance data.
 *
 * CONSUMERS
 * ---------
 *   - Gemini synthesis prompts (pipelines.py calls Edge Function, which references this)
 *   - Hook diagnosis (P0-5 intent)
 *   - Brief generation (P0-3 intent)
 *   - Niche intelligence context injection
 */

// ============================================================
// HOOK CATEGORIES — 9 categories, Vietnamese-native labels
// ============================================================

export const HOOK_CATEGORIES = {
  canh_bao: {
    name_vi: 'Cảnh Báo',
    name_en: 'warning',
    description: 'Cảnh báo người xem đừng làm gì đó — tạo FOMO + tò mò',
    templates: [
      'ĐỪNG [hành động] nếu chưa xem video này',
      'Sai lầm này khiến mình mất [thời gian] làm content không hiệu quả',
      'ĐỪNG [mua/dùng] [sản phẩm] — lý do ở cuối video',
      'Sai lầm khi [hành động] khiến bạn mất [hậu quả] mà không biết',
    ],
    mechanism_vi: 'Chạy vì: tạo cảm giác sợ bỏ lỡ, người xem phải xem hết để biết lý do',
    best_niches: ['skincare', 'review_do_gia_dung', 'tech', 'tai_chinh'],
    visual_pairing: 'Mở bằng mặt nghiêm túc nhìn camera + text overlay lớn trong 0.5s đầu',
  },

  gia_soc: {
    name_vi: 'Giá Sốc',
    name_en: 'price_shock',
    description: 'Mở bằng giá bất ngờ — rẻ hơn kỳ vọng hoặc đắt hơn tưởng',
    templates: [
      '[Sản phẩm] chỉ [giá] — mua ở đâu?',
      'Bạn có tin chỉ với [giá] bạn có thể [kết quả]?',
      '[Số] món đồ Shopee dưới [giá] mà dùng mãi không hết',
      '[Sản phẩm] Shopee mall [giá] — rẻ hơn cửa hàng [số]K',
    ],
    mechanism_vi: 'Chạy vì: giá bất ngờ tạo phản ứng "thật hả?" → xem tiếp để xác nhận',
    best_niches: ['review_do_gia_dung', 'thoi_trang', 'do_dien_tu', 'shopee_haul'],
    visual_pairing: 'Text giá lớn + highlight màu đỏ/vàng trong frame đầu',
  },

  phan_ung: {
    name_vi: 'Phản Ứng',
    name_en: 'reaction',
    description: 'Dùng thử sản phẩm và phản ứng chân thật — tạo tò mò muốn biết kết quả',
    templates: [
      'Mua [sản phẩm] về dùng thử và...',
      'Thử [sản phẩm] 7 ngày — kết quả bất ngờ',
      'Mình mua [sản phẩm] viral và đây là sự thật...',
      'Trước và sau khi dùng [sản phẩm] [thời gian]',
    ],
    mechanism_vi: 'Chạy vì: kết quả bỏ lửng ("và...") buộc xem đến cuối. Chân thật hơn quảng cáo.',
    best_niches: ['skincare', 'review_do_gia_dung', 'thuc_pham', 'my_pham'],
    visual_pairing: 'B-roll mở hộp + cận mặt phản ứng. Kết quả reveal ở giữa video.',
  },

  so_sanh: {
    name_vi: 'So Sánh',
    name_en: 'comparison',
    description: 'Đặt 2 sản phẩm/cách làm cạnh nhau — người xem muốn biết cái nào hơn',
    templates: [
      '[Sản phẩm A] vs [Sản phẩm B] — cái nào đáng tiền hơn?',
      'So sánh [A] giá [giá A] và [B] giá [giá B] — khác biệt ở đâu?',
      '[Sản phẩm] Shopee vs [sản phẩm] chính hãng — có khác gì?',
      'Xử lý vấn đề [A] có thực sự khó như lời đồn?',
    ],
    mechanism_vi: 'Chạy vì: ai cũng muốn biết cái nào tốt hơn. Comment tranh luận → algorithm đẩy.',
    best_niches: ['skincare', 'tech', 'thoi_trang', 'do_dien_tu'],
    visual_pairing: 'Split screen hoặc 2 sản phẩm cạnh nhau. Text so sánh 2 cột.',
  },

  boc_phot: {
    name_vi: 'Bóc Phốt',
    name_en: 'expose',
    description: 'Vạch trần sự thật — tạo cảm giác "mình biết điều người khác không biết"',
    templates: [
      'Sự thật về [sản phẩm/trend] mà không ai nói cho bạn',
      '[Sản phẩm] quảng cáo "thần thánh" — sự thật đằng sau',
      'Điều mà [X] năm học [lĩnh vực] không dạy bạn',
      'Vì sao [sản phẩm viral] không đáng mua — review thật',
    ],
    mechanism_vi: 'Chạy vì: người xem cảm giác được biết "inside info". Comment chia phe → engagement cao.',
    best_niches: ['skincare', 'giao_duc', 'tai_chinh', 'review_do_gia_dung'],
    visual_pairing: 'Mặt nghiêm túc + text "SỰ THẬT" overlay. Tone giọng tự tin, không thì thầm.',
  },

  huong_dan: {
    name_vi: 'Hướng Dẫn',
    name_en: 'tutorial',
    description: 'Dạy cách làm gì đó nhanh gọn — mở bằng kết quả hoặc con số',
    templates: [
      'Cách [hành động] trong [thời gian] — ai cũng làm được',
      'Mẹo [topic] mà 99% không biết',
      '[Số] bước đơn giản để [kết quả]',
      'Tool này giúp mình [kết quả] mà không cần [nỗ lực]',
    ],
    mechanism_vi: 'Chạy vì: hứa hẹn kết quả cụ thể + thời gian ngắn. Save rate cao → algorithm ưu tiên.',
    best_niches: ['giao_duc', 'tech', 'skincare', 'nau_an', 'tai_chinh'],
    visual_pairing: 'Show kết quả trước (3s đầu) → quay lại hướng dẫn từ đầu',
  },

  ke_chuyen: {
    name_vi: 'Kể Chuyện',
    name_en: 'story',
    description: 'Mở bằng câu chuyện cá nhân — tạo kết nối cảm xúc trước khi bán hàng',
    templates: [
      'Hôm qua mình [sự việc] và [kết quả bất ngờ]',
      'Mình từng suýt [từ bỏ], cho đến khi...',
      '1 năm trước mình vẫn chưa biết [lĩnh vực] là gì...',
      'Một bạn học viên từng [kết quả] chỉ nhờ [hành động đơn giản]',
    ],
    mechanism_vi: 'Chạy vì: não bộ phản ứng với câu chuyện mạnh hơn số liệu. Tạo trust trước khi bán.',
    best_niches: ['tai_chinh', 'giao_duc', 'skincare', 'shopee_affiliate'],
    visual_pairing: 'Nói chuyện trực tiếp với camera, casual (ngồi xe, đi bộ, uống cà phê). Không studio.',
  },

  pov: {
    name_vi: 'POV',
    name_en: 'pov',
    description: 'Đặt người xem vào một tình huống — đặc trưng văn hoá Việt',
    templates: [
      'POV: bạn là [nhân vật] và [tình huống]',
      'POV: ba mẹ hỏi điểm thi',
      'POV: bạn vừa tìm được [giải pháp] cho [vấn đề]',
      'POV: bà ngoại ép ăn thêm cơm',
    ],
    mechanism_vi: 'Chạy vì: người xem tưởng tượng mình trong tình huống → watch time cao. Vietnamese-specific POV chạy tốt hơn POV quốc tế.',
    best_niches: ['giai_tri', 'giao_duc', 'thoi_trang', 'skincare'],
    visual_pairing: 'Camera đặt ngang mặt. Acting tự nhiên. Text overlay mô tả tình huống.',
  },

  bang_chung: {
    name_vi: 'Bằng Chứng',
    name_en: 'social_proof',
    description: 'Mở bằng con số kết quả thật — tạo uy tín ngay 3 giây đầu',
    templates: [
      'Trước: [số] đơn/ngày. Sau: [số] đơn/ngày, chỉ vì thay đổi đúng 1 [điều]',
      'Tụi mình đã tăng [số] lượt tiếp cận chỉ bằng cách [hành động đơn giản]',
      'Content bạn flop không phải do thuật toán, mà do bạn sai ngay từ [phần]',
      '[Số]% người [hành động] mà quên bước này',
    ],
    mechanism_vi: 'Chạy vì: số liệu cụ thể tạo uy tín ngay lập tức. "Trước/Sau" format chạy đặc biệt tốt.',
    best_niches: ['giao_duc', 'tai_chinh', 'marketing', 'shopee_affiliate'],
    visual_pairing: 'Text overlay số liệu lớn, JetBrains Mono style. Screenshot kết quả thật.',
  },
} as const;

export type HookCategory = keyof typeof HOOK_CATEGORIES;

// ============================================================
// SHOPEE AFFILIATE HOOKS — commerce-specific templates
// ============================================================

export const SHOPEE_HOOKS = {
  sale_event: {
    name_vi: 'Sale Event',
    templates: [
      'Shopee sale [ngày] — [số] món đồ đáng mua nhất',
      'Flash sale hôm nay: [sản phẩm] giảm [phần trăm]%',
      'Shopee [ngày.ngày] — mình mua gì và có đáng không?',
    ],
  },
  price_anchor: {
    name_vi: 'Neo Giá',
    templates: [
      '[Sản phẩm] Shopee mall [giá sale] — giá gốc [giá gốc]',
      'Haul Shopee dưới [giá] — món nào dùng được, món nào vứt',
      'Mã giảm giá Shopee hôm nay — tiết kiệm [số]K',
    ],
  },
  trust_signal: {
    name_vi: 'Tín Hiệu Tin Cậy',
    templates: [
      'Shopee Mall chính hãng [giá] — rẻ hơn cửa hàng [số]K',
      'Review thật: [sản phẩm] Shopee — có đáng tiền không?',
      'Mình đã dùng [sản phẩm] [thời gian], đây là review thật',
    ],
  },
  cta_phrases: [
    'Link ở bio',
    'Link mua mình gắn ở Bio',
    'Nhấn vào giỏ hàng màu vàng',
    'Bấm giỏ hàng màu cam để mua',
    'Mã giảm giá trong comment',
    'Link sản phẩm ở comment',
  ],
  hashtags: [
    '#tiepthilienket', '#affiliatetiktok', '#tiktokshopvn',
    '#muasamcungtiktok', '#reviewdoshopee', '#haulshopee',
    '#chotdon', '#koc', '#shopeemall',
  ],
} as const;

// ============================================================
// TIKTOK SHOP COMMERCE HOOKS — urgency + trust vocabulary
// ============================================================

export const TIKTOK_SHOP_HOOKS = {
  urgency: [
    'Flash sale',
    'Giảm sốc [phần trăm]%',
    'Chỉ hôm nay',
    'Số lượng có hạn',
    'Bên em chỉ đi [số] đơn cuối',
    'Hết live là hết ưu đãi này nha mọi người',
    'Giảm sâu đến [phần trăm]%',
  ],
  price_anchor: [
    'Giá gốc [giá gốc], giá sale [giá sale]',
    'Giá niêm yết [giá], giá trong live chỉ [giá live]',
    'Rẻ hơn ngoài cửa hàng [số]K',
  ],
  trust: [
    'Shopee Mall chính hãng',
    'Hàng chính hãng 100%',
    'Cam kết hàng thật giá thật',
    'Review thật — không seeding',
  ],
  shipping: [
    'Freeship',
    'Miễn phí vận chuyển',
    'Mã freeship',
    'Freeship toàn quốc',
  ],
} as const;

// ============================================================
// VIDEO STRUCTURE — 5-phase commerce formula
// ============================================================

export const COMMERCE_VIDEO_STRUCTURE = {
  phases: [
    { phase: 1, name_vi: 'Hook', time: '0-3s', description: 'Câu hook + mặt/text overlay. Quyết định video sống hay chết.' },
    { phase: 2, name_vi: 'Giới thiệu sản phẩm', time: '3-10s', description: 'Show sản phẩm + giá + USP chính. Cầm sản phẩm lên hoặc unbox.' },
    { phase: 3, name_vi: 'Demo/Lợi ích', time: '10-40s', description: 'Demo trực tiếp hoặc kể trải nghiệm. Nếu skincare: show kết quả trên da.' },
    { phase: 4, name_vi: 'Social proof', time: 'optional', description: 'Screenshot review, số đơn đã bán, hoặc feedback khách hàng.' },
    { phase: 5, name_vi: 'CTA', time: 'cuối 5-10s', description: 'Hướng dẫn mua: "link ở bio" / "bấm giỏ hàng vàng" + nhắc lại giá sale.' },
  ],
  formats: [
    { format: 'review', name_vi: 'Review sản phẩm', hook_pairing: ['phan_ung', 'boc_phot', 'so_sanh'] },
    { format: 'haul', name_vi: 'Haul/Mở hộp', hook_pairing: ['gia_soc', 'phan_ung'] },
    { format: 'comparison', name_vi: 'So sánh', hook_pairing: ['so_sanh', 'boc_phot'] },
    { format: 'tutorial', name_vi: 'Hướng dẫn', hook_pairing: ['huong_dan', 'bang_chung'] },
    { format: 'before_after', name_vi: 'Trước/Sau', hook_pairing: ['phan_ung', 'bang_chung'] },
    { format: 'story_hack', name_vi: 'Kể chuyện + mẹo', hook_pairing: ['ke_chuyen', 'huong_dan'] },
    { format: 'grwm', name_vi: 'GRWM', hook_pairing: ['ke_chuyen', 'pov'] },
    { format: 'faceless', name_vi: 'Không mặt (tay + voice)', hook_pairing: ['huong_dan', 'gia_soc'] },
  ],
} as const;

// ============================================================
// NICHE-SPECIFIC HOOK GUIDANCE
// ============================================================

export const NICHE_HOOK_GUIDANCE: Record<string, {
  name_vi: string;
  top_hooks: HookCategory[];
  signature_phrases: string[];
  visual_notes: string;
}> = {
  skincare: {
    name_vi: 'Skincare / Làm đẹp',
    top_hooks: ['boc_phot', 'phan_ung', 'so_sanh', 'canh_bao'],
    signature_phrases: [
      'Đây là những món skincare tui chấm 10/10 nhưng trên thị trường rất flop',
      '5 lý do khiến cho mọi người skincare mà da vẫn không hết được mụn',
      'Mình đã dùng qua 5 loại, đều thất vọng vì...',
    ],
    visual_notes: 'GRWM format + cận da mặt. Ánh sáng tự nhiên. Show kết quả trên da thật.',
  },
  review_do_gia_dung: {
    name_vi: 'Review đồ gia dụng / Đồ bếp',
    top_hooks: ['gia_soc', 'canh_bao', 'phan_ung', 'so_sanh'],
    signature_phrases: [
      'Mua về dùng thử và bất ngờ...',
      'Đồ bếp dưới 100K mà xài cực đã',
      'ĐỪNG MUA đồ bếp nếu chưa xem video này',
    ],
    visual_notes: 'Cầm sản phẩm demo trực tiếp. Cận tay thao tác. B-roll sản phẩm đang hoạt động.',
  },
  thoi_trang: {
    name_vi: 'Thời trang',
    top_hooks: ['pov', 'so_sanh', 'gia_soc', 'phan_ung'],
    signature_phrases: [
      'Biến hình từ đồ ở nhà → outfit đi chơi chỉ trong 5 giây',
      'Outfit công sở dưới 300K — mua ở Shopee',
      'Shopee haul thời trang — món nào mặc được, món nào trả',
    ],
    visual_notes: 'Transition outfit change trong 3s đầu. Quay full body + cận chi tiết.',
  },
  nau_an: {
    name_vi: 'Nấu ăn / Món ăn',
    top_hooks: ['huong_dan', 'phan_ung', 'ke_chuyen'],
    signature_phrases: [
      'Show thành phẩm trước → quay lại từ đầu',
      'Mẹ tôi dạy tôi cách làm [món] và nó đã thay đổi cuộc chơi',
      'Nấu ăn 3 phút cho sinh viên',
    ],
    visual_notes: 'Thành phẩm ở frame đầu (sensory hook). Cận tay nấu. #NauAn3Phut trending.',
  },
  tech: {
    name_vi: 'Công nghệ / Đồ điện tử',
    top_hooks: ['canh_bao', 'so_sanh', 'boc_phot', 'gia_soc'],
    signature_phrases: [
      'iPhone giá 3 triệu — hàng thật hay hàng giả?',
      'ĐỪNG MUA tai nghe nếu chưa biết điều này',
      'So sánh [A] vs [B] — cái nào đáng tiền?',
    ],
    visual_notes: 'Unbox close-up + spec text overlay. So sánh side-by-side trên bàn.',
  },
  giao_duc: {
    name_vi: 'Giáo dục / Học tập',
    top_hooks: ['bang_chung', 'boc_phot', 'huong_dan', 'canh_bao'],
    signature_phrases: [
      '99% người không biết công cụ này',
      'Sai lầm khiến 90% người học content không bao giờ tiến bộ',
      'Điều mà 4 năm đại học không dạy bạn',
    ],
    visual_notes: 'Text overlay số liệu lớn. Nói chuyện trực tiếp camera. Tone tự tin.',
  },
  tai_chinh: {
    name_vi: 'Tài chính / Kiếm tiền',
    top_hooks: ['ke_chuyen', 'bang_chung', 'canh_bao', 'boc_phot'],
    signature_phrases: [
      'Hồi mới làm content, mình từng tiêu 30 triệu mà không ra đơn nào',
      'Thu nhập tháng này: [số] triệu — làm gì mà nhiều vậy?',
      'Sai lầm tài chính khiến bạn mãi không giàu',
    ],
    visual_notes: 'Screenshot thu nhập (thật). Nói chuyện casual, không studio.',
  },
  shopee_affiliate: {
    name_vi: 'Shopee Affiliate / Tiếp thị liên kết',
    top_hooks: ['gia_soc', 'phan_ung', 'ke_chuyen', 'bang_chung'],
    signature_phrases: [
      'Haul Shopee dưới 200K — dùng thật rồi mới review',
      'Trước 3 đơn/ngày, sau 21 đơn/ngày, chỉ vì thay đổi 1 dòng',
      'Cách mình kiếm [số] triệu/tháng từ Shopee Affiliate',
    ],
    visual_notes: 'Mở hộp hàng loạt. Cận sản phẩm + giá. CTA giỏ hàng vàng cuối video.',
  },
};

// ============================================================
// CREATOR TERMINOLOGY — Vietnamese ↔ English mapping
// ============================================================

export const CREATOR_TERMS = {
  // Performance terms
  performance: {
    'chạy': 'video/content đang có nhiều views, engagement tốt',
    'flop': 'video ít views, không được algorithm đẩy',
    'lên xu hướng': 'getting on trending/FYP',
    'lên FYP': 'getting on For You Page',
    'viral': 'used as-is (English loanword)',
    'bóp reach': 'algorithm suppression / shadowban',
    'bóp tương tác': 'engagement suppression',
  },
  // Influencer tiers (Vietnamese-specific taxonomy)
  influencer_tiers: {
    'KOL': 'Key Opinion Leader — macro influencer, chuyên gia',
    'KOC': 'Key Opinion Consumer — micro influencer, review như người tiêu dùng thật (<50K followers)',
    'KOS': 'Key Opinion Sales — chuyên gia livestream bán hàng, chốt đơn',
  },
  // Commerce terms
  commerce: {
    'chốt đơn': 'finalize/close an order (critical livestream action)',
    'ra đơn': 'generate orders / get sales',
    'hoa hồng': 'commission',
    'giỏ hàng vàng': 'TikTok Shop yellow cart icon (product tag)',
    'giỏ hàng cam': 'Shopee orange cart',
    'seeding': 'planting promotional comments (English loanword)',
    'freeship': 'free shipping (English loanword, dominant form)',
  },
  // English loanwords used as-is (do NOT translate these)
  english_loanwords: [
    'hook', 'content', 'viral', 'trend', 'brief', 'format', 'niche',
    'view', 'follower', 'like', 'share', 'comment', 'creator',
    'haul', 'unbox', 'GRWM', 'POV', 'CTA', 'flash sale',
    'livestream', 'filter', 'effect', 'edit', 'caption', 'hashtag',
    'KOL', 'KOC', 'KOS', 'freeship', 'seeding',
  ],
  // Vietnamese slang (2025-2026)
  slang: {
    'đỉnh': 'awesome / top-tier (also: "đỉnh khoai")',
    'toang': 'collapsed / went wrong',
    'sống ảo': 'staging life for social media',
    'ăn hành': 'getting trolled',
    '+1 máy': 'expressing agreement (biggest slang trend 2025)',
    'bảnh': 'cool / stylish (Gen Z)',
  },
} as const;

// ============================================================
// 3-SECOND RULE — hook effectiveness framework
// ============================================================

export const HOOK_EFFECTIVENESS = {
  rule: 'First 3 seconds determine algorithmic distribution. Videos with 3s retention >65% get 4-7x more impressions.',
  principles: [
    'Negative framing outperforms positive: "Cơ thể bạn sẽ hỏng dần..." > "Trong video này chúng tôi sẽ nói về..."',
    'Text overlay trong 0.5s đầu — Vietnamese users respond strongly to text hooks',
    'Mở bằng mặt (face in first frame) — 92% top videos in most niches show face within 0.5s',
    'Show kết quả trước, hướng dẫn sau — đặc biệt với tutorial và before/after',
    'Bỏ lửng (...) buộc xem tiếp — "Mua về dùng thử và..." hiệu quả hơn "Mua về dùng thử rất tốt"',
  ],
  visual_hooks: [
    'Camera shake/movement mạnh trong frame đầu',
    'Text overlay lớn (chiếm >30% frame)',
    'Mặt shock/ngạc nhiên trước khi nói',
    'Mở giữa câu (mid-sentence start)',
    'Screenshot tin nhắn / kết quả thật',
    '5 giây im lặng nhìn camera (pattern interrupt)',
  ],
  metrics: {
    retention_3s_good: 0.65,    // >65% = video will be pushed
    retention_3s_great: 0.80,   // >80% = viral potential
    completion_rate_good: 0.30, // >30% for videos >15s
    save_rate_high: 0.02,       // >2% = high value signal
  },
} as const;

// ============================================================
// SYNTHESIS PROMPT HELPERS
// ============================================================

/**
 * Returns the Vietnamese hook name for a given category key
 */
export function getHookNameVI(category: HookCategory): string {
  return HOOK_CATEGORIES[category].name_vi;
}

/**
 * Returns top hook categories for a niche
 */
export function getTopHooksForNiche(nicheKey: string): HookCategory[] {
  return NICHE_HOOK_GUIDANCE[nicheKey]?.top_hooks ?? ['canh_bao', 'phan_ung', 'huong_dan'];
}

/**
 * Returns a random template for a hook category (for brief generation)
 */
export function getRandomTemplate(category: HookCategory): string {
  const templates = HOOK_CATEGORIES[category].templates;
  return templates[Math.floor(Math.random() * templates.length)];
}

/**
 * Returns the mechanism explanation for a hook category (for "Chạy vì:" blocks)
 */
export function getMechanismVI(category: HookCategory): string {
  return HOOK_CATEGORIES[category].mechanism_vi;
}

/**
 * Returns commerce video structure phases for brief generation
 */
export function getCommerceStructure() {
  return COMMERCE_VIDEO_STRUCTURE.phases;
}

/**
 * Checks if a word is an English loanword that should NOT be translated
 */
export function isEnglishLoanword(word: string): boolean {
  return CREATOR_TERMS.english_loanwords.includes(word.toLowerCase()) ||
         CREATOR_TERMS.english_loanwords.includes(word);
}
