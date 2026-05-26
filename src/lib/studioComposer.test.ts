import { describe, expect, it } from "vitest";

import { planStudioComposerSubmit } from "./studioComposer";

describe("planStudioComposerSubmit", () => {
  it("routes Khám Kênh to /app/channel with handle and depth", () => {
    const plan = planStudioComposerSubmit("channel", "@creator", "deep");
    expect(plan).toEqual({
      kind: "navigate",
      to: "/app/channel?handle=creator&depth=deep",
    });
  });

  it("routes video flop URL to /app/answer with mode=flop", () => {
    const url = "https://www.tiktok.com/@x/video/123";
    const plan = planStudioComposerSubmit("video_flop", url, "basic");
    expect(plan.kind).toBe("navigate");
    if (plan.kind === "navigate") {
      expect(plan.to).toContain("/app/answer?");
      expect(plan.to).toContain("mode=flop");
      expect(plan.to).toContain(encodeURIComponent(url));
    }
  });

  it("routes Tạo kịch bản to /app/answer without depth param", () => {
    const plan = planStudioComposerSubmit("script", "Kịch bản review son 30s", "deep");
    expect(plan.kind).toBe("navigate");
    if (plan.kind === "navigate") {
      expect(plan.to).toContain("/app/answer?");
      expect(plan.to).toContain("from=composer");
      expect(plan.to).not.toContain("depth=");
    }
  });

  it("does not attach mode=flop for generic text without TikTok URL", () => {
    const plan = planStudioComposerSubmit(
      "video_flop",
      "Xu hướng TikTok tuần này trong ngách skincare",
      "basic",
    );
    expect(plan.kind).toBe("navigate");
    if (plan.kind === "navigate") {
      expect(plan.to).toContain("/app/answer?");
      expect(plan.to).not.toContain("mode=flop");
    }
  });
});
