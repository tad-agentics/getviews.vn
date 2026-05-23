import type { ButtonHTMLAttributes, ReactNode } from "react";

type BtnVariant = "ink" | "ghost" | "accent" | "pos";
type BtnSize = "sm" | "md" | "lg";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all " +
  "disabled:pointer-events-none " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[color:var(--gv-accent)]";

const VARIANTS: Record<BtnVariant, string> = {
  // `.btn` in the design: 1px ink border, ink bg, canvas text, hover lift.
  ink:
    "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] border border-[color:var(--gv-ink)] " +
    "hover:-translate-y-[1px] hover:shadow-[0_8px_20px_-8px_rgba(0,0,0,0.3)] " +
    "disabled:opacity-50",
  ghost:
    "font-medium bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] border border-[color:var(--gv-rule)] hover:bg-[color:var(--gv-canvas-2)] " +
    "disabled:opacity-50",
  accent:
    "bg-[color:var(--gv-accent)] text-white border border-[color:var(--gv-accent)] " +
    "hover:bg-[color:var(--gv-accent-deep)] hover:border-[color:var(--gv-accent-deep)] " +
    "disabled:bg-[color:var(--gv-faint)] disabled:text-[color:var(--gv-ink-4)] disabled:cursor-not-allowed disabled:border-[color:var(--gv-rule)]",
  pos:
    "bg-[color:var(--gv-pos)] text-white border border-[color:var(--gv-pos)] " +
    "hover:bg-[color:var(--gv-pos-deep)] hover:border-[color:var(--gv-pos-deep)] " +
    "disabled:bg-[color:var(--gv-faint)] disabled:text-[color:var(--gv-ink-4)] disabled:cursor-not-allowed disabled:border-[color:var(--gv-rule)]",
};

const SIZES: Record<BtnSize, string> = {
  sm: "h-8 min-h-[44px] px-3 text-xs",
  md: "h-10 px-4 text-sm leading-tight",
  lg: "h-12 px-6 text-sm leading-tight",
};

export function Btn({
  children,
  variant = "ink",
  size = "md",
  className,
  ...rest
}: {
  children: ReactNode;
  variant?: BtnVariant;
  size?: BtnSize;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={[BASE, VARIANTS[variant], SIZES[size], className ?? ""].filter(Boolean).join(" ")}
      {...rest}
    >
      {children}
    </button>
  );
}
