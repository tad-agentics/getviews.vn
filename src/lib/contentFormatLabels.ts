/** Vietnamese-friendly labels for ``video_corpus.content_format`` slugs. */
const CONTENT_FORMAT_LABELS: Record<string, string> = {
  tutorial: "Hướng dẫn",
  review: "Đánh giá",
  haul: "Mua sắm",
  grwm: "Chuẩn bị đi",
  vlog: "Vlog ngày",
  before_after: "Trước/Sau",
  pov: "Góc nhìn POV",
  talking_head: "Nói thẳng camera",
  storytime: "Kể chuyện",
  listicle: "Danh sách",
  mukbang: "Mukbang",
  recipe: "Nấu ăn",
  comparison: "So sánh",
  storytelling: "Kể chuyện",
  comedy_skit: "Tiểu phẩm",
  outfit_transition: "Phối đồ",
  dance: "Nhảy",
  faceless: "Không lộ mặt",
  highlight: "Tóm tắt clip",
  gameplay: "Chơi game",
  lesson: "Bài học",
  other: "Khác",
};

/** Explore §II format pills — same labels as rail chips. */
export const CONTENT_FORMAT_FILTER_OPTIONS: { label: string; value: string }[] = [
  { value: "tutorial", label: CONTENT_FORMAT_LABELS.tutorial },
  { value: "review", label: CONTENT_FORMAT_LABELS.review },
  { value: "haul", label: CONTENT_FORMAT_LABELS.haul },
  { value: "grwm", label: CONTENT_FORMAT_LABELS.grwm },
  { value: "vlog", label: CONTENT_FORMAT_LABELS.vlog },
  { value: "before_after", label: CONTENT_FORMAT_LABELS.before_after },
  { value: "pov", label: CONTENT_FORMAT_LABELS.pov },
];

export function contentFormatLabelVi(slug: string | null | undefined): string | null {
  if (!slug?.trim()) return null;
  const key = slug.trim().toLowerCase();
  return CONTENT_FORMAT_LABELS[key] ?? key.replace(/_/g, " ");
}
