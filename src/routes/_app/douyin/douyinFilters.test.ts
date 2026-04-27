/**
 * D4c (2026-06-04) — Pure filter + sort transform tests.
 */

import { describe, expect, it } from "vitest";

import type { DouyinVideo } from "@/lib/api-types";

import {
  INITIAL_FILTERS,
  applyFilters,
  applyFiltersAndSort,
  hasAnyFilter,
  sortVideos,
} from "./douyinFilters";


function _video(overrides: Partial<DouyinVideo> = {}): DouyinVideo {
  return {
    video_id: "v1",
    douyin_url: null,
    niche_id: 1,
    creator_handle: "alice",
    creator_name: "Alice",
    thumbnail_url: null,
    video_url: null,
    video_duration: 30,
    views: 100_000,
    likes: 0,
    saves: 0,
    engagement_rate: 0,
    posted_at: null,
    title_zh: "睡前",
    title_vi: "Trước khi ngủ",
    sub_vi: null,
    hashtags_zh: [],
    adapt_level: "green",
    adapt_reason: null,
    eta_weeks_min: null,
    eta_weeks_max: null,
    cn_rise_pct: null,
    translator_notes: [],
    synth_computed_at: null,
    indexed_at: null,
    ...overrides,
  };
}


// Use 2-tier slug→id map so tests don't depend on real niche IDs.
const slugToNicheId = (slug: string): number | null => {
  if (slug === "wellness") return 1;
  if (slug === "tech") return 2;
  return null;
};


describe("douyinFilters · hasAnyFilter", () => {
  it("returns false on INITIAL_FILTERS", () => {
    expect(hasAnyFilter(INITIAL_FILTERS)).toBe(false);
  });

  it("returns true when any field deviates", () => {
    expect(hasAnyFilter({ ...INITIAL_FILTERS, nicheSlug: "tech" })).toBe(true);
    expect(hasAnyFilter({ ...INITIAL_FILTERS, search: "abc" })).toBe(true);
    expect(hasAnyFilter({ ...INITIAL_FILTERS, adaptLevel: "green" })).toBe(true);
    expect(hasAnyFilter({ ...INITIAL_FILTERS, sort: "views" })).toBe(true);
    expect(hasAnyFilter({ ...INITIAL_FILTERS, savedOnly: true })).toBe(true);
  });

  it("treats whitespace-only search as no filter", () => {
    expect(hasAnyFilter({ ...INITIAL_FILTERS, search: "   " })).toBe(false);
  });
});


describe("douyinFilters · applyFilters", () => {
  const videos = [
    _video({ video_id: "w1", niche_id: 1, title_vi: "Wellness video", adapt_level: "green" }),
    _video({ video_id: "w2", niche_id: 1, title_vi: "Yoga buổi sáng", adapt_level: "yellow" }),
    _video({ video_id: "t1", niche_id: 2, title_vi: "Test iPhone", adapt_level: "green", creator_handle: "techguy" }),
    _video({ video_id: "p1", niche_id: 2, title_vi: "Pending", adapt_level: null }),
  ];

  it("returns all videos under INITIAL_FILTERS", () => {
    const out = applyFilters(videos, INITIAL_FILTERS, {
      slugToNicheId,
      savedIds: new Set(),
    });
    expect(out.map((v) => v.video_id)).toEqual(["w1", "w2", "t1", "p1"]);
  });

  it("filters by niche slug", () => {
    const out = applyFilters(
      videos,
      { ...INITIAL_FILTERS, nicheSlug: "tech" },
      { slugToNicheId, savedIds: new Set() },
    );
    expect(out.map((v) => v.video_id)).toEqual(["t1", "p1"]);
  });

  it("returns all videos when nicheSlug is unknown", () => {
    // unknown slug → slugToNicheId returns null → no niche filter
    const out = applyFilters(
      videos,
      { ...INITIAL_FILTERS, nicheSlug: "ghost" },
      { slugToNicheId, savedIds: new Set() },
    );
    expect(out).toHaveLength(4);
  });

  it("filters by adapt level — pending rows are excluded from level chips", () => {
    const greenOnly = applyFilters(
      videos,
      { ...INITIAL_FILTERS, adaptLevel: "green" },
      { slugToNicheId, savedIds: new Set() },
    );
    expect(greenOnly.map((v) => v.video_id)).toEqual(["w1", "t1"]);

    const yellowOnly = applyFilters(
      videos,
      { ...INITIAL_FILTERS, adaptLevel: "yellow" },
      { slugToNicheId, savedIds: new Set() },
    );
    expect(yellowOnly.map((v) => v.video_id)).toEqual(["w2"]);
  });

  it("filters by case-insensitive substring across title_vi / title_zh / creator_handle / adapt_reason", () => {
    const yogaOnly = applyFilters(
      videos,
      { ...INITIAL_FILTERS, search: "YOGA" },
      { slugToNicheId, savedIds: new Set() },
    );
    expect(yogaOnly.map((v) => v.video_id)).toEqual(["w2"]);

    const handleHit = applyFilters(
      videos,
      { ...INITIAL_FILTERS, search: "techguy" },
      { slugToNicheId, savedIds: new Set() },
    );
    expect(handleHit.map((v) => v.video_id)).toEqual(["t1"]);
  });

  it("savedOnly narrows to the saved set", () => {
    const out = applyFilters(
      videos,
      { ...INITIAL_FILTERS, savedOnly: true },
      { slugToNicheId, savedIds: new Set(["w1", "p1"]) },
    );
    expect(out.map((v) => v.video_id)).toEqual(["w1", "p1"]);
  });

  it("composes filters AND-style (niche + adapt + search)", () => {
    const out = applyFilters(
      videos,
      {
        ...INITIAL_FILTERS,
        nicheSlug: "tech",
        adaptLevel: "green",
        search: "iphone",
      },
      { slugToNicheId, savedIds: new Set() },
    );
    expect(out.map((v) => v.video_id)).toEqual(["t1"]);
  });
});


describe("douyinFilters · sortVideos", () => {
  it("sorts by cn_rise_pct DESC (null → end)", () => {
    const videos = [
      _video({ video_id: "a", cn_rise_pct: 10 }),
      _video({ video_id: "b", cn_rise_pct: 50 }),
      _video({ video_id: "c", cn_rise_pct: null }),
      _video({ video_id: "d", cn_rise_pct: 30 }),
    ];
    expect(sortVideos(videos, "rise").map((v) => v.video_id)).toEqual([
      "b",
      "d",
      "a",
      "c",
    ]);
  });

  it("sorts by views DESC", () => {
    const videos = [
      _video({ video_id: "a", views: 100 }),
      _video({ video_id: "b", views: 1_000 }),
      _video({ video_id: "c", views: 10 }),
    ];
    expect(sortVideos(videos, "views").map((v) => v.video_id)).toEqual([
      "b",
      "a",
      "c",
    ]);
  });

  it("sorts by indexed_at DESC; null indexed_at lands at the end", () => {
    const videos = [
      _video({ video_id: "old", indexed_at: "2026-05-01T00:00:00Z" }),
      _video({ video_id: "new", indexed_at: "2026-06-01T00:00:00Z" }),
      _video({ video_id: "miss", indexed_at: null }),
      _video({ video_id: "mid", indexed_at: "2026-05-15T00:00:00Z" }),
    ];
    expect(sortVideos(videos, "recent").map((v) => v.video_id)).toEqual([
      "new",
      "mid",
      "old",
      "miss",
    ]);
  });

  it("does not mutate the input array", () => {
    const videos = [
      _video({ video_id: "a", views: 1 }),
      _video({ video_id: "b", views: 2 }),
    ];
    const before = videos.map((v) => v.video_id);
    sortVideos(videos, "views");
    expect(videos.map((v) => v.video_id)).toEqual(before);
  });
});


describe("douyinFilters · applyFiltersAndSort", () => {
  it("filters first, then sorts the survivors", () => {
    const videos = [
      _video({ video_id: "w1", niche_id: 1, adapt_level: "green", cn_rise_pct: 80 }),
      _video({ video_id: "w2", niche_id: 1, adapt_level: "yellow", cn_rise_pct: 90 }),
      _video({ video_id: "w3", niche_id: 1, adapt_level: "green", cn_rise_pct: 50 }),
    ];
    const out = applyFiltersAndSort(
      videos,
      { ...INITIAL_FILTERS, adaptLevel: "green", sort: "rise" },
      { slugToNicheId, savedIds: new Set() },
    );
    expect(out.map((v) => v.video_id)).toEqual(["w1", "w3"]);
  });
});
