import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { useIsAdmin } from "@/hooks/useIsAdmin";

export interface Hi13GeminiCallsWindow {
  count: number;
  cost_usd: number;
}

export interface Hi13RunRow {
  job_name: string;
  started_at: string | null;
  finished_at: string | null;
  status: string | null;
  duration_ms: number | null;
  error: string | null;
  hi13: {
    batch_line_ok: number;
    batch_line_fail: number;
    sync_fallback: number;
    batch_jobs_ok: number;
    batch_jobs_failed: number;
  };
  batch_line_hits: number;
  sync_fallback: number;
  skipped_duplicate_run?: boolean;
}

export interface Hi13BatchHealthResponse {
  ok: boolean;
  as_of: string;
  config: {
    enabled: boolean;
    poll_interval_s: number;
    poll_max_s: number;
  };
  gemini_calls: {
    batch_7d: Hi13GeminiCallsWindow;
    batch_30d: Hi13GeminiCallsWindow;
    sync_extraction_7d: Hi13GeminiCallsWindow;
    sync_extraction_30d: Hi13GeminiCallsWindow;
    batch_tier_share_7d: number | null;
    batch_tier_share_30d: number | null;
  };
  ingest_30d: {
    runs: number;
    batch_line_ok: number;
    batch_line_fail: number;
    sync_fallback: number;
    batch_jobs_ok: number;
    batch_jobs_failed: number;
    batch_line_success_rate: number;
    batch_path_share: number | null;
    batch_path_share_target: number;
  };
  recent_runs: Hi13RunRow[];
}

/** `/admin/hi13-batch-health` — HI-13 Batch API observability. */
export function useHi13BatchHealth() {
  const { isAdmin } = useIsAdmin();
  return useQuery({
    queryKey: ["admin", "hi13-batch-health"] as const,
    enabled: isAdmin,
    queryFn: async (): Promise<Hi13BatchHealthResponse> => {
      const base = env.VITE_CLOUD_RUN_BATCH_URL;
      if (!base) throw new Error("cloud_run_batch_url_unset");
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");
      const res = await fetch(`${base}/admin/hi13-batch-health`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("admin_required");
      if (!res.ok) throw new Error(`http_${res.status}`);
      return (await res.json()) as Hi13BatchHealthResponse;
    },
    staleTime: 2 * 60_000,
  });
}
