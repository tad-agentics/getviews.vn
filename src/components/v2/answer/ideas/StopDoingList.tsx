/**
 * Phase C.3.2 — StopDoing × 5 list (rank / bad+why / fix).
 */

type StopRow = { bad?: string; why?: string; fix?: string } & Record<string, string>;

export function StopDoingList({ rows }: { rows: StopRow[] }) {
  if (rows.length === 0) return null;
  return (
    <ol className="overflow-hidden rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
      {rows.map((r, i) => (
        <li
          key={`${r.bad}-${i}`}
          className="grid grid-cols-[60px_1fr] gap-3 border-t border-[color:var(--gv-rule)] px-4 py-3 first:border-t-0 min-[700px]:grid-cols-[80px_1fr_1fr]"
        >
          <span className="gv-serif text-[22px] leading-none text-[color:var(--gv-ink-4)]">
            {String(i + 1).padStart(2, "0")}
          </span>
          <div className="min-w-0 text-[13px] leading-[1.5] text-[color:var(--gv-ink-2)]">
            <p className="gv-serif text-[15px] font-medium text-[color:var(--gv-ink)]">{r.bad}</p>
            {r.why ? (
              <p className="mt-1 text-[12px] text-[color:var(--gv-ink-3)]">{r.why}</p>
            ) : null}
          </div>
          {r.fix ? (
            <p className="col-span-full min-[700px]:col-auto rounded bg-[color:var(--gv-accent-soft)] px-3 py-2 text-[13px] leading-[1.5] text-[color:var(--gv-accent-deep)]">
              <span className="gv-mono mr-2 text-[10px] uppercase tracking-wide">Fix</span>
              {r.fix}
            </p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
