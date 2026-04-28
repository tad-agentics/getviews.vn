import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { RETIRED_NICHE_TAXONOMY_IDS, resolveNicheNameVn } from "@/lib/profileNiches";

export const nicheTaxonomyKeys = {
  all: () => ["niche_taxonomy"] as const,
};

export function useNicheTaxonomy() {
  return useQuery({
    queryKey: nicheTaxonomyKeys.all(),
    queryFn: async () => {
      const { data, error } = await supabase.from("niche_taxonomy").select("id, name_vn").order("name_vn");
      if (error) throw error;
      return (data ?? [])
        .filter((row) => !RETIRED_NICHE_TAXONOMY_IDS.has(row.id))
        .map((row) => ({ id: row.id, name: resolveNicheNameVn(row.id, row.name_vn) }));
    },
    staleTime: 5 * 60_000,
  });
}
