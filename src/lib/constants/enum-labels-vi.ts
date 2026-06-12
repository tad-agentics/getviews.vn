/**
 * Vietnamese display labels for enum values surfaced in the UI.
 *
 * Mirrors ``cloud-run/getviews_pipeline/enum_labels_vi.py`` — the two
 * files must stay in sync. Whenever a new enum code flows from the
 * corpus into a user-visible string, add its translation here AND in
 * the Python module.
 *
 * The QA audit on 2026-04-22 (BUG-02) caught raw codes like
 * ``TEXT_TITLE``, ``QUESTION_XL``, ``STAT_BURST``, ``face_to_camera``,
 * ``BOLD CENTER``, ``how_to`` rendering verbatim across the Script
 * editor, Chế độ quay, Channel detail and Video detail pages. The root
 * cause was components rendering ``shot.overlay`` / ``scene.type`` /
 * ``hook.type`` straight from the data model without a display layer.
 */

export const OVERLAY_STYLE_VI: Record<string, string> = {
  TEXT_TITLE: "Tiêu đề lớn",
  BOLD_CENTER: "Chữ in đậm ở giữa",
  "BOLD CENTER": "Chữ in đậm ở giữa",
  SUB_CAPTION: "Phụ đề",
  "SUB-CAPTION": "Phụ đề",
  QUESTION_XL: "Câu hỏi cỡ lớn",
  STAT_BURST: "Số liệu nổi bật",
  LABEL: "Nhãn",
  NONE: "Không có chữ",
  "": "Không có chữ",
};

export const SCENE_TYPE_VI: Record<string, string> = {
  face_to_camera: "Cận mặt",
  product_shot: "Cận sản phẩm",
  screen_recording: "Quay màn hình",
  broll: "B-roll",
  text_card: "Thẻ chữ",
  demo: "Demo sản phẩm",
  action: "Hành động",
  other: "Khác",
};

export const FIRST_FRAME_VI: Record<string, string> = {
  face: "Cận mặt",
  face_with_text: "Cận mặt + chữ",
  product: "Sản phẩm",
  text_only: "Chỉ chữ",
  action: "Hành động",
  screen_recording: "Quay màn hình",
  other: "Khác",
};

export const HOOK_TIMELINE_EVENT_VI: Record<string, string> = {
  face_enter: "Khuôn mặt xuất hiện",
  first_word: "Lời thoại đầu",
  text_overlay: "Chữ hiện lên màn hình",
  sound_drop: "Nhạc/âm thanh bắt đầu",
  cut: "Cắt cảnh đầu tiên",
  product_enter: "Sản phẩm xuất hiện",
  reveal: "Khoảnh khắc chốt hạ",
};

/**
 * ``VideoEnrichment.style_tags`` — production-style chips in "KIỂU SẢN
 * XUẤT" (ContextStrip). Open vocabulary from Gemini enrichment, so this
 * map covers the recurring codes (live audit 2026-06-12 caught
 * ``product_showcase`` / ``lifestyle_b_roll`` / ``text_overlay_heavy``
 * rendering raw); anything unmapped falls back to humanized text
 * (underscores → spaces) via {@link styleTagVi} — never the raw enum.
 * Mirrors ``enum_labels_vi.STYLE_TAG_VI``.
 */
export const STYLE_TAG_VI: Record<string, string> = {
  product_showcase: "Trưng bày sản phẩm",
  lifestyle_b_roll: "B-roll đời thường",
  text_overlay_heavy: "Nhiều chữ trên màn hình",
  talking_head: "Nói trước camera",
  voiceover: "Lồng tiếng",
  voiceover_b_roll: "Lồng tiếng + B-roll",
  asmr: "ASMR",
  unboxing: "Đập hộp",
  before_after: "Trước — sau",
  tutorial: "Hướng dẫn từng bước",
  pov: "POV",
  street_interview: "Phỏng vấn đường phố",
  skit: "Tiểu phẩm",
  vlog: "Vlog",
  green_screen: "Phông xanh",
  fast_cuts: "Cắt cảnh nhanh",
  cinematic: "Quay điện ảnh",
  screen_recording: "Quay màn hình",
  foreign_reup: "Reup nước ngoài",
};

/** ``VideoAnalysis.tone`` — mirrors ``enum_labels_vi.VIDEO_TONE_VI``. */
export const VIDEO_TONE_VI: Record<string, string> = {
  educational: "Giáo dục",
  entertaining: "Giải trí",
  emotional: "Cảm xúc",
  humorous: "Hài hước",
  inspirational: "Truyền cảm hứng",
  urgent: "Khẩn trương",
  conversational: "Trò chuyện",
  authoritative: "Chuyên gia",
};

function lookup(
  table: Record<string, string>,
  value: string | null | undefined,
  fallback?: string,
): string {
  if (!value) return fallback ?? "";
  const raw = String(value).trim();
  if (raw in table) return table[raw]!;
  // Case-insensitive + whitespace/underscore agnostic lookup so upstream
  // stylistic drift still resolves (``"face enter"`` vs ``face_enter``).
  const norm = raw.toLowerCase().replace(/[-\s]/g, "_");
  for (const [k, v] of Object.entries(table)) {
    if (k.toLowerCase().replace(/[-\s]/g, "_") === norm) return v;
  }
  return fallback ?? raw;
}

export const overlayStyleVi = (v: string | null | undefined, fallback?: string) =>
  lookup(OVERLAY_STYLE_VI, v, fallback);

export const sceneTypeVi = (v: string | null | undefined, fallback?: string) =>
  lookup(SCENE_TYPE_VI, v, fallback);

export const firstFrameVi = (v: string | null | undefined, fallback?: string) =>
  lookup(FIRST_FRAME_VI, v, fallback);

export const hookTimelineEventVi = (v: string | null | undefined, fallback?: string) =>
  lookup(HOOK_TIMELINE_EVENT_VI, v, fallback);

export const videoToneVi = (v: string | null | undefined, fallback?: string) =>
  lookup(VIDEO_TONE_VI, v, fallback);

/** ``product_showcase`` → ``product showcase`` — readable fallback for open-vocabulary enums. */
export function humanizeEnumCode(v: string | null | undefined): string {
  return String(v ?? "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Style-tag chip label — mapped Vietnamese, else humanized (never the raw enum). */
export const styleTagVi = (v: string | null | undefined) =>
  lookup(STYLE_TAG_VI, v, humanizeEnumCode(v));
