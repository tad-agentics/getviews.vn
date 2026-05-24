/**
 * Admin — HI-13 Gemini Batch API corpus extraction observability.
 */
import { useHi13BatchHealth, type Hi13RunRow } from "@/hooks/useHi13BatchHealth";

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

function StatusChip({ enabled }: { enabled: boolean }) {
  const tone = enabled
    ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]"
    : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)]";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 gv-kicker ${tone}`}>
      {enabled ? "Đang bật" : "Tắt"}
    </span>
  );
}

function RunStatusChip({ status }: { status: string | null }) {
  const s = status ?? "unknown";
  const tone =
    s === "ok"
      ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]"
      : s === "failed"
        ? "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-danger)]"
        : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 gv-kicker ${tone}`}>
      {s}
    </span>
  );
}

function formatPct(rate: number) {
  return `${Math.round(rate * 1000) / 10}%`;
}

function formatUsd(n: number) {
  return `$${n.toFixed(2)}`;
}

function RunRow({ row }: { row: Hi13RunRow }) {
  const label = row.job_name === "batch/hi13-pilot" ? "Pilot HI-13" : "Ingest nightly";
  const started = row.started_at
    ? new Date(row.started_at).toLocaleString("vi-VN", { hour12: false })
    : "—";
  const ok = row.hi13.batch_line_ok;
  const fail = row.hi13.batch_line_fail;
  const fallback = row.sync_fallback;
  return (
    <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
      <td className="py-2.5 pr-4 text-sm text-[color:var(--gv-ink)]">{label}</td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] text-[color:var(--gv-ink-3)]">{started}</td>
      <td className="py-2.5 pr-4">
        <RunStatusChip status={row.status} />
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-accent-deep)]">
        {ok}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-danger)]">
        {fail}
      </td>
      <td className="py-2.5 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-4)]">
        {fallback}
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

export function Hi13BatchHealthPanel() {
  const q = useHi13BatchHealth();

  if (q.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải HI-13 batch health"
        className="h-48 animate-pulse rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (q.isError) {
    const code = q.error instanceof Error ? q.error.message : "unknown";
    return (
      <p className="text-sm text-[color:var(--gv-danger)]">
        Không tải được HI-13 batch health ({code}).
      </p>
    );
  }
  if (!q.data) return null;

  const { config, gemini_calls, ingest_30d, recent_runs, as_of } = q.data;
  const asOfLabel = new Date(as_of).toLocaleString("vi-VN", { hour12: false });

  return (
    <div className="flex flex-col gap-7">
      <div className="flex flex-wrap items-center gap-3">
        <StatusChip enabled={config.enabled} />
        <span className="text-sm text-[color:var(--gv-ink-4)]">
          Cập nhật {asOfLabel}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
        <Bignum label="Batch line OK · 30 ngày" value={ingest_30d.batch_line_ok} />
        <Bignum label="Batch line lỗi · 30 ngày" value={ingest_30d.batch_line_fail} />
        <Bignum
          label="Tỷ lệ thành công line"
          value={formatPct(ingest_30d.batch_line_success_rate)}
        />
        <Bignum label="Sync fallback · 30 ngày" value={ingest_30d.sync_fallback} />
      </div>

      <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
        <Bignum label="Gemini batch calls · 7 ngày" value={gemini_calls.batch_7d.count} />
        <Bignum label="Chi phí batch · 7 ngày" value={formatUsd(gemini_calls.batch_7d.cost_usd)} />
        <Bignum label="Gemini batch calls · 30 ngày" value={gemini_calls.batch_30d.count} />
        <Bignum label="Chi phí batch · 30 ngày" value={formatUsd(gemini_calls.batch_30d.cost_usd)} />
      </div>

      {recent_runs.length > 0 ? (
        <div className="overflow-x-auto rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)]">
          <table className="w-full min-w-[640px] border-collapse px-4">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <TH>Job</TH>
                <TH>Bắt đầu</TH>
                <TH>Trạng thái</TH>
                <TH>Line OK</TH>
                <TH>Line lỗi</TH>
                <TH>Fallback sync</TH>
              </tr>
            </thead>
            <tbody>
              {recent_runs.slice(0, 12).map((row, idx) => (
                <RunRow key={`${row.job_name}-${row.started_at ?? idx}`} row={row} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-[color:var(--gv-ink-4)]">
          Chưa có lần chạy ingest/pilot ghi nhận HI-13 trong 30 ngày qua.
        </p>
      )}
    </div>
  );
}
