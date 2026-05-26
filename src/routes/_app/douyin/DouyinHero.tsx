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
        className="pointer-events-none absolute right-5 top-3 select-none font-extrabold leading-none tracking-[-0.04em]"
        style={{
          fontSize: "7.5rem",
          color: "color-mix(in srgb, var(--gv-accent) 8%, transparent)",
        }}
      >
        抖音
      </span>

      {/* Kicker */}
      <p className="gv-mono mb-2.5 text-[11px] gv-kicker tracking-[0.06em] text-[color:var(--gv-accent)]">
        TRUNG QUỐC · XU HƯỚNG DOUYIN · DỊCH NGHĨA VIỆT HÓA · CẬP NHẬT MỖI 24H
      </p>

      {/* H1 — accent highlight on "không cần VPN". */}
      <h1
        className="gv-tight m-0 mb-4 max-w-[720px] text-[42px] font-medium leading-[1.05] tracking-[-0.025em] text-[color:var(--gv-canvas)]"
        style={{ fontFamily: "var(--gv-font-display)" }}
      >
        Xu hướng Douyin{" "}
        <span className="text-[color:var(--gv-accent)]">không cần VPN</span> —
        sẵn phụ đề Việt hóa, đánh giá khả năng chuyển thể.
      </h1>

      {/* Caption */}
      <p className="m-0 mb-5 max-w-[640px] text-[14px] leading-[1.5] text-[color:var(--gv-ink-3)]">
        {totalInPool} video tuyển chọn từ Douyin · Phụ đề tiếng Việt hiển thị sẵn · Lưu ý văn hóa bổ ích · Đánh giá mức độ khả thi Xanh / Vàng / Đỏ khi chuyển thể về Việt Nam.
      </p>

      {/* Stats grid — 2 cols on mobile (avoid cramping at 360px),
          3 cols ≥sm. Top border separates from the caption. */}
      <div className="grid grid-cols-2 gap-5 border-t border-[color:color-mix(in_srgb,var(--gv-canvas)_18%,transparent)] pt-4 sm:grid-cols-3 sm:gap-9">
        <HeroNum
          label="Video tuyển chọn"
          value={totalInPool}
          sub={scopeLabel ? `mảng ${scopeLabel}` : "tất cả các mảng"}
        />
        <HeroNum
          label="Dễ chuyển thể (Xanh)"
          value={greenCount}
          sub="sử dụng được ngay"
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
      <p className="gv-mono mb-1.5 text-[11px] gv-kicker tracking-[0.06em] text-[color:var(--gv-ink-3)]">
        {label}
      </p>
      <p
        className="gv-tight m-0 text-[32px] leading-none text-[color:var(--gv-canvas)]"
        style={{ fontFamily: "var(--gv-font-display)" }}
      >
        {value}
      </p>
      <p className="gv-mono mt-1.5 text-[11px] text-[color:var(--gv-ink-3)]">
        {sub}
      </p>
    </div>
  );
}
