import type { ReactNode } from "react";

/**
 * Per-screen sticky top bar. Matches the design's 64px topbar:
 * mono uppercase kicker + `.tight` screen title (`<p>`, not `<h1>`) on the left,
 * optional right-slot (action buttons, live-data chip). 56px on mobile.
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
        "sticky top-0 z-10 w-full",
        /* Cùng band với sidebar brand: 56px / 64px (h-14 / h-16) */
        "box-border flex h-14 items-center justify-between gap-4 px-4 md:h-16 md:px-7",
        "border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)]",
        className ?? "",
      ].filter(Boolean).join(" ")}
    >
      <div className="min-w-0">
        <p className="gv-uc mb-[3px] text-[9.5px] text-[color:var(--gv-ink-4)]">{kicker}</p>
        <p className="gv-tight mt-0 truncate text-[19px] leading-none tracking-[-0.03em] text-[color:var(--gv-ink)] md:text-[24px]">
          {title}
        </p>
      </div>
      {right ? <div className="shrink-0 flex items-center gap-2.5">{right}</div> : null}
    </header>
  );
}
