import type { HTMLAttributes, ReactNode } from "react";

type CardVariant = "paper" | "canvas" | "ink" | "brutal" | "brutal-compact";

const BASE = "w-full";

const VARIANTS: Record<CardVariant, string> = {
  paper:
    "rounded-[18px] bg-[color:var(--gv-paper)] border border-[color:var(--gv-rule)]",
  canvas:
    "rounded-[18px] bg-[color:var(--gv-canvas-2)] border border-[color:var(--gv-rule-2)]",
  ink:
    "rounded-[18px] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] border border-[color:var(--gv-ink)]",
  brutal: "gv-surface-brutal",
  "brutal-compact": "gv-surface-brutal gv-surface-brutal--compact",
};

/**
 * Generic card container. Use `variant="brutal"` for the composer / primary
 * CTA surface (2px ink border + hard offset shadow); use `variant="ink"`
 * for the pulse-card lead surface; the rest are canvas/paper tints.
 */
export function Card({
  children,
  variant = "paper",
  className,
  ...rest
}: {
  children: ReactNode;
  variant?: CardVariant;
} & HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={[BASE, VARIANTS[variant], className ?? ""].filter(Boolean).join(" ")}
      {...rest}
    >
      {children}
    </div>
  );
}
