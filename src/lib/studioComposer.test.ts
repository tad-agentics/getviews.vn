import { describe, expect, it } from "vitest";

import {
  composerDepthHint,
  composerDepthTooltip,
  planStudioComposerSubmit,
} from "./studioComposer";

describe("composerDepthHint", () => {
  it("explains channel deep cost and remaining runs", () => {
    const hint = composerDepthHint("channel", "deep", 10);
    expect(hint.activeLine).toMatch(/Chuyên sâu · 3 credit/);
    expect(hint.compareLine).toMatch(/Cơ bản · 0 credit/);
    expect(hint.creditsLine).toMatch(/còn 10 credit/);
    expect(hint.creditsLine).toMatch(/khoảng 3 lần/);
  });

  it("explains video basic with run estimate", () => {
    const hint = composerDepthHint("video_flop", "basic", 5);
    expect(hint.activeLine).toMatch(/Cơ bản · 1 credit/);
    expect(hint.creditsLine).toMatch(/khoảng 5 lần/);
  });
});

describe("composerDepthTooltip", () => {
  it("includes cost, deliverable, and run estimate for video deep", () => {
    const tip = composerDepthTooltip("video_flop", "deep", 6);
    expect(tip).toMatch(/Chuyên sâu — 2 credit/);
    expect(tip).toMatch(/heatmap giờ đăng/i);
    expect(tip).toMatch(/khoảng 3 lần/);
  });

  it("warns when channel deep credits are insufficient", () => {
    const tip = composerDepthTooltip("channel", "deep", 2, 3);
    expect(tip).toMatch(/Cần tối thiểu 3 credit/);
    expect(tip).toMatch(/còn 2/);
  });
});

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

  it("blocks YouTube URL before navigation", () => {
    const plan = planStudioComposerSubmit(
      "video_flop",
      "https://www.youtube.com/watch?v=abc",
      "basic",
    );
    expect(plan).toEqual({
      kind: "blocked",
      reason: "non_tiktok_url",
      message: expect.stringMatching(/link TikTok/i),
    });
  });

  it("passes composer depth when channel intent detected on non-channel pill", () => {
    const plan = planStudioComposerSubmit(
      "video_flop",
      "Soi kênh @rival — audit đối thủ",
      "deep",
    );
    expect(plan).toEqual({
      kind: "navigate",
      to: "/app/channel?handle=rival&depth=deep",
    });
  });
});
