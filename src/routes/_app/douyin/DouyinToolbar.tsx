import { memo } from "react";
import { Bookmark, Search } from "lucide-react";

import type {
  DouyinFilters,
  DouyinSortKey,
} from "./douyinFilters";

/**
 * D4c (2026-06-04) — Kho Douyin · toolbar.
 *
 * Search · sort · saved-only toggle. Adapt-level chips removed — creators
 * judge transferability themselves after watching + reading subs.
 */

export type DouyinToolbarProps = {
  filters: DouyinFilters;
  onFiltersChange: (next: DouyinFilters) => void;
  savedCount: number;
};

const SORT_OPTIONS: { value: DouyinSortKey; label: string }[] = [
  { value: "rise", label: "Sắp xếp: Tăng nhanh nhất" },
  { value: "views", label: "Sắp xếp: Nhiều view nhất" },
  { value: "recent", label: "Sắp xếp: Mới nhất" },
];

export const DouyinToolbar = memo(function DouyinToolbar({
  filters,
  onFiltersChange,
  savedCount,
}: DouyinToolbarProps) {
  const setSearch = (search: string) =>
    onFiltersChange({ ...filters, search });
  const setSort = (sort: DouyinSortKey) =>
    onFiltersChange({ ...filters, sort });
  const toggleSavedOnly = () =>
    onFiltersChange({ ...filters, savedOnly: !filters.savedOnly });

  return (
    <div
      className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"
      role="toolbar"
      aria-label="Bộ lọc Kho Douyin"
    >
      <label className="flex h-9 w-full items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 transition-colors hover:border-[color:var(--gv-ink-4)] focus-within:border-[color:var(--gv-accent)] focus-within:ring-2 focus-within:ring-[color:var(--gv-accent)] focus-within:ring-offset-1 lg:max-w-[280px]">
        <Search
          className="h-3.5 w-3.5 shrink-0 text-[color:var(--gv-ink-4)]"
          strokeWidth={2}
          aria-hidden
        />
        <input
          type="search"
          value={filters.search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-0 flex-1 border-none bg-transparent py-0 text-[17px] leading-none text-[color:var(--gv-ink)] outline-none placeholder:text-[color:var(--gv-ink-4)] sm:text-[12px]"
          placeholder="Tìm trong kho · tên TQ, dịch VN, ngách…"
          aria-label="Tìm trong Kho Douyin"
        />
      </label>

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={filters.sort}
          onChange={(e) => setSort(e.target.value as DouyinSortKey)}
          className="h-11 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 text-[17px] text-[color:var(--gv-ink)] outline-none transition-colors hover:border-[color:var(--gv-ink-4)] focus-visible:border-[color:var(--gv-accent)] focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-1 sm:h-8 sm:text-[12px]"
          aria-label="Sắp xếp video"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={toggleSavedOnly}
          aria-pressed={filters.savedOnly}
          className={
            "inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-[12px] transition-colors " +
            (filters.savedOnly
              ? "border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] font-semibold text-[color:var(--gv-canvas)]"
              : "border-[color:var(--gv-rule)] bg-transparent font-medium text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink-4)]")
          }
        >
          <Bookmark className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
          Kho cá nhân
          {savedCount > 0 ? (
            <span className="gv-kicker opacity-80">· {savedCount}</span>
          ) : null}
        </button>
      </div>
    </div>
  );
});
