import type { ButtonHTMLAttributes, ReactNode } from "react";

type ChipVariant = "default" | "accent" | "pos" | "neg" | "ink" | "lime";
type ChipSize = "sm" | "md";

const BASE =
  "inline-flex items-center gap-1.5 rounded-full border font-medium transition-colors " +
  "disabled:opacity-50 disabled:pointer-events-none";

const VARIANTS: Record<ChipVariant, string> = {
  default:
    "border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink-2)] hover:bg-[color:var(--gv-canvas-2)]",
  accent:
    "border-transparent bg-[color:var(--gv-accent-soft)] font-semibold text-[color:var(--gv-accent-deep)] hover:bg-[color:var(--gv-accent-soft)]",
  pos:
    "border-transparent bg-[color:var(--gv-pos-soft)] text-[color:var(--gv-pos-deep)]",
  neg:
    "border-transparent bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg-deep)]",
  ink:
    "border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] hover:bg-[color:var(--gv-ink-2)]",
  lime:
    "border-transparent text-[color:var(--gv-ink)] [background:var(--gv-lime)] hover:opacity-90",
};

const SIZES: Record<ChipSize, string> = {
  /* Reference ``styles.css`` .chip: 12px, padding 6px 12px, weight 500 */
  sm: "min-h-0 py-1 px-2.5 text-xs font-medium leading-none",
  md: "min-h-0 py-1.5 px-3 text-xs font-medium leading-none",
};

/**
 * Pill chip for filters, tags, badges. Rendered as a `<button>` when an
 * onClick is passed (interactive filter row), else as a `<span>`.
 */
export function Chip({
  children,
  variant = "default",
  size = "md",
  active = false,
  className,
  ...rest
}: {
  children: ReactNode;
  variant?: ChipVariant;
  size?: ChipSize;
  active?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const classes = [
    BASE, VARIANTS[variant], SIZES[size],
    active ? "ring-1 ring-offset-0 ring-[color:var(--gv-ink)]" : "",
    className ?? "",
  ].filter(Boolean).join(" ");
  if (rest.onClick || rest.type === "button" || rest.type === "submit") {
    return (
      <button className={classes} {...rest}>
        {children}
      </button>
    );
  }
  return <span className={classes}>{children}</span>;
}
