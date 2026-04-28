/** Session key — last niche chosen on Studio Home or Xu hướng (per browser tab / session). */
const KEY = "gv:studio_niche_id";

function parseStored(raw: string | null): number | null {
  if (raw == null || raw === "") return null;
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) return null;
  return Math.floor(n);
}

/** Read the last saved Studio niche id, or null if missing / invalid. */
export function readStudioNicheId(): number | null {
  if (typeof window === "undefined") return null;
  try {
    return parseStored(sessionStorage.getItem(KEY));
  } catch {
    return null;
  }
}

/** Persist after Home picker or Trends niche filter so both surfaces stay aligned. */
export function writeStudioNicheId(id: number | null): void {
  if (typeof window === "undefined") return;
  try {
    if (id == null) sessionStorage.removeItem(KEY);
    else sessionStorage.setItem(KEY, String(id));
  } catch {
    /* private mode or quota */
  }
}
