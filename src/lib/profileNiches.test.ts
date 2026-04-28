import { describe, expect, it } from "vitest";
import {
  MAX_CREATOR_NICHES,
  MIN_CREATOR_NICHES,
  normalizeNicheIds,
  normalizeNicheIdsForProfile,
  profileFirstNicheId,
  profileFollowedNicheIds,
  profileHasMinimumNiches,
  resolveNicheNameVn,
} from "./profileNiches";

describe("profileNiches", () => {
  it("profileHasMinimumNiches accepts legacy primary-only", () => {
    expect(profileHasMinimumNiches({ primary_niche: 4, niche_ids: null })).toBe(true);
    expect(profileHasMinimumNiches({ primary_niche: 4, niche_ids: [] })).toBe(true);
  });

  it("profileHasMinimumNiches accepts three or more niche_ids", () => {
    expect(
      profileHasMinimumNiches({ primary_niche: 1, niche_ids: [1, 2, 3] }),
    ).toBe(true);
    expect(profileHasMinimumNiches({ primary_niche: null, niche_ids: [1, 2, 3] })).toBe(true);
  });

  it("profileHasMinimumNiches rejects empty profile", () => {
    expect(profileHasMinimumNiches(null)).toBe(false);
    expect(profileHasMinimumNiches({ primary_niche: null, niche_ids: null })).toBe(false);
  });

  it("profileHasMinimumNiches rejects one or two niche_ids only", () => {
    expect(profileHasMinimumNiches({ primary_niche: null, niche_ids: [1] })).toBe(false);
    expect(profileHasMinimumNiches({ primary_niche: null, niche_ids: [1, 2] })).toBe(false);
  });

  it("normalizeNicheIds dedupes in order", () => {
    expect(normalizeNicheIds([3, 1, 3, 2, 1])).toEqual([3, 1, 2]);
  });

  it("resolveNicheNameVn pins merged food niche label for id 4", () => {
    expect(resolveNicheNameVn(4, "Review đồ ăn / F&B")).toBe("Ẩm thực & Ăn uống");
    expect(resolveNicheNameVn(3, "Thời trang")).toBe("Thời trang");
  });

  it("normalizeNicheIdsForProfile maps merged niche ids and dedupes", () => {
    expect(normalizeNicheIdsForProfile([1, 23, 4])).toEqual([1, 11, 4]);
    expect(normalizeNicheIdsForProfile([14, 25, 2])).toEqual([14, 2]);
    expect(normalizeNicheIdsForProfile([11, 23])).toEqual([11]);
    expect(normalizeNicheIdsForProfile([15, 24, 2])).toEqual([15, 2]);
    expect(normalizeNicheIdsForProfile([4, 18, 2])).toEqual([4, 2]);
  });

  it("profileFirstNicheId prefers niche_ids[0] over legacy primary", () => {
    expect(profileFirstNicheId({ niche_ids: [7, 4, 2], primary_niche: 1 })).toBe(7);
    expect(profileFirstNicheId({ niche_ids: null, primary_niche: 4 })).toBe(4);
    expect(profileFirstNicheId({ niche_ids: [], primary_niche: 4 })).toBe(4);
  });

  it("profileFollowedNicheIds returns up to 3 ordered ids or legacy single", () => {
    expect(profileFollowedNicheIds({ niche_ids: [1, 2, 3, 9] })).toEqual([1, 2, 3]);
    expect(profileFollowedNicheIds({ niche_ids: null, primary_niche: 5 })).toEqual([5]);
  });

  it("constants are sane", () => {
    expect(MIN_CREATOR_NICHES).toBe(3);
    expect(MAX_CREATOR_NICHES).toBe(3);
    expect(MAX_CREATOR_NICHES).toBeGreaterThanOrEqual(MIN_CREATOR_NICHES);
  });
});
