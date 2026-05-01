import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { useIsAdmin } from "@/hooks/useIsAdmin";

export interface Layer0Run {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  duration_ms: number | null;
  summary: Record<string, unknown> | null;
  error: string | null;
}

export interface Layer0Candidate {
  id: number;
  hashtag: string;
  occurrences: number;
  avg_views: number | null;
  discovery_date: string | null;
  sample_video_ids: string[] | null;
  notes: string | null;
  assigned_niche_id: number | null;
}

export interface Layer0NicheFreshness {
  niche_id: number;
  name_vn: string | null;
  name_en: string | null;
  signal_count: number;
  stale_count: number;
  last_hashtag_refresh: string | null;
}

export interface Layer0HealthSummary {
  last_run_at: string | null;
  last_run_status: string | null;
  last_run_duration_ms: number | null;
  pending_review_count: number;
  hashtag_map_size: number;
  niches_with_stale_signals: number;
  niches_total: number;
}

export interface AdminLayer0Response {
  ok: boolean;
  as_of: string;
  summary: Layer0HealthSummary;
  recent_runs: Layer0Run[];
  pending_candidates: Layer0Candidate[];
  niches: Layer0NicheFreshness[];
}

/**
 * Fetches the `/admin/layer0-health` snapshot. Layer0 is the
 * hashtag-discovery loop that feeds new candidate hashtags into
 * `niche_taxonomy.signal_hashtags` and `hashtag_niche_map`. Operators
 * use this to spot stale-signal niches and triage `niche_candidates`
 * awaiting human review.
 */
export function useAdminLayer0() {
  const { isAdmin } = useIsAdmin();
  return useQuery({
    queryKey: ["admin", "layer0-health"] as const,
    enabled: isAdmin,
    queryFn: async (): Promise<AdminLayer0Response> => {
      const base = env.VITE_CLOUD_RUN_BATCH_URL;
      if (!base) throw new Error("cloud_run_batch_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/layer0-health`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as AdminLayer0Response;
    },
    staleTime: 2 * 60_000,
  });
}
