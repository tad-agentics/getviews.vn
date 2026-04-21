import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export type NicheWithHot = {
  id: number;
  name: string;
  /** Corpus sample size from `niche_intelligence` MV (30d window in current schema). */
  hot: number;
};

/**
 * Top niches ranked by corpus sample size (`niche_intelligence.sample_size`).
 * Feeds "Ngách của bạn" in the sidebar. Callers pass the user's primary niche id
 * so it floats to the top even if another niche has a larger sample.
 */
export function useTopNiches(primaryNicheId: number | null, limit: number | "all" = 3) {
  return useQuery<NicheWithHot[]>({
    queryKey: ["home", "top_niches", primaryNicheId, limit],
    queryFn: async () => {
      // niche_intelligence MV: `sample_size` is the stable count column (rebuilt MVs
      // dropped legacy `video_count_7d` — selecting a missing column yields HTTP 400).
      const [{ data: taxonomy, error: tErr }, { data: intel, error: iErr }] = await Promise.all([
        supabase.from("niche_taxonomy").select("id, name_vn").order("name_vn"),
        supabase.from("niche_intelligence").select("niche_id, sample_size"),
      ]);
      if (tErr) throw tErr;
      if (iErr) throw iErr;
      const hotByNiche = new Map<number, number>();
      for (const row of intel ?? []) {
        if (row.niche_id != null) hotByNiche.set(row.niche_id, row.sample_size ?? 0);
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
      return limit === "all" ? rows : rows.slice(0, limit);
    },
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
