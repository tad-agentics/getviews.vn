import type { VideoFlopIssue } from "@/lib/api-types";

export type IssueCardProps = {
  issue: VideoFlopIssue;
  /** Optional CTA (e.g. navigate to script / chat). */
  onApplyToScript?: () => void;
  className?: string;
};

const sevLabel: Record<string, string> = {
  high: "Cao",
  mid: "TB",
  low: "Thấp",
};

/**
 * Flop diagnostic row — grid `80px 1fr auto` per Phase B plan.
 */
export function IssueCard({ issue, onApplyToScript, className = "" }: IssueCardProps) {
  const isHigh = issue.sev === "high";
  return (
    <div
      className={`grid grid-cols-[80px_1fr_auto] items-start gap-4 border border-[color:var(--gv-rule)] border-l-[4px] bg-[color:var(--gv-paper)] px-4 py-3.5 ${
        isHigh ? "border-l-[color:var(--gv-accent)]" : "border-l-[color:var(--gv-ink-4)]"
      } ${className}`.trim()}
    >
      <div>
        <div className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
          {issue.t}s – {issue.end}s
        </div>
        <div
          className={`gv-mono mt-1 text-[9px] uppercase tracking-[0.14em] ${isHigh ? "text-[color:var(--gv-accent)]" : "text-[color:var(--gv-ink-4)]"}`}
        >
          {sevLabel[issue.sev] ?? issue.sev}
        </div>
      </div>
      <div className="min-w-0">
        <h4 className="gv-tight m-0 text-lg font-medium leading-snug tracking-tight text-[color:var(--gv-ink)]">
          {issue.title}
        </h4>
        <p className="mt-1.5 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">{issue.detail}</p>
        <div className="mt-2 inline-block bg-[color:var(--gv-canvas-2)] px-2.5 py-1.5 text-xs text-[color:var(--gv-ink-2)]">
          <span className="gv-mono mr-1.5 text-[9px] uppercase tracking-[0.14em] text-[color:var(--gv-accent)]">
            Fix
          </span>
          {issue.fix}
        </div>
      </div>
      {onApplyToScript ? (
        <button
          type="button"
          onClick={onApplyToScript}
          className="self-start rounded-md border border-[color:var(--gv-rule)] bg-transparent px-2 py-1 text-[11px] text-[color:var(--gv-ink-2)] transition-colors hover:bg-[color:var(--gv-canvas-2)]"
        >
          Áp vào kịch bản
        </button>
      ) : (
        <span className="w-px shrink-0" aria-hidden />
      )}
    </div>
  );
}
