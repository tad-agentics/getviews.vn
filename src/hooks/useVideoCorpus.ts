import { useInfiniteQuery } from "@tanstack/react-query";
import {
  applyBrowsableCorpusFilter,
  applyVideoCorpusNicheFilter,
} from "@/lib/corpusNicheFilter";
import { supabase } from "@/lib/supabase";

const PAGE_SIZE = 20;

export interface VideoCorpusFilters {
  nicheId?: number | null;
  /** Two-axis junction filter — class-only when non-empty. */
  contentClassIds?: number[];
  sortBy?: "views" | "engagement_rate" | "indexed_at";
  sortOrder?: "asc" | "desc";
  dateFrom?: string | null;
  dateTo?: string | null;
  search?: string;
  minViews?: number;
  contentFormat?: string;
  /** F6 Kho — ED metadata promoted @ ingest (utilization Wave 2 A). */
  stitchOnly?: boolean;
  duetOnly?: boolean;
}

export const corpusKeys = {
  all: () => ["video_corpus"] as const,
  list: (filters: VideoCorpusFilters) => ["video_corpus", "list", filters] as const,
  detail: (id: string) => ["video_corpus", "detail", id] as const,
  related: (videoId: string, nicheId: number) => ["video_corpus", "related", videoId, nicheId] as const,
  /** Top videos by views for a niche — powers the lg+ breakout sidebar on /app/trends. */
  breakout: (nicheId: number | null) => ["video_corpus", "breakout", nicheId] as const,
  /** Head-only count of rows matching the active filter combo. Used for the
   *  filter chip's "N kết quả" affordance without paying for a full fetch. */
  count: (
    filters: Pick<
      VideoCorpusFilters,
      "nicheId" | "contentClassIds" | "search" | "minViews" | "contentFormat" | "stitchOnly" | "duetOnly"
    >,
  ) => ["video_corpus", "count", filters] as const,
  /** All indexed videos for a niche — no search / views / format filters (hero, trust). */
  nicheTotal: (nicheId: number | null) => ["video_corpus", "niche_total", nicheId] as const,
  /** Videos indexed in the rolling last 7 days for a niche (hero H1). */
  nicheLast7d: (nicheId: number | null) => ["video_corpus", "niche_last7d", nicheId] as const,
};

export function useVideoCorpus(filters: VideoCorpusFilters = {}) {
  const {
    nicheId,
    contentClassIds,
    sortBy = "indexed_at",
    sortOrder = "desc",
    dateFrom,
    dateTo,
    search,
    minViews,
    contentFormat,
    stitchOnly,
    duetOnly,
  } = filters;

  return useInfiniteQuery({
    queryKey: corpusKeys.list(filters),
    queryFn: async ({ pageParam = 0 }) => {
      let query = supabase.from("video_corpus").select(
        "id, video_id, tiktok_url, video_url, thumbnail_url, creator_handle, views, engagement_rate, content_type, content_format, content_class_id, ingest_loop_niche_id, indexed_at, likes, shares, comments, hook_phrase, breakout_multiplier, tone, cta_type, is_commerce, sound_name, creator_tier, posting_hour, video_duration, is_stitch, is_duet",
      );

      query = applyBrowsableCorpusFilter(
        applyVideoCorpusNicheFilter(query, {
          legacyNicheId: nicheId,
          contentClassIds,
        }),
      );
      if (dateFrom) {
        query = query.gte("indexed_at", dateFrom);
      }
      if (dateTo) {
        query = query.lte("indexed_at", dateTo);
      }
      if (search && search.trim().length > 0) {
        query = query.textSearch("search_vector", search.trim(), {
          config: "simple",
          type: "plain",
        });
      }
      if (minViews != null && minViews > 0) {
        query = query.gte("views", minViews);
      }
      if (contentFormat) {
        query = query.eq("content_format", contentFormat);
      }
      if (stitchOnly) {
        query = query.eq("is_stitch", true);
      }
      if (duetOnly) {
        query = query.eq("is_duet", true);
      }

      const ascending = sortOrder === "asc";
      // NULLS LAST for numeric columns so missing metrics do not dominate the top of the list.
      const nullsFirst =
        sortBy === "views" || sortBy === "engagement_rate" ? false : undefined;
      query = query.order(sortBy, { ascending, nullsFirst });
      query = query.range(pageParam * PAGE_SIZE, (pageParam + 1) * PAGE_SIZE - 1);

      const { data, error } = await query;
      if (error) throw error;
      return data ?? [];
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length === PAGE_SIZE ? allPages.length : undefined,
    staleTime: 5 * 60_000,
  });
}
