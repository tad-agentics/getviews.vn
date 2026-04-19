import type { ReactNode } from "react";
import type { KolBrowseRow } from "@/lib/api-types";

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

const AVATAR_BG = [
  "bg-[color:var(--gv-accent)]",
  "bg-[color:var(--gv-ink-2)]",
  "bg-[color:var(--gv-pos-deep)]",
  "bg-[color:var(--gv-neg-deep)]",
  "[background:var(--gv-lime)]",
  "bg-[color:color-mix(in_srgb,var(--gv-accent)_55%,var(--gv-ink)_45%)]",
] as const;

function formatCompactVi(n: number): string {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}M`;
  }
  if (n >= 1_000) {
    return `${(n / 1_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}K`;
  }
  return n.toLocaleString("vi-VN");
}

function growthLabel(pct: number): string {
  if (pct === 0) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${Math.round(pct * 100)}%`;
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
  return (
    <div>
      <div
        className="grid grid-cols-[40px_minmax(0,2fr)_100px_100px_100px_80px] items-center gap-x-2 border-b border-[color:var(--gv-ink)] px-[18px] py-2.5"
        role="row"
      >
        {COLS.map((c) => (
          <button
            key={c.key}
            type="button"
            role="columnheader"
            className="gv-mono text-left text-[9px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)] hover:text-[color:var(--gv-ink-3)]"
            onClick={() => onSort(c.key)}
          >
            {c.label}
            {sortKey === c.key ? (sortDir === "asc" ? " ·↑" : " ·↓") : ""}
          </button>
        ))}
      </div>
      {rows.map((row, i) => {
        const letter = (row.name || row.handle || "?").charAt(0).toUpperCase();
        const bg = AVATAR_BG[i % AVATAR_BG.length];
        const showGhim = row.is_pinned && tab === "discover";
        return (
          <button
            key={row.handle}
            type="button"
            role="row"
            onClick={() => onSelect(row.handle)}
            className={
              "grid w-full grid-cols-[40px_minmax(0,2fr)_100px_100px_100px_80px] items-center gap-x-2 border-b border-[color:var(--gv-rule)] px-[18px] py-3.5 text-left transition-colors " +
              (selectedHandle === row.handle ? "bg-[color:var(--gv-paper)]" : "hover:bg-[color:var(--gv-canvas-2)]")
            }
          >
            <span className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div className="flex min-w-0 items-center gap-3">
              <div
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[15px] font-medium text-[color:var(--gv-canvas)] ${bg}`}
              >
                {letter}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="gv-tight truncate text-[13px] text-[color:var(--gv-ink)]">{row.name}</span>
                  {showGhim ? (
                    <span className="gv-mono shrink-0 rounded px-1 py-px text-[8px] font-bold uppercase tracking-[0.1em] text-[color:var(--gv-accent-deep)] [background:var(--gv-accent-soft)]">
                      GHIM
                    </span>
                  ) : null}
                </div>
                <div className="gv-mono truncate text-[10px] text-[color:var(--gv-ink-4)]">
                  @{row.handle}
                  {row.tone ? ` · ${row.tone}` : ""}
                </div>
              </div>
            </div>
            <span className="gv-mono text-xs text-[color:var(--gv-ink)]">{formatCompactVi(row.followers)}</span>
            <span className="gv-mono text-xs text-[color:var(--gv-ink)]">{formatCompactVi(row.avg_views)}</span>
            <span className="gv-mono text-xs font-semibold text-[color:var(--gv-pos-deep)]">{growthLabel(row.growth_30d_pct)}</span>
            <div className="min-w-0">{renderMatch(row)}</div>
          </button>
        );
      })}
    </div>
  );
}
