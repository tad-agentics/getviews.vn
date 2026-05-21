import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase", () => ({
  supabase: { from: vi.fn() },
}));

import { applyVideoCorpusNicheFilter } from "./corpusNicheFilter";

function mockQuery() {
  const calls: { op: string; col: string; val: unknown }[] = [];
  const q = {
    eq(col: string, val: number) {
      calls.push({ op: "eq", col, val });
      return q;
    },
    in(col: string, val: number[]) {
      calls.push({ op: "in", col, val });
      return q;
    },
    calls,
  };
  return q;
}

describe("applyVideoCorpusNicheFilter", () => {
  it("prefers content_class_id when junction classes exist", () => {
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, {
      legacyNicheId: 28,
      contentClassIds: [10, 11],
    });
    expect(q.calls).toEqual([{ op: "in", col: "content_class_id", val: [10, 11] }]);
  });

  it("falls back to niche_id only when no content classes", () => {
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, { legacyNicheId: 27, contentClassIds: [] });
    expect(q.calls).toEqual([{ op: "eq", col: "niche_id", val: 27 }]);
  });

  it("applies no filter when scope is empty", () => {
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, { legacyNicheId: null, contentClassIds: [] });
    expect(q.calls).toEqual([]);
  });
});
