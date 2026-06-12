import { describe, expect, it } from "vitest";
import { breakoutAnalyzePath } from "./BreakoutGrid";

describe("breakoutAnalyzePath", () => {
  it("uses tiktok_url when present", () => {
    const path = breakoutAnalyzePath({
      video_id: "123",
      tiktok_url: "https://www.tiktok.com/@creator/video/123",
      creator_handle: "creator",
    });
    expect(path).toContain(encodeURIComponent("https://www.tiktok.com/@creator/video/123"));
    expect(path).toContain("from=home-breakout");
    expect(path).not.toContain("mode=");
  });

  it("builds URL from handle when tiktok_url missing", () => {
    const path = breakoutAnalyzePath({
      video_id: "456",
      tiktok_url: "",
      creator_handle: "@shop",
    });
    expect(path).toContain(encodeURIComponent("https://www.tiktok.com/@shop/video/456"));
  });
});
