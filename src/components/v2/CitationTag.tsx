export type CitationTagProps = {
  sampleSize: number;
  nicheLabel: string;
  windowDays?: number;
};

export function CitationTag({ sampleSize, nicheLabel, windowDays = 7 }: CitationTagProps) {
  const label = nicheLabel.trim() || "ngách của bạn";
  return (
    <div className="gv-mono rounded-[var(--gv-radius-sm)] border border-dashed border-[color:var(--gv-rule)] px-3 py-2.5 text-[10px] leading-snug text-[color:var(--gv-ink-4)]">
      ✻ Gợi ý dựa trên{" "}
      <span className="font-medium text-[color:var(--gv-ink-2)]">{sampleSize} video</span> trong ngách{" "}
      {label} · {windowDays} ngày gần nhất
    </div>
  );
}
