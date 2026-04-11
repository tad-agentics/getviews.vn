import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/** Row shape for `trending_cards` (weekly pre-generated trend cards). */
export interface TrendingCardRow {
  id: string;
  niche_id: number;
  title: string;
  description: string;
  signal: string;
  hook_type: string | null;
  video_ids: string[] | null;
  corpus_cite: string | null;
  computed_at: string | null;
  week_of: string;
}

export function useTrendingCards(nicheId: number | null) {
  return useQuery({
    queryKey: ["trending_cards", nicheId] as const,
    queryFn: async (): Promise<TrendingCardRow[]> => {
      if (nicheId == null) return [];

      const { data, error } = await supabase
        .from("trending_cards")
        .select("*")
        .eq("niche_id", nicheId)
        .order("week_of", { ascending: false })
        .limit(30);

      if (error) {
        console.warn("[useTrendingCards]", error.message);
        return [];
      }

      const rows = (data ?? []) as TrendingCardRow[];
      if (rows.length === 0) return [];

      const latestWeek = rows[0]?.week_of;
      if (latestWeek == null) return [];

      return rows.filter((r) => r.week_of === latestWeek).slice(0, 10);
    },
    enabled: nicheId != null,
    staleTime: 30 * 60 * 1000,
  });
}
