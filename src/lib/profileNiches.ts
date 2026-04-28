/** Minimum niches a creator must pick when using multi-niche onboarding / settings. */
export const MIN_CREATOR_NICHES = 3;

/** Upper bound — aligns with onboarding and settings (exactly three focus niches). */
export const MAX_CREATOR_NICHES = 3;

/** Taxonomy ids merged or retired — exclude from niche pickers (covers pre-migration DB rows). */
export const RETIRED_NICHE_TAXONOMY_IDS: ReadonlySet<number> = new Set([6, 12, 18, 23, 24, 25]);

/** Legacy id → surviving taxonomy id (matches Supabase merge / retire migrations). */
const NICHE_TAXONOMY_ALIASES: Readonly<Record<number, number>> = {
  6: 3, // Chị đẹp retired → Thời trang
  12: 5, // Livestream → Kinh doanh online
  18: 4, // Nấu ăn / Công thức → Ẩm thực & Ăn uống (id 4)
  23: 11, // Học tiếng → EduTok VN
  24: 15, // Crypto / Web3 → Tài chính / Đầu tư
  25: 14, // Moto culture → Ô tô / Xe máy
};

/** Resolve a taxonomy id after merges (no-op if already current). */
export function canonicalNicheTaxonomyId(id: number): number {
  return NICHE_TAXONOMY_ALIASES[id] ?? id;
}

/**
 * VN label for settings / pickers. Prefer this over raw `niche_taxonomy.name_vn` from Supabase
 * so product copy stays correct if a linked DB has not applied the latest migration yet.
 * Keys must stay aligned with `niche_taxonomy` UPDATEs in merge migrations.
 */
const NICHE_TAXONOMY_NAME_VN_BY_ID: Readonly<Partial<Record<number, string>>> = {
  4: "Ẩm thực & Ăn uống",
};

/** UI-facing Vietnamese name for a taxonomy row (id + value from DB). */
export function resolveNicheNameVn(id: number, nameVnFromDb: string): string {
  return NICHE_TAXONOMY_NAME_VN_BY_ID[id] ?? nameVnFromDb;
}

/** Apply merge aliases then dedupe order — use when reading profile niche picks in the UI. */
export function normalizeNicheIdsForProfile(ids: readonly number[]): number[] {
  return normalizeNicheIds(ids.map(canonicalNicheTaxonomyId));
}

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
