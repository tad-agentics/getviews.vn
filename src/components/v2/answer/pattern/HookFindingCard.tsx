import type { HookFindingData } from "@/lib/api-types";
import { momentumVi } from "./patternFormat";

function TonePill({ tone }: { tone: "up" | "down" | "neutral" }) {
  const cls =
    tone === "up"
      ? "text-[color:var(--gv-pos)]"
      : tone === "down"
        ? "text-[color:var(--gv-neg)]"
        : "text-[color:var(--gv-ink-3)]";
  return <span className={`font-mono text-[10px] ${cls}`}>●</span>;
}

export function HookFindingCard({ row }: { row: HookFindingData }) {
  const mom = momentumVi(row.lifecycle.momentum);
  return (
    <div className="grid grid-cols-[40px_minmax(0,1fr)_auto] gap-x-3 gap-y-2 border-b border-[color:var(--gv-rule-2)] pb-4 last:border-b-0 last:pb-0">
      <div className="gv-serif text-[28px] leading-none text-[color:var(--gv-ink-3)]">#{row.rank}</div>
      <div className="min-w-0 space-y-2">
        <p className="gv-serif text-[17px] leading-snug text-[color:var(--gv-ink)]">{row.pattern}</p>
        <p className="text-[13.5px] leading-relaxed text-[color:var(--gv-ink-2)]">{row.insight}</p>
        <p className="gv-mono mt-[10px] flex flex-wrap gap-x-[14px] gap-y-1 text-[11px] text-[color:var(--gv-ink-3)]">
          <span>Xuất hiện {row.lifecycle.first_seen}</span>
          <span>·</span>
          <span>Đỉnh {row.lifecycle.peak}</span>
          <span>·</span>
          <span style={{ color: mom.colorVar }}>{mom.label}</span>
        </p>
        <p className="mt-2 text-[12px] leading-[1.5] text-[color:var(--gv-ink-2)]">
          Thắng vì: {row.contrast_against.why_this_won} · So với: “{row.contrast_against.pattern}”
        </p>
        {row.prerequisites.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {row.prerequisites.map((p) => (
              <span
                key={p}
                className="gv-mono rounded bg-[color:var(--gv-canvas-2)] px-2 py-0.5 text-[10px] text-[color:var(--gv-ink-3)]"
              >
                {p}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="flex flex-col items-end gap-1 text-right">
        <div className="flex items-center gap-1">
          <span className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">RET</span>
          <TonePill tone="up" />
          <span className="gv-mono text-sm font-medium text-[color:var(--gv-ink)]">{row.retention.value}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">Δ</span>
          <TonePill tone={row.delta.numeric >= 0 ? "up" : "down"} />
          <span className="gv-mono text-sm font-medium text-[color:var(--gv-pos)]">{row.delta.value}</span>
        </div>
        <p className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">{row.uses} lượt</p>
      </div>
    </div>
  );
}
