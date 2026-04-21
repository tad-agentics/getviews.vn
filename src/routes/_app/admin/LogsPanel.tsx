/**
 * Phase D.6.4 — Cloud Run logs panel.
 *
 * Optional feature: the backend returns `{enabled: false, reason, hint}`
 * when the `[logs]` extra isn't installed, the env flag is off, or
 * credentials aren't provisioned. The panel renders each of those
 * states as a specific actionable message rather than a generic error,
 * so an operator who wants logs enabled knows exactly which knob to
 * turn next (set env var vs. install dep vs. grant IAM role).
 *
 * When enabled, shows a severity dropdown + time-window dropdown on top,
 * then a tail of entries newest-first. Click a row to expand the full
 * payload (often a JSON-flattened struct log).
 */
import { useState } from "react";
import {
  useCloudRunLogs,
  type CloudRunLogEntry,
  type LogSeverity,
} from "@/hooks/useCloudRunLogs";

const SEVERITIES: LogSeverity[] = ["INFO", "WARNING", "ERROR", "CRITICAL"];
const WINDOWS = [
  { label: "15 phút", minutes: 15 },
  { label: "1 giờ", minutes: 60 },
  { label: "6 giờ", minutes: 360 },
  { label: "24 giờ", minutes: 1440 },
];

function severityTone(severity: string): string {
  if (severity === "ERROR" || severity === "CRITICAL" || severity === "ALERT" || severity === "EMERGENCY") {
    return "text-[color:var(--gv-danger)]";
  }
  if (severity === "WARNING") {
    // No dedicated warn token in the design system — we distinguish warn
    // from info by boldness + ink (primary) vs ink-4 (faint) rather than
    // by hue. Good enough for a compact log tail; if this panel grows a
    // --gv-warn token belongs in app.css.
    return "text-[color:var(--gv-ink)]";
  }
  return "text-[color:var(--gv-ink-4)]";
}

function LogEntryRow({ entry }: { entry: CloudRunLogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const ts = entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString("vi-VN") : "—";
  const preview = entry.message.length > 140 ? entry.message.slice(0, 140) + "…" : entry.message;
  const hasMore = entry.message.length > 140;

  return (
    <div className="border-b border-[color:var(--gv-rule)] py-1.5 last:border-0">
      <button
        type="button"
        onClick={() => (hasMore ? setExpanded((v) => !v) : undefined)}
        className="flex w-full items-start gap-2 text-left"
        aria-expanded={hasMore ? expanded : undefined}
      >
        <span className="w-[72px] shrink-0 gv-mono text-[10px] tabular-nums text-[color:var(--gv-ink-4)]">
          {ts}
        </span>
        <span className={`w-[70px] shrink-0 gv-mono text-[10px] font-semibold uppercase ${severityTone(entry.severity)}`}>
          {entry.severity}
        </span>
        <span className="min-w-0 flex-1 gv-mono text-[11px] leading-relaxed text-[color:var(--gv-ink)] break-words">
          {expanded ? entry.message : preview}
        </span>
      </button>
    </div>
  );
}

function DisabledState({ reason, hint }: { reason: string; hint: string }) {
  const titleByReason: Record<string, string> = {
    disabled: "Panel chưa được bật",
    sdk_missing: "Thiếu google-cloud-logging SDK",
    project_missing: "Thiếu GCP_PROJECT_ID",
    credentials_error: "Credentials lỗi",
  };
  const title = titleByReason[reason] ?? "Panel chưa sẵn sàng";
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-3">
      <p className="text-[13px] font-medium text-[color:var(--gv-ink)]">{title}</p>
      <p className="gv-mono text-[11px] leading-relaxed text-[color:var(--gv-ink-3)]">
        {hint}
      </p>
    </div>
  );
}

export function LogsPanel() {
  const [severity, setSeverity] = useState<LogSeverity>("INFO");
  const [minutes, setMinutes] = useState<number>(60);
  const q = useCloudRunLogs({ severity, minutes, limit: 100 });

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1.5">
          <span className="gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
            Severity
          </span>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as LogSeverity)}
            className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2 py-1 gv-mono text-[11px]"
          >
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1.5">
          <span className="gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
            Window
          </span>
          <select
            value={minutes}
            onChange={(e) => setMinutes(Number(e.target.value))}
            className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2 py-1 gv-mono text-[11px]"
          >
            {WINDOWS.map((w) => (
              <option key={w.minutes} value={w.minutes}>
                {w.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => void q.refetch()}
          disabled={q.isFetching}
          className="ml-auto rounded-md border border-[color:var(--gv-rule)] px-3 py-1 gv-mono text-[11px] text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)] disabled:opacity-50"
        >
          {q.isFetching ? "Đang tải…" : "Refresh"}
        </button>
      </div>

      {q.isLoading ? (
        <div
          role="status"
          aria-label="Đang tải logs"
          className="h-40 animate-pulse rounded-md bg-[color:var(--gv-canvas-2)]"
        />
      ) : q.isError ? (
        <p className="text-[12px] text-[color:var(--gv-danger)]">
          Không tải được logs ({q.error instanceof Error ? q.error.message : "unknown"}).
        </p>
      ) : !q.data ? null : q.data.enabled === false ? (
        <DisabledState reason={q.data.reason} hint={q.data.hint} />
      ) : q.data.entries.length === 0 ? (
        <p className="text-[12px] text-[color:var(--gv-ink-3)]">
          Không có log nào trong cửa sổ này (severity ≥ {severity}, {minutes}m).
        </p>
      ) : (
        <div className="max-h-[360px] overflow-y-auto rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-2">
          {q.data.entries.map((entry, i) => (
            <LogEntryRow key={`${entry.timestamp ?? i}-${i}`} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
