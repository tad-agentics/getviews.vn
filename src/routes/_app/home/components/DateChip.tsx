import { memo } from "react";

const WEEKDAY_VI: Record<number, string> = {
  0: "Chủ Nhật",
  1: "Thứ Hai",
  2: "Thứ Ba",
  3: "Thứ Tư",
  4: "Thứ Năm",
  5: "Thứ Sáu",
  6: "Thứ Bảy",
};

/** Mono chip: "THỨ BẢY · 18.04". Computed once per render. */
export const DateChip = memo(function DateChip() {
  const now = new Date();
  const label = `${WEEKDAY_VI[now.getDay()]} · ${String(now.getDate()).padStart(2, "0")}.${String(now.getMonth() + 1).padStart(2, "0")}`;
  return (
    <span className="inline-flex items-center rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-mono text-[11px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-3)]">
      {label}
    </span>
  );
});
