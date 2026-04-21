/**
 * Phase C.6.1 RPC — unified answer + chat rows for history.
 * Phase D.2.4 — swap one-shot useQuery for useInfiniteQuery with keyset
 * (`p_cursor` = last row's `updated_at`), and add a cross-type search
 * hook that ORs over answer_sessions (title + initial_q) and
 * chat_sessions (title + first_message + chat_messages.content).
 */
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { supabase } from "@/lib/supabase";

export type HistoryUnionRow = {
  id: string;
  type: "answer" | "chat";
  format: string | null;
  niche_id: number | null;
  title: string | null;
  turn_count: number;
  updated_at: string;
};

/** Page size shared by pagination + search. 50 keeps the first paint
 * responsive while giving scroll-lazy users enough rows to reach the
 * IntersectionObserver sentinel without an immediate refetch. */
export const HISTORY_PAGE_SIZE = 50;

export const historyUnionKeys = {
  all: ["history-union"] as const,
  list: (filter: string) => [...historyUnionKeys.all, filter] as const,
  search: (query: string) => [...historyUnionKeys.all, "search", query] as const,
};

/**
 * Infinite-query version of the unified history feed. Each page has up
 * to `HISTORY_PAGE_SIZE` rows ordered by `updated_at DESC`; the next
 * cursor is the last row's `updated_at` (keyset — stable under inserts
 * because the RPC orders by the same column).
 */
export function useHistoryUnion(filter: "all" | "answer" | "chat", enabled: boolean) {
  return useInfiniteQuery({
    queryKey: historyUnionKeys.list(filter),
    queryFn: async ({ pageParam }) => {
      const { data, error } = await supabase.rpc("history_union", {
        p_filter: filter,
        p_cursor: (pageParam as string | null) ?? null,
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

/**
 * Cross-type search. Returns `HistoryUnionRow[]` identical to the
 * pagination feed so the list renderer doesn't need a second shape.
 * No pagination yet — `p_limit` caps at 50 to keep the typing-UX
 * responsive; users who need deeper search refine the query.
 */
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
