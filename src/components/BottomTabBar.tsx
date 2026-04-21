import { useNavigate } from "react-router";
import {
  Home as HomeIcon,
  Sparkles,
  TrendingUp,
  Settings as SettingsIcon,
} from "lucide-react";

/** Keys rendered as bottom tabs (four slots). */
type Tab = "home" | "answer" | "trends" | "settings";

/** Shell-wide active section; values not in the bottom bar show no tab as selected. */
export type AppShellActive = Tab | "kol" | "script";

/**
 * Mobile bottom tab bar (Phase A · A3.3).
 *
 * Matches the design's 4-item bottom bar for screens ≤ 900px wide. On
 * viewports without the desktop sidebar, this row is the primary section switcher.
 * Active tab ink-filled, others subdued; tapping navigates.
 *
 * Sits above the browser safe area via `pb-[env(safe-area-inset-bottom)]`
 * so iOS home-indicator devices don't clip the labels.
 */
export function BottomTabBar({ active }: { active?: AppShellActive }) {
  const navigate = useNavigate();

  const items: ReadonlyArray<{
    key: Tab;
    label: string;
    icon: React.ElementType;
    to: string;
  }> = [
    { key: "home",     label: "Trang chủ", icon: HomeIcon,       to: "/app" },
    { key: "answer",   label: "Nghiên cứu", icon: Sparkles,      to: "/app/answer" },
    { key: "trends",   label: "Xu hướng",  icon: TrendingUp,     to: "/app/trends" },
    { key: "settings", label: "Cài đặt",   icon: SettingsIcon,   to: "/app/settings" },
  ];

  return (
    <nav
      aria-label="Điều hướng dưới"
      className="md:hidden fixed inset-x-0 bottom-0 z-30 border-t border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] pb-[env(safe-area-inset-bottom)]"
    >
      <ul className="grid grid-cols-4">
        {items.map(({ key, label, icon: Icon, to }) => {
          const isActive = active === key;
          return (
            <li key={key}>
              <button
                type="button"
                onClick={() => navigate(to)}
                aria-current={isActive ? "page" : undefined}
                className={
                  "flex h-14 w-full flex-col items-center justify-center gap-1 text-[10px] font-medium transition-colors " +
                  (isActive
                    ? "text-[color:var(--gv-ink)]"
                    : "text-[color:var(--gv-ink-4)] active:text-[color:var(--gv-ink)]")
                }
              >
                <Icon
                  className="h-5 w-5"
                  strokeWidth={isActive ? 2.2 : 1.7}
                />
                <span>{label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
