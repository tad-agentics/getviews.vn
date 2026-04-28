/**
 * D4c (2026-06-04) — VN niche_id → Douyin niche slug mapping.
 *
 * Drives the auto-niche banner above the toolbar: when the user has a
 * a mapped VN niche (first ``niche_ids`` or legacy id) set AND the Douyin slug has at
 * least one video in the corpus, the banner says
 *
 *   "Đang ưu tiên ngách <slug-name> dựa trên hồ sơ của bạn — Xoá ưu
 *    tiên"
 *
 * and applies the slug as the initial chip filter. The user can clear
 * it at any time; the dismissal is session-local (the banner reappears
 * on the next mount because the profile niche list is the source of truth).
 *
 * Both sides are 1:1 stable:
 *   • VN niche_taxonomy IDs are pinned in
 *     ``supabase/migrations/20260409000001_niche_taxonomy.sql``.
 *   • Douyin niche slugs are pinned in
 *     ``supabase/migrations/20260603000000_douyin_niche_taxonomy.sql``.
 *
 * Niches without a clean Douyin equivalent (MMO / EduTok / Livestream
 * / Hài / Ô tô / Gaming) return ``null`` — the banner stays hidden.
 */

const VN_TO_DOUYIN: Record<number, string> = {
  // 1  Review đồ Shopee / Gia dụng — closest to Douyin "home" lifestyle.
  1: "home",
  // 2  Làm đẹp / Skincare
  2: "beauty",
  // 3  Thời trang / Outfit
  3: "fashion",
  // 4  Ẩm thực & Ăn uống (dining + home cooking)
  4: "food",
  // 6  Chị đẹp — aspirational feminine lifestyle.
  6: "lifestyle",
  // 7  Mẹ bỉm sữa / Parenting
  7: "parenting",
  // 8  Gym / Fitness VN
  8: "wellness",
  // 9  Công nghệ / Tech
  9: "tech",
  // 10 Bất động sản — also lands on "home".
  10: "home",
  // 15 Tài chính / Đầu tư
  15: "finance",
  // 16 Du lịch / Travel
  16: "travel",
  // 5  MMO / 11 EduTok / 12 Livestream / 13 Hài / 14 Ô tô / 17 Gaming
  // intentionally omitted — no clean Douyin equivalent.
};

/** Returns the Douyin niche slug for a VN niche_id, or ``null`` when
 *  no mapping exists / the input is null. */
export function vnNicheToDouyinSlug(
  vnNicheId: number | null | undefined,
): string | null {
  if (vnNicheId == null) return null;
  return VN_TO_DOUYIN[vnNicheId] ?? null;
}
