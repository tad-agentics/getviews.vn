import type { ScriptEditorShot } from "@/lib/scriptEditorMerge";

export type ScriptPacingRibbonProps = {
  shots: ScriptEditorShot[];
  activeShot: number;
  onSelectShot: (index: number) => void;
};

function LegendDot({ colorVar, label }: { colorVar: string; label: string }) {
  return (
    <span className="gv-mono inline-flex items-center gap-1.5 text-[10px] text-[color:var(--gv-ink-3)]">
      <span className="inline-block h-2 w-2 shrink-0" style={{ background: `var(${colorVar})` }} />
      {label}
    </span>
  );
}

export function ScriptPacingRibbon({ shots, activeShot, onSelectShot }: ScriptPacingRibbonProps) {
  if (!shots.length) return null;
  const total = shots[shots.length - 1]!.t1;

  return (
    <div className="rounded-[var(--gv-radius-sm)] border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] p-3.5">
      <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="gv-mono mb-1 text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
            NHỊP ĐỘ · PACING RIBBON
          </div>
          <p className="text-[13px] leading-snug text-[color:var(--gv-ink-2)]">
            Tempo kịch bản vs{" "}
            <span className="text-[color:var(--gv-chart-benchmark)]">video thắng trong ngách</span>
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <LegendDot colorVar="--gv-accent" label="Của bạn" />
          <LegendDot colorVar="--gv-chart-benchmark" label="Ngách" />
        </div>
      </div>

      <div className="flex h-[38px] gap-0.5">
        {shots.map((s, i) => {
          const span = s.t1 - s.t0;
          const w = (span / total) * 100;
          const yoursH = Math.min(100, (span / (s.winnerAvg * 2)) * 60 + 30);
          const nicheH = Math.min(100, (s.winnerAvg / (s.winnerAvg * 2)) * 60 + 30);
          const slow = span > s.winnerAvg * 1.2;
          return (
            <button
              key={`${s.t0}-${s.t1}-${i}`}
              type="button"
              title={`Shot ${String(i + 1).padStart(2, "0")}`}
              className={`relative cursor-pointer border-0 p-0 transition-colors ${
                activeShot === i ? "bg-[color:var(--gv-accent-soft)]" : "bg-transparent"
              }`}
              style={{ flex: `${w} 1 0%` }}
              onClick={() => onSelectShot(i)}
            >
              <div
                className="absolute bottom-0 left-[20%] w-1/4"
                style={{
                  height: `${yoursH}%`,
                  backgroundColor: slow ? "var(--gv-accent)" : "var(--gv-ink)",
                }}
              />
              <div
                className="absolute bottom-0 left-[55%] w-1/4 opacity-50"
                style={{ height: `${nicheH}%`, backgroundColor: "var(--gv-chart-benchmark)" }}
              />
              <div className="gv-mono pointer-events-none absolute left-[3px] top-0 text-[9px] text-[color:var(--gv-ink-4)]">
                {String(i + 1).padStart(2, "0")}
              </div>
            </button>
          );
        })}
      </div>

      <div className="relative mt-1 flex h-4">
        {shots.map((s, i) => (
          <div
            key={`tick-${i}`}
            className={`gv-mono pt-0.5 pl-[3px] text-[9px] text-[color:var(--gv-ink-4)] ${
              i > 0 ? "border-l border-[color:var(--gv-rule)]" : ""
            }`}
            style={{ flex: (s.t1 - s.t0) / total }}
          >
            {s.t0}s
          </div>
        ))}
      </div>
    </div>
  );
}
