import type { ReactNode } from "react";

/** Single report block shell — wraps §J body renderers (Phase C.2.3 full pattern layout). */
export function AnswerBlock({
  kicker,
  children,
  bare,
}: {
  kicker: string;
  children: ReactNode;
  /** Báo cáo dạng “trang reference”: không khung ngoài, thân section tự thở. */
  bare?: boolean;
}) {
  if (bare) {
    return <div className="min-w-0">{children}</div>;
  }
  return (
    <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
      <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)]">
        {kicker}
      </p>
      <div className="mt-4">{children}</div>
    </div>
  );
}
