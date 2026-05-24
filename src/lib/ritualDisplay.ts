/** Studio Home daily-ritual script display helpers. */

const MECHANISM_PREFIX = /^([a-z][a-z0-9_]*)\s*[—–-]\s*(.+)$/i;

/** Backend title_vi often ships with ASCII/smart quotes — strip before UI quotes. */
export function formatRitualHookTitle(raw: string | null | undefined): string {
  let t = raw?.trim() ?? "";
  if (!t) return "";
  for (let i = 0; i < 3; i += 1) {
    const next = t.replace(/^["'""«]+|["'""»]+$/g, "").trim();
    if (next === t) break;
    t = next;
  }
  return t;
}

/** Hide English mechanism slug; show Vietnamese explanation only. */
export function formatRitualWhyWorks(raw: string | null | undefined): string {
  const t = raw?.trim() ?? "";
  if (!t) return "";
  const m = t.match(MECHANISM_PREFIX);
  if (!m) return t;
  const body = m[2]?.trim();
  return body || t;
}

export function formatRitualShotLabel(shotCount: number, lengthSec: number): string {
  return `SCRIPT SẴN · ${shotCount} shot · ${lengthSec}s`;
}
