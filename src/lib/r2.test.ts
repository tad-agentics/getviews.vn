import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  env: { VITE_R2_PUBLIC_URL: "https://media.getviews.vn" },
}));

import { corpusThumbnailSrcCandidates, r2FrameUrl, r2ThumbnailUrl } from "./r2";

describe("r2 thumbnail helpers", () => {
  it("builds frame and thumbnail URLs", () => {
    expect(r2FrameUrl("123")).toBe("https://media.getviews.vn/frames/123/0.png");
    expect(r2ThumbnailUrl("123", "webp")).toBe("https://media.getviews.vn/thumbnails/123.webp");
    expect(r2ThumbnailUrl("123", "png")).toBe("https://media.getviews.vn/thumbnails/123.png");
    expect(r2ThumbnailUrl("123", "jpg")).toBe("https://media.getviews.vn/thumbnails/123.jpg");
  });

  it("orders corpus candidates: webp first, then DB URL, then legacy R2", () => {
    expect(
      corpusThumbnailSrcCandidates("999", "https://tiktok.cdn/expired.jpg"),
    ).toEqual([
      "https://media.getviews.vn/thumbnails/999.webp",
      "https://tiktok.cdn/expired.jpg",
      "https://media.getviews.vn/thumbnails/999.png",
      "https://media.getviews.vn/thumbnails/999.jpg",
    ]);
  });

  it("dedupes when DB URL is already R2 webp", () => {
    const r2 = "https://media.getviews.vn/thumbnails/999.webp";
    expect(corpusThumbnailSrcCandidates("999", r2)).toEqual([
      r2,
      "https://media.getviews.vn/thumbnails/999.png",
      "https://media.getviews.vn/thumbnails/999.jpg",
    ]);
  });

  it("returns R2-only list when thumbnail_url is missing", () => {
    expect(corpusThumbnailSrcCandidates("999", null)).toEqual([
      "https://media.getviews.vn/thumbnails/999.webp",
      "https://media.getviews.vn/thumbnails/999.png",
      "https://media.getviews.vn/thumbnails/999.jpg",
    ]);
  });

  it("does not fall back to heavy frames/0.png", () => {
    const urls = corpusThumbnailSrcCandidates("999", null);
    expect(urls.some((u) => u.includes("/frames/"))).toBe(false);
  });
});
