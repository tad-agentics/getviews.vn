export type DurationInsightProps = {
  durationSec: number;
};

/** Four-tier copy from ``script.jsx`` DurationInsight. */
export function DurationInsight({ durationSec }: DurationInsightProps) {
  let msg: string;
  let toneClass: string;
  if (durationSec < 22) {
    msg = "Ngắn — phù hợp hook thuần, ít dữ liệu";
    toneClass = "text-[color:var(--gv-ink-4)]";
  } else if (durationSec <= 40) {
    msg = "★ Vùng vàng — 71% video thắng nằm đây";
    toneClass = "text-[color:var(--gv-pos-deep)]";
  } else if (durationSec <= 60) {
    msg = "Dài hơn TB — cần payoff rõ lúc 40s";
    toneClass = "text-[color:var(--gv-ink-4)]";
  } else {
    msg = "⚠ > 60s retention giảm 34%";
    toneClass = "text-[color:var(--gv-accent-deep)]";
  }

  return (
    <p className={`gv-mono mt-2 text-[11px] leading-[1.45] ${toneClass}`.trim()}>{msg}</p>
  );
}
