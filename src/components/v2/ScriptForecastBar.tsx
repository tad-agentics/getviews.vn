import { ArrowRight, Loader2 } from "lucide-react";
import { Btn } from "@/components/v2/Btn";

/**
 * Acknowledged tech-debt — the three forecast helpers below
 * (``scriptForecastViews`` / ``scriptForecastRetentionPct`` /
 * ``scriptHookScore``) ship deterministic placeholders from
 * ``artifacts/plans/phase-b-plan.md``. They turn duration + hook
 * delay into a "rough enough" preview number so the bar has
 * something to render before the corpus-backed forecast API
 * lands; the cut-points (22-40s sweet spot, 1.4s/2.0s hook
 * thresholds) come from the phase-B exploratory analysis on the
 * VN corpus and have held up directionally for the screens we've
 * shipped against them.
 *
 * The corpus-backed forecast (per-niche regression on
 * ``video_corpus``) lives in ``artifacts/plans/phase-d-plan.md``
 * as a follow-up; until that lands the placeholders are the
 * intended path. No ``TODO(owner@date)`` because there's no
 * commitment to swap them at a specific date — the swap happens
 * when the API exists. Tracked-not-targeted.
 */

export type ScriptForecastBarProps = {
  durationSec: number;
  hookDelayMs: number;
  /** When set, enables the save CTA (same flow as ScriptScreen `handleSave`). */
  onSaveDraft?: () => void | Promise<void>;
  savePending?: boolean;
  /** Draft already persisted this session (e.g. after Copy); label shows "Đã lưu". */
  saved?: boolean;
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

export function ScriptForecastBar({
  durationSec,
  hookDelayMs,
  onSaveDraft,
  savePending = false,
  saved = false,
}: ScriptForecastBarProps) {
  const viewsK = scriptForecastViews(durationSec);
  const ret = scriptForecastRetentionPct(durationSec);
  const hookScore = scriptHookScore(hookDelayMs);

  const saveLabel = savePending ? "Đang lưu…" : saved ? "Đã lưu" : "Lưu kịch bản";
  const saveDisabled = !onSaveDraft || savePending;

  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 bg-[color:var(--gv-ink)] px-5 py-4 text-[color:var(--gv-canvas)]">
      <div>
        <div className="gv-mono gv-uc mb-1 text-[9.5px] tracking-[0.16em] opacity-50">DỰ KIẾN HIỆU SUẤT</div>
        <div className="text-[14px] font-normal leading-normal">
          <span className="text-[28px] font-medium leading-none tracking-[-0.035em] [font-family:var(--gv-font-display)]">
            ~{viewsK}K
          </span>
          <span className="opacity-60"> view · </span>
          giữ chân <span className="text-[rgb(0,159,250)]">{ret}%</span> · hook{" "}
          <span className="text-[color:var(--gv-accent)]">{hookScore.toFixed(1)}/10</span>
        </div>
      </div>
      <Btn
        variant="accent"
        type="button"
        className="shrink-0 gap-1"
        disabled={saveDisabled}
        onClick={() => void onSaveDraft?.()}
      >
        {savePending ? (
          <Loader2 className="h-3 w-3 animate-spin" strokeWidth={2} aria-hidden />
        ) : null}
        {saveLabel}
        {!savePending ? <ArrowRight className="h-3 w-3" strokeWidth={2} aria-hidden /> : null}
      </Btn>
    </div>
  );
}
