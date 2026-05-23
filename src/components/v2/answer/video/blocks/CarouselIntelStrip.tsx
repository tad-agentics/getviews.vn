import type { CarouselIntelPayload, CarouselSlideIntel } from "@/lib/api-types";
import { carouselLabel } from "@/lib/carouselLabels";

function slidePreview(slide: CarouselSlideIntel): string {
  const text = slide.text_preview?.trim();
  if (text) return text.length > 48 ? `${text.slice(0, 48)}…` : text;
  if (slide.has_product) return "Sản phẩm";
  if (slide.has_face) return "Có mặt người";
  return "Slide trống / chỉ hình";
}

/** §5.4 — carousel slide intel from ``CarouselAnalysis`` extraction. */
export function CarouselIntelStrip({ intel }: { intel: CarouselIntelPayload | null | undefined }) {
  const slides = intel?.slides ?? [];
  if (!intel || slides.length === 0) return null;

  const metaRows: { label: string; value: string }[] = [];
  if (intel.content_arc) {
    metaRows.push({ label: "Cấu trúc", value: carouselLabel.contentArc(intel.content_arc) });
  }
  if (intel.swipe_trigger_type) {
    metaRows.push({
      label: "Cơ chế lướt",
      value: carouselLabel.swipeTrigger(intel.swipe_trigger_type),
    });
  }
  if (intel.visual_consistency) {
    metaRows.push({
      label: "Visual",
      value: carouselLabel.visualConsistency(intel.visual_consistency),
    });
  }
  if (intel.estimated_read_time_seconds != null) {
    metaRows.push({
      label: "Thời gian đọc",
      value: `${intel.estimated_read_time_seconds}s`,
    });
  }
  if (intel.has_numbered_hook != null) {
    metaRows.push({
      label: "Hook số",
      value: intel.has_numbered_hook ? "Có" : "Không",
    });
  }
  if (intel.slide_pacing_score != null) {
    metaRows.push({
      label: "Nhịp slide",
      value: `${Math.round(intel.slide_pacing_score * 100)}%`,
    });
  }

  return (
    <section
      className="mb-4 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4"
      aria-label="Phân tích carousel theo slide"
    >
      <p className="gv-kicker mb-2 text-[color:var(--gv-ink-3)]">
        Logic lướt · {slides.length} slide
      </p>
      {metaRows.length > 0 ? (
        <div className="mb-3 flex flex-wrap gap-2">
          {metaRows.map((row) => (
            <span
              key={row.label}
              className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2 py-1 text-xs text-[color:var(--gv-ink-2)]"
            >
              <span className="gv-kicker text-[color:var(--gv-ink-4)]">{row.label}: </span>
              {row.value}
            </span>
          ))}
        </div>
      ) : null}
      <ol className="m-0 flex list-none flex-col gap-2 p-0">
        {slides.map((slide) => (
          <li
            key={slide.index}
            className="flex items-start gap-3 rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2"
          >
            <span className="gv-mono shrink-0 text-[11px] font-semibold text-[color:var(--gv-accent)]">
              {slide.index + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm leading-snug text-[color:var(--gv-ink)]">{slidePreview(slide)}</p>
              <p className="mt-0.5 text-xs text-[color:var(--gv-ink-3)]">
                {slide.swipe_anchor
                  ? carouselLabel.swipeAnchor(slide.swipe_anchor)
                  : "—"}
                {slide.layout ? ` · ${carouselLabel.layout(slide.layout)}` : ""}
                {slide.word_count != null ? ` · ${slide.word_count} chữ` : ""}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
