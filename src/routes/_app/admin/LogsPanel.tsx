/**
 * Phase D.6.4 — Cloud Run logs panel (UIUX reference-aligned).
 *
 * Uses the chip/Btn/gv-mono palette from the reference. When disabled
 * (missing env flag, SDK, or creds) the panel renders a dashed-border
 * config card naming the specific knob to turn, so an operator knows
 * exactly what's blocking without digging into Cloud Run docs.
 */
import { useState } from "react";
import { Btn } from "@/components/v2/Btn";
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
    // No dedicated --gv-warn token yet; bold ink provides the contrast.
    return "text-[color:var(--gv-ink)]";
  }
  return "text-[color:var(--gv-ink-4)]";
}

function PillSelect<T extends string | number>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T;
  onChange: (v: T) => void;
  options: ReadonlyArray<{ value: T; label: string }>;
}) {
  return (
    <label className="inline-flex items-center gap-2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5">
      <span className="gv-uc text-[10px] font-semibold text-[color:var(--gv-ink-4)]">
        {label}
      </span>
      <select
        value={String(value)}
        onChange={(e) => {
          const raw = e.target.value;
          const matched = options.find((o) => String(o.value) === raw);
          if (matched) onChange(matched.value);
        }}
        className="bg-transparent gv-mono text-[11px] font-semibold text-[color:var(--gv-ink)] gv-focus"
      >
        {options.map((o) => (
          <option key={String(o.value)} value={String(o.value)}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function LogEntryRow({ entry }: { entry: CloudRunLogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const ts = entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString("vi-VN") : "—";
  const preview = entry.message.length > 140 ? entry.message.slice(0, 140) + "…" : entry.message;
  const hasMore = entry.message.length > 140;

  return (
    <div className="border-b border-[color:var(--gv-rule)] py-2 last:border-0">
      <button
        type="button"
        onClick={() => (hasMore ? setExpanded((v) => !v) : undefined)}
        className="flex w-full items-start gap-3 text-left"
        aria-expanded={hasMore ? expanded : undefined}
      >
        <span className="w-[76px] shrink-0 gv-mono text-[10px] tabular-nums text-[color:var(--gv-ink-4)]">
          {ts}
        </span>
        <span className={`w-[74px] shrink-0 gv-mono text-[10px] font-semibold uppercase tracking-[0.08em] ${severityTone(entry.severity)}`}>
          {entry.severity}
        </span>
        <span className="min-w-0 flex-1 gv-mono text-[11px] leading-relaxed text-[color:var(--gv-ink)] break-words">
          {expanded ? entry.message : preview}
        </span>
      </button>
    </div>
  );
}

function DisabledCard({ reason, hint }: { reason: string; hint: string }) {
  const titleByReason: Record<string, string> = {
    disabled: "Panel chưa được bật",
    sdk_missing: "Thiếu google-cloud-logging SDK",
    project_missing: "Thiếu GCP_PROJECT_ID",
    credentials_error: "Credentials lỗi",
  };
  const title = titleByReason[reason] ?? "Panel chưa sẵn sàng";
  return (
    <div className="flex flex-col gap-1.5 rounded-[var(--gv-radius-md)] border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4">
      <p className="gv-serif text-[14px] text-[color:var(--gv-ink)]">{title}</p>
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
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <PillSelect
          label="SEV"
          value={severity}
          onChange={(v) => setSeverity(v)}
          options={SEVERITIES.map((s) => ({ value: s, label: s }))}
        />
        <PillSelect
          label="WINDOW"
          value={minutes}
          onChange={(v) => setMinutes(v)}
          options={WINDOWS.map((w) => ({ value: w.minutes, label: w.label }))}
        />
        <Btn
          variant="ghost"
          size="sm"
          onClick={() => void q.refetch()}
          disabled={q.isFetching}
          className="ml-auto"
        >
          {q.isFetching ? "Đang tải…" : "Refresh"}
        </Btn>
      </div>

      {q.isLoading ? (
        <div
          role="status"
          aria-label="Đang tải logs"
          className="h-48 animate-pulse rounded-[var(--gv-radius-md)] bg-[color:var(--gv-canvas-2)]"
        />
      ) : q.isError ? (
        <p className="text-[13px] text-[color:var(--gv-danger)]">
          Không tải được logs ({q.error instanceof Error ? q.error.message : "unknown"}).
        </p>
      ) : !q.data ? null : q.data.enabled === false ? (
        <DisabledCard reason={q.data.reason} hint={q.data.hint} />
      ) : q.data.entries.length === 0 ? (
        <p className="gv-mono text-[12px] text-[color:var(--gv-ink-3)]">
          Không có log nào trong cửa sổ này (severity ≥ {severity}, {minutes}m).
        </p>
      ) : (
        <div className="max-h-[420px] overflow-y-auto rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3">
          {q.data.entries.map((entry, i) => (
            <LogEntryRow key={`${entry.timestamp ?? i}-${i}`} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
