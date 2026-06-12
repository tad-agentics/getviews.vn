import { describe, expect, it } from "vitest";

import {
  buildCreatorComparisonProse,
  buildHookAnalysisFallbackProse,
  creatorComparisonPercentileLabel,
  hasContextStripContent,
  shouldShowMetadataBlock,
  shouldShowScriptStructureBlock,
} from "@/lib/videoAdjunctSections";

describe("videoAdjunctSections", () => {
  it("shows metadata block when stats_history has two snapshots", () => {
    expect(
      shouldShowMetadataBlock(
        {
          stats_history: [
            { at: "a", phase: "t0", views: 100, likes: 1, comments: 0, shares: 0 },
            { at: "b", phase: "t6h", views: 500, likes: 5, comments: 1, shares: 0 },
          ],
        } as never,
        null,
      ),
    ).toBe(true);
  });

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

  it("never labels a 1.3× video as below channel median (live bug 2026-06-12)", () => {
    // 201.903 view vs median 151K → 1.3× — the cached BE string said
    // "dưới mức trung bình"; the FE must derive the label from the ratio.
    const text = buildCreatorComparisonProse(
      {
        creator_handle: "@a",
        total_posts_analyzed: 9,
        median_views: 151_000,
        target_vs_median: 1.3,
        target_percentile: "dưới mức trung bình", // stale inverted BE value
        delta: 4,
        hit: { views: 600_000 },
        flop: { views: 150_000 },
      } as never,
      201_903,
      false,
    );
    expect(text).toContain("trên mức trung bình");
    expect(text).not.toContain("dưới mức trung bình");
  });

  it("derives percentile label bands from target_vs_median", () => {
    expect(creatorComparisonPercentileLabel(0.2)).toBe("hiệu suất thấp nhất kênh");
    expect(creatorComparisonPercentileLabel(0.5)).toBe("dưới mức trung bình");
    expect(creatorComparisonPercentileLabel(0.79)).toBe("dưới mức trung bình");
    expect(creatorComparisonPercentileLabel(0.8)).toBe("quanh mức trung bình");
    expect(creatorComparisonPercentileLabel(1.0)).toBe("quanh mức trung bình");
    expect(creatorComparisonPercentileLabel(1.2)).toBe("quanh mức trung bình");
    expect(creatorComparisonPercentileLabel(1.3)).toBe("trên mức trung bình");
    expect(creatorComparisonPercentileLabel(4.99)).toBe("trên mức trung bình");
    expect(creatorComparisonPercentileLabel(5)).toBe("top 10% kênh");
    // No ratio → fall back to the BE-provided string.
    expect(creatorComparisonPercentileLabel(null, "top 35%")).toBe("top 35%");
    expect(creatorComparisonPercentileLabel(undefined)).toBe("");
  });

  it("shows structure block from segments, or from duration when segments empty", () => {
    // Primary: stored segments present.
    expect(
      shouldShowScriptStructureBlock({ segments: [{ name: "x" }], meta: {} } as never),
    ).toBe(true);
    // Legacy/corpus replay: no segments but a real video with duration.
    expect(
      shouldShowScriptStructureBlock({
        segments: [],
        meta: { duration_sec: 15, content_format: "mukbang" },
      } as never),
    ).toBe(true);
    // Carousel: never a video-structure block.
    expect(
      shouldShowScriptStructureBlock({
        segments: [],
        meta: { duration_sec: 0, content_format: "carousel" },
      } as never),
    ).toBe(false);
    // No segments, no duration → nothing to show.
    expect(
      shouldShowScriptStructureBlock({ segments: [], meta: { duration_sec: 0 } } as never),
    ).toBe(false);
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
