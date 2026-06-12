/**
 * View-ratio coherence between the PerformanceTierChip and the KPI strip.
 *
 * Live audit (2026-06-12): the chip said "0.7× TB FORMAT" (BE
 * ``tier_ratio`` — views ÷ format corpus avg) while the VIEW KPI said
 * "0.6× ngách" (BE ``build_kpis`` — views ÷ niche avg). Two ratios for
 * "how this video compares" on the same screen reads as a bug. One source
 * of truth: when the payload carries ``tier_ratio`` the VIEW KPI delta
 * shows the SAME number (and the same cohort name) as the chip; when it's
 * missing, the KPI keeps its own niche-relative computation.
 */

import type { VideoKpi } from "@/lib/api-types";

/** Chip/KPI shared number format — 1 decimal, integers from 10×. */
export function formatTierRatio(ratio: number): string {
  if (ratio >= 10) return `${Math.round(ratio)}×`;
  return `${ratio.toFixed(1)}×`;
}

const VIEW_RATIO_DELTA_RE = /×\s*ngách/i;

export function reconcileViewKpiWithTierRatio(
  kpis: VideoKpi[],
  tierRatio: number | null | undefined,
): VideoKpi[] {
  const ratio =
    typeof tierRatio === "number" && Number.isFinite(tierRatio) && tierRatio > 0
      ? tierRatio
      : null;
  if (ratio === null) return kpis;
  return kpis.map((k) => {
    if (k.label !== "VIEW") return k;
    const delta = (k.delta ?? "").trim();
    // Only override the ratio-shaped delta (or its "—" sparse-cohort
    // placeholder) — never clobber an unrelated annotation.
    if (delta !== "" && delta !== "—" && !VIEW_RATIO_DELTA_RE.test(delta)) return k;
    return { ...k, delta: `${formatTierRatio(ratio)} TB format` };
  });
}
