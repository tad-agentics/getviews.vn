/**
 * StepProgress — shows the current pipeline step during streaming.
 * Displayed while status === "streaming" before narrative appears.
 */

import type { TrajectoryShape } from "@/lib/api-types";

export const TRAJECTORY_LABELS: Record<TrajectoryShape, string> = {
  decline_from_peak: "Kênh đang giảm từ đỉnh",
  stagnant: "Kênh đang trì trệ",
  steady_growth: "Kênh tăng trưởng đều",
  breakout: "Kênh breakout",
  bursty: "Kênh không đều",
  new_account: "Kênh mới",
};

interface StepProgressProps {
  activeStepIndex: number;
  activeStepLabel: string;
  heartbeatCount: number;
  trajectoryShape: TrajectoryShape | null;
}

export function StepProgress({
  activeStepIndex,
  activeStepLabel,
  heartbeatCount,
  trajectoryShape,
}: StepProgressProps) {
  // The BE currently emits 5 step events (Tải dữ liệu → Phân loại format →
  // Inflection → UGC creators → Soạn báo cáo). If a future step is added,
  // showing "6/5" would be wrong; clamp the denominator to the highest
  // index actually observed so the bar always reads "N/N or smaller".
  const totalSteps = Math.max(5, activeStepIndex);
  const elapsed = heartbeatCount * 10;

  return (
    <div className="flex flex-col gap-3 px-4 py-4" aria-live="polite">
      {/* Trajectory badge — shown once known */}
      {trajectoryShape && (
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[color:var(--gv-accent-soft)] self-start">
          <span className="text-xs font-medium text-[color:var(--gv-accent-deep)]">
            {TRAJECTORY_LABELS[trajectoryShape]}
          </span>
        </div>
      )}

      {/* Step bar */}
      {activeStepIndex >= 0 && (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <p className="text-sm text-[color:var(--gv-ink-3)]">{activeStepLabel}</p>
            <p className="text-xs text-[color:var(--gv-ink-3)] font-mono">
              {activeStepIndex}/{totalSteps}
            </p>
          </div>
          <div className="h-1 rounded-full bg-[color:var(--gv-canvas-2)]">
            <div
              className="h-1 rounded-full bg-[color:var(--primary)] transition-all duration-300"
              style={{ width: `${Math.min((activeStepIndex / totalSteps) * 100, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Elapsed time */}
      {elapsed > 0 && (
        <p className="text-xs text-[color:var(--gv-ink-3)]">
          Đang xử lý · {elapsed}s…
        </p>
      )}
    </div>
  );
}
