import { type ReactNode } from "react";
import { useMobileShell, MobileShellDrawerButton } from "@/components/mobileShell";

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
  const shell = useMobileShell();

  return (
    <header
      className={[
        "sticky top-0 z-10 w-full",
        /* Cùng band với sidebar brand + iOS safe area (PWA standalone). */
        "box-border flex min-h-[calc(3.5rem+var(--gv-safe-top))] shrink-0 items-center justify-between gap-2 px-4 pt-[var(--gv-safe-top)] md:min-h-[calc(4rem+var(--gv-safe-top))] md:gap-4 md:px-7",
        "border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)]",
        className ?? "",
      ].filter(Boolean).join(" ")}
    >
      <div className="flex min-w-0 flex-1 items-center gap-2.5">
        {shell?.drawerEnabled ? <MobileShellDrawerButton /> : null}
        <div className="min-w-0 flex-1">
          <p className="gv-uc mb-[3px] text-[11px] text-[color:var(--gv-ink-3)]">{kicker}</p>
          <p className="gv-tight mt-0 truncate text-[17px] leading-none tracking-[-0.03em] text-[color:var(--gv-ink)] md:text-[24px]">
            {title}
          </p>
        </div>
      </div>
      {right ? (
        <div className="flex shrink-0 items-center justify-end gap-2 pl-2 sm:gap-2.5">
          {right}
        </div>
      ) : null}
    </header>
  );
}
