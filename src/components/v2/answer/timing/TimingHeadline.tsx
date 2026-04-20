/**
 * Phase C.4.3 — Timing headline block.
 * Mirrors `thread-turns.jsx:111-140`: left = kicker + serif top window +
 * insight sentence. Right = "3 cửa sổ cao nhất" list with rank mono + lift.
 */

import type { TimingReportPayload } from "@/lib/api-types";

type Insight = { insight?: string };

export function TimingHeadline({ report }: { report: TimingReportPayload }) {
  const tw = report.top_window as Record<string, unknown> & Insight;
  const day = (tw.day as string | undefined) ?? "—";
  const hours = (tw.hours as string | undefined) ?? "—";
  const insight = tw.insight ?? "";
  const top3 = report.top_3_windows as Array<{
    rank: number;
    day: string;
    hours: string;
    lift_multiplier: number;
  }>;

  return (
    <section className="grid grid-cols-1 gap-6 border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] px-6 py-5 min-[900px]:grid-cols-[1fr_280px]">
      <div>
        <p className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          Sướng nhất
        </p>
        <h3 className="gv-serif mt-1 text-[32px] font-medium leading-[1.1] tracking-tight text-[color:var(--gv-ink)]">
          {day}, {hours}
        </h3>
        {insight ? (
          <p className="mt-3 max-w-[560px] text-[14px] leading-[1.5] text-[color:var(--gv-ink-3)]">
            {insight}
          </p>
        ) : null}
      </div>

      <div>
        <p className="gv-mono text-[9px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          3 cửa sổ cao nhất
        </p>
        <ol className="mt-2 flex flex-col gap-2 text-[12px]">
          {top3.map((w) => (
            <li key={`${w.day}-${w.hours}`} className="flex items-center gap-2">
              <span className="gv-mono w-5 text-[color:var(--gv-accent)] font-semibold">
                {String(w.rank).padStart(2, "0")}
              </span>
              <span className="flex-1 text-[color:var(--gv-ink-2)]">
                {w.day} · {w.hours}
              </span>
              <span className="gv-mono text-[color:var(--gv-accent-deep)]">
                ▲ {w.lift_multiplier.toFixed(1)}×
              </span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
