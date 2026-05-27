import { describe, expect, it } from "vitest";
import {
  extractTikTokVideoIdFromText,
  hasTikTokUrlInText,
  nonTikTokUrlValidationMessage,
  queryUrlChipState,
} from "./tiktokUrl";

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

  it("allows bare tiktok.com video path without scheme", () => {
    expect(
      nonTikTokUrlValidationMessage("tiktok.com/@x/video/7634391245737053447"),
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
});

describe("hasTikTokUrlInText", () => {
  it("detects vt short links", () => {
    expect(hasTikTokUrlInText("x https://vt.tiktok.com/ZZZ y")).toBe(true);
  });

  it("detects bare tiktok.com host", () => {
    expect(hasTikTokUrlInText("tiktok.com/@x/video/1")).toBe(true);
  });
});
