import { memo } from "react";

import type { DouyinNiche } from "@/lib/api-types";

/**
 * D4b (2026-06-04) — Kho Douyin niche filter chips.
 *
 * Per design pack ``screens/douyin.jsx`` lines 611-626: horizontal
 * scrolling row of pill chips, leading "Tất cả" + 1 chip per active
 * niche. Active state uses ink bg / canvas text. Passing
 * ``activeSlug=null`` highlights "Tất cả".
 *
 * D4c lands the toolbar (search + adapt-level filter + sort + saved-
 * only) below this strip.
 */

const ALL_SLUG = "__all__";

export type DouyinNicheChipsProps = {
  niches: DouyinNiche[];
  activeSlug: string | null;
  onSelect: (slug: string | null) => void;
};

export const DouyinNicheChips = memo(function DouyinNicheChips({
  niches,
  activeSlug,
  onSelect,
}: DouyinNicheChipsProps) {
  const isAllActive = activeSlug === null;

  return (
    <nav
      aria-label="Lọc theo ngách"
      className="mb-5 flex items-center gap-1.5 overflow-x-auto border-b border-[color:var(--gv-rule)] pb-3.5"
    >
      <Chip
        label="Tất cả"
        active={isAllActive}
        onClick={() => onSelect(null)}
        slugForKey={ALL_SLUG}
      />
      {niches.map((niche) => (
        <Chip
          key={niche.slug}
          label={niche.name_vn}
          active={activeSlug === niche.slug}
          onClick={() => onSelect(niche.slug)}
          slugForKey={niche.slug}
        />
      ))}
    </nav>
  );
});

function Chip({
  label,
  active,
  onClick,
  slugForKey,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  slugForKey: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      data-niche-slug={slugForKey}
      className={
        "shrink-0 whitespace-nowrap rounded-full px-3 py-1.5 text-[12px] transition-colors duration-[120ms] " +
        (active
          ? "border border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] font-semibold text-[color:var(--gv-canvas)]"
          : "border border-[color:var(--gv-rule)] bg-transparent font-medium text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink-4)]")
      }
    >
      {label}
    </button>
  );
}
