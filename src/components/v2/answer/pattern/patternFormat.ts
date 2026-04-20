import type { LifecycleData } from "@/lib/api-types";

export function formatViews(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "0";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(Math.round(n));
}

export function formatDurationSec(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export function momentumVi(m: LifecycleData["momentum"]): { label: string; colorVar: string } {
  switch (m) {
    case "rising":
      return { label: "đang lên", colorVar: "var(--gv-accent)" };
    case "plateau":
      return { label: "đứng yên", colorVar: "var(--gv-ink-3)" };
    case "declining":
      return { label: "đang giảm", colorVar: "var(--gv-ink-2)" };
    default:
      return { label: "—", colorVar: "var(--gv-ink-3)" };
  }
}

export function wowDiffHasContent(
  w: {
    new_entries: unknown[];
    dropped: unknown[];
    rank_changes: unknown[];
  } | null | undefined,
): boolean {
  if (!w) return false;
  return w.new_entries.length > 0 || w.dropped.length > 0 || w.rank_changes.length > 0;
}

export function summarizeWoWDiff(w: {
  new_entries: Array<Record<string, unknown>>;
  dropped: Array<Record<string, unknown>>;
  rank_changes: Array<Record<string, unknown>>;
}): string {
  const parts: string[] = [];
  if (w.new_entries.length) parts.push(`${w.new_entries.length} hook mới trong top`);
  if (w.dropped.length) parts.push(`${w.dropped.length} hook rớt khỏi bảng`);
  if (w.rank_changes.length) parts.push(`${w.rank_changes.length} thay đổi thứ hạng`);
  return parts.join(" · ");
}
