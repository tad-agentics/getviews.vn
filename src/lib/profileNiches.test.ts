import { describe, expect, it } from "vitest";
import {
  canonicalNicheTaxonomyId,
  profileFirstNicheId,
  profileHasNiche,
  resolveNicheNameVn,
} from "./profileNiches";

describe("profileNiches (single-niche model)", () => {
  it("profileHasNiche accepts a profile with primary_niche set", () => {
    expect(profileHasNiche({ primary_niche: 4 })).toBe(true);
    expect(profileHasNiche({ primary_niche: 1 })).toBe(true);
  });

  it("profileHasNiche rejects null/empty profile", () => {
    expect(profileHasNiche(null)).toBe(false);
    expect(profileHasNiche(undefined)).toBe(false);
    expect(profileHasNiche({ primary_niche: null })).toBe(false);
    expect(profileHasNiche({})).toBe(false);
  });

  it("profileFirstNicheId returns canonical primary_niche or null", () => {
    expect(profileFirstNicheId({ primary_niche: 7 })).toBe(7);
    expect(profileFirstNicheId({ primary_niche: 4 })).toBe(4);
    // Retired-merged ids resolve to the surviving id.
    expect(profileFirstNicheId({ primary_niche: 18 })).toBe(4);
    expect(profileFirstNicheId({ primary_niche: 23 })).toBe(11);
    expect(profileFirstNicheId(null)).toBeNull();
    expect(profileFirstNicheId({ primary_niche: null })).toBeNull();
  });

  it("canonicalNicheTaxonomyId maps retired ids and is a no-op for current ones", () => {
    expect(canonicalNicheTaxonomyId(1)).toBe(5); // Shopee review → Kinh doanh online
    expect(canonicalNicheTaxonomyId(18)).toBe(4);
    expect(canonicalNicheTaxonomyId(22)).toBe(13); // K-pop / Âm nhạc → Hài / Giải trí
    expect(canonicalNicheTaxonomyId(23)).toBe(11);
    expect(canonicalNicheTaxonomyId(7)).toBe(7);
  });

  it("resolveNicheNameVn pins overridden labels for ids 3 + 4", () => {
    expect(resolveNicheNameVn(4, "Review đồ ăn / F&B")).toBe("Ẩm thực & Ăn uống");
    expect(resolveNicheNameVn(3, "Thời trang / Outfit")).toBe("Thời trang Phụ kiện");
    // No override → DB value passes through.
    expect(resolveNicheNameVn(7, "Mẹ bỉm sữa / Parenting")).toBe("Mẹ bỉm sữa / Parenting");
  });
});
