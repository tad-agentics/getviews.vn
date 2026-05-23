/**
 * Phase C.4.3 — Timing report body. Locked render order (plan §C.4 design
 * spec):
 *
 *   ConfidenceStrip → HumilityBanner (thin) → TimingHeadline → Heatmap
 *                   → VarianceNote → FatigueBand (optional) → ActionCards
 *
 * `TimingHeatmap` omits numeric labels for cells with score &lt; 5; thin
 * samples (`sample_size &lt; 80`) still show a real corpus grid with
 * `variance_note.kind === "sparse"`.
 */

import { useState } from "react";

import type { TimingReportPayload } from "@/lib/api-types";

import { ConfidenceStrip } from "../pattern/ConfidenceStrip";
import { HumilityBanner } from "../pattern/HumilityBanner";
import { CalendarStrip } from "./CalendarStrip";
import { FatigueBand } from "./FatigueBand";
import { TimingActionCards } from "./TimingActionCards";
import { TimingHeadline } from "./TimingHeadline";
import { TimingHeatmap } from "./TimingHeatmap";
import { VarianceNote } from "./VarianceNote";
import { timingActionsSectionTitle } from "../sessionIntentLabels";

export function TimingBody({
  report,
  sessionIntentType,
}: {
  report: TimingReportPayload;
  sessionIntentType?: string;
}) {
  const thin = report.confidence.sample_size < 80;
  const [humilityOpen, setHumilityOpen] = useState(true);

  const legendFooter = `Dữ liệu từ ${report.confidence.sample_size} video · ngách ${
    report.confidence.niche_scope ?? "—"
  }`;

  return (
    <div className="space-y-8 text-sm text-[color:var(--gv-ink-2)]">
      <ConfidenceStrip
        data={report.confidence}
        thinSample={thin}
        humilityVisible={humilityOpen}
        onHumilityToggle={() => setHumilityOpen((v) => !v)}
      />

      {thin && humilityOpen ? <HumilityBanner /> : null}

      <TimingHeadline report={report} sessionIntentType={sessionIntentType} />

      <TimingHeatmap grid={report.grid} legendFooter={legendFooter} />

      <VarianceNote note={report.variance_note} />

      {report.contrarian_note ? (
        <div className="mt-4 rounded-lg bg-[color:var(--gv-accent-soft)] px-4 py-3">
          <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-widest text-[color:var(--gv-accent)]">
            Insight thực tế
          </p>
          <p className="text-sm leading-relaxed text-[color:var(--gv-ink-2)]">{report.contrarian_note}</p>
        </div>
      ) : null}

      {report.fatigue_band ? <FatigueBand band={report.fatigue_band} /> : null}

      <CalendarStrip slots={report.calendar_slots ?? []} />

      {report.actions.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "240ms" }}>
          <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">
            Bước tiếp theo
          </p>
          <h3 className="gv-serif mb-3 text-[17px] text-[color:var(--gv-ink)]">
            {timingActionsSectionTitle(sessionIntentType)}
          </h3>
          <TimingActionCards actions={report.actions} />
        </section>
      ) : null}
    </div>
  );
}
