/**
 * Phase C — answer-only history via ``history_union`` / ``search_history_union``.
 */
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { supabase } from "@/lib/supabase";

export type HistoryUnionRow = {
  id: string;
  type: "answer";
  format: string | null;
  niche_id: number | null;
  title: string | null;
  turn_count: number;
  updated_at: string;
};

export const HISTORY_PAGE_SIZE = 50;

export const historyUnionKeys = {
  all: ["history-union"] as const,
  list: (filter: string) => [...historyUnionKeys.all, filter] as const,
  search: (query: string) => [...historyUnionKeys.all, "search", query] as const,
};

export function useHistoryUnion(filter: "all" | "answer", enabled: boolean) {
  return useInfiniteQuery({
    queryKey: historyUnionKeys.list(filter),
    queryFn: async ({ pageParam }) => {
      const { data, error } = await supabase.rpc("history_union", {
        p_filter: filter,
        p_cursor: (pageParam as string | null) ?? undefined,
        p_limit: HISTORY_PAGE_SIZE,
      });
      if (error) throw error;
      return (data ?? []) as HistoryUnionRow[];
    },
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => {
      if (!lastPage || lastPage.length < HISTORY_PAGE_SIZE) return null;
      const last = lastPage[lastPage.length - 1];
      return last?.updated_at ?? null;
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useSearchHistoryUnion(query: string) {
  return useQuery({
    queryKey: historyUnionKeys.search(query),
    queryFn: async () => {
      const q = query.trim();
      if (!q) return [] as HistoryUnionRow[];
      const { data, error } = await supabase.rpc("search_history_union", {
        p_query: q,
        p_limit: HISTORY_PAGE_SIZE,
      });
      if (error) throw error;
      return (data ?? []) as HistoryUnionRow[];
    },
    enabled: query.trim().length > 0,
    staleTime: 10_000,
  });
}
