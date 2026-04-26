import type { ReactNode } from "react";

/**
 * Phase C.1.3 — canonical `/app/answer` column + two-column grid (answer.jsx §layout).
 * `aside` tùy chọn — khi không có phiên, chỉ hiển thị một cột nội dung.
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
  aside?: ReactNode;
}) {
  const hasAside = aside != null;
  return (
    <main className="gv-route-main gv-route-main--1280 gv-route-main--answer">
      {crumb}
      {header}
      <section
        className={
          hasAside
            ? "mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start lg:gap-10"
            : "mt-8"
        }
      >
        <div className="min-w-0">{main}</div>
        {hasAside ? (
          <aside className="flex min-w-0 flex-col gap-4 lg:sticky lg:top-16">{aside}</aside>
        ) : null}
      </section>
    </main>
  );
}
