/**
 * Phase D.6.1 — Corpus health panel (UIUX reference-aligned).
 *
 * Renders the `/admin/corpus-health` response with the editorial rhythm
 * from `artifacts/uiux-reference/screens/*.jsx`: gv-bignum counters in
 * a four-column strip, a kicker-labelled claim-tier histogram, and a
 * table of the ten busiest niches by 30d volume. Tier chips use the
 * accent-soft / ink-4 palette the reference sound/trend chips use.
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
      className={
        "inline-flex items-center rounded-full px-2.5 py-0.5 gv-mono text-[10px] font-semibold uppercase tracking-[0.08em] " +
        (passing
          ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]"
          : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)]")
      }
    >
      {TIER_LABEL[tier]}
    </span>
  );
}

function Bignum({ label, value }: { label: string; value: number | string }) {
  const display = typeof value === "number" ? value.toLocaleString("vi-VN") : value;
  return (
    <div className="flex flex-col gap-1.5">
      <span className="gv-uc text-[10px] font-semibold text-[color:var(--gv-ink-4)]">
        {label}
      </span>
      <span className="gv-bignum text-[color:var(--gv-ink)] tabular-nums">{display}</span>
    </div>
  );
}

function TierHistogram({ histogram, total }: { histogram: Record<ClaimTier, number>; total: number }) {
  if (total === 0) {
    return (
      <p className="text-[13px] text-[color:var(--gv-ink-3)]">
        Chưa có niche nào đạt ngưỡng đầu tiên.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {TIER_ORDER.map((tier) => {
        const count = histogram[tier] ?? 0;
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        return (
          <div key={tier} className="flex items-center gap-3">
            <div className="w-[150px] shrink-0">
              <TierChip tier={tier} />
            </div>
            <div
              className="relative h-[8px] flex-1 overflow-hidden rounded-full"
              style={{ background: "var(--gv-rule-2)" }}
            >
              <div
                className="absolute inset-y-0 left-0 rounded-full"
                style={{ width: `${pct}%`, background: "var(--gv-accent)" }}
              />
            </div>
            <span className="w-[72px] shrink-0 gv-mono text-[11px] tabular-nums text-[color:var(--gv-ink-3)]">
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
      <td className="py-2.5 pr-4 text-[13px] text-[color:var(--gv-ink)]">{name}</td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-3)]">
        {row.videos_7d}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink)]">
        {row.videos_30d}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-4)]">
        {row.videos_90d}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
        {relativeAge(row.last_ingest_at)}
      </td>
      <td className="py-2.5">
        <TierChip tier={row.highest_passing_tier} />
      </td>
    </tr>
  );
}

function TH({ children }: { children: React.ReactNode }) {
  return (
    <th className="py-2 pr-4 text-left gv-uc text-[9.5px] font-semibold text-[color:var(--gv-ink-4)]">
      {children}
    </th>
  );
}

export function CorpusHealthPanel() {
  const q = useCorpusHealth();

  const topTen = useMemo(() => q.data?.niches.slice(0, 10) ?? [], [q.data]);
  const remainder = useMemo(() => (q.data?.niches.length ?? 0) - (q.data?.niches.slice(0, 10).length ?? 0), [q.data]);

  if (q.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải corpus health"
        className="h-48 animate-pulse rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (q.isError) {
    const code = q.error instanceof Error ? q.error.message : "unknown";
    return (
      <p className="text-[13px] text-[color:var(--gv-danger)]">
        Không tải được corpus health ({code}).
      </p>
    );
  }
  if (!q.data) return null;

  const { summary, as_of, niches } = q.data;

  return (
    <div className="flex flex-col gap-7">
      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
        <Bignum label="Niches" value={summary.niches_total} />
        <Bignum label="Videos · 7d" value={summary.videos_7d_total} />
        <Bignum label="Videos · 30d" value={summary.videos_30d_total} />
        <Bignum label="Videos · 90d" value={summary.videos_90d_total} />
      </div>

      {/* Tier distribution */}
      <div className="rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
        <p className="gv-kicker gv-kicker--dot mb-3">
          Claim tier distribution
        </p>
        <TierHistogram histogram={summary.tier_histogram} total={summary.niches_total} />
      </div>

      {/* Top-10 niches */}
      <div className="rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
        <p className="gv-kicker gv-kicker--dot gv-kicker--muted mb-3">
          Top niches by 30d volume
        </p>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <TH>Niche</TH>
                <TH>7d</TH>
                <TH>30d</TH>
                <TH>90d</TH>
                <TH>Last ingest</TH>
                <TH>Tier</TH>
              </tr>
            </thead>
            <tbody>
              {topTen.map((n) => (
                <NicheRow key={n.niche_id} row={n} />
              ))}
            </tbody>
          </table>
          {remainder > 0 ? (
            <p className="mt-3 gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
              + {remainder} niche khác (ẩn để giữ panel gọn).
            </p>
          ) : null}
        </div>
      </div>

      <p className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
        As of {new Date(as_of).toLocaleString("vi-VN")} · {niches.length} niches total
      </p>
    </div>
  );
}
