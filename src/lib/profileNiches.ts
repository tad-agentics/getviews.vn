/** Minimum niches a creator must pick when using multi-niche onboarding / settings. */
export const MIN_CREATOR_NICHES = 3;

/** Upper bound to keep payloads and UI reasonable. */
export const MAX_CREATOR_NICHES = 12;

export function profileHasMinimumNiches(
  profile: { primary_niche?: number | null; niche_ids?: number[] | null } | null | undefined,
): boolean {
  if (!profile) return false;
  const ids = profile.niche_ids;
  if (Array.isArray(ids) && ids.length >= MIN_CREATOR_NICHES) return true;
  // Legacy: only primary_niche before multi-niche column shipped
  if ((!ids || ids.length === 0) && profile.primary_niche != null) return true;
  return false;
}

/** Dedupe while preserving first-seen order. */
export function normalizeNicheIds(ids: readonly number[]): number[] {
  const seen = new Set<number>();
  const out: number[] = [];
  for (const id of ids) {
    if (!Number.isFinite(id) || seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}
