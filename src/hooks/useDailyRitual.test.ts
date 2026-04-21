import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchDailyRitual } from "shared/api/ritual";
import type { DailyRitual } from "shared/types/ritual";

const baseParams = {
  baseUrl: "https://cr.example",
  accessToken: "jwt",
  expectedNicheId: 4,
};

function mockRitual(overrides: Partial<DailyRitual> = {}): DailyRitual {
  return {
    generated_for_date: "2026-04-21",
    niche_id: 4,
    adequacy: "niche_norms",
    scripts: [
      {
        hook_type_en: "comparison",
        hook_type_vi: "So sánh",
        title_vi: '"Test hook"',
        why_works: "Creates tension between two options for scroll-stoppers.",
        retention_est_pct: 55,
        shot_count: 4,
        length_sec: 35,
      },
      {
        hook_type_en: "pov",
        hook_type_vi: "POV",
        title_vi: '"POV line"',
        why_works: "Immediate identification with the viewer situation.",
        retention_est_pct: 50,
        shot_count: 3,
        length_sec: 30,
      },
      {
        hook_type_en: "how_to",
        hook_type_vi: "Hướng dẫn",
        title_vi: '"How to line"',
        why_works: "Utility promise keeps watch time.",
        retention_est_pct: 52,
        shot_count: 5,
        length_sec: 40,
      },
    ],
    generated_at: "2026-04-21T00:00:00.000Z",
    ...overrides,
  };
}

describe("fetchDailyRitual", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns ritual_no_row on 404 with code", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 404,
      ok: false,
      json: () => Promise.resolve({ code: "ritual_no_row", message: "Sắp có" }),
    });

    const r = await fetchDailyRitual(baseParams);
    expect(r).toEqual({ data: null, emptyReason: "ritual_no_row" });
  });

  it("returns ritual_niche_stale on 404 with code", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 404,
      ok: false,
      json: () => Promise.resolve({ code: "ritual_niche_stale", message: "Stale" }),
    });

    const r = await fetchDailyRitual(baseParams);
    expect(r).toEqual({ data: null, emptyReason: "ritual_niche_stale" });
  });

  it("defaults to ritual_no_row on 404 with bad JSON", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 404,
      ok: false,
      json: () => Promise.reject(new SyntaxError("bad json")),
    });

    const r = await fetchDailyRitual(baseParams);
    expect(r).toEqual({ data: null, emptyReason: "ritual_no_row" });
  });

  it("returns ritual_niche_stale when 200 niche_id mismatches expected", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(mockRitual({ niche_id: 99 })),
    });

    const r = await fetchDailyRitual(baseParams);
    expect(r).toEqual({ data: null, emptyReason: "ritual_niche_stale" });
  });

  it("returns data when 200 niche_id matches", async () => {
    const ritual = mockRitual();
    globalThis.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(ritual),
    });

    const r = await fetchDailyRitual(baseParams);
    expect(r).toEqual({ data: ritual, emptyReason: null });
  });

  it("strips trailing slash from baseUrl", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 404,
      ok: false,
      json: () => Promise.resolve({ code: "ritual_no_row", message: "" }),
    });
    globalThis.fetch = fetchMock;

    await fetchDailyRitual({ ...baseParams, baseUrl: "https://cr.example/" });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://cr.example/home/daily-ritual",
      expect.objectContaining({ headers: { Authorization: "Bearer jwt" } }),
    );
  });
});
