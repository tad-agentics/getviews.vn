import { createContext, useContext, type ReactNode } from "react";
import { useNavigate } from "react-router";
import { AlignLeft } from "lucide-react";

import { markDouyinFeedVisited } from "@/lib/douyinNewBadge";

export type AppShellActive =
  | "home"
  | "answer"
  | "trends"
  | "settings"
  | "script"
  | "admin"
  | "douyin"
  | "channel";

type MobileShellContextValue = {
  active?: AppShellActive;
  openDrawer: () => void;
};

const MobileShellContext = createContext<MobileShellContextValue | null>(null);

export function MobileShellProvider({
  active,
  openDrawer,
  children,
}: {
  active?: AppShellActive;
  openDrawer: () => void;
  children: ReactNode;
}) {
  return (
    <MobileShellContext.Provider value={{ active, openDrawer }}>
      {children}
    </MobileShellContext.Provider>
  );
}

export function useMobileShell() {
  return useContext(MobileShellContext);
}

type MobileTabKey = "home" | "trends" | "douyin";

function tabActive(active: AppShellActive | undefined, tab: MobileTabKey): boolean {
  switch (tab) {
    case "home":
      return active === "home" || active === "channel";
    case "trends":
      return active === "trends";
    case "douyin":
      return active === "douyin";
  }
}

const MOBILE_PRIMARY_TABS: { key: MobileTabKey; label: string; to: string }[] = [
  { key: "home", label: "Studio", to: "/app" },
  { key: "trends", label: "Xu Hướng", to: "/app/trends" },
  { key: "douyin", label: "Kho Douyin", to: "/app/douyin" },
];

/** Row 2 mobile chrome: hamburger + Studio / Xu Hướng / Kho Douyin (below screen TopBar). */
export function MobileShellBar({
  placement = "below-topbar",
}: {
  /** ``below-topbar`` — under screen TopBar; ``standalone`` — top of scroll (no TopBar). */
  placement?: "below-topbar" | "standalone";
}) {
  const ctx = useMobileShell();
  const navigate = useNavigate();
  if (!ctx) return null;

  const stickyTop =
    placement === "standalone"
      ? "top-[env(safe-area-inset-top)]"
      : "top-[calc(3.5rem+var(--gv-safe-top))]";

  return (
    <div
      className={`lg:hidden sticky z-20 border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] ${stickyTop}`}
    >
      <div className="flex min-h-11 items-center gap-1 px-2 py-1">
        <button
          type="button"
          aria-label="Mở lịch sử phiên"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink-2)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
          onClick={ctx.openDrawer}
        >
          <AlignLeft className="h-5 w-5" strokeWidth={1.8} aria-hidden />
        </button>
        <div className="flex min-w-0 flex-1 items-center gap-1">
          {MOBILE_PRIMARY_TABS.map((tab) => {
            const isActive = tabActive(ctx.active, tab.key);
            return (
              <button
                key={tab.key}
                type="button"
                aria-current={isActive ? "page" : undefined}
                onClick={() => {
                  if (tab.key === "douyin") markDouyinFeedVisited();
                  navigate(tab.to);
                }}
                className={
                  "min-h-[44px] flex-1 truncate rounded-md px-2 py-2 text-center text-xs font-medium transition-colors " +
                  (isActive
                    ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
                    : "text-[color:var(--gv-ink-2)] hover:bg-[rgba(20,17,12,0.05)] hover:text-[color:var(--gv-ink)]")
                }
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
