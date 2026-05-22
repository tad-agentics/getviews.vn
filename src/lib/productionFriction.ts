/**
 * Heuristic production friction from `format_axis` (Phase 2 v0).
 * Full per-class column deferred to Wave 4 — see two-axis-niche-model.md §3.2.
 */

export type ProductionFriction = "low" | "mid" | "high";

export type MorningEnergyMode = "low" | "high";

export const MORNING_ENERGY_STORAGE_KEY = "gv_morning_energy_mode";

const LOW_FRICTION_AXES = new Set([
  "vlog_daily",
  "talking_head_advice",
  "review_unboxing",
  "observational_relatable",
  "react_commentary",
  "tutorial_carousel",
  "listicle_carousel",
  "gallery_carousel",
]);

const HIGH_FRICTION_AXES = new Set([
  "montage_highlights",
  "dance_choreography",
  "skit_scripted",
  "music_performance",
  "live_commerce",
  "comparison_carousel",
  "story_carousel",
]);

/** Map format_axis → friction tier (default mid). */
export function frictionFromFormatAxis(formatAxis: string | null | undefined): ProductionFriction {
  const axis = (formatAxis ?? "").trim();
  if (!axis) return "mid";
  if (LOW_FRICTION_AXES.has(axis)) return "low";
  if (HIGH_FRICTION_AXES.has(axis)) return "high";
  if (axis === "tutorial" || axis === "pov_storytelling") return "mid";
  return "mid";
}

export function readMorningEnergyMode(): MorningEnergyMode {
  if (typeof window === "undefined") return "high";
  const raw = window.localStorage.getItem(MORNING_ENERGY_STORAGE_KEY);
  return raw === "low" ? "low" : "high";
}

export function writeMorningEnergyMode(mode: MorningEnergyMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(MORNING_ENERGY_STORAGE_KEY, mode);
}

/** When energy is low, prefer low-friction classes; high mode keeps all eligible rows. */
export function rowMatchesEnergyMode(
  contentClassId: number,
  formatAxisByClassId: Map<number, string>,
  mode: MorningEnergyMode,
): boolean {
  if (mode === "high") return true;
  const axis = formatAxisByClassId.get(contentClassId);
  return frictionFromFormatAxis(axis) === "low";
}
