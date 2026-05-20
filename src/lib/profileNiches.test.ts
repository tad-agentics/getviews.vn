import { describe, expect, it } from "vitest";
import {
  canonicalNicheTaxonomyId,
  creatorNicheIdForLegacyNiche,
  legacyNicheIdForCreatorNiche,
  profileCreatorNicheId,
  profileFirstNicheId,
  profileHasNiche,
  resolveNicheNameVn,
} from "./profileNiches";

describe("profileNiches (two-axis model since PR6)", () => {
  it("profileHasNiche accepts a profile with creator_niche_id set", () => {
    expect(profileHasNiche({ creator_niche_id: 1 })).toBe(true);
    expect(profileHasNiche({ creator_niche_id: 14 })).toBe(true);
  });

  it("profileHasNiche rejects null/empty profile", () => {
    expect(profileHasNiche(null)).toBe(false);
    expect(profileHasNiche(undefined)).toBe(false);
    expect(profileHasNiche({ creator_niche_id: null })).toBe(false);
    expect(profileHasNiche({})).toBe(false);
  });

  it("profileCreatorNicheId returns the column value or null", () => {
    expect(profileCreatorNicheId({ creator_niche_id: 5 })).toBe(5);
    expect(profileCreatorNicheId({ creator_niche_id: null })).toBeNull();
    expect(profileCreatorNicheId(null)).toBeNull();
  });

  it("profileFirstNicheId resolves creator_niche_id → representative legacy niche_id", () => {
    expect(profileFirstNicheId({ creator_niche_id: 1 })).toBe(2);    // Beauty → Skincare
    expect(profileFirstNicheId({ creator_niche_id: 3 })).toBe(4);    // Food → F&B
    expect(profileFirstNicheId({ creator_niche_id: 14 })).toBe(8);   // Gym & Fitness → Gym
    expect(profileFirstNicheId(null)).toBeNull();
    expect(profileFirstNicheId({ creator_niche_id: null })).toBeNull();
  });

  it("legacyNicheIdForCreatorNiche covers active creator_niches", () => {
    const expected: Record<number, number | null> = {
      1: 2, 2: 3, 3: 4, 4: 27, 6: 7, 7: 11, 8: 9, 9: 5,
      10: 26, 11: 16, 12: 14, 14: 8, 15: 28, 16: 10,
    };
    for (const [cni, legacy] of Object.entries(expected)) {
      expect(legacyNicheIdForCreatorNiche(Number(cni))).toBe(legacy);
    }
    expect(legacyNicheIdForCreatorNiche(999)).toBeNull();
  });

  it("creatorNicheIdForLegacyNiche picks lowest id on ties (mirror Python)", () => {
    expect(creatorNicheIdForLegacyNiche(26)).toBe(10);
    expect(creatorNicheIdForLegacyNiche(27)).toBe(4);
    expect(creatorNicheIdForLegacyNiche(28)).toBe(15); // Âm nhạc · Vũ đạo
    expect(creatorNicheIdForLegacyNiche(13)).toBe(4); // retired Hài alias → lifestyle
    expect(creatorNicheIdForLegacyNiche(999)).toBeNull();
  });

  it("canonicalNicheTaxonomyId maps retired ids and is a no-op for current ones", () => {
    expect(canonicalNicheTaxonomyId(1)).toBe(5); // Shopee review → Kinh doanh online
    expect(canonicalNicheTaxonomyId(18)).toBe(4);
    expect(canonicalNicheTaxonomyId(22)).toBe(28); // K-pop → Âm nhạc · Vũ đạo ingest
    expect(canonicalNicheTaxonomyId(13)).toBe(27);
    expect(canonicalNicheTaxonomyId(23)).toBe(11);
    expect(canonicalNicheTaxonomyId(7)).toBe(7);
  });

  it("resolveNicheNameVn pins overridden labels for ids 2–4 (taxonomy ↔ creator copy)", () => {
    expect(resolveNicheNameVn(2, "Làm đẹp / Skincare")).toBe("Làm đẹp · Skincare");
    expect(resolveNicheNameVn(4, "Review đồ ăn / F&B")).toBe("Ẩm thực & Ăn uống");
    expect(resolveNicheNameVn(3, "Thời trang / Outfit")).toBe("Thời trang Phụ kiện");
    // No override → DB value passes through.
    expect(resolveNicheNameVn(7, "Mẹ bỉm sữa / Parenting")).toBe("Mẹ bỉm sữa / Parenting");
  });
});
