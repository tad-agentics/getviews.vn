import { supabase } from "@/lib/supabase";

/** HI-16 carousel format buckets — junction-linked to every creator niche; topic = ``inferred_creator_niche_id``. */
export const CAROUSEL_FORMAT_CLASS_IDS = [75, 76, 77, 78, 79] as const;

/** HI-9 confidence floor — below this, browse may show loop-assigned class without inferred guard. */
export const INFERRED_TOPIC_CONFIDENCE_FLOOR = 0.6;

/** PostgREST query builder subset used for ``video_corpus`` niche scoping. */
export type CorpusNicheFilterableQuery = {
  eq: (column: string, value: number) => CorpusNicheFilterableQuery;
  in: (column: string, values: number[]) => CorpusNicheFilterableQuery;
  not: (column: string, operator: string, value: null) => CorpusNicheFilterableQuery;
  or: (filters: string) => CorpusNicheFilterableQuery;
};

export type VideoCorpusNicheScope = {
  /** Legacy ``niche_taxonomy.id`` — used only when junction is empty. */
  legacyNicheId?: number | null;
  /** UX ``creator_niches.id`` — used to load junction ``content_class_id`` list. */
  creatorNicheId?: number | null;
  /** Pre-resolved class ids (skip junction fetch when caller already has them). */
  contentClassIds?: number[];
};

export type FetchContentClassIdsOptions = {
  /** Morning Signal / ritual anchor — primary junction only. Browse keeps default false. */
  primaryOnly?: boolean;
};

/**
 * Junction ``content_class_id`` rows for a creator niche (two-axis browse filter).
 */
export async function fetchContentClassIdsForCreatorNiche(
  creatorNicheId: number,
  options?: FetchContentClassIdsOptions,
): Promise<number[]> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let query = (supabase as any)
    .from("creator_niche_content_classes")
    .select("content_class_id")
    .eq("creator_niche_id", creatorNicheId);
  if (options?.primaryOnly) {
    query = query.eq("is_primary", true);
  }
  const { data, error } = await query;
  if (error) {
    // Fail-soft to an empty set so browse falls back to unscoped rather than
    // erroring — but surface the cause: an empty result here is otherwise
    // indistinguishable from "this niche genuinely has no classes".
    if (import.meta.env.DEV) {
      console.warn("[corpusNicheFilter] junction query failed:", error.message);
    }
    return [];
  }
  if (!data) return [];
  return (data as { content_class_id: number }[]).map((r) => r.content_class_id);
}

/**
 * Carousel format classes (75–79) are shared across all UX niches. When browsing
 * a creator niche, require ``inferred_creator_niche_id`` to match so a tech
 * carousel does not appear under Âm nhạc · Vũ đạo.
 */
export function applyCarouselTopicGuard<T extends Pick<CorpusNicheFilterableQuery, "or">>(
  query: T,
  creatorNicheId: number,
): T {
  const carouselIds = CAROUSEL_FORMAT_CLASS_IDS.join(",");
  return query.or(
    `content_class_id.not.in.(${carouselIds}),inferred_creator_niche_id.eq.${creatorNicheId}`,
  ) as unknown as T;
}

/**
 * When Gemini inferred topic (``inferred_creator_niche_id``) disagrees with the
 * browse niche, hide the row unless confidence is low or inferred is missing.
 * Prevents HI-11 loop misfiles (e.g. baby vlog under BĐS ``real_estate_listing``).
 */
export function applyInferredTopicGuard<T extends Pick<CorpusNicheFilterableQuery, "or">>(
  query: T,
  creatorNicheId: number,
): T {
  const floor = INFERRED_TOPIC_CONFIDENCE_FLOOR;
  return query.or(
    `inferred_creator_niche_id.is.null,niche_resolution_confidence.is.null,niche_resolution_confidence.lt.${floor},inferred_creator_niche_id.eq.${creatorNicheId}`,
  ) as unknown as T;
}

/**
 * Class-first browse: ``content_class_id IN (...)`` when junction classes exist.
 * Phase C: no ``video_corpus.niche_id`` fallback — empty junction returns unscoped query.
 */
export function applyVideoCorpusNicheFilter<T extends CorpusNicheFilterableQuery>(
  query: T,
  scope: VideoCorpusNicheScope,
): T {
  let q = query;
  const classIds = scope.contentClassIds ?? [];
  if (classIds.length > 0) {
    q = q.in("content_class_id", classIds) as T;
  }
  if (scope.creatorNicheId != null && scope.creatorNicheId > 0) {
    q = applyCarouselTopicGuard(q, scope.creatorNicheId) as T;
    q = applyInferredTopicGuard(q, scope.creatorNicheId) as T;
  }
  return q;
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
