import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase", () => ({
  supabase: { from: vi.fn() },
}));

vi.mock("@/lib/corpusNicheFilter", () => ({
  applyBrowsableCorpusFilter: vi.fn((q: unknown) => q),
}));

import { fetchCrossNicheBreakouts } from "./useCrossNicheBreakouts";
import { supabase } from "@/lib/supabase";

function mockChain() {
  const calls: { method: string; args: unknown[] }[] = [];
  const chain = {
    select: (...args: unknown[]) => {
      calls.push({ method: "select", args });
      return chain;
    },
    gte: (...args: unknown[]) => {
      calls.push({ method: "gte", args });
      return chain;
    },
    eq: (...args: unknown[]) => {
      calls.push({ method: "eq", args });
      return chain;
    },
    not: (...args: unknown[]) => {
      calls.push({ method: "not", args });
      return chain;
    },
    order: (...args: unknown[]) => {
      calls.push({ method: "order", args });
      return chain;
    },
    limit: (...args: unknown[]) => {
      calls.push({ method: "limit", args });
      // Enough rows on eligible pass → skip reference_eligible=false fallback run.
      const stubRows = [
        { video_id: "v1" },
        { video_id: "v2" },
        { video_id: "v3" },
      ];
      return { data: stubRows, error: null, calls };
    },
    calls,
  };
  return chain;
}

describe("fetchCrossNicheBreakouts", () => {
  beforeEach(() => {
    vi.mocked(supabase.from).mockReset();
  });

  it("skips content_class exclude filter when junction is empty", async () => {
    const chain = mockChain();
    vi.mocked(supabase.from).mockReturnValue(chain as never);

    await fetchCrossNicheBreakouts([], 3);

    const eqCalls = chain.calls.filter((c) => c.method === "eq");
    expect(eqCalls.map((c) => c.args)).toEqual([["reference_eligible", true]]);

    const notCalls = chain.calls.filter((c) => c.method === "not");
    expect(notCalls).toHaveLength(1);
    expect(notCalls[0]?.args).toEqual(["content_class_id", "is", null]);
  });

  it("excludes junction classes via PostgREST in-list syntax", async () => {
    const chain = mockChain();
    vi.mocked(supabase.from).mockReturnValue(chain as never);

    await fetchCrossNicheBreakouts([10, 24, 27], 3);

    expect(chain.calls.filter((c) => c.method === "eq").map((c) => c.args)).toEqual([
      ["reference_eligible", true],
    ]);

    const notCalls = chain.calls.filter((c) => c.method === "not");
    expect(notCalls).toHaveLength(2);
    expect(notCalls[1]?.args).toEqual([
      "content_class_id",
      "in",
      "(10,24,27)",
    ]);
  });

  it("falls back without reference_eligible when eligible pool is thin", async () => {
    const calls: { method: string; args: unknown[] }[] = [];
    let limitCall = 0;
    const chain = {
      select: (...args: unknown[]) => {
        calls.push({ method: "select", args });
        return chain;
      },
      gte: (...args: unknown[]) => {
        calls.push({ method: "gte", args });
        return chain;
      },
      eq: (...args: unknown[]) => {
        calls.push({ method: "eq", args });
        return chain;
      },
      not: (...args: unknown[]) => {
        calls.push({ method: "not", args });
        return chain;
      },
      order: (...args: unknown[]) => {
        calls.push({ method: "order", args });
        return chain;
      },
      limit: (...args: unknown[]) => {
        calls.push({ method: "limit", args });
        limitCall += 1;
        const data =
          limitCall === 1
            ? [{ video_id: "eligible-only" }]
            : [{ video_id: "fallback-only" }];
        return { data, error: null };
      },
    };
    vi.mocked(supabase.from).mockReturnValue(chain as never);

    const rows = await fetchCrossNicheBreakouts([], 3);

    expect(rows.map((r) => r.video_id)).toEqual(["eligible-only", "fallback-only"]);
    expect(calls.filter((c) => c.method === "eq").map((c) => c.args)).toEqual([
      ["reference_eligible", true],
    ]);
    expect(limitCall).toBe(2);
  });
});
