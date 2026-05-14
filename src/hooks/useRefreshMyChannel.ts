import { useMutation, useQueryClient } from "@tanstack/react-query";
import { readErrorDetail } from "@/lib/cloudRunErrors";
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
 * Server reads the caller's ``profiles.tiktok_handle`` and profile niche scope
 * (post-PR6: ``creator_niche_id`` / legacy corpus id) and only scrapes that handle (a creator
 * can only refresh their OWN channel via this route). 18h staleness
 * gate is enforced server-side — repeated calls within the window
 * return ``status: "cached"`` without burning ED units.
 *
 * On refreshed-with-new-rows, the caller invalidates
 * ``["channel-diagnose"]`` so the dashboard re-fetches the
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
        let detail: string;
        try {
          detail = await readErrorDetail(res);
        } catch (err: unknown) {
          console.warn(
            `[useRefreshMyChannel] failed to read response body for http_${res.status}:`,
            err,
          );
          detail = "";
        }
        throw new Error(detail || `http_${res.status}`);
      }
      return (await res.json()) as RefreshMyChannelResponse;
    },
    onSuccess: (data) => {
      // Only invalidate when fresh rows actually landed — cached / zero-count
      // refreshes leave the existing response unchanged.
      if (data.status === "refreshed" && data.count > 0) {
        queryClient.invalidateQueries({ queryKey: ["channel-diagnose"] });
      }
    },
  });
}
