import type { ReactNode } from "react";

/**
 * Single report block shell (Phase C.1.3) — wraps §J body renderers.
 * Pattern reports include the C.2 placeholder until full layout ships.
 */
export function AnswerBlock({
  kicker,
  children,
  c2Placeholder = false,
}: {
  kicker: string;
  children: ReactNode;
  /** When true, show the Phase C.2 full-layout teaser line (pattern only). */
  c2Placeholder?: boolean;
}) {
  return (
    <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
      <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)]">
        {kicker}
      </p>
      <div className="mt-4">{children}</div>
      {c2Placeholder ? (
        <p className="mt-6 border-t border-[color:var(--gv-rule)] pt-3 font-mono text-[10px] leading-relaxed text-[color:var(--gv-ink-4)]">
          C.2 incoming — hook grid, evidence rail, pattern cells, action forecasts (full layout).
        </p>
      ) : null}
    </div>
  );
}
