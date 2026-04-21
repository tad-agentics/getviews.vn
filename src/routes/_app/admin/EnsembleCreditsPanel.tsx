/**
 * Phase D.6.2 — EnsembleData credits panel (UIUX reference-aligned).
 *
 * Four `gv-bignum` counters + a 14-day bar sparkline. Runway projection
 * turns red-tone only when < 7 days remain and the ED_MONTHLY_UNIT_BUDGET
 * env var is set (otherwise the runway pivot never triggers). Failed
 * days render as a faint ink-4 stub bar with a tooltip — the panel
 * stays readable even during a partial ED outage.
 */
import { useMemo } from "react";
import { useEnsembleCredits, type EnsembleDailyUnits } from "@/hooks/useEnsembleCredits";

function formatInt(n: number): string {
  return n.toLocaleString("vi-VN");
}

function Bignum({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number | string;
  tone?: "default" | "pos" | "danger";
}) {
  const display = typeof value === "number" ? formatInt(value) : value;
  const toneClass =
    tone === "pos"
      ? "text-[color:var(--gv-pos)]"
      : tone === "danger"
        ? "text-[color:var(--gv-danger)]"
        : "text-[color:var(--gv-ink)]";
  return (
    <div className="flex flex-col gap-1.5">
      <span className="gv-uc text-[10px] font-semibold text-[color:var(--gv-ink-4)]">
        {label}
      </span>
      <span className={`gv-bignum tabular-nums ${toneClass}`}>{display}</span>
    </div>
  );
}

function UsageBarChart({ days, peak }: { days: EnsembleDailyUnits[]; peak: number }) {
  if (days.length === 0) return null;
  return (
    <div
      className="flex h-[96px] items-end gap-[3px] rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3"
      role="img"
      aria-label="EnsembleData daily usage trend"
    >
      {days.map((d) => {
        const height = peak > 0 ? Math.max(3, Math.round((d.units / peak) * 72)) : 3;
        const failed = !d.ok;
        return (
          <div
            key={d.date}
            className="group relative flex-1"
            title={failed ? `${d.date} · lỗi: ${d.error}` : `${d.date} · ${formatInt(d.units)} units`}
          >
            <div
              className="w-full rounded-[2px]"
              style={{
                height: `${height}px`,
                background: failed ? "var(--gv-ink-4)" : "var(--gv-accent)",
                opacity: failed ? 0.35 : 1,
              }}
            />
          </div>
        );
      })}
    </div>
  );
}

export function EnsembleCreditsPanel() {
  const q = useEnsembleCredits(14);

  const { today, last7dTotal, peak, projection } = useMemo(() => {
    const days = q.data?.days ?? [];
    if (days.length === 0) {
      return { today: 0, last7dTotal: 0, peak: 0, projection: null as number | null };
    }
    const successful = days.filter((d) => d.ok);
    const latest = days[days.length - 1];
    const last7 = days.slice(-7).filter((d) => d.ok);
    const last7Sum = last7.reduce((acc, d) => acc + d.units, 0);
    const peakUnits = Math.max(0, ...successful.map((d) => d.units));
    const avg = last7.length > 0 ? last7Sum / last7.length : 0;
    const projected = avg > 0 ? Math.round(avg * 30) : null;
    return {
      today: latest?.ok ? latest.units : 0,
      last7dTotal: last7Sum,
      peak: peakUnits,
      projection: projected,
    };
  }, [q.data]);

  if (q.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải ensemble credits"
        className="h-48 animate-pulse rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (q.isError) {
    const msg = q.error instanceof Error ? q.error.message : "unknown";
    if (msg === "ensemble_token_unset") {
      return (
        <div className="rounded-[var(--gv-radius-md)] border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4">
          <p className="text-[13px] font-medium text-[color:var(--gv-ink)]">
            ENSEMBLE_DATA_API_KEY chưa được cấu hình
          </p>
          <p className="mt-1.5 gv-mono text-[11px] leading-relaxed text-[color:var(--gv-ink-3)]">
            Đặt env var trên Cloud Run và redeploy để panel này hoạt động.
          </p>
        </div>
      );
    }
    return (
      <p className="text-[13px] text-[color:var(--gv-danger)]">
        Không tải được EnsembleData usage ({msg}).
      </p>
    );
  }
  if (!q.data) return null;

  const { days, monthly_budget, as_of } = q.data;
  const monthlyUsed = days.filter((d) => d.ok).reduce((acc, d) => acc + d.units, 0);
  const remaining = monthly_budget != null ? Math.max(0, monthly_budget - monthlyUsed) : null;
  const runwayDays =
    monthly_budget != null && projection != null && projection > 0
      ? Math.max(0, Math.round((remaining ?? 0) / (projection / 30)))
      : null;

  return (
    <div className="flex flex-col gap-7">
      <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
        <Bignum label="Hôm nay" value={today} />
        <Bignum label="7 ngày qua" value={last7dTotal} />
        {monthly_budget != null ? (
          <>
            <Bignum
              label="Tháng này"
              value={`${formatInt(monthlyUsed)} / ${formatInt(monthly_budget)}`}
            />
            <Bignum
              label="Runway"
              value={runwayDays != null ? `${runwayDays}d` : "—"}
              tone={runwayDays != null && runwayDays < 7 ? "danger" : "default"}
            />
          </>
        ) : (
          <>
            <Bignum label="Projection · 30d" value={projection != null ? projection : "—"} />
            <Bignum label="Budget" value="Chưa đặt" />
          </>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <p className="gv-kicker gv-kicker--dot gv-kicker--muted">14 ngày gần nhất</p>
        <UsageBarChart days={days} peak={peak} />
      </div>

      <p className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
        As of {new Date(as_of).toLocaleString("vi-VN")} · {days.length} ngày (UTC)
        {monthly_budget == null
          ? " · đặt ED_MONTHLY_UNIT_BUDGET env để thấy runway"
          : ""}
      </p>
    </div>
  );
}
