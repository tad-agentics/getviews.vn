import type { VideoSegment } from "@/lib/api-types";
import {
  formatStructureTimeRange,
  structureBeatLabelVi,
} from "@/lib/structureTimeline";
import { segmentColorVar } from "./segmentColorKey";

export type TimelineProps = {
  segments: VideoSegment[];
  durationSec: number;
  className?: string;
};

/**
 * Eight-segment flex bar from structural decomposition + timestamp axis.
 */
export function Timeline({ segments, durationSec, className = "" }: TimelineProps) {
  const segs = segments.length ? segments : [];
  const tMax = Math.max(durationSec, 1);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const sec = tMax * f;
    const label =
      sec >= 60
        ? `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`
        : `${Math.round(sec)}s`;
    return label;
  });

  return (
    <div className={className}>
      <div
        className="flex h-10 overflow-hidden rounded-[6px] border border-[color:var(--gv-rule)]"
        role="list"
        aria-label="Dòng thời gian cấu trúc video"
      >
        {segs.map((s, i) => {
          const bg = segmentColorVar(s.color_key);
          const isEdge = i === 0 || i === segs.length - 1;
          const labelVi = structureBeatLabelVi(s.name);
          const hasRange =
            s.start_sec != null &&
            s.end_sec != null &&
            Number.isFinite(s.start_sec) &&
            Number.isFinite(s.end_sec);
          const rangeLabel = hasRange
            ? formatStructureTimeRange(s.start_sec!, s.end_sec!)
            : `${s.pct}%`;
          const title = hasRange
            ? `${labelVi} · ${rangeLabel} (${s.pct}% clip)`
            : `${labelVi} · ${s.pct}% clip`;
          return (
            <div
              key={`${s.name}-${i}`}
              role="listitem"
              className="flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-0.5 py-0.5 text-center font-[family-name:var(--gv-font-mono)] text-[11px] font-semibold gv-kicker leading-tight tracking-[0.05em]"
              style={{
                flexGrow: Math.max(s.pct, 1),
                flexBasis: 0,
                background: bg,
                color: isEdge ? "var(--gv-paper)" : "var(--gv-canvas)",
              }}
              title={title}
            >
              <span className="truncate">{labelVi}</span>
              <span
                className={`text-[11px] font-normal normal-case tabular-nums tracking-normal ${
                  isEdge
                    ? "text-[color:color-mix(in_srgb,var(--gv-paper)_82%,transparent)]"
                    : "text-[color:color-mix(in_srgb,var(--gv-canvas)_55%,var(--gv-ink)_45%)]"
                }`}
              >
                {rangeLabel}
              </span>
            </div>
          );
        })}
      </div>
      <div className="mt-1.5 flex justify-between font-[family-name:var(--gv-font-mono)] text-[11px] text-[color:var(--gv-ink-4)]">
        {ticks.map((t) => (
          <span key={t}>{t}</span>
        ))}
      </div>
    </div>
  );
}
