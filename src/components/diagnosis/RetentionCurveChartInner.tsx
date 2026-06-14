import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  XAxis,
  YAxis,
} from "recharts";

import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { RetentionPoint } from "@/lib/api-types";

function mergeSeries(
  userCurve: RetentionPoint[],
  nicheCurve: RetentionPoint[] | null | undefined,
  durationSec: number,
): Array<{ t: number; user: number; niche: number | null }> {
  const maxT = Math.max(durationSec, ...userCurve.map((p) => p.t), ...(nicheCurve ?? []).map((p) => p.t));
  const steps = userCurve.length >= 2 ? userCurve.length : 20;
  const out: Array<{ t: number; user: number; niche: number | null }> = [];

  const interp = (curve: RetentionPoint[], t: number): number => {
    if (!curve.length) return 0;
    if (t <= curve[0]!.t) return curve[0]!.pct;
    for (let i = 1; i < curve.length; i++) {
      const a = curve[i - 1]!;
      const b = curve[i]!;
      if (t <= b.t) {
        const span = b.t - a.t || 1;
        const r = (t - a.t) / span;
        return a.pct + r * (b.pct - a.pct);
      }
    }
    return curve[curve.length - 1]!.pct;
  };

  for (let i = 0; i < steps; i++) {
    const t = (maxT * i) / Math.max(1, steps - 1);
    out.push({
      t: Math.round(t * 10) / 10,
      user: Math.round(interp(userCurve, t)),
      niche: nicheCurve?.length ? Math.round(interp(nicheCurve, t)) : null,
    });
  }
  return out;
}

const chartConfig = {
  user: { label: "Video bạn", color: "var(--gv-accent)" },
  niche: { label: "TB ngách", color: "var(--gv-ink-3)" },
};

export function RetentionCurveChartInner({
  userCurve,
  nicheCurve,
  durationSec,
  markSec,
}: {
  userCurve: RetentionPoint[];
  nicheCurve?: RetentionPoint[] | null;
  durationSec: number;
  markSec?: number;
}) {
  const data = mergeSeries(userCurve, nicheCurve, durationSec);
  const markPoint =
    markSec != null && Number.isFinite(markSec)
      ? data.reduce<{ t: number; user: number } | null>((best, row) => {
          if (Math.abs(row.t - markSec!) < Math.abs((best?.t ?? Infinity) - markSec!)) {
            return { t: row.t, user: row.user };
          }
          return best;
        }, null)
      : null;

  return (
    <ChartContainer config={chartConfig} className="aspect-[2/1] h-[140px] w-full min-h-[120px]">
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="t"
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}s`}
          fontSize={11}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          width={36}
          fontSize={11}
        />
        <ChartTooltip content={<ChartTooltipContent />} />
        {nicheCurve?.length ? (
          <Line
            type="monotone"
            dataKey="niche"
            stroke="var(--gv-ink-3)"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={false}
            connectNulls
          />
        ) : null}
        <Line
          type="monotone"
          dataKey="user"
          stroke="var(--gv-accent)"
          strokeWidth={2}
          dot={false}
        />
        {markPoint ? (
          <ReferenceDot
            x={markPoint.t}
            y={markPoint.user}
            r={5}
            fill="var(--gv-danger)"
            stroke="var(--gv-paper)"
            strokeWidth={2}
          />
        ) : null}
      </LineChart>
    </ChartContainer>
  );
}
