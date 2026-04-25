import { describe, expect, it } from "vitest";
import { MAX_CREATOR_NICHES, MIN_CREATOR_NICHES, normalizeNicheIds, profileHasMinimumNiches } from "./profileNiches";

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

  it("constants are sane", () => {
    expect(MIN_CREATOR_NICHES).toBe(3);
    expect(MAX_CREATOR_NICHES).toBeGreaterThanOrEqual(MIN_CREATOR_NICHES);
  });
});
