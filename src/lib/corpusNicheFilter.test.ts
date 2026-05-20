import { describe, expect, it } from "vitest";
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
  it("applies content_class and niche_id when both provided", () => {
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, {
      legacyNicheId: 28,
      contentClassIds: [28, 29],
    });
    expect(q.calls).toEqual([
      { op: "in", col: "content_class_id", val: [28, 29] },
      { op: "eq", col: "niche_id", val: 28 },
    ]);
  });

  it("falls back to niche_id only when no content classes", () => {
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, { legacyNicheId: 27, contentClassIds: [] });
    expect(q.calls).toEqual([{ op: "eq", col: "niche_id", val: 27 }]);
  });
});
