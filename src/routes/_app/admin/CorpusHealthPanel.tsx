/**
 * Phase D.6.1 — Corpus health panel (UIUX reference-aligned).
 *
 * Renders the `/admin/corpus-health` response with the editorial rhythm
 * from `artifacts/uiux-reference/screens/*.jsx`: gv-bignum counters in
 * a four-column strip, a claim-tier histogram, and a table of taxonomy
 * niches by 30d volume (10 rows by default, expandable to all). Tier chips use the
 * accent-soft / ink-4 palette the reference sound/trend chips use.
 */
import { useMemo, useState } from "react";
import { useCorpusHealth, type ClaimTier, type CorpusHealthNicheRow } from "@/hooks/useCorpusHealth";

const TIER_LABEL: Record<ClaimTier, string> = {
  none: "Chưa đủ ngưỡng",
  reference_pool: "Pool tham chiếu (≥5 / 30d)",
  basic_citation: "Trích dẫn cơ bản (≥20)",
  niche_norms: "Chuẩn ngách (≥30)",
  hook_effectiveness: "Hiệu quả hook (≥50)",
  trend_delta: "Delta xu hướng (≥100)",
};

/** Default rows before "Xem thêm"; full list available via toggle. */
const COLLAPSED_NICHE_ROWS = 10;

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
        "inline-flex items-center rounded-full px-2.5 py-0.5 gv-kicker " +
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
      <span className="gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
        {label}
      </span>
      <span className="gv-bignum text-[color:var(--gv-ink)] tabular-nums">{display}</span>
    </div>
  );
}

function TierHistogram({ histogram, total }: { histogram: Record<ClaimTier, number>; total: number }) {
  if (total === 0) {
    return (
      <p className="text-sm text-[color:var(--gv-ink-3)]">
        Chưa có dòng taxonomy nào trong danh sách.
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
            <span className="w-[72px] shrink-0 gv-kicker tabular-nums text-[color:var(--gv-ink-3)]">
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
      <td className="py-2.5 pr-4 text-sm text-[color:var(--gv-ink)]">{name}</td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-3)]">
        {row.videos_7d}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink)]">
        {row.videos_30d}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-4)]">
        {row.videos_90d}
      </td>
      <td className="py-2.5 pr-4 gv-kicker text-[color:var(--gv-ink-3)]">
        {relativeAge(row.last_ingest_at)}
      </td>
      <td className="py-2.5 pr-4 gv-kicker text-[color:var(--gv-ink-4)]">
        {relativeAge(row.last_pattern_at ?? null)}
      </td>
      <td className="py-2.5">
        <TierChip tier={row.highest_passing_tier} />
      </td>
    </tr>
  );
}

function TH({ children }: { children: React.ReactNode }) {
  return (
    <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
      {children}
    </th>
  );
}

export function CorpusHealthPanel() {
  const q = useCorpusHealth();
  const [showAllNiches, setShowAllNiches] = useState(false);

  const niches = q.data?.niches ?? [];
  const canExpandNiches = niches.length > COLLAPSED_NICHE_ROWS;
  const visibleNiches = useMemo(() => {
    if (!canExpandNiches || showAllNiches) return niches;
    return niches.slice(0, COLLAPSED_NICHE_ROWS);
  }, [canExpandNiches, niches, showAllNiches]);

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
      <p className="text-sm text-[color:var(--gv-danger)]">
        Không tải được corpus health ({code}).
      </p>
    );
  }
  if (!q.data) return null;

  const { summary, as_of } = q.data;

  return (
    <div className="flex flex-col gap-7">
      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
        <Bignum label="Dòng taxonomy" value={summary.niches_total} />
        <Bignum label="Video corpus · 7 ngày" value={summary.videos_7d_total} />
        <Bignum label="Video corpus · 30 ngày" value={summary.videos_30d_total} />
        <Bignum label="Video corpus · 90 ngày" value={summary.videos_90d_total} />
      </div>

      {/* Tier distribution */}
      <div className="rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
        <p className="gv-kicker gv-kicker--dot mb-3">
          Phân bố tier claim (theo video 30d / niche_id)
        </p>
        <TierHistogram histogram={summary.tier_histogram} total={summary.niches_total} />
      </div>

      {/* Niche volume table — collapsed to first rows; expand to full list */}
      <div className="rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
        <p className="gv-kicker gv-kicker--dot gv-kicker--muted mb-3">
          Bảng taxonomy — sắp theo lượng video 30 ngày
        </p>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <TH>Ngách (taxonomy)</TH>
                <TH>7 ngày</TH>
                <TH>30 ngày</TH>
                <TH>90 ngày</TH>
                <TH>Ingest gần nhất</TH>
                <TH>Mẫu trend</TH>
                <TH>Tier claim</TH>
              </tr>
            </thead>
            <tbody>
              {visibleNiches.map((n) => (
                <NicheRow key={n.niche_id} row={n} />
              ))}
            </tbody>
          </table>
          {canExpandNiches ? (
            <div className="mt-2 flex justify-end border-t border-[color:var(--gv-rule)] pt-2">
              <button
                type="button"
                className="min-h-11 min-w-11 rounded-md px-3 text-sm font-medium text-[color:var(--gv-accent-deep)] underline decoration-[color:var(--gv-rule)] underline-offset-2 transition-colors hover:text-[color:var(--gv-ink)]"
                onClick={() => setShowAllNiches((v) => !v)}
                aria-expanded={showAllNiches}
              >
                {showAllNiches
                  ? "Thu gọn"
                  : `Xem thêm (${niches.length - COLLAPSED_NICHE_ROWS})`}
              </button>
            </div>
          ) : null}
        </div>
      </div>

      <p className="gv-kicker text-[color:var(--gv-ink-3)]">
        Cập nhật {new Date(as_of).toLocaleString("vi-VN")} · {niches.length} dòng taxonomy
      </p>
    </div>
  );
}
