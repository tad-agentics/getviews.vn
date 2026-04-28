/**
 * Phase C.3.2 — Ideas report body. Locked render order (plan §C.3 design spec):
 *
 *   ConfidenceStrip → HumilityBanner (thin) → LeadParagraph → IdeaBlocks
 *                    → StyleCards → StopDoing → ActionCards
 *
 * Empty state (sample_size < 60): shrink to 3 IdeaBlocks + suppress StopDoing
 * (upstream `report_ideas.build_thin_corpus_ideas_report` already truncates the
 *  payload; this body renders whatever it receives without further filtering).
 *
 * Variant mode (`payload.variant === "hook_variants"`): suppress StopDoing via
 * the empty array upstream; LeadParagraph copy is the variant brief. Same body
 * primitives render — no component-level branching.
 */

import { useState } from "react";

import type { IdeasReportPayload } from "@/lib/api-types";

import { ConfidenceStrip } from "../pattern/ConfidenceStrip";
import { HumilityBanner } from "../pattern/HumilityBanner";
import { IdeaBlock } from "./IdeaBlock";
import { IdeasActionCards } from "./IdeasActionCards";
import { LeadParagraph } from "./LeadParagraph";
import { NicheInsightCard } from "./NicheInsightCard";
import { StopDoingList } from "./StopDoingList";
import { StyleCardGrid } from "./StyleCardGrid";
import { ideasLeadAndSectionTitles } from "../sessionIntentLabels";

export function IdeasBody({
  report,
  sessionIntentType,
}: {
  report: IdeasReportPayload;
  sessionIntentType?: string;
}) {
  const thin = report.confidence.sample_size < 60;
  const [humilityOpen, setHumilityOpen] = useState(true);

  const { leadTitle, sectionKicker, ideasHeading } = ideasLeadAndSectionTitles({
    variant: report.variant,
    sessionIntentType,
  });

  const ideasActionsTitle =
    report.variant === "hook_variants"
      ? "Biến ý tưởng thành video"
      : sessionIntentType === "brief_generation"
        ? "Từ brief ra video"
        : "Biến ý tưởng thành video";

  return (
    <div className="space-y-8 text-sm text-[color:var(--gv-ink-2)]">
      <ConfidenceStrip
        data={report.confidence}
        thinSample={thin}
        humilityVisible={humilityOpen}
        onHumilityToggle={() => setHumilityOpen((v) => !v)}
      />

      {thin && humilityOpen ? <HumilityBanner /> : null}

      <LeadParagraph title={leadTitle} body={report.lead} />

      {report.ideas.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "0ms" }}>
          <p className="gv-kicker gv-kicker--dot mb-2 text-[color:var(--gv-accent-deep)]">
            {sectionKicker}
          </p>
          <h3 className="gv-tight mb-4 text-[24px] text-[color:var(--gv-ink)] min-[700px]:text-[28px]">
            {ideasHeading}
          </h3>
          <div className="flex flex-col gap-4">
            {report.ideas.map((block) => (
              <IdeaBlock key={block.id} block={block} />
            ))}
          </div>
        </section>
      ) : null}

      <NicheInsightCard insight={report.niche_insight} />

      {report.style_cards.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "120ms" }}>
          <p className="gv-mono mb-1 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
            Phong cách
          </p>
          <h3 className="gv-serif mb-3 text-[18px] text-[color:var(--gv-ink)]">
            5 hướng quay song song
          </h3>
          <StyleCardGrid cards={report.style_cards} />
        </section>
      ) : null}

      {report.stop_doing.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "180ms" }}>
          <p className="gv-mono mb-1 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
            Bỏ ngay
          </p>
          <h3 className="gv-serif mb-3 text-[18px] text-[color:var(--gv-ink)]">
            5 thói quen rớt view
          </h3>
          <StopDoingList rows={report.stop_doing} />
        </section>
      ) : null}

      {report.actions.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "240ms" }}>
          <p className="gv-mono mb-1 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
            Bước tiếp theo
          </p>
          <h3 className="gv-serif mb-3 text-[18px] text-[color:var(--gv-ink)]">
            {ideasActionsTitle}
          </h3>
          <IdeasActionCards actions={report.actions} />
        </section>
      ) : null}
    </div>
  );
}
