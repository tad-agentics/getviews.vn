import type { ReactNode } from "react";

export type CardInputProps = {
  label: ReactNode;
  children: ReactNode;
  className?: string;
};

/** B.4 — bordered paper panel (``script.jsx`` CardInput). */
export function CardInput({ label, children, className = "" }: CardInputProps) {
  return (
    <div
      className={`rounded-[var(--gv-radius-sm)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3.5 ${className}`.trim()}
    >
      <div className="gv-mono mb-2.5 text-[9.5px] font-medium uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
        {label}
      </div>
      {children}
    </div>
  );
}
