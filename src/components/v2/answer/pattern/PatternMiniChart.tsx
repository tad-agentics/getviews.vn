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

/**
 * A2 — CTA bars 2-row horizontal layout (per design pack
 * ``screens/answer.jsx`` lines 615-632). Shows up to N labeled rows where
 * each row is a label + filled bar + multiplier value; the first row uses
 * accent fill (the "winning" CTA), subsequent rows render as a thin gray
 * track with proportional fill (the baselines being compared against).
 *
 * The widest multiplier sets the scale — every other bar widthi is
 * ``multiplier / max * 100``. Falls back gracefully to a single 100%
 * accent bar if only one row is provided.
 */
type CtaRow = { label: string; multiplier: number };

function CtaBars2Row({ rows }: { rows: CtaRow[] }) {
  const max = Math.max(...rows.map((r) => r.multiplier), 1);
  return (
    <div className="flex flex-col gap-1.5">
      {rows.map((r, i) => {
        const widthPct = Math.min(100, Math.max(8, (r.multiplier / max) * 100));
        const isPrimary = i === 0;
        return (
          <div key={r.label} className="flex items-center gap-2">
            <span
              className="gv-mono w-[64px] shrink-0 text-[10px] text-[color:var(--gv-ink-3)]"
              title={r.label}
            >
              {r.label}
            </span>
            {isPrimary ? (
              <div
                className="h-2.5 rounded-sm bg-[color:var(--gv-accent)]"
                style={{ width: `${widthPct}%` }}
              />
            ) : (
              <div className="h-2.5 flex-1 overflow-hidden rounded-sm bg-[color:var(--gv-canvas-2)]">
                <div
                  className="h-full bg-[color:var(--gv-ink-4)]"
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            )}
            <span className="gv-mono w-[34px] shrink-0 text-right text-[10px] text-[color:var(--gv-ink-2)] tabular-nums">
              {r.multiplier.toFixed(1)}×
            </span>
          </div>
        );
      })}
    </div>
  );
}

function normCtaRows(raw: unknown): CtaRow[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((row): CtaRow | null => {
      if (!row || typeof row !== "object") return null;
      const r = row as { label?: unknown; multiplier?: unknown };
      const label = typeof r.label === "string" ? r.label.trim() : "";
      const mult =
        typeof r.multiplier === "number" && Number.isFinite(r.multiplier)
          ? r.multiplier
          : null;
      if (!label || mult == null || mult <= 0) return null;
      return { label, multiplier: mult };
    })
    .filter((row): row is CtaRow => row !== null);
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
  // A2 — design's CtaBars (HỎI NGƯỢC 3.4× / "FOLLOW" 1.0×). Prefer the
  // labeled 2-row horizontal layout when the BE emits ``rows`` shape;
  // legacy ``bars`` (vertical) flow stays as fallback for older
  // payloads that haven't switched yet.
  if (cell.chart_kind === "cta_bars") {
    const rows = normCtaRows(d.rows);
    if (rows.length > 0) {
      return (
        <div className="min-h-[60px] rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-2">
          <CtaBars2Row rows={rows} />
        </div>
      );
    }
  }
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
