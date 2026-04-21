import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export type LogSeverity =
  | "DEFAULT"
  | "DEBUG"
  | "INFO"
  | "NOTICE"
  | "WARNING"
  | "ERROR"
  | "CRITICAL"
  | "ALERT"
  | "EMERGENCY";

export interface CloudRunLogEntry {
  timestamp: string | null;
  severity: string;
  message: string;
  logger: string;
}

export type DisabledReason =
  | "disabled"
  | "sdk_missing"
  | "project_missing"
  | "credentials_error";

export type CloudRunLogsResponse =
  | { ok: true; enabled: true; filter: string; entries: CloudRunLogEntry[] }
  | { ok: true; enabled: false; reason: DisabledReason; hint: string };

export interface LogsQueryParams {
  limit?: number;
  severity?: LogSeverity;
  minutes?: number;
}

/**
 * Queries `/admin/logs`. When the backend is disabled (missing env flag,
 * missing SDK, missing credentials), the response comes back with
 * `enabled: false` + a `reason` + `hint` — render that as a config
 * message rather than treating it as an error. Real errors (500 from
 * Cloud Run, admin_required) throw.
 */
export function useCloudRunLogs(params: LogsQueryParams = {}) {
  const { limit = 100, severity = "INFO", minutes = 60 } = params;
  return useQuery({
    queryKey: ["admin", "logs", { limit, severity, minutes }] as const,
    queryFn: async (): Promise<CloudRunLogsResponse> => {
      const base = env.VITE_CLOUD_RUN_API_URL;
      if (!base) throw new Error("cloud_run_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const qs = new URLSearchParams({
        limit: String(limit),
        severity,
        minutes: String(minutes),
      });
      const res = await fetch(`${base}/admin/logs?${qs}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as CloudRunLogsResponse;
    },
    // 30s — logs tail is the one admin panel an operator wants to refresh
    // more often than the others. refetchInterval is opt-in per caller.
    staleTime: 30_000,
  });
}
