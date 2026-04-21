import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export interface EnsembleCallSiteBucket {
  key: string;
  count: number;
  pct: number;
}

export interface EnsembleCallSitesResponse {
  ok: boolean;
  as_of: string;
  total: number;
  days: number;
  by_call_site: EnsembleCallSiteBucket[];
  by_endpoint: EnsembleCallSiteBucket[];
  by_request_class: EnsembleCallSiteBucket[];
}

/**
 * Per-call-site attribution of EnsembleData HTTP calls over the last N days.
 *
 * Pairs with `useEnsembleCredits` — that one tells us total units burned
 * (ED's authoritative bill), this one tells us which pipeline stage is
 * doing the burning. Keep them side by side on the dashboard so an
 * operator sees "we burned 40k units and 80% of them were
 * corpus_ingest.batch" without stitching queries together.
 */
export function useEnsembleCallSites(days = 7) {
  return useQuery({
    queryKey: ["admin", "ensemble-call-sites", days] as const,
    queryFn: async (): Promise<EnsembleCallSitesResponse> => {
      const base = env.VITE_CLOUD_RUN_API_URL;
      if (!base) throw new Error("cloud_run_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/ensemble-call-sites?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as EnsembleCallSitesResponse;
    },
    staleTime: 2 * 60_000,
  });
}
