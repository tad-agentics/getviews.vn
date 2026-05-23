import type { VideoAnalyzeMeta, VideoEnrichment } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

const PROMOTION_LABEL_VI: Record<NonNullable<VideoEnrichment["promotion_type"]>, string> = {
  organic: "Tự sản xuất",
  brand_deal: "Đặt hàng nhãn",
  affiliate: "Affiliate",
  self_promotion: "Tự quảng bá",
};

export function ContextStrip({
  meta,
  enrichment,
}: {
  meta: VideoAnalyzeMeta;
  enrichment?: VideoEnrichment | null;
}) {
  const ratio = meta.target_vs_creator_median ?? null;
  const median = meta.creator_median_views ?? null;
  const hasRatio = ratio != null && median != null && median > 0;
  const audience = enrichment?.target_audience?.trim() ?? "";
  const painPoints = (enrichment?.pain_points ?? []).filter((p) => p.trim().length > 0);
  const styleTags = (enrichment?.style_tags ?? []).filter((s) => s.trim().length > 0);
  const promotion = enrichment?.promotion_type ?? "organic";
  const showPromotion = promotion !== "organic";

  if (!hasRatio && !audience && painPoints.length === 0 && styleTags.length === 0 && !showPromotion) {
    return null;
  }

  return (
    <section
      aria-label="Bối cảnh phân tích"
      className="mt-6 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4"
    >
      <p className="gv-mono mb-3 text-[10px] uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
        BỐI CẢNH PHÂN TÍCH
      </p>
      <div className="grid grid-cols-1 gap-3 min-[700px]:grid-cols-2">
        {hasRatio ? (
          <div>
            <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              SO VỚI KÊNH BẠN
            </p>
            <p className="gv-mono m-0 text-[18px] font-semibold text-[color:var(--gv-ink)]">
              {ratio!.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}× kênh trung bình
            </p>
            <p className="m-0 text-[11.5px] text-[color:var(--gv-ink-3)]">
              Trung vị {formatViews(median!)} view trên các bài gần đây
            </p>
          </div>
        ) : null}
        {audience ? (
          <div>
            <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              NHẮM TỚI
            </p>
            <p className="m-0 text-[13px] leading-relaxed text-[color:var(--gv-ink)]">
              {audience}
            </p>
          </div>
        ) : null}
        {painPoints.length > 0 ? (
          <div>
            <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              ĐIỂM NHẠY KHAI THÁC
            </p>
            <ul className="m-0 list-disc pl-4 text-[12.5px] leading-relaxed text-[color:var(--gv-ink-2)]">
              {painPoints.slice(0, 3).map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {styleTags.length > 0 || showPromotion ? (
          <div>
            <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              KIỂU SẢN XUẤT
            </p>
            <div className="flex flex-wrap gap-1.5">
              {showPromotion ? (
                <span className="rounded-full border border-[color:var(--gv-accent)] bg-[color:var(--gv-canvas)] px-2 py-0.5 text-[11px] text-[color:var(--gv-accent)]">
                  {PROMOTION_LABEL_VI[promotion]}
                </span>
              ) : null}
              {styleTags.slice(0, 5).map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-2 py-0.5 text-[11px] text-[color:var(--gv-ink-2)]"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
