import type { ReactNode } from "react";

/**
 * KOL filter ribbon — matches `artifacts/uiux-reference/screens/kol.jsx`:
 * one row (`justify-between`, `flex-wrap`), “LỌC THEO” inline with pills (gap 10px),
 * padding `8px 0 18px`, trailing cluster `gap: 8px`.
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
      className={`flex flex-wrap items-center justify-between gap-x-4 gap-y-3 py-2 pb-[18px] ${className}`.trim()}
    >
      <div className="flex min-w-0 max-w-full flex-1 flex-wrap items-center gap-[10px]">
        {label ? (
          <span className="gv-uc shrink-0 text-[9px] text-[color:var(--gv-ink-4)]">{label}</span>
        ) : null}
        {children}
      </div>
      {trailing ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{trailing}</div>
      ) : null}
    </div>
  );
}
