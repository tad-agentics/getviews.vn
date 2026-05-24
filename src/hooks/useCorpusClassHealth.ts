import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { useIsAdmin } from "@/hooks/useIsAdmin";

export type AssignmentTierKey = "validated" | "low_conf" | "flagged" | "null";

export interface CorpusClassHealthRow {
  content_class_id: number;
  slug: string | null;
  name_vn: string | null;
  format_axis: string | null;
  videos_7d: number;
  videos_30d: number;
  videos_90d: number;
  viability_tier: string | null;
  daily_vpn: number | null;
  ingest_active: boolean | null;
}

export interface CorpusClassHealthResponse {
  ok: boolean;
  as_of: string;
  summary: {
    classes_total: number;
    classes_with_corpus_30d: number;
    classes_zero_corpus_30d: number;
    classes_thin_under_20: number;
    videos_7d_total: number;
    videos_30d_total: number;
    videos_90d_total: number;
    assignment_tier_histogram_30d: Record<AssignmentTierKey, number>;
    junction_miss_30d: number;
    junction_miss_rate_30d: number;
    viability_histogram: Record<string, number>;
  };
  content_classes: CorpusClassHealthRow[];
}

/** `/admin/corpus-class-health` — content_class-first corpus snapshot. */
export function useCorpusClassHealth() {
  const { isAdmin } = useIsAdmin();
  return useQuery({
    queryKey: ["admin", "corpus-class-health"] as const,
    enabled: isAdmin,
    queryFn: async (): Promise<CorpusClassHealthResponse> => {
      const base = env.VITE_CLOUD_RUN_BATCH_URL;
      if (!base) throw new Error("cloud_run_batch_url_unset");
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/corpus-class-health`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as CorpusClassHealthResponse;
    },
    staleTime: 2 * 60_000,
  });
}
