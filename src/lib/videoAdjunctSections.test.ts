import { describe, expect, it } from "vitest";

import {
  buildCreatorComparisonProse,
  buildHookAnalysisFallbackProse,
  hasContextStripContent,
} from "@/lib/videoAdjunctSections";

describe("videoAdjunctSections", () => {
  it("detects context strip payload", () => {
    expect(
      hasContextStripContent(
        { creator_median_views: 10_000, target_vs_creator_median: 0.5 } as never,
        null,
      ),
    ).toBe(true);
    expect(hasContextStripContent({} as never, null)).toBe(false);
  });

  it("builds creator comparison prose for win", () => {
    const text = buildCreatorComparisonProse(
      {
        creator_handle: "@a",
        total_posts_analyzed: 8,
        median_views: 1000,
        target_vs_median: 2,
        target_percentile: "top",
        delta: 1,
        hit: { views: 1 },
        flop: { views: 1 },
      } as never,
      2000,
      false,
    );
    expect(text).toMatch(/8 bài/);
    expect(text).toMatch(/hit\/flop/i);
  });

  it("uses hook narrative fallback when present", () => {
    const text = buildHookAnalysisFallbackProse(
      [{ t_range: "0–1s", label: "Mặt", body: "x" }],
      true,
      {
        loi_chinh_narrative: [{ error_id: "hook_slow", narrative: "Hook vào chậm 2s." }],
      } as never,
    );
    expect(text).toBe("Hook vào chậm 2s.");
  });
});
