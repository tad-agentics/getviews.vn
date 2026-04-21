/**
 * Phase D.1.4 — `/channel` posting heatmap (C.8.4 carryover).
 *
 * 7 days × 8 hour buckets video-count matrix. Visual shape matches
 * `TimingHeatmap` (Phase C.4) but uses a single-hue `--gv-ink` ramp
 * instead of the accent-blue ramp — this keeps the Channel screen
 * visually distinct from the Timing report (which uses accent).
 *
 * Rendering contract:
 *   - `grid[dayIndex][hourBucket]` is a raw video count (non-negative int).
 *   - Colours normalize against `max(grid flattened)` so a channel that
 *     posts only 3–4×/week never looks washed out against a daily poster.
 *   - `grid === []` (empty outer array) → parent should not render this
 *     component; `_compute_posting_heatmap` uses the same empty-sentinel.
 */

const DAYS_VN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
const HOURS_VN = ["6–9", "9–12", "12–15", "15–18", "18–20", "20–22", "22–24", "0–3"];

/** Single-hue cell background — `--gv-ink` ramp, normalised to grid max. */
export function postingCellBackground(value: number, max: number): string {
  if (max <= 0 || value <= 0) return "var(--gv-paper)";
  const pct = value / max;
  if (pct >= 0.85) return "var(--gv-ink)";
  if (pct >= 0.6) return "var(--gv-ink-3)";
  if (pct >= 0.35) return "var(--gv-ink-4)";
  if (pct >= 0.1) return "var(--gv-rule)";
  return "var(--gv-rule-2)";
}

/** Label colour — paper on the dark bands (≥ 0.35), muted ink otherwise. */
export function postingCellLabelColor(value: number, max: number): string {
  if (max <= 0 || value <= 0) return "var(--gv-ink-4)";
  const pct = value / max;
  if (pct >= 0.6) return "var(--gv-paper)";
  if (pct >= 0.35) return "var(--gv-ink)";
  return "var(--gv-ink-3)";
}

export function PostingHeatmap({ grid, legendFooter }: { grid: number[][]; legendFooter?: string }) {
  const flat = grid.flat();
  const max = flat.length ? Math.max(...flat, 0) : 0;

  return (
    <section>
      <p className="gv-mono mb-[10px] text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-3)] font-semibold">
        Nhịp đăng · 7 ngày × 8 khung giờ
      </p>
      <div
        className="grid gap-[3px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-[10px]"
        style={{ gridTemplateColumns: "28px repeat(8, minmax(0, 1fr))" }}
      >
        <div />
        {HOURS_VN.map((h) => (
          <div
            key={h}
            className="gv-mono px-0 py-[2px] text-center text-[9px] text-[color:var(--gv-ink-4)]"
          >
            {h}
          </div>
        ))}
        {DAYS_VN.map((d, di) => (
          <Row key={d} label={d} values={grid[di] ?? []} max={max} />
        ))}
      </div>
      <div className="mt-[10px] flex items-center gap-3 text-[10px]">
        <span className="gv-mono text-[color:var(--gv-ink-4)]">Ít</span>
        {[0, 0.15, 0.4, 0.7, 1].map((pct, i) => (
          <span
            key={i}
            aria-hidden
            className="h-3 w-4 border border-[color:var(--gv-rule)]"
            style={{ backgroundColor: postingCellBackground(pct * (max || 1), max || 1) }}
          />
        ))}
        <span className="gv-mono text-[color:var(--gv-ink-4)]">Nhiều</span>
        <span className="flex-1" />
        {legendFooter ? (
          <span className="gv-mono text-[color:var(--gv-ink-4)]">{legendFooter}</span>
        ) : null}
      </div>
    </section>
  );
}

function Row({ label, values, max }: { label: string; values: number[]; max: number }) {
  return (
    <>
      <div className="gv-mono flex items-center text-[10px] font-medium text-[color:var(--gv-ink-3)]">
        {label}
      </div>
      {values.map((v, hi) => (
        <div
          key={hi}
          aria-label={`${label} · ${HOURS_VN[hi]} · ${v} video`}
          className="gv-mono flex items-center justify-center text-[10px]"
          style={{
            backgroundColor: postingCellBackground(v, max),
            color: postingCellLabelColor(v, max),
            aspectRatio: "1.6 / 1",
            fontWeight: max > 0 && v / max >= 0.6 ? 600 : 400,
          }}
        >
          {v > 0 ? v : ""}
        </div>
      ))}
    </>
  );
}
