/** Taxonomy ids merged or retired — exclude from niche pickers (covers pre-migration DB rows). */
export const RETIRED_NICHE_TAXONOMY_IDS: ReadonlySet<number> = new Set([1, 6, 12, 18, 23, 24, 25]);

/** Legacy id → surviving taxonomy id (matches Supabase merge / retire migrations). */
const NICHE_TAXONOMY_ALIASES: Readonly<Record<number, number>> = {
  1: 5, // Review đồ Shopee / Gia dụng → Kinh doanh online / Bán hàng
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

/** The user's single niche, or `null` before onboarding completes. */
export function profileFirstNicheId(
  profile: { primary_niche?: number | null } | null | undefined,
): number | null {
  if (!profile || profile.primary_niche == null) return null;
  return canonicalNicheTaxonomyId(profile.primary_niche);
}

/** Whether the profile has a niche set (used by the /app/* layout guard). */
export function profileHasNiche(
  profile: { primary_niche?: number | null } | null | undefined,
): boolean {
  return profile?.primary_niche != null;
}
