import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/** Top-K example videos in a pattern — drives the PatternCard collage strip. */
export type PatternVideo = {
  video_id: string;
  thumbnail_url: string | null;
  creator_handle: string | null;
  views: number;
  /** Canonical TikTok URL when present — helps derive embed id if ``video_id`` is not numeric. */
  tiktok_url: string | null;
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
  /** Within-niche corpus rows tagged with this pattern (the credibility number). */
  niche_video_count: number;
  /** All-time, cross-niche corpus count. Kept for the modal header copy; the
   * card no longer surfaces this directly because mixing it with niche-scoped
   * VIEW TB confused creators ("VIDEO 1 · VIEW TB 121K" reads as a sample-of-1). */
  instance_count: number;
  niche_spread: number[];
  /** Within-niche average views — denominator of ``lift`` against niche median. */
  avg_views: number | null;
  /** L2.2 Sprint 5 — niche-scoped lift over the niche median (last 30d).
   * ``null`` when the niche median is unknown or zero. Cards rank by this. */
  lift_vs_niche: number | null;
  /** Hook phrase from the most-viewed video in this pattern (display example). */
  sample_hook: string | null;
  /** Top videos in this pattern by view count, niche-scoped. Empty array when
   * no corpus rows tagged with the pattern exist in the caller's niche. */
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

/** Studio Home hook tier + ``HooksTable`` — shared cap (query key includes this). */
export const STUDIO_HOME_TOP_PATTERNS_LIMIT = 6;

/** L2.2 Sprint 5 — Tier A ("strong" credibility) gate. n≥3 niche-scoped
 *  corpus rows AND avg-views at least 1.2× the niche 30d median. */
const TIER_A_MIN_NICHE_VIDEOS = 3;
const TIER_A_MIN_LIFT = 1.2;

/** L2.2 Sprint 7b — Tier B ("early signal") gate. Requires at least 2
 *  niche-scoped videos (raised from n≥1 to avoid single-video patterns
 *  being surfaced as formulas) and lift ≥1.5× to filter anti-signal
 *  patterns. Card chrome flags these as "Tín hiệu sớm". */
const TIER_B_MIN_NICHE_VIDEOS = 2;
const TIER_B_MIN_LIFT = 1.5;

/** L2.2 Sprint 7a — safety cap on the niche-views payload. We pull every
 * 30d niche video for a true median; this cap protects the wire from a
 * runaway niche (currently the largest niche has ~600 in 30d, but a
 * future viral niche could spike). The cap is large enough that the
 * head-bias of fetching only the top-N (which inflated the "median"
 * 2-5× before this fix) is negligible at realistic niche sizes. */
const NICHE_VIEWS_MAX = 5000;

function computeMedian(values: ReadonlyArray<number>): number | null {
  const filtered = values.filter((v) => Number.isFinite(v) && v > 0);
  if (filtered.length === 0) return null;
  const sorted = [...filtered].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? sorted[mid]!
    : (sorted[mid - 1]! + sorted[mid]!) / 2;
}

/**
 * Top patterns whose niche_spread contains the user's niche, ranked by
 * within-niche lift over the niche-median view count.
 *
 * L2.2 Sprint 5 reshape — the surface answers "công thức nào đang được
 * các video viral khác trong ngách dùng" instead of "what video buckets
 * exist". Concrete shape:
 *
 *   1. ``video_patterns`` — pull the deck-synthesized rows (``structure``
 *      is non-null) whose niche_spread contains the caller. Only patterns
 *      that have a Gemini-extracted recipe are eligible — un-decked
 *      patterns have no formula to teach.
 *   2. ``video_corpus`` — niche-scoped rows tagged with one of those
 *      pattern ids (drives ``avg_views`` / ``niche_video_count`` /
 *      ``videos[]``).
 *   3. ``video_corpus`` — niche-scoped views over last 30d, top
 *      ``NICHE_MEDIAN_SAMPLE`` by views, used to compute the niche
 *      median view count (lift denominator).
 *
 * Then filter+rank: keep patterns with ``niche_video_count ≥ 3`` AND
 * ``lift_vs_niche ≥ 1.2``, sort by lift DESC.
 */
export function useTopPatterns(nicheId: number | null, limit = STUDIO_HOME_TOP_PATTERNS_LIMIT) {
  return useQuery<TopPattern[]>({
    queryKey: ["home", "top_patterns", nicheId, limit],
    queryFn: async () => {
      if (nicheId == null) return [];

      // Step 1 — eligible patterns (deck-synthesized, niche match).
      // Cap at 50 to keep the client-side niche-spread filter cheap; in
      // practice the 6-card slot fills well before that.
      const { data: patternRows, error: pErr } = await supabase
        .from("video_patterns")
        .select(
          "id, display_name, weekly_instance_count, weekly_instance_count_prev, instance_count, niche_spread, structure, why, careful, angles",
        )
        .eq("is_active", true)
        .not("structure", "is", null)
        .order("weekly_instance_count", { ascending: false })
        .limit(50);
      if (pErr) throw pErr;

      type PatternRow = TopPattern & { niche_spread?: number[] };
      const eligible = ((patternRows ?? []) as PatternRow[]).filter((r) =>
        (r.niche_spread ?? []).includes(nicheId),
      );
      if (eligible.length === 0) return [];

      const ids = eligible.map((p) => p.id);

      // Step 2 — niche-scoped corpus rows for the eligible patterns.
      const corpusPromise = supabase
        .from("video_corpus")
        .select("video_id, pattern_id, views, hook_phrase, thumbnail_url, creator_handle, tiktok_url")
        .in("pattern_id", ids)
        .eq("niche_id", nicheId);

      // Step 3 — niche median over the recent corpus (lift denominator).
      // ``views`` only — payload is a single integer per row, ~6 bytes.
      //
      // L2.2 Sprint 7a — fetch every video in the 30d window, not just the
      // top-N by views. The Sprint 5 ``NICHE_MEDIAN_SAMPLE = 200`` cap
      // combined with ``ORDER BY views DESC`` silently computed the
      // median of the top-200 head of the distribution → 2-5× higher
      // than the true niche median for any niche with ≥200 videos in
      // 30d. The 1.2× lift gate accidentally became 2.4-6× the true
      // median, hiding patterns that actually were winning. Fix is to
      // skip the order/limit-based sampling entirely and let the median
      // be computed over the actual population.
      const since30d = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      const medianPromise = supabase
        .from("video_corpus")
        .select("views")
        .eq("niche_id", nicheId)
        .gte("created_at", since30d)
        .not("views", "is", null)
        .limit(NICHE_VIEWS_MAX);

      const [corpusRes, medianRes] = await Promise.all([corpusPromise, medianPromise]);
      if (corpusRes.error) throw corpusRes.error;
      if (medianRes.error) throw medianRes.error;

      const nicheMedian = computeMedian(
        (medianRes.data ?? []).map((r) => Number((r as { views?: number | null }).views ?? 0)),
      );

      type RowAcc = {
        totalViews: number;
        n: number;
        topViews: number;
        topHook: string | null;
        rows: PatternVideo[];
      };
      const byPattern = new Map<string, RowAcc>();
      for (const row of corpusRes.data ?? []) {
        const pid = (row as { pattern_id?: string | null }).pattern_id;
        if (!pid) continue;
        const views = Number((row as { views?: number | null }).views ?? 0);
        const hook = (row as { hook_phrase?: string | null }).hook_phrase ?? null;
        const videoId = String((row as { video_id?: string | null }).video_id ?? "");
        const thumbnail = (row as { thumbnail_url?: string | null }).thumbnail_url ?? null;
        const handle = (row as { creator_handle?: string | null }).creator_handle ?? null;
        const tiktokUrl = (row as { tiktok_url?: string | null }).tiktok_url ?? null;
        const acc = byPattern.get(pid) ?? {
          totalViews: 0, n: 0, topViews: 0, topHook: null, rows: [],
        };
        acc.totalViews += views;
        acc.n += 1;
        if (views > acc.topViews) {
          acc.topViews = views;
          acc.topHook = hook;
        }
        if (videoId) {
          acc.rows.push({
            video_id: videoId,
            thumbnail_url: thumbnail,
            creator_handle: handle,
            views,
            tiktok_url: tiktokUrl,
          });
        }
        byPattern.set(pid, acc);
      }

      // Tier the patterns:
      //   Tier A — strict credibility ("đang chạy tốt"): n≥3 AND lift≥1.2×.
      //   Tier B — early signal ("tín hiệu sớm"): n≥2 AND lift≥1.5×.
      // Patterns missing both gates are dropped (no card). When ``lift`` is
      // null (niche median unknown), only Tier A's count gate applies — we
      // can't tier as "early signal" without a lift comparator, so we tier
      // by ``strong`` if n is sufficient, else drop.
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
          avgViews != null && nicheMedian != null && nicheMedian > 0
            ? avgViews / nicheMedian
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
          sample_hook: stat?.topHook ?? null,
          videos,
          tier,
          structure: (p as { structure?: string[] | null }).structure ?? null,
          why: (p as { why?: string | null }).why ?? null,
          careful: (p as { careful?: string | null }).careful ?? null,
          angles: (p as { angles?: PatternDeckAngle[] | null }).angles ?? null,
        }];
      });

      // Rank: strong tier first (sorted by lift DESC), then early tier
      // (sorted by lift DESC). Within a tier, tie-break by within-niche n
      // (more samples = more confidence).
      enriched.sort((a, b) => {
        if (a.tier !== b.tier) return a.tier === "strong" ? -1 : 1;
        const lA = a.lift_vs_niche ?? -1;
        const lB = b.lift_vs_niche ?? -1;
        if (lB !== lA) return lB - lA;
        return b.niche_video_count - a.niche_video_count;
      });

      return enriched.slice(0, limit);
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
