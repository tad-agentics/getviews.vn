import { memo, useMemo } from "react";
import { useHomeTicker, type TickerItem } from "@/hooks/useHomeTicker";

/**
 * Ink-bar marquee under the TopBar — dark strip, colour-coded bucket tags.
 * Data: GET /home/ticker only (7-day corpus buckets). No Figma mock copy in prod.
 */

const BUCKET_TONE: Record<TickerItem["bucket"], string> = {
  breakout: "text-[color:var(--gv-accent)]",
  hook_mới: "text-[color:var(--gv-accent-2)]",
  cảnh_báo: "text-[color:var(--gv-neg)]",
  âm_thanh: "text-[color:var(--gv-lime)]",
};

/** Spec: hide marquee when fewer than 3 distinct signals (system-design § /home/ticker). */
export const MIN_TICKER_UNIQUE_ITEMS = 3;

/** Dedupe by bucket + target before looping the CSS marquee. */
export function uniqueTickerItems(items: TickerItem[]): TickerItem[] {
  const seen = new Set<string>();
  const out: TickerItem[] = [];
  for (const it of items) {
    const key = `${it.bucket}:${it.target_id ?? it.headline_vi}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(it);
  }
  return out;
}

/** Duplicate once for seamless CSS marquee loop (only when enough unique rows). */
export function tickerMarqueeRows(items: TickerItem[]): TickerItem[] {
  const unique = uniqueTickerItems(items);
  if (unique.length < MIN_TICKER_UNIQUE_ITEMS) return [];
  return [...unique, ...unique];
}

export const TickerMarquee = memo(function TickerMarquee({
  viewNicheId = null,
}: {
  /** Matches ``NichePicker`` / Home headline — same niche as gợi ý & pulse. */
  viewNicheId?: number | null;
} = {}) {
  const { data: items, isPending, isError, isFetched } = useHomeTicker(true, viewNicheId);

  const rowItems = useMemo(
    () => (items && items.length > 0 ? tickerMarqueeRows(items) : []),
    [items],
  );

  // Avoid flashing mock while the query is in flight; hide when API empty/errors.
  if (isPending || !isFetched || isError || rowItems.length === 0) {
    return null;
  }

  return (
    <section
      aria-label="Dòng tin tuần này"
      className="relative overflow-hidden border-b border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
    >
      <div className="animate-scroll-ticker flex min-w-[200%] items-center gap-12 whitespace-nowrap py-2">
        {rowItems.map((it, idx) => (
          <span
            key={`${it.bucket}-${it.target_id ?? idx}-${idx}`}
            className="gv-mono inline-flex items-center gap-2.5 text-[11px] leading-normal"
          >
            <span className={"font-semibold " + BUCKET_TONE[it.bucket]}>{it.label_vi}</span>
            <span className="font-medium text-[color:var(--gv-canvas)] opacity-[0.85]">
              {it.headline_vi}
            </span>
            <span aria-hidden="true" className="text-[color:var(--gv-canvas)] opacity-40">
              ·
            </span>
          </span>
        ))}
      </div>
    </section>
  );
});
