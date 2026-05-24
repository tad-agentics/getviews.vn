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
  /** False when ``enableMobileSidebar`` is off — hide drawer trigger. */
  drawerEnabled: boolean;
};

const MobileShellContext = createContext<MobileShellContextValue | null>(null);

/** Reserve space above the home indicator + floating nav pill on mobile. */
export const MOBILE_FLOATING_NAV_CLEARANCE =
  "calc(4.25rem + max(0.75rem, env(safe-area-inset-bottom)))";

export function MobileShellProvider({
  active,
  openDrawer,
  drawerEnabled = false,
  children,
}: {
  active?: AppShellActive;
  openDrawer: () => void;
  drawerEnabled?: boolean;
  children: ReactNode;
}) {
  return (
    <MobileShellContext.Provider value={{ active, openDrawer, drawerEnabled }}>
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

/** History drawer trigger — lives in TopBar or standalone mobile header. */
export function MobileShellDrawerButton({ className }: { className?: string }) {
  const ctx = useMobileShell();
  if (!ctx?.drawerEnabled) return null;

  return (
    <button
      type="button"
      aria-label="Mở lịch sử phiên"
      className={
        className ??
        "flex h-11 w-11 shrink-0 items-center justify-center rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink-2)] transition-colors hover:bg-[color:var(--gv-canvas-2)] lg:hidden"
      }
      onClick={ctx.openDrawer}
    >
      <AlignLeft className="h-5 w-5" strokeWidth={1.8} aria-hidden />
    </button>
  );
}

/** Floating bottom nav: Studio · Xu Hướng · Kho Douyin (mobile only). */
export function MobileFloatingBottomNav() {
  const ctx = useMobileShell();
  const navigate = useNavigate();
  if (!ctx) return null;

  return (
    <nav
      aria-label="Điều hướng chính"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-30 px-3 lg:hidden"
      style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
    >
      <div className="pointer-events-auto mx-auto flex max-w-md items-stretch gap-1 rounded-2xl border border-[color:var(--gv-rule)] bg-[color:color-mix(in_srgb,var(--gv-paper)_92%,transparent)] p-1 shadow-[0_10px_40px_rgba(20,17,12,0.14)] backdrop-blur-md">
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
                "min-h-[44px] min-w-0 flex-1 truncate rounded-[14px] px-2 py-2 text-center text-[11px] font-semibold leading-tight transition-colors sm:text-xs " +
                (isActive
                  ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] shadow-sm"
                  : "text-[color:var(--gv-ink-2)] hover:bg-[rgba(20,17,12,0.05)] hover:text-[color:var(--gv-ink)]")
              }
            >
              {tab.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

/** @deprecated Use ``MobileShellDrawerButton`` + ``MobileFloatingBottomNav``. */
export function MobileShellBar({
  placement = "below-topbar",
}: {
  placement?: "below-topbar" | "standalone";
}) {
  void placement;
  return (
    <>
      <MobileShellDrawerButton />
      <MobileFloatingBottomNav />
    </>
  );
}
