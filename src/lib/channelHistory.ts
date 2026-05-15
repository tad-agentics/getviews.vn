/**
 * Client-side channel diagnosis history stored in localStorage.
 * channel_diagnoses has no user_id FK (shared cache), so we track
 * per-user visits locally. Max 20 entries, deduped by handle.
 */

const MAX_ENTRIES = 20;

export interface ChannelHistoryEntry {
  handle: string;
  visitedAt: string; // ISO
}

function storageKey(userId: string): string {
  return `gv_channel_history_${userId}`;
}

export function readChannelHistory(userId: string): ChannelHistoryEntry[] {
  try {
    const raw = localStorage.getItem(storageKey(userId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (e): e is ChannelHistoryEntry =>
        typeof e?.handle === "string" && typeof e?.visitedAt === "string",
    );
  } catch {
    return [];
  }
}

export function pushChannelHistory(userId: string, handle: string): void {
  try {
    const prev = readChannelHistory(userId).filter(
      (e) => e.handle.toLowerCase() !== handle.toLowerCase(),
    );
    const next: ChannelHistoryEntry[] = [
      { handle, visitedAt: new Date().toISOString() },
      ...prev,
    ].slice(0, MAX_ENTRIES);
    localStorage.setItem(storageKey(userId), JSON.stringify(next));
  } catch {
    // storage quota — silently skip
  }
}

export function removeChannelHistory(userId: string, handle: string): void {
  try {
    const next = readChannelHistory(userId).filter(
      (e) => e.handle.toLowerCase() !== handle.toLowerCase(),
    );
    localStorage.setItem(storageKey(userId), JSON.stringify(next));
  } catch {
    // ignore
  }
}
