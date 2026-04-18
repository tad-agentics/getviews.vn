import type { HTMLAttributes, ReactNode } from "react";

type KickerTone = "default" | "muted" | "pos";

/**
 * Mono all-caps label.
 *
 * The `●` bullet prefix is opt-in via `dot` — in the design, only
 * SectionHeader kickers show the dot; plain inline kickers like
 * "STUDIO · CREATOR" render as flat uppercase-mono.
 */
export function Kicker({
  children,
  tone = "default",
  dot = false,
  className,
  ...rest
}: {
  children: ReactNode;
  tone?: KickerTone;
  dot?: boolean;
} & Omit<HTMLAttributes<HTMLSpanElement>, "children">) {
  const classes = [
    "gv-kicker",
    dot ? "gv-kicker--dot" : "",
    tone === "pos" ? "gv-kicker--pos" : "",
    tone === "muted" ? "gv-kicker--muted" : "",
    className ?? "",
  ].filter(Boolean).join(" ");
  return (
    <span className={classes} {...rest}>
      {children}
    </span>
  );
}
