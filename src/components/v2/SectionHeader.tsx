import type { ReactNode } from "react";
import { Kicker } from "./Kicker";

/**
 * Kicker + tight h2 + optional caption + optional right action. The design
 * uses this on every section; wrapping it lets us change the scaffold once
 * (e.g. add an underline rule) without touching every call site.
 */
export function SectionHeader({
  kicker,
  title,
  caption,
  right,
  kickerTone,
  className,
}: {
  kicker: string;
  title: ReactNode;
  caption?: ReactNode;
  right?: ReactNode;
  kickerTone?: "default" | "muted" | "pos";
  className?: string;
}) {
  return (
    <header className={["flex items-start justify-between gap-4", className ?? ""].join(" ").trim()}>
      <div className="min-w-0">
        <Kicker tone={kickerTone} dot>{kicker}</Kicker>
        <h2
          className="gv-tight mt-2 text-[28px] leading-none text-[color:var(--gv-ink)]"
          style={{ fontFamily: "var(--gv-font-display)" }}
        >
          {title}
        </h2>
        {caption ? (
          <p className="mt-2 max-w-prose text-[13px] leading-snug text-[color:var(--gv-ink-3)]">
            {caption}
          </p>
        ) : null}
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </header>
  );
}
