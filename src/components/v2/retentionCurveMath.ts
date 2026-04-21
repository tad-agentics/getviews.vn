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

type DropSeg = {
  d: number;
  tMid: number;
  x: number;
  y: number;
  label: string;
};

function _labelForDrop(d: number, tMid: number): string {
  const tLabel = tMid < 10 ? tMid.toFixed(1) : String(Math.round(tMid));
  return `drop −${Math.round(-d)}% @ ${tLabel}s`;
}

/** Place mono label near curve point (viewBox units). */
function _placeAnnotation(x: number, y: number): { cx: number; cy: number } {
  const cx = Math.min(VB_W - 72, Math.max(8, x - 24));
  const cy = Math.max(12, y - 8);
  return { cx, cy };
}

const MIN_ANNOTATION_X_GAP = VB_W / 5;

/**
 * Up to two steepest downward steps as SVG label anchors. Second pick skips
 * segments whose curve midpoint **x** is within ``VB_W/5`` of the first. If
 * the second label's **cy** is within 8px of the first's, the second is
 * shifted down by 10px.
 */
export function retentionDropAnnotations(
  curve: RetentionPoint[],
  durationSec: number,
  opts?: { minDropPct?: number },
): { cx: number; cy: number; label: string }[] {
  const minDrop = opts?.minDropPct ?? 4;
  if (curve.length < 2) return [];
  const tMax = retentionTMax(curve, durationSec);
  const segs: DropSeg[] = [];
  for (let i = 0; i < curve.length - 1; i++) {
    const d = curve[i + 1].pct - curve[i].pct;
    if (d >= -minDrop) continue;
    const tMid = (curve[i].t + curve[i + 1].t) / 2;
    const pctMid = (curve[i].pct + curve[i + 1].pct) / 2;
    const { x, y } = retentionPointXY({ t: tMid, pct: pctMid }, tMax);
    segs.push({ d, tMid, x, y, label: _labelForDrop(d, tMid) });
  }
  if (!segs.length) return [];
  segs.sort((a, b) => a.d - b.d);

  const first = segs[0];
  const p1 = _placeAnnotation(first.x, first.y);
  const out: { cx: number; cy: number; label: string }[] = [{ cx: p1.cx, cy: p1.cy, label: first.label }];

  let second: DropSeg | null = null;
  for (let k = 1; k < segs.length; k++) {
    if (Math.abs(segs[k].x - first.x) >= MIN_ANNOTATION_X_GAP) {
      second = segs[k];
      break;
    }
  }
  if (!second) return out;

  let { cx: cx2, cy: cy2 } = _placeAnnotation(second.x, second.y);
  if (Math.abs(cy2 - p1.cy) < 8) {
    cy2 += 10;
  }
  out.push({ cx: cx2, cy: cy2, label: second.label });
  return out;
}

export { VB_H, VB_W };
