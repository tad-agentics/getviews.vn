/** Carousel enum labels — aligned with ``cloud-run/getviews_pipeline/models.py`` + prompts. */

export const SWIPE_ANCHOR_VI: Record<string, string> = {
  cliffhanger_image: "Ảnh gây tò mò",
  incomplete_text: "Chữ chưa đủ — buộc lướt",
  numbered_progression: "Đếm bước / số thứ tự",
  curiosity_question: "Câu hỏi mở",
  none: "Không rõ",
};

export const SWIPE_TRIGGER_VI: Record<string, string> = {
  list_momentum: "Đà danh sách",
  curiosity_chain: "Chuỗi tò mò",
  narrative_tension: "Căng kể chuyện",
  none: "Không rõ",
};

export const CONTENT_ARC_VI: Record<string, string> = {
  list: "Danh sách",
  story: "Kể chuyện",
  before_after: "Trước / sau",
  comparison: "So sánh",
  tutorial_steps: "Hướng dẫn từng bước",
  gallery: "Gallery",
  narrative: "Narrative",
};

export const VISUAL_CONSISTENCY_VI: Record<string, string> = {
  consistent: "Đồng nhất",
  mixed: "Lẫn lộn",
  inconsistent: "Không đồng nhất",
};

export const SLIDE_LAYOUT_VI: Record<string, string> = {
  single_image: "Một ảnh",
  split_screen: "Chia đôi",
  text_only: "Chỉ chữ",
  photo_with_caption: "Ảnh + caption",
  infographic: "Infographic",
  meme_format: "Meme",
};

function lookup(table: Record<string, string>, value: string | null | undefined): string {
  if (!value) return "—";
  const raw = value.trim();
  if (table[raw]) return table[raw];
  const norm = raw.toLowerCase().replace(/-/g, "_");
  for (const [k, v] of Object.entries(table)) {
    if (k.toLowerCase().replace(/-/g, "_") === norm) return v;
  }
  return raw.replace(/_/g, " ");
}

export const carouselLabel = {
  swipeAnchor: (v: string | null | undefined) => lookup(SWIPE_ANCHOR_VI, v),
  swipeTrigger: (v: string | null | undefined) => lookup(SWIPE_TRIGGER_VI, v),
  contentArc: (v: string | null | undefined) => lookup(CONTENT_ARC_VI, v),
  visualConsistency: (v: string | null | undefined) => lookup(VISUAL_CONSISTENCY_VI, v),
  layout: (v: string | null | undefined) => lookup(SLIDE_LAYOUT_VI, v),
};
