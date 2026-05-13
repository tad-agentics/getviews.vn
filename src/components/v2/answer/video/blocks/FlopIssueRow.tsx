import { EvidenceVideoEmbed } from "@/components/v2/answer/video/EvidenceVideoEmbed";
import type {
  LoidChinhNarrativeItem,
  ReferenceVideoCard,
  VideoFlopIssue,
} from "@/lib/api-types";

const SEV_BORDER: Record<VideoFlopIssue["sev"], string> = {
  high: "border-[color:var(--gv-accent)]",
  mid: "border-[color:var(--gv-warn)]",
  low: "border-[color:var(--gv-rule)]",
};

const SEV_NUM_CLS: Record<VideoFlopIssue["sev"], string> = {
  high: "bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg)]",
  mid: "bg-[color:var(--gv-warn-soft)] text-[color:var(--gv-warn)]",
  low: "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]",
};

/**
 * Phase 4.4.2 + v5 audit — numbered layout (1/2/3) aligned with spec.
 * Severity drives border + number badge color; timestamps are removed from
 * the primary view (available in the collapsed detail only if needed).
 * "Sửa:" replaces the "Fix" chip to match the Vietnamese voice spec.
 */
export function FlopIssueNarrativeRow({
  rank,
  issue,
  narrativeItem,
  referenceVideos,
}: {
  rank: number;
  issue: VideoFlopIssue;
  narrativeItem?: LoidChinhNarrativeItem;
  referenceVideos: ReferenceVideoCard[];
}) {
  const borderCls = SEV_BORDER[issue.sev] ?? "border-[color:var(--gv-rule)]";
  const numCls = SEV_NUM_CLS[issue.sev] ?? SEV_NUM_CLS.low;

  return (
    <div
      className={`flex items-start gap-4 rounded-[12px] border bg-[color:var(--gv-paper)] px-4 py-3.5 ${borderCls}`}
    >
      {/* Rank number */}
      <div
        className={`gv-mono mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[13px] font-bold ${numCls}`}
        aria-label={`Lỗi ${rank}`}
      >
        {rank}
      </div>

      <div className="min-w-0 flex-1">
        <h4 className="gv-serif m-0 text-[17px] font-medium leading-[1.3] text-[color:var(--gv-ink)]">
          {issue.title}
        </h4>

        {narrativeItem?.narrative ? (
          <p className="mb-2 mt-1.5 max-w-[640px] text-[13px] leading-relaxed text-foreground">
            {narrativeItem.narrative}
          </p>
        ) : null}

        {narrativeItem?.evidence_aweme_id ? (
          <EvidenceVideoEmbed
            aweme_id={narrativeItem.evidence_aweme_id}
            reference_videos={referenceVideos}
          />
        ) : null}

        {/* detail paragraph */}
        {issue.detail ? (
          <p className="mb-2 mt-1 max-w-[640px] text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
            {issue.detail}
          </p>
        ) : null}

        {/* Fix action — "Sửa:" matches Vietnamese voice spec */}
        {issue.fix ? (
          <p className="mt-1.5 max-w-[640px] text-[13px] leading-relaxed text-[color:var(--gv-ink-2)]">
            <span className="gv-mono mr-1.5 font-semibold text-[color:var(--gv-accent)]">
              Sửa:
            </span>
            {issue.fix}
          </p>
        ) : null}
      </div>
    </div>
  );
}
