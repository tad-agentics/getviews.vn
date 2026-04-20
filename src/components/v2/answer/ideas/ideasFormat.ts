/**
 * Phase C.3 — shared formatting helpers for Ideas primitives.
 */

export type IdeasVariant = "standard" | "hook_variants";

/** Short tag label (mono chip) shown next to the idea title. */
export function tagLabelVi(tag: string): string {
  const key = (tag || "").trim().toLowerCase();
  const map: Record<string, string> = {
    testimonial: "Testimonial",
    listicle: "Listicle",
    curiosity_gap: "Curiosity",
    bold_claim: "Bold claim",
    pov: "POV",
    stat: "Stat",
    story: "Story",
    how_to: "How-to",
    pain_point: "Pain point",
    trend_hijack: "Trend hijack",
    hook_variant: "Hook variant",
    question: "Question",
  };
  return map[key] ?? tag.replace(/_/g, " ") ?? "Ý tưởng";
}

/** Visual style chip label (right-col). */
export function styleLabelVi(style: string): string {
  const key = (style || "").trim().toLowerCase();
  const map: Record<string, string> = {
    handheld: "Quay handheld",
    "screen-record": "Screen record",
    "voice-led": "Voice-led",
    desk: "Desk demo",
    "before-after": "Before / after",
  };
  return map[key] ?? (style || "Handheld");
}
