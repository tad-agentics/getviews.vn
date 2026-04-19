import type { ButtonHTMLAttributes, ReactNode } from "react";

type BtnVariant = "ink" | "ghost" | "accent" | "pos";
type BtnSize = "sm" | "md" | "lg";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all " +
  "disabled:opacity-50 disabled:pointer-events-none " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[color:var(--gv-accent)]";

const VARIANTS: Record<BtnVariant, string> = {
  // `.btn` in the design: 1px ink border, ink bg, canvas text, hover lift.
  ink:
    "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] border border-[color:var(--gv-ink)] " +
    "hover:-translate-y-[1px] hover:shadow-[0_8px_20px_-8px_rgba(0,0,0,0.3)]",
  ghost:
    "font-medium bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] border border-[color:var(--gv-rule)] hover:bg-[color:var(--gv-canvas-2)]",
  accent:
    "bg-[color:var(--gv-accent)] text-white border border-[color:var(--gv-accent)] " +
    "hover:bg-[color:var(--gv-accent-deep)] hover:border-[color:var(--gv-accent-deep)]",
  pos:
    "bg-[color:var(--gv-pos)] text-white border border-[color:var(--gv-pos)] " +
    "hover:bg-[color:var(--gv-pos-deep)] hover:border-[color:var(--gv-pos-deep)]",
};

const SIZES: Record<BtnSize, string> = {
  sm: "h-8 px-3 text-xs",
  /* Reference .btn: 13px */
  md: "h-10 px-4 text-[13px] leading-tight",
  lg: "h-12 px-6 text-[15px] leading-tight",
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
