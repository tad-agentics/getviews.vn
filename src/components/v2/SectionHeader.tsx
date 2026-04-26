import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";

/**
 * Editorial section title — matches UIUX `home.jsx` SectionHeader:
 * ● kicker in accent-deep mono 10px, h2 28px tight, caption 13px ink-3
 * on the same baseline row as the title when space allows.
 */
export function SectionHeader({
  kicker,
  title,
  caption,
  right,
  kickerTone,
  kickerSparkles,
  className,
}: {
  kicker: string;
  title: ReactNode;
  caption?: ReactNode;
  right?: ReactNode;
  kickerTone?: "default" | "muted" | "pos";
  /** Kicker dạng spark + chữ accent (ref GỢI Ý HÔM NAY). */
  kickerSparkles?: boolean;
  className?: string;
}) {
  const kickerColor =
    kickerTone === "pos"
      ? "text-[color:var(--gv-pos-deep)]"
      : kickerTone === "muted"
        ? "text-[color:var(--gv-ink-4)]"
        : "text-[color:var(--gv-accent-deep)]";

  return (
    <header
      className={[
        "mb-4 flex justify-between gap-4",
        right ? "items-end" : "items-start",
        className ?? "",
      ]
        .join(" ")
        .trim()}
    >
      <div className="min-w-0 flex-1">
        <span
          className={[
            "gv-uc mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold",
            kickerSparkles ? "text-[color:var(--gv-accent-deep)]" : kickerColor,
          ].join(" ")}
        >
          {kickerSparkles ? (
            <>
              <Sparkles className="h-2.5 w-2.5 shrink-0 text-[color:var(--gv-accent)]" strokeWidth={2} aria-hidden />
              {kicker}
            </>
          ) : (
            <>● {kicker}</>
          )}
        </span>
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 className="gv-tight m-0 text-[28px] leading-none text-[color:var(--gv-ink)]">{title}</h2>
          {caption ? (
            <p className="min-w-0 max-w-prose flex-1 text-[13px] leading-snug text-[color:var(--gv-ink-3)]">
              {caption}
            </p>
          ) : null}
        </div>
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </header>
  );
}
