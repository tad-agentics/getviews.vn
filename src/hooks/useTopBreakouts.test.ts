import { describe, expect, it, vi } from "vitest";

import { fetchBreakoutPass, pickRotatingBreakoutWindow } from "./useTopBreakouts";

vi.mock("@/lib/supabase", () => ({
  supabase: { from: vi.fn() },
}));

vi.mock("@/lib/corpusNicheFilter", () => ({
  applyBrowsableCorpusFilter: (q: unknown) => q,
  applyVideoCorpusNicheFilter: (q: unknown) => q,
  fetchContentClassIdsForCreatorNiche: vi.fn(async () => []),
}));

describe("fetchBreakoutPass", () => {
  it("queries reference_eligible=true before unfiltered fallback", async () => {
    const { supabase } = await import("@/lib/supabase");
    const chainEligible = {
      select: vi.fn().mockReturnThis(),
      gte: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnThis(),
      limit: vi.fn().mockReturnThis(),
      then: undefined,
    };
    chainEligible.limit.mockImplementation(() =>
      Promise.resolve({
        data: [{ video_id: "e1", views: 100, breakout_multiplier: 2 }],
        error: null,
      }),
    );
    const chainAll = {
      select: vi.fn().mockReturnThis(),
      gte: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnThis(),
      limit: vi.fn().mockReturnThis(),
    };
    chainAll.limit.mockImplementation(() =>
      Promise.resolve({
        data: [
          { video_id: "e1", views: 100, breakout_multiplier: 2 },
          { video_id: "u1", views: 90, breakout_multiplier: 1.5 },
        ],
        error: null,
      }),
    );
    vi.mocked(supabase.from)
      .mockReturnValueOnce(chainEligible as never)
      .mockReturnValueOnce(chainAll as never);

    const rows = await fetchBreakoutPass("2026-01-01", { contentClassIds: [], legacyNicheId: null }, 2);
    expect(chainEligible.eq).toHaveBeenCalledWith("reference_eligible", true);
    expect(rows[0]!.video_id).toBe("e1");
    expect(rows.some((r) => r.video_id === "u1")).toBe(true);
  });
});

describe("pickRotatingBreakoutWindow", () => {
  const pool = [
    { video_id: "a" },
    { video_id: "b" },
    { video_id: "c" },
    { video_id: "d" },
    { video_id: "e" },
  ];
  const ROT = 15 * 60 * 1000;

  it("returns full pool when length <= limit", () => {
    expect(pickRotatingBreakoutWindow(pool.slice(0, 2), 3, 0, ROT)).toEqual(pool.slice(0, 2));
  });

  it("rotates start index in a 15m bucket", () => {
    const a = pickRotatingBreakoutWindow(pool, 3, 0, ROT);
    const b = pickRotatingBreakoutWindow(pool, 3, ROT, ROT);
    expect(a).toHaveLength(3);
    expect(b).toHaveLength(3);
    expect(a[0]!.video_id).not.toBe(b[0]!.video_id);
  });

  it("is stable within the same rotation bucket", () => {
    const a = pickRotatingBreakoutWindow(pool, 3, 1000, ROT);
    const b = pickRotatingBreakoutWindow(pool, 3, 2000, ROT);
    expect(a.map((x) => x.video_id)).toEqual(b.map((x) => x.video_id));
  });
});
