import type { ReactNode } from "react";

/**
 * The 56px bold tight number used in KPI-style cells.
 * `tone="pos"`/`"neg"` colour the number for delta rendering.
 */
export function Bignum({
  children,
  tone = "ink",
  suffix,
  className,
}: {
  children: ReactNode;
  tone?: "ink" | "pos" | "neg";
  suffix?: ReactNode;
  className?: string;
}) {
  const toneClass =
    tone === "pos" ? "text-[color:var(--gv-pos)]" :
    tone === "neg" ? "text-[color:var(--gv-neg)]" :
    "text-[color:var(--gv-ink)]";
  return (
    <div
      className={["gv-bignum flex items-baseline gap-2", toneClass, className ?? ""]
        .filter(Boolean).join(" ")}
    >
      <span>{children}</span>
      {suffix ? (
        <span className="text-xs font-medium text-[color:var(--gv-ink-4)] gv-uc">
          {suffix}
        </span>
      ) : null}
    </div>
  );
}
