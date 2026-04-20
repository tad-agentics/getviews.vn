/** Explicit empty-state row when WhatStalled is [] but reason is set (§J invariant). */
export function WhatStalledRow({ empty, reason }: { empty: boolean; reason: string | null }) {
  if (!empty) return null;
  return (
    <div
      className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-3 py-2 text-xs text-[color:var(--gv-ink-2)]"
      data-testid="what-stalled-empty"
    >
      <span className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-danger)]">
        Không đủ tín hiệu
      </span>
      <p className="mt-1 text-[color:var(--gv-ink-3)]">{reason ?? "—"}</p>
    </div>
  );
}
