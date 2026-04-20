/**
 * Phase C.4 — shared helpers for Timing primitives.
 *
 * Tone ramp lifted from `thread-turns.jsx:101-107` but re-mapped to the
 * `--gv-*` namespace (no rgba / purple shims). Five levels, keyed to
 * heatmap cell value (0–10 normalised).
 */

export type TimingVarianceKind = "strong" | "weak" | "sparse";

/**
 * Background colour for a heatmap cell. The reference used `--accent`,
 * `--accent-soft`, and translucent rgba overlays; here we stay on the
 * `--gv-*` token set so audits pass without exceptions.
 */
export function cellBackgroundForValue(v: number): string {
  if (v >= 9) return "var(--gv-accent)";
  if (v >= 7) return "var(--gv-accent-soft)";
  if (v >= 5) return "var(--gv-accent-2-soft)";
  if (v >= 3) return "var(--gv-canvas-2)";
  return "var(--gv-paper)";
}

/** Cell text colour — dark on the two highest bands, muted otherwise. */
export function cellLabelColorForValue(v: number): string {
  if (v >= 9) return "var(--gv-paper)";
  if (v >= 7) return "var(--gv-ink)";
  return "var(--gv-ink-4)";
}

/** Border — the #1 cell gets an accent-deep ring; rest stays transparent. */
export function cellBorderForValue(v: number): string {
  return v >= 9 ? "1px solid var(--gv-accent-deep)" : "1px solid transparent";
}
