import { describe, expect, it } from "vitest";

import {
  buildStatsHistoryProse,
  hasStatsHistorySnapshots,
  resolveMetadataStripProse,
} from "@/lib/statsHistoryProse";

describe("statsHistoryProse", () => {
  it("detects at least two snapshots", () => {
    expect(hasStatsHistorySnapshots([{ at: "a", phase: "t0", views: 1, likes: 0, comments: 0, shares: 0 }])).toBe(
      false,
    );
    expect(
      hasStatsHistorySnapshots([
        { at: "a", phase: "t0", views: 100, likes: 1, comments: 0, shares: 0 },
        { at: "b", phase: "t6h", views: 200, likes: 2, comments: 0, shares: 0 },
      ]),
    ).toBe(true);
  });

  it("describes spike_then_flat with fix guidance", () => {
    const prose = buildStatsHistoryProse(
      [
        { at: "a", phase: "t0", views: 111_800, likes: 3000, comments: 50, shares: 20 },
        { at: "b", phase: "t6h", views: 182_500, likes: 5000, comments: 60, shares: 25 },
        { at: "c", phase: "t24h", views: 182_900, likes: 5100, comments: 62, shares: 26 },
      ],
      "spike_then_flat",
    );
    expect(prose).toMatch(/6 giờ đầu/);
    expect(prose).toMatch(/Chưa tốt/);
    expect(prose).toMatch(/comment/);
  });

  it("pairs fallback prose with context and built stats prose with stats strip", () => {
    const { contextProse, statsProse } = resolveMetadataStripProse({
      sectionText: "",
      fallbackProse: "Ngách phân tích: Làm đẹp.",
      meta: {
        stats_history: [
          { at: "a", phase: "t0", views: 1000, likes: 50, comments: 10, shares: 5 },
          { at: "b", phase: "t6h", views: 5000, likes: 80, comments: 12, shares: 4 },
          { at: "c", phase: "t24h", views: 5100, likes: 82, comments: 12, shares: 4 },
        ],
        distribution_shape: "spike_then_flat",
      } as never,
    });
    expect(contextProse).toMatch(/Làm đẹp/);
    expect(statsProse).toMatch(/Chưa tốt/);
  });

  it("describes steady growth positively", () => {
    const prose = buildStatsHistoryProse([
      { at: "a", phase: "t0", views: 10_000, likes: 500, comments: 40, shares: 10 },
      { at: "b", phase: "t6h", views: 25_000, likes: 1200, comments: 90, shares: 30 },
      { at: "c", phase: "t24h", views: 45_000, likes: 2200, comments: 150, shares: 55 },
    ]);
    expect(prose).toMatch(/Tốt/);
    expect(prose).toMatch(/tăng đều/);
  });
});
