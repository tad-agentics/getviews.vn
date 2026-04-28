import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import {
  canonicalNicheTaxonomyId,
  normalizeNicheIds,
  resolveNicheNameVn,
  RETIRED_NICHE_TAXONOMY_IDS,
} from "@/lib/profileNiches";

export type NicheWithHot = {
  id: number;
  name: string;
  /** Corpus sample size from `niche_intelligence` MV (30d window in current schema). */
  hot: number;
};

/**
 * Top niches ranked by corpus sample size (`niche_intelligence.sample_size`).
 * Feeds "Ngách của bạn" in the sidebar. Callers pass a preferred id (e.g. first
 * pick) so it floats to the top even if another niche has a larger sample.
 */
export function useTopNiches(preferNicheId: number | null, limit: number | "all" = 3) {
  return useQuery<NicheWithHot[]>({
    queryKey: ["home", "top_niches", preferNicheId, limit],
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
      const rows: NicheWithHot[] = (taxonomy ?? [])
        .filter((n) => !RETIRED_NICHE_TAXONOMY_IDS.has(n.id))
        .map((n) => ({
          id: n.id,
          name: resolveNicheNameVn(n.id, n.name_vn),
          hot: hotByNiche.get(n.id) ?? 0,
        }));
      rows.sort((a, b) => {
        if (a.id === preferNicheId) return -1;
        if (b.id === preferNicheId) return 1;
        return b.hot - a.hot;
      });
      return limit === "all" ? rows : rows.slice(0, limit);
    },
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}

/** Sidebar: resolve taxonomy names + hot counts for an ordered list of niche ids (max 3 typical). */
export function useNicheRowsForIds(ids: readonly number[] | null | undefined) {
  const ordered = normalizeNicheIds((ids ?? []).map(canonicalNicheTaxonomyId)).slice(0, 3);
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
