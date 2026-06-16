import { memo } from "react";

/**
 * D4b — Kho Douyin hero block.
 *
 * Dark ink card with corpus stats: video count, hook overlay coverage,
 * and saved-set size.
 */

export type DouyinHeroProps = {
  totalInPool: number;
  /** Rows with hook overlay text (sub_vi, title_vi, or title_zh). */
  subViCount: number;
  savedCount: number;
  scopeLabel: string | null;
};

export const DouyinHero = memo(function DouyinHero({
  totalInPool,
  subViCount,
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
        TRUNG QUỐC · XU HƯỚNG DOUYIN · HOOK VIỆT HÓA · CẬP NHẬT MỖI 24H
      </p>

      {/* H1 — accent highlight on "không cần VPN". */}
      <h1
        className="gv-tight m-0 mb-4 max-w-[720px] text-[42px] font-medium leading-[1.05] tracking-[-0.025em] text-[color:var(--gv-canvas)]"
        style={{ fontFamily: "var(--gv-font-display)" }}
      >
        Xu hướng Douyin{" "}
        <span className="text-[color:var(--gv-accent)]">không cần VPN</span> —
        hook được Việt hoá, xem trước và tự đánh giá chuyển thể.
      </h1>

      <p className="m-0 mb-5 max-w-[640px] text-[14px] leading-[1.5] text-[color:var(--gv-ink-3)]">
        {totalInPool} video tuyển chọn từ Douyin · Hook Việt hoá hiển thị sẵn · Lưu video hay vào kho cá nhân · Bạn tự quyết định format nào phù hợp kênh VN.
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
          label="Hook Việt hoá"
          value={subViCount}
          sub="trên thẻ video"
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
