/**
 * Admin — content_class-first corpus health (Phase 0 pivot observability).
 */
import { useMemo, useState } from "react";
import {
  useCorpusClassHealth,
  type AssignmentTierKey,
  type CorpusClassHealthRow,
} from "@/hooks/useCorpusClassHealth";

const TIER_LABEL: Record<AssignmentTierKey, string> = {
  validated: "Validated (ACQE)",
  low_conf: "Low confidence",
  flagged: "Flagged",
  null: "Chưa tier",
};

const COLLAPSED_ROWS = 10;

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

function ViabilityChip({ tier }: { tier: string | null }) {
  const t = tier ?? "unknown";
  const tone =
    t === "Healthy"
      ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]"
      : t === "Thin"
        ? "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]"
        : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)]";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 gv-kicker ${tone}`}>
      {t}
    </span>
  );
}

function ClassRow({ row }: { row: CorpusClassHealthRow }) {
  const name = row.name_vn || row.slug || `class ${row.content_class_id}`;
  return (
    <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
      <td className="py-2.5 pr-4 text-sm text-[color:var(--gv-ink)]">{name}</td>
      <td className="py-2.5 pr-4 gv-kicker text-[color:var(--gv-ink-4)]">{row.format_axis ?? "—"}</td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-3)]">
        {row.videos_7d}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink)]">
        {row.videos_30d}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-4)]">
        {row.videos_90d}
      </td>
      <td className="py-2.5">
        <ViabilityChip tier={row.viability_tier} />
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

export function CorpusClassHealthPanel() {
  const q = useCorpusClassHealth();
  const [showAll, setShowAll] = useState(false);

  const rows = q.data?.content_classes ?? [];
  const canExpand = rows.length > COLLAPSED_ROWS;
  const visible = useMemo(() => {
    if (!canExpand || showAll) return rows;
    return rows.slice(0, COLLAPSED_ROWS);
  }, [canExpand, rows, showAll]);

  if (q.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải corpus class health"
        className="h-48 animate-pulse rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (q.isError) {
    const code = q.error instanceof Error ? q.error.message : "unknown";
    return (
      <p className="text-sm text-[color:var(--gv-danger)]">
        Không tải được corpus class health ({code}).
      </p>
    );
  }
  if (!q.data) return null;

  const { summary, as_of } = q.data;
  const missPct = Math.round(summary.junction_miss_rate_30d * 1000) / 10;
  const tierOrder: AssignmentTierKey[] = ["validated", "low_conf", "flagged", "null"];

  return (
    <div className="flex flex-col gap-7">
      <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
        <Bignum label="Content class active" value={summary.classes_total} />
        <Bignum label="Class có corpus · 30 ngày" value={summary.classes_with_corpus_30d} />
        <Bignum label="Video corpus · 30 ngày" value={summary.videos_30d_total} />
        <Bignum
          label="Junction miss · 30 ngày"
          value={`${summary.junction_miss_30d} (${missPct}%)`}
        />
      </div>

      <div className="grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-4">
        <Bignum label="Class mỏng (<20 / 30d)" value={summary.classes_thin_under_20} />
        <Bignum label="Class 0 corpus · 30d" value={summary.classes_zero_corpus_30d} />
        <Bignum label="Video · 7 ngày" value={summary.videos_7d_total} />
        <Bignum label="Video · 90 ngày" value={summary.videos_90d_total} />
      </div>

      <div className="rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
        <p className="gv-kicker gv-kicker--dot mb-3">
          Phân bố assignment tier (video 30d)
        </p>
        <div className="flex flex-col gap-2">
          {tierOrder.map((tier) => {
            const count = summary.assignment_tier_histogram_30d[tier] ?? 0;
            const total = summary.videos_30d_total;
            const pct = total > 0 ? Math.round((count / total) * 100) : 0;
            return (
              <div key={tier} className="flex items-center gap-3">
                <span className="w-[140px] shrink-0 gv-kicker text-[color:var(--gv-ink-3)]">
                  {TIER_LABEL[tier]}
                </span>
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
      </div>

      <div className="rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
        <p className="gv-kicker gv-kicker--dot gv-kicker--muted mb-3">
          Bảng content class — sắp theo lượng video 30 ngày
        </p>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <TH>Content class</TH>
                <TH>Format axis</TH>
                <TH>7 ngày</TH>
                <TH>30 ngày</TH>
                <TH>90 ngày</TH>
                <TH>ACQE tier</TH>
              </tr>
            </thead>
            <tbody>
              {visible.map((r) => (
                <ClassRow key={r.content_class_id} row={r} />
              ))}
            </tbody>
          </table>
          {canExpand ? (
            <div className="mt-2 flex justify-end border-t border-[color:var(--gv-rule)] pt-2">
              <button
                type="button"
                className="min-h-11 min-w-11 rounded-md px-3 text-sm font-medium text-[color:var(--gv-accent-deep)] underline decoration-[color:var(--gv-rule)] underline-offset-2 transition-colors hover:text-[color:var(--gv-ink)]"
                onClick={() => setShowAll((v) => !v)}
                aria-expanded={showAll}
              >
                {showAll ? "Thu gọn" : `Xem thêm (${rows.length - COLLAPSED_ROWS})`}
              </button>
            </div>
          ) : null}
        </div>
      </div>

      <p className="gv-kicker text-[color:var(--gv-ink-3)]">
        Cập nhật {new Date(as_of).toLocaleString("vi-VN")} · {rows.length} content class
      </p>
    </div>
  );
}
