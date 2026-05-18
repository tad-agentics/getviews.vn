/**
 * Niche posting heatmap embedded in video/carousel diagnosis (corpus 7×8 grid).
 * Data from Cloud Run `niche_posting_context` — not the full Timing report payload.
 */

import type { DiagnosisPostingContextPayload, TimingReportPayload } from "@/lib/api-types";
import { TimingHeatmap } from "@/components/v2/answer/timing/TimingHeatmap";
import { VarianceNote } from "@/components/v2/answer/timing/VarianceNote";
import { isTimingHeatmapGrid } from "@/lib/timingGridLabels";

export function DiagnosisPostingContextBlock({ payload }: { payload: DiagnosisPostingContextPayload }) {
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
    <section
      className="mb-6 rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4"
      aria-label="Khung giờ đăng trong ngách"
    >
      <h3 className="gv-mono mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
        Khung giờ đăng trong ngách
      </h3>
      <div className="mb-4">
        <VarianceNote note={note} />
      </div>
      {payload.user_post_window_vi ? (
        <p className="mb-3 text-[12px] leading-relaxed text-[color:var(--gv-ink-3)]">
          {payload.user_post_window_vi}
        </p>
      ) : null}
      <TimingHeatmap grid={payload.grid} legendFooter={footer} />
      {payload.top_3_windows?.length ? (
        <div className="mt-4">
          <p className="gv-mono mb-2 text-[10px] font-semibold uppercase tracking-wide text-[color:var(--gv-ink-4)]">
            Top cửa sổ (median views trong ô)
          </p>
          <ol className="m-0 list-decimal space-y-1.5 pl-4 text-[12px] text-[color:var(--gv-ink-2)]">
            {payload.top_3_windows.map((w, i) => {
              const day = String(w.day ?? "");
              const hours = String(w.hours ?? "");
              const liftRaw = w.lift_multiplier;
              const lift = typeof liftRaw === "number" ? liftRaw : Number(liftRaw);
              const samp = w.sample;
              return (
                <li key={`${i}-${day}-${hours}`}>
                  <span className="text-foreground">
                    {day} {hours}
                  </span>
                  {Number.isFinite(lift) ? ` — ~${lift}× trung vị ngách` : ""}
                  {typeof samp === "number" ? ` · ${samp} clip` : ""}
                </li>
              );
            })}
          </ol>
        </div>
      ) : null}
    </section>
  );
}
