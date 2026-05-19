/**
 * Standalone posting block (pre-v6 or when `distribution` section did not emit).
 * v6 + distribution: heatmap lives inside `DiagnosisSectionRenderer` via `PostingHeatmapEmbed`.
 */

import type { DiagnosisPostingContextPayload } from "@/lib/api-types";
import { SectionProseBlocks } from "@/components/SectionProseBlocks";
import { PostingHeatmapEmbed } from "@/components/diagnosis/PostingHeatmapEmbed";
import { buildDiagnosisPostingNarrative } from "@/lib/postingContextNarrative";
import { isTimingHeatmapGrid } from "@/lib/timingGridLabels";

export function DiagnosisPostingContextBlock({
  payload,
}: {
  payload: DiagnosisPostingContextPayload;
}) {
  if (!isTimingHeatmapGrid(payload.grid)) return null;

  const narrative = buildDiagnosisPostingNarrative(payload);

  return (
    <div className="mb-6" aria-label="Khung giờ đăng trong ngách">
      <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">
        Khung giờ đăng trong ngách
      </h3>
      {narrative.trim() ? (
        <SectionProseBlocks
          text={narrative}
          wrapperClassName="space-y-2 mt-2"
          paragraphClassName="text-[15px] leading-relaxed text-[color:var(--foreground)]"
        />
      ) : null}
      <PostingHeatmapEmbed payload={payload} />
    </div>
  );
}
