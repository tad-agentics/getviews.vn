/**
 * One `diagnosis_vi.sections[]` block — verdict-first, findings as hero (redesign 2026-05).
 */
import { SectionProseBlocks } from "@/components/SectionProseBlocks";
import { formatDiagnosisSectionTitle } from "@/lib/formatters";
import type {
  ChannelContext,
  ChannelNextVideoConcept,
  CreatorComparison,
  DiagnosisEvidenceAnchorVi,
  DiagnosisFinding,
  DiagnosisSectionVi,
  ReferenceVideoCard,
} from "@/lib/api-types";
import {
  buildDiagnosisReferenceTiles,
  stripSectionProseForEmbeddedRefs,
} from "@/lib/diagnosisReferenceTiles";
import { splitVerdictProse } from "@/lib/humanizeStatsProse";
import { CreatorComparisonEmbed } from "@/components/diagnosis/CreatorComparisonEmbed";
import {
  ChannelContextLegacy,
  ChannelProofBlock,
} from "@/components/v2/answer/video/blocks/ChannelProofBlock";
import { ContextStrip } from "@/components/v2/answer/video/blocks/ContextStrip";
import { Timeline } from "@/components/v2/Timeline";
import { HookPhaseGrid } from "@/components/v2/HookPhaseCard";
import { HookTimelineStrip } from "@/routes/_app/components/HookTimelineStrip";
import { DiagnosisReferenceVideoCards } from "@/components/diagnosis/DiagnosisReferenceVideoCards";
import { NextVideoCard, NextVideoCardEmpty } from "@/routes/_app/channel/components/NextVideoCard";
import type {
  HookTimelineEvent,
  VideoAnalyzeMeta,
  VideoEnrichment,
  VideoHookPhase,
  VideoSegment,
} from "@/lib/api-types";

function sectionTitle(s: DiagnosisSectionVi): string {
  const raw = (s.title_vi || s.title || "").trim();
  const base = raw || String(s.section_id ?? "");
  return formatDiagnosisSectionTitle(base);
}

function sectionText(s: DiagnosisSectionVi): string {
  return (s.text_vi || s.text || "").trim();
}

export {
  buildDiagnosisReferenceTiles,
  embeddedTilesFromEvidenceAnchors,
  mapDiagnosisEmbeddedTiles,
} from "@/lib/diagnosisReferenceTiles";

function looseNextVideoConcept(
  raw: Record<string, unknown> | null | undefined,
): ChannelNextVideoConcept | null {
  if (!raw) return null;
  const hook = String(raw.hook_vi ?? "").trim();
  const premise = String(raw.premise_vi ?? "").trim();
  const reason = String(raw.reason_vi ?? "").trim();
  const narrative = [hook, premise, reason].filter(Boolean).join("\n\n").trim();
  const rationale = String(
    raw.rationale_struct ?? raw.expected_views_range ?? "",
  ).trim();
  const body = narrative || rationale;
  if (!body) return null;
  const fmtLabel = String(raw.format ?? raw.format_label ?? "Gợi ý");
  return {
    format: fmtLabel,
    format_label: fmtLabel,
    duration_sec: Number(raw.duration_sec ?? 30) || 30,
    rationale_struct: rationale || narrative.slice(0, 240) || body.slice(0, 240),
    sample_peer_handle: String(raw.sample_peer_handle ?? ""),
    sample_video_url: String(raw.sample_video_url ?? raw.tiktok_url ?? ""),
    sample_thumbnail_url: (raw.sample_thumbnail_url as string | null | undefined) ?? null,
    peer_avg_views: Number(raw.peer_avg_views ?? 0) || 0,
    channel_share_pct: Number(raw.channel_share_pct ?? 0) || 0,
    narrative: narrative || undefined,
  };
}

/** Findings-first card with copy-paste fix chip. */
function SectionFindingCard({
  rank,
  finding,
}: {
  rank: number;
  finding: DiagnosisFinding;
}) {
  const { title_vi, body_vi, fix_vi } = finding;
  if (!title_vi && !body_vi && !fix_vi) return null;
  return (
    <div className="flex items-start gap-4 rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3.5">
      <div className="gv-mono mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[color:var(--gv-canvas-2)] text-sm font-bold text-[color:var(--gv-ink)]">
        {rank}
      </div>
      <div className="min-w-0 flex-1">
        {title_vi ? (
          <h4 className="gv-serif m-0 text-[17px] font-medium leading-[1.3] text-[color:var(--gv-ink)]">
            {title_vi}
          </h4>
        ) : null}
        {body_vi ? (
          <p className="mt-1.5 max-w-[640px] text-sm leading-relaxed text-foreground">
            {body_vi}
          </p>
        ) : null}
        {fix_vi ? (
          <span className="mt-2 inline-flex max-w-full rounded-full border border-[color:var(--gv-accent)]/30 bg-[color:var(--gv-accent)]/8 px-3 py-1.5 text-[13px] leading-snug text-[color:var(--gv-ink)]">
            <span className="gv-mono mr-1.5 shrink-0 font-semibold text-[color:var(--gv-accent)]">
              Sửa
            </span>
            <span>{fix_vi}</span>
          </span>
        ) : null}
      </div>
    </div>
  );
}

function SectionVerdictBlock({ text }: { text: string }) {
  const { verdict, support } = splitVerdictProse(text);
  if (!verdict && !support) return null;
  return (
    <div className="mt-2 space-y-1.5">
      {verdict ? (
        <p className="m-0 text-[17px] font-bold leading-snug text-[color:var(--foreground)]">
          {verdict}
        </p>
      ) : null}
      {support ? (
        <SectionProseBlocks
          text={support}
          wrapperClassName="space-y-1.5"
          paragraphClassName="text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]"
        />
      ) : !verdict && text.trim() ? (
        <SectionProseBlocks
          text={text}
          wrapperClassName="space-y-1.5"
          paragraphClassName="text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]"
        />
      ) : null}
    </div>
  );
}

export interface ChannelPatternEmbedProps {
  channelContext: ChannelContext;
  analyzedFormat?: string | null;
  creatorHandle?: string | null;
  metaTitle?: string | null;
  metaViews: number;
  isV5: boolean;
}

export interface VideoDiagnosisSectionEmbeds {
  scriptStructure?: { segments: VideoSegment[]; durationSec: number };
  hookAnalysis?: {
    phases?: VideoHookPhase[];
    timeline?: HookTimelineEvent[];
    chartCaption?: string;
  };
  metadata?: { meta: VideoAnalyzeMeta; enrichment?: VideoEnrichment | null };
}

interface DiagnosisSectionRendererProps {
  section: DiagnosisSectionVi;
  referenceVideos: ReferenceVideoCard[];
  evidenceAnchors?: DiagnosisEvidenceAnchorVi[];
  creatorComparison?: CreatorComparison | null;
  channelPatternEmbed?: ChannelPatternEmbedProps | null;
  videoEmbeds?: VideoDiagnosisSectionEmbeds;
  fallbackProse?: string;
}

export function DiagnosisSectionRenderer({
  section,
  referenceVideos,
  evidenceAnchors,
  creatorComparison,
  channelPatternEmbed,
  videoEmbeds,
  fallbackProse,
}: DiagnosisSectionRendererProps) {
  const title = sectionTitle(section);
  const sid = String(section.section_id);
  const referenceTiles = buildDiagnosisReferenceTiles(
    section,
    referenceVideos,
    evidenceAnchors,
  );
  const rawText = sectionText(section) || (fallbackProse ?? "").trim();
  const text =
    referenceTiles.length > 0 ? stripSectionProseForEmbeddedRefs(rawText) : rawText;

  if (sid === "next_video") {
    const nvRaw =
      section.next_video && typeof section.next_video === "object"
        ? (section.next_video as Record<string, unknown>)
        : null;
    const concept = looseNextVideoConcept(nvRaw);
    const hasShotScript = text.includes("•") || /Hook\s*\(/i.test(text);
    return (
      <div className="mb-6">
        <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">{title}</h3>
        {text ? (
          <SectionProseBlocks
            text={text}
            wrapperClassName="mt-3 space-y-1 font-mono text-[15px]"
            paragraphClassName="whitespace-pre-wrap leading-relaxed text-[color:var(--foreground)]"
          />
        ) : concept ? (
          <div className="mt-4">
            <NextVideoCard concept={concept} />
          </div>
        ) : (
          <NextVideoCardEmpty />
        )}
        {text && concept && !hasShotScript ? (
          <div className="mt-4 opacity-90">
            <NextVideoCard concept={concept} />
          </div>
        ) : null}
      </div>
    );
  }

  const findings = (section.findings ?? []).filter(
    (f) => f.title_vi || f.body_vi || f.fix_vi,
  );

  return (
    <div className="mb-6">
      <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">{title}</h3>
      {findings.length > 0 ? (
        <div className="mt-3 flex flex-col gap-3">
          {findings.map((f, i) => (
            <SectionFindingCard key={i} rank={i + 1} finding={f} />
          ))}
        </div>
      ) : null}
      {text ? <SectionVerdictBlock text={text} /> : null}
      {sid === "channel_pattern" && creatorComparison ? (
        <CreatorComparisonEmbed data={creatorComparison} />
      ) : null}
      {sid === "channel_pattern" && channelPatternEmbed?.channelContext.available ? (
        channelPatternEmbed.isV5 ? (
          <ChannelProofBlock
            channelContext={channelPatternEmbed.channelContext}
            analyzedFormat={channelPatternEmbed.analyzedFormat}
            creatorHandle={channelPatternEmbed.creatorHandle}
            variant="embed"
          />
        ) : (
          <ChannelContextLegacy
            channelContext={channelPatternEmbed.channelContext}
            metaTitle={channelPatternEmbed.metaTitle}
            metaViews={channelPatternEmbed.metaViews}
            variant="embed"
          />
        )
      ) : null}
      {referenceTiles.length > 0 ? (
        <DiagnosisReferenceVideoCards
          tiles={referenceTiles}
          label={sid === "niche_pattern" ? "Top ngách — sao chép cách này" : "Video tham chiếu"}
        />
      ) : null}
      {sid === "script_structure" && videoEmbeds?.scriptStructure ? (
        <div className="mt-4">
          <Timeline
            segments={videoEmbeds.scriptStructure.segments}
            durationSec={videoEmbeds.scriptStructure.durationSec}
          />
        </div>
      ) : null}
      {sid === "hook_analysis" && videoEmbeds?.hookAnalysis ? (
        <div className="mt-4">
          {videoEmbeds.hookAnalysis.chartCaption ? (
            <p className="mb-3 max-w-[680px] text-[12px] leading-relaxed text-[color:var(--gv-ink-2)]">
              {videoEmbeds.hookAnalysis.chartCaption}
            </p>
          ) : null}
          {videoEmbeds.hookAnalysis.phases?.length ? (
            <HookPhaseGrid phases={videoEmbeds.hookAnalysis.phases} />
          ) : null}
          {videoEmbeds.hookAnalysis.timeline?.length ? (
            <HookTimelineStrip events={videoEmbeds.hookAnalysis.timeline} />
          ) : null}
        </div>
      ) : null}
      {sid === "metadata" && videoEmbeds?.metadata ? (
        <div className="mt-4">
          <ContextStrip
            meta={videoEmbeds.metadata.meta}
            enrichment={videoEmbeds.metadata.enrichment}
            variant="embed"
          />
        </div>
      ) : null}
    </div>
  );
}
