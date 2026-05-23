/**
 * One `diagnosis_vi.sections[]` block — shared prose primitive + channel `VideoTileRow` / `NextVideoCard`.
 */
import { SectionProseBlocks } from "@/components/SectionProseBlocks";
import type {
  ChannelContext,
  ChannelNextVideoConcept,
  ChannelPerformerTile,
  CreatorComparison,
  DiagnosisEvidenceAnchorVi,
  DiagnosisFinding,
  DiagnosisPostingContextPayload,
  DiagnosisSectionVi,
  ReferenceVideoCard,
} from "@/lib/api-types";
import { CreatorComparisonEmbed } from "@/components/diagnosis/CreatorComparisonEmbed";
import { PostingHeatmapEmbed } from "@/components/diagnosis/PostingHeatmapEmbed";
import {
  ChannelContextLegacy,
  ChannelProofBlock,
} from "@/components/v2/answer/video/blocks/ChannelProofBlock";
import { NextVideoCard, NextVideoCardEmpty } from "@/routes/_app/channel/components/NextVideoCard";
import { VideoTileRow } from "@/routes/_app/channel/components/VideoTileRow";

function sectionTitle(s: DiagnosisSectionVi): string {
  const raw = (s.title_vi || s.title || "").trim();
  return raw || String(s.section_id ?? "");
}

function sectionText(s: DiagnosisSectionVi): string {
  return (s.text_vi || s.text || "").trim();
}

export function mapDiagnosisEmbeddedTiles(
  tiles: unknown[] | undefined,
  references: ReferenceVideoCard[],
): ChannelPerformerTile[] {
  if (!tiles?.length) return [];
  const byId: Record<string, ReferenceVideoCard> = {};
  for (const r of references) {
    if (r.aweme_id) byId[String(r.aweme_id)] = r;
  }
  const out: ChannelPerformerTile[] = [];
  for (const t of tiles) {
    if (!t || typeof t !== "object") continue;
    const row = t as Record<string, unknown>;
    const aid = String(row.aweme_id ?? row.video_id ?? "");
    const src = aid ? byId[aid] : undefined;
    // Only show tiles joined to the synthesis reference pool — never orphan Gemini captions.
    if (!src) continue;
    const url = String(src.tiktok_url ?? row.video_url ?? row.tiktok_url ?? "");
    const thumb = String(src.thumbnail_url ?? row.thumbnail_url ?? "");
    const views = Number(src.views ?? row.views ?? 0) || 0;
    const snip = String(src.desc ?? row.caption_snippet ?? row.desc ?? "").slice(0, 120);
    if (!url && !thumb && !snip) continue;
    out.push({
      video_url: url,
      thumbnail_url: thumb,
      views,
      caption_snippet: snip,
      posted_at: String(row.posted_at ?? ""),
      content_format: (src?.content_format ?? row.content_format) as string | undefined,
    });
  }
  return out;
}

/** Map v6 ``evidence_anchors`` (aweme_id only) into tiles when section has no embedded_tiles. */
export function embeddedTilesFromEvidenceAnchors(
  anchors: DiagnosisEvidenceAnchorVi[] | undefined,
  references: ReferenceVideoCard[],
  sectionId: string,
): ChannelPerformerTile[] {
  if (!anchors?.length) return [];
  const sid = sectionId.trim();
  const hints: unknown[] = [];
  for (const a of anchors) {
    if (!a || typeof a !== "object") continue;
    const typ = String(a.type ?? "")
      .toLowerCase()
      .replace(/-/g, "_");
    if (typ !== "aweme_id") continue;
    const anchorSid = String(a.section_id ?? "").trim();
    if (anchorSid && anchorSid !== sid) continue;
    const aid = String(a.quote ?? a.location ?? "").trim();
    if (aid && /^\d{15,22}$/.test(aid)) {
      hints.push({ aweme_id: aid });
    }
  }
  return mapDiagnosisEmbeddedTiles(hints, references);
}

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

/** Numbered finding card — summary + "Sửa:" at the close of each issue-type section. */
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
          <p className="mt-1.5 max-w-[640px] text-sm leading-relaxed text-[color:var(--gv-ink-2)]">
            <span className="gv-mono mr-1.5 font-semibold text-[color:var(--gv-accent)]">
              Sửa:
            </span>
            {fix_vi}
          </p>
        ) : null}
      </div>
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

interface DiagnosisSectionRendererProps {
  section: DiagnosisSectionVi;
  referenceVideos: ReferenceVideoCard[];
  /** v6 peer citations when ``embedded_tiles`` is empty (aweme_id anchors only). */
  evidenceAnchors?: DiagnosisEvidenceAnchorVi[];
  /** Corpus 7×8 grid — embedded under `distribution` prose when present. */
  postingContext?: DiagnosisPostingContextPayload | null;
  /** Hit/flop peer videos — embedded under `channel_pattern` prose. */
  creatorComparison?: CreatorComparison | null;
  /** Format-range channel stats — embedded under `channel_pattern` when available. */
  channelPatternEmbed?: ChannelPatternEmbedProps | null;
}

export function DiagnosisSectionRenderer({
  section,
  referenceVideos,
  evidenceAnchors,
  postingContext,
  creatorComparison,
  channelPatternEmbed,
}: DiagnosisSectionRendererProps) {
  const title = sectionTitle(section);
  const text = sectionText(section);
  const sid = String(section.section_id);
  const tilesFromSection = mapDiagnosisEmbeddedTiles(section.embedded_tiles, referenceVideos);
  const tiles =
    tilesFromSection.length > 0
      ? tilesFromSection
      : embeddedTilesFromEvidenceAnchors(evidenceAnchors, referenceVideos, sid);

  if (sid === "next_video") {
    const nvRaw =
      section.next_video && typeof section.next_video === "object"
        ? (section.next_video as Record<string, unknown>)
        : null;
    const concept = looseNextVideoConcept(nvRaw);
    return (
      <div className="mb-6">
        <h3 className="text-base font-bold text-[color:var(--foreground)] leading-snug">{title}</h3>
        {/* Prose + bullets always first — narrative-first principle */}
        {text ? (
          <SectionProseBlocks
            text={text}
            wrapperClassName="space-y-2 mt-2"
            paragraphClassName="text-[17px] leading-relaxed text-[color:var(--foreground)]"
          />
        ) : null}
        {/* Structured concept card is secondary — summary of the prose above */}
        {concept ? (
          <div className="mt-4">
            <NextVideoCard concept={concept} />
          </div>
        ) : !text ? (
          <NextVideoCardEmpty />
        ) : null}
      </div>
    );
  }

  const findings = (section.findings ?? []).filter(
    (f) => f.title_vi || f.body_vi || f.fix_vi,
  );

  return (
    <div className="mb-6">
      <h3 className="text-base font-bold text-[color:var(--foreground)] leading-snug">{title}</h3>
      <div className="relative mt-1">
        <SectionProseBlocks
          text={text}
          wrapperClassName="space-y-2 mt-2"
          paragraphClassName="text-[17px] leading-relaxed text-[color:var(--foreground)]"
        />
      </div>
      {sid === "distribution" && postingContext ? (
        <PostingHeatmapEmbed payload={postingContext} />
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
      {tiles.length > 0 ? (
        <div className="mt-4 border-t border-[color:var(--gv-rule)] pt-4">
          <VideoTileRow tiles={tiles} />
        </div>
      ) : null}
      {findings.length > 0 ? (
        <div className="mt-4 flex flex-col gap-3">
          {findings.map((f, i) => (
            <SectionFindingCard key={i} rank={i + 1} finding={f} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
