import type { RetentionPoint } from "@/lib/api-types";

const VB_W = 400;
const VB_H = 80;

/** Horizontal scale: last sample time vs declared duration. */
export function retentionTMax(curve: RetentionPoint[], durationSec: number): number {
  if (!curve.length) return Math.max(durationSec, 0.001);
  const lastT = curve[curve.length - 1]?.t ?? 0;
  return Math.max(durationSec, lastT, 0.001);
}

export function retentionPointXY(
  p: RetentionPoint,
  tMax: number,
): { x: number; y: number } {
  const x = (p.t / tMax) * VB_W;
  const pct = Math.min(100, Math.max(0, p.pct));
  const y = VB_H - (pct / 100) * (VB_H - 10) - 5;
  return { x, y };
}

export function polylinePoints(curve: RetentionPoint[], durationSec: number): string {
  if (!curve.length) return "";
  const tMax = retentionTMax(curve, durationSec);
  return curve
    .map((p) => {
      const { x, y } = retentionPointXY(p, tMax);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function areaPath(curve: RetentionPoint[], durationSec: number): string {
  if (!curve.length) return "";
  const tMax = retentionTMax(curve, durationSec);
  const xy = curve.map((p) => retentionPointXY(p, tMax));
  let d = `M 0,${VB_H} L ${xy[0].x},${xy[0].y}`;
  for (let i = 1; i < xy.length; i++) {
    d += ` L ${xy[i].x},${xy[i].y}`;
  }
  d += ` L ${xy[xy.length - 1].x},${VB_H} Z`;
  return d;
}

/** Single largest downward step (for one light-weight SVG label). */
export function largestRetentionDropAnnotation(
  curve: RetentionPoint[],
  durationSec: number,
  opts?: { minDropPct?: number },
): { cx: number; cy: number; label: string } | null {
  const minDrop = opts?.minDropPct ?? 4;
  if (curve.length < 2) return null;
  const tMax = retentionTMax(curve, durationSec);
  let best = -Infinity;
  let idx = -1;
  for (let i = 0; i < curve.length - 1; i++) {
    const d = curve[i + 1].pct - curve[i].pct;
    if (d < best) {
      best = d;
      idx = i;
    }
  }
  if (idx < 0 || best >= -minDrop) return null;
  const tMid = (curve[idx].t + curve[idx + 1].t) / 2;
  const pctMid = (curve[idx].pct + curve[idx + 1].pct) / 2;
  const { x, y } = retentionPointXY({ t: tMid, pct: pctMid }, tMax);
  const cx = Math.min(VB_W - 72, Math.max(8, x - 24));
  const cy = Math.max(12, y - 8);
  const label = `−${Math.round(-best)}% @ ${tMid < 10 ? tMid.toFixed(1) : Math.round(tMid)}s`;
  return { cx, cy, label };
}

export { VB_H, VB_W };
