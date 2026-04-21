import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export interface EnsembleHistoryEntry {
  date: string | null;
  endpoint: string | null;
  units: number;
  count: number | null;
}

export interface EnsembleHistoryResponse {
  ok: boolean;
  as_of: string;
  days: number;
  entries: EnsembleHistoryEntry[];
  /** EnsembleData's raw response body — escape hatch when upstream
   *  ships a new shape the normaliser doesn't recognise. Renders
   *  collapsed in the panel so the operator can still read it. */
  raw: unknown;
}

/**
 * Per-endpoint usage history from EnsembleData's own /customer/get-history
 * endpoint. Authoritative (their source of truth) — pair with the local
 * `useEnsembleCallSites` hook to verify our attribution table captures
 * every call. Divergence signals a helper forgot `ed_call_site()`.
 *
 * Cached client-side for 2 minutes; server-side for 5 minutes per
 * (days) bucket. Ops don't need sub-minute freshness here.
 */
export function useEnsembleHistory(days = 10) {
  return useQuery({
    queryKey: ["admin", "ensemble-history", days] as const,
    queryFn: async (): Promise<EnsembleHistoryResponse> => {
      const base = env.VITE_CLOUD_RUN_API_URL;
      if (!base) throw new Error("cloud_run_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/ensemble-history?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (res.status === 503) throw new Error("ensemble_token_unset");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as EnsembleHistoryResponse;
    },
    staleTime: 2 * 60_000,
  });
}
