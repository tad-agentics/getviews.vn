import type { ConfidenceStripData } from "@/lib/api-types";

export function ConfidenceStrip({ data }: { data: ConfidenceStripData }) {
  return (
    <div className="flex flex-wrap gap-2 rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-3)]">
      <span>n={data.sample_size}</span>
      <span>·</span>
      <span>{data.window_days}d</span>
      <span>·</span>
      <span>{data.intent_confidence}</span>
      {data.niche_scope ? (
        <>
          <span>·</span>
          <span>{data.niche_scope}</span>
        </>
      ) : null}
    </div>
  );
}
