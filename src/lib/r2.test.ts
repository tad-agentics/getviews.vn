import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  env: { VITE_R2_PUBLIC_URL: "https://media.getviews.vn" },
}));

import { corpusThumbnailSrcCandidates, r2FrameUrl, r2ThumbnailUrl } from "./r2";

describe("r2 thumbnail helpers", () => {
  it("builds frame and thumbnail URLs", () => {
    expect(r2FrameUrl("123")).toBe("https://media.getviews.vn/frames/123/0.png");
    expect(r2ThumbnailUrl("123", "png")).toBe("https://media.getviews.vn/thumbnails/123.png");
    expect(r2ThumbnailUrl("123", "jpg")).toBe("https://media.getviews.vn/thumbnails/123.jpg");
  });

  it("orders corpus candidates: DB URL then R2 fallbacks", () => {
    expect(
      corpusThumbnailSrcCandidates("999", "https://tiktok.cdn/expired.jpg"),
    ).toEqual([
      "https://tiktok.cdn/expired.jpg",
      "https://media.getviews.vn/thumbnails/999.png",
      "https://media.getviews.vn/thumbnails/999.jpg",
      "https://media.getviews.vn/frames/999/0.png",
    ]);
  });

  it("dedupes when DB URL is already R2", () => {
    const r2 = "https://media.getviews.vn/thumbnails/999.png";
    expect(corpusThumbnailSrcCandidates("999", r2)).toEqual([
      r2,
      "https://media.getviews.vn/thumbnails/999.jpg",
      "https://media.getviews.vn/frames/999/0.png",
    ]);
  });

  it("returns R2-only list when thumbnail_url is missing", () => {
    expect(corpusThumbnailSrcCandidates("999", null)).toEqual([
      "https://media.getviews.vn/thumbnails/999.png",
      "https://media.getviews.vn/thumbnails/999.jpg",
      "https://media.getviews.vn/frames/999/0.png",
    ]);
  });
});
