import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_CORPUS_BROWSE_CLASS_FIRST: false,
    VITE_CORPUS_BROWSE_CLASS_ONLY: false,
  },
}));

vi.mock("@/lib/supabase", () => ({
  supabase: { from: vi.fn() },
}));

import { env } from "@/lib/env";
import {
  applyVideoCorpusNicheFilter,
  CORPUS_CLASS_FIRST_MIN_AGGREGATE_SAMPLE,
  shouldUseClassFirstBrowse,
  shouldUseClassOnlyBrowse,
} from "./corpusNicheFilter";

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

describe("shouldUseClassFirstBrowse", () => {
  afterEach(() => {
    env.VITE_CORPUS_BROWSE_CLASS_FIRST = false;
    env.VITE_CORPUS_BROWSE_CLASS_ONLY = false;
  });

  it("returns false when flag off", () => {
    expect(
      shouldUseClassFirstBrowse({ contentClassIds: [1, 2] }, CORPUS_CLASS_FIRST_MIN_AGGREGATE_SAMPLE),
    ).toBe(false);
  });

  it("returns true when flag on and aggregate meets floor", () => {
    env.VITE_CORPUS_BROWSE_CLASS_FIRST = true;
    expect(
      shouldUseClassFirstBrowse({ contentClassIds: [1, 2] }, CORPUS_CLASS_FIRST_MIN_AGGREGATE_SAMPLE),
    ).toBe(true);
  });

  it("returns false when aggregate below floor", () => {
    env.VITE_CORPUS_BROWSE_CLASS_FIRST = true;
    expect(
      shouldUseClassFirstBrowse(
        { contentClassIds: [1] },
        CORPUS_CLASS_FIRST_MIN_AGGREGATE_SAMPLE - 1,
      ),
    ).toBe(false);
  });

  it("CLASS_ONLY forces class-first regardless of sample", () => {
    env.VITE_CORPUS_BROWSE_CLASS_ONLY = true;
    expect(shouldUseClassFirstBrowse({ contentClassIds: [3] }, 0)).toBe(true);
    expect(shouldUseClassOnlyBrowse({ contentClassIds: [3] })).toBe(true);
  });
});

describe("applyVideoCorpusNicheFilter", () => {
  afterEach(() => {
    env.VITE_CORPUS_BROWSE_CLASS_FIRST = false;
    env.VITE_CORPUS_BROWSE_CLASS_ONLY = false;
  });

  it("applies content_class and niche_id when both provided (legacy)", () => {
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

  it("class-first skips niche_id when aggregate threshold met", () => {
    env.VITE_CORPUS_BROWSE_CLASS_FIRST = true;
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, {
      legacyNicheId: 28,
      contentClassIds: [10, 11],
      aggregateSampleSize: CORPUS_CLASS_FIRST_MIN_AGGREGATE_SAMPLE,
    });
    expect(q.calls).toEqual([{ op: "in", col: "content_class_id", val: [10, 11] }]);
  });

  it("CLASS_ONLY filters content_class_id only", () => {
    env.VITE_CORPUS_BROWSE_CLASS_ONLY = true;
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, {
      legacyNicheId: 27,
      contentClassIds: [5, 6],
    });
    expect(q.calls).toEqual([{ op: "in", col: "content_class_id", val: [5, 6] }]);
  });
});
