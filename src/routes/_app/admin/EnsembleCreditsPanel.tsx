/**
 * Phase D.6.2 — EnsembleData credits panel.
 *
 * Three numbers an operator wants here: "what did we burn today", "are
 * we trending up or down this week", and "when does the monthly budget
 * run out". The first two come straight from `/customer/get-used-units`
 * per UTC day (proxied through Cloud Run so the token doesn't ship to
 * the client). The third is computed against `ED_MONTHLY_UNIT_BUDGET` —
 * when it's unset we hide the projection instead of guessing a ceiling.
 *
 * A per-day failure (transient ED outage on one date) blanks only that
 * bar; the rest of the chart stays useful. "ensemble_token_unset" at
 * the top-level surfaces as a config hint rather than a generic error.
 */
import { useMemo } from "react";
import { useEnsembleCredits, type EnsembleDailyUnits } from "@/hooks/useEnsembleCredits";

function formatInt(n: number): string {
  return n.toLocaleString("vi-VN");
}

function SummaryCounter({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number | string;
  tone?: "default" | "accent" | "danger";
}) {
  const toneClass =
    tone === "accent"
      ? "text-[color:var(--gv-accent)]"
      : tone === "danger"
        ? "text-[color:var(--gv-danger)]"
        : "text-[color:var(--gv-ink)]";
  return (
    <div className="flex flex-col gap-1">
      <span className="gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
        {label}
      </span>
      <span className={`gv-mono text-[22px] font-semibold tabular-nums ${toneClass}`}>
        {typeof value === "number" ? formatInt(value) : value}
      </span>
    </div>
  );
}

function UsageBarChart({ days, peak }: { days: EnsembleDailyUnits[]; peak: number }) {
  if (days.length === 0) return null;
  return (
    <div className="flex h-[80px] items-end gap-[3px]" role="img" aria-label="EnsembleData daily usage trend">
      {days.map((d) => {
        const height = peak > 0 ? Math.max(2, Math.round((d.units / peak) * 78)) : 2;
        const failed = !d.ok;
        return (
          <div
            key={d.date}
            className="group relative flex-1"
            title={failed ? `${d.date} · lỗi: ${d.error}` : `${d.date} · ${formatInt(d.units)} units`}
          >
            <div
              className={`w-full rounded-sm ${
                failed
                  ? "bg-[color:var(--gv-ink-4)]/30"
                  : "bg-[color:var(--gv-accent)]"
              }`}
              style={{ height: `${height}px` }}
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
        className="h-40 animate-pulse rounded-md bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (q.isError) {
    const msg = q.error instanceof Error ? q.error.message : "unknown";
    if (msg === "ensemble_token_unset") {
      return (
        <p className="text-[12px] text-[color:var(--gv-ink-3)]">
          ENSEMBLE_DATA_API_KEY chưa được cấu hình trên Cloud Run. Đặt env var và redeploy để
          panel này hoạt động.
        </p>
      );
    }
    return (
      <p className="text-[12px] text-[color:var(--gv-danger)]">
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
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
        <SummaryCounter label="Hôm nay" value={today} />
        <SummaryCounter label="7 ngày qua" value={last7dTotal} />
        {monthly_budget != null ? (
          <>
            <SummaryCounter
              label="Tháng này"
              value={`${formatInt(monthlyUsed)} / ${formatInt(monthly_budget)}`}
            />
            <SummaryCounter
              label="Runway"
              value={runwayDays != null ? `${runwayDays} ngày` : "—"}
              tone={runwayDays != null && runwayDays < 7 ? "danger" : "default"}
            />
          </>
        ) : (
          <>
            <SummaryCounter
              label="Projection 30d"
              value={projection != null ? projection : "—"}
            />
            <SummaryCounter label="Budget" value="Chưa đặt" />
          </>
        )}
      </div>

      <UsageBarChart days={days} peak={peak} />

      <p className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
        As of {new Date(as_of).toLocaleString("vi-VN")} · {days.length} ngày (UTC)
        {monthly_budget == null
          ? " · đặt ED_MONTHLY_UNIT_BUDGET env để thấy runway"
          : ""}
      </p>
    </div>
  );
}
