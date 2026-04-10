import { Clock, MessageCircle, TrendingUp } from "lucide-react";
import { NavLink } from "react-router";

const tabs = [
  { to: "/app", label: "Chat", icon: MessageCircle, end: true },
  { to: "/app/history", label: "Lịch sử", icon: Clock, end: false },
  { to: "/app/trends", label: "Xu hướng", icon: TrendingUp, end: false },
] as const;

export function BottomNav() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 border-t border-[var(--border)] bg-[var(--surface)] pb-[env(safe-area-inset-bottom)]"
      aria-label="Điều hướng chính"
    >
      <div className="mx-auto flex max-w-lg items-stretch justify-around gap-1 px-2 pt-1">
        {tabs.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex min-h-[48px] min-w-[44px] flex-1 flex-col items-center justify-center gap-0.5 rounded-lg px-2 py-1 text-[11px] font-medium transition-colors duration-[120ms] ${
                isActive ? "text-[var(--purple)]" : "text-[var(--muted)] hover:text-[var(--ink-soft)]"
              }`
            }
          >
            <Icon className="h-5 w-5 shrink-0" strokeWidth={2} aria-hidden />
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
