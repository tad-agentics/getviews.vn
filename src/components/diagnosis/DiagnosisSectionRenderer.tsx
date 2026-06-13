/**
 * One `diagnosis_vi.sections[]` block — verdict-first, findings as hero (redesign 2026-05).
 */
import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";

import { SectionProseBlocks } from "@/components/SectionProseBlocks";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { formatDiagnosisSectionTitle } from "@/lib/formatters";
import { Timeline } from "@/components/v2/Timeline";
import { ThumbnailTile } from "@/routes/_app/components/ThumbnailTile";
import {
  buildStructureTimelineSummary,
  isInformativeStructureTimeline,
} from "@/lib/structureTimeline";
import type {
  ChannelContext,
  CreatorComparison,
  DiagnosisEvidenceAnchorVi,
  DiagnosisFinding,
  DiagnosisSectionVi,
  ReferenceVideoCard,
  VideoSegment,
  VideoStructureAxisBlock,
} from "@/lib/api-types";
import type { CommentRadarData } from "@/lib/types/corpus-sidecars";
import { buildCommentRadarProse } from "@/lib/commentRadarProse";
import {
  buildDiagnosisReferenceTiles,
  enrichReferenceTilesForGaps,
  fallbackNichePatternReferenceTiles,
  formatNichePatternBridgeProse,
  formatReferenceBridgeProse,
  formatSingleGapBridgeProse,
  GAP_PEER_MISSING_VI,
  partitionFindingsByChip,
  resolvePeerReferenceTiles,
  sectionProseHasNichePatternBridge,
  stripSectionProseForEmbeddedRefs,
  type DiagnosisReferenceTile,
  type ReferenceBridgeTopic,
} from "@/lib/diagnosisReferenceTiles";
import { contentFormatLabelVi } from "@/lib/contentFormatLabels";
import type { ThumbnailAnalysisData } from "@/lib/types/corpus-sidecars";
import { fixChipMeta } from "@/lib/findingFixChip";
import {
  FindingEvidenceClip,
  type AnalyzedClipContext,
} from "@/components/diagnosis/FindingEvidenceClip";
import { humanizeStatsProse, splitVerdictProse } from "@/lib/humanizeStatsProse";
import { CreatorComparisonEmbed } from "@/components/diagnosis/CreatorComparisonEmbed";
import {
  ChannelContextLegacy,
  ChannelProofBlock,
} from "@/components/v2/answer/video/blocks/ChannelProofBlock";
import { ContextStrip } from "@/components/v2/answer/video/blocks/ContextStrip";
import { StatsHistoryStrip } from "@/components/v2/answer/video/blocks/StatsHistoryStrip";
import {
  hasStatsHistorySnapshots,
  resolveMetadataStripProse,
  STATS_PROSE_IN_SECTION_RE,
} from "@/lib/statsHistoryProse";
import { hasContextStripContent } from "@/lib/videoAdjunctSections";
import { DiagnosisReferenceVideoCards } from "@/components/diagnosis/DiagnosisReferenceVideoCards";
import { CommentRadarTile } from "@/routes/_app/components/CommentRadarTile";
import type {
  VideoAnalyzeMeta,
  VideoEnrichment,
} from "@/lib/api-types";

function MetadataContextEmbed({
  meta,
  enrichment,
  sectionText,
  fallbackProse,
  commentRadar,
}: {
  meta: VideoAnalyzeMeta;
  enrichment?: VideoEnrichment | null;
  sectionText: string;
  fallbackProse?: string;
  commentRadar?: CommentRadarData | null;
}) {
  const hasContextGrid = hasContextStripContent(meta, enrichment);
  const { contextProse: resolvedContext, statsProse } = resolveMetadataStripProse({
    sectionText,
    fallbackProse: hasContextGrid ? fallbackProse : undefined,
    meta,
  });
  const sectionOnly = sectionText.trim();
  const contextProse = hasContextGrid
    ? resolvedContext
    : sectionOnly && !STATS_PROSE_IN_SECTION_RE.test(sectionOnly)
      ? sectionOnly
      : undefined;
  const showStats = hasStatsHistorySnapshots(meta.stats_history);
  const showContext = hasContextGrid || Boolean(contextProse);
  const commentProse = buildCommentRadarProse(commentRadar);

  return (
    <div className="mt-4 flex flex-col gap-3">
      {showContext ? (
        <ContextStrip
          meta={meta}
          enrichment={enrichment}
          introProse={contextProse}
          variant="embed"
        />
      ) : null}
      {showStats ? (
        <StatsHistoryStrip
          variant="embed"
          history={meta.stats_history}
          distributionShape={meta.distribution_shape}
          interpretationProse={statsProse}
        />
      ) : null}
      {commentProse ? (
        <p className="m-0 text-sm leading-relaxed text-[color:var(--gv-ink-2)]">{commentProse}</p>
      ) : null}
      {commentRadar ? <CommentRadarTile data={commentRadar} embedded /> : null}
    </div>
  );
}

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

/** Findings-first card with copy-paste fix chip. */
function SectionFindingCard({
  rank,
  finding,
  analyzedClip,
}: {
  rank: number;
  finding: DiagnosisFinding;
  /** When present, a strength/observation can show a "Xem đoạn này" clip from the analyzed video. */
  analyzedClip?: AnalyzedClipContext | null;
}) {
  const title_vi = finding.title_vi ? humanizeStatsProse(finding.title_vi) : "";
  const body_vi = finding.body_vi ? humanizeStatsProse(finding.body_vi) : "";
  const fix_vi = finding.fix_vi ? humanizeStatsProse(finding.fix_vi) : "";
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
          // Keep-advice ("Tiếp tục…", "Giữ…", "Nhân bản…", "Duy trì…") gets a
          // positive "Giữ" chip — "Sửa: Tiếp tục sử dụng…" was a live bug
          // (2026-06-12 audit).
          (() => {
            const chip = fixChipMeta(fix_vi);
            return (
              <span
                className={`mt-2 inline-flex max-w-full rounded-full border px-3 py-1.5 text-[13px] leading-snug text-[color:var(--gv-ink)] ${
                  chip.positive
                    ? "border-[color:var(--gv-pos)]/30 bg-[color:var(--gv-pos)]/8"
                    : "border-[color:var(--gv-accent)]/30 bg-[color:var(--gv-accent)]/8"
                }`}
              >
                <span
                  className={`gv-mono mr-1.5 shrink-0 font-semibold ${
                    chip.positive
                      ? "text-[color:var(--gv-pos)]"
                      : "text-[color:var(--gv-accent)]"
                  }`}
                >
                  {chip.label}
                </span>
                <span>{fix_vi}</span>
              </span>
            );
          })()
        ) : null}
        <FindingEvidenceClip evidenceRef={finding.evidence_ref} clip={analyzedClip} />
      </div>
    </div>
  );
}

function StrengthGapSectionLayout({
  sectionId,
  title,
  text,
  findings,
  referenceTiles,
  gapKicker,
  bridgeTopic,
  inlineGapRefs = false,
  analyzedClip,
  compact = false,
  structureTimeline,
  supportEmbed,
}: {
  sectionId: string;
  title: string;
  text: string;
  findings: DiagnosisFinding[];
  referenceTiles: DiagnosisReferenceTile[];
  gapKicker: "KHOẢNG TRỐNG" | "THIẾU SÓT";
  bridgeTopic: ReferenceBridgeTopic;
  /** Pair each gap finding with its reference tile directly under the card. */
  inlineGapRefs?: boolean;
  analyzedClip?: AnalyzedClipContext | null;
  /** Omit outer section heading/wrapper — used inside multi-axis structure block. */
  compact?: boolean;
  /** Eight-beat bar — flat script_structure layout only (multi-axis renders on rhythm). */
  structureTimeline?: { segments: VideoSegment[]; durationSec: number };
  /** Evidence tile under verdict prose (e.g. cover stop-power). */
  supportEmbed?: ReactNode;
}) {
  const { strengths, gaps, observations } = partitionFindingsByChip(findings);
  const gapLinkedTiles = resolvePeerReferenceTiles(
    sectionId,
    referenceTiles,
    findings,
    bridgeTopic,
    inlineGapRefs,
  );
  const refBridge =
    !inlineGapRefs && gapLinkedTiles.length > 0
      ? formatReferenceBridgeProse(gaps, gapLinkedTiles.length, bridgeTopic)
      : "";
  let findingRank = 0;

  const body = (
    <>
      {!compact && structureTimeline ? (
        <StructureTimelineEmbed timeline={structureTimeline} />
      ) : null}
      {text ? <SectionVerdictBlock text={text} /> : null}
      {supportEmbed}
      {strengths.length > 0 ? (
        <div className="mt-4">
          <p className="gv-mono m-0 mb-2 text-[11px] gv-kicker tracking-[0.14em] text-[color:var(--gv-ink-3)]">
            ĐIỂM MẠNH
          </p>
          <div className="flex flex-col gap-3">
            {strengths.map((f, i) => {
              findingRank += 1;
              return (
                <SectionFindingCard
                  key={`s-${f.title_vi ?? i}`}
                  rank={findingRank}
                  finding={f}
                  analyzedClip={analyzedClip}
                />
              );
            })}
          </div>
        </div>
      ) : null}
      {gaps.length > 0 ? (
        <div className="mt-4">
          <p className="gv-mono m-0 mb-2 text-[11px] gv-kicker tracking-[0.14em] text-[color:var(--gv-ink-3)]">
            {gapKicker}
          </p>
          <div className="flex flex-col gap-3">
            {gaps.map((f, i) => {
              findingRank += 1;
              const pairedTile = inlineGapRefs ? gapLinkedTiles[i] : undefined;
              return (
                <div key={`g-${f.title_vi ?? i}`} className="flex flex-col gap-3">
                  <SectionFindingCard rank={findingRank} finding={f} />
                  {pairedTile ? (
                    <>
                      <p className="m-0 text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]">
                        {formatSingleGapBridgeProse(f.title_vi ?? "", bridgeTopic)}
                      </p>
                      <DiagnosisReferenceVideoCards
                        tiles={[pairedTile]}
                        embedded
                        showLabel={false}
                      />
                    </>
                  ) : (
                    <p className="m-0 text-sm leading-relaxed text-[color:var(--gv-ink-3)]">
                      {GAP_PEER_MISSING_VI}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
      {observations.length > 0 ? (
        <div className="mt-4">
          <p className="gv-mono m-0 mb-2 text-[11px] gv-kicker tracking-[0.14em] text-[color:var(--gv-ink-3)]">
            QUAN SÁT
          </p>
          <div className="flex flex-col gap-3">
            {observations.map((f, i) => {
              findingRank += 1;
              return (
                <SectionFindingCard
                  key={`o-${f.title_vi ?? i}`}
                  rank={findingRank}
                  finding={f}
                  analyzedClip={analyzedClip}
                />
              );
            })}
          </div>
        </div>
      ) : null}
      {refBridge ? (
        <p className="m-0 mt-4 text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]">
          {refBridge}
        </p>
      ) : null}
      {!inlineGapRefs && gapLinkedTiles.length > 0 ? (
        <DiagnosisReferenceVideoCards
          tiles={gapLinkedTiles}
          label="VÍ DỤ TRONG NGÁCH"
          embedded
          showLabel={!refBridge}
        />
      ) : null}
    </>
  );

  if (!compact && title) {
    return (
      <Collapsible defaultOpen className="mb-6">
        <CollapsibleTrigger className="flex w-full min-h-[44px] items-center justify-between gap-3 rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)]/40 [&[data-state=open]>svg]:rotate-180">
          <span className="text-base font-bold leading-snug text-[color:var(--foreground)]">
            {title}
          </span>
          <ChevronDown
            className="h-4 w-4 shrink-0 text-[color:var(--gv-ink-3)] transition-transform duration-200"
            aria-hidden
          />
        </CollapsibleTrigger>
        <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down">
          <div className="pt-1">{body}</div>
        </CollapsibleContent>
      </Collapsible>
    );
  }

  return (
    <div className={compact ? "mt-0" : "mb-6"}>
      {!compact && title ? (
        <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">
          {title}
        </h3>
      ) : null}
      {body}
    </div>
  );
}

function StructureTimelineEmbed({
  timeline,
}: {
  timeline: { segments: VideoSegment[]; durationSec: number };
}) {
  if (!timeline.segments.length || !isInformativeStructureTimeline(timeline.segments)) {
    return null;
  }
  const summary = buildStructureTimelineSummary(timeline.segments, timeline.durationSec);
  return (
    <div className="mt-3">
      <Timeline segments={timeline.segments} durationSec={timeline.durationSec} />
      <p className="mt-2 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">{summary}</p>
    </div>
  );
}

function resolveStructureAxisPeerTiles(
  axisFindings: DiagnosisFinding[],
  axisSection: DiagnosisSectionVi,
  referenceVideos: ReferenceVideoCard[],
  evidenceAnchors: DiagnosisEvidenceAnchorVi[] | undefined,
  analyzedContentFormat: string | null | undefined,
): DiagnosisReferenceTile[] {
  const built = buildDiagnosisReferenceTiles(axisSection, referenceVideos, evidenceAnchors);
  const linked = resolvePeerReferenceTiles(
    "script_structure",
    built,
    axisFindings,
    "structure",
    true,
  );
  if (linked.length > 0) return linked;
  const { gaps } = partitionFindingsByChip(axisFindings);
  if (!gaps.length || !referenceVideos.length) return [];
  const fallback = fallbackNichePatternReferenceTiles(
    referenceVideos,
    gaps.length,
    analyzedContentFormat,
  );
  return enrichReferenceTilesForGaps(fallback, gaps, "structure", true);
}

function VideoStructureAxesLayout({
  title,
  axes,
  referenceVideos,
  evidenceAnchors,
  analyzedClip,
  structureTimeline,
  analyzedContentFormat,
}: {
  title: string;
  axes: VideoStructureAxisBlock[];
  referenceVideos: ReferenceVideoCard[];
  evidenceAnchors?: DiagnosisEvidenceAnchorVi[];
  analyzedClip?: AnalyzedClipContext | null;
  structureTimeline?: { segments: VideoSegment[]; durationSec: number };
  analyzedContentFormat?: string | null;
}) {
  const hasRhythmAxis = axes.some((axis) => axis.axis_id === "rhythm");
  return (
    <div className="mb-6">
      <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">{title}</h3>
      {structureTimeline && !hasRhythmAxis ? (
        <StructureTimelineEmbed timeline={structureTimeline} />
      ) : null}
      {axes.map((axis) => {
        const axisSection: DiagnosisSectionVi = {
          section_id: "script_structure",
          embedded_tiles: axis.embedded_tiles,
          findings: axis.findings,
        };
        const axisText = humanizeStatsProse((axis.text_vi || axis.text || "").trim());
        const axisFindings = (axis.findings ?? []).filter(
          (f) => f.title_vi || f.body_vi || f.fix_vi,
        );
        const axisTiles = resolveStructureAxisPeerTiles(
          axisFindings,
          axisSection,
          referenceVideos,
          evidenceAnchors,
          analyzedContentFormat,
        );
        return (
          <div key={axis.axis_id} className="mt-5 border-t border-[color:var(--gv-rule)] pt-4 first:mt-3 first:border-t-0 first:pt-0">
            <p className="gv-mono m-0 mb-2 text-[11px] gv-kicker tracking-[0.14em] text-[color:var(--gv-ink-3)]">
              {axis.title_vi}
            </p>
            {axis.axis_id === "rhythm" && structureTimeline ? (
              <StructureTimelineEmbed timeline={structureTimeline} />
            ) : null}
            <StrengthGapSectionLayout
              sectionId="script_structure"
              title=""
              text={axisText}
              findings={axisFindings}
              referenceTiles={axisTiles}
              gapKicker="THIẾU SÓT"
              bridgeTopic="structure"
              inlineGapRefs
              analyzedClip={analyzedClip}
              compact
            />
          </div>
        );
      })}
    </div>
  );
}

function SectionVerdictBlock({ text }: { text: string }) {
  const { verdict, support } = splitVerdictProse(text);
  if (!verdict && !support) return null;

  const proseClass = "text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]";

  if (verdict && support) {
    const supportParts = support.split(/\n\n+/).map((p) => p.trim()).filter(Boolean);
    const leadSupport = supportParts[0] ?? "";
    const tailSupport = supportParts.slice(1).join("\n\n").trim();
    return (
      <div className="mt-2 space-y-1.5">
        <p className={`m-0 ${proseClass}`}>
          <span className="font-bold">{verdict}</span>
          {leadSupport ? ` ${leadSupport}` : null}
        </p>
        {tailSupport ? (
          <SectionProseBlocks
            text={tailSupport}
            wrapperClassName="space-y-1.5"
            paragraphClassName={proseClass}
          />
        ) : null}
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-1.5">
      {verdict ? (
        <p className={`m-0 font-bold ${proseClass}`}>
          {verdict}
        </p>
      ) : null}
      {support ? (
        <SectionProseBlocks
          text={support}
          wrapperClassName="space-y-1.5"
          paragraphClassName={proseClass}
        />
      ) : !verdict && text.trim() ? (
        <SectionProseBlocks
          text={text}
          wrapperClassName="space-y-1.5"
          paragraphClassName={proseClass}
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
  metadata?: {
    meta: VideoAnalyzeMeta;
    enrichment?: VideoEnrichment | null;
    commentRadar?: CommentRadarData | null;
  };
  /** Analyzed clip context for per-finding "Xem đoạn này" deep-links. */
  analyzedClip?: AnalyzedClipContext | null;
  /** Eight-beat segment bar — shown under «Nhịp & cắt» in the structure block. */
  structureTimeline?: { segments: VideoSegment[]; durationSec: number };
  /** Cover stop-power — rendered under hook or diagnosis prose (not standalone). */
  thumbnailAnalysis?: {
    data: ThumbnailAnalysisData;
    frameUrl?: string | null;
  };
}

interface DiagnosisSectionRendererProps {
  section: DiagnosisSectionVi;
  referenceVideos: ReferenceVideoCard[];
  evidenceAnchors?: DiagnosisEvidenceAnchorVi[];
  creatorComparison?: CreatorComparison | null;
  channelPatternEmbed?: ChannelPatternEmbedProps | null;
  videoEmbeds?: VideoDiagnosisSectionEmbeds;
  fallbackProse?: string;
  /** Analyzed clip content_format — niche_pattern bridge + peer fallback. */
  analyzedContentFormat?: string | null;
  /** Render cover stop-power tile under this section's verdict prose. */
  embedThumbnailSupport?: boolean;
}

export function DiagnosisSectionRenderer({
  section,
  referenceVideos,
  evidenceAnchors,
  creatorComparison,
  channelPatternEmbed,
  videoEmbeds,
  fallbackProse,
  analyzedContentFormat = null,
  embedThumbnailSupport = false,
}: DiagnosisSectionRendererProps) {
  const title = sectionTitle(section);
  const sid = String(section.section_id);
  const referenceTiles = buildDiagnosisReferenceTiles(
    section,
    referenceVideos,
    evidenceAnchors,
  );
  const findings = (section.findings ?? []).filter(
    (f) => f.title_vi || f.body_vi || f.fix_vi,
  );
  const peerTiles = resolvePeerReferenceTiles(sid, referenceTiles, findings);
  const isNichePatternSection = sid === "niche_pattern";
  const displayTiles =
    isNichePatternSection && peerTiles.length === 0 && referenceVideos.length > 0
      ? fallbackNichePatternReferenceTiles(referenceVideos, 3, analyzedContentFormat)
      : peerTiles;
  const sectionOnlyText = sectionText(section);
  const rawText =
    sid === "metadata"
      ? sectionOnlyText
      : sectionOnlyText || (fallbackProse ?? "").trim();
  const formatLabel = analyzedContentFormat
    ? contentFormatLabelVi(analyzedContentFormat)
    : displayTiles[0]?.content_format
      ? contentFormatLabelVi(displayTiles[0].content_format)
      : null;
  const synthesisHasNicheBridge =
    isNichePatternSection && sectionProseHasNichePatternBridge(rawText);
  const nicheBridge =
    isNichePatternSection &&
    displayTiles.length > 0 &&
    !synthesisHasNicheBridge
      ? formatNichePatternBridgeProse(displayTiles.length, formatLabel)
      : "";
  const text =
    displayTiles.length > 0 && !synthesisHasNicheBridge
      ? stripSectionProseForEmbeddedRefs(rawText)
      : rawText;

  const isVideoStructureSection = sid === "script_structure";
  const isHookSection = sid === "hook_analysis";
  const isDiagnosisSection = sid === "diagnosis";
  const thumbnailSupportEmbed =
    embedThumbnailSupport && videoEmbeds?.thumbnailAnalysis ? (
      <ThumbnailTile
        data={videoEmbeds.thumbnailAnalysis.data}
        frameUrl={videoEmbeds.thumbnailAnalysis.frameUrl}
        embedded
      />
    ) : null;
  const structureAxes =
    isVideoStructureSection && Array.isArray(section.structure_axes)
      ? section.structure_axes.filter(
          (axis) =>
            (axis.text_vi || axis.text || "").trim() ||
            (axis.findings?.length ?? 0) > 0 ||
            (axis.embedded_tiles?.length ?? 0) > 0,
        )
      : [];

  if (isVideoStructureSection && structureAxes.length > 0) {
    return (
      <VideoStructureAxesLayout
        title={title}
        axes={structureAxes}
        referenceVideos={referenceVideos}
        evidenceAnchors={evidenceAnchors}
        analyzedClip={videoEmbeds?.analyzedClip}
        structureTimeline={videoEmbeds?.structureTimeline}
        analyzedContentFormat={analyzedContentFormat}
      />
    );
  }

  const partitioned = partitionFindingsByChip(findings);
  const useStrengthGapLayout =
    isVideoStructureSection ||
    isHookSection ||
    (sid === "diagnosis" &&
      (title.toLowerCase().includes("khoảng trống") ||
        partitioned.strengths.length > 0 ||
        partitioned.gaps.length > 0 ||
        partitioned.observations.length > 0 ||
        embedThumbnailSupport));

  if (useStrengthGapLayout) {
    return (
      <StrengthGapSectionLayout
        sectionId={sid}
        title={title}
        text={text}
        findings={findings}
        referenceTiles={referenceTiles}
        gapKicker={isVideoStructureSection || isHookSection ? "THIẾU SÓT" : "KHOẢNG TRỐNG"}
        bridgeTopic={
          isVideoStructureSection ? "structure" : isHookSection ? "hook" : "general"
        }
        inlineGapRefs={isVideoStructureSection || isHookSection}
        analyzedClip={videoEmbeds?.analyzedClip}
        structureTimeline={
          isVideoStructureSection ? videoEmbeds?.structureTimeline : undefined
        }
        supportEmbed={
          (isHookSection || isDiagnosisSection) ? thumbnailSupportEmbed : undefined
        }
      />
    );
  }

  return (
    <div className="mb-6">
      <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">{title}</h3>
      {findings.length > 0 ? (
        <div className="mt-3 flex flex-col gap-3">
          {findings.map((f, i) => (
            <SectionFindingCard
              key={i}
              rank={i + 1}
              finding={f}
              analyzedClip={videoEmbeds?.analyzedClip}
            />
          ))}
        </div>
      ) : null}
      {text && sid !== "metadata" ? <SectionVerdictBlock text={text} /> : null}
      {nicheBridge ? (
        <p className="m-0 mt-3 text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]">
          {nicheBridge}
        </p>
      ) : null}
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
      {displayTiles.length > 0 ? (
        <DiagnosisReferenceVideoCards
          tiles={displayTiles}
          label="VIDEO DẪN ĐẦU NGÁCH"
          embedded
          showLabel={!nicheBridge}
        />
      ) : null}
      {sid === "metadata" && videoEmbeds?.metadata ? (
        <MetadataContextEmbed
          meta={videoEmbeds.metadata.meta}
          enrichment={videoEmbeds.metadata.enrichment}
          sectionText={sectionOnlyText}
          fallbackProse={fallbackProse}
          commentRadar={videoEmbeds.metadata.commentRadar}
        />
      ) : null}
    </div>
  );
}
