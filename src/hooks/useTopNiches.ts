import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import {
  canonicalNicheTaxonomyId,
  creatorNicheIdForLegacyNiche,
  resolveNicheNameVn,
  RETIRED_NICHE_TAXONOMY_IDS,
} from "@/lib/profileNiches";

export type NicheWithHot = {
  id: number;
  name: string;
  /** Corpus sample size from junction ``content_class_intelligence`` rows (30d window). */
  hot: number;
};

/** Resolve taxonomy labels + aggregate class MV sample for legacy ``niche_taxonomy`` ids. */
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
      const [{ data: taxonomy, error: tErr }, { data: junction, error: jErr }, { data: cci, error: cErr }] =
        await Promise.all([
          supabase.from("niche_taxonomy").select("id, name_vn").order("name_vn"),
          supabase.from("creator_niche_content_classes").select("creator_niche_id, content_class_id"),
          supabase.from("content_class_intelligence").select("content_class_id, sample_size"),
        ]);
      if (tErr) throw tErr;
      if (jErr) throw jErr;
      if (cErr) throw cErr;

      const sampleByClass = new Map<number, number>();
      for (const row of cci ?? []) {
        if (row.content_class_id != null) {
          sampleByClass.set(row.content_class_id, row.sample_size ?? 0);
        }
      }

      const classesByCreator = new Map<number, number[]>();
      for (const row of junction ?? []) {
        const cni = row.creator_niche_id;
        const cc = row.content_class_id;
        if (cni == null || cc == null) continue;
        const list = classesByCreator.get(cni) ?? [];
        list.push(cc);
        classesByCreator.set(cni, list);
      }

      const nameBy = new Map(
        (taxonomy ?? []).map((n) => [n.id, resolveNicheNameVn(n.id, n.name_vn as string)]),
      );

      const hotForLegacy = (legacyId: number): number => {
        const creatorId = creatorNicheIdForLegacyNiche(legacyId);
        if (creatorId == null) return 0;
        const classIds = classesByCreator.get(creatorId) ?? [];
        if (classIds.length === 0) return 0;
        return classIds.reduce((sum, cc) => sum + (sampleByClass.get(cc) ?? 0), 0);
      };

      return ordered.map((id) => ({
        id,
        name: nameBy.get(id) ?? `Ngách #${id}`,
        hot: hotForLegacy(id),
      }));
    },
    enabled: ordered.length > 0,
    staleTime: 60 * 60_000,
  });
}

/** Active niches for pickers — excludes retired taxonomy ids. */
export function useTopNiches() {
  return useQuery({
    queryKey: ["niche_taxonomy", "active"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("niche_taxonomy")
        .select("id, name_vn")
        .order("name_vn");
      if (error) throw error;
      return (data ?? [])
        .filter((n) => !RETIRED_NICHE_TAXONOMY_IDS.has(n.id))
        .map((n) => ({
          id: n.id,
          name: resolveNicheNameVn(n.id, n.name_vn as string),
        }));
    },
    staleTime: 24 * 60 * 60_000,
  });
}
