/**
 * Phase C.5.3 — PatternSubreport wrapper.
 *
 * Plan §A.4 "Report + timing" merge: when Pattern's `subreports.timing`
 * is populated, render a boxed TimingBody between `PatternCells` and
 * `ActionCards`. Kicker signals the merge: `KÈM THEO · TIMING`.
 *
 * Subreport keys we know about today:
 *   - `timing` → full `TimingBody` (heatmap + headline + variance + fatigue)
 *
 * Unknown keys are ignored — Pattern is the primary payload, subreports
 * are additive.
 */

import type { PatternReportPayload, TimingReportPayload } from "@/lib/api-types";

import { TimingBody } from "../timing/TimingBody";

type SubreportsDict = Record<string, unknown>;

export function PatternSubreports({ report }: { report: PatternReportPayload }) {
  const subs = report.subreports as SubreportsDict | null | undefined;
  if (!subs || typeof subs !== "object") return null;

  const timing = subs.timing as TimingReportPayload | undefined;
  if (!timing) return null;

  return (
    <section
      className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4"
      aria-label="Timing subreport"
    >
      <p className="gv-mono mb-3 text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)] font-semibold">
        Kèm theo · Timing
      </p>
      <TimingBody report={timing} />
    </section>
  );
}
