import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { useIsAdmin } from "@/hooks/useIsAdmin";

export type ClaimTier =
  | "none"
  | "reference_pool"
  | "basic_citation"
  | "niche_norms"
  | "hook_effectiveness"
  | "trend_delta";

export interface CorpusHealthNicheRow {
  niche_id: number;
  name_en: string | null;
  name_vn: string | null;
  videos_7d: number;
  videos_30d: number;
  videos_90d: number;
  last_ingest_at: string | null;
  claim_tiers: Record<ClaimTier, boolean>;
  highest_passing_tier: ClaimTier;
}

export interface CorpusHealthResponse {
  ok: boolean;
  as_of: string;
  summary: {
    niches_total: number;
    videos_7d_total: number;
    videos_30d_total: number;
    videos_90d_total: number;
    tier_histogram: Record<ClaimTier, number>;
  };
  niches: CorpusHealthNicheRow[];
}

/**
 * Queries the `/admin/corpus-health` Cloud Run endpoint. Gated server-side
 * by `require_admin`; this hook fails closed with an error if the caller's
 * profile doesn't have `is_admin = true`. Cached for 2 minutes — the
 * underlying video_corpus aggregation is cheap (~700 rows in Python) but
 * running it on every focus-refetch is wasteful.
 */
export function useCorpusHealth() {
  const { isAdmin } = useIsAdmin();
  return useQuery({
    queryKey: ["admin", "corpus-health"] as const,
    enabled: isAdmin,
    queryFn: async (): Promise<CorpusHealthResponse> => {
      const base = env.VITE_CLOUD_RUN_BATCH_URL;
      if (!base) throw new Error("cloud_run_batch_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/corpus-health`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as CorpusHealthResponse;
    },
    staleTime: 2 * 60_000,
  });
}
