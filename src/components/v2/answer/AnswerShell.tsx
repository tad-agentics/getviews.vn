import type { ReactNode } from "react";

/**
 * Phase C.1.3 — canonical `/app/answer` column + two-column grid (answer.jsx §layout).
 */
export function AnswerShell({
  crumb,
  header,
  main,
  aside,
}: {
  crumb: ReactNode;
  header: ReactNode;
  main: ReactNode;
  aside: ReactNode;
}) {
  return (
    <main className="gv-route-main gv-route-main--1280 gv-route-main--answer">
      {crumb}
      {header}
      <section className="mt-10 grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
        <div className="min-w-0">{main}</div>
        <aside className="flex min-w-0 flex-col gap-4">{aside}</aside>
      </section>
    </main>
  );
}
