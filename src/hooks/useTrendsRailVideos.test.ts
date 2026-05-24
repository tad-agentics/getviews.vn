import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchTrendsRailBreakouts } from "./useTrendsRailVideos";
import { pickRotatingBreakoutWindow } from "./useTopBreakouts";

vi.mock("@/lib/supabase", () => ({
  supabase: { from: vi.fn() },
}));

vi.mock("@/lib/corpusNicheFilter", () => ({
  applyBrowsableCorpusFilter: (q: unknown) => q,
  applyVideoCorpusNicheFilter: (q: unknown) => q,
}));

function mockChain(rows: unknown[]) {
  const chain = {
    select: vi.fn().mockReturnThis(),
    gte: vi.fn().mockReturnThis(),
    not: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    limit: vi.fn().mockReturnThis(),
  };
  chain.limit.mockImplementation(() => Promise.resolve({ data: rows, error: null }));
  return chain;
}

describe("fetchTrendsRailBreakouts", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const { supabase } = await import("@/lib/supabase");
    vi.mocked(supabase.from).mockReset();
  });
  it("returns empty when neither junction nor legacy niche is set", async () => {
    const out = await fetchTrendsRailBreakouts({ contentClassIds: [] });
    expect(out.videos).toEqual([]);
    expect(out.meta.eligibleCount).toBe(0);
  });

  it("queries legacy ingest_loop_niche_id when junction is empty", async () => {
    const { supabase } = await import("@/lib/supabase");
    const chainEligible = mockChain([{ video_id: "l1", views: 100, breakout_multiplier: 2.1 }]);
    const chainFallback = mockChain([]);
    vi.mocked(supabase.from)
      .mockReturnValueOnce(chainEligible as never)
      .mockReturnValueOnce(chainFallback as never);

    const out = await fetchTrendsRailBreakouts(
      { contentClassIds: [], legacyNicheId: 7 },
      5,
      1_700_000_000_000,
    );
    expect(chainEligible.eq).toHaveBeenCalledWith("ingest_loop_niche_id", 7);
    expect(out.videos[0]!.video_id).toBe("l1");
  });

  it("queries reference_eligible=true before unfiltered fallback", async () => {
    const { supabase } = await import("@/lib/supabase");
    const chainEligible = mockChain([{ video_id: "e1", views: 100, breakout_multiplier: 2.1 }]);
    const chainAll = mockChain([
      { video_id: "e1", views: 100, breakout_multiplier: 2.1 },
      { video_id: "u1", views: 90, breakout_multiplier: 1.6 },
    ]);
    vi.mocked(supabase.from)
      .mockReturnValueOnce(chainEligible as never)
      .mockReturnValueOnce(chainAll as never);

    const out = await fetchTrendsRailBreakouts({ contentClassIds: [12, 34] }, 2);
    expect(chainEligible.eq).toHaveBeenCalledWith("reference_eligible", true);
    expect(out.videos.some((v) => v.video_id === "u1")).toBe(true);
    expect(out.meta.usedFallback).toBe(true);
  });

  it("skips fallback query when eligible pool fills the rotation pool", async () => {
    const { supabase } = await import("@/lib/supabase");
    const eligibleRows = Array.from({ length: 20 }, (_, i) => ({
      video_id: `e${i}`,
      views: 100 + i,
      breakout_multiplier: 3 - i * 0.01,
    }));
    const chainEligible = mockChain(eligibleRows);
    vi.mocked(supabase.from).mockReturnValueOnce(chainEligible as never);

    const out = await fetchTrendsRailBreakouts({ contentClassIds: [1] }, 5);
    expect(supabase.from).toHaveBeenCalledTimes(1);
    expect(out.videos).toHaveLength(5);
    expect(out.meta.usedFallback).toBe(false);
  });

  it("marks usedFallback false when every visible row is eligible", async () => {
    const { supabase } = await import("@/lib/supabase");
    const chainEligible = mockChain([
      { video_id: "e1", views: 100, breakout_multiplier: 2.1 },
      { video_id: "e2", views: 90, breakout_multiplier: 1.9 },
    ]);
    const chainFallback = mockChain([]);
    vi.mocked(supabase.from)
      .mockReturnValueOnce(chainEligible as never)
      .mockReturnValueOnce(chainFallback as never);

    const out = await fetchTrendsRailBreakouts({ contentClassIds: [1] }, 2);
    expect(out.meta.usedFallback).toBe(false);
    expect(out.videos.every((v) => v.video_id.startsWith("e"))).toBe(true);
  });

  it("rotates visible slice with bucket offset vs Home default", () => {
    const pool = Array.from({ length: 10 }, (_, i) => ({ video_id: `v${i}` }));
    const home = pickRotatingBreakoutWindow(pool, 3, 0, 15 * 60 * 1000, 0);
    const trends = pickRotatingBreakoutWindow(pool, 5, 0, 15 * 60 * 1000, 3);
    expect(home.map((r) => r.video_id)).not.toEqual(trends.map((r) => r.video_id));
  });
});
