import { useQuery } from "@tanstack/react-query";
import { applyVideoCorpusNicheFilter } from "@/lib/corpusNicheFilter";
import { supabase } from "@/lib/supabase";
import { normalizeHookPhrase } from "@/lib/patternDisplay";

/** Top-K example videos in a pattern — drives the PatternCard collage strip. */
export type PatternVideo = {
  video_id: string;
  thumbnail_url: string | null;
  creator_handle: string | null;
  views: number;
  /** Canonical TikTok URL when present — helps derive embed id if ``video_id`` is not numeric. */
  tiktok_url: string | null;
  content_type?: "video" | "carousel" | null;
};

/** Single content angle inside a pattern (PatternModal "GÓC CÒN TRỐNG"). */
export type PatternDeckAngle = {
  angle: string;
  filled: number;
  /** ``true`` when no creator has covered this angle yet. */
  gap: boolean;
};

export type TopPattern = {
  id: string;
  display_name: string;
  weekly_instance_count: number;
  weekly_instance_count_prev: number;
  /** Within-scope corpus rows tagged with this pattern (the credibility number). */
  niche_video_count: number;
  /** All-time, cross-niche corpus count. Kept for the modal header copy; the
   * card no longer surfaces this directly because mixing it with niche-scoped
   * VIEW TB confused creators ("VIDEO 1 · VIEW TB 121K" reads as a sample-of-1). */
  instance_count: number;
  niche_spread: number[];
  /** Within-scope average views — denominator of ``lift`` against cohort median. */
  avg_views: number | null;
  /** L2.2 Sprint 5 — scoped lift over the cohort median (last 30d).
   * ``null`` when the median is unknown or zero. Cards rank by this. */
  lift_vs_niche: number | null;
  /** Hook phrase from the most-viewed video in this pattern (display example). */
  sample_hook: string | null;
  /** Creator on the highest-view scoped video — for VÍ DỤ when hook_phrase missing. */
  sample_creator_handle?: string | null;
  /** Top videos in this pattern by view count, scope-scoped. Empty array when
   * no corpus rows tagged with the pattern exist in the caller's scope. */
  videos: PatternVideo[];
  /** L2.2 Sprint 7b — credibility tier the card was admitted under.
   *  - ``"strong"`` — n≥3 AND lift≥1.2× (the original Sprint 5 strict gate).
   *    Card renders with the green ``↑ {lift}× ngách`` badge.
   *  - ``"early"`` — n≥2 AND lift≥1.5× (raised from n≥1 to avoid single-video
   *    anti-signal patterns out). Card renders with a yellow "Tín hiệu sớm"
   *    badge so creators know it's a smaller-sample observation, not a
   *    credible "đang chạy tốt" claim. */
  tier: "strong" | "early";
  /**
   * Deck content synthesized by ``pattern_deck_synth.py`` (nightly).
   * All four fields are ``null`` until the cron has run for this
   * pattern; the card filters un-decked patterns out (no formula = no
   * card) so any ``TopPattern`` reaching the FE has a real recipe.
   */
  structure: string[] | null;
  why: string | null;
  careful: string | null;
  angles: PatternDeckAngle[] | null;
};

/** Class-first scope for pattern ranking (Round B — content_class pivot). */
export type TopPatternsScope = {
  contentClassIds: number[];
  /** UX ``creator_niches.id`` — carousel topic guard on pattern sample videos. */
  creatorNicheId?: number | null;
  /** Thin fallback when junction has no classes (legacy ingest bucket). */
  legacyNicheId?: number | null;
};

/** Studio Home hook tier + ``HooksTable`` — shared cap (query key includes this). */
export const STUDIO_HOME_TOP_PATTERNS_LIMIT = 6;

/** L2.2 Sprint 5 — Tier A ("strong" credibility) gate. n≥3 scoped
 *  corpus rows AND avg-views at least 1.2× the cohort 30d median. */
const TIER_A_MIN_NICHE_VIDEOS = 3;
const TIER_A_MIN_LIFT = 1.2;

/** L2.2 Sprint 7b — Tier B ("early signal") gate. Requires at least 2
 *  scoped videos (raised from n≥1 to avoid single-video patterns
 *  being surfaced as formulas) and lift ≥1.5× to filter anti-signal
 *  patterns. Card chrome flags these as "Tín hiệu sớm". */
const TIER_B_MIN_NICHE_VIDEOS = 2;
const TIER_B_MIN_LIFT = 1.5;

/** Safety cap on the views payload for median computation. */
const COHORT_VIEWS_MAX = 5000;

const PATTERN_PREFETCH_LIMIT = 50;

function computeMedian(values: ReadonlyArray<number>): number | null {
  const filtered = values.filter((v) => Number.isFinite(v) && v > 0);
  if (filtered.length === 0) return null;
  const sorted = [...filtered].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? sorted[mid]!
    : (sorted[mid - 1]! + sorted[mid]!) / 2;
}

function scopeQueryKey(scope: TopPatternsScope): string {
  const classes = [...scope.contentClassIds].sort((a, b) => a - b).join(",");
  return `c:${classes}|cn:${scope.creatorNicheId ?? ""}|n:${scope.legacyNicheId ?? ""}`;
}

function applyCorpusScope<T extends { eq: (col: string, val: number) => T; in: (col: string, val: number[]) => T; not: (col: string, op: string, val: null) => T; or: (filters: string) => T }>(
  query: T,
  scope: TopPatternsScope,
): T {
  return applyVideoCorpusNicheFilter(query, {
    contentClassIds: scope.contentClassIds,
    creatorNicheId: scope.creatorNicheId,
    legacyNicheId: scope.legacyNicheId,
  });
}

type PatternRow = TopPattern & { niche_spread?: number[] };

async function fetchEligiblePatterns(
  scope: TopPatternsScope,
  classFirst: boolean,
): Promise<PatternRow[]> {
  if (classFirst) {
    let idQuery = supabase
      .from("video_corpus")
      .select("pattern_id")
      .not("pattern_id", "is", null);
    idQuery = applyCorpusScope(idQuery, scope);
    const { data: idRows, error: idErr } = await idQuery.limit(500);
    if (idErr) throw idErr;
    const patternIds = [
      ...new Set(
        (idRows ?? [])
          .map((r) => (r as { pattern_id?: string | null }).pattern_id)
          .filter((id): id is string => Boolean(id)),
      ),
    ];
    if (patternIds.length === 0) return [];

    const { data: patternRows, error: pErr } = await supabase
      .from("video_patterns")
      .select(
        "id, display_name, weekly_instance_count, weekly_instance_count_prev, instance_count, niche_spread, structure, why, careful, angles",
      )
      .eq("is_active", true)
      .not("structure", "is", null)
      .in("id", patternIds.slice(0, PATTERN_PREFETCH_LIMIT))
      .order("weekly_instance_count", { ascending: false })
      .limit(PATTERN_PREFETCH_LIMIT);
    if (pErr) throw pErr;
    return (patternRows ?? []) as PatternRow[];
  }

  const legacyId = scope.legacyNicheId;
  if (legacyId == null) return [];

  const { data: patternRows, error: pErr } = await supabase
    .from("video_patterns")
    .select(
      "id, display_name, weekly_instance_count, weekly_instance_count_prev, instance_count, niche_spread, structure, why, careful, angles",
    )
    .eq("is_active", true)
    .not("structure", "is", null)
    .order("weekly_instance_count", { ascending: false })
    .limit(PATTERN_PREFETCH_LIMIT);
  if (pErr) throw pErr;

  return ((patternRows ?? []) as PatternRow[]).filter((r) =>
    (r.niche_spread ?? []).includes(legacyId),
  );
}

/**
 * Top patterns ranked by within-scope lift over the cohort median view count.
 *
 * Class-first (Round B): filters ``video_corpus`` by junction
 * ``content_class_id`` list. Legacy fallback (empty junction): uses
 * ``niche_spread`` + ``video_corpus.niche_id`` until the column is dropped.
 */
export function useTopPatterns(scope: TopPatternsScope | null, limit = STUDIO_HOME_TOP_PATTERNS_LIMIT) {
  const classFirst = (scope?.contentClassIds.length ?? 0) > 0;

  return useQuery<TopPattern[]>({
    queryKey: ["home", "top_patterns", scope ? scopeQueryKey(scope) : null, limit],
    queryFn: async () => {
      if (scope == null) return [];
      if (scope.contentClassIds.length === 0 && scope.legacyNicheId == null) return [];

      const eligible = await fetchEligiblePatterns(scope, classFirst);
      if (eligible.length === 0) return [];

      const ids = eligible.map((p) => p.id);
      const since30d = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

      let corpusQuery = supabase
        .from("video_corpus")
        .select("video_id, pattern_id, views, hook_phrase, thumbnail_url, creator_handle, tiktok_url, content_type")
        .in("pattern_id", ids);
      corpusQuery = applyCorpusScope(corpusQuery, scope);

      let medianQuery = supabase
        .from("video_corpus")
        .select("views")
        .gte("created_at", since30d)
        .not("views", "is", null)
        .limit(COHORT_VIEWS_MAX);
      medianQuery = applyCorpusScope(medianQuery, scope);

      const [corpusRes, medianRes] = await Promise.all([corpusQuery, medianQuery]);
      if (corpusRes.error) throw corpusRes.error;
      if (medianRes.error) throw medianRes.error;

      const cohortMedian = computeMedian(
        (medianRes.data ?? []).map((r) => Number((r as { views?: number | null }).views ?? 0)),
      );

      type RowAcc = {
        totalViews: number;
        n: number;
        topViews: number;
        topHookViews: number;
        sampleHook: string | null;
        topCreatorViews: number;
        topCreatorHandle: string | null;
        rows: PatternVideo[];
      };
      const byPattern = new Map<string, RowAcc>();
      for (const row of corpusRes.data ?? []) {
        const pid = (row as { pattern_id?: string | null }).pattern_id;
        if (!pid) continue;
        const views = Number((row as { views?: number | null }).views ?? 0);
        const hook = normalizeHookPhrase((row as { hook_phrase?: string | null }).hook_phrase);
        const videoId = String((row as { video_id?: string | null }).video_id ?? "");
        const thumbnail = (row as { thumbnail_url?: string | null }).thumbnail_url ?? null;
        const handle = (row as { creator_handle?: string | null }).creator_handle ?? null;
        const tiktokUrl = (row as { tiktok_url?: string | null }).tiktok_url ?? null;
        const contentType = (row as { content_type?: "video" | "carousel" | null }).content_type ?? null;
        const acc = byPattern.get(pid) ?? {
          totalViews: 0,
          n: 0,
          topViews: 0,
          topHookViews: -1,
          sampleHook: null,
          topCreatorViews: -1,
          topCreatorHandle: null,
          rows: [],
        };
        acc.totalViews += views;
        acc.n += 1;
        if (views > acc.topViews) acc.topViews = views;
        if (hook && views >= acc.topHookViews) {
          acc.topHookViews = views;
          acc.sampleHook = hook;
        }
        const cleanHandle = handle?.trim();
        if (cleanHandle && views >= acc.topCreatorViews) {
          acc.topCreatorViews = views;
          acc.topCreatorHandle = cleanHandle;
        }
        if (videoId && thumbnail?.trim()) {
          acc.rows.push({
            video_id: videoId,
            thumbnail_url: thumbnail,
            creator_handle: handle,
            views,
            tiktok_url: tiktokUrl,
            content_type: contentType,
          });
        }
        byPattern.set(pid, acc);
      }

      type Tier = "strong" | "early" | null;
      const tierOf = (n: number, lift: number | null): Tier => {
        if (lift == null) return n >= TIER_A_MIN_NICHE_VIDEOS ? "strong" : null;
        if (n >= TIER_A_MIN_NICHE_VIDEOS && lift >= TIER_A_MIN_LIFT) return "strong";
        if (n >= TIER_B_MIN_NICHE_VIDEOS && lift >= TIER_B_MIN_LIFT) return "early";
        return null;
      };

      const enriched = eligible.flatMap((p) => {
        const stat = byPattern.get(p.id);
        const n = stat?.n ?? 0;
        const avgViews = stat && stat.n > 0 ? Math.round(stat.totalViews / stat.n) : null;
        const lift =
          avgViews != null && cohortMedian != null && cohortMedian > 0
            ? avgViews / cohortMedian
            : null;
        const tier = tierOf(n, lift);
        if (tier == null) return [];
        const videos = stat
          ? [...stat.rows].sort((a, b) => b.views - a.views).slice(0, 4)
          : [];
        return [{
          ...p,
          niche_video_count: n,
          avg_views: avgViews,
          lift_vs_niche: lift,
          sample_hook: stat?.sampleHook ?? null,
          sample_creator_handle: stat?.topCreatorHandle ?? null,
          videos,
          tier,
          structure: (p as { structure?: string[] | null }).structure ?? null,
          why: (p as { why?: string | null }).why ?? null,
          careful: (p as { careful?: string | null }).careful ?? null,
          angles: (p as { angles?: PatternDeckAngle[] | null }).angles ?? null,
        }];
      });

      enriched.sort((a, b) => {
        if (a.tier !== b.tier) return a.tier === "strong" ? -1 : 1;
        const lA = a.lift_vs_niche ?? -1;
        const lB = b.lift_vs_niche ?? -1;
        if (lB !== lA) return lB - lA;
        return b.niche_video_count - a.niche_video_count;
      });

      const deduped: TopPattern[] = [];
      const seenFormulas = new Set<string>();
      for (const p of enriched) {
        // Card/modal need at least one corpus row with a displayable thumbnail.
        if (p.videos.length === 0) continue;
        const key = (p.display_name?.trim() || p.id).toLowerCase();
        if (seenFormulas.has(key)) continue;
        seenFormulas.add(key);
        deduped.push(p);
        if (deduped.length >= limit) break;
      }

      return deduped;
    },
    enabled:
      scope != null &&
      (scope.contentClassIds.length > 0 || scope.legacyNicheId != null),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
