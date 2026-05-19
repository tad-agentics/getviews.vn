/**
 * Corpus posting heatmap — embedded evidence under v6 section prose (same slot as VideoTileRow).
 */

import type { DiagnosisPostingContextPayload, TimingReportPayload } from "@/lib/api-types";
import { TimingHeatmap } from "@/components/v2/answer/timing/TimingHeatmap";
import { VarianceNote } from "@/components/v2/answer/timing/VarianceNote";
import { isTimingHeatmapGrid } from "@/lib/timingGridLabels";

export function PostingHeatmapEmbed({ payload }: { payload: DiagnosisPostingContextPayload }) {
  if (!isTimingHeatmapGrid(payload.grid)) return null;

  const footer = [
    `${payload.sample_size} video`,
    `~${payload.window_days} ngày`,
    payload.niche_label?.trim(),
  ]
    .filter(Boolean)
    .join(" · ");

  const note = payload.variance_note as TimingReportPayload["variance_note"];

  return (
    <div
      className="mt-4 border-t border-[color:var(--gv-rule)] pt-4"
      aria-label="Bằng chứng khung giờ corpus"
    >
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-[color:var(--muted)]">
        Corpus khung giờ đăng (7 ngày × 8 khung · ICT)
      </p>
      <div className="mb-2">
        <VarianceNote note={note} />
      </div>
      <div className="max-w-[min(100%,20rem)] rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-2">
        <TimingHeatmap grid={payload.grid} legendFooter={footer} variant="embed" />
      </div>
    </div>
  );
}
