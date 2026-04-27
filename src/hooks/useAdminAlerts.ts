import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { useIsAdmin } from "@/hooks/useIsAdmin";

export type AlertSeverity = "info" | "warn" | "crit";
export type AlertPhase = "firing" | "cleared";

export interface AlertFire {
  id: string;
  rule_key: string;
  severity: AlertSeverity;
  message: string;
  context_json: Record<string, unknown>;
  phase: AlertPhase;
  delivered_at: string | null;
  created_at: string;
}

export interface AdminAlertFiresResponse {
  ok: boolean;
  fires: AlertFire[];
}

export function useAdminAlertFires(limit = 20) {
  const { isAdmin } = useIsAdmin();
  return useQuery({
    queryKey: ["admin", "alert-fires", limit] as const,
    enabled: isAdmin,
    queryFn: async (): Promise<AdminAlertFiresResponse> => {
      const base = env.VITE_CLOUD_RUN_API_URL;
      if (!base) throw new Error("cloud_run_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/alert-fires?limit=${limit}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as AdminAlertFiresResponse;
    },
    staleTime: 60_000,
  });
}
