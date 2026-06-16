import type { DouyinVideo } from "@/lib/api-types";

/**
 * D4c (2026-06-04) — Kho Douyin · pure filter + sort module.
 */

export type DouyinSortKey = "rise" | "views" | "recent";

export type DouyinFilters = {
  nicheSlug: string | null;
  search: string;
  sort: DouyinSortKey;
  savedOnly: boolean;
};

export const INITIAL_FILTERS: DouyinFilters = {
  nicheSlug: null,
  search: "",
  sort: "rise",
  savedOnly: false,
};

export function hasAnyFilter(filters: DouyinFilters): boolean {
  return (
    filters.nicheSlug !== null ||
    filters.search.trim().length > 0 ||
    filters.sort !== INITIAL_FILTERS.sort ||
    filters.savedOnly
  );
}

function _matchesSearch(video: DouyinVideo, q: string): boolean {
  if (!q) return true;
  const haystack = [
    video.title_vi,
    video.title_zh,
    video.creator_handle,
    video.creator_name,
  ]
    .filter((s): s is string => typeof s === "string" && s.length > 0)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

export function applyFilters(
  videos: DouyinVideo[],
  filters: DouyinFilters,
  context: {
    slugToNicheId: (slug: string) => number | null;
    savedIds: Set<string>;
  },
): DouyinVideo[] {
  const q = filters.search.trim().toLowerCase();
  const activeNicheId =
    filters.nicheSlug !== null ? context.slugToNicheId(filters.nicheSlug) : null;

  return videos.filter((v) => {
    if (filters.savedOnly && !context.savedIds.has(v.video_id)) return false;
    if (activeNicheId != null && v.niche_id !== activeNicheId) return false;
    if (!_matchesSearch(v, q)) return false;
    return true;
  });
}

export function sortVideos(
  videos: DouyinVideo[],
  sort: DouyinSortKey,
): DouyinVideo[] {
  const arr = [...videos];
  if (sort === "rise") {
    arr.sort((a, b) => (b.cn_rise_pct ?? -1) - (a.cn_rise_pct ?? -1));
  } else if (sort === "views") {
    arr.sort((a, b) => (b.views ?? 0) - (a.views ?? 0));
  } else {
    arr.sort((a, b) => {
      const ta = a.indexed_at ? Date.parse(a.indexed_at) : NaN;
      const tb = b.indexed_at ? Date.parse(b.indexed_at) : NaN;
      const va = Number.isNaN(ta) ? -Infinity : ta;
      const vb = Number.isNaN(tb) ? -Infinity : tb;
      return vb - va;
    });
  }
  return arr;
}

export function applyFiltersAndSort(
  videos: DouyinVideo[],
  filters: DouyinFilters,
  context: {
    slugToNicheId: (slug: string) => number | null;
    savedIds: Set<string>;
  },
): DouyinVideo[] {
  return sortVideos(applyFilters(videos, filters, context), filters.sort);
}
