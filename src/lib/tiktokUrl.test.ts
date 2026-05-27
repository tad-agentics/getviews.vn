import { describe, expect, it } from "vitest";
import {
  extractTikTokHandleFromText,
  extractTikTokVideoIdFromText,
  formatTikTokSidebarHint,
  hasTikTokUrlInText,
  nonTikTokUrlValidationMessage,
  queryUrlChipState,
} from "./tiktokUrl";

describe("formatTikTokSidebarHint", () => {
  it("combines handle and short video id tail", () => {
    expect(
      formatTikTokSidebarHint(
        "https://www.tiktok.com/@curnon.official/video/7634391245737053447",
      ),
    ).toBe("@curnon.official · …053447");
  });
});

describe("extractTikTokHandleFromText", () => {
  it("parses @handle from video URL", () => {
    expect(
      extractTikTokHandleFromText("https://www.tiktok.com/@shop.vn/video/7634391245737053447"),
    ).toBe("shop.vn");
  });
});

describe("extractTikTokVideoIdFromText", () => {
  it("parses standard video URL", () => {
    expect(
      extractTikTokVideoIdFromText(
        "https://www.tiktok.com/@curnon.official/video/7634391245737053447?lang=vi-VN",
      ),
    ).toBe("7634391245737053447");
  });

  it("parses URL without @handle", () => {
    expect(extractTikTokVideoIdFromText("https://www.tiktok.com/video/7634391245737053447")).toBe(
      "7634391245737053447",
    );
  });
});

describe("nonTikTokUrlValidationMessage", () => {
  it("returns null for plain text without URLs", () => {
    expect(nonTikTokUrlValidationMessage("Xu hướng hook tuần này")).toBeNull();
  });

  it("returns null for TikTok-only URLs", () => {
    expect(
      nonTikTokUrlValidationMessage(
        "https://www.tiktok.com/@x/video/7634391245737053447 tại sao flop",
      ),
    ).toBeNull();
  });

  it("blocks YouTube URLs", () => {
    expect(
      nonTikTokUrlValidationMessage("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ).toMatch(/link TikTok/i);
  });

  it("blocks YouTube without https scheme", () => {
    expect(nonTikTokUrlValidationMessage("youtube.com/watch?v=abc")).toMatch(/link TikTok/i);
  });

  it("blocks bare non-TikTok /video/ paths without https", () => {
    expect(
      nonTikTokUrlValidationMessage("linhbeauty.vn/video/74012345678901234"),
    ).toMatch(/link TikTok/i);
  });

  it("blocks https non-TikTok /video/ paths", () => {
    expect(
      nonTikTokUrlValidationMessage("https://linhbeauty.vn/video/74012345678901234"),
    ).toMatch(/link TikTok/i);
  });

  it("allows bare tiktok.com video path without scheme", () => {
    expect(
      nonTikTokUrlValidationMessage("tiktok.com/@x/video/7634391245737053447"),
    ).toBeNull();
  });

  it("allows TikTok URLs with dotted handles (not external /video/ domains)", () => {
    expect(
      nonTikTokUrlValidationMessage(
        "https://www.tiktok.com/@curnon.official/video/7638856358812634375",
      ),
    ).toBeNull();
    expect(
      nonTikTokUrlValidationMessage(
        "https://www.tiktok.com/@shop.vn/video/7634391245737053447",
      ),
    ).toBeNull();
  });

  it("blocks when TikTok and non-TikTok URLs are mixed", () => {
    expect(
      nonTikTokUrlValidationMessage(
        "https://www.tiktok.com/@a/video/1 https://youtu.be/abc",
      ),
    ).toMatch(/link TikTok/i);
  });
});

describe("queryUrlChipState", () => {
  it("marks TikTok URL as tiktok chip", () => {
    expect(
      queryUrlChipState("https://vm.tiktok.com/abc123"),
    ).toEqual({ kind: "tiktok" });
  });

  it("marks YouTube as invalid", () => {
    const s = queryUrlChipState("https://youtube.com/watch?v=1");
    expect(s.kind).toBe("invalid");
    if (s.kind === "invalid") expect(s.message).toMatch(/link TikTok/i);
  });

  it("marks bare non-TikTok video page as invalid", () => {
    const s = queryUrlChipState("linhbeauty.vn/video/74012345678901234");
    expect(s).toEqual({
      kind: "invalid",
      message: expect.stringMatching(/link TikTok/i),
    });
  });
});

describe("hasTikTokUrlInText", () => {
  it("detects vt short links", () => {
    expect(hasTikTokUrlInText("x https://vt.tiktok.com/ZZZ y")).toBe(true);
  });

  it("detects bare tiktok.com host", () => {
    expect(hasTikTokUrlInText("tiktok.com/@x/video/1")).toBe(true);
  });
});
