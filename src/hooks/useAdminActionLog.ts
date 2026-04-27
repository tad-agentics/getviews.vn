import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { useIsAdmin } from "@/hooks/useIsAdmin";

export type AdminActionStatus = "queued" | "running" | "ok" | "error";

export interface AdminActionLogEntry {
  id: string;
  user_id: string | null;
  action: string;
  params_json: Record<string, unknown>;
  result_status: AdminActionStatus;
  error_message: string | null;
  duration_ms: number | null;
  result_json: Record<string, unknown> | null;
  created_at: string;
}

export interface AdminActionLogResponse {
  ok: boolean;
  entries: AdminActionLogEntry[];
}

export function useAdminActionLog(limit = 50) {
  const { isAdmin } = useIsAdmin();
  return useQuery({
    queryKey: ["admin", "action-log", limit] as const,
    enabled: isAdmin,
    queryFn: async (): Promise<AdminActionLogResponse> => {
      const base = env.VITE_CLOUD_RUN_API_URL;
      if (!base) throw new Error("cloud_run_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/action-log?limit=${limit}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as AdminActionLogResponse;
    },
    staleTime: 60_000,
  });
}
