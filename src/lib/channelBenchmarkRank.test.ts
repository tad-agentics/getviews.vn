import { describe, expect, it } from "vitest";

import { benchmarkBarPct, benchmarkRankLabel, formatEngagementPct } from "./channelBenchmarkRank";

describe("channelBenchmarkRank", () => {
  it("caps bar fill at 100%", () => {
    expect(benchmarkBarPct(200, 100)).toBe(100);
  });

  it("rank label uses p50/p75 thresholds", () => {
    expect(benchmarkRankLabel(90, 50, 80)).toBe("Top 25%");
    expect(benchmarkRankLabel(60, 50, 80)).toBe("Top 50%");
    expect(benchmarkRankLabel(10, 50, 80)).toBe("Top 75%+");
  });

  it("formatEngagementPct handles ratio and percent", () => {
    expect(formatEngagementPct(0.052)).toBe("5.2%");
    expect(formatEngagementPct(5.2)).toBe("5.2%");
  });
});
