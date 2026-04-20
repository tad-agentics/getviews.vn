/**
 * Phase C.4.3 — Timing heatmap (7 days × 8 hour buckets).
 *
 * Cell tone lifted from `thread-turns.jsx:101-107` via
 * `timingFormat.cellBackgroundForValue` so all colours resolve through
 * `--gv-*` tokens (no rgba, no hex, no purple shims).
 *
 * Sparse-mode contract: when `variance_note.kind === "sparse"` the parent
 * passes `maskBelowFive={true}`; we hide value labels for cells < 5 to
 * avoid over-reading noise. Empty labels also mean fewer accessibility
 * announcements during keyboard traversal.
 */

import type { TimingReportPayload } from "@/lib/api-types";
import {
  cellBackgroundForValue,
  cellBorderForValue,
  cellLabelColorForValue,
} from "./timingFormat";

const DAYS_VN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
const HOURS_VN = ["6–9", "9–12", "12–15", "15–18", "18–20", "20–22", "22–24", "0–3"];

export function TimingHeatmap({
  grid,
  maskBelowFive,
  legendFooter,
}: {
  grid: TimingReportPayload["grid"];
  maskBelowFive: boolean;
  /** Right-aligned footer text, e.g. "Dữ liệu từ 112 video · niche Tech". */
  legendFooter?: string;
}) {
  return (
    <section>
      <p className="gv-mono mb-[10px] text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)] font-semibold">
        Heatmap · 7 ngày × 8 khung giờ
      </p>
      <div
        className="grid gap-[3px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-[10px]"
        style={{ gridTemplateColumns: "28px repeat(8, minmax(0, 1fr))" }}
      >
        <div />
        {HOURS_VN.map((h) => (
          <div
            key={h}
            className="gv-mono px-0 py-[2px] text-center text-[9px] text-[color:var(--gv-ink-4)]"
          >
            {h}
          </div>
        ))}
        {DAYS_VN.map((d, di) => (
          <Row
            key={d}
            label={d}
            values={grid[di] ?? []}
            maskBelowFive={maskBelowFive}
          />
        ))}
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

function Row({
  label,
  values,
  maskBelowFive,
}: {
  label: string;
  values: number[];
  maskBelowFive: boolean;
}) {
  return (
    <>
      <div className="gv-mono flex items-center text-[10px] font-medium text-[color:var(--gv-ink-3)]">
        {label}
      </div>
      {values.map((v, hi) => (
        <div
          key={hi}
          aria-label={`${label} · ${HOURS_VN[hi]} · ${v.toFixed(1)}`}
          className="gv-mono flex items-center justify-center text-[10px]"
          style={{
            backgroundColor: cellBackgroundForValue(v),
            border: cellBorderForValue(v),
            color: cellLabelColorForValue(v),
            aspectRatio: "1.6 / 1",
            fontWeight: v >= 7 ? 600 : 400,
          }}
        >
          {!maskBelowFive && v >= 5 ? Math.round(v) : ""}
        </div>
      ))}
    </>
  );
}
