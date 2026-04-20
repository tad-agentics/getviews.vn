import type { PatternCellPayloadData } from "@/lib/api-types";

type ChartData = Record<string, unknown>;

function normBars(raw: unknown): number[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((x) => (typeof x === "number" && Number.isFinite(x) ? Math.max(0, x) : 0));
}

function BarRow({ bars, accent }: { bars: number[]; accent?: boolean }) {
  const max = Math.max(...bars, 1);
  return (
    <div className="flex h-[52px] items-end gap-1">
      {bars.map((b, i) => (
        <div
          key={i}
          className="min-w-0 flex-1 rounded-t bg-[color:var(--gv-canvas-2)]"
          style={{
            height: `${Math.max(8, (b / max) * 100)}%`,
            backgroundColor: accent && i === bars.length - 1 ? "var(--gv-accent)" : undefined,
          }}
        />
      ))}
    </div>
  );
}

function SoundMixBar({ primaryPct }: { primaryPct: number }) {
  const p = Math.min(100, Math.max(0, primaryPct));
  const q = 100 - p;
  return (
    <div className="flex h-[52px] w-full overflow-hidden rounded border border-[color:var(--gv-rule)]">
      <div
        className="h-full bg-[color:var(--gv-accent-soft)]"
        style={{ width: `${p}%` }}
        title={`Gốc ${p.toFixed(0)}%`}
      />
      <div className="h-full flex-1 bg-[color:var(--gv-canvas-2)]" title={`Trend ${q.toFixed(0)}%`} />
    </div>
  );
}

function HookTimingTrack({ marker }: { marker: number }) {
  const m = Math.min(1, Math.max(0, marker));
  return (
    <div className="relative h-[52px] rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2">
      <div className="absolute bottom-2 left-2 right-2 top-2 border-b border-[color:var(--gv-rule)]" />
      <div
        className="absolute bottom-2 h-3 w-3 -translate-x-1/2 rounded-full border-2 border-[color:var(--gv-accent)] bg-[color:var(--gv-paper)]"
        style={{ left: `${m * 100}%` }}
        title={`~${(m * 1.2).toFixed(2)}s`}
      />
    </div>
  );
}

/** Renders §J `chart_kind` + optional `chart_data`; falls back to kind label. */
export function PatternMiniChart({ cell }: { cell: PatternCellPayloadData }) {
  const d = (cell.chart_data ?? {}) as ChartData;
  const bars = normBars(d.bars);
  if (bars.length > 0) {
    return (
      <div className="min-h-[60px] rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-2">
        <BarRow bars={bars} accent={cell.chart_kind === "cta_bars"} />
      </div>
    );
  }
  if (cell.chart_kind === "sound_mix" && typeof d.primary_pct === "number") {
    return (
      <div className="min-h-[60px] rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-2">
        <SoundMixBar primaryPct={d.primary_pct} />
        <p className="gv-mono mt-1 text-[9px] text-[color:var(--gv-ink-4)]">Gốc · Trend</p>
      </div>
    );
  }
  if (cell.chart_kind === "hook_timing" && typeof d.marker === "number") {
    return (
      <div className="min-h-[60px] rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-2">
        <HookTimingTrack marker={d.marker} />
      </div>
    );
  }
  /* Fallback: abstract sparkline using gv tokens */
  const seed = cell.finding.length + cell.chart_kind.length;
  const fake = [20 + (seed % 30), 35 + (seed % 25), 50 + (seed % 20), 40 + (seed % 15)];
  return (
    <div className="min-h-[60px] rounded border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-2">
      <BarRow bars={fake} />
      <p className="gv-mono mt-1 text-center text-[9px] text-[color:var(--gv-ink-4)]">{cell.chart_kind}</p>
    </div>
  );
}
