import { useQuery } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

export type StarterCreator = {
  handle: string;
  display_name: string | null;
  followers: number;
  avg_views: number;
  video_count: number;
  rank: number;
};

/**
 * Onboarding step 2 — the 10 starter creators for the user's primary niche.
 * Backed by GET /home/starter-creators (cloud-run). Returns [] for users
 * without a niche yet or when the cloud-run URL isn't configured (local
 * dev); the onboarding step treats an empty list as "skip silently".
 */
export function useStarterCreators(enabled: boolean = true) {
  return useQuery<StarterCreator[]>({
    queryKey: ["home", "starter_creators"],
    queryFn: async () => {
      const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;
      if (!cloudRunUrl) return [];
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return [];
      const res = await fetch(`${cloudRunUrl}/home/starter-creators`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.status === 404) return []; // no niche set yet
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = (await res.json()) as { creators: StarterCreator[] };
      return body.creators ?? [];
    },
    enabled,
    staleTime: 30 * 60 * 1000, // creator list doesn't change within a session
    retry: false,
  });
}
