/**
 * Phase C.4.3 — Timing ActionCards × 2.
 *
 * Mirrors Pattern/Ideas ActionCard shape (forecast row above CTA) so the
 * §J `ActionCardPayload` contract stays uniform across report formats.
 */

import { useNavigate } from "react-router";

import type { ActionCardPayloadData } from "@/lib/api-types";
import { renderForecastLine } from "@/components/v2/answer/forecastLine";

function defaultRoute(a: ActionCardPayloadData): string {
  if (a.route) return a.route;
  const t = a.title.toLowerCase();
  if (t.includes("lịch") || t.includes("schedule") || t.includes("script")) return "/app/script";
  if (t.includes("kol") || t.includes("đối thủ") || t.includes("kênh")) return "/app/kol";
  return "/app";
}

function actionIcon(symbol: string): string {
  switch (symbol) {
    case "calendar":
      return "📅";
    case "search":
      return "🔎";
    case "users":
      return "👥";
    default:
      return "•";
  }
}

export function TimingActionCards({ actions }: { actions: ActionCardPayloadData[] }) {
  const navigate = useNavigate();
  if (actions.length === 0) return null;
  return (
    <ul className="grid grid-cols-1 gap-3 min-[900px]:grid-cols-2">
      {actions.map((a) => {
        const primary = Boolean(a.primary);
        const forecastBg = primary
          ? "bg-[color:var(--gv-forecast-primary-bg)]"
          : "bg-[color:var(--gv-canvas-2)]";
        return (
          <li
            key={a.title}
            className={`flex flex-col rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4 ${
              primary ? "ring-1 ring-[color:var(--gv-accent)]" : ""
            }`}
          >
            <div className="mb-2 text-[20px] leading-none" aria-hidden>
              {actionIcon(a.icon)}
            </div>
            <p className="gv-serif text-[16px] text-[color:var(--gv-ink)]">{a.title}</p>
            <p className="mt-1 text-sm text-[color:var(--gv-ink-3)]">{a.sub}</p>
            {(() => {
              // Timing cards historically used "baseline" instead of
              // "kênh TB" — preserve that wording but drop the whole row
              // when both values are empty (BUG-15).
              const line = renderForecastLine(a.forecast, { unit: "" });
              return line ? (
                <div
                  className={`mt-[10px] rounded px-[10px] py-2 gv-mono text-[11px] text-[color:var(--gv-ink-3)] ${forecastBg}`}
                >
                  {line}
                </div>
              ) : null;
            })()}
            <button
              type="button"
              className={`mt-3 w-full rounded-md py-2 text-center gv-mono text-[12px] font-medium ${
                primary
                  ? "bg-[color:var(--gv-accent)] text-white"
                  : "border border-[color:var(--gv-rule)] text-[color:var(--gv-ink)]"
              }`}
              onClick={() => navigate(defaultRoute(a))}
            >
              {a.cta}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
