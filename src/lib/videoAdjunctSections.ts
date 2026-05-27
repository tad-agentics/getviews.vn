import { formatDiagnosisSectionTitle } from "@/lib/formatters";
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
  const percentile = data.target_percentile?.trim();
  const viewsLabel = metaViews > 0 ? `${metaViews.toLocaleString("vi-VN")} view` : "lượt xem hiện tại";

  if (isFlop) {
    return [
      posts > 0
        ? `Trên ${posts} bài gần đây của ${handle}, video này (${viewsLabel}) đang dưới mức trung vị kênh${mult ? ` — khoảng ${mult}× median` : ""}${percentile ? ` (${percentile})` : ""}.`
        : `So với các video khác trên ${handle}, clip này đang yếu hơn mức trung bình kênh.`,
      "Cặp hit/flop bên dưới cho thấy format và hook nào đang kéo view — không chỉ so một clip đơn lẻ.",
    ].join(" ");
  }

  return [
    posts > 0
      ? `Trên ${posts} bài gần đây của ${handle}, video này (${viewsLabel})${mult ? ` đạt khoảng ${mult}× trung vị kênh` : " đang nổi trên median kênh"}${percentile ? ` — ${percentile}` : ""}.`
      : `Video này đang chạy tốt hơn median trên ${handle}.`,
    "Hai mẫu hit/flop trên cùng kênh giúp thấy format và hook đang phân hóa — trước khi copy sang clip tiếp theo.",
  ].join(" ");
}

export function buildScriptStructureFallbackProse(durationSec: number): string {
  const sec = Math.max(1, Math.round(durationSec));
  return `Phân tích đọc video qua các khung hình được lấy mẫu theo thời gian (nhận diện hình + cấu trúc cảnh), rồi gom thành 8 nhịp kịch bản trong ${sec} giây. Số % trên mỗi ô là phần thời lượng dành cho nhịp đó — không phải tỉ lệ khán giả còn xem. Trục giây bên dưới khớp độ dài video.`;
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
    : " Ba thẻ dưới tóm tắt hình mở, kiểu hook và chỗ lời/kết nối sớm — không phải transcript đầy đủ.";

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
    "Các chỉ số so với kênh, giọng điệu và đối tượng nhắm giúp đặt video trong bối cảnh sáng tạo — không chỉ nhìn view tuyệt đối.",
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
      hit: "Dòng thời gian · Cấu trúc video",
      average: "Dòng thời gian · Cấu trúc video",
      flop: "Dòng thời gian · Cấu trúc video",
      unknown: "Dòng thời gian · Cấu trúc video",
    },
    hook_analysis: {
      hit: "Giải mã hook · 3 giây đầu vì sao người xem dừng",
      average: "Giải mã hook · 3 giây đầu",
      flop: "Giải mã hook · 3 giây đầu dễ mất người xem",
      unknown: "Giải mã hook",
    },
    metadata: {
      hit: "Bối cảnh phân tích",
      average: "Bối cảnh phân tích",
      flop: "Bối cảnh phân tích",
      unknown: "Bối cảnh phân tích",
    },
  };
  const tier = performanceTier in defaults.script_structure ? performanceTier : "unknown";
  const fallback = defaults[sectionId]?.[tier] ?? sectionId;
  return formatDiagnosisSectionTitle(fallback);
}

export function shouldShowScriptStructureBlock(report: VideoReportPayload): boolean {
  return (report.segments?.length ?? 0) > 0;
}

export function shouldShowHookAnalysisBlock(report: VideoReportPayload): boolean {
  return (report.hook_phases?.length ?? 0) > 0 || (report.hook_timeline?.length ?? 0) > 0;
}

export function shouldShowMetadataBlock(
  meta: VideoAnalyzeMeta,
  enrichment?: VideoEnrichment | null,
): boolean {
  return hasContextStripContent(meta, enrichment);
}
