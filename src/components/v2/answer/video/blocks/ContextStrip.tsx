import type { VideoAnalyzeMeta, VideoEnrichment } from "@/lib/api-types";
import { styleTagVi, videoToneVi } from "@/lib/constants/enum-labels-vi";
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
  introProse,
  variant = "standalone",
}: {
  meta: VideoAnalyzeMeta;
  enrichment?: VideoEnrichment | null;
  /** Diễn giải đi kèm các chỉ số bối cảnh — luôn nằm trong cùng khối với strip. */
  introProse?: string | null;
  /** ``embed`` — parent section already shows the block title. */
  variant?: "standalone" | "embed";
}) {
  const ratio = meta.target_vs_creator_median ?? null;
  const median = meta.creator_median_views ?? null;
  const hasRatio = ratio != null && median != null && median > 0;
  const audience = enrichment?.target_audience?.trim() ?? "";
  const painPoints = (enrichment?.pain_points ?? []).filter((p) => p.trim().length > 0);
  const styleTags = (enrichment?.style_tags ?? []).filter((s) => s.trim().length > 0);
  const promotion = enrichment?.promotion_type ?? "organic";
  const showPromotion = promotion !== "organic";
  const toneLabel = enrichment?.tone ? videoToneVi(enrichment.tone) : "";

  const intro = introProse?.trim() ?? "";
  if (
    !intro &&
    !hasRatio &&
    !audience &&
    painPoints.length === 0 &&
    styleTags.length === 0 &&
    !showPromotion &&
    !toneLabel
  ) {
    return null;
  }

  return (
    <section
      aria-label="Chỉ số bối cảnh video"
      className={
        variant === "embed"
          ? "rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4"
          : "mt-6 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4"
      }
    >
      {variant === "standalone" ? (
        <p className="gv-mono mb-3 text-[11px] gv-kicker tracking-[0.18em] text-[color:var(--gv-ink-3)]">
          CHỈ SỐ BỐI CẢNH
        </p>
      ) : null}
      {intro ? (
        <p className="mb-3 text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]">
          {intro}
        </p>
      ) : null}
      <div className="grid grid-cols-1 gap-3 min-[700px]:grid-cols-2">
        {hasRatio ? (
          <div>
            <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-wider text-[color:var(--gv-ink-3)]">
              SO VỚI KÊNH BẠN
            </p>
            <p className="gv-mono m-0 text-[17px] font-semibold text-[color:var(--gv-ink)]">
              {ratio!.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}× kênh trung bình
            </p>
            <p className="m-0 text-xs text-[color:var(--gv-ink-3)]">
              Trung vị {formatViews(median!)} view trên các bài gần đây
            </p>
          </div>
        ) : null}
        {toneLabel ? (
          <div>
            <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-wider text-[color:var(--gv-ink-3)]">
              GIỌNG ĐIỆU
            </p>
            <p className="m-0 text-sm leading-relaxed text-[color:var(--gv-ink)]">{toneLabel}</p>
          </div>
        ) : null}
        {audience ? (
          <div>
            <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-wider text-[color:var(--gv-ink-3)]">
              NHẮM TỚI
            </p>
            <p className="m-0 text-sm leading-relaxed text-[color:var(--gv-ink)]">
              {audience}
            </p>
          </div>
        ) : null}
        {painPoints.length > 0 ? (
          <div>
            <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-wider text-[color:var(--gv-ink-3)]">
              ĐIỂM NHẠY KHAI THÁC
            </p>
            <ul className="m-0 list-disc pl-4 text-xs leading-relaxed text-[color:var(--gv-ink-2)]">
              {painPoints.slice(0, 3).map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {styleTags.length > 0 || showPromotion ? (
          <div>
            <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-wider text-[color:var(--gv-ink-3)]">
              KIỂU SẢN XUẤT
            </p>
            <div className="flex flex-wrap gap-1.5">
              {showPromotion ? (
                <span className="rounded-full border border-[color:var(--gv-accent)] bg-[color:var(--gv-canvas)] px-2 py-0.5 text-[11px] text-[color:var(--gv-accent)]">
                  {PROMOTION_LABEL_VI[promotion]}
                </span>
              ) : null}
              {/* Live audit 2026-06-12: raw enums (product_showcase, lifestyle_b_roll,
                  text_overlay_heavy) leaked into the chips — map to Vietnamese,
                  humanize unmapped codes. */}
              {styleTags.slice(0, 5).map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-2 py-0.5 text-[11px] text-[color:var(--gv-ink-2)]"
                >
                  {styleTagVi(tag)}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
