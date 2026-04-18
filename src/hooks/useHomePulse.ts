import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export type PulseStats = {
  niche_id: number;
  views_this_week: number;
  views_last_week: number;
  views_delta_pct: number;
  videos_this_week: number;
  new_creators_this_week: number;
  viral_count_this_week: number;
  new_hooks_this_week: number;
  top_hook_name: string | null;
  adequacy:
    | "none" | "reference_pool" | "basic_citation"
    | "niche_norms" | "hook_effectiveness" | "trend_delta";
  as_of: string;
};

/** GET /home/pulse — 6 numbers + adequacy tier for the user's niche. */
export function useHomePulse(enabled = true) {
  return useQuery<PulseStats | null>({
    queryKey: ["home", "pulse"],
    queryFn: async () => {
      const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;
      if (!cloudRunUrl) return null;
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return null;
      const res = await fetch(`${cloudRunUrl}/home/pulse`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.status === 404) return null;
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return (await res.json()) as PulseStats;
    },
    enabled,
    staleTime: 60 * 60 * 1000, // 1h — pulse is a morning-coffee read
    retry: false,
  });
}
