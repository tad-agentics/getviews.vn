import { describe, expect, it } from "vitest";

import { tierImpliesWinFraming, videoReportWasModeCorrected } from "./videoReportCoherence";

describe("videoReportCoherence", () => {
  it("treats hit tier as win framing", () => {
    expect(tierImpliesWinFraming("hit")).toBe(true);
    expect(tierImpliesWinFraming("flop")).toBe(false);
  });

  it("treats channel breakout (average tier + ratio) as win framing", () => {
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
    expect(tierImpliesWinFraming("average", meta)).toBe(true);
  });

  it("detects when stored mode disagrees with hit tier", () => {
    expect(videoReportWasModeCorrected("flop", "hit")).toBe(true);
    expect(videoReportWasModeCorrected("win", "hit")).toBe(false);
  });
});
