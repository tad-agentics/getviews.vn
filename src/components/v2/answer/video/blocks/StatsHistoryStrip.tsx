import type { StatsHistorySnapshot } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

const PHASE_LABEL: Record<string, string> = {
  t0: "Đăng",
  t6h: "+6h",
  t24h: "+24h",
};

function erPct(row: StatsHistorySnapshot): string {
  const v = row.views;
  if (v <= 0) return "—";
  const pct = ((row.likes + row.comments + row.shares) / v) * 100;
  return `${pct.toFixed(1)}%`;
}

/** §4.7 M4 — corpus stats_history snapshots surfaced on video diagnosis. */
export function StatsHistoryStrip({
  history,
  distributionShape,
}: {
  history: StatsHistorySnapshot[] | null | undefined;
  distributionShape?: string | null;
}) {
  const rows = (history ?? []).filter(
    (r) => r && typeof r.views === "number" && r.phase,
  );
  if (rows.length < 2) return null;

  const ordered = [...rows].sort((a, b) => {
    const rank = (p: string) =>
      p === "t0" ? 0 : p === "t6h" ? 1 : p === "t24h" ? 2 : 9;
    return rank(a.phase) - rank(b.phase) || a.at.localeCompare(b.at);
  });

  const spikeFlat = distributionShape === "spike_then_flat";

  return (
    <section
      className="mb-4 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4"
      aria-label="Diễn biến view theo thời gian"
    >
      <p className="gv-kicker mb-2 text-[color:var(--gv-ink-3)]">
        Diễn biến sau đăng
        {spikeFlat ? (
          <span className="ml-2 rounded-full bg-[color:var(--gv-accent-soft)] px-2 py-0.5 text-[color:var(--gv-accent-deep)]">
            Spike rồi phẳng
          </span>
        ) : null}
      </p>
      <div className="grid grid-cols-1 gap-2 min-[480px]:grid-cols-3">
        {ordered.map((row) => (
          <div
            key={`${row.phase}-${row.at}`}
            className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2"
          >
            <span className="gv-mono block text-[11px] font-semibold tracking-[0.18em] text-[color:var(--gv-ink-3)]">
              {PHASE_LABEL[row.phase] ?? row.phase}
            </span>
            <p className="gv-mono mt-1 text-base font-semibold tabular-nums text-[color:var(--gv-ink)]">
              {formatViews(row.views)}
            </p>
            <p className="mt-0.5 text-xs text-[color:var(--gv-ink-3)]">
              ER {erPct(row)}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
