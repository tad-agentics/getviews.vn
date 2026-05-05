import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import {
  canonicalNicheTaxonomyId,
  resolveNicheNameVn,
  RETIRED_NICHE_TAXONOMY_IDS,
} from "@/lib/profileNiches";

export type NicheWithHot = {
  id: number;
  name: string;
  /** Corpus sample size from `niche_intelligence` MV (30d window in current schema). */
  hot: number;
};

/** Resolve taxonomy labels + ``niche_intelligence.sample_size`` for ordered legacy ``niche_taxonomy`` ids (e.g. sidebar + Home picker). */
export function useNicheRowsForIds(ids: readonly number[] | null | undefined) {
  const seen = new Set<number>();
  const ordered: number[] = [];
  for (const raw of (ids ?? [])) {
    const id = canonicalNicheTaxonomyId(raw);
    if (!Number.isFinite(id) || seen.has(id)) continue;
    seen.add(id);
    ordered.push(id);
  }
  const key = ordered.join(",");

  return useQuery<NicheWithHot[]>({
    queryKey: ["niche_rows_for_ids", key],
    queryFn: async () => {
      if (ordered.length === 0) return [];
      const [{ data: taxonomy, error: tErr }, { data: intel, error: iErr }] = await Promise.all([
        supabase.from("niche_taxonomy").select("id, name_vn").order("name_vn"),
        supabase.from("niche_intelligence").select("niche_id, sample_size"),
      ]);
      if (tErr) throw tErr;
      if (iErr) throw iErr;
      const nameBy = new Map(
        (taxonomy ?? []).map((n) => [n.id, resolveNicheNameVn(n.id, n.name_vn as string)]),
      );
      const hotBy = new Map<number, number>();
      for (const row of intel ?? []) {
        if (row.niche_id != null) hotBy.set(row.niche_id, row.sample_size ?? 0);
      }
      return ordered.map((id) => ({
        id,
        name: nameBy.get(id) ?? `Ngách #${id}`,
        hot: hotBy.get(id) ?? 0,
      }));
    },
    enabled: ordered.length > 0,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
