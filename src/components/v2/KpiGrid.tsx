import type { VideoKpi } from "@/lib/api-types";

export type KpiGridProps = {
  kpis: VideoKpi[];
  className?: string;
};

/**
 * 2×2 responsive KPI strip (Phase B video + later channel surfaces).
 */
export function KpiGrid({ kpis, className = "" }: KpiGridProps) {
  return (
    <div
      className={`grid grid-cols-2 gap-px overflow-hidden rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-rule)] min-[520px]:grid-cols-[repeat(auto-fit,minmax(140px,1fr))] ${className}`.trim()}
    >
      {kpis.map((m) => (
        <div key={m.label} className="bg-[color:var(--gv-paper)] p-[18px]">
          <div className="gv-uc mb-1.5 text-[9px] text-[color:var(--gv-ink-4)]">{m.label}</div>
          <div className="gv-tight text-[30px] leading-none text-[color:var(--gv-ink)]">{m.value}</div>
          <div
            className={
              m.deltaClassName ??
              "gv-mono mt-1.5 text-[10px] text-[color:var(--gv-pos-deep)]"
            }
          >
            {m.delta}
          </div>
        </div>
      ))}
    </div>
  );
}
