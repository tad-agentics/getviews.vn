import type { RetentionPoint } from "@/lib/api-types";
import {
  areaPath,
  largestRetentionDropAnnotation,
  polylinePoints,
  retentionTMax,
  VB_H,
  VB_W,
} from "./retentionCurveMath";

export type RetentionCurveProps = {
  durationSec: number;
  userCurve: RetentionPoint[];
  benchmarkCurve?: RetentionPoint[] | null;
  className?: string;
};

/**
 * SVG retention chart — user curve (accent) + optional dashed niche benchmark (pos blue).
 * B.1.4 tighten: shared scale math, round caps, one drop annotation when slope is steep.
 */
export function RetentionCurve({
  durationSec,
  userCurve,
  benchmarkCurve,
  className = "",
}: RetentionCurveProps) {
  const userPts = polylinePoints(userCurve, durationSec);
  const benchPts =
    benchmarkCurve && benchmarkCurve.length
      ? polylinePoints(benchmarkCurve, durationSec)
      : "";
  const fillD = userCurve.length ? areaPath(userCurve, durationSec) : "";
  const dropNote = userCurve.length ? largestRetentionDropAnnotation(userCurve, durationSec) : null;

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((frac) => {
    const sec = durationSec * frac;
    const label =
      sec >= 60
        ? `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`
        : `${Math.round(sec)}s`;
    return label;
  });

  const tMaxUser = userCurve.length ? retentionTMax(userCurve, durationSec) : durationSec;

  return (
    <div className={`border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4 ${className}`.trim()}>
      <div className="gv-mono mb-3 text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
        Đường giữ chân · vs ngách
      </div>
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="h-20 w-full" role="img" aria-label="Biểu đồ giữ chân">
        {fillD ? (
          <path
            d={fillD}
            fill="color-mix(in srgb, var(--gv-accent) 12%, transparent)"
            stroke="none"
          />
        ) : null}
        {benchPts ? (
          <polyline
            fill="none"
            points={benchPts}
            stroke="var(--gv-pos)"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : null}
        {userPts ? (
          <polyline
            fill="none"
            points={userPts}
            stroke="var(--gv-accent)"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : (
          <text
            x={8}
            y={24}
            fill="var(--gv-ink-4)"
            fontSize={10}
            fontFamily="var(--gv-font-mono)"
          >
            Chưa có dữ liệu đường cong
          </text>
        )}
        {dropNote && userPts ? (
          <text
            x={dropNote.cx}
            y={dropNote.cy}
            fill="var(--gv-accent-deep)"
            fontSize={9}
            fontFamily="var(--gv-font-mono)"
          >
            {dropNote.label}
          </text>
        ) : null}
      </svg>
      <div className="mt-1 flex justify-between font-[family-name:var(--gv-font-mono)] text-[10px] text-[color:var(--gv-ink-4)]">
        {ticks.map((t, i) => (
          <span key={`${i}-${t}`}>{t}</span>
        ))}
      </div>
      <p className="sr-only">
        Trục thời gian tối đa khoảng {Math.round(tMaxUser)} giây; phần trăm giữ chân từ 0 đến 100.
      </p>
    </div>
  );
}
