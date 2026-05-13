import type { VideoFlopIssue } from "@/lib/api-types";

export type IssueCardProps = {
  issue: VideoFlopIssue;
  className?: string;
};

const sevLabel: Record<string, string> = {
  high: "Cao",
  mid: "TB",
  low: "Thấp",
};

/**
 * Flop diagnostic row — grid `80px 1fr` per Phase B plan.
 */
export function IssueCard({ issue, className = "" }: IssueCardProps) {
  const isHigh = issue.sev === "high";
  return (
    <div
      className={`grid grid-cols-1 items-start gap-4 border border-l-[4px] bg-[color:var(--gv-paper)] px-4 py-3.5 sm:grid-cols-[80px_1fr] ${
        isHigh
          ? "border-[color:var(--gv-accent)] border-l-[color:var(--gv-accent)]"
          : "border-[color:var(--gv-rule)] border-l-[color:var(--gv-ink-4)]"
      } ${className}`.trim()}
    >
      <div>
        <div className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
          {issue.t}s – {issue.end}s
        </div>
        <div
          className={`gv-mono mt-1 inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em] ${
            issue.sev === "high"
              ? "bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg)]"
              : issue.sev === "mid"
                ? "bg-[color:var(--gv-warn-soft)] text-[color:var(--gv-warn)]"
                : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)]"
          }`}
        >
          {sevLabel[issue.sev] ?? issue.sev}
        </div>
      </div>
      <div className="min-w-0">
        <h4 className="gv-serif m-0 text-[18px] font-medium leading-[1.25] text-[color:var(--gv-ink)]">
          {issue.title}
        </h4>
        <p className="mt-1.5 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">{issue.detail}</p>
        <div className="mt-2 inline-block bg-[color:var(--gv-canvas-2)] px-2.5 py-1.5 text-xs text-[color:var(--gv-ink-2)]">
          <span className="gv-uc mr-1.5 text-[9px] text-[color:var(--gv-accent)]">Fix</span>
          {issue.fix}
        </div>
      </div>
    </div>
  );
}
