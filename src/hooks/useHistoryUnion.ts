/**
 * Phase C.6.1 RPC — unified answer + chat rows for history (filter=all|answer|chat).
 */
import { useQuery } from "@tanstack/react-query";
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

export const historyUnionKeys = {
  all: ["history-union"] as const,
  list: (filter: string) => [...historyUnionKeys.all, filter] as const,
};

export function useHistoryUnion(filter: "all" | "answer" | "chat", enabled: boolean) {
  return useQuery({
    queryKey: historyUnionKeys.list(filter),
    queryFn: async () => {
      const { data, error } = await supabase.rpc("history_union", {
        p_filter: filter,
        p_cursor: null,
        p_limit: 50,
      });
      if (error) throw error;
      return (data ?? []) as HistoryUnionRow[];
    },
    enabled,
    staleTime: 30_000,
  });
}
