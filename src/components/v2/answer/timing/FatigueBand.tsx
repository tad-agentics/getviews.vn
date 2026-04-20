/**
 * Phase C.4.3 — Timing FatigueBand (plan §2.3 section 6 — NEW, optional).
 *
 * Shows only when the backend populates `fatigue_band` (streak ≥ 4 weeks).
 * The wrapper is a soft info band — ink-2 copy on canvas-2 with a mono
 * kicker — so it reads as "heads-up" rather than "error".
 */

import type { TimingReportPayload } from "@/lib/api-types";

export function FatigueBand({ band }: { band: TimingReportPayload["fatigue_band"] }) {
  if (!band) return null;
  const weeks = (band.weeks_at_top as number | undefined) ?? 0;
  const copy = (band.copy as string | undefined) ?? "";
  return (
    <aside
      role="note"
      className="flex flex-col gap-1 rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-4 py-3 text-[color:var(--gv-ink-2)]"
    >
      <p className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
        Cảnh báo bão hoà · {weeks} tuần
      </p>
      <p className="text-[13px] leading-[1.5]">{copy}</p>
    </aside>
  );
}
