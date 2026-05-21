import { supabase } from "@/lib/supabase";

/** PostgREST query builder subset used for ``video_corpus`` niche scoping. */
export type CorpusNicheFilterableQuery = {
  eq: (column: string, value: number) => CorpusNicheFilterableQuery;
  in: (column: string, values: number[]) => CorpusNicheFilterableQuery;
  not: (column: string, operator: string, value: null) => CorpusNicheFilterableQuery;
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
 * Class-first browse: ``content_class_id IN (...)`` when junction classes exist.
 * Phase C: no ``video_corpus.niche_id`` fallback — empty junction returns unscoped query.
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
  return query;
}

/**
 * Browse-only filter: hide corpus rows with no stable thumbnail (NULL after
 * backfill). Keeps analysis/matcher rows in DB; Explore grid, Home breakouts,
 * and browse counts use this. Do not apply to thin-corpus / intel sample checks.
 */
export function applyBrowsableCorpusFilter<T extends Pick<CorpusNicheFilterableQuery, "not">>(
  query: T,
): T {
  return query.not("thumbnail_url", "is", null) as unknown as T;
}
