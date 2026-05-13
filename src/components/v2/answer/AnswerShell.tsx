import type { ReactNode } from "react";

/**
 * Phase C.1.3 — canonical `/app/answer` column container.
 *
 * The original spec carried an optional two-column grid (300px aside),
 * but every caller in `src/**` passes only `crumb`/`header`/`main`,
 * so the aside branch was dead and the grid collapsed to one column.
 * Re-introduce the aside when there's a real consumer; for now keep
 * the shell minimal.
 */
export function AnswerShell({
  crumb,
  header,
  main,
}: {
  crumb: ReactNode;
  header: ReactNode;
  main: ReactNode;
}) {
  return (
    <main className="gv-route-main gv-route-main--1280 gv-route-main--answer">
      {crumb}
      {header}
      <section className="mt-8">
        <div className="min-w-0">{main}</div>
      </section>
    </main>
  );
}
