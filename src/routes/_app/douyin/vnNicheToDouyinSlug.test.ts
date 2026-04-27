import { describe, expect, it } from "vitest";

import { vnNicheToDouyinSlug } from "./vnNicheToDouyinSlug";


describe("vnNicheToDouyinSlug", () => {
  it("maps the 11 supported VN niches to the correct Douyin slug", () => {
    expect(vnNicheToDouyinSlug(1)).toBe("home"); // Shopee / Gia dụng
    expect(vnNicheToDouyinSlug(2)).toBe("beauty");
    expect(vnNicheToDouyinSlug(3)).toBe("fashion");
    expect(vnNicheToDouyinSlug(4)).toBe("food");
    expect(vnNicheToDouyinSlug(6)).toBe("lifestyle");
    expect(vnNicheToDouyinSlug(7)).toBe("parenting");
    expect(vnNicheToDouyinSlug(8)).toBe("wellness");
    expect(vnNicheToDouyinSlug(9)).toBe("tech");
    expect(vnNicheToDouyinSlug(10)).toBe("home");
    expect(vnNicheToDouyinSlug(15)).toBe("finance");
    expect(vnNicheToDouyinSlug(16)).toBe("travel");
  });

  it("returns null for VN niches without a clean Douyin equivalent", () => {
    // 5 MMO, 11 EduTok, 12 Livestream, 13 Hài, 14 Ô tô, 17 Gaming
    expect(vnNicheToDouyinSlug(5)).toBeNull();
    expect(vnNicheToDouyinSlug(11)).toBeNull();
    expect(vnNicheToDouyinSlug(12)).toBeNull();
    expect(vnNicheToDouyinSlug(13)).toBeNull();
    expect(vnNicheToDouyinSlug(14)).toBeNull();
    expect(vnNicheToDouyinSlug(17)).toBeNull();
  });

  it("returns null for null / undefined / unknown ids", () => {
    expect(vnNicheToDouyinSlug(null)).toBeNull();
    expect(vnNicheToDouyinSlug(undefined)).toBeNull();
    expect(vnNicheToDouyinSlug(999)).toBeNull();
  });
});
