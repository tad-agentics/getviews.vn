/**
 * B.2.2 — MATCH column: thin rule track + accent fill + mono score (0–100).
 * @see `artifacts/uiux-reference/screens/kol.jsx`
 */
export function MatchScoreBar({ match }: { match: number }) {
  const m = Math.max(0, Math.min(100, Math.round(match)));
  return (
    <div className="flex min-w-0 items-center gap-1.5">
      <div className="h-1 min-w-0 flex-1 overflow-hidden rounded-full bg-[color:var(--gv-rule)]">
        <div
          className="h-full rounded-full bg-[color:var(--gv-accent)]"
          style={{ width: `${m}%` }}
        />
      </div>
      <span className="gv-mono w-[22px] shrink-0 text-right text-[10px] text-[color:var(--gv-ink)]">{m}</span>
    </div>
  );
}
