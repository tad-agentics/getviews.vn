import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";

/** PostgREST query builder subset used for ``video_corpus`` niche scoping. */
export type CorpusNicheFilterableQuery = {
  eq: (column: string, value: number) => CorpusNicheFilterableQuery;
  in: (column: string, values: number[]) => CorpusNicheFilterableQuery;
};

export type VideoCorpusNicheScope = {
  /** Legacy ``niche_taxonomy.id`` for ingest bucket (``video_corpus.niche_id``). */
  legacyNicheId?: number | null;
  /** UX ``creator_niches.id`` — used to load junction ``content_class_id`` list. */
  creatorNicheId?: number | null;
  /** Pre-resolved class ids (skip junction fetch when caller already has them). */
  contentClassIds?: number[];
};

/** Sum of ``content_class_intelligence.sample_size`` across junction classes (Phase 1 gate). */
export const CORPUS_CLASS_FIRST_MIN_AGGREGATE_SAMPLE = 20;

/**
 * Phase 4 — class-only browse (no ``niche_id`` AND) when flag on and junction non-empty.
 */
export function shouldUseClassOnlyBrowse(scope: { contentClassIds?: number[] }): boolean {
  return Boolean(env.VITE_CORPUS_BROWSE_CLASS_ONLY) && (scope.contentClassIds?.length ?? 0) > 0;
}

/**
 * Phase 1 class-first browse: env flag + junction classes + aggregate MV sample floor.
 * Phase 4 ``CLASS_ONLY`` forces class-only filter regardless of sample size.
 */
export function shouldUseClassFirstBrowse(
  scope: { contentClassIds?: number[] },
  aggregateSampleSize: number,
): boolean {
  if (shouldUseClassOnlyBrowse(scope)) return true;
  if (!env.VITE_CORPUS_BROWSE_CLASS_FIRST) return false;
  const classIds = scope.contentClassIds ?? [];
  if (classIds.length === 0) return false;
  return aggregateSampleSize >= CORPUS_CLASS_FIRST_MIN_AGGREGATE_SAMPLE;
}

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
 * Prefer ``content_class_id IN (...)`` when junction rows exist.
 *
 * Legacy path ANDs ``niche_id`` when set (lifestyle 27 vs music 28 split).
 * Class-first / class-only paths filter on ``content_class_id`` only.
 */
export function applyVideoCorpusNicheFilter<T extends CorpusNicheFilterableQuery>(
  query: T,
  scope: {
    legacyNicheId?: number | null;
    contentClassIds?: number[];
    /** Override env-derived class-first; defaults from ``shouldUseClassFirstBrowse``. */
    classFirstBrowse?: boolean;
    aggregateSampleSize?: number;
  },
): T {
  const classIds = scope.contentClassIds ?? [];
  const legacyId = scope.legacyNicheId;
  const classFirst =
    scope.classFirstBrowse ??
    shouldUseClassFirstBrowse(
      { contentClassIds: classIds },
      scope.aggregateSampleSize ?? 0,
    );

  let q = query;
  if (classFirst && classIds.length > 0) {
    return q.in("content_class_id", classIds) as T;
  }
  if (classIds.length > 0) {
    q = q.in("content_class_id", classIds) as T;
  }
  if (legacyId != null && legacyId !== 0) {
    q = q.eq("niche_id", legacyId) as T;
  }
  return q;
}
