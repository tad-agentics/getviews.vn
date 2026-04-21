/**
 * Phase D.6.6 — admin action log panel.
 *
 * Reads `/admin/action-log`. Rows are triggered-job audit entries with
 * actor, params snapshot, result status, duration, and timestamp. This
 * is where "who ran scene_intelligence on Tuesday at 4am" gets
 * answered, without leaving the dashboard for the Supabase studio.
 *
 * Keeping the panel compact — latest 50 entries in a borderless table
 * with gv-mono for dense data and a status chip (ok=pos, error=danger).
 * An "error" row's `error_message` is truncated on screen; click to
 * reveal the full string (same pattern as LogsPanel entries).
 */
import { useState } from "react";
import { Btn } from "@/components/v2/Btn";
import {
  useAdminActionLog,
  type AdminActionLogEntry,
} from "@/hooks/useAdminActionLog";

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const sec = Math.round((Date.now() - then) / 1000);
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.round(sec / 60)}m`;
  if (sec < 86400) return `${Math.round(sec / 3600)}h`;
  return `${Math.round(sec / 86400)}d`;
}

function formatDuration(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`;
}

function StatusChip({ status }: { status: "queued" | "running" | "ok" | "error" }) {
  const config: Record<typeof status, { bg: string; fg: string; label: string }> = {
    queued: {
      bg: "bg-[color:var(--gv-canvas-2)]",
      fg: "text-[color:var(--gv-ink-4)]",
      label: "queued",
    },
    running: {
      bg: "bg-[color:var(--gv-warn-soft)]",
      fg: "text-[color:var(--gv-warn)]",
      label: "running",
    },
    ok: {
      bg: "bg-[color:var(--gv-pos-soft)]",
      fg: "text-[color:var(--gv-pos-deep)]",
      label: "ok",
    },
    error: {
      bg: "bg-[color:var(--gv-accent-soft)]",
      fg: "text-[color:var(--gv-danger)]",
      label: "error",
    },
  };
  const c = config[status];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 gv-mono text-[10px] font-semibold uppercase tracking-[0.08em] ${c.bg} ${c.fg}`}
    >
      {c.label}
    </span>
  );
}

function TH({ children }: { children: React.ReactNode }) {
  return (
    <th className="py-2 pr-4 text-left gv-uc text-[9.5px] font-semibold text-[color:var(--gv-ink-4)]">
      {children}
    </th>
  );
}

function EntryRow({ entry }: { entry: AdminActionLogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const hasError = Boolean(entry.error_message);
  const paramKeys = Object.keys(entry.params_json);
  const paramSummary = paramKeys.length > 0 ? paramKeys.join(", ") : "—";

  return (
    <>
      <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
        <td className="py-2.5 pr-4 gv-mono text-[11px] text-[color:var(--gv-ink-3)]" title={entry.created_at}>
          {relativeTime(entry.created_at)}
        </td>
        <td className="py-2.5 pr-4 text-[13px] text-[color:var(--gv-ink)]">{entry.action}</td>
        <td className="py-2.5 pr-4 gv-mono text-[11px] tabular-nums text-[color:var(--gv-ink-4)]">
          {formatDuration(entry.duration_ms)}
        </td>
        <td className="py-2.5 pr-4 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
          {paramSummary}
        </td>
        <td className="py-2.5 pr-4">
          <StatusChip status={entry.result_status} />
        </td>
        <td className="py-2.5">
          {hasError ? (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="gv-mono text-[11px] text-[color:var(--gv-accent)] underline"
            >
              {expanded ? "Đóng" : "Xem lỗi"}
            </button>
          ) : (
            <span className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">—</span>
          )}
        </td>
      </tr>
      {expanded && hasError ? (
        <tr className="border-b border-[color:var(--gv-rule)]">
          <td colSpan={6} className="px-0 pb-3 pt-1">
            <pre className="max-h-40 overflow-auto rounded-[var(--gv-radius-sm)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-2 gv-mono text-[10px] text-[color:var(--gv-danger)]">
              {entry.error_message}
            </pre>
          </td>
        </tr>
      ) : null}
    </>
  );
}

export function ActionLogPanel() {
  const q = useAdminActionLog(50);

  if (q.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải audit log"
        className="h-40 animate-pulse rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (q.isError) {
    const msg = q.error instanceof Error ? q.error.message : "unknown";
    return (
      <p className="text-[13px] text-[color:var(--gv-danger)]">
        Không tải được audit log ({msg}).
      </p>
    );
  }
  if (!q.data) return null;
  if (q.data.entries.length === 0) {
    return (
      <p className="gv-mono text-[12px] text-[color:var(--gv-ink-3)]">
        Chưa có action nào được ghi (table mới hoặc không ai chạy job gần đây).
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-end">
        <Btn variant="ghost" size="sm" onClick={() => void q.refetch()} disabled={q.isFetching}>
          {q.isFetching ? "Đang tải…" : "Refresh"}
        </Btn>
      </div>
      <div className="overflow-x-auto rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-[color:var(--gv-rule)]">
              <TH>When</TH>
              <TH>Action</TH>
              <TH>Duration</TH>
              <TH>Params</TH>
              <TH>Status</TH>
              <TH>Error</TH>
            </tr>
          </thead>
          <tbody>
            {q.data.entries.map((entry) => (
              <EntryRow key={entry.id} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
