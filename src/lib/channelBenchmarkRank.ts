/** Benchmark bar + rank labels for HomeMyChannelSection (§6). */

export function benchmarkBarPct(userValue: number, p75: number): number {
  if (!Number.isFinite(userValue) || userValue <= 0 || p75 <= 0) return 0;
  return Math.min(100, Math.round((userValue / p75) * 100));
}

export function benchmarkRankLabel(userValue: number, p50: number, p75: number): string {
  if (p75 > 0 && userValue >= p75) return "Top 25%";
  if (p50 > 0 && userValue >= p50) return "Top 50%";
  return "Top 75%+";
}

export function formatEngagementPct(value: number): string {
  const pct = value <= 1 ? value * 100 : value;
  return `${pct.toFixed(1)}%`;
}
