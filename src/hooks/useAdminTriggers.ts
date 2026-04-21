import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export interface AdminTriggerJob {
  id: string;
  label: string;
  body_schema: Record<string, string>;
  heavy: boolean;
}

export interface AdminTriggerResult {
  ok: boolean;
  [key: string]: unknown;
}

export type JobStatus = "queued" | "running" | "ok" | "error";

export interface AdminJobRow {
  id: string;
  user_id: string | null;
  action: string;
  params_json: Record<string, unknown>;
  result_status: JobStatus;
  error_message: string | null;
  duration_ms: number | null;
  result_json: Record<string, unknown> | null;
  created_at: string;
}

export interface AdminTriggerAcceptedResponse {
  ok: true;
  job_id: string | null;
  status: JobStatus;
  // When `job_id` is null (audit insert failed, sync fallback), the
  // runner's response is attached inline — no polling needed.
  result?: AdminTriggerResult;
}

async function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  const base = env.VITE_CLOUD_RUN_API_URL;
  if (!base) throw new Error("cloud_run_url_unset");
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;
  if (!token) throw new Error("no_session");
  const headers = {
    ...(init?.headers ?? {}),
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  return fetch(`${base}${path}`, { ...init, headers });
}

/** Server-side job catalog. The SPA renders forms off `body_schema` so
 *  adding a job on the backend doesn't require a frontend redeploy. */
export function useAdminTriggerCatalog() {
  return useQuery({
    queryKey: ["admin", "triggers", "catalog"] as const,
    queryFn: async (): Promise<AdminTriggerJob[]> => {
      const res = await adminFetch("/admin/triggers");
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      const data = (await res.json()) as { jobs: AdminTriggerJob[] };
      return data.jobs;
    },
    staleTime: 10 * 60_000,
  });
}

/** POSTs an admin trigger. The backend returns 202 + a `job_id` so the
 *  SPA can poll `useAdminJobPoll(job_id)` through queued → running →
 *  ok/error without holding an HTTP connection open for minutes.
 *
 *  If the backend's audit-row insert fails it falls back to synchronous
 *  execution and returns `{job_id: null, status: "ok" | "error", result}`
 *  — callers should check `job_id` and only poll when it's non-null. */
export function useAdminTrigger() {
  return useMutation({
    mutationFn: async (args: { job: string; body?: Record<string, unknown> }): Promise<AdminTriggerAcceptedResponse> => {
      const res = await adminFetch(`/admin/trigger/${args.job}`, {
        method: "POST",
        body: JSON.stringify(args.body ?? {}),
      });
      if (res.status === 403) throw new Error("admin_required");
      if (res.status === 503) {
        const detail = await res.json().catch(() => ({ detail: "budget_exceeded" }));
        throw new Error(String((detail as { detail?: string }).detail ?? "budget_exceeded"));
      }
      if (!res.ok && res.status !== 202) throw new Error(`http_${res.status}`);
      return (await res.json()) as AdminTriggerAcceptedResponse;
    },
  });
}

/** Polls `/admin/jobs/{job_id}` every ~3s while the row is non-terminal.
 *  Stops polling the moment the job lands on `ok` or `error`, so an
 *  idle tab doesn't keep hitting Supabase after the work is done.
 *  Invalidates the corpus-health cache on successful completion so
 *  the dashboard's summary strip reflects a fresh ingest. */
export function useAdminJobPoll(jobId: string | null) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["admin", "job", jobId] as const,
    enabled: Boolean(jobId),
    refetchInterval: (q) => {
      const status = (q.state.data as { job?: AdminJobRow } | undefined)?.job?.result_status;
      if (status === "ok" || status === "error") return false;
      return 3_000;
    },
    // Keep the row cached briefly after completion so the UI can show
    // the final state without a refetch flash.
    staleTime: 10_000,
    queryFn: async (): Promise<{ ok: boolean; job: AdminJobRow }> => {
      if (!jobId) throw new Error("no_job_id");
      const res = await adminFetch(`/admin/jobs/${jobId}`);
      if (res.status === 403) throw new Error("admin_required");
      if (res.status === 404) throw new Error("job_not_found");
      if (!res.ok) throw new Error(`http_${res.status}`);
      const data = (await res.json()) as { ok: boolean; job: AdminJobRow };
      // On terminal ok, invalidate the corpus-health cache so the
      // summary strip refreshes with the just-ingested rows.
      if (data.job.result_status === "ok") {
        void qc.invalidateQueries({ queryKey: ["admin", "corpus-health"] });
        void qc.invalidateQueries({ queryKey: ["admin", "action-log"] });
      }
      return data;
    },
  });
}
