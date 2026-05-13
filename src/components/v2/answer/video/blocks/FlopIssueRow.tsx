import { EvidenceVideoEmbed } from "@/components/v2/answer/video/EvidenceVideoEmbed";
import type {
  LoidChinhNarrativeItem,
  ReferenceVideoCard,
  VideoFlopIssue,
} from "@/lib/api-types";

const FLOP_SEV_LABEL: Record<VideoFlopIssue["sev"], string> = {
  high: "Cao",
  mid: "TB",
  low: "Thấp",
};

/**
 * Phase 4.4.2 — border color extended to 3-tier: red (high) / orange (mid) / yellow (low).
 * Previously: red for high, default rule for mid+low.
 */
export function FlopIssueNarrativeRow({
  issue,
  narrativeItem,
  referenceVideos,
}: {
  issue: VideoFlopIssue;
  narrativeItem?: LoidChinhNarrativeItem;
  referenceVideos: ReferenceVideoCard[];
}) {
  const leftBorderCls =
    issue.sev === "high"
      ? "border-l-[color:var(--gv-accent)]"
      : issue.sev === "mid"
        ? "border-l-[color:var(--gv-warn)]"
        : "border-l-[color:var(--gv-ink-4)]";

  const outerBorderCls =
    issue.sev === "high"
      ? "border-[color:var(--gv-accent)]"
      : issue.sev === "mid"
        ? "border-[color:var(--gv-warn)]"
        : "border-[color:var(--gv-rule)]";

  return (
    <div
      className={`grid grid-cols-1 items-start gap-4 border border-l-[4px] bg-[color:var(--gv-paper)] px-4 py-3.5 sm:grid-cols-[80px_1fr] ${outerBorderCls} ${leftBorderCls}`.trim()}
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
          {FLOP_SEV_LABEL[issue.sev] ?? issue.sev}
        </div>
      </div>
      <div className="min-w-0">
        <h4 className="gv-serif m-0 text-[18px] font-medium leading-[1.25] text-[color:var(--gv-ink)]">
          {issue.title}
        </h4>
        {narrativeItem?.narrative ? (
          <p className="mb-2 mt-1 max-w-[640px] text-[13px] leading-relaxed text-foreground">
            {narrativeItem.narrative}
          </p>
        ) : null}
        {narrativeItem?.evidence_aweme_id ? (
          <EvidenceVideoEmbed
            aweme_id={narrativeItem.evidence_aweme_id}
            reference_videos={referenceVideos}
          />
        ) : null}
        <div className="mt-2 max-w-[640px]">
          <div className="space-y-2">
            <p className="m-0 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
              {issue.detail}
            </p>
            <div className="inline-block bg-[color:var(--gv-canvas-2)] px-2.5 py-1.5 text-xs text-[color:var(--gv-ink-2)]">
              <span className="gv-uc mr-1.5 text-[9px] text-[color:var(--gv-accent)]">Fix</span>
              {issue.fix}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
