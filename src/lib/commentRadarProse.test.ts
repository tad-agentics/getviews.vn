import { describe, expect, it } from "vitest";

import { buildCommentRadarProse, hasCommentRadarContent } from "./commentRadarProse";

const base = {
  sampled: 30,
  total_available: 945,
  sentiment: { positive_pct: 3, negative_pct: 0, neutral_pct: 97 },
  purchase_intent: { count: 1, top_phrases: ["Vãi cái áo mua ở đâu mn"] },
  questions_asked: 1,
  language: "vi" as const,
};

describe("buildCommentRadarProse", () => {
  it("flags neutral-heavy comment sections", () => {
    expect(buildCommentRadarProse(base)).toMatch(/trung tính \(97%\)/);
  });

  it("calls out light purchase intent", () => {
    expect(buildCommentRadarProse(base)).toMatch(/1 bình luận hỏi mua/);
  });

  it("returns empty for missing or empty radar", () => {
    expect(buildCommentRadarProse(null)).toBe("");
    expect(buildCommentRadarProse({ ...base, sampled: 0 })).toBe("");
  });
});

describe("hasCommentRadarContent", () => {
  it("requires sampled > 0", () => {
    expect(hasCommentRadarContent(base)).toBe(true);
    expect(hasCommentRadarContent({ ...base, sampled: 0 })).toBe(false);
  });
});
