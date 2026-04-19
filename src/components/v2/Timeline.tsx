import type { VideoSegment } from "@/lib/api-types";
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
        className="flex h-9 overflow-hidden rounded-[6px] border border-[color:var(--gv-rule)]"
        role="list"
        aria-label="Dòng thời gian cấu trúc video"
      >
        {segs.map((s, i) => {
          const bg = segmentColorVar(s.color_key);
          const isEdge = i === 0 || i === segs.length - 1;
          return (
            <div
              key={`${s.name}-${i}`}
              role="listitem"
              className="flex min-w-0 flex-1 items-center justify-center px-0.5 text-center font-[family-name:var(--gv-font-mono)] text-[10px] font-semibold uppercase tracking-[0.05em]"
              style={{
                flexGrow: Math.max(s.pct, 1),
                flexBasis: 0,
                background: bg,
                color: isEdge ? "var(--gv-paper)" : "var(--gv-canvas)",
              }}
              title={`${s.name} · ${s.pct}%`}
            >
              <span className="truncate">{s.name}</span>
            </div>
          );
        })}
      </div>
      <div className="mt-1.5 flex justify-between font-[family-name:var(--gv-font-mono)] text-[10px] text-[color:var(--gv-ink-4)]">
        {ticks.map((t) => (
          <span key={t}>{t}</span>
        ))}
      </div>
    </div>
  );
}
