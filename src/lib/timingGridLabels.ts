/** Shared 7×8 timing / posting heatmap labels (Mon→Sun × 8 hour buckets). */

export const TIMING_DAYS_VN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"] as const;

export const TIMING_HOURS_VN = [
  "6–9",
  "9–12",
  "12–15",
  "15–18",
  "18–20",
  "20–22",
  "22–24",
  "0–3",
] as const;

/** Backend sends 7×8 floats; reject malformed grids so labels stay aligned. */
export function isTimingHeatmapGrid(grid: unknown): grid is number[][] {
  if (!Array.isArray(grid) || grid.length !== 7) return false;
  return grid.every(
    (row) =>
      Array.isArray(row) &&
      row.length === 8 &&
      row.every((c) => typeof c === "number" && Number.isFinite(c)),
  );
}
