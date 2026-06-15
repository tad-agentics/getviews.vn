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
  /** Seek target when opening inline peer playback (hook window). */
  peer_hook_start_sec?: number | null;
}

const EMBED_PROSE_TRAIL_RE =
  /(?:\n\n|\n)?(?:Video dưới đây|Đây là (?:những )?video|Tham khảo (?:các )?video|Xem (?:các )?video tham chiếu)[^.!?…]*[.!?…]\s*$/iu;

const NICHE_BRIDGE_TRAIL_RE =
  /(?:\n\n|\n)?(?:\d+\s+clip dưới (?:là )?video dẫn đầu ngách|Clip dưới là video dẫn đầu ngách)[^.!?…]*[.!?…]\s*$/iu;

const NICHE_BRIDGE_INLINE_RE =
  /(?:\d+\s+clip dưới (?:là )?video dẫn đầu ngách|Clip dưới là video dẫn đầu ngách)/iu;

export function stripSectionProseForEmbeddedRefs(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return trimmed;
  return trimmed
    .replace(EMBED_PROSE_TRAIL_RE, "")
    .replace(NICHE_BRIDGE_TRAIL_RE, "")
    .trim();
}

/** True when synthesis already ends with a niche-pattern reference bridge sentence. */
export function sectionProseHasNichePatternBridge(text: string): boolean {
  return NICHE_BRIDGE_INLINE_RE.test(text.trim());
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
    const snip = sanitizeReferenceCaptionSnippet(
      String(src.desc ?? row.caption_snippet ?? row.desc ?? ""),
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
      peer_hook_start_sec: src.peer_hook_start_sec ?? null,
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

/** Mirrors ``analysis_guards.TRANSCRIPT_UNAVAILABLE_MARKER`` — strip before user-facing copy. */
const INTERNAL_TRANSCRIPT_MARKER_RE =
  /\[Transcript không khả dụng[^\]]*\]/giu;

/** Remove internal transcript-failure markers from reference captions (cached reports). */
export function sanitizeReferenceCaptionSnippet(text: string): string {
  return text.replace(INTERNAL_TRANSCRIPT_MARKER_RE, " ").replace(/\s+/g, " ").trim();
}

/** Strip handle/view boilerplate from cached tile narratives (footer already shows both). */
export function sanitizeReferenceTileNarrative(text: string): string {
  let t = sanitizeReferenceCaptionSnippet(text.trim());
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
      : topic === "hook"
        ? `mở 3 giây đầu rõ hơn clip đang phân tích nhờ ${hookPhrase} và ${formatPhrase}.`
        : `giữ nhịp mở và giữ chân tốt hơn mức view thường trong ngách nhờ ${hookPhrase} và ${formatPhrase}.`;
  }
  if (hookPhrase) {
    return topic === "structure"
      ? `giữ nhịp cắt và âm nền ổn định suốt clip nhờ ${hookPhrase} ngay khung mở.`
      : topic === "hook"
        ? `xử lý 3 giây đầu rõ hơn clip đang phân tích nhờ ${hookPhrase} ngay khung mở.`
        : `giữ chân ổn định suốt clip nhờ ${hookPhrase} ngay khung mở.`;
  }
  if (formatPhrase) {
    return topic === "structure"
      ? `phân bổ cảnh và nhịp dẫn rõ hơn clip đang phân tích nhờ ${formatPhrase}.`
      : topic === "hook"
        ? `mở đầu mute-safe và dẫn ý rõ hơn clip đang phân tích nhờ ${formatPhrase}.`
        : `giữ nhịp dẫn ổn định suốt clip nhờ ${formatPhrase}.`;
  }
  return topic === "structure"
    ? "xen cận đều và tránh dead air — đối chiếu nhịp cắt, cảnh và âm thanh với clip của bạn."
    : topic === "hook"
      ? "mở 3 giây đầu rõ và giữ chân tốt hơn — đối chiếu text overlay, lời thoại và visual layering với clip của bạn."
      : "giữ chân ổn định suốt clip — đối chiếu cách mở đầu, nhịp dẫn và chốt với clip của bạn.";
}

const GENERIC_REF_LEAD_RE =
  /^(?:Được chọn vì|Tham chiếu vì|Lý do tham chiếu:)\s*/iu;
const GENERIC_REF_ANGLE_RE =
  /\s*(?:So format và giữ chân suốt clip với video đang phân tích\.|Quan sát cấu trúc kịch bản và nhịp cuốn\.|Chú ý tương tác giữa clip và CTA chốt\.|Đối chiếu cách mở đầu và giữ chân với clip đang phân tích\.|Quan sát nhịp truyền tải và cách chốt ý cho lần quay tiếp theo của creator\.|Học cách duy trì momentum giữa clip mà không bị rời nhịp\.)\s*$/iu;
const GAP_FRAMED_NARRATIVE_RE = /để\s+(?:xử lý|sửa|khắc phục)/iu;
const GAP_TITLE_FRAME_PREFIX_RE =
  /^Để\s+(?:xử lý|sửa|khắc phục)\s+«[^»]+»,\s*(?:clip này\s+)?/iu;

function stripGapTitleFrame(text: string): string {
  return text.replace(GAP_TITLE_FRAME_PREFIX_RE, "").trim();
}

/** Strip cached backend boilerplate from tile narratives before gap reframing. */
export function stripGenericReferenceBoilerplate(text: string): string {
  let t = text.trim();
  if (!t) return t;
  t = t.replace(GENERIC_REF_LEAD_RE, "");
  t = t.replace(GENERIC_REF_ANGLE_RE, "");
  return t.trim();
}

/**
 * Split findings into three buckets:
 * - `strengths`: keep-advice (fix_vi starts «Tiếp tục»/«Giữ»/…).
 * - `gaps`: corrective findings that carry an actionable `fix_vi`.
 * - `observations`: findings with no `fix_vi` — neither keep nor fix.
 *
 * Only `gaps` pull peer reference clips; a finding without `fix_vi` no
 * longer drags an unrelated peer video onto the report (2026-06-13 audit).
 */
export function partitionFindingsByChip(findings: DiagnosisFinding[]): {
  strengths: DiagnosisFinding[];
  gaps: DiagnosisFinding[];
  observations: DiagnosisFinding[];
} {
  const strengths: DiagnosisFinding[] = [];
  const gaps: DiagnosisFinding[] = [];
  const observations: DiagnosisFinding[] = [];
  for (const f of findings) {
    const hasFix = Boolean(f.fix_vi?.trim());
    if (hasFix && fixChipMeta(f.fix_vi).positive) {
      strengths.push(f);
    } else if (hasFix) {
      gaps.push(f);
    } else {
      observations.push(f);
    }
  }
  return { strengths, gaps, observations };
}

export type ReferenceBridgeTopic = "general" | "structure" | "hook";

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
    if (topic === "hook") {
      return tileCount === 1
        ? "Clip tham chiếu dưới minh họa cách creator trong ngách xử lý 3 giây đầu — đối chiếu text overlay, lời thoại và visual layering với video của bạn."
        : `${tileCount} clip dưới minh họa cách creator trong ngách xử lý từng thiếu sót hook — đối chiếu 3 giây mở đầu với video của bạn.`;
    }
    return tileCount === 1
      ? "Clip tham chiếu dưới minh họa cách creator trong ngách xử lý điểm cần cải thiện — đối chiếu cách mở đầu và giữ nhịp với video của bạn."
      : `${tileCount} clip dưới minh họa cách creator trong ngách xử lý từng điểm cần cải thiện — đối chiếu cách mở đầu và giữ nhịp với video của bạn.`;
  }
  if (titles.length === 1 && tileCount === 1) {
    if (topic === "structure") {
      return `Để khắc phục thiếu sót «${titles[0]}», xem clip tham chiếu dưới — creator trong ngách đã xử lý nhịp/cảnh/âm đúng điểm này như thế nào.`;
    }
    if (topic === "hook") {
      return `Để khắc phục «${titles[0]}», xem clip tham chiếu dưới — creator trong ngách đã xử lý 3 giây đầu đúng điểm này như thế nào.`;
    }
    return `Để khắc phục «${titles[0]}», xem clip tham chiếu dưới — creator trong ngách đã xử lý đúng điểm này như thế nào.`;
  }
  const listed = titles.map((t) => `«${t}»`).join(", ");
  if (topic === "structure") {
    return `${tileCount} clip dưới là ví dụ trong ngách cho thiếu sót ${listed} — mỗi clip gắn một hướng sửa nhịp/cảnh cụ thể.`;
  }
  if (topic === "hook") {
    return `${tileCount} clip dưới là ví dụ trong ngách cho thiếu sót hook ${listed} — mỗi clip gắn một hướng sửa 3 giây đầu cụ thể.`;
  }
  return `${tileCount} clip dưới là ví dụ trong ngách cho ${listed} — mỗi clip gắn với một hướng sửa cụ thể.`;
}

/** Lead-in before niche_pattern reference grid — top peers / same formula. */
export function formatNichePatternBridgeProse(
  tileCount: number,
  formatLabel?: string | null,
): string {
  if (!tileCount) return "";
  const fmt = formatLabel?.trim();
  const fmtClause = fmt ? ` định dạng ${fmt}` : " công thức đang chạy";
  if (tileCount === 1) {
    return `Clip dưới là video dẫn đầu ngách cùng${fmtClause} — đối chiếu hook, nhịp và cách giữ chân với clip đang phân tích.`;
  }
  return `${tileCount} clip dưới là video dẫn đầu ngách cùng${fmtClause} — mỗi clip minh họa một cách triển khai công thức đang thắng view trong ngách.`;
}

/** When synthesis omits tiles, surface top corpus peers for niche_pattern. */
export function referenceCardToTile(src: ReferenceVideoCard): DiagnosisReferenceTile {
  const tile: DiagnosisReferenceTile = {
    aweme_id: String(src.aweme_id),
    video_url: String(src.tiktok_url ?? ""),
    thumbnail_url: String(src.thumbnail_url ?? ""),
    views: Number(src.views ?? 0) || 0,
    caption_snippet: sanitizeReferenceCaptionSnippet(String(src.desc ?? "")).slice(0, 200),
    posted_at: "",
    content_format: src.content_format ?? undefined,
    author_handle: src.author_handle ?? null,
    hook_type: src.hook_type ?? null,
    playback_url: src.playback_url ?? null,
    peer_hook_start_sec: src.peer_hook_start_sec ?? null,
  };
  return {
    ...tile,
    narrative_vi: referenceTileNarrative(tile),
  };
}

export function fallbackNichePatternReferenceTiles(
  referenceVideos: ReferenceVideoCard[],
  limit = 3,
  analyzedContentFormat?: string | null,
  excludeIds?: ReadonlySet<string>,
): DiagnosisReferenceTile[] {
  const analyzedFmt = analyzedContentFormat?.trim().toLowerCase() ?? "";
  const eligible = referenceVideos.filter(
    (r) =>
      r.aweme_id &&
      (!excludeIds || !excludeIds.has(String(r.aweme_id))) &&
      (r.thumbnail_url || r.tiktok_url),
  );
  const sameFormat = analyzedFmt
    ? eligible.filter((r) => String(r.content_format ?? "").toLowerCase() === analyzedFmt)
    : [];
  const pool = sameFormat.length > 0 ? sameFormat : eligible;
  const sorted = [...pool].sort((a, b) => (Number(b.views) || 0) - (Number(a.views) || 0));
  return sorted.slice(0, limit).map(referenceCardToTile);
}

/**
 * Tracks aweme_ids already shown in this report render so fallback peer
 * picks rotate through the corpus instead of repeating the same top-3 everywhere.
 */
export class ReferenceTileAllocator {
  private usedIds = new Set<string>();

  constructor(private readonly referenceVideos: ReferenceVideoCard[]) {}

  private sortedPool(
    analyzedContentFormat?: string | null,
    extraExclude?: ReadonlySet<string>,
  ): ReferenceVideoCard[] {
    const analyzedFmt = analyzedContentFormat?.trim().toLowerCase() ?? "";
    const eligible = this.referenceVideos.filter((r) => {
      const id = r.aweme_id ? String(r.aweme_id) : "";
      if (!id || !(r.thumbnail_url || r.tiktok_url)) return false;
      if (this.usedIds.has(id)) return false;
      if (extraExclude?.has(id)) return false;
      return true;
    });
    const sameFormat = analyzedFmt
      ? eligible.filter((r) => String(r.content_format ?? "").toLowerCase() === analyzedFmt)
      : [];
    const pool = sameFormat.length > 0 ? sameFormat : eligible;
    return [...pool].sort((a, b) => (Number(b.views) || 0) - (Number(a.views) || 0));
  }

  private markUsed(tiles: DiagnosisReferenceTile[]) {
    for (const tile of tiles) {
      if (tile.aweme_id) this.usedIds.add(String(tile.aweme_id));
    }
  }

  /** Prefer synthesis-linked tiles; swap duplicates for unused corpus peers when possible. */
  private diversify(
    tiles: DiagnosisReferenceTile[],
    analyzedContentFormat?: string | null,
  ): DiagnosisReferenceTile[] {
    const out: DiagnosisReferenceTile[] = [];
    const picked = new Set<string>();
    for (const tile of tiles) {
      const id = tile.aweme_id ? String(tile.aweme_id) : "";
      if (id && (this.usedIds.has(id) || picked.has(id))) {
        const alt = this.sortedPool(analyzedContentFormat, picked)[0];
        if (alt) {
          const replacement = referenceCardToTile(alt);
          out.push(replacement);
          picked.add(String(alt.aweme_id));
          continue;
        }
      }
      out.push(tile);
      if (id) picked.add(id);
    }
    return out;
  }

  allocateSectionTiles(
    section: DiagnosisSectionVi,
    evidenceAnchors: DiagnosisEvidenceAnchorVi[] | undefined,
    limit = 3,
    analyzedContentFormat?: string | null,
  ): DiagnosisReferenceTile[] {
    const built = buildDiagnosisReferenceTiles(section, this.referenceVideos, evidenceAnchors);
    const tiles =
      built.length > 0
        ? this.diversify(built, analyzedContentFormat).slice(0, limit)
        : fallbackNichePatternReferenceTiles(
            this.referenceVideos,
            limit,
            analyzedContentFormat,
            this.usedIds,
          );
    this.markUsed(tiles);
    return tiles;
  }

  allocateFallback(limit: number, analyzedContentFormat?: string | null): DiagnosisReferenceTile[] {
    const tiles = fallbackNichePatternReferenceTiles(
      this.referenceVideos,
      limit,
      analyzedContentFormat,
      this.usedIds,
    );
    this.markUsed(tiles);
    return tiles;
  }
}

function sentenceCaseVi(text: string): string {
  const t = text.trim();
  if (!t) return t;
  return t.charAt(0).toLowerCase() + t.slice(1);
}

function inlineCompareLine(topic: ReferenceBridgeTopic): string {
  if (topic === "hook") {
    return "So 3 giây đầu (cắt, chữ overlay, hình mở) với clip của bạn.";
  }
  if (topic === "structure") {
    return "Đối chiếu nhịp cắt, cảnh và âm thanh với clip đang phân tích.";
  }
  return "Đối chiếu cách mở đầu và giữ nhịp với clip của bạn.";
}

/** Strip gap framing / fix chip from tile narrative before inline finding prose. */
function inlinePeerLessonFromTile(
  tile: DiagnosisReferenceTile,
  topic: ReferenceBridgeTopic,
): string {
  let lesson = tile.narrative_vi?.trim() ?? "";
  lesson = stripGenericReferenceBoilerplate(lesson);
  lesson = stripGapTitleFrame(lesson);
  lesson = lesson.replace(/\s*Áp dụng:.*$/isu, "").trim();
  if (lesson.length < 20) {
    lesson = referenceFallbackNarrative(tile, topic);
  }
  return sentenceCaseVi(lesson.replace(/\.$/, ""));
}

/** Prose inside a gap finding card — peer lesson woven after the finding body. */
export function buildFindingInlinePeerProse(
  gap: DiagnosisFinding,
  tiles: DiagnosisReferenceTile[],
  topic: ReferenceBridgeTopic,
): string {
  if (!tiles.length) return "";

  const compare = inlineCompareLine(topic);

  if (tiles.length === 1) {
    const tile = tiles[0];
    const handle = formatCreatorHandle(tile.author_handle);
    const body = inlinePeerLessonFromTile(tile, topic);
    const peerLead = handle
      ? `Clip ${handle} trong ngách ${body}.`
      : `Clip tham chiếu ${body}.`;
    if (/đối chiếu|so 3 giây/i.test(body)) {
      return peerLead;
    }
    return `${peerLead} ${compare}`;
  }

  const segments = tiles.map((tile) => {
    const handle = formatCreatorHandle(tile.author_handle);
    const body = inlinePeerLessonFromTile(tile, topic);
    const who = handle ? `Clip ${handle}` : "Clip tham chiếu";
    return `${who} — ${body}.`;
  });
  const gapTitle = gap.title_vi?.trim();
  const prefix = gapTitle ? `Với **${gapTitle}**:\n\n` : "";
  const core = segments.join("\n\n");
  if (/đối chiếu|so 3 giây/i.test(core)) {
    return `${prefix}${core}`.trim();
  }
  return `${prefix}${core} ${compare}`.trim();
}

/**
 * Peer tiles for one gap row (inline finding cards).
 *
 * Pairing contract (synthesis → FE):
 * - **One gap** in the section/axis → every `embedded_tiles` entry renders under that gap.
 * - **Multiple gaps** → `embedded_tiles[i]` pairs with corrective finding `gaps[i]` (same order
 *   as `findings` after strength/gap partition). Extra tiles are ignored; extra gaps show
 *   `GAP_PEER_MISSING_VI`.
 * - Enrichment (`buildGapLinkedTileNarrative` with `inlineBridge`) runs here only — callers must
 *   pass raw `buildDiagnosisReferenceTiles` output, not pre-enriched tiles.
 */
export function peerTilesForGapAtIndex(
  gapIndex: number,
  gaps: DiagnosisFinding[],
  allReferenceTiles: DiagnosisReferenceTile[],
  topic: ReferenceBridgeTopic,
  inlineGapRefs: boolean,
): DiagnosisReferenceTile[] {
  if (!inlineGapRefs || !gaps.length || !allReferenceTiles.length) return [];
  if (gaps.length === 1) {
    return enrichReferenceTilesForGaps(allReferenceTiles, gaps, topic, true);
  }
  const enriched = enrichReferenceTilesForGaps(
    allReferenceTiles.slice(0, gaps.length),
    gaps,
    topic,
    true,
  );
  const tile = enriched[gapIndex];
  return tile ? [tile] : [];
}

/** Card copy: peer lesson framed as evidence for one gap (+ optional fix). */
export function buildGapLinkedTileNarrative(
  tile: DiagnosisReferenceTile,
  gap?: Pick<DiagnosisFinding, "title_vi" | "fix_vi">,
  topic: ReferenceBridgeTopic = "general",
  options?: { leadWithGapTitle?: boolean },
): string {
  const leadWithGapTitle = options?.leadWithGapTitle !== false;
  const cleaned = stripGenericReferenceBoilerplate(tile.narrative_vi?.trim() ?? "");
  if (cleaned && GAP_FRAMED_NARRATIVE_RE.test(cleaned) && leadWithGapTitle) {
    return cleaned;
  }

  let peerLesson = cleaned;
  if (GAP_FRAMED_NARRATIVE_RE.test(peerLesson)) {
    peerLesson = stripGapTitleFrame(peerLesson);
  }
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
      ? "Đối chiếu nhịp cắt, cảnh và âm thanh với clip đang phân tích"
      : topic === "hook"
        ? "So 3 giây đầu (cắt, chữ overlay, hình mở) với clip đang phân tích"
        : "Đối chiếu cách clip này mở đầu và giữ nhịp với clip đang phân tích";

  if (!leadWithGapTitle) {
    const bodyRaw = peerLesson
      ? sentenceCaseVi(peerLesson.replace(/\.$/, ""))
      : compareFallback;
    const body = bodyRaw.charAt(0).toUpperCase() + bodyRaw.slice(1);
    return `${body.endsWith(".") ? body : `${body}.`}${fixClause}`;
  }

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
  inlineBridge = false,
): DiagnosisReferenceTile[] {
  if (!gaps.length) return tiles;
  return tiles.map((tile, i) => ({
    ...tile,
    narrative_vi: buildGapLinkedTileNarrative(tile, gaps[i] ?? gaps[0], topic, {
      leadWithGapTitle: !inlineBridge,
    }),
  }));
}

/** Sections where peer corpus clips illustrate gaps — not strengths. */
export const PEER_REF_GAP_ONLY_SECTION_IDS = new Set([
  "diagnosis",
  "hook_analysis",
  "script_structure",
]);

/**
 * Peer reference videos belong under corrective findings only.
 * Strengths should cite the analyzed clip (timeline/segments), not other creators.
 */
export function resolvePeerReferenceTiles(
  sectionId: string,
  tiles: DiagnosisReferenceTile[],
  findings: DiagnosisFinding[],
  topic: ReferenceBridgeTopic = "general",
  inlineBridge = false,
): DiagnosisReferenceTile[] {
  if (!tiles.length) return [];
  if (!PEER_REF_GAP_ONLY_SECTION_IDS.has(sectionId.trim())) {
    return tiles;
  }
  const { gaps } = partitionFindingsByChip(findings);
  if (!gaps.length) return [];
  return enrichReferenceTilesForGaps(tiles.slice(0, gaps.length), gaps, topic, inlineBridge);
}

/** Shown under an inline gap card when the synthesis pool has no peer for that gap. */
export const GAP_PEER_MISSING_VI =
  "Chưa có clip tham chiếu trong ngách cho thiếu sót này.";

/** Lead-in copy before a single inline reference tile under one gap card. */
export function formatSingleGapBridgeProse(
  gapTitle: string,
  topic: ReferenceBridgeTopic = "general",
): string {
  const title = gapTitle.trim();
  if (!title) return "";
  if (topic === "structure") {
    return `Thiếu sót «${title}» — clip dưới minh họa cách ngách xử lý nhịp, cảnh và âm. Đối chiếu với clip của bạn.`;
  }
  if (topic === "hook") {
    return `Thiếu sót «${title}» — clip dưới minh họa cách ngách mở 3 giây đầu. So cắt, chữ overlay và hình mở với clip của bạn.`;
  }
  return `Thiếu sót «${title}» — clip dưới minh họa cách creator trong ngách xử lý điểm này.`;
}

export function referenceTileNarrative(tile: DiagnosisReferenceTile): string {
  const custom = tile.narrative_vi?.trim();
  if (custom) {
    const cleaned = sanitizeReferenceTileNarrative(custom);
    if (cleaned.length >= 32) return cleaned;
  }
  const desc = sanitizeReferenceCaptionSnippet(tile.caption_snippet?.trim() ?? "");
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
