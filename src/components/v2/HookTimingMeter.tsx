export type HookTimingMeterProps = {
  /** Milliseconds 400–3000 */
  delayMs: number;
};

/**
 * 14px bar + sweet band 0.8–1.4s (``--gv-chart-benchmark``) per B.4 spec.
 */
export function HookTimingMeter({ delayMs }: HookTimingMeterProps) {
  const pct = Math.min(100, (delayMs / 3000) * 100);
  const inSweet = delayMs >= 800 && delayMs <= 1400;
  const sweetLeft = (800 / 3000) * 100;
  const sweetRight = (1400 / 3000) * 100;

  return (
    <div className="relative mt-2 h-3.5">
      <div className="absolute inset-0 bg-[color:var(--gv-canvas-2)]" />
      <div
        className="absolute top-0 bottom-0 border-l border-r border-dashed border-[color:var(--gv-chart-benchmark)] bg-[color:color-mix(in_srgb,var(--gv-chart-benchmark)_22%,transparent)]"
        style={{ left: `${sweetLeft}%`, right: `${100 - sweetRight}%` }}
      />
      <div
        className="absolute top-[-4px] bottom-[-4px] w-[3px]"
        style={{
          left: `calc(${pct}% - 1.5px)`,
          backgroundColor: inSweet ? "var(--gv-chart-benchmark)" : "var(--gv-accent)",
        }}
      />
      <div className="gv-mono pointer-events-none absolute top-[18px] right-0 left-0 flex justify-between text-[9px] text-[color:var(--gv-ink-4)]">
        <span>0s</span>
        <span>1s</span>
        <span>2s</span>
        <span>3s</span>
      </div>
    </div>
  );
}
