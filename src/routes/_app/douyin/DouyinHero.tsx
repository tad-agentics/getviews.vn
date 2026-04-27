import { memo } from "react";

/**
 * D4b (2026-06-04) — Kho Douyin hero block.
 *
 * Per design pack ``screens/douyin.jsx`` lines 530-564: dark ink card,
 * faint 抖音 watermark in the top-right, accent-highlighted serif H1,
 * 3 hero stats grid (VIDEO TRONG KHO / DỄ ADAPT (XANH) / ĐÃ LƯU).
 *
 * Stats are passed in by the parent screen — the saved count comes
 * from ``useDouyinSavedSet``, the corpus + green counts come from
 * filtering ``useDouyinFeed`` data.
 */

export type DouyinHeroProps = {
  totalInPool: number;
  greenCount: number;
  savedCount: number;
  /** When set, the niche-filter chip strip is active so the hero
   *  ``sub`` reads "ngách <label>" instead of "tất cả ngách". */
  scopeLabel: string | null;
};

export const DouyinHero = memo(function DouyinHero({
  totalInPool,
  greenCount,
  savedCount,
  scopeLabel,
}: DouyinHeroProps) {
  return (
    <section className="relative mb-6 overflow-hidden rounded-xl bg-[color:var(--gv-ink)] px-9 py-7 text-[color:var(--gv-canvas)]">
      {/* Decorative — faint Chinese characters background. Positioned
          top-right so it doesn't fight the H1. */}
      <span
        aria-hidden
        className="pointer-events-none absolute right-5 top-3 select-none text-[130px] font-extrabold leading-none tracking-[-0.04em]"
        style={{
          color: "color-mix(in srgb, var(--gv-accent) 8%, transparent)",
        }}
      >
        抖音
      </span>

      {/* Kicker */}
      <p className="gv-mono mb-2.5 text-[10px] uppercase tracking-[0.06em] text-[color:var(--gv-accent)]">
        🇨🇳 Kho Douyin · Đà Việt hoá · Cập nhật mỗi 24h
      </p>

      {/* H1 — accent highlight on "không cần VPN". */}
      <h1
        className="gv-tight m-0 mb-4 max-w-[720px] text-[44px] font-medium leading-[1.05] tracking-[-0.025em] text-[color:var(--gv-canvas)]"
        style={{ fontFamily: "var(--gv-font-display)" }}
      >
        Trend Douyin{" "}
        <span className="text-[color:var(--gv-accent)]">không cần VPN</span> —
        đã sub VN, đã chấm khả năng adapt.
      </h1>

      {/* Caption */}
      <p className="m-0 mb-5 max-w-[640px] text-[14px] leading-[1.5] text-[color:var(--gv-ink-3)]">
        {totalInPool} video tuyển chọn từ Douyin · phụ đề tiếng Việt cứng · note
        văn hoá · gắn cờ Xanh / Vàng / Đỏ theo khả năng đem về VN.
      </p>

      {/* Stats grid — 3 columns separated by a top border. */}
      <div className="grid grid-cols-3 gap-9 border-t border-[color:color-mix(in_srgb,var(--gv-canvas)_18%,transparent)] pt-4">
        <HeroNum
          label="Video trong kho"
          value={totalInPool}
          sub={scopeLabel ? `ngách ${scopeLabel}` : "tất cả ngách"}
        />
        <HeroNum
          label="Dễ adapt (xanh)"
          value={greenCount}
          sub="dịch thẳng được"
        />
        <HeroNum
          label="Đã lưu"
          value={savedCount}
          sub="kho cá nhân"
        />
      </div>
    </section>
  );
});

function HeroNum({
  label,
  value,
  sub,
}: {
  label: string;
  value: number;
  sub: string;
}) {
  return (
    <div>
      <p className="gv-mono mb-1.5 text-[9px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-4)]">
        {label}
      </p>
      <p
        className="gv-tight m-0 text-[30px] leading-none text-[color:var(--gv-canvas)]"
        style={{ fontFamily: "var(--gv-font-display)" }}
      >
        {value}
      </p>
      <p className="gv-mono mt-1.5 text-[10px] text-[color:var(--gv-ink-3)]">
        {sub}
      </p>
    </div>
  );
}
