import { describe, expect, it } from "vitest";
import { extractChannelHandleFromMessage, normalizeChannelHandleInput } from "./channelHandle";

describe("normalizeChannelHandleInput", () => {
  it("strips @ and whitespace", () => {
    expect(normalizeChannelHandleInput("  @foo.bar  ")).toBe("foo.bar");
    expect(normalizeChannelHandleInput(null)).toBe(null);
  });
});

describe("extractChannelHandleFromMessage", () => {
  it("parses TikTok profile URL", () => {
    expect(extractChannelHandleFromMessage("x https://www.tiktok.com/@some_user y")).toBe("some_user");
  });
  it("skips video URLs", () => {
    expect(
      extractChannelHandleFromMessage("https://www.tiktok.com/@u/video/123"),
    ).toBeNull();
  });
  it("parses first @handle", () => {
    expect(extractChannelHandleFromMessage("Soi @abc")).toBe("abc");
  });
});
