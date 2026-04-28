/**
 * Phase C.4.3 — Timing report body. Locked render order (plan §C.4 design
 * spec):
 *
 *   ConfidenceStrip → HumilityBanner (thin) → TimingHeadline → Heatmap
 *                   → VarianceNote → FatigueBand (optional) → ActionCards
 *
 * Empty state (`sample_size < 80`) forwards to `TimingHeatmap` with
 * `maskBelowFive={true}` so cells below the value floor render blank; the
 * top-3 list in the headline still shows, matching plan §2.3 empty-state
 * contract.
 *
 * Variance chip `sparse` also triggers the mask so weak heatmaps never
 * ship false confidence.
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
  const varianceKind = (report.variance_note?.kind as string | undefined) ?? "strong";
  const maskBelowFive = thin || varianceKind === "sparse";
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

      <TimingHeatmap
        grid={report.grid}
        maskBelowFive={maskBelowFive}
        legendFooter={legendFooter}
      />

      <VarianceNote note={report.variance_note} />

      {report.fatigue_band ? <FatigueBand band={report.fatigue_band} /> : null}

      <CalendarStrip slots={report.calendar_slots ?? []} />

      {report.actions.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "240ms" }}>
          <p className="gv-mono mb-1 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
            Bước tiếp theo
          </p>
          <h3 className="gv-serif mb-3 text-[18px] text-[color:var(--gv-ink)]">
            {timingActionsSectionTitle(sessionIntentType)}
          </h3>
          <TimingActionCards actions={report.actions} />
        </section>
      ) : null}
    </div>
  );
}
