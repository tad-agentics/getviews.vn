import type {
  ChannelPerformerTile,
  DiagnosisEvidenceAnchorVi,
  DiagnosisFinding,
  DiagnosisSectionVi,
  ReferenceVideoCard,
} from "@/lib/api-types";
import { contentFormatLabelVi } from "@/lib/contentFormatLabels";
import { hookNameVI } from "@/lib/constants/hook-names-vi";
import { fixChipMeta } from "@/lib/findingFixChip";
import { formatViews } from "@/lib/formatters";

/** One peer reference video shown under a diagnosis section. */
export interface DiagnosisReferenceTile extends ChannelPerformerTile {
  aweme_id?: string;
  /** Per-video comparison copy from synthesis (preferred). */
  narrative_vi?: string;
  author_handle?: string | null;
  hook_type?: string | null;
  /** R2-hosted MP4 — present ⇒ play inline instead of linking to TikTok. */
  playback_url?: string | null;
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
      playback_url: src.playback_url ?? null,
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

function referenceHookFormatPhrases(tile: DiagnosisReferenceTile): {
  hookPhrase: string;
  formatPhrase: string;
} {
  const hookRaw = tile.hook_type?.trim();
  const fmtRaw = tile.content_format?.trim();
  const hookVi = hookRaw ? hookNameVI(hookRaw) : "";
  const fmtVi = fmtRaw ? contentFormatLabelVi(fmtRaw) : null;
  return {
    hookPhrase: hookVi ? `hook dạng ${hookVi}` : "",
    formatPhrase: fmtVi ? `định dạng ${fmtVi}` : "",
  };
}

function referenceFallbackNarrative(
  tile: DiagnosisReferenceTile,
  topic: ReferenceBridgeTopic = "general",
): string {
  const { hookPhrase, formatPhrase } = referenceHookFormatPhrases(tile);
  if (hookPhrase && formatPhrase) {
    return topic === "structure"
      ? `xen cận đều và giữ nhịp cắt chặt hơn clip đang phân tích nhờ ${hookPhrase} và ${formatPhrase}.`
      : `giữ nhịp mở và giữ chân tốt hơn mức view thường trong ngách nhờ ${hookPhrase} và ${formatPhrase}.`;
  }
  if (hookPhrase) {
    return topic === "structure"
      ? `giữ nhịp cắt và âm nền ổn định suốt clip nhờ ${hookPhrase} ngay khung mở.`
      : `giữ chân ổn định suốt clip nhờ ${hookPhrase} ngay khung mở.`;
  }
  if (formatPhrase) {
    return topic === "structure"
      ? `phân bổ cảnh và nhịp dẫn rõ hơn clip đang phân tích nhờ ${formatPhrase}.`
      : `giữ nhịp dẫn ổn định suốt clip nhờ ${formatPhrase}.`;
  }
  return topic === "structure"
    ? "xen cận đều và tránh dead air — đối chiếu nhịp cắt, cảnh và âm thanh với clip của bạn."
    : "giữ chân ổn định suốt clip — đối chiếu cách mở đầu, nhịp dẫn và chốt với clip của bạn.";
}

const GENERIC_REF_LEAD_RE =
  /^(?:Được chọn vì|Tham chiếu vì|Lý do tham chiếu:)\s*/iu;
const GENERIC_REF_ANGLE_RE =
  /\s*(?:So format và giữ chân suốt clip với video đang phân tích\.|Quan sát cấu trúc kịch bản và nhịp cuốn\.|Chú ý tương tác giữa clip và CTA chốt\.|Đối chiếu cách mở đầu và giữ chân với clip đang phân tích\.|Quan sát nhịp truyền tải và cách chốt ý cho lần quay tiếp theo của creator\.|Học cách duy trì momentum giữa clip mà không bị rời nhịp\.)\s*$/iu;
const GAP_FRAMED_NARRATIVE_RE = /để\s+(?:xử lý|sửa|khắc phục)/iu;

/** Strip cached backend boilerplate from tile narratives before gap reframing. */
export function stripGenericReferenceBoilerplate(text: string): string {
  let t = text.trim();
  if (!t) return t;
  t = t.replace(GENERIC_REF_LEAD_RE, "");
  t = t.replace(GENERIC_REF_ANGLE_RE, "");
  return t.trim();
}

/** Split findings into keep-advice (điểm mạnh) vs corrective (khoảng trống). */
export function partitionFindingsByChip(findings: DiagnosisFinding[]): {
  strengths: DiagnosisFinding[];
  gaps: DiagnosisFinding[];
} {
  const strengths: DiagnosisFinding[] = [];
  const gaps: DiagnosisFinding[] = [];
  for (const f of findings) {
    if (fixChipMeta(f.fix_vi).positive) {
      strengths.push(f);
    } else {
      gaps.push(f);
    }
  }
  return { strengths, gaps };
}

export type ReferenceBridgeTopic = "general" | "structure";

/** Lead-in prose before reference cards — ties gaps to peer examples. */
export function formatReferenceBridgeProse(
  gaps: DiagnosisFinding[],
  tileCount: number,
  topic: ReferenceBridgeTopic = "general",
): string {
  if (!tileCount || !gaps.length) return "";
  const titles = gaps.map((g) => g.title_vi?.trim()).filter(Boolean) as string[];
  if (!titles.length) {
    if (topic === "structure") {
      return tileCount === 1
        ? "Clip tham chiếu dưới minh họa cách creator trong ngách xử lý nhịp, cảnh và âm thanh — đối chiếu với dòng thời gian video của bạn."
        : `${tileCount} clip dưới minh họa cách creator trong ngách xử lý từng thiếu sót về nhịp/cảnh/âm — đối chiếu với dòng thời gian video của bạn.`;
    }
    return tileCount === 1
      ? "Clip tham chiếu dưới minh họa cách creator trong ngách xử lý điểm cần cải thiện — đối chiếu cách mở đầu và giữ nhịp với video của bạn."
      : `${tileCount} clip dưới minh họa cách creator trong ngách xử lý từng điểm cần cải thiện — đối chiếu cách mở đầu và giữ nhịp với video của bạn.`;
  }
  if (titles.length === 1 && tileCount === 1) {
    if (topic === "structure") {
      return `Để khắc phục thiếu sót «${titles[0]}», xem clip tham chiếu dưới — creator trong ngách đã xử lý nhịp/cảnh/âm đúng điểm này như thế nào.`;
    }
    return `Để khắc phục «${titles[0]}», xem clip tham chiếu dưới — creator trong ngách đã xử lý đúng điểm này như thế nào.`;
  }
  const listed = titles.map((t) => `«${t}»`).join(", ");
  if (topic === "structure") {
    return `${tileCount} clip dưới là ví dụ trong ngách cho thiếu sót ${listed} — mỗi clip gắn một hướng sửa nhịp/cảnh cụ thể.`;
  }
  return `${tileCount} clip dưới là ví dụ trong ngách cho ${listed} — mỗi clip gắn với một hướng sửa cụ thể.`;
}

function sentenceCaseVi(text: string): string {
  const t = text.trim();
  if (!t) return t;
  return t.charAt(0).toLowerCase() + t.slice(1);
}

/** Card copy: peer lesson framed as evidence for one gap (+ optional fix). */
export function buildGapLinkedTileNarrative(
  tile: DiagnosisReferenceTile,
  gap?: Pick<DiagnosisFinding, "title_vi" | "fix_vi">,
  topic: ReferenceBridgeTopic = "general",
): string {
  const cleaned = stripGenericReferenceBoilerplate(tile.narrative_vi?.trim() ?? "");
  if (cleaned && GAP_FRAMED_NARRATIVE_RE.test(cleaned)) {
    return cleaned;
  }

  let peerLesson = cleaned;
  if (peerLesson.length < 24) {
    peerLesson = stripGenericReferenceBoilerplate(referenceFallbackNarrative(tile, topic));
  }

  const gapTitle = gap?.title_vi?.trim();
  if (!gapTitle) {
    return peerLesson || referenceTileNarrative(tile);
  }

  const fix = gap?.fix_vi?.trim();
  const fixClause =
    fix && !fixChipMeta(fix).positive
      ? ` Áp dụng: ${sentenceCaseVi(fix.replace(/\.$/, ""))}.`
      : "";

  const compareFallback =
    topic === "structure"
      ? "đối chiếu nhịp cắt, cảnh và âm thanh của clip này với video của bạn"
      : "đối chiếu cách clip này mở đầu và giữ nhịp so với video của bạn";

  const core = peerLesson
    ? `Để xử lý «${gapTitle}», clip này ${sentenceCaseVi(peerLesson.replace(/\.$/, ""))}.`
    : `Để xử lý «${gapTitle}», ${compareFallback}.`;

  return `${core}${fixClause}`;
}

/** Clone tiles with gap-aware narratives for strength-gap diagnosis layout. */
export function enrichReferenceTilesForGaps(
  tiles: DiagnosisReferenceTile[],
  gaps: DiagnosisFinding[],
  topic: ReferenceBridgeTopic = "general",
): DiagnosisReferenceTile[] {
  if (!gaps.length) return tiles;
  return tiles.map((tile, i) => ({
    ...tile,
    narrative_vi: buildGapLinkedTileNarrative(tile, gaps[i] ?? gaps[0], topic),
  }));
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
    return `cùng chủ đề «${clipped}» nhưng mở đầu và nhịp dẫn rõ hơn clip đang phân tích.`;
  }
  return referenceFallbackNarrative(tile);
}

export function formatCreatorHandle(handle: string | null | undefined): string | null {
  if (!handle?.trim()) return null;
  const h = handle.trim();
  return h.startsWith("@") ? h : `@${h}`;
}
