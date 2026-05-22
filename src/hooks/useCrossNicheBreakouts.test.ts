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
      return { data: [], error: null, calls };
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

    const notCalls = chain.calls.filter((c) => c.method === "not");
    expect(notCalls).toHaveLength(1);
    expect(notCalls[0]?.args).toEqual(["content_class_id", "is", null]);
  });

  it("excludes junction classes via PostgREST in-list syntax", async () => {
    const chain = mockChain();
    vi.mocked(supabase.from).mockReturnValue(chain as never);

    await fetchCrossNicheBreakouts([10, 24, 27], 3);

    const notCalls = chain.calls.filter((c) => c.method === "not");
    expect(notCalls).toHaveLength(2);
    expect(notCalls[1]?.args).toEqual([
      "content_class_id",
      "in",
      "(10,24,27)",
    ]);
  });
});
