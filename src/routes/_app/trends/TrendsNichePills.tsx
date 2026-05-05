import { memo, useMemo } from "react";

/**
 * Trends niche filter pills (PR4 of single-niche refactor, 2026-05-05).
 *
 * Uniform pill row across the full taxonomy — no special "Của tôi" pill;
 * the user's niche is the default selected pill on mount, which is enough
 * self-documentation. Alphabetical order so users can scan to a known
 * label quickly. Selection is mandatory (no "Tất cả" affordance) since
 * the Trends queries downstream are gated by ``niche_id`` and the
 * design pack treats Xu hướng as a niche-scoped surface.
 *
 * ``niches`` shape matches ``useNicheTaxonomy()`` output — the hook
 * already runs ``resolveNicheNameVn`` so labels are migration-safe.
 */

export type TrendsNichePillsProps = {
  niches: ReadonlyArray<{ id: number; name: string }>;
  activeId: number | null;
  onSelect: (id: number) => void;
  /** Disables interaction while taxonomy/profile is still loading. */
  disabled?: boolean;
};

export const TrendsNichePills = memo(function TrendsNichePills({
  niches,
  activeId,
  onSelect,
  disabled,
}: TrendsNichePillsProps) {
  const sorted = useMemo(() => {
    const out = [...niches];
    // Locale-aware Vietnamese alphabetical sort (handles diacritics).
    out.sort((a, b) => a.name.localeCompare(b.name, "vi"));
    return out;
  }, [niches]);

  if (sorted.length === 0) return null;

  return (
    <nav
      aria-label="Lọc xu hướng theo ngách"
      className="mb-5 flex items-center gap-1.5 overflow-x-auto border-b border-[color:var(--gv-rule)] pb-3.5"
    >
      {sorted.map((n) => (
        <Pill
          key={n.id}
          label={n.name}
          active={activeId === n.id}
          disabled={disabled}
          onClick={() => onSelect(n.id)}
        />
      ))}
    </nav>
  );
});

function Pill({
  label,
  active,
  disabled,
  onClick,
}: {
  label: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={
        "shrink-0 whitespace-nowrap rounded-full px-3 py-1.5 text-[12px] transition-colors duration-[120ms] disabled:opacity-50 " +
        (active
          ? "border border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] font-semibold text-[color:var(--gv-canvas)]"
          : "border border-[color:var(--gv-rule)] bg-transparent font-medium text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink-4)]")
      }
    >
      {label}
    </button>
  );
}
