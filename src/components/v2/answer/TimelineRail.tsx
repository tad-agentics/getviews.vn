import type { ReactNode } from "react";

/** Left rail when a session has multiple turns (Phase C.1.3). */
export function TimelineRail({
  turnCount,
  children,
}: {
  turnCount: number;
  children: ReactNode;
}) {
  if (turnCount <= 1) return <>{children}</>;
  return (
    <div className="relative pl-6">
      <div
        className="absolute bottom-0 left-[7px] top-0 w-px bg-[var(--gv-rule)]"
        aria-hidden
      />
      <div className="absolute left-0 top-2 flex size-4 items-center justify-center rounded-full border border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] font-mono text-[9px] text-[color:var(--gv-ink)]">
        {turnCount}
      </div>
      {children}
    </div>
  );
}
