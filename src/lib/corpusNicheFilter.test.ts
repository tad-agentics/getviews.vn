import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase", () => ({
  supabase: { from: vi.fn() },
}));

import {
  applyBrowsableCorpusFilter,
  applyCarouselTopicGuard,
  applyVideoCorpusNicheFilter,
  CAROUSEL_FORMAT_CLASS_IDS,
  fetchContentClassIdsForCreatorNiche,
} from "./corpusNicheFilter";
import { supabase } from "./supabase";

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
    not(col: string, operator: string, val: null) {
      calls.push({ op: "not", col, val: operator });
      return q;
    },
    or(filter: string) {
      calls.push({ op: "or", col: "postgrest", val: filter });
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

  it("applies no filter when junction is empty (Phase C)", () => {
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, { legacyNicheId: 27, contentClassIds: [] });
    expect(q.calls).toEqual([]);
  });

  it("applies no filter when scope is empty", () => {
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, { legacyNicheId: null, contentClassIds: [] });
    expect(q.calls).toEqual([]);
  });

  it("requires inferred_creator_niche_id for HI-16 carousel format classes", () => {
    const q = mockQuery();
    applyVideoCorpusNicheFilter(q, {
      contentClassIds: [10, 75],
      creatorNicheId: 15,
    });
    expect(q.calls[0]).toEqual({ op: "in", col: "content_class_id", val: [10, 75] });
    expect(q.calls[1]?.op).toBe("or");
    expect(String(q.calls[1]?.val)).toContain("inferred_creator_niche_id.eq.15");
    expect(String(q.calls[1]?.val)).toContain(CAROUSEL_FORMAT_CLASS_IDS.join(","));
  });
});

describe("applyCarouselTopicGuard", () => {
  it("builds postgrest or filter for carousel format class ids", () => {
    const q = mockQuery();
    applyCarouselTopicGuard(q, 8);
    expect(q.calls).toEqual([
      {
        op: "or",
        col: "postgrest",
        val: "content_class_id.not.in.(75,76,77,78,79),inferred_creator_niche_id.eq.8",
      },
    ]);
  });
});

describe("applyBrowsableCorpusFilter", () => {
  it("excludes rows with null thumbnail_url", () => {
    const q = mockQuery();
    applyBrowsableCorpusFilter(q);
    expect(q.calls).toEqual([{ op: "not", col: "thumbnail_url", val: "is" }]);
  });
});

describe("fetchContentClassIdsForCreatorNiche", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads all junction content_class_id rows without is_primary filter by default", async () => {
    const eq = vi.fn().mockReturnThis();
    const select = vi.fn().mockReturnValue({ eq });
    vi.mocked(supabase.from).mockReturnValue({ select } as never);
    eq.mockResolvedValue({
      data: [
        { content_class_id: 1 },
        { content_class_id: 2 },
      ],
      error: null,
    });

    const ids = await fetchContentClassIdsForCreatorNiche(4);

    expect(supabase.from).toHaveBeenCalledWith("creator_niche_content_classes");
    expect(select).toHaveBeenCalledWith("content_class_id");
    expect(eq).toHaveBeenCalledWith("creator_niche_id", 4);
    expect(eq).toHaveBeenCalledTimes(1);
    expect(ids).toEqual([1, 2]);
  });

  it("filters is_primary when primaryOnly is true (Morning Signal scope)", async () => {
    const result = { data: [{ content_class_id: 16 }], error: null };
    const builder = {
      eq: vi.fn(),
      then(onFulfilled: (v: typeof result) => void) {
        onFulfilled(result);
        return Promise.resolve();
      },
    };
    builder.eq.mockReturnValue(builder);
    const select = vi.fn().mockReturnValue(builder);
    vi.mocked(supabase.from).mockReturnValue({ select } as never);

    const ids = await fetchContentClassIdsForCreatorNiche(4, { primaryOnly: true });

    expect(builder.eq).toHaveBeenCalledWith("creator_niche_id", 4);
    expect(builder.eq).toHaveBeenCalledWith("is_primary", true);
    expect(ids).toEqual([16]);
  });
});
