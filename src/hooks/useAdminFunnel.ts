import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { useIsAdmin } from "@/hooks/useIsAdmin";

/**
 * GET /admin/funnel response — aggregate counts from ``usage_events`` over
 * a configurable trailing window. Backed by the batch pod (service_role
 * read), gated by ``require_admin``.
 */
export interface AdminFunnelResponse {
  ok: boolean;
  as_of: string;
  days: number;
  /** action → total count over the window */
  totals: Record<string, number>;
  /** action → distinct user count over the window */
  unique_users: Record<string, number>;
  /** top-10 actions × ISO-day string ("2026-05-07") → count */
  daily_top_actions: Record<string, Record<string, number>>;
  /** Pre-baked conversion ratios from the BE; the L2.2 panel computes
   * its own L2.2-specific ratios on top of ``totals`` to avoid coupling
   * to BE-side ratio definitions. */
  conversion: Record<string, number | null>;
}

/**
 * Queries ``/admin/funnel``. Same RLS-bypass pattern as ``useCorpusHealth``
 * — the BE walks ``usage_events`` via service_role and returns
 * pre-aggregated counts; the FE never sees raw event rows.
 *
 * Cached for 60s. The window param re-keys the cache so toggling between
 * 7d / 14d / 30d doesn't hit the BE on every flip.
 */
export function useAdminFunnel(days: number = 7) {
  const { isAdmin } = useIsAdmin();
  return useQuery({
    queryKey: ["admin", "funnel", days] as const,
    enabled: isAdmin,
    queryFn: async (): Promise<AdminFunnelResponse> => {
      const base = env.VITE_CLOUD_RUN_BATCH_URL;
      if (!base) throw new Error("cloud_run_batch_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/funnel?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as AdminFunnelResponse;
    },
    staleTime: 60_000,
  });
}
