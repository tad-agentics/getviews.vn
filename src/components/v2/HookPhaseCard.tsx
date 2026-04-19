import type { VideoHookPhase } from "@/lib/api-types";

export type HookPhaseCardProps = {
  phase: VideoHookPhase;
  className?: string;
};

export function HookPhaseCard({ phase, className = "" }: HookPhaseCardProps) {
  return (
    <article
      className={`rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4 ${className}`.trim()}
    >
      <div className="gv-mono mb-1.5 text-[10px] text-[color:var(--gv-accent-deep)]">{phase.t_range}</div>
      <h4 className="gv-tight m-0 mb-1.5 text-base text-[color:var(--gv-ink)]">{phase.label}</h4>
      <p className="m-0 text-xs leading-snug text-[color:var(--gv-ink-3)]">{phase.body || "—"}</p>
    </article>
  );
}

export type HookPhaseGridProps = {
  phases: VideoHookPhase[];
  className?: string;
};

export function HookPhaseGrid({ phases, className = "" }: HookPhaseGridProps) {
  const items = phases.slice(0, 3);
  return (
    <div
      className={`grid grid-cols-1 gap-3 min-[700px]:grid-cols-3 ${className}`.trim()}
    >
      {items.map((p, i) => (
        <HookPhaseCard key={`${p.t_range}-${i}`} phase={p} />
      ))}
    </div>
  );
}
