import type { ReactNode } from "react";

/** Phase C.1.3 — `QueryHeader` kicker + serif title (answer.jsx). */
export function QueryHeader({
  title,
  kicker = "Câu hỏi",
  meta,
  children,
}: {
  title: string;
  kicker?: string;
  meta?: ReactNode;
  /** Research strip, progress, etc. (Phase C.1.3). */
  children?: ReactNode;
}) {
  return (
    <header className="border-t-2 border-[var(--gv-ink)] border-b border-[var(--gv-rule)] py-6">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <p className="font-mono text-[10px] uppercase tracking-wide text-[var(--gv-ink-4)]">{kicker}</p>
        {meta ? (
          <>
            <span className="h-px min-w-[12px] flex-1 bg-[var(--gv-rule)] opacity-60" aria-hidden />
            <div className="font-mono text-[10px] text-[var(--gv-ink-4)]">{meta}</div>
          </>
        ) : null}
      </div>
      <h1 className="gv-serif text-[clamp(1.5rem,3vw,2.25rem)] font-medium leading-tight text-[var(--gv-ink)]">
        {title}
      </h1>
      {children}
    </header>
  );
}
