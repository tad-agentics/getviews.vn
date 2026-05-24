/** Vietnamese-friendly labels for ``video_corpus.content_format`` slugs. */
const CONTENT_FORMAT_LABELS: Record<string, string> = {
  tutorial: "Tutorial",
  review: "Review",
  haul: "Haul",
  grwm: "GRWM",
  vlog: "Vlog",
  before_after: "Trước/Sau",
  pov: "POV",
  talking_head: "Talking head",
  storytime: "Storytime",
  listicle: "Listicle",
};

export function contentFormatLabelVi(slug: string | null | undefined): string | null {
  if (!slug?.trim()) return null;
  const key = slug.trim();
  return CONTENT_FORMAT_LABELS[key] ?? key.replace(/_/g, " ");
}
