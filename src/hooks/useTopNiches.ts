import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export type NicheWithHot = {
  id: number;
  name: string;
  hot: number; // videos in the niche in the last 7 days (from niche_intelligence)
};

/**
 * Top niches ranked by weekly video count. Feeds "Ngách của bạn" in the
 * sidebar. Callers pass the user's primary niche id so it floats to the
 * top of the list even if another niche has more videos this week.
 */
export function useTopNiches(primaryNicheId: number | null, limit = 3) {
  return useQuery<NicheWithHot[]>({
    queryKey: ["home", "top_niches", primaryNicheId, limit],
    queryFn: async () => {
      // niche_intelligence is a materialized view with video_count_7d per
      // niche. Name comes from niche_taxonomy — join via niche_id.
      const [{ data: taxonomy, error: tErr }, { data: intel, error: iErr }] = await Promise.all([
        supabase.from("niche_taxonomy").select("id, name_vn").order("name_vn"),
        supabase.from("niche_intelligence").select("niche_id, video_count_7d"),
      ]);
      if (tErr) throw tErr;
      if (iErr) throw iErr;
      const hotByNiche = new Map<number, number>();
      for (const row of intel ?? []) {
        if (row.niche_id != null) hotByNiche.set(row.niche_id, row.video_count_7d ?? 0);
      }
      const rows: NicheWithHot[] = (taxonomy ?? []).map((n) => ({
        id: n.id,
        name: n.name_vn,
        hot: hotByNiche.get(n.id) ?? 0,
      }));
      rows.sort((a, b) => {
        if (a.id === primaryNicheId) return -1;
        if (b.id === primaryNicheId) return 1;
        return b.hot - a.hot;
      });
      return rows.slice(0, limit);
    },
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
