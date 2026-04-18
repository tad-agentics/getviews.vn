import { memo } from "react";
import { useHomeTicker, type TickerItem } from "@/hooks/useHomeTicker";

/**
 * Ink-bar marquee at the top of the Home screen. Five buckets, colour-
 * coded labels, items scroll right-to-left at 40s per lap.
 *
 * Hides itself when < 3 items come back — a sparse ticker reads worse
 * than no ticker.
 */

const BUCKET_TONE: Record<TickerItem["bucket"], string> = {
  breakout:   "text-[color:var(--gv-accent)]",
  hook_mới:   "text-[color:var(--gv-accent-2)]",
  cảnh_báo:   "text-[color:var(--gv-neg)]",
  kol_nổi:    "text-[color:var(--gv-pos)]",
  âm_thanh:   "text-[color:var(--gv-lime)]",
};

export const TickerMarquee = memo(function TickerMarquee() {
  const { data: items = [] } = useHomeTicker();

  if (items.length < 3) return null;

  // Duplicate the item list so the -50% translate in the keyframe renders
  // a seamless loop (see `scroll-infinite` in app.css).
  const row = [...items, ...items];

  return (
    <section
      aria-label="Dòng tin tuần này"
      className="relative overflow-hidden border-y border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
    >
      <div className="animate-scroll-ticker flex min-w-[200%] items-center gap-10 whitespace-nowrap py-2.5">
        {row.map((it, idx) => (
          <span
            key={`${it.bucket}-${it.target_id ?? idx}-${idx}`}
            className="inline-flex items-center gap-2.5 text-[12px]"
          >
            <span
              className={
                "gv-mono gv-uc text-[10px] tracking-[0.14em] " +
                BUCKET_TONE[it.bucket]
              }
            >
              {it.label_vi}
            </span>
            <span className="font-medium text-[color:var(--gv-canvas)]">
              {it.headline_vi}
            </span>
            <span aria-hidden="true" className="text-[color:var(--gv-ink-4)]">·</span>
          </span>
        ))}
      </div>
    </section>
  );
});
