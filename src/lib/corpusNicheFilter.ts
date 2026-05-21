import { supabase } from "@/lib/supabase";

/** PostgREST query builder subset used for ``video_corpus`` niche scoping. */
export type CorpusNicheFilterableQuery = {
  eq: (column: string, value: number) => CorpusNicheFilterableQuery;
  in: (column: string, values: number[]) => CorpusNicheFilterableQuery;
};

export type VideoCorpusNicheScope = {
  /** Legacy ``niche_taxonomy.id`` — used only when junction is empty. */
  legacyNicheId?: number | null;
  /** UX ``creator_niches.id`` — used to load junction ``content_class_id`` list. */
  creatorNicheId?: number | null;
  /** Pre-resolved class ids (skip junction fetch when caller already has them). */
  contentClassIds?: number[];
};

/**
 * Junction ``content_class_id`` rows for a creator niche (two-axis browse filter).
 */
export async function fetchContentClassIdsForCreatorNiche(
  creatorNicheId: number,
): Promise<number[]> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data, error } = await (supabase as any)
    .from("creator_niche_content_classes")
    .select("content_class_id")
    .eq("creator_niche_id", creatorNicheId);
  if (error || !data) return [];
  return (data as { content_class_id: number }[]).map((r) => r.content_class_id);
}

/**
 * Class-first browse: ``content_class_id IN (...)`` when junction classes exist;
 * otherwise legacy ``niche_id`` equality (thin junction fallback only).
 */
export function applyVideoCorpusNicheFilter<T extends CorpusNicheFilterableQuery>(
  query: T,
  scope: {
    legacyNicheId?: number | null;
    contentClassIds?: number[];
  },
): T {
  const classIds = scope.contentClassIds ?? [];
  if (classIds.length > 0) {
    return query.in("content_class_id", classIds) as T;
  }
  const legacyId = scope.legacyNicheId;
  if (legacyId != null && legacyId !== 0) {
    return query.eq("niche_id", legacyId) as T;
  }
  return query;
}
