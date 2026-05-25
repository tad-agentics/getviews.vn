/**
 * Phase C.5.2 — Generic (humility) report body. Locked render order (plan §C.5):
 *
 *   ConfidenceStrip (FALLBACK pinned) → OffTaxonomyBanner → NarrativeAnswer
 *                                    → EvidenceVideos × 3 → (no ActionCards)
 *
 * FALLBACK chip: Generic is the humility landing; `intent_confidence` is
 * pinned to `"low"` by the backend. The FALLBACK chip here renders
 * unconditionally via a dedicated pill so low-intent queries always
 * announce themselves as "we couldn't classify this confidently".
 *
 * No ActionCards section — the OffTaxonomyBanner IS the routing surface.
 */

import type { GenericReportPayload } from "@/lib/api-types";

import { GenericEvidenceGrid } from "./GenericEvidenceGrid";
import { NarrativeAnswer } from "./NarrativeAnswer";
import { OffTaxonomyBanner } from "./OffTaxonomyBanner";
import { ReportNarrativeHeadline } from "../ReportNarrativeHeadline";

export function GenericBody({ report }: { report: GenericReportPayload }) {
  return (
    <div className="space-y-6 text-sm text-[color:var(--gv-ink-2)]">
      <div className="flex flex-col gap-2">
        <span className="gv-mono inline-flex w-fit items-center gap-1 rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-[2px] text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-4)]">
          Fallback · intent thấp
        </span>
      </div>

      <OffTaxonomyBanner data={report.off_taxonomy} />

      <ReportNarrativeHeadline source={{ kind: "generic", report }} kicker="Kết luận" />

      <NarrativeAnswer data={report.narrative} />

      {report.evidence_videos.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "120ms" }}>
          <p className="gv-mono mb-2 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">
            Video mẫu
          </p>
          <GenericEvidenceGrid items={report.evidence_videos} />
        </section>
      ) : null}
    </div>
  );
}
