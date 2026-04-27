import type { DouyinAdaptLevel, DouyinVideo } from "@/lib/api-types";

/**
 * D4c (2026-06-04) — Kho Douyin · pure filter + sort module.
 *
 * Owns the toolbar state shape and the deterministic transforms that
 * turn ``allVideos`` → ``visibleVideos``. Kept free of React so the
 * sort/filter logic is unit-testable in isolation and can be reused by
 * the modal (D4d) for "next / prev within filter" navigation.
 *
 * Design pack reference: ``screens/douyin.jsx`` lines 626-690 — toolbar
 * row sits below the niche chip strip and combines:
 *   • Search input (matches title_vi / title_zh / creator_handle /
 *     adapt_reason — case-insensitive substring).
 *   • Adapt-level filter chips (XANH / VÀNG / ĐỎ + "Tất cả").
 *   • Sort dropdown (rise / views / recent).
 *   • "Kho cá nhân" toggle — narrows to ``saved`` ids only.
 */

/** UI sort options. Maps to a stable sort key so two videos with the
 *  same primary value preserve corpus insertion order. */
export type DouyinSortKey = "rise" | "views" | "recent";

/** Adapt-level filter chip selection. ``"all"`` means no filter. */
export type DouyinAdaptFilter = "all" | DouyinAdaptLevel;

export type DouyinFilters = {
  /** ``null`` → all niches. Otherwise the slug of an active chip. */
  nicheSlug: string | null;
  /** Free-text search — empty string means no filter. Lower-cased
   *  before matching. */
  search: string;
  adaptLevel: DouyinAdaptFilter;
  sort: DouyinSortKey;
  /** When true, the grid is narrowed to videos whose ``video_id`` is in
   *  the parent's localStorage saved set. */
  savedOnly: boolean;
};

export const INITIAL_FILTERS: DouyinFilters = {
  nicheSlug: null,
  search: "",
  adaptLevel: "all",
  sort: "rise",
  savedOnly: false,
};

/** True when any field deviates from ``INITIAL_FILTERS`` — drives the
 *  "Xoá bộ lọc" link visibility. */
export function hasAnyFilter(filters: DouyinFilters): boolean {
  return (
    filters.nicheSlug !== null ||
    filters.search.trim().length > 0 ||
    filters.adaptLevel !== "all" ||
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
    video.adapt_reason,
  ]
    .filter((s): s is string => typeof s === "string" && s.length > 0)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

function _matchesAdapt(video: DouyinVideo, level: DouyinAdaptFilter): boolean {
  if (level === "all") return true;
  // NULL adapt_level (synth-pending) is intentionally excluded from
  // every adapt-level chip — those rows still show under "Tất cả".
  return video.adapt_level === level;
}

/**
 * Apply niche / search / adapt / saved-only filters. ``savedIds`` is a
 * caller-supplied set so this function stays decoupled from the
 * localStorage hook.
 */
export function applyFilters(
  videos: DouyinVideo[],
  filters: DouyinFilters,
  context: {
    /** Lookup from chip slug to niche_id. */
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
    if (!_matchesAdapt(v, filters.adaptLevel)) return false;
    if (!_matchesSearch(v, q)) return false;
    return true;
  });
}

/**
 * Stable sort. ``rise`` and ``views`` are descending numeric. ``recent``
 * is descending by ``indexed_at``; rows missing ``indexed_at`` sort to
 * the end. Returns a new array — the input is not mutated.
 */
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

/** Convenience — apply both filter + sort in one pass. */
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
