import { formatDiagnosisSectionTitle } from "@/lib/formatters";
import { hasStatsHistorySnapshots } from "@/lib/statsHistoryProse";
import { VIDEO_STRUCTURE_SECTION_TITLE } from "@/lib/mergeVideoStructureSections";
import type {
  CreatorComparison,
  DiagnosisSectionVi,
  NarrativeVi,
  VideoAnalyzeMeta,
  VideoEnrichment,
  VideoFlopIssue,
  VideoHookPhase,
  VideoReportPayload,
} from "@/lib/api-types";

export function findDiagnosisSection(
  sections: DiagnosisSectionVi[],
  sectionId: string,
): DiagnosisSectionVi | undefined {
  return sections.find((s) => String(s.section_id) === sectionId);
}

export function diagnosisSectionText(section: DiagnosisSectionVi | undefined): string {
  if (!section) return "";
  return (section.text_vi || section.text || "").trim();
}

export function hasContextStripContent(
  meta: VideoAnalyzeMeta,
  enrichment?: VideoEnrichment | null,
): boolean {
  const ratio = meta.target_vs_creator_median ?? null;
  const median = meta.creator_median_views ?? null;
  const hasRatio = ratio != null && median != null && median > 0;
  const audience = enrichment?.target_audience?.trim() ?? "";
  const painPoints = (enrichment?.pain_points ?? []).filter((p) => p.trim().length > 0);
  const styleTags = (enrichment?.style_tags ?? []).filter((s) => s.trim().length > 0);
  const promotion = enrichment?.promotion_type ?? "organic";
  const showPromotion = promotion !== "organic";
  const toneLabel = enrichment?.tone?.trim() ?? "";
  return Boolean(
    hasRatio || audience || painPoints.length > 0 || styleTags.length > 0 || showPromotion || toneLabel,
  );
}

/**
 * Derive the vs-channel-median label from the ratio itself.
 *
 * Bug-fix (2026-06-12): the BE used to label every ratio in [0.5, 2) as
 * "dưới mức trung bình" — a 1.3× video (ABOVE median) rendered as
 * below-average right next to the "1,3×" number. Deriving the label from
 * `target_vs_median` on the FE also shields cached reports that still carry
 * the inverted string. Bands match cloud-run `target_percentile_label`:
 * <0.5 thấp nhất · 0.5–<0.8 dưới · 0.8–1.2 quanh · >1.2 trên · ≥5 top 10%.
 */
export function creatorComparisonPercentileLabel(
  ratio: number | null | undefined,
  fallback?: string | null,
): string {
  if (ratio == null || !Number.isFinite(ratio)) return fallback?.trim() ?? "";
  if (ratio >= 5) return "top 10% kênh";
  if (ratio > 1.2) return "trên mức trung bình";
  if (ratio >= 0.8) return "quanh mức trung bình";
  if (ratio >= 0.5) return "dưới mức trung bình";
  return "hiệu suất thấp nhất kênh";
}

export function buildCreatorComparisonProse(
  data: CreatorComparison,
  metaViews: number,
  isFlop: boolean,
): string {
  const handle = data.creator_handle?.trim() || "kênh bạn";
  const posts = data.total_posts_analyzed ?? 0;
  const mult =
    data.target_vs_median != null
      ? data.target_vs_median.toLocaleString("vi-VN", { maximumFractionDigits: 1 })
      : null;
  const percentile = creatorComparisonPercentileLabel(
    data.target_vs_median,
    data.target_percentile,
  );
  const viewsLabel = metaViews > 0 ? `${metaViews.toLocaleString("vi-VN")} view` : "lượt xem hiện tại";
  const channelTypical = "mức view thường trên kênh";

  if (isFlop) {
    return [
      posts > 0
        ? `Trên ${posts} bài gần đây của ${handle}, video này (${viewsLabel}) đang dưới ${channelTypical}${mult ? ` — khoảng ${mult}× so với mức đó` : ""}${percentile ? ` (${percentile})` : ""}.`
        : `So với các video khác trên ${handle}, clip này đang yếu hơn mức trung bình kênh.`,
      "Cặp hit/flop bên dưới cho thấy format và hook nào đang kéo view — không chỉ so một clip đơn lẻ.",
    ].join(" ");
  }

  return [
    posts > 0
      ? `Trên ${posts} bài gần đây của ${handle}, video này (${viewsLabel})${mult ? ` đạt khoảng ${mult}× ${channelTypical}` : ` đang nổi trên ${channelTypical}`}${percentile ? ` — ${percentile}` : ""}.`
      : `Video này đang chạy tốt hơn ${channelTypical} trên ${handle}.`,
    "Hai mẫu hit/flop trên cùng kênh giúp thấy format và hook đang phân hóa — trước khi copy sang clip tiếp theo.",
  ].join(" ");
}

export function buildScriptStructureFallbackProse(durationSec: number): string {
  const sec = Math.max(1, Math.round(durationSec));
  return `Phân tích đọc video qua các khung hình được lấy mẫu theo thời gian, rồi gom thành các nhịp kịch bản trong ${sec} giây. Khi nhịp cắt có tín hiệu rõ (hook dài/ngắn, thân chia lệch), thanh thời gian hiện mốc giây từng nhịp — nếu không thấy thanh, xem phần «Nhịp & cắt» bên dưới.`;
}

export function buildHookAnalysisFallbackProse(
  phases: VideoHookPhase[] | undefined,
  isFlop: boolean,
  narrativeVi?: NarrativeVi | null,
  flopIssues?: VideoFlopIssue[],
): string {
  const hookNarrative = narrativeVi?.loi_chinh_narrative?.find((n) =>
    String(n.error_id ?? "").toLowerCase().includes("hook"),
  )?.narrative?.trim();
  if (hookNarrative) return hookNarrative;

  const firstPhase = phases?.[0];
  const phaseHint = firstPhase?.label?.trim() || firstPhase?.body?.trim();
  const lead = isFlop
    ? "Ba giây đầu quyết định phần lớn người rời — đây là cửa sổ dễ sửa nhất trước khi quay lại."
    : "Ba giây đầu cho biết vì sao người xem dừng lại — dù video đã breakout, hook vẫn là điểm tối ưu tiếp theo.";

  const detail = phaseHint
    ? ` Tóm tắt từ phân tích hình: ${phaseHint.slice(0, 160)}${phaseHint.length > 160 ? "…" : ""}.`
    : "";

  const flopHook = flopIssues?.find((e) => /hook/i.test(e.title ?? e.error_id ?? ""));
  if (flopHook?.fix?.trim()) {
    return `${lead}${detail} Gợi ý sửa: ${flopHook.fix.trim()}`;
  }
  return `${lead}${detail}`;
}

export function buildMetadataFallbackProse(meta: VideoAnalyzeMeta): string {
  const niche = meta.niche_label?.trim();
  const posted = meta.date_posted?.trim();
  const parts = [
    "Các chỉ số so với kênh, giọng điệu và đối tượng nhắm giúp đặt video trong bối cảnh — không chỉ nhìn view tuyệt đối.",
  ];
  if (niche) parts.push(`Ngách phân tích: ${niche}.`);
  if (posted) parts.push(`Đăng ${posted}.`);
  return parts.join(" ");
}

export function adjunctSectionTitle(
  sectionId: string,
  section: DiagnosisSectionVi | undefined,
  performanceTier: "hit" | "average" | "flop" | "unknown",
): string {
  const fromSection = (section?.title_vi || section?.title || "").trim();
  if (fromSection) return formatDiagnosisSectionTitle(fromSection);

  const defaults: Record<string, Record<string, string>> = {
    script_structure: {
      hit: VIDEO_STRUCTURE_SECTION_TITLE,
      average: VIDEO_STRUCTURE_SECTION_TITLE,
      flop: VIDEO_STRUCTURE_SECTION_TITLE,
      unknown: VIDEO_STRUCTURE_SECTION_TITLE,
    },
    hook_analysis: {
      hit: "Giải mã hook · 3 giây đầu vì sao người xem dừng",
      average: "Giải mã hook · 3 giây đầu",
      flop: "Giải mã hook · 3 giây đầu dễ mất người xem",
      unknown: "Giải mã hook",
    },
    metadata: {
      hit: "Phân tích bối cảnh & diễn biến",
      average: "Phân tích bối cảnh & diễn biến",
      flop: "Phân tích bối cảnh & diễn biến",
      unknown: "Phân tích bối cảnh & diễn biến",
    },
  };
  const tier = performanceTier in defaults.script_structure ? performanceTier : "unknown";
  const fallback = defaults[sectionId]?.[tier] ?? sectionId;
  return formatDiagnosisSectionTitle(fallback);
}

export function shouldShowScriptStructureBlock(report: VideoReportPayload): boolean {
  if ((report.segments?.length ?? 0) > 0) return true;
  // Safety net for legacy/corpus-replayed payloads with no stored segments: a
  // real (non-carousel) video with a known duration still gets a structure
  // block — the adjunct renderer derives prose from duration alone.
  const fmt = (report.meta?.content_format ?? "").toLowerCase();
  if (fmt.includes("carousel")) return false;
  return (report.meta?.duration_sec ?? 0) > 0;
}

/** Hook phase cards + 0–3s timeline removed from UI — hook value lives in v6 findings/prose. */
export function shouldShowHookAnalysisBlock(_report: VideoReportPayload): boolean {
  return false;
}

export function shouldShowMetadataBlock(
  meta: VideoAnalyzeMeta,
  enrichment?: VideoEnrichment | null,
): boolean {
  return (
    hasContextStripContent(meta, enrichment) ||
    hasStatsHistorySnapshots(meta.stats_history)
  );
}
