import { lazy, Suspense } from "react";

import type { RetentionPoint } from "@/lib/api-types";
import { RETENTION_CURVE_LEGEND_VI } from "@/lib/retentionCurveLegend";

export interface RetentionRiskEvent {
  t: number;
  severity?: number;
  reason_vi?: string;
  source?: string;
}

const RetentionCurveChartInner = lazy(() =>
  import("./RetentionCurveChartInner").then((m) => ({ default: m.RetentionCurveChartInner })),
);

export function RetentionCurveChart({
  userCurve,
  nicheCurve,
  durationSec,
  riskEvents,
}: {
  userCurve: RetentionPoint[];
  nicheCurve?: RetentionPoint[] | null;
  durationSec: number;
  riskEvents?: RetentionRiskEvent[] | null;
}) {
  if (!userCurve?.length) return null;

  const topRisk = riskEvents?.[0];
  const riskLabel =
    topRisk && typeof topRisk.t === "number" && topRisk.reason_vi?.trim()
      ? `${topRisk.t.toFixed(1)}s — ${topRisk.reason_vi.trim()}`
      : null;

  return (
    <div className="mt-3 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-3">
      <p className="gv-kicker mb-1 text-[11px] text-[color:var(--gv-ink-3)]">Đường cong giữ chân</p>
      <Suspense
        fallback={
          <div
            className="flex h-[140px] items-center justify-center text-xs text-[color:var(--gv-ink-4)]"
            aria-hidden
          >
            Đang tải biểu đồ…
          </div>
        }
      >
        <RetentionCurveChartInner
          userCurve={userCurve}
          nicheCurve={nicheCurve}
          durationSec={durationSec}
          markSec={topRisk?.t}
        />
      </Suspense>
      <p className="mt-2 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
        {RETENTION_CURVE_LEGEND_VI}
      </p>
      {riskLabel ? (
        <p className="mt-1 text-[13px] font-medium leading-snug text-[color:var(--gv-accent)]">
          Rớt mạnh nhất: {riskLabel}
        </p>
      ) : null}
    </div>
  );
}
