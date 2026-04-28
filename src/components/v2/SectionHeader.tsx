import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";

/**
 * Editorial section title — matches UIUX `home.jsx` SectionHeader:
 * ● kicker in accent-deep mono 10px, h2 tight, caption ink-3.
 * Mobile: title + caption stack full-width; sm+: caption can sit on the title row when space allows.
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
        "mb-4 flex gap-3 sm:gap-4",
        right
          ? "flex-col sm:flex-row sm:items-end sm:justify-between"
          : "flex-col sm:flex-row sm:items-start sm:justify-between",
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
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-baseline sm:gap-x-3 sm:gap-y-1">
          <h2 className="gv-tight m-0 w-full text-[22px] font-semibold leading-[1.1] tracking-[-0.02em] text-[color:var(--gv-ink)] sm:w-auto sm:max-w-[min(100%,36rem)] sm:text-[26px] sm:leading-none lg:text-[28px]">
            {title}
          </h2>
          {caption ? (
            <p className="min-w-0 w-full text-[12.5px] leading-relaxed text-[color:var(--gv-ink-3)] sm:max-w-prose sm:flex-1 sm:text-[13px] sm:leading-snug">
              {caption}
            </p>
          ) : null}
        </div>
      </div>
      {right ? <div className="shrink-0 self-start sm:self-auto">{right}</div> : null}
    </header>
  );
}
