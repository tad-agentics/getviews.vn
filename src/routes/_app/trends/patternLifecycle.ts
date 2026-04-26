/**
 * Pattern lifecycle hint — drives the dot color + age text on
 * PatternCard (PR-T3). Derived from week-over-week instance counts so
 * we can ship without an extra BE field.
 *
 * Buckets:
 *   • "Mới · tuần đầu"      — prev=0, curr>0 (truly new) → pos dot
 *   • "Đang lên · X% tuần này" — curr ≥ prev × 1.5      → pos dot
 *   • "Đang sống"            — neutral growth            → pos dot
 *   • "Đang chậm lại"        — curr < prev × 0.7         → ink-3 dot
 *   • "Hết sóng"             — curr = 0                  → ink-3 dot
 *
 * Mirrors the design pack's freshness signal
 * (``screens/trends.jsx`` lines 632-635) where a green dot indicates
 * ``fresh / count > 0.5``.
 */

export type PatternLifecycle = {
  text: string;
  isFresh: boolean;
};

export function lifecycleHint(curr: number, prev: number): PatternLifecycle {
  if (curr <= 0) {
    return { text: "Hết sóng", isFresh: false };
  }
  if (prev === 0) {
    return { text: "Mới · tuần đầu", isFresh: true };
  }
  const ratio = curr / prev;
  if (ratio >= 1.5) {
    const pct = Math.round((ratio - 1) * 100);
    return { text: `Đang lên · +${pct}% tuần này`, isFresh: true };
  }
  if (ratio < 0.7) {
    return { text: "Đang chậm lại", isFresh: false };
  }
  return { text: "Đang sống", isFresh: true };
}
