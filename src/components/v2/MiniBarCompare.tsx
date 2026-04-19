export type MiniBarCompareProps = {
  yoursSec: number;
  corpusSec: number;
  winnerSec: number;
};

function Bar({
  label,
  value,
  max,
  colorVar,
  bold,
}: {
  label: string;
  value: number;
  max: number;
  colorVar: string;
  bold?: boolean;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="gv-mono w-16 shrink-0 text-[10px] text-[color:var(--gv-ink-4)]">{label}</span>
      <div className="relative h-3 flex-1 bg-[color:var(--gv-canvas-2)]">
        <div className="absolute inset-y-0 left-0" style={{ width: `${pct}%`, backgroundColor: `var(${colorVar})` }} />
      </div>
      <span
        className="gv-mono w-8 shrink-0 text-right text-[10px]"
        style={{ color: `var(${colorVar})`, fontWeight: bold ? 600 : 400 }}
      >
        {value.toFixed(1)}s
      </span>
    </div>
  );
}

export function MiniBarCompare({ yoursSec, corpusSec, winnerSec }: MiniBarCompareProps) {
  const max = Math.max(yoursSec, corpusSec, winnerSec) * 1.1;
  return (
    <div className="flex flex-col gap-1.5">
      <Bar label="Của bạn" value={yoursSec} max={max} colorVar="--gv-accent" bold />
      <Bar label="Ngách TB" value={corpusSec} max={max} colorVar="--gv-ink-3" />
      <Bar label="Winner" value={winnerSec} max={max} colorVar="--gv-chart-benchmark" />
    </div>
  );
}
