export type DurationInsightProps = {
  durationSec: number;
};

/** Four-tier copy from ``script.jsx`` DurationInsight. */
export function DurationInsight({ durationSec }: DurationInsightProps) {
  let toneClass: string;

  if (durationSec < 22) {
    return (
      <p className="gv-mono mt-2 text-[11px] leading-[1.45] text-[color:var(--gv-ink-4)]">
        Ngắn — phù hợp hook thuần, ít dữ liệu
      </p>
    );
  }

  if (durationSec <= 40) {
    return (
      <p className="gv-mono mt-2 text-[11px] leading-[1.45] text-[color:var(--gv-chart-benchmark)]">
        <span className="gv-kicker gv-kicker--dot gv-kicker--pos">Vùng vàng</span>
        {" — 71% video thắng nằm đây"}
      </p>
    );
  }

  if (durationSec <= 60) {
    return (
      <p className="gv-mono mt-2 text-[11px] leading-[1.45] text-[color:var(--gv-ink-4)]">
        Dài hơn TB — cần payoff rõ lúc 40s
      </p>
    );
  }

  return (
    <p className="gv-mono mt-2 text-[11px] leading-[1.45] text-[color:var(--gv-accent-deep)]">
      <span className="gv-kicker">Cảnh báo</span>
      {" — > 60s retention giảm 34%"}
    </p>
  );
}
