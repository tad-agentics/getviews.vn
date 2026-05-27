import type {
  ChannelPerformerTile,
  DiagnosisEvidenceAnchorVi,
  DiagnosisSectionVi,
  ReferenceVideoCard,
} from "@/lib/api-types";

/** One peer reference video shown under a diagnosis section. */
export interface DiagnosisReferenceTile extends ChannelPerformerTile {
  aweme_id?: string;
  /** Per-video comparison copy from synthesis (preferred). */
  narrative_vi?: string;
  author_handle?: string | null;
  hook_type?: string | null;
}

const EMBED_PROSE_TRAIL_RE =
  /(?:\n\n|\n)?(?:Video dưới đây|Đây là (?:những )?video|Tham khảo (?:các )?video|Xem (?:các )?video tham chiếu)[^.!?…]*[.!?…]\s*$/iu;

export function stripSectionProseForEmbeddedRefs(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return trimmed;
  return trimmed.replace(EMBED_PROSE_TRAIL_RE, "").trim();
}

export function mapDiagnosisEmbeddedTiles(
  tiles: unknown[] | undefined,
  references: ReferenceVideoCard[],
): DiagnosisReferenceTile[] {
  if (!tiles?.length) return [];
  const byId: Record<string, ReferenceVideoCard> = {};
  for (const r of references) {
    if (r.aweme_id) byId[String(r.aweme_id)] = r;
  }
  const out: DiagnosisReferenceTile[] = [];
  for (const t of tiles) {
    if (!t || typeof t !== "object") continue;
    const row = t as Record<string, unknown>;
    const aid = String(row.aweme_id ?? row.video_id ?? "");
    const src = aid ? byId[aid] : undefined;
    if (!src) continue;
    const url = String(src.tiktok_url ?? row.video_url ?? row.tiktok_url ?? "");
    const thumb = String(src.thumbnail_url ?? row.thumbnail_url ?? "");
    const views = Number(src.views ?? row.views ?? 0) || 0;
    const snip = String(
      src.desc ?? row.caption_snippet ?? row.desc ?? "",
    ).slice(0, 200);
    const narrative = String(row.narrative_vi ?? row.narrative ?? "").trim();
    if (!url && !thumb && !snip && !narrative) continue;
    out.push({
      aweme_id: aid || undefined,
      video_url: url,
      thumbnail_url: thumb,
      views,
      caption_snippet: snip,
      posted_at: String(row.posted_at ?? ""),
      content_format: (src.content_format ?? row.content_format) as string | undefined,
      narrative_vi: narrative || undefined,
      author_handle: src.author_handle ?? null,
      hook_type: src.hook_type ?? null,
    });
  }
  return out;
}

export function embeddedTilesFromEvidenceAnchors(
  anchors: DiagnosisEvidenceAnchorVi[] | undefined,
  references: ReferenceVideoCard[],
  sectionId: string,
): DiagnosisReferenceTile[] {
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

export function buildDiagnosisReferenceTiles(
  section: DiagnosisSectionVi,
  referenceVideos: ReferenceVideoCard[],
  evidenceAnchors?: DiagnosisEvidenceAnchorVi[],
): DiagnosisReferenceTile[] {
  const sid = String(section.section_id ?? "");
  const fromSection = mapDiagnosisEmbeddedTiles(section.embedded_tiles, referenceVideos);
  const merged =
    fromSection.length > 0
      ? fromSection
      : embeddedTilesFromEvidenceAnchors(evidenceAnchors, referenceVideos, sid);
  return merged.slice(0, 3);
}

export function referenceTileNarrative(tile: DiagnosisReferenceTile): string {
  const custom = tile.narrative_vi?.trim();
  if (custom) return custom;
  const desc = tile.caption_snippet?.trim();
  if (desc) {
    const clipped = desc.length > 180 ? `${desc.slice(0, 177)}…` : desc;
    return `Video trong ngách làm cùng chủ đề: «${clipped}». So sánh cách mở đầu và nhịp dẫn với clip của bạn.`;
  }
  return "Video tham chiếu trong cùng ngách — quan sát hook, nhịp dẫn và cách giữ chân ở vài giây đầu.";
}

export function formatCreatorHandle(handle: string | null | undefined): string | null {
  if (!handle?.trim()) return null;
  const h = handle.trim();
  return h.startsWith("@") ? h : `@${h}`;
}
