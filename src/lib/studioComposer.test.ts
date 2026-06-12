import { describe, expect, it } from "vitest";

import { planStudioComposerSubmit } from "./studioComposer";

describe("planStudioComposerSubmit", () => {
  it("routes Khám Kênh to /app/channel with handle", () => {
    const plan = planStudioComposerSubmit("channel", "@creator");
    expect(plan).toEqual({
      kind: "navigate",
      to: "/app/channel?handle=creator",
    });
  });

  it("routes video URL to /app/answer without mode (tier decides framing)", () => {
    const url = "https://www.tiktok.com/@x/video/123";
    const plan = planStudioComposerSubmit("video", url);
    expect(plan.kind).toBe("navigate");
    if (plan.kind === "navigate") {
      expect(plan.to).toContain("/app/answer?");
      expect(plan.to).not.toContain("mode=");
      expect(plan.to).not.toContain("depth=");
      expect(plan.to).toContain(encodeURIComponent(url));
    }
  });

  it("routes Tạo kịch bản to /app/answer without depth param", () => {
    const plan = planStudioComposerSubmit("script", "Kịch bản review son 30s");
    expect(plan.kind).toBe("navigate");
    if (plan.kind === "navigate") {
      expect(plan.to).toContain("/app/answer?");
      expect(plan.to).toContain("from=composer");
      expect(plan.to).not.toContain("depth=");
    }
  });

  it("does not attach mode for generic text without TikTok URL", () => {
    const plan = planStudioComposerSubmit(
      "video",
      "Xu hướng TikTok tuần này trong ngách skincare",
    );
    expect(plan.kind).toBe("navigate");
    if (plan.kind === "navigate") {
      expect(plan.to).toContain("/app/answer?");
      expect(plan.to).not.toContain("mode=");
    }
  });

  it("blocks bare non-TikTok video page URL before navigation", () => {
    const plan = planStudioComposerSubmit(
      "video",
      "linhbeauty.vn/video/74012345678901234",
    );
    expect(plan).toEqual({
      kind: "blocked",
      reason: "non_tiktok_url",
      message: expect.stringMatching(/link TikTok/i),
    });
  });

  it("blocks YouTube URL before navigation", () => {
    const plan = planStudioComposerSubmit(
      "video",
      "https://www.youtube.com/watch?v=abc",
    );
    expect(plan).toEqual({
      kind: "blocked",
      reason: "non_tiktok_url",
      message: expect.stringMatching(/link TikTok/i),
    });
  });

  it("routes channel intent detected on video pill", () => {
    const plan = planStudioComposerSubmit(
      "video",
      "Soi kênh @rival — audit đối thủ",
    );
    expect(plan).toEqual({
      kind: "navigate",
      to: "/app/channel?handle=rival",
    });
  });
});
