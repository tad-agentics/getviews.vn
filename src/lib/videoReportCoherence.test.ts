import { describe, expect, it } from "vitest";

import {
  effectiveVideoReportMode,
  tierImpliesWinFraming,
  videoReportWasModeCorrected,
} from "./videoReportCoherence";

describe("videoReportCoherence", () => {
  it("maps flop report mode to win when tier is hit", () => {
    expect(effectiveVideoReportMode("flop", "hit")).toBe("win");
  });

  it("maps flop to win on channel breakout (average tier + ratio)", () => {
    const meta = {
      creator: "embeireview",
      views: 406_098,
      likes: 1,
      comments: 1,
      shares: 1,
      save_rate: 0.01,
      duration_sec: 30,
      thumbnail_url: null,
      date_posted: "2026-05-01",
      title: "t",
      niche_label: "Review",
      retention_source: "modeled" as const,
      creator_median_views: 934,
      target_vs_creator_median: 435,
    };
    expect(effectiveVideoReportMode("flop", "average", meta)).toBe("win");
    expect(tierImpliesWinFraming("average", meta)).toBe(true);
  });

  it("detects when stored mode disagrees with hit tier", () => {
    expect(videoReportWasModeCorrected("flop", "hit")).toBe(true);
    expect(videoReportWasModeCorrected("win", "hit")).toBe(false);
  });
});
