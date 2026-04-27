import { useInfiniteQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

const PAGE_SIZE = 20;

export interface VideoCorpusFilters {
  nicheId?: number | null;
  sortBy?: "views" | "engagement_rate" | "indexed_at";
  sortOrder?: "asc" | "desc";
  dateFrom?: string | null;
  dateTo?: string | null;
  search?: string;
  minViews?: number;
  contentFormat?: string;
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
  count: (filters: Pick<VideoCorpusFilters, "nicheId" | "search" | "minViews" | "contentFormat">) =>
    ["video_corpus", "count", filters] as const,
};

export function useVideoCorpus(filters: VideoCorpusFilters = {}) {
  const { nicheId, sortBy = "indexed_at", sortOrder = "desc", dateFrom, dateTo, search, minViews, contentFormat } = filters;

  return useInfiniteQuery({
    queryKey: corpusKeys.list(filters),
    queryFn: async ({ pageParam = 0 }) => {
      let query = supabase
        .from("video_corpus")
        .select(
          "id, video_id, tiktok_url, video_url, thumbnail_url, creator_handle, views, engagement_rate, content_type, content_format, niche_id, indexed_at, likes, shares, comments, hook_phrase, breakout_multiplier, tone, cta_type, is_commerce, sound_name, creator_tier, posting_hour, video_duration",
        )
        .order(sortBy, { ascending: sortOrder === "asc" })
        .range(pageParam * PAGE_SIZE, (pageParam + 1) * PAGE_SIZE - 1);

      if (nicheId != null && nicheId !== 0) {
        query = query.eq("niche_id", nicheId);
      }
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
