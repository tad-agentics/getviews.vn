import type { BoostAttributionLevel } from "@/lib/api-types";

/** Mirrors ``corpus_boost_suspect.BoostAttribution`` — user-facing Vietnamese labels. */
export const BOOST_ATTRIBUTION_VI: Record<BoostAttributionLevel, string> = {
  unknown: "Chưa đủ dữ liệu",
  organic_confident: "Organic — không thấy dấu hiệu boost",
  suspect_low: "Nghi ngờ nhẹ — view cao, ER vừa",
  suspect_medium: "Nghi ngờ mạnh — có thể ads/seeding",
};

export function boostAttributionLabel(
  value: string | null | undefined,
): string {
  if (!value) return BOOST_ATTRIBUTION_VI.unknown;
  const key = value as BoostAttributionLevel;
  return BOOST_ATTRIBUTION_VI[key] ?? value.replace(/_/g, " ");
}

export function shouldShowBoostAttributionBlock(
  attribution: string | null | undefined,
  referenceEligible: boolean | null | undefined,
): boolean {
  if (referenceEligible === false) return true;
  if (attribution === "suspect_low" || attribution === "suspect_medium") return true;
  return false;
}
