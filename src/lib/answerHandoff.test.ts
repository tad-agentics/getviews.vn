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
  it("builds trends win path", () => {
    const path = trendsVideoHandoffPath("https://www.tiktok.com/@a/video/1");
    expect(path).toContain("/app/answer?");
    expect(path).toContain("depth=basic");
    expect(path).toContain("mode=win");
    expect(path).toContain("from=trends");
  });

  it("parses depth and mode", () => {
    const sp = new URLSearchParams("q=x&depth=deep&mode=flop&from=pattern");
    expect(parseAnswerHandoffParams(sp)).toEqual({
      depth: "deep",
      mode: "flop",
      from: "pattern",
    });
  });

  it("defaults depth to basic", () => {
    const sp = new URLSearchParams("q=x");
    expect(parseAnswerHandoffParams(sp).depth).toBe("basic");
    expect(parseAnswerHandoffParams(sp).mode).toBeNull();
  });

  it("buildAnswerHandoffPath encodes q", () => {
    const path = buildAnswerHandoffPath({ q: "a b", mode: "win" });
    expect(path).toMatch(/q=a\+b|q=a%20b/);
  });

  it("buildAnswerHandoffPath omits depth when includeDepth is false", () => {
    const path = buildAnswerHandoffPath({
      q: "brief",
      from: "composer",
      includeDepth: false,
    });
    expect(path).toContain("/app/answer?");
    expect(path).not.toContain("depth=");
    expect(path).toContain("from=composer");
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
