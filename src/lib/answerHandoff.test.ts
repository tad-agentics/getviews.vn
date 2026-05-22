import { describe, expect, it } from "vitest";
import {
  buildAnswerHandoffPath,
  parseAnswerHandoffParams,
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
});
