import { memo, useMemo } from "react";
import { useHomeTicker, type TickerItem } from "@/hooks/useHomeTicker";

/**
 * Ink-bar marquee under the TopBar — dark strip, colour-coded bucket tags,
 * headlines scroll left on a 40s loop (`animate-scroll-ticker` in app.css).
 *
 * Uses GET /home/ticker when it returns **≥3** rows; otherwise falls back to
 * the same demo lines as `screens/home.jsx` in the UIUX pack so the strip
 * still matches the design in dev or thin data weeks.
 */

/** UIUX reference `Ticker()` mock — kept in API shape for fallback only. */
const FALLBACK_ITEMS: TickerItem[] = [
  {
    bucket: "breakout",
    label_vi: "BREAKOUT",
    headline_vi: '@aifreelance — "5 app AI mà chưa ai nói" · 234K view trong 18h',
    target_kind: "none",
    target_id: null,
  },
  {
    bucket: "hook_mới",
    label_vi: "HOOK MỚI",
    headline_vi: '"Khi bạn ___" tăng 248% sử dụng tuần này',
    target_kind: "none",
    target_id: null,
  },
  {
    bucket: "cảnh_báo",
    label_vi: "CẢNH BÁO",
    headline_vi: "Format unboxing dài >60s đang giảm 18% reach trong Tech",
    target_kind: "none",
    target_id: null,
  },
  {
    bucket: "kol_nổi",
    label_vi: "KOL NỔI",
    headline_vi: "@minhtuan.dev tăng 34% follower trong 7 ngày",
    target_kind: "none",
    target_id: null,
  },
  {
    bucket: "âm_thanh",
    label_vi: "ÂM THANH",
    headline_vi: 'Sound "Lo-fi typewriter" đang được gắn vào 1.2K video Edu',
    target_kind: "none",
    target_id: null,
  },
];

const BUCKET_TONE: Record<TickerItem["bucket"], string> = {
  breakout:   "text-[color:var(--gv-accent)]",
  hook_mới:   "text-[color:var(--gv-accent-2)]",
  cảnh_báo:   "text-[color:var(--gv-neg)]",
  kol_nổi:    "text-[color:var(--gv-pos)]",
  âm_thanh:   "text-[color:var(--gv-lime)]",
};

export const TickerMarquee = memo(function TickerMarquee() {
  const { data: items = [] } = useHomeTicker();

  const rowItems = useMemo(() => {
    const list = items.length >= 3 ? items : FALLBACK_ITEMS;
    return [...list, ...list];
  }, [items]);

  return (
    <section
      aria-label="Dòng tin tuần này"
      className="relative overflow-hidden border-b border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
    >
      {/* gap-[48px] matches UIUX `.marquee-track`; py-2 = 8px like screens/home.jsx Ticker */}
      <div className="animate-scroll-ticker flex min-w-[200%] items-center gap-12 whitespace-nowrap py-2">
        {rowItems.map((it, idx) => (
          <span
            key={`${it.bucket}-${it.target_id ?? idx}-${idx}`}
            className="gv-mono inline-flex items-center gap-2.5 text-[11px] leading-normal"
          >
            <span className={"font-semibold " + BUCKET_TONE[it.bucket]}>{it.label_vi}</span>
            <span className="font-medium text-[color:var(--gv-canvas)] opacity-[0.85]">{it.headline_vi}</span>
            <span aria-hidden="true" className="text-[color:var(--gv-canvas)] opacity-40">
              ·
            </span>
          </span>
        ))}
      </div>
    </section>
  );
});
