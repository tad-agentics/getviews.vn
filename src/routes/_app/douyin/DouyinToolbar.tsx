import { memo } from "react";
import { Bookmark, Search } from "lucide-react";

import type { DouyinAdaptLevel } from "@/lib/api-types";

import { ADAPT_META } from "./DouyinVideoCard";
import type {
  DouyinAdaptFilter,
  DouyinFilters,
  DouyinSortKey,
} from "./douyinFilters";

/**
 * D4c (2026-06-04) — Kho Douyin · toolbar.
 *
 * Sits below the niche chip strip per design pack ``screens/douyin.jsx``
 * lines 626-690. Combines four controls in one row:
 *
 *   • Search input (title_vi / title_zh / handle / adapt_reason).
 *   • Adapt-level chip group (Tất cả · XANH · VÀNG · ĐỎ).
 *   • Sort select (Tăng nhanh · Nhiều view · Mới index).
 *   • "Kho cá nhân" toggle pill — narrows to the saved set.
 *
 * Pure controlled component — all state lives on ``DouyinScreen`` via
 * the ``DouyinFilters`` shape. Counts (``savedCount``) come in as props
 * so the saved-only pill can show "Kho cá nhân · 5".
 */

export type DouyinToolbarProps = {
  filters: DouyinFilters;
  onFiltersChange: (next: DouyinFilters) => void;
  /** Total saved videos across all niches; rendered next to the
   *  "Kho cá nhân" toggle for affordance. */
  savedCount: number;
};

const ADAPT_OPTIONS: { value: DouyinAdaptFilter; label: string }[] = [
  { value: "all", label: "Tất cả" },
  { value: "green", label: ADAPT_META.green.short },
  { value: "yellow", label: ADAPT_META.yellow.short },
  { value: "red", label: ADAPT_META.red.short },
];

const SORT_OPTIONS: { value: DouyinSortKey; label: string }[] = [
  { value: "rise", label: "Tăng nhanh" },
  { value: "views", label: "Nhiều view" },
  { value: "recent", label: "Mới index" },
];

export const DouyinToolbar = memo(function DouyinToolbar({
  filters,
  onFiltersChange,
  savedCount,
}: DouyinToolbarProps) {
  const setSearch = (search: string) =>
    onFiltersChange({ ...filters, search });
  const setAdapt = (adaptLevel: DouyinAdaptFilter) =>
    onFiltersChange({ ...filters, adaptLevel });
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
      {/* Search */}
      <label className="flex h-9 w-full items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 transition-colors hover:border-[color:var(--gv-ink-4)] lg:max-w-[280px]">
        <Search
          className="h-3.5 w-3.5 shrink-0 text-[color:var(--gv-ink-4)]"
          strokeWidth={2}
          aria-hidden
        />
        <input
          type="search"
          value={filters.search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-0 flex-1 border-none bg-transparent py-0 text-[12px] leading-none text-[color:var(--gv-ink)] outline-none placeholder:text-[color:var(--gv-ink-4)]"
          placeholder="Tìm tiêu đề, handle, lý do…"
          aria-label="Tìm trong Kho Douyin"
        />
      </label>

      <div className="flex flex-wrap items-center gap-2">
        {/* Adapt-level chips */}
        <div
          className="flex items-center gap-1.5"
          role="group"
          aria-label="Lọc theo mức độ adapt"
        >
          {ADAPT_OPTIONS.map((opt) => (
            <AdaptChip
              key={opt.value}
              active={filters.adaptLevel === opt.value}
              level={opt.value === "all" ? null : (opt.value as DouyinAdaptLevel)}
              label={opt.label}
              onClick={() => setAdapt(opt.value)}
            />
          ))}
        </div>

        {/* Sort */}
        <label className="flex items-center gap-1.5">
          <span className="gv-mono text-[10px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-4)]">
            Sắp xếp
          </span>
          <select
            value={filters.sort}
            onChange={(e) => setSort(e.target.value as DouyinSortKey)}
            className="h-8 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 text-[12px] text-[color:var(--gv-ink)] outline-none transition-colors hover:border-[color:var(--gv-ink-4)]"
            aria-label="Sắp xếp video"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        {/* Saved-only toggle */}
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
            <span className="gv-mono text-[10px] opacity-80">· {savedCount}</span>
          ) : null}
        </button>
      </div>
    </div>
  );
});


function AdaptChip({
  active,
  level,
  label,
  onClick,
}: {
  active: boolean;
  /** ``null`` for the "Tất cả" chip — uses neutral tone classes. */
  level: DouyinAdaptLevel | null;
  label: string;
  onClick: () => void;
}) {
  const meta = level ? ADAPT_META[level] : null;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      data-adapt-level={level ?? "all"}
      className={
        "gv-mono inline-flex h-8 items-center gap-1 rounded-full border px-3 text-[10px] font-semibold uppercase tracking-[0.05em] transition-colors " +
        (active
          ? meta
            ? meta.toneClass
            : "border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
          : "border-[color:var(--gv-rule)] bg-transparent text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink-4)]")
      }
    >
      {meta ? (
        <span aria-hidden className="block h-1 w-1 rounded-full bg-current" />
      ) : null}
      {label}
    </button>
  );
}
