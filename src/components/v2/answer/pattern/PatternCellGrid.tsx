import type { PatternCellPayloadData } from "@/lib/api-types";

import { PatternMiniChart } from "./PatternMiniChart";

export function PatternCellGrid({ cells }: { cells: PatternCellPayloadData[] }) {
  if (cells.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-lg bg-[color:var(--gv-ink)] p-px">
      <div className="grid grid-cols-1 gap-px sm:grid-cols-2">
        {cells.map((c) => (
          <div key={c.title} className="bg-[color:var(--gv-paper)] p-4">
            <p className="gv-mono mb-2 text-[10px] tracking-wide text-[color:var(--gv-ink-4)]">{c.title}</p>
            <p className="gv-serif text-[28px] leading-none text-[color:var(--gv-ink)]">{c.finding}</p>
            <div className="mt-3">
              <PatternMiniChart cell={c} />
            </div>
            <p className="mt-2 text-[13px] text-[color:var(--gv-ink-3)]">{c.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
