import type { SourceRowData } from "@/lib/api-types";

/** Phase C.1.3 — Sources rail stub; fills from payload when C.2+ aggregates land. */
export function AnswerSourcesCard({
  sources,
  placeholder = "Corpus + Gemini (C.2+)",
}: {
  sources?: SourceRowData[] | null;
  placeholder?: string;
}) {
  const rows = sources?.length ? sources.slice(0, 6) : null;
  return (
    <div className="rounded-lg border border-[var(--gv-rule)] bg-[var(--gv-paper)] p-4">
      <div className="flex items-baseline justify-between gap-2">
        <p className="font-mono text-[10px] uppercase tracking-wide text-[var(--gv-ink-4)]">Nguồn</p>
        {rows ? (
          <span className="font-mono text-[11px] text-[color:var(--gv-accent)]">{rows.length}</span>
        ) : null}
      </div>
      {rows ? (
        <ul className="mt-3 space-y-2">
          {rows.map((s, i) => (
            <li
              key={`${s.kind}-${s.label}-${i}`}
              className="flex items-start gap-2 border-t border-[var(--gv-rule)] pt-2 first:border-t-0 first:pt-0"
            >
              <span className="mt-0.5 size-7 shrink-0 rounded border border-[var(--gv-rule)] bg-[var(--gv-canvas-2)]" />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-[var(--gv-ink)]">{s.label}</p>
                <p className="font-mono text-[10px] text-[var(--gv-ink-4)]">{s.sub}</p>
              </div>
              <span className="font-mono text-sm tabular-nums text-[var(--gv-ink)]">{s.count}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[var(--gv-ink-3)]">{placeholder}</p>
      )}
      {rows ? (
        <p className="mt-3 border-t border-[var(--gv-rule)] pt-3">
          <span className="gv-mono text-[11px] text-[color:var(--gv-accent)]">Xem chi tiết nguồn →</span>
        </p>
      ) : null}
    </div>
  );
}
