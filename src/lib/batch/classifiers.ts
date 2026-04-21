/**
 * Corpus classification functions for video_corpus batch ingestion.
 * These run BEFORE each INSERT to populate the 30 new classification columns.
 * All functions are pure — no side effects, no I/O.
 */

// ── Types ────────────────────────────────────────────────────────────────────

export interface Analysis {
  audio_transcript?: string;
  text_overlays?: Array<{ text: string; [key: string]: unknown }>;
  hook_analysis?: {
    hook_type?: string;
    hook_phrase?: string;
    face_appears_at?: number;
    first_frame_type?: string;
    [key: string]: unknown;
  };
  scenes?: Array<{
    type?: string;
    end?: number;
    [key: string]: unknown;
  }>;
  topics?: string[];
  tone?: string;
  transitions_per_second?: number;
  cta?: string;
  [key: string]: unknown;
}

// ── Language detection ───────────────────────────────────────────────────────

/**
 * Detect language from Gemini analysis content.
 * Used as QUALITY GATE: skip non-Vietnamese videos entirely.
 */
export function detectLanguage(analysis: Analysis): 'vi' | 'en' | 'other' {
  const transcript = analysis.audio_transcript ?? '';
  const textOverlays = (analysis.text_overlays ?? []).map(t => t.text).join(' ');
  const combined = `${transcript} ${textOverlays}`;

  const vnPattern = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/gi;
  const vnMatches = (combined.match(vnPattern) ?? []).length;

  if (vnMatches > 5) return 'vi';
  if (/^[a-zA-Z\s.,!?0-9[\]()'"]+$/.test(combined.trim())) return 'en';
  return 'other';
}

// ── Hook type normalization ──────────────────────────────────────────────────

const HOOK_TYPE_ALIASES: Record<string, string> = {
  // Canonical values from models.py HookType — must all pass through unchanged
  question: 'question',
  bold_claim: 'bold_claim',
  shock_stat: 'shock_stat',
  story_open: 'story_open',
  controversy: 'controversy',
  challenge: 'challenge',
  how_to: 'how_to',
  social_proof: 'social_proof',
  curiosity_gap: 'curiosity_gap',
  pain_point: 'pain_point',
  trend_hijack: 'trend_hijack',
  none: 'none',
  other: 'other',

  // Additional canonical values from knowledge-base HOOK_CATEGORIES (Gemini also returns these)
  warning: 'warning',
  price_shock: 'price_shock',
  reaction: 'reaction',
  comparison: 'comparison',
  expose: 'expose',
  pov: 'pov',

  // Vietnamese-language aliases (from HOOK_CATEGORIES keys)
  canh_bao: 'warning',
  gia_soc: 'price_shock',
  phan_ung: 'reaction',
  so_sanh: 'comparison',
  boc_phot: 'expose',
  huong_dan: 'how_to',
  ke_chuyen: 'story_open',
  bang_chung: 'social_proof',

  // English synonyms Gemini might use
  tutorial: 'how_to',
  story: 'story_open',
  storytelling: 'story_open',
  shock: 'bold_claim',
  tips: 'how_to',
  fomo: 'warning',
  fear: 'warning',
};

export function normalizeHookType(raw: string): string {
  return HOOK_TYPE_ALIASES[raw.toLowerCase()] ?? 'other';
}

// ── Content format classification ────────────────────────────────────────────

/**
 * Classify video format from Gemini analysis.
 * Returns one of 17 values matching COMMERCE_VIDEO_STRUCTURE.formats.
 * Order matters: mukbang is checked before recipe (mukbang is a superset in food niche).
 */
export function classifyFormat(analysis: Analysis, nicheId: number): string {
  const transcript = (analysis.audio_transcript ?? '').toLowerCase();
  const topics = (analysis.topics ?? []).map(t => t.toLowerCase()).join(' ');
  const scenes = analysis.scenes ?? [];
  const tone = analysis.tone ?? '';
  const combined = `${transcript} ${topics}`;

  if (combined.match(/mukbang|ăn.*cùng|mời.*ăn|eating|asmr/)) return 'mukbang';
  if (nicheId === 4 && scenes.length >= 10 && tone === 'entertaining') return 'mukbang';

  if (combined.match(/grwm|get ready|makeup routine|morning routine|buổi sáng/)) return 'grwm';

  if (combined.match(/công thức|recipe|nấu|cách làm|nguyên liệu|ướp|xào|chiên|nướng|hấp/)) return 'recipe';

  if (combined.match(/haul|đập hộp|unbox|mở hộp|mua.*về|đặt.*gửi/)) return 'haul';

  if (combined.match(/review|chấm điểm|đánh giá|dùng thử|trải nghiệm/)) return 'review';

  if (combined.match(/cách|hướng dẫn|tutorial|mẹo|bước|step|tips/)) return 'tutorial';

  if (combined.match(/vs |so sánh|versus|cái nào|nào hơn|nào tốt/)) return 'comparison';

  if (combined.match(/kể chuyện|story|hồi đó|hồi nhỏ|ngày xưa|mình từng/)) return 'storytelling';

  if (combined.match(/trước.*sau|before.*after|biến đổi|thay đổi.*ngày|glow.?up/)) return 'before_after';

  if (/^pov[: ]/i.test(combined.trimStart())) return 'pov';

  if (combined.match(/outfit|ootd|biến hình|transition|mix đồ|phối đồ/)) return 'outfit_transition';

  if (combined.match(/vlog|daily|thường ngày|một ngày/)) return 'vlog';

  if (scenes.length > 0 && scenes.every(s => s.type === 'action') && !analysis.audio_transcript) return 'dance';

  const allProductOrDemo = scenes.length > 0 &&
    scenes.every(s => ['product_shot', 'demo', 'action'].includes(s.type ?? ''));
  const hasVoice = (analysis.audio_transcript?.length ?? 0) > 50;
  const noFace = !scenes.some(s => s.type === 'face_to_camera');
  if (allProductOrDemo && hasVoice && noFace) return 'faceless';

  return 'other';
}

// ── CTA type classification ──────────────────────────────────────────────────

/**
 * Classify Vietnamese CTA patterns.
 * Returns one of 7 values or null if no CTA.
 */
export function classifyCTA(cta: string | null | undefined): string | null {
  if (!cta) return null;
  const c = cta.toLowerCase();

  if (c.match(/lưu lại|lưu ngay|save|lưu về/)) return 'save';
  if (c.match(/theo dõi|follow|đăng ký|subscribe/)) return 'follow';
  if (c.match(/comment|bình luận|cho.*biết|chia sẻ.*bên dưới/)) return 'comment';
  if (c.match(/giỏ hàng|mua ngay|chốt đơn|đặt hàng|shop|cart/)) return 'shop_cart';
  if (c.match(/link.*bio|bio.*link|link.*comment|link.*mô tả/)) return 'link_bio';
  if (c.match(/còn tiếp|phần 2|part 2|tiếp tục|tập sau/)) return 'part2';
  if (c.match(/thử đi|thử.*xem|làm.*thử|ăn thử/)) return 'try_it';

  return 'other';
}

// ── Commerce detection ───────────────────────────────────────────────────────

/**
 * Detect if a video is commerce/affiliate content.
 * Keywords are cross-referenced with knowledge-base SHOPEE_HOOKS and TIKTOK_SHOP_HOOKS.
 */
export function detectCommerce(analysis: Analysis): boolean {
  const transcript = (analysis.audio_transcript ?? '').toLowerCase();
  const textOverlays = (analysis.text_overlays ?? []).map(t => t.text.toLowerCase()).join(' ');
  const combined = `${transcript} ${textOverlays}`;

  if (combined.match(/\d+k\b|\d+đ\b|\d+\.\d+đ|giá.*\d|giảm.*\d+%/)) return true;
  if (combined.match(/shopee|tiktok shop|lazada|link.*bio|giỏ hàng|mã giảm|voucher|freeship|affiliate/)) return true;
  if (combined.match(/mua ngay|chốt đơn|đặt hàng|mua.*ở đâu|link.*mua|bán hàng|ra đơn/)) return true;
  if (combined.match(/flash sale|sale|giảm sốc|giảm giá|khuyến mãi|ưu đãi|hết.*là.*hết/)) return true;
  if (combined.match(/giá gốc|giá sale|rẻ hơn|đáng tiền|tiết kiệm/)) return true;

  if (analysis.cta && analysis.cta.toLowerCase().match(/mua|chốt|giỏ hàng|shop|link/)) return true;

  return false;
}

// ── Dialect detection ────────────────────────────────────────────────────────

const SOUTHERN_MARKERS = [
  /\btui\b/, /\bmấy bà\b/, /\bnè\b/, /\bnha\b/, /\bhông\b/,
  /\bquá trời\b/, /\bdzậy\b/, /\bvầy\b/, /\bbiết hông\b/,
  /á(?=\s|[.,!?])/, /\btrời ơi\b/, /\bluôn á\b/,
  /\bnghen\b/, /\bhen\b/, /\bquá xá\b/,
];

const NORTHERN_MARKERS = [
  /\bmình\b/, /\bcác bạn\b/, /\bnhé\b/, /ạ(?=\s|[.,!?])/,
  /\bcực kỳ\b/, /\bthế\b/, /\bvậy à\b/, /\bbiết không\b/,
  /\bkhông ạ\b/, /\bấy\b/, /\bđấy\b/, /\bcơ\b/,
];

const CENTRAL_MARKERS = [
  /\bchi\b/, /\bmô\b(?=\s)/, /\bni\b/, /\brứa\b/, /\brăng\b/,
];

/**
 * Detect Southern vs Northern Vietnamese dialect.
 * Requires ≥2 markers to classify. Returns null for short/no-speech content.
 */
export function detectDialect(
  transcript: string,
): 'southern' | 'northern' | 'central' | 'mixed' | null {
  if (!transcript || transcript.length < 20) return null;

  const t = transcript.toLowerCase();

  const southScore = SOUTHERN_MARKERS.filter(r => r.test(t)).length;
  const northScore = NORTHERN_MARKERS.filter(r => r.test(t)).length;
  const centralScore = CENTRAL_MARKERS.filter(r => r.test(t)).length;

  const maxScore = Math.max(southScore, northScore, centralScore);
  if (maxScore < 2) return null;

  if (centralScore >= 3) return 'central';
  if (southScore > northScore * 1.5) return 'southern';
  if (northScore > southScore * 1.5) return 'northern';
  if (southScore >= 2 && northScore >= 2) return 'mixed';

  return southScore > northScore ? 'southern' : 'northern';
}

// ── Handle normalization ─────────────────────────────────────────────────────

/**
 * Normalize TikTok handle: strip @ prefix, lowercase, trim.
 */
export function normalizeHandle(handle: string): string {
  return handle.replace(/^@/, '').toLowerCase().trim();
}
