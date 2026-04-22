import type { ReactNode } from "react";
import type { KolBrowseRow } from "@/lib/api-types";
import { kolAvatarBgClassAt } from "@/lib/kolAvatarPalette";

export type KolSortKey = "idx" | "name" | "followers" | "avg_views" | "growth" | "match";
export type KolSortDir = "asc" | "desc";

const COLS: { key: KolSortKey; label: string }[] = [
  { key: "idx", label: "#" },
  { key: "name", label: "CREATOR" },
  { key: "followers", label: "FOLLOW" },
  { key: "avg_views", label: "VIEW TB" },
  { key: "growth", label: "TĂNG 30D" },
  { key: "match", label: "MATCH" },
];

function formatCompactVi(n: number): string {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}M`;
  }
  if (n >= 1_000) {
    return `${(n / 1_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}K`;
  }
  return n.toLocaleString("vi-VN");
}

/** `growth_30d_pct` is a fractional rate (e.g. 0.12 → +12%). Zero is valid (flat proxy), not “missing”. */
function growthLabel(pct: number): string {
  if (!Number.isFinite(pct)) return "—";
  const rounded = Math.round(pct * 100);
  if (rounded === 0) return "0%";
  if (rounded > 0) return `+${rounded}%`;
  return `${rounded}%`;
}

/**
 * B.2.2 — creator grid table with client-side sortable headers.
 */
export function SortableCreatorsTable({
  rows,
  selectedHandle,
  onSelect,
  sortKey,
  sortDir,
  onSort,
  tab,
  renderMatch,
}: {
  rows: KolBrowseRow[];
  selectedHandle: string | null;
  onSelect: (handle: string) => void;
  sortKey: KolSortKey;
  sortDir: KolSortDir;
  onSort: (key: KolSortKey) => void;
  tab: "pinned" | "discover";
  renderMatch: (row: KolBrowseRow) => ReactNode;
}) {
  // Responsive column strategy — BUG-10 QA audit 2026-04-22: the CREATOR
  // column was truncating both the display name AND the @handle to ~4
  // chars on a 390px viewport because ``minmax(0, 2fr)`` + five fixed
  // 80–100px columns crushed the flexible cell to ~60px. The fix hides
  // the two lowest-value columns (VIEW TB, TĂNG 30D) on narrow widths so
  // the creator cell gets the breathing room. Every cell also carries a
  // ``title`` tooltip so power users can see the full handle on hover
  // even when the table is dense.
  const GRID_CLASS =
    "grid-cols-[32px_minmax(0,1fr)_72px_72px] min-[520px]:grid-cols-[40px_minmax(0,2fr)_90px_90px_90px] min-[820px]:grid-cols-[40px_minmax(0,2fr)_100px_100px_100px_80px]";
  const HIDE_NARROW = "hidden min-[520px]:block";
  const HIDE_MID = "hidden min-[820px]:block";
  const HIDE_CLASS_FOR_COL = (key: KolSortKey): string => {
    if (key === "avg_views") return HIDE_NARROW;
    if (key === "growth") return HIDE_MID;
    return "";
  };

  return (
    <div>
      <div
        className={`grid ${GRID_CLASS} items-center gap-x-2 border-b border-[color:var(--gv-ink)] px-[18px] py-2.5`}
        role="row"
      >
        {COLS.map((c) => (
          <button
            key={c.key}
            type="button"
            role="columnheader"
            className={
              "gv-uc text-left text-[9px] text-[color:var(--gv-ink-4)] outline-none hover:text-[color:var(--gv-ink-3)] focus-visible:text-[color:var(--gv-ink)] focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-2 " +
              HIDE_CLASS_FOR_COL(c.key)
            }
            onClick={() => onSort(c.key)}
          >
            {c.label}
            {sortKey === c.key ? (sortDir === "asc" ? " ·↑" : " ·↓") : ""}
          </button>
        ))}
      </div>
      {rows.map((row, i) => {
        const letter = (row.name || row.handle || "?").charAt(0).toUpperCase();
        const bg = kolAvatarBgClassAt(i);
        const showGhim = row.is_pinned && tab === "discover";
        const titleAttr = row.name ? `${row.name} · @${row.handle}` : `@${row.handle}`;
        return (
          <button
            key={row.handle}
            type="button"
            role="row"
            aria-selected={selectedHandle === row.handle}
            onClick={() => onSelect(row.handle)}
            title={titleAttr}
            className={
              `grid w-full ${GRID_CLASS} items-center gap-x-2 border-b border-[color:var(--gv-rule)] px-[18px] py-3.5 text-left outline-none transition-colors ` +
              (selectedHandle === row.handle
                ? "bg-[color:var(--gv-paper)] ring-1 ring-inset ring-[color:var(--gv-rule)]"
                : "hover:bg-[color:var(--gv-canvas-2)] focus-visible:bg-[color:var(--gv-canvas-2)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[color:var(--gv-accent)]")
            }
          >
            <span className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div className="flex min-w-0 items-center gap-3">
              <div
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[16px] font-medium leading-none text-[color:var(--gv-canvas)] ${bg}`}
              >
                {letter}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span
                    className="gv-tight truncate text-[13px] text-[color:var(--gv-ink)]"
                    title={row.name ?? undefined}
                  >
                    {row.name}
                  </span>
                  {showGhim ? (
                    <span className="gv-mono shrink-0 rounded px-1 py-px text-[8px] font-bold uppercase tracking-[0.1em] text-[color:var(--gv-accent-deep)] [background:var(--gv-accent-soft)]">
                      GHIM
                    </span>
                  ) : null}
                </div>
                <div
                  className="gv-mono truncate text-[10px] text-[color:var(--gv-ink-4)]"
                  title={`@${row.handle}`}
                >
                  @{row.handle}
                </div>
              </div>
            </div>
            <span className="gv-mono text-xs text-[color:var(--gv-ink)]">{formatCompactVi(row.followers)}</span>
            <span className={`gv-mono text-xs text-[color:var(--gv-ink)] ${HIDE_NARROW}`}>
              {formatCompactVi(row.avg_views)}
            </span>
            <span className={`gv-mono text-xs font-semibold text-[color:var(--gv-pos-deep)] ${HIDE_MID}`}>
              {growthLabel(row.growth_30d_pct)}
            </span>
            <div className="min-w-0">{renderMatch(row)}</div>
          </button>
        );
      })}
    </div>
  );
}
