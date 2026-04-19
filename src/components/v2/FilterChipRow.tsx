import type { ReactNode } from "react";

/**
 * B.2.2 — filter ribbon left cluster: mono “LỌC THEO” + horizontal scroll of chips.
 * @see `artifacts/uiux-reference/screens/kol.jsx`
 */
export function FilterChipRow({
  label = "LỌC THEO",
  children,
  trailing,
  className = "",
}: {
  label?: string;
  children: ReactNode;
  /** Search input + action buttons (right side of ribbon). */
  trailing?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col gap-3 min-[640px]:flex-row min-[640px]:items-center min-[640px]:justify-between ${className}`.trim()}
    >
      <div className="flex min-w-0 flex-1 items-center gap-2.5 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <span className="gv-mono shrink-0 text-[9px] uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]">
          {label}
        </span>
        {children}
      </div>
      {trailing ? <div className="flex shrink-0 flex-wrap items-center gap-2">{trailing}</div> : null}
    </div>
  );
}
