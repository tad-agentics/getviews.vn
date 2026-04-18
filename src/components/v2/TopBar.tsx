import type { ReactNode } from "react";

/**
 * Per-screen sticky top bar. Matches the design's 64px topbar:
 * mono uppercase kicker + `.tight` title on the left, optional
 * right-slot (action buttons, live-data chip). 56px on mobile.
 *
 * Sits inside the screen's main area, not inside AppLayout — each
 * screen owns its own topbar copy.
 */
export function TopBar({
  kicker,
  title,
  right,
  className,
}: {
  kicker: string;
  title: ReactNode;
  right?: ReactNode;
  className?: string;
}) {
  return (
    <header
      className={[
        "sticky top-0 z-10 w-full min-h-[56px] md:min-h-[64px]",
        "flex items-center justify-between gap-4 px-4 md:px-7 py-3",
        "border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)]",
        className ?? "",
      ].filter(Boolean).join(" ")}
    >
      <div className="min-w-0">
        <p className="gv-mono text-[9.5px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          {kicker}
        </p>
        <h1
          className="gv-tight mt-0.5 truncate text-[19px] md:text-[24px] leading-none text-[color:var(--gv-ink)]"
          style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.03em" }}
        >
          {title}
        </h1>
      </div>
      {right ? <div className="shrink-0 flex items-center gap-2">{right}</div> : null}
    </header>
  );
}
