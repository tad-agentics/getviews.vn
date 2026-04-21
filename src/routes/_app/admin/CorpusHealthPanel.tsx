/**
 * Phase D.6.1 — Corpus health panel.
 *
 * Renders the `/admin/corpus-health` response (which already existed for
 * ops-secret callers and was moved to `require_admin` in D.6.0). Two
 * sections: a summary strip across the top with four monospace counters
 * and a tier-histogram bar, then a per-niche table sorted by 30-day
 * ingest volume descending — which is the order an operator cares about
 * when deciding where to kick off a manual ingest.
 *
 * The panel intentionally does NOT render alarms / thresholds yet. The
 * plan mentions "stale data warning at 7d without ingest" but that
 * threshold is niche-specific (a slow niche like education is fine at
 * 7d, a fast one like beauty is broken); wiring that in needs per-niche
 * config which is out of scope for D.6.1.
 */
import { useMemo } from "react";
import { useCorpusHealth, type ClaimTier, type CorpusHealthNicheRow } from "@/hooks/useCorpusHealth";

const TIER_LABEL: Record<ClaimTier, string> = {
  none: "Chưa đủ",
  reference_pool: "Reference pool",
  basic_citation: "Basic citation",
  niche_norms: "Niche norms",
  hook_effectiveness: "Hook effectiveness",
  trend_delta: "Trend delta",
};

const TIER_ORDER: ClaimTier[] = [
  "none",
  "reference_pool",
  "basic_citation",
  "niche_norms",
  "hook_effectiveness",
  "trend_delta",
];

function relativeAge(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const hours = Math.round((Date.now() - then) / 3_600_000);
  if (hours < 1) return "<1h";
  if (hours < 24) return `${hours}h`;
  return `${Math.round(hours / 24)}d`;
}

function TierChip({ tier }: { tier: ClaimTier }) {
  const passing = tier !== "none";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 gv-mono text-[10px] uppercase tracking-wider ${
        passing
          ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent)]"
          : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)]"
      }`}
    >
      {TIER_LABEL[tier]}
    </span>
  );
}

function SummaryCounter({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
        {label}
      </span>
      <span className="gv-mono text-[24px] font-semibold text-[color:var(--gv-ink)] tabular-nums">
        {typeof value === "number" ? value.toLocaleString("vi-VN") : value}
      </span>
    </div>
  );
}

function TierHistogram({ histogram, total }: { histogram: Record<ClaimTier, number>; total: number }) {
  if (total === 0) {
    return (
      <p className="text-[12px] text-[color:var(--gv-ink-3)]">
        Chưa có niche nào đạt ngưỡng đầu tiên.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-1.5">
      {TIER_ORDER.map((tier) => {
        const count = histogram[tier] ?? 0;
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        return (
          <div key={tier} className="flex items-center gap-3">
            <div className="w-[140px] shrink-0">
              <TierChip tier={tier} />
            </div>
            <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-[color:var(--gv-canvas-2)]">
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-[color:var(--gv-accent)]"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-[60px] shrink-0 gv-mono text-[11px] tabular-nums text-[color:var(--gv-ink-3)]">
              {count} ({pct}%)
            </span>
          </div>
        );
      })}
    </div>
  );
}

function NicheRow({ row }: { row: CorpusHealthNicheRow }) {
  const name = row.name_vn || row.name_en || `niche ${row.niche_id}`;
  return (
    <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
      <td className="py-2 pr-4 text-[13px] text-[color:var(--gv-ink)]">{name}</td>
      <td className="py-2 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-3)]">
        {row.videos_7d}
      </td>
      <td className="py-2 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink)]">
        {row.videos_30d}
      </td>
      <td className="py-2 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-4)]">
        {row.videos_90d}
      </td>
      <td className="py-2 pr-4 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
        {relativeAge(row.last_ingest_at)}
      </td>
      <td className="py-2">
        <TierChip tier={row.highest_passing_tier} />
      </td>
    </tr>
  );
}

export function CorpusHealthPanel() {
  const q = useCorpusHealth();

  const topTen = useMemo(() => q.data?.niches.slice(0, 10) ?? [], [q.data]);
  const remainder = useMemo(() => q.data?.niches.slice(10) ?? [], [q.data]);

  if (q.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải corpus health"
        className="h-40 animate-pulse rounded-md bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (q.isError) {
    const code = q.error instanceof Error ? q.error.message : "unknown";
    return (
      <p className="text-[12px] text-[color:var(--gv-danger)]">
        Không tải được corpus health ({code}).
      </p>
    );
  }
  if (!q.data) return null;

  const { summary, niches, as_of } = q.data;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
        <SummaryCounter label="Niches" value={summary.niches_total} />
        <SummaryCounter label="Videos · 7d" value={summary.videos_7d_total} />
        <SummaryCounter label="Videos · 30d" value={summary.videos_30d_total} />
        <SummaryCounter label="Videos · 90d" value={summary.videos_90d_total} />
      </div>

      <div className="flex flex-col gap-2">
        <h3 className="gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
          Claim tier distribution
        </h3>
        <TierHistogram histogram={summary.tier_histogram} total={summary.niches_total} />
      </div>

      <div className="flex flex-col gap-2">
        <h3 className="gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
          Top niches by 30d volume
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <th className="py-2 pr-4 text-left gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
                  Niche
                </th>
                <th className="py-2 pr-4 text-left gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
                  7d
                </th>
                <th className="py-2 pr-4 text-left gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
                  30d
                </th>
                <th className="py-2 pr-4 text-left gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
                  90d
                </th>
                <th className="py-2 pr-4 text-left gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
                  Last ingest
                </th>
                <th className="py-2 text-left gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
                  Tier
                </th>
              </tr>
            </thead>
            <tbody>
              {topTen.map((n) => (
                <NicheRow key={n.niche_id} row={n} />
              ))}
            </tbody>
          </table>
          {remainder.length > 0 ? (
            <p className="mt-2 gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
              +{remainder.length} niches khác (ẩn để giữ panel gọn).
            </p>
          ) : null}
        </div>
      </div>

      <p className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
        As of {new Date(as_of).toLocaleString("vi-VN")} · {niches.length} niches total
      </p>
    </div>
  );
}
