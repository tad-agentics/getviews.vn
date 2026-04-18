import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export type BreakoutVideo = {
  video_id: string;
  tiktok_url: string;
  thumbnail_url: string | null;
  creator_handle: string;
  views: number;
  breakout_multiplier: number | null;
  hook_phrase: string | null;
  hook_type: string | null;
};

/**
 * Top breakout videos in the user's niche over the last 14 days. Ranked by
 * breakout_multiplier. Feeds BreakoutGrid (3-tile row) on the Home screen.
 */
export function useTopBreakouts(nicheId: number | null, limit = 3) {
  return useQuery<BreakoutVideo[]>({
    queryKey: ["home", "top_breakouts", nicheId, limit],
    queryFn: async () => {
      if (nicheId == null) return [];
      const since = new Date(Date.now() - 14 * 24 * 3600 * 1000).toISOString();
      const { data, error } = await supabase
        .from("video_corpus")
        .select(
          "video_id, tiktok_url, thumbnail_url, creator_handle, views, breakout_multiplier, hook_phrase, hook_type",
        )
        .eq("niche_id", nicheId)
        .gte("created_at", since)
        .not("breakout_multiplier", "is", null)
        .order("breakout_multiplier", { ascending: false })
        .limit(limit);
      if (error) throw error;
      return (data ?? []) as BreakoutVideo[];
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
