import { useMutation, useQueryClient } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { fetchWithTimeout } from "@/lib/fetchWithTimeout";
import { supabase } from "@/lib/supabase";

export type RefreshMyChannelResponse =
  | {
      status: "cached";
      last_ingest_at: string;
      stale_after_hours: number;
    }
  | {
      status: "refreshed";
      count: number;
      skipped?: number;
      failed?: number;
      last_ingest_at: string | null;
      reason?: string;
    }
  | {
      status: "error";
      reason: string;
      detail?: string;
    };

/**
 * POST `/channel/refresh-mine`. Per-handle on-demand corpus refresh —
 * closes the ~24h staleness gap from the nightly ``cron-batch-ingest``.
 *
 * Server reads the caller's ``profiles.tiktok_handle`` and
 * ``profiles.primary_niche`` and only scrapes that handle (a creator
 * can only refresh their OWN channel via this route). 18h staleness
 * gate is enforced server-side — repeated calls within the window
 * return ``status: "cached"`` without burning ED units.
 *
 * On refreshed-with-new-rows, the caller invalidates
 * ``["channel-analyze", handle]`` so the dashboard re-fetches the
 * now-fresh response.
 */
export function useRefreshMyChannel() {
  const queryClient = useQueryClient();
  return useMutation<RefreshMyChannelResponse>({
    mutationFn: async () => {
      const base = env.VITE_CLOUD_RUN_API_URL;
      if (!base) throw new Error("cloud_run_url_unset");
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error("no_session");

      const res = await fetchWithTimeout(`${base}/channel/refresh-mine`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: "{}",
        // ED scrape + Gemini analysis on up to 8 new videos can take a
        // while; allow generous timeout but the FE renders cached data
        // in parallel so the user doesn't wait on this.
        timeoutMs: 60_000,
      });
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `http_${res.status}`);
      }
      return (await res.json()) as RefreshMyChannelResponse;
    },
    onSuccess: (data) => {
      // Only invalidate the channel-analyze query when fresh rows
      // actually landed. ``cached`` and zero-count refreshes leave the
      // existing response unchanged, so re-fetching would just burn a
      // round trip without changing anything visible.
      if (data.status === "refreshed" && data.count > 0) {
        queryClient.invalidateQueries({ queryKey: ["channel-analyze"] });
      }
    },
  });
}
