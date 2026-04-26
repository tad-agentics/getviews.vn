import { memo } from "react";
import type { NicheWithHot } from "@/hooks/useTopNiches";

/**
 * Trends — NGÁCH BẠN THEO DÕI tab strip (PR-T1).
 *
 * Sits above the Trends hero. When the creator follows ≥ 2 niches, this
 * row lets them pivot the whole page (hero, pattern grid, video grid,
 * rail) to a different niche without leaving Trends.
 *
 * Mirrors design pack ``screens/trends.jsx`` lines 298-328 — mono uc
 * kicker on the left, tab buttons with an ink underline on the active
 * tab, ``+ ĐỔI NGÁCH ĐANG THEO DÕI`` link on the right that routes to
 * Settings.
 *
 * Hidden when ``niches.length < 2`` — single-niche profiles don't need
 * a switcher; the URL ``?niche=N`` param already pins the view.
 */

export const TrendsNicheTabs = memo(function TrendsNicheTabs({
  niches,
  selectedNicheId,
  onSelectNiche,
  onEditNiches,
}: {
  niches: ReadonlyArray<NicheWithHot>;
  selectedNicheId: number | null;
  onSelectNiche: (id: number) => void;
  onEditNiches: () => void;
}) {
  if (niches.length < 2) return null;

  return (
    <div
      className="mb-6 flex flex-wrap items-end gap-x-2 gap-y-1 border-b border-[color:var(--gv-rule)]"
      role="tablist"
      aria-label="Ngách bạn theo dõi"
    >
      <span className="gv-mono mr-3 pb-3 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        NGÁCH BẠN THEO DÕI
      </span>
      {niches.map((n) => {
        const isActive = n.id === selectedNicheId;
        return (
          <button
            key={n.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onSelectNiche(n.id)}
            className={
              "-mb-px border-b-2 px-3 py-2.5 text-[14px] transition-colors " +
              (isActive
                ? "border-[color:var(--gv-ink)] font-semibold text-[color:var(--gv-ink)]"
                : "border-transparent font-medium text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)]")
            }
          >
            {n.name}
          </button>
        );
      })}
      <span className="ml-auto" />
      <button
        type="button"
        onClick={onEditNiches}
        className="gv-mono pb-3 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)] transition-colors hover:text-[color:var(--gv-ink)]"
      >
        + Đổi ngách đang theo dõi
      </button>
    </div>
  );
});
