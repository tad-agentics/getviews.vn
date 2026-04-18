import type { ButtonHTMLAttributes, ReactNode } from "react";

type BtnVariant = "ink" | "ghost" | "accent" | "pos";
type BtnSize = "sm" | "md" | "lg";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-full font-medium transition-all " +
  "disabled:opacity-50 disabled:pointer-events-none " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[color:var(--gv-ink)]";

const VARIANTS: Record<BtnVariant, string> = {
  ink:
    "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] hover:bg-[color:var(--gv-ink-2)]",
  ghost:
    "bg-[color:var(--gv-paper)] text-[color:var(--gv-ink)] border border-[color:var(--gv-rule)] hover:border-[color:var(--gv-ink-4)]",
  accent:
    "bg-[color:var(--gv-accent)] text-white hover:bg-[color:var(--gv-accent-deep)]",
  pos:
    "bg-[color:var(--gv-pos)] text-white hover:bg-[color:var(--gv-pos-deep)]",
};

const SIZES: Record<BtnSize, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
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
