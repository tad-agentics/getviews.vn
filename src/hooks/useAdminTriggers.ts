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

/** Fires a manual batch job. Invalidates corpus-health on completion so
 *  the dashboard's summary row reflects whatever ingest just ran. */
export function useAdminTrigger() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { job: string; body?: Record<string, unknown> }): Promise<AdminTriggerResult> => {
      const res = await adminFetch(`/admin/trigger/${args.job}`, {
        method: "POST",
        body: JSON.stringify(args.body ?? {}),
      });
      if (res.status === 403) throw new Error("admin_required");
      if (res.status === 503) {
        const detail = await res.json().catch(() => ({ detail: "budget_exceeded" }));
        throw new Error(String((detail as { detail?: string }).detail ?? "budget_exceeded"));
      }
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as AdminTriggerResult;
    },
    onSuccess: () => {
      // Most triggers mutate corpus / analytics; refresh the panel that
      // reads from the same tables so the admin sees their change take
      // effect without a manual reload.
      void qc.invalidateQueries({ queryKey: ["admin", "corpus-health"] });
    },
  });
}
