/**
 * Phase C.4.3 — Timing heatmap (7 days × 8 hour buckets).
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
  variant = "default",
}: {
  grid: TimingReportPayload["grid"];
  legendFooter?: string;
  /** `compact` — standalone card; `embed` — inside section evidence (no section heading). */
  variant?: "default" | "compact" | "embed";
}) {
  if (!isTimingHeatmapGrid(grid)) {
    return null;
  }

  const embed = variant === "embed";
  const compact = embed || variant === "compact";

  const gridBlock = (
    <>
      <div className={embed ? "" : compact ? "max-w-[min(100%,22rem)]" : "overflow-x-auto"}>
        <div
          className={`grid ${
            embed
              ? "gap-[2px]"
              : compact
                ? "gap-[2px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-1.5"
                : "min-w-[580px] gap-[3px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-[10px]"
          }`}
          style={{
            gridTemplateColumns: compact
              ? "20px repeat(8, minmax(0, 1fr))"
              : "28px repeat(8, minmax(0, 1fr))",
          }}
        >
          <div />
          {TIMING_HOURS_VN.map((h) => (
            <div
              key={h}
              className={`gv-mono px-0 text-center text-[color:var(--gv-ink-4)] ${
                compact ? "py-0 text-[11px]" : "py-[2px] text-[11px]"
              }`}
            >
              {h}
            </div>
          ))}
          {TIMING_DAYS_VN.map((d, di) => (
            <Row key={d} label={d} values={grid[di]!} compact={compact} />
          ))}
        </div>
      </div>
      <div
        className={`flex items-center gap-3 text-[11px] ${compact ? "mt-1.5 gap-2 text-[11px]" : "mt-[10px]"}`}
      >
        <span className="gv-mono text-[color:var(--gv-ink-4)]">Thấp</span>
        {[0, 3, 5, 7, 9].map((v) => (
          <span
            key={v}
            aria-hidden
            className={`border border-[color:var(--gv-rule)] ${compact ? "h-2 w-3" : "h-3 w-4"}`}
            style={{ backgroundColor: cellBackgroundForValue(v) }}
          />
        ))}
        <span className="gv-mono text-[color:var(--gv-ink-4)]">Cao</span>
        <span className="flex-1" />
        {legendFooter ? (
          <span className="gv-mono text-[color:var(--gv-ink-4)]">{legendFooter}</span>
        ) : null}
      </div>
    </>
  );

  if (embed) {
    return <div className="min-w-0">{gridBlock}</div>;
  }

  return (
    <section>
      <p
        className={`gv-mono uppercase tracking-wide text-[color:var(--gv-accent)] font-semibold ${
          compact ? "mb-1.5 text-[11px]" : "mb-[10px] text-[11px]"
        }`}
      >
        Lưới khung giờ (ICT) · 7 ngày × 8 khung
      </p>
      {gridBlock}
    </section>
  );
}

function Row({
  label,
  values,
  compact,
}: {
  label: string;
  values: number[];
  compact: boolean;
}) {
  return (
    <>
      <div
        className={`gv-mono flex items-center font-medium text-[color:var(--gv-ink-3)] ${
          compact ? "text-[11px]" : "text-[11px]"
        }`}
      >
        {label}
      </div>
      {values.map((v, hi) => (
        <div
          key={hi}
          aria-label={`${label} · ${TIMING_HOURS_VN[hi]} · ${Number.isFinite(v) ? v.toFixed(1) : "—"}`}
          className={`gv-mono flex items-center justify-center ${
            compact ? "min-h-[14px] text-[11px]" : "text-[11px]"
          }`}
          style={{
            backgroundColor: cellBackgroundForValue(v),
            border: cellBorderForValue(v),
            color: cellLabelColorForValue(v),
            aspectRatio: compact ? "1.35 / 1" : "1.6 / 1",
            fontWeight: v >= 7 ? 600 : 400,
          }}
        >
          {v >= (compact ? 6 : 5) ? Math.round(v) : ""}
        </div>
      ))}
    </>
  );
}
