/**
 * One `diagnosis_vi.sections[]` block — shared prose primitive + channel `VideoTileRow` / `NextVideoCard`.
 */
import { SectionProseBlocks } from "@/components/SectionProseBlocks";
import type {
  ChannelNextVideoConcept,
  ChannelPerformerTile,
  DiagnosisSectionVi,
  ReferenceVideoCard,
} from "@/lib/api-types";
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
    const url = String(src?.tiktok_url ?? row.video_url ?? row.tiktok_url ?? "");
    const thumb = String(src?.thumbnail_url ?? row.thumbnail_url ?? "");
    const views = Number(src?.views ?? row.views ?? 0) || 0;
    const snip = String(src?.desc ?? row.caption_snippet ?? row.desc ?? "").slice(0, 120);
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

interface DiagnosisSectionRendererProps {
  section: DiagnosisSectionVi;
  referenceVideos: ReferenceVideoCard[];
}

export function DiagnosisSectionRenderer({ section, referenceVideos }: DiagnosisSectionRendererProps) {
  const title = sectionTitle(section);
  const text = sectionText(section);
  const sid = String(section.section_id);
  const tiles = mapDiagnosisEmbeddedTiles(section.embedded_tiles, referenceVideos);

  if (sid === "next_video") {
    const nvRaw =
      section.next_video && typeof section.next_video === "object"
        ? (section.next_video as Record<string, unknown>)
        : null;
    const concept = looseNextVideoConcept(nvRaw);
    return (
      <div className="mb-6">
        <h3 className="text-base font-bold text-[color:var(--foreground)] leading-snug">{title}</h3>
        {concept ? (
          <NextVideoCard concept={concept} />
        ) : text ? (
          <SectionProseBlocks
            text={text}
            wrapperClassName="space-y-2 mt-2"
            paragraphClassName="text-[15px] leading-relaxed text-[color:var(--foreground)]"
          />
        ) : (
          <NextVideoCardEmpty />
        )}
      </div>
    );
  }

  return (
    <div className="mb-6">
      <h3 className="text-base font-bold text-[color:var(--foreground)] leading-snug">{title}</h3>
      <div className="relative mt-1">
        <SectionProseBlocks
          text={text}
          wrapperClassName="space-y-2 mt-2"
          paragraphClassName="text-[15px] leading-relaxed text-[color:var(--foreground)]"
        />
      </div>
      {tiles.length > 0 ? <VideoTileRow tiles={tiles} /> : null}
    </div>
  );
}
