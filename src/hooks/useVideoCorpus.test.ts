/**
 * corpusKeys — registry consistency regression.
 *
 * The Explore screen previously defined its `breakout_videos` + `corpus_count`
 * keys inline via `useQuery({ queryKey: [...] })`, divorced from the
 * `corpusKeys` registry that the rest of the app uses. Two separate screens
 * asking for the same breakout data therefore defined two divergent keys,
 * making cache invalidation on new corpus writes impossible. This test locks
 * the registry shape so future consumers are forced to go through it.
 */
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
  },
}));

vi.mock("@/lib/supabase", () => ({
  supabase: { auth: { getSession: vi.fn() } },
}));

import { corpusKeys } from "./useVideoCorpus";

describe("corpusKeys registry", () => {
  it("namespaces every key under ['video_corpus']", () => {
    expect(corpusKeys.all()[0]).toBe("video_corpus");
    expect(corpusKeys.list({ nicheId: 1 })[0]).toBe("video_corpus");
    expect(corpusKeys.detail("abc")[0]).toBe("video_corpus");
    expect(corpusKeys.related("vid-1", 2)[0]).toBe("video_corpus");
    expect(corpusKeys.breakout(1)[0]).toBe("video_corpus");
    expect(corpusKeys.count({ nicheId: 1 })[0]).toBe("video_corpus");
  });

  it("breakout keys split the cache by nicheId so two niches don't collide", () => {
    const k1 = corpusKeys.breakout(1);
    const k2 = corpusKeys.breakout(2);
    expect(JSON.stringify(k1)).not.toBe(JSON.stringify(k2));
  });

  it("breakout accepts null for the 'no niche selected' branch", () => {
    expect(() => corpusKeys.breakout(null)).not.toThrow();
    const key = corpusKeys.breakout(null);
    expect(key[key.length - 1]).toBeNull();
  });

  it("count is keyed on the full filter combo so filter changes miss cache", () => {
    const kA = corpusKeys.count({ nicheId: 1, search: "abc" });
    const kB = corpusKeys.count({ nicheId: 1, search: "xyz" });
    const kC = corpusKeys.count({ nicheId: 2, search: "abc" });
    expect(JSON.stringify(kA)).not.toBe(JSON.stringify(kB));
    expect(JSON.stringify(kA)).not.toBe(JSON.stringify(kC));
  });

  it("list and count keys are distinct even for the same filter object", () => {
    const filters = { nicheId: 1, search: "abc" };
    expect(JSON.stringify(corpusKeys.list(filters))).not.toBe(
      JSON.stringify(corpusKeys.count(filters)),
    );
  });
});
