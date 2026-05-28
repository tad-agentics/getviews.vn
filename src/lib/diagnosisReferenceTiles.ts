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

const LEGACY_REF_NARRATIVE_LEAD_RE =
  /^(?:Kênh|Tài khoản|Nhà sáng tạo|Trang)\s+@\S+/iu;
const VIEW_COUNT_IN_NARRATIVE_RE = /\([\d.,]+[KM]?\s*view\)/iu;
const LEGACY_WEAK_MIDDLE_RE =
  /^(?:đang vận hành cực kỳ hiệu quả|ghi nhận hiệu suất tương tác rất tốt|đạt các chỉ số tăng trưởng rất ấn tượng)\.\s*/iu;

/** Strip handle/view boilerplate from cached tile narratives (footer already shows both). */
export function sanitizeReferenceTileNarrative(text: string): string {
  let t = text.trim();
  if (!t) return t;
  if (LEGACY_REF_NARRATIVE_LEAD_RE.test(t) || VIEW_COUNT_IN_NARRATIVE_RE.test(t)) {
    t = t.replace(
      /^(?:Kênh|Tài khoản|Nhà sáng tạo|Trang)\s+@\S+\s*\([^)]*view\)\s*/iu,
      "",
    );
    t = t.replace(LEGACY_WEAK_MIDDLE_RE, "");
  }
  return t.trim();
}

function referenceFallbackNarrative(tile: DiagnosisReferenceTile): string {
  const hook = tile.hook_type?.trim();
  const fmt = tile.content_format?.trim();
  const parts: string[] = [];
  if (hook) parts.push(`hook ${hook}`);
  if (fmt) parts.push(`format ${fmt}`);
  if (parts.length > 0) {
    return `Được chọn vì ${parts.join(" và ")} làm tốt hơn median — đối chiếu nhịp mở và cách giữ chân với clip của bạn.`;
  }
  return "Được chọn vì cấu trúc format giữ chân ổn định — đối chiếu hook, nhịp dẫn và cách chốt với clip của bạn.";
}

export function referenceTileNarrative(tile: DiagnosisReferenceTile): string {
  const custom = tile.narrative_vi?.trim();
  if (custom) {
    const cleaned = sanitizeReferenceTileNarrative(custom);
    if (cleaned.length >= 32) return cleaned;
  }
  const desc = tile.caption_snippet?.trim();
  if (desc) {
    const clipped = desc.length > 180 ? `${desc.slice(0, 177)}…` : desc;
    return `Được chọn vì cùng chủ đề «${clipped}» — so sánh cách mở đầu và nhịp dẫn với clip của bạn.`;
  }
  return referenceFallbackNarrative(tile);
}

export function formatCreatorHandle(handle: string | null | undefined): string | null {
  if (!handle?.trim()) return null;
  const h = handle.trim();
  return h.startsWith("@") ? h : `@${h}`;
}
