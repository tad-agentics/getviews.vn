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
