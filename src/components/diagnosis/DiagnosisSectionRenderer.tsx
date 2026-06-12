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
  formatReferenceBridgeProse,
  partitionFindingsByChip,
  resolvePeerReferenceTiles,
  stripSectionProseForEmbeddedRefs,
  type DiagnosisReferenceTile,
  type ReferenceBridgeTopic,
} from "@/lib/diagnosisReferenceTiles";
import { fixChipMeta } from "@/lib/findingFixChip";
import {
  FindingEvidenceClip,
  type AnalyzedClipContext,
} from "@/components/diagnosis/FindingEvidenceClip";
import { splitVerdictProse } from "@/lib/humanizeStatsProse";
import { sortScriptBulletsByTimestamp } from "@/lib/nextVideoScript";
import { CreatorComparisonEmbed } from "@/components/diagnosis/CreatorComparisonEmbed";
import {
  ChannelContextLegacy,
  ChannelProofBlock,
} from "@/components/v2/answer/video/blocks/ChannelProofBlock";
import { ContextStrip } from "@/components/v2/answer/video/blocks/ContextStrip";
import { Timeline } from "@/components/v2/Timeline";
import { DiagnosisReferenceVideoCards } from "@/components/diagnosis/DiagnosisReferenceVideoCards";
import { NextVideoCard, NextVideoCardEmpty } from "@/routes/_app/channel/components/NextVideoCard";
import type { VideoAnalyzeMeta, VideoEnrichment, VideoSegment } from "@/lib/api-types";

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
  analyzedClip,
}: {
  rank: number;
  finding: DiagnosisFinding;
  /** When present, a strength/observation can show a "Xem đoạn này" clip from the analyzed video. */
  analyzedClip?: AnalyzedClipContext | null;
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
  analyzedClip,
  analyzedClipEvidence,
}: {
  sectionId: string;
  title: string;
  text: string;
  findings: DiagnosisFinding[];
  referenceTiles: DiagnosisReferenceTile[];
  gapKicker: "KHOẢNG TRỐNG" | "THIẾU SÓT";
  bridgeTopic: ReferenceBridgeTopic;
  /** Per-finding deep-link context into the analyzed clip (strengths cite own clip). */
  analyzedClip?: AnalyzedClipContext | null;
  /** Timeline / segments from the video under analysis — not peer corpus clips. */
  analyzedClipEvidence?: React.ReactNode;
}) {
  const { strengths, gaps, observations } = partitionFindingsByChip(findings);
  const gapLinkedTiles = resolvePeerReferenceTiles(
    sectionId,
    referenceTiles,
    findings,
    bridgeTopic,
  );
  const refBridge =
    gapLinkedTiles.length > 0
      ? formatReferenceBridgeProse(gaps, gapLinkedTiles.length, bridgeTopic)
      : "";
  const hasAnyFinding = strengths.length + gaps.length + observations.length > 0;
  let findingRank = 0;

  return (
    <div className="mb-6">
      <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">
        {title}
      </h3>
      {text ? <SectionVerdictBlock text={text} /> : null}
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
                  key={`s-${i}`}
                  rank={findingRank}
                  finding={f}
                  analyzedClip={analyzedClip}
                />
              );
            })}
          </div>
          {analyzedClipEvidence ? <div className="mt-3">{analyzedClipEvidence}</div> : null}
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
              return <SectionFindingCard key={`g-${i}`} rank={findingRank} finding={f} />;
            })}
          </div>
          {strengths.length === 0 && analyzedClipEvidence ? (
            <div className="mt-3">{analyzedClipEvidence}</div>
          ) : null}
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
                  key={`o-${i}`}
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
      {gapLinkedTiles.length > 0 ? (
        <DiagnosisReferenceVideoCards
          tiles={gapLinkedTiles}
          label="VÍ DỤ TRONG NGÁCH"
          embedded
          showLabel={!refBridge}
        />
      ) : null}
      {!hasAnyFinding && analyzedClipEvidence ? (
        <div className="mt-4">{analyzedClipEvidence}</div>
      ) : null}
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
  scriptStructure?: { segments: VideoSegment[]; durationSec: number };
  metadata?: { meta: VideoAnalyzeMeta; enrichment?: VideoEnrichment | null };
  /** Analyzed clip context for per-finding "Xem đoạn này" deep-links. */
  analyzedClip?: AnalyzedClipContext | null;
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
  const findings = (section.findings ?? []).filter(
    (f) => f.title_vi || f.body_vi || f.fix_vi,
  );
  const peerTiles = resolvePeerReferenceTiles(sid, referenceTiles, findings);
  const rawText = sectionText(section) || (fallbackProse ?? "").trim();
  const text =
    peerTiles.length > 0 ? stripSectionProseForEmbeddedRefs(rawText) : rawText;

  if (sid === "next_video") {
    const nvRaw =
      section.next_video && typeof section.next_video === "object"
        ? (section.next_video as Record<string, unknown>)
        : null;
    const concept = looseNextVideoConcept(nvRaw);
    const hasShotScript = text.includes("•") || /Hook\s*\(/i.test(text);
    // Belt-and-braces: the prompt demands chronological bullets, but a
    // shuffled script still renders in order when lines carry "(Ns-Ms)".
    const orderedText = text ? sortScriptBulletsByTimestamp(text) : text;
    return (
      <div className="mb-6">
        <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">{title}</h3>
        {text ? (
          // Body prose stays in the normal text face — mono is reserved for
          // kickers/numbers per the design system (live audit 2026-06-12:
          // the whole GỢI Ý script rendered monospace).
          <SectionProseBlocks
            text={orderedText}
            wrapperClassName="mt-3 space-y-1 text-[15px]"
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

  const isVideoStructureSection = sid === "script_structure";
  const isHookSection = sid === "hook_analysis";

  const partitioned = partitionFindingsByChip(findings);
  const useStrengthGapLayout =
    isVideoStructureSection ||
    isHookSection ||
    (sid === "diagnosis" &&
      (title.toLowerCase().includes("khoảng trống") ||
        partitioned.strengths.length > 0 ||
        partitioned.gaps.length > 0 ||
        partitioned.observations.length > 0));

  if (useStrengthGapLayout) {
    // Only the structure block owns the segment Timeline; hook/diagnosis cite
    // the analyzed clip per-finding via FindingEvidenceClip instead.
    const analyzedClipEvidence =
      isVideoStructureSection && videoEmbeds?.scriptStructure ? (
        <>
          <p className="gv-mono m-0 mb-2 text-[11px] gv-kicker tracking-[0.14em] text-[color:var(--gv-ink-3)]">
            BẰNG CHỨNG TRONG CLIP
          </p>
          <Timeline
            segments={videoEmbeds.scriptStructure.segments}
            durationSec={videoEmbeds.scriptStructure.durationSec}
          />
        </>
      ) : undefined;

    return (
      <StrengthGapSectionLayout
        sectionId={sid}
        title={title}
        text={text}
        findings={findings}
        referenceTiles={referenceTiles}
        gapKicker={isVideoStructureSection || isHookSection ? "THIẾU SÓT" : "KHOẢNG TRỐNG"}
        bridgeTopic={isVideoStructureSection ? "structure" : "general"}
        analyzedClip={videoEmbeds?.analyzedClip}
        analyzedClipEvidence={analyzedClipEvidence}
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
      {peerTiles.length > 0 ? (
        <DiagnosisReferenceVideoCards tiles={peerTiles} embedded showLabel={false} />
      ) : null}
      {sid === "script_structure" && videoEmbeds?.scriptStructure ? (
        <div className="mt-4">
          <Timeline
            segments={videoEmbeds.scriptStructure.segments}
            durationSec={videoEmbeds.scriptStructure.durationSec}
          />
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
