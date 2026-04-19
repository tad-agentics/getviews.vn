import type { VideoKpi } from "@/lib/api-types";

export type KpiGridProps = {
  kpis: VideoKpi[];
  className?: string;
  /**
   * `video` — B.1 deep-dive strip (larger value type, paper cells, wider breakpoints).
   * `channel` — `channel.jsx` / §B.3 hero right column: fixed 2×2, **22px** values,
   * canvas cells, label mb **4px**, delta mt **4px** (plan L677–683).
   */
  variant?: "video" | "channel";
};

/**
 * 2×2 responsive KPI strip (Phase B video + `/app/channel` hero).
 */
export function KpiGrid({ kpis, className = "", variant = "video" }: KpiGridProps) {
  const isChannel = variant === "channel";
  const gridCols = isChannel
    ? "grid-cols-2"
    : "grid-cols-2 min-[520px]:grid-cols-[repeat(auto-fit,minmax(140px,1fr))]";
  const cellBg = isChannel ? "bg-[color:var(--gv-canvas)]" : "bg-[color:var(--gv-paper)]";
  const labelMb = isChannel ? "mb-1" : "mb-1.5";
  const valueClass = isChannel
    ? "gv-tight text-[22px] leading-[1.1] text-[color:var(--gv-ink)]"
    : "gv-tight text-[30px] leading-none text-[color:var(--gv-ink)]";
  const defaultDelta = isChannel
    ? "gv-mono mt-1 text-[10px] text-[color:var(--gv-pos-deep)]"
    : "gv-mono mt-1.5 text-[10px] text-[color:var(--gv-pos-deep)]";

  return (
    <div
      className={`grid ${gridCols} gap-px overflow-hidden rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-rule)] ${className}`.trim()}
    >
      {kpis.map((m) => (
        <div key={m.label} className={`${cellBg} p-[18px]`}>
          <div className={`gv-uc ${labelMb} text-[9px] text-[color:var(--gv-ink-4)]`}>{m.label}</div>
          <div className={valueClass}>{m.value}</div>
          <div className={m.deltaClassName ?? defaultDelta}>{m.delta}</div>
        </div>
      ))}
    </div>
  );
}
