/** Taxonomy ids merged or retired — exclude from niche pickers (covers pre-migration DB rows). */
export const RETIRED_NICHE_TAXONOMY_IDS: ReadonlySet<number> = new Set([
  1, 6, 12, 18, 19, 20, 22, 23, 24, 25,
]);

/** Retired UX buckets — hidden from pickers. */
export const RETIRED_CREATOR_NICHE_IDS: ReadonlySet<number> = new Set([13]);

/** Legacy id → surviving taxonomy id (matches Supabase merge / retire migrations). */
const NICHE_TAXONOMY_ALIASES: Readonly<Record<number, number>> = {
  1: 5, // Review đồ Shopee / Gia dụng → Kinh doanh online / Bán hàng
  6: 3, // Chị đẹp retired → Thời trang Phụ kiện
  12: 5, // Livestream → Kinh doanh online
  18: 4, // Nấu ăn / Công thức → Ẩm thực & Ăn uống (id 4)
  19: 27, // Thú cưng (retired) → Đời sống · Tâm sự
  20: 27, // Nhà cửa (retired) → Đời sống · Tâm sự
  22: 28, // K-pop (retired) → Âm nhạc · Vũ đạo ingest
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
  /** Corpus row id=2 — align label with ``creator_niches`` id=1 (PR1 middle dot, not slash). */
  2: "Làm đẹp · Skincare",
  3: "Thời trang Phụ kiện",
  4: "Ẩm thực & Ăn uống",
};

/** UI-facing Vietnamese name for a taxonomy row (id + value from DB). */
export function resolveNicheNameVn(id: number, nameVnFromDb: string): string {
  return NICHE_TAXONOMY_NAME_VN_BY_ID[id] ?? nameVnFromDb;
}

/**
 * The user's representative legacy niche id (for downstream queries
 * that still filter on ``video_corpus.niche_id``). Returns ``null`` for
 * pre-onboarding profiles.
 *
 * Two-axis refactor PR6: derived from ``creator_niche_id`` (canonical
 * column since PR3). The ``primary_niche`` column was dropped in PR6;
 * Trends pills, Home, Script, Answer, etc. that previously read
 * ``primary_niche`` directly continue to work because the helper
 * signature is unchanged.
 */
export function profileFirstNicheId(
  profile: { creator_niche_id?: number | null } | null | undefined,
): number | null {
  if (!profile || profile.creator_niche_id == null) return null;
  return legacyNicheIdForCreatorNiche(profile.creator_niche_id);
}

/**
 * The user's creator_niche_id (UX-facing axis since PR3). Returns null
 * for pre-onboarding profiles. Used by Trends pills + Settings active
 * highlight — surfaces that should display the new 16-bucket label.
 */
export function profileCreatorNicheId(
  profile: { creator_niche_id?: number | null } | null | undefined,
): number | null {
  if (!profile || profile.creator_niche_id == null) return null;
  return profile.creator_niche_id;
}

/**
 * Whether the profile has a niche set (used by the /app/* layout guard).
 * Two-axis refactor PR6: only ``creator_niche_id`` matters now;
 * legacy ``primary_niche`` column was dropped.
 */
export function profileHasNiche(
  profile: { creator_niche_id?: number | null } | null | undefined,
): boolean {
  return profile?.creator_niche_id != null;
}

/**
 * Reverse map: ``creator_niches.id`` → most-representative
 * ``niche_taxonomy.id`` for legacy callers (Cloud Run still filters
 * ``video_corpus.niche_id`` after PR6). Mirror of (inverse of)
 * ``map_legacy_niche_to_creator_niche()`` in
 * ``20260510000004_two_axis_niche_pr1_schema.sql``.
 *
 * Returns the canonical legacy id post-merge (e.g. id=4 for Food, not
 * the retired id=18). Keep for ≥30 days after PR6 and until analysis
 * pivots off legacy ``niche_id`` — see
 * ``artifacts/docs/two-axis-niche-cutover-runbook.md``.
 */
export function legacyNicheIdForCreatorNiche(creatorNicheId: number): number | null {
  switch (creatorNicheId) {
    case 1:  return 2;  // Beauty → Skincare
    case 2:  return 3;  // Fashion → Thời trang Phụ kiện
    case 3:  return 4;  // Food → Ẩm thực & Ăn uống
    case 4:  return 27; // Lifestyle → Đời sống · Tâm sự (legacy ingest)
    case 5:  return 13; // Comedy → Hài · Giải trí (restored v2)
    case 6:  return 7;  // Family → Mẹ bỉm
    case 7:  return 11; // Education → EduTok VN
    case 8:  return 9;  // Tech & Gaming → Công nghệ (representative; Gaming = legacy 17)
    case 9:  return 5;  // Business & Finance → Kinh doanh online
    case 10: return 26; // Wellness → Sức khoẻ / Wellness (mirrors Cloud Run profile_niches.py)
    case 11: return 16; // Travel & Outdoor Sports → Travel (representative; Sports = legacy 21)
    case 12: return 14; // Auto & Moto → Ô tô / Xe máy
    case 14: return 8;  // Gym & Fitness → Gym / Fitness VN
    case 15: return 28; // Music & Dance → Âm nhạc · Vũ đạo (legacy ingest)
    case 16: return 10; // Real Estate → Bất động sản (niche_taxonomy)
    case 17: return 29; // Art & Craft → Nghệ thuật · Thủ công (v2)
    default: return null;
  }
}

/**
 * Pick one ``creator_niches.id`` for a representative legacy ``niche_taxonomy.id``.
 * When several creator niches map to the same legacy id (e.g. 4, 5, 15 → 13),
 * returns the **lowest** id for a stable tie-break. Mirror of
 * ``creator_niche_id_for_legacy_niche()`` in ``profile_niches.py``.
 */
export function creatorNicheIdForLegacyNiche(legacyNicheId: number | null | undefined): number | null {
  if (legacyNicheId == null) return null;
  const canonical = canonicalNicheTaxonomyId(legacyNicheId);
  const matches: number[] = [];
  for (let cni = 1; cni <= 17; cni += 1) {
    const leg = legacyNicheIdForCreatorNiche(cni);
    if (leg === canonical) matches.push(cni);
  }
  if (matches.length === 0) return null;
  return Math.min(...matches);
}
