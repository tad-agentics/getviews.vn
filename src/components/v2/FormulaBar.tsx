import type { ChannelFormulaGate, ChannelFormulaStep } from "@/lib/api-types";

const SEGMENT_BG = [
  "bg-[color:var(--gv-accent)]",
  "bg-[color:var(--gv-ink-2)]",
  "bg-[color:var(--gv-ink-3)]",
  "bg-[color:var(--gv-accent-deep)]",
] as const;

export type FormulaBarProps = {
  steps: ChannelFormulaStep[] | null | undefined;
  formulaGate: ChannelFormulaGate;
  className?: string;
};

/**
 * 80px flex formula strip (Phase B · `/app/channel`). Thin corpus: centered
 * empty copy per plan.
 */
export function FormulaBar({ steps, formulaGate, className = "" }: FormulaBarProps) {
  const list = steps?.filter((s) => s && (s.step || s.detail)) ?? [];
  const hasSegments = list.length > 0;

  return (
    <div
      className={`flex h-20 overflow-hidden rounded-lg border border-[color:var(--gv-ink)] ${className}`.trim()}
      role="region"
      aria-label="Công thức phát hiện"
    >
      {hasSegments ? (
        list.map((s, i) => (
          <div
            key={`${s.step}-${i}`}
            className={`flex min-w-0 flex-col justify-between px-3 py-3 text-white ${SEGMENT_BG[i % SEGMENT_BG.length]}`}
            style={{ flex: `${Math.max(s.pct, 1)} 1 0%` }}
          >
            <div className="gv-mono text-[10px] font-medium uppercase tracking-[0.08em] opacity-90">
              {s.step} · {s.pct}%
            </div>
            <div className="text-[11px] leading-snug">{s.detail}</div>
          </div>
        ))
      ) : (
        <div className="flex flex-1 items-center justify-center bg-[color:var(--gv-canvas-2)] px-4">
          <p className="gv-mono m-0 text-center text-[11px] text-[color:var(--gv-ink-3)]">
            {formulaGate === "thin_corpus" ? "Chưa đủ video" : "Chưa có công thức"}
          </p>
        </div>
      )}
    </div>
  );
}
