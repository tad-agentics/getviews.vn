import type { RetentionPoint } from "@/lib/api-types";

export type RetentionCurveProps = {
  durationSec: number;
  userCurve: RetentionPoint[];
  benchmarkCurve?: RetentionPoint[] | null;
  className?: string;
};

const VB_W = 400;
const VB_H = 80;

function polylinePoints(curve: RetentionPoint[], durationSec: number): string {
  if (!curve.length) return "";
  const lastT = curve[curve.length - 1]?.t ?? 0;
  const tMax = Math.max(durationSec, lastT, 0.001);
  return curve
    .map((p) => {
      const x = (p.t / tMax) * VB_W;
      const pct = Math.min(100, Math.max(0, p.pct));
      const y = VB_H - (pct / 100) * (VB_H - 10) - 5;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function areaPath(curve: RetentionPoint[], durationSec: number): string {
  if (!curve.length) return "";
  const lastT = curve[curve.length - 1]?.t ?? 0;
  const tMax = Math.max(durationSec, lastT, 0.001);
  const xy = curve.map((p) => {
    const x = (p.t / tMax) * VB_W;
    const pct = Math.min(100, Math.max(0, p.pct));
    const y = VB_H - (pct / 100) * (VB_H - 10) - 5;
    return [x, y] as const;
  });
  let d = `M 0,${VB_H} L ${xy[0][0]},${xy[0][1]}`;
  for (let i = 1; i < xy.length; i++) {
    d += ` L ${xy[i][0]},${xy[i][1]}`;
  }
  d += ` L ${xy[xy.length - 1][0]},${VB_H} Z`;
  return d;
}

/**
 * SVG retention chart — user curve (accent) + optional dashed niche benchmark (pos blue).
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

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const sec = durationSec * f;
    const label =
      sec >= 60
        ? `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`
        : `${Math.round(sec)}s`;
    return { f, label };
  });

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
          />
        ) : null}
        {userPts ? (
          <polyline
            fill="none"
            points={userPts}
            stroke="var(--gv-accent)"
            strokeWidth={2.5}
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
      </svg>
      <div className="mt-1 flex justify-between font-[family-name:var(--gv-font-mono)] text-[10px] text-[color:var(--gv-ink-4)]">
        {ticks.map((t) => (
          <span key={t.label}>{t.label}</span>
        ))}
      </div>
    </div>
  );
}
