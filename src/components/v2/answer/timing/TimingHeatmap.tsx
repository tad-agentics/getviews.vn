/**
 * Phase C.4.3 — Timing heatmap (7 days × 8 hour buckets).
 *
 * Cell tone lifted from `thread-turns.jsx:101-107` via
 * `timingFormat.cellBackgroundForValue` so all colours resolve through
 * `--gv-*` tokens (no rgba, no hex, no purple shims).
 *
 * Value labels: show rounded score for cells ≥ 5 only; lower scores stay
 * blank so sparse cells do not read as “confident” counts.
 */

import type { TimingReportPayload } from "@/lib/api-types";
import { TIMING_DAYS_VN, TIMING_HOURS_VN, isTimingHeatmapGrid } from "@/lib/timingGridLabels";
import {
  cellBackgroundForValue,
  cellBorderForValue,
  cellLabelColorForValue,
} from "./timingFormat";

export function TimingHeatmap({
  grid,
  legendFooter,
}: {
  grid: TimingReportPayload["grid"];
  /** Right-aligned footer text, e.g. "Dữ liệu từ 112 video · niche Tech". */
  legendFooter?: string;
}) {
  if (!isTimingHeatmapGrid(grid)) {
    return null;
  }

  return (
    <section>
      <p className="gv-mono mb-[10px] text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)] font-semibold">
        Lưới khung giờ (ICT) · 7 ngày × 8 khung
      </p>
      <div className="overflow-x-auto">
        <div
          className="grid min-w-[580px] gap-[3px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-[10px]"
          style={{ gridTemplateColumns: "28px repeat(8, minmax(0, 1fr))" }}
        >
          <div />
          {TIMING_HOURS_VN.map((h) => (
            <div
              key={h}
              className="gv-mono px-0 py-[2px] text-center text-[9px] text-[color:var(--gv-ink-4)]"
            >
              {h}
            </div>
          ))}
          {TIMING_DAYS_VN.map((d, di) => (
            <Row key={d} label={d} values={grid[di]!} />
          ))}
        </div>
      </div>
      <div className="mt-[10px] flex items-center gap-3 text-[10px]">
        <span className="gv-mono text-[color:var(--gv-ink-4)]">Thấp</span>
        {[0, 3, 5, 7, 9].map((v) => (
          <span
            key={v}
            aria-hidden
            className="h-3 w-4 border border-[color:var(--gv-rule)]"
            style={{ backgroundColor: cellBackgroundForValue(v) }}
          />
        ))}
        <span className="gv-mono text-[color:var(--gv-ink-4)]">Cao</span>
        <span className="flex-1" />
        {legendFooter ? (
          <span className="gv-mono text-[color:var(--gv-ink-4)]">{legendFooter}</span>
        ) : null}
      </div>
    </section>
  );
}

function Row({ label, values }: { label: string; values: number[] }) {
  return (
    <>
      <div className="gv-mono flex items-center text-[10px] font-medium text-[color:var(--gv-ink-3)]">
        {label}
      </div>
      {values.map((v, hi) => (
        <div
          key={hi}
          aria-label={`${label} · ${TIMING_HOURS_VN[hi]} · ${Number.isFinite(v) ? v.toFixed(1) : "—"}`}
          className="gv-mono flex items-center justify-center text-[10px]"
          style={{
            backgroundColor: cellBackgroundForValue(v),
            border: cellBorderForValue(v),
            color: cellLabelColorForValue(v),
            aspectRatio: "1.6 / 1",
            fontWeight: v >= 7 ? 600 : 400,
          }}
        >
          {v >= 5 ? Math.round(v) : ""}
        </div>
      ))}
    </>
  );
}
