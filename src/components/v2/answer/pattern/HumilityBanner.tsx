/** Thin-sample humility copy (Phase C.2.3) — always shown when `sample_size` &lt; 30. */
export function HumilityBanner() {
  return (
    <div
      className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-[18px] py-4 text-[14px] leading-[1.55] text-[color:var(--gv-ink-2)]"
      role="note"
    >
      Mẫu dưới 30 video trong cửa sổ — dùng để định hướng, không kết luận toàn bộ ngách. Ưu tiên
      thử nghiệm nhỏ trước khi scale.
    </div>
  );
}
