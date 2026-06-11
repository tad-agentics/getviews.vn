import { describe, expect, it } from "vitest";
import {
  buildAnswerHandoffPath,
  parseAnswerHandoffParams,
  resolveVideoHandoffQuery,
  scriptRouteRedirectPath,
  scriptShootRedirectPath,
  trendsVideoHandoffPath,
} from "./answerHandoff";

describe("answerHandoff", () => {
  it("builds trends win path without depth param", () => {
    const path = trendsVideoHandoffPath("https://www.tiktok.com/@a/video/1");
    expect(path).toContain("/app/answer?");
    expect(path).not.toContain("depth=");
    expect(path).toContain("mode=win");
    expect(path).toContain("from=trends");
  });

  it("parses mode and from (ignores legacy depth param)", () => {
    const sp = new URLSearchParams("q=x&depth=deep&mode=flop&from=pattern");
    expect(parseAnswerHandoffParams(sp)).toEqual({
      mode: "flop",
      from: "pattern",
    });
  });

  it("defaults mode to null when absent", () => {
    const sp = new URLSearchParams("q=x");
    expect(parseAnswerHandoffParams(sp).mode).toBeNull();
  });

  it("buildAnswerHandoffPath encodes q", () => {
    const path = buildAnswerHandoffPath({ q: "a b", mode: "win" });
    expect(path).toMatch(/q=a\+b|q=a%20b/);
    expect(path).not.toContain("depth=");
  });

  it("scriptRouteRedirectPath maps legacy script deeplink to Answer", () => {
    const sp = new URLSearchParams("topic=abc&hook=def&duration=30");
    const path = scriptRouteRedirectPath(sp);
    expect(path).toContain("/app/answer?");
    expect(path).toContain("q=");
  });

  it("scriptShootRedirectPath preserves session + shoot draft id", () => {
    const sp = new URLSearchParams("session=sess-1");
    const path = scriptShootRedirectPath("draft-9", sp);
    expect(path).toContain("session=sess-1");
    expect(path).toContain("shoot=draft-9");
  });

  it("resolveVideoHandoffQuery prefers seedQ then session initial_q", () => {
    expect(
      resolveVideoHandoffQuery({
        seedQ: "https://tiktok.com/@a/video/1",
        sessionInitialQ: "https://tiktok.com/@b/video/2",
      }),
    ).toBe("https://tiktok.com/@a/video/1");
    expect(
      resolveVideoHandoffQuery({
        seedQ: "",
        sessionInitialQ: "https://tiktok.com/@b/video/2",
      }),
    ).toBe("https://tiktok.com/@b/video/2");
  });

  it("resolveVideoHandoffQuery reconstructs URL from video_id + creator", () => {
    expect(
      resolveVideoHandoffQuery({
        videoId: "7123456789",
        creatorHandle: "@creatorx",
      }),
    ).toBe("https://www.tiktok.com/@creatorx/video/7123456789");
    expect(resolveVideoHandoffQuery({ videoId: "7123456789" })).toBe(
      "https://www.tiktok.com/video/7123456789",
    );
  });
});
