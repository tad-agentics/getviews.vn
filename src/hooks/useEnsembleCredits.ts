import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { useIsAdmin } from "@/hooks/useIsAdmin";

export interface EnsembleDailyUnits {
  date: string;
  units: number;
  ok: boolean;
  error?: string;
}

export interface EnsembleCreditsResponse {
  ok: boolean;
  as_of: string;
  monthly_budget: number | null;
  days: EnsembleDailyUnits[];
}

/**
 * Per-UTC-day EnsembleData "units used" for the last N days, proxied
 * through `/admin/ensemble-credits` so the API token never leaves the
 * server. The backend caches each date for 5 minutes and fails open
 * per-day (partial outages stay partially useful).
 *
 * `monthly_budget` is the configured `ED_MONTHLY_UNIT_BUDGET` env var —
 * null means "not set", and the panel hides remainder math in that case.
 */
export function useEnsembleCredits(days = 14) {
  const { isAdmin } = useIsAdmin();
  return useQuery({
    queryKey: ["admin", "ensemble-credits", days] as const,
    enabled: isAdmin,
    queryFn: async (): Promise<EnsembleCreditsResponse> => {
      const base = env.VITE_CLOUD_RUN_API_URL;
      if (!base) throw new Error("cloud_run_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/ensemble-credits?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (res.status === 503) throw new Error("ensemble_token_unset");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as EnsembleCreditsResponse;
    },
    staleTime: 2 * 60_000,
  });
}
