import { ArrowRight } from "lucide-react";
import { Btn } from "@/components/v2/Btn";

export type ScriptForecastBarProps = {
  durationSec: number;
  hookDelayMs: number;
};

/** Deterministic forecast from ``phase-b-plan.md`` / ``script.jsx`` — no API. */
export function scriptForecastViews(durationSec: number): number {
  const goodLen = durationSec >= 22 && durationSec <= 40;
  return goodLen ? 62 : 34;
}

export function scriptForecastRetentionPct(durationSec: number): number {
  const goodLen = durationSec >= 22 && durationSec <= 40;
  return goodLen ? 72 : 54;
}

export function scriptHookScore(hookDelayMs: number): number {
  if (hookDelayMs <= 1400) return 8.4;
  if (hookDelayMs <= 2000) return 6.2;
  return 4.1;
}

export function ScriptForecastBar({ durationSec, hookDelayMs }: ScriptForecastBarProps) {
  const viewsK = scriptForecastViews(durationSec);
  const ret = scriptForecastRetentionPct(durationSec);
  const hookScore = scriptHookScore(hookDelayMs);

  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 bg-[color:var(--gv-ink)] px-5 py-4 text-[color:var(--gv-canvas)]">
      <div>
        <div className="gv-mono gv-uc mb-1 text-[9.5px] tracking-[0.16em] opacity-50">DỰ KIẾN HIỆU SUẤT</div>
        <p className="text-sm leading-snug">
          <span className="gv-tight gv-serif text-[28px] font-medium leading-none tracking-[-0.02em]">~{viewsK}K</span>
          <span className="opacity-60"> view · </span>
          giữ chân <span className="text-[rgb(0,159,250)]">{ret}%</span> · hook{" "}
          <span className="text-[color:var(--gv-accent)]">{hookScore.toFixed(1)}/10</span>
        </p>
      </div>
      <Btn variant="accent" type="button" className="shrink-0 gap-1" disabled title="Sắp có">
        Lưu vào lịch quay
        <ArrowRight className="h-3 w-3" strokeWidth={2} aria-hidden />
      </Btn>
    </div>
  );
}
