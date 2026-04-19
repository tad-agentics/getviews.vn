/** Maps backend ``color_key`` to design tokens (``video_structural``). */

const KEY_TO_VAR: Record<string, string> = {
  accent: "var(--gv-accent)",
  "accent-deep": "var(--gv-accent-deep)",
  "ink-2": "var(--gv-ink-2)",
  "ink-3": "var(--gv-ink-3)",
  canvas: "var(--gv-canvas)",
};

export function segmentColorVar(colorKey: string): string {
  return KEY_TO_VAR[colorKey] ?? "var(--gv-ink-3)";
}
