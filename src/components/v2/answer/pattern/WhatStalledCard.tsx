import type { HookFindingData } from "@/lib/api-types";

/** Negative HookFinding row — danger rail, grey rank, ▼ delta (Phase C.2.3). */
export function WhatStalledCard({ row }: { row: HookFindingData }) {
  const deltaNeg = row.delta.numeric < 0 || row.delta.value.trim().startsWith("-");
  return (
    <div
      className="grid grid-cols-[40px_minmax(0,1fr)_auto] gap-x-3 gap-y-2 border-b border-[color:var(--gv-rule-2)] border-l-[3px] border-l-[color:var(--gv-danger)] pb-4 pl-3 last:border-b-0 last:pb-0"
      data-testid="what-stalled-card"
    >
      <div className="gv-serif text-[28px] leading-none text-[color:var(--gv-ink-4)]">#{row.rank}</div>
      <div className="min-w-0 space-y-2">
        <p className="gv-serif text-[17px] leading-snug text-[color:var(--gv-ink)]">{row.pattern}</p>
        <p className="text-[13.5px] leading-relaxed text-[color:var(--gv-ink-2)]">{row.insight}</p>
        <p className="gv-mono mt-[10px] flex flex-wrap gap-x-[14px] gap-y-1 text-[11px] text-[color:var(--gv-ink-3)]">
          <span>Xuất hiện {row.lifecycle.first_seen}</span>
          <span>·</span>
          <span>Đỉnh {row.lifecycle.peak}</span>
          <span>·</span>
          <span className="text-[color:var(--gv-ink-2)]">đang giảm</span>
        </p>
      </div>
      <div className="flex flex-col items-end gap-1 text-right">
        <div className="flex items-center gap-1">
          <span className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">RET</span>
          <span className="gv-mono text-sm font-medium text-[color:var(--gv-ink)]">{row.retention.value}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="gv-mono text-[10px] text-[color:var(--gv-ink-2)]">▼</span>
          <span
            className={`gv-mono text-sm font-medium ${deltaNeg ? "text-[color:var(--gv-ink-2)]" : "text-[color:var(--gv-ink-3)]"}`}
          >
            {row.delta.value}
          </span>
        </div>
        <p className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">{row.uses} lượt</p>
      </div>
    </div>
  );
}
