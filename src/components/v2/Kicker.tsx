import type { HTMLAttributes, ReactNode } from "react";

type KickerTone = "default" | "muted" | "pos";

/**
 * "● KICKER" label pattern — mono all-caps prefix used above every section
 * header in the redesign. Dot colour is pink by default; `tone="pos"` swaps
 * to blue for positive-delta sections, `tone="muted"` neutral-greys it.
 */
export function Kicker({
  children,
  tone = "default",
  className,
  ...rest
}: {
  children: ReactNode;
  tone?: KickerTone;
} & Omit<HTMLAttributes<HTMLSpanElement>, "children">) {
  const toneClass =
    tone === "pos" ? "gv-kicker gv-kicker--pos" :
    tone === "muted" ? "gv-kicker gv-kicker--muted" :
    "gv-kicker";
  return (
    <span className={[toneClass, className ?? ""].join(" ").trim()} {...rest}>
      {children}
    </span>
  );
}
